"""
Genera una villa contemporanea 3D molto dettagliata e salva il file Blender
`villa.blend`.

Modello: villa moderna su due livelli con volumi sfalsati, facciata vetrata a
doppia altezza, ala a un piano con terrazza praticabile, tetto piano con
parapetto, pannelli solari e giardino disegnato (piscina a sfioro, deck in
teak, ghiaia, graminacee e alberi a più fusti).

Tutta la geometria è costruita proceduralmente, elemento per elemento: solai e
muri con spessore reale e vani passanti, infissi in alluminio con vetri veri,
scuri frangisole in legno, scale in acciaio e legno, arredi visibili
attraverso i vetri, impianti sul tetto, ecc. Nessuna geometria importata e
nessuna texture esterna: i materiali sono tutti nodi procedurali.

Contenuto del modello
---------------------
  * platea e solai in calcestruzzo con bordi a vista (giunti e fori dei
    casseri), muri perimetrali spessi 30 cm con vani passanti e spalle
  * tre volumi: corpo principale a due piani, corpo vetrato a doppia altezza,
    ala a un piano con terrazza praticabile sul tetto
  * facciata sud completamente vetrata (6,2 x 5,9 m) con montanti in alluminio,
    traversa di piano, ante scorrevoli con binario e una anta aperta
  * frangisole in listelli di legno (brise-soleil) con lame inclinate,
    rivestimento in doghe verticali, cemento a vista, intonaco bianco
  * ingresso con portico incassato, porta a bilico in acciaio con maniglione,
    citofono, cassetta postale, numero civico e applique
  * tetto piano: massetto in ghiaia, parapetto con copertina in lamiera,
    scarichi con griglia, pluviali, camino della stufa, lucernario sul vano
    scala e 8 pannelli fotovoltaici con struttura di supporto
  * interni visibili attraverso i vetri: pavimento in rovere, controsoffitto
    con faretti, cucina con isola in marmo e sgabelli, tavolo da pranzo con
    sei sedie, divano con cuscini, camino a stufa con canna fumaria, scale in
    acciaio/legno con parapetto in vetro, camera con letto e armadio,
    bagno con sanitari e mensole, libreria con libri, quadri e piante
  * giardino: deck in teak, piscina a sfioro con acqua, vialetto in lastre di
    cemento nel ghiaino, siepi, aiuole di ghiaia con massi, graminacee,
    lavande, alberi a più fusti (betulle) con foglie posate una a una
  * paesaggio di fondo: colline con macchie di alberi e cipressi, sfumati da
    una foschia atmosferica che cresce con la distanza
  * cielo procedurale (Nishita), sole, camera 40 mm con profondità di campo,
    Cycles + AgX

Esecuzione (richiede il modulo `bpy` di Blender):
    python3 genera_villa.py                 # costruisce e salva villa.blend
    python3 genera_villa.py --render        # ... e renderizza anteprima.png
    python3 genera_villa.py --quick         # render veloce di controllo
"""

import math
import os
import random
import sys

import bpy
from mathutils import Vector, Matrix, noise

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_BLEND = os.path.join(HERE, "villa.blend")
OUT_PNG = os.path.join(HERE, "anteprima.png")

SEED = 20261012
random.seed(SEED)

PI = math.pi
TAU = 2.0 * math.pi

# ---------------------------------------------------------------------------
# Parametri generali del progetto (unità: metri)
# ---------------------------------------------------------------------------
# Corpo principale (due piani):  X [-6.80, 2.80]   Y [-3.40, 3.80]
# Ala a un piano (terrazza):     X [ 2.80, 7.20]   Y [-1.00, 3.80]
AX0, AX1 = -6.80, 2.80
AY0, AY1 = -3.40, 3.80
BX0, BX1 = 2.80, 7.20
BY0, BY1 = -1.00, 3.80

T_W = 0.30                  # spessore dei muri perimetrali
T_I = 0.12                  # spessore dei tramezzi interni

Z_F0 = 0.30                 # quota del pavimento del piano terra
H_F0 = 2.95                 # altezza interna del piano terra
Z_S0 = Z_F0 + H_F0          # intradosso del solaio intermedio (3.25)
T_S0 = 0.28                 # spessore del solaio
Z_F1 = Z_S0 + T_S0          # quota del pavimento del primo piano (3.53)
H_F1 = 2.80                 # altezza interna del primo piano
Z_TOP = Z_F1 + H_F1         # sommità dei muri (6.33)
T_R = 0.32                  # spessore del solaio di copertura
Z_ROOF = Z_TOP + T_R        # piano di calpestio del tetto (6.65)
H_PARA = 0.42               # parapetto del tetto
Z_PARA = Z_ROOF + H_PARA    # sommità del parapetto (7.07)

# ala a un piano
Z_WING = 3.35               # estradosso del solaio dell'ala (terrazza)
T_WING = 0.28               # spessore del solaio dell'ala
PARAPET_W = 0.18            # cordolo perimetrale della terrazza
H_RAIL = 1.05               # altezza dei parapetti in vetro

# vani scala: doppia altezza sul soggiorno e vano della scala
VOID_X0, VOID_X1 = -6.80, -1.00     # vuoto del soggiorno a doppia altezza
VOID_Y0, VOID_Y1 = 1.00, 3.80
ST_X0, ST_X1 = -1.00, 0.20          # vano scala
ST_Y0, ST_Y1 = -1.60, 3.80

# scala: 18 alzate da 0.18 m (dislivello 3.23 m), pedate da 0.28 m
N_RISER = 18
H_RISER = (Z_F1 - Z_F0) / N_RISER   # 0.1794
T_TREAD = 0.28
W_STAIR = ST_X1 - ST_X0             # 1.20 m
Y_STAIR_BOT = AY1 - 0.28            # spigolo sud della prima pedata (3.52)

# terrazza sul tetto dell'ala (deck in legno)
DECK_Z = Z_WING + 0.06

HALF_X = (AX1 - AX0) / 2.0
HALF_Y = (AY1 - AY0) / 2.0


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def rr(a, b):
    return a + (b - a) * random.random()


def clamp(x, a, b):
    return a if x < a else (b if x > b else x)


def lerp(a, b, t):
    return a + (b - a) * t


def srgb(r, g=None, b=None):
    """Colore sRGB 0-255 -> lineare. Accetta anche una terna."""
    if g is None:
        r, g, b = r
    return tuple((c / 255.0) ** 2.2 for c in (r, g, b))


def jitter_color(col, amount):
    return tuple(clamp(c * (1.0 + rr(-amount, amount)), 0.0, 1.0) for c in col)


def mix_col(a, b, t):
    return tuple(lerp(a[i], b[i], t) for i in range(3))


# ---------------------------------------------------------------------------
# Buffer geometrici: accumulo vertici/facce e creo le mesh una sola volta
# ---------------------------------------------------------------------------
class Buf:
    """Contenitore di geometria grezza associato a un materiale."""

    __slots__ = ("name", "mat", "V", "F", "S", "C", "use_color", "color")

    def __init__(self, name, mat, use_color=False):
        self.name = name
        self.mat = mat
        self.V = []          # vertici (tuple)
        self.F = []          # facce (tuple di indici)
        self.S = []          # flag di shading smooth per faccia
        self.C = []          # colore per vertice (se use_color)
        self.use_color = use_color
        self.color = (1.0, 1.0, 1.0)

    def add(self, pts):
        """Aggiunge una lista di punti, restituisce l'indice del primo."""
        base = len(self.V)
        if self.use_color:
            col = self.color
            self.C.extend([col] * len(pts))
        self.V.extend((p[0], p[1], p[2]) for p in pts)
        return base

    def face(self, idx, smooth=False):
        self.F.append(tuple(idx))
        self.S.append(smooth)

    def poly(self, pts, smooth=False):
        """Aggiunge direttamente un poligono (vertici non condivisi)."""
        b = self.add(pts)
        self.face(range(b, b + len(pts)), smooth)

    def quad_dir(self, p0, p1, p2, p3, want, smooth=False):
        """Quad con avvolgimento tale che la normale punti verso `want`."""
        n = (p1 - p0).cross(p3 - p0)
        if n.dot(want) < 0.0:
            p0, p1, p2, p3 = p0, p3, p2, p1
        self.poly((p0, p1, p2, p3), smooth)

    @property
    def nverts(self):
        return len(self.V)


BUFS = []


def new_buf(name, mat, use_color=False):
    b = Buf(name, mat, use_color)
    BUFS.append(b)
    return b


# ---------------------------------------------------------------------------
# Primitive geometriche
# ---------------------------------------------------------------------------
_BOX_FACES = (
    ("z-", (0, 2, 6, 4)),
    ("z+", (1, 5, 7, 3)),
    ("y-", (0, 4, 5, 1)),
    ("y+", (2, 3, 7, 6)),
    ("x-", (0, 1, 3, 2)),
    ("x+", (4, 6, 7, 5)),
)


def add_box_v(buf, o, ax, ay, az, skip=()):
    """Parallelepipedo dato un vertice d'angolo e i tre vettori spigolo."""
    o = Vector(o)
    ax, ay, az = Vector(ax), Vector(ay), Vector(az)
    if ax.cross(ay).dot(az) < 0.0:
        ax, ay = ay, ax
    pts = []
    for i in (0, 1):
        for j in (0, 1):
            for k in (0, 1):
                pts.append(o + ax * i + ay * j + az * k)
    for name, idx in _BOX_FACES:
        if name in skip:
            continue
        buf.poly([pts[i] for i in idx])


def add_box(buf, p0, p1, skip=()):
    """Parallelepipedo allineato agli assi, da p0 (min) a p1 (max)."""
    p0 = Vector(p0)
    p1 = Vector(p1)
    d = p1 - p0
    add_box_v(buf, p0, (d.x, 0, 0), (0, d.y, 0), (0, 0, d.z), skip)


def add_box_c(buf, center, size, rot=None, skip=()):
    """Parallelepipedo dato centro, dimensioni e matrice di rotazione 3x3."""
    center = Vector(center)
    sx, sy, sz = size
    ax, ay, az = Vector((sx, 0, 0)), Vector((0, sy, 0)), Vector((0, 0, sz))
    if rot is not None:
        ax, ay, az = rot @ ax, rot @ ay, rot @ az
    o = center - (ax + ay + az) * 0.5
    add_box_v(buf, o, ax, ay, az, skip)


def lbox(buf, O, ex, ey, ez, u0, u1, v0, v1, w0, w1):
    """Scatola in un sistema di riferimento locale: O + ex*u + ey*v + ez*w."""
    O = Vector(O)
    p0 = O + ex * u0 + ey * v0 + ez * w0
    add_box_v(buf, p0, ex * (u1 - u0), ey * (v1 - v0), ez * (w1 - w0))


def frame_rect(buf, O, ex, ey, ez, u0, u1, v0, v1, w0, w1, t):
    """Cornice rettangolare (4 scatole) nello spazio locale."""
    lbox(buf, O, ex, ey, ez, u0, u1, v0, v0 + t, w0, w1)
    lbox(buf, O, ex, ey, ez, u0, u1, v1 - t, v1, w0, w1)
    lbox(buf, O, ex, ey, ez, u0, u0 + t, v0 + t, v1 - t, w0, w1)
    lbox(buf, O, ex, ey, ez, u1 - t, u1, v0 + t, v1 - t, w0, w1)


def ensure_ccw(profile):
    """Ordina un profilo 2D in senso antiorario."""
    a = 0.0
    n = len(profile)
    for i in range(n):
        x0, y0 = profile[i]
        x1, y1 = profile[(i + 1) % n]
        a += x0 * y1 - x1 * y0
    return profile if a >= 0 else profile[::-1]


def sweep(buf, frames, profile, closed=True, caps=True, seg_smooth=None):
    """Estrusione di un profilo 2D lungo una sequenza di sistemi di riferimento.

    frames: lista di (origine, asse_u, asse_v, scala) -- la direzione di
            avanzamento deve essere asse_u cross asse_v
    profile: lista di coppie (u, v) in senso antiorario
    """
    npf = len(profile)
    rings = []
    for fr in frames:
        o, xa, ya, s = fr
        if isinstance(s, (int, float)):
            sx = sy = s
        else:
            sx, sy = s
        rings.append(buf.add([o + xa * (p[0] * sx) + ya * (p[1] * sy) for p in profile]))
    nseg = npf if closed else npf - 1
    for r in range(len(rings) - 1):
        a, b = rings[r], rings[r + 1]
        for i in range(nseg):
            j = (i + 1) % npf
            sm = True if seg_smooth is None else seg_smooth[i]
            buf.face((a + i, a + j, b + j, b + i), sm)
    if caps and closed:
        for idx, rev in ((0, True), (len(frames) - 1, False)):
            fr = frames[idx]
            o, xa, ya, s = fr
            sx, sy = (s, s) if isinstance(s, (int, float)) else s
            pts = [o + xa * (p[0] * sx) + ya * (p[1] * sy) for p in profile]
            buf.poly(pts[::-1] if rev else pts)


def circle_profile(n, r=1.0, phase=0.0):
    return [(r * math.cos(phase + TAU * i / n), r * math.sin(phase + TAU * i / n))
            for i in range(n)]


def add_cylinder(buf, p0, p1, r, sides=12, caps=True, smooth=True, r2=None):
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0)
    L = d.length
    if L < 1e-9:
        return
    zax = d / L
    ref = Vector((0, 0, 1)) if abs(zax.z) < 0.9 else Vector((1, 0, 0))
    xa = zax.cross(ref).normalized()
    ya = zax.cross(xa).normalized()
    prof = circle_profile(sides, r)
    fr = [(p0, xa, ya, 1.0), (p1, xa, ya, 1.0)]
    if r2 is not None:
        fr = [(p0, xa, ya, 1.0), (p1, xa, ya, r2 / r)]
    sweep(buf, fr, prof, True, caps, seg_smooth=[smooth] * sides)


def add_tube(buf, pts, r, sides=10, caps=True):
    """Tubo lungo una spezzata (usato per mancorrenti e gronde)."""
    pts = [Vector(p) for p in pts]
    frames = []
    for i, p in enumerate(pts):
        if i == 0:
            d = pts[1] - pts[0]
        elif i == len(pts) - 1:
            d = pts[-1] - pts[-2]
        else:
            d = (pts[i + 1] - pts[i - 1])
        d = d.normalized()
        ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        xa = d.cross(ref).normalized()
        ya = d.cross(xa).normalized()
        frames.append((p, xa, ya, 1.0))
    sweep(buf, frames, circle_profile(sides, r), True, caps)


def add_sphere(buf, center, radius, segs=16, rings=10, amp=0.0, nscale=2.0,
               scale=(1.0, 1.0, 1.0), seed_off=0.0):
    """Sfera (eventualmente schiacciata e deformata da rumore)."""
    c = Vector(center)
    sx, sy, sz = scale
    grid = []
    for i in range(rings + 1):
        v = PI * i / rings
        row = []
        for j in range(segs):
            u = TAU * j / segs
            d = Vector((math.sin(v) * math.cos(u), math.sin(v) * math.sin(u), math.cos(v)))
            r = radius
            if amp > 0.0:
                nz = noise.noise(d * nscale + Vector((seed_off, seed_off, seed_off)))
                r *= 1.0 + amp * nz
            row.append(c + Vector((d.x * r * sx, d.y * r * sy, d.z * r * sz)))
        grid.append(row)
    base = [buf.add(row) for row in grid]
    for i in range(rings):
        a, b = base[i], base[i + 1]
        for j in range(segs):
            k = (j + 1) % segs
            if i == 0:
                buf.face((a + j, b + k, b + j), True)
            elif i == rings - 1:
                buf.face((a + j, a + k, b + j), True)
            else:
                buf.face((a + j, a + k, b + k, b + j), True)


def add_disc(buf, center, r, axis, sides=20):
    """Disco (faccia singola) con normale lungo `axis`."""
    c = Vector(center)
    ax = Vector(axis).normalized()
    ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
    xa = ax.cross(ref).normalized()
    ya = ax.cross(xa).normalized()
    pts = [c + xa * (r * math.cos(TAU * i / sides)) + ya * (r * math.sin(TAU * i / sides))
           for i in range(sides)]
    buf.poly(pts)


def add_loft(buf, ring_a, ring_b, smooth=True):
    """Collega due anelli di vertici (liste di punti) con facce quadrilatere."""
    a = buf.add(ring_a)
    b = buf.add(ring_b)
    n = len(ring_a)
    for i in range(n):
        j = (i + 1) % n
        buf.face((a + i, a + j, b + j, b + i), smooth)


# ---------------------------------------------------------------------------
# Muri e pannelli con vani passanti
# ---------------------------------------------------------------------------
def panel(buf, o, u, v, W, H, holes, flip=False):
    """Pannello rettangolare (W x H) con fori rettangolari.

    holes: lista di (u0, z0, u1, z1) in coordinate locali del pannello.
    Il pannello viene suddiviso in fasce orizzontali comprese fra i bordi
    dei fori, e ogni fascia è divisa in segmenti pieni.
    """
    cuts = {0.0, H}
    for (a0, b0, a1, b1) in holes:
        cuts.add(clamp(b0, 0.0, H))
        cuts.add(clamp(b1, 0.0, H))
    cuts = sorted(cuts)
    for i in range(len(cuts) - 1):
        y0, y1 = cuts[i], cuts[i + 1]
        if y1 - y0 < 1e-6:
            continue
        ym = 0.5 * (y0 + y1)
        spans = sorted((a0, a1) for (a0, b0, a1, b1) in holes if b0 < ym < b1)
        x = 0.0
        segs = []
        for (a0, a1) in spans:
            if a0 > x + 1e-6:
                segs.append((x, a0))
            x = max(x, a1)
        if W > x + 1e-6:
            segs.append((x, W))
        for (x0, x1) in segs:
            p0 = o + u * x0 + v * y0
            p1 = o + u * x1 + v * y0
            p2 = o + u * x1 + v * y1
            p3 = o + u * x0 + v * y1
            if flip:
                buf.poly((p0, p3, p2, p1))
            else:
                buf.poly((p0, p1, p2, p3))


def wall(buf_out, buf_in, buf_edge, o, u, v, W, H, T, holes,
         cap_top=True, cap_bottom=False, cap_left=False, cap_right=False):
    """Muro con spessore reale e vani passanti.

    o: angolo esterno in basso a sinistra; u: direzione della larghezza;
    v: direzione dell'altezza; la normale esterna è u x v.
    """
    o = Vector(o)
    u, v = Vector(u).normalized(), Vector(v).normalized()
    n = u.cross(v).normalized()
    oi = o - n * T                       # faccia interna
    panel(buf_out, o, u, v, W, H, holes, flip=False)
    panel(buf_in, oi, u, v, W, H, holes, flip=True)
    for (a0, b0, a1, b1) in holes:       # sguinci (spalle, architrave, soglia)
        P = [o + u * a0 + v * b0, o + u * a1 + v * b0,
             o + u * a1 + v * b1, o + u * a0 + v * b1]
        Q = [p - n * T for p in P]
        buf_edge.quad_dir(P[0], P[1], Q[1], Q[0], v)
        buf_edge.quad_dir(P[3], P[2], Q[2], Q[3], -v)
        buf_edge.quad_dir(P[0], P[3], Q[3], Q[0], u)
        buf_edge.quad_dir(P[1], P[2], Q[2], Q[1], -u)
    if cap_top:
        buf_edge.quad_dir(o + v * H, o + u * W + v * H,
                          o + u * W + v * H - n * T, o + v * H - n * T, v)
    if cap_bottom:
        buf_edge.quad_dir(o, o + u * W, o + u * W - n * T, o - n * T, -v)
    if cap_left:
        buf_edge.quad_dir(o, o + v * H, o + v * H - n * T, o - n * T, -u)
    if cap_right:
        buf_edge.quad_dir(o + u * W, o + u * W + v * H,
                          o + u * W + v * H - n * T, o + u * W - n * T, u)


# ---------------------------------------------------------------------------
# Sistemi di riferimento delle facciate
# ---------------------------------------------------------------------------
class Frame:
    """Sistema di riferimento di una facciata: origine, u (larghezza lungo la
    facciata), v (alto) e normale esterna."""

    __slots__ = ("o", "u", "v", "n", "name")

    def __init__(self, name, o, u, n):
        self.name = name
        self.o = Vector(o)
        self.u = Vector(u).normalized()
        self.v = Vector((0.0, 0.0, 1.0))
        self.n = Vector(n).normalized()

    def pt(self, s, z, out=0.0):
        """Punto sul piano della facciata: ascissa lungo u, quota z,
        spostamento `out` verso l'esterno."""
        return self.o + self.u * s + self.v * z + self.n * out

    def sx(self, x):
        return (Vector((x, 0.0, 0.0)) - self.o).dot(self.u)

    def sy(self, y):
        return (Vector((0.0, y, 0.0)) - self.o).dot(self.u)

    def local(self, pt):
        """Coordinate (ascissa, quota, fuori-piano) di un punto."""
        d = Vector(pt) - self.o
        return (d.dot(self.u), d.dot(self.v), d.dot(self.n))


def facciata_sud(x0, x1, y, name="sud"):
    """Facciata rivolta a sud (+Y): u cresce verso -X per avere la normale a +Y."""
    return Frame(name, (x1, y, 0.0), (-1.0, 0.0, 0.0), (0.0, 1.0, 0.0))


def facciata_nord(x0, x1, y, name="nord"):
    return Frame(name, (x0, y, 0.0), (1.0, 0.0, 0.0), (0.0, -1.0, 0.0))


def facciata_est(x, y0, y1, name="est"):
    return Frame(name, (x, y0, 0.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0))


def facciata_ovest(x, y0, y1, name="ovest"):
    return Frame(name, (x, y1, 0.0), (0.0, -1.0, 0.0), (-1.0, 0.0, 0.0))


def hole_x(fr, x0, x1, z0, z1):
    """Vano espresso in coordinate X (con la facciata rivolta a est/ovest)."""
    a, b = fr.sx(x0), fr.sx(x1)
    return (min(a, b), min(z0, z1), max(a, b), max(z0, z1))


def hole_y(fr, y0, y1, z0, z1):
    """Vano espresso in coordinate Y (con la facciata rivolta a sud/nord)."""
    a, b = fr.sy(y0), fr.sy(y1)
    return (min(a, b), min(z0, z1), max(a, b), max(z0, z1))


def sx_f(fr):
    """Funzione ascissa per vani espressi in X."""
    return lambda x0, x1, z0, z1: hole_x(fr, x0, x1, z0, z1)


def wall_on(buf_out, buf_in, buf_edge, fr, s0, s1, z0, z1, T, holes=(),
            cap_top=True, cap_bottom=False, cap_left=False, cap_right=False):
    """Muro (con spessore) appoggiato sulla facciata: s = ascissa lungo la
    facciata, z = quota. Vani: lista di (s0, z0, s1, z1) in coordinate facciata."""
    if s1 < s0:
        s0, s1 = s1, s0
    if z1 < z0:
        z0, z1 = z1, z0
    o = fr.pt(s0, z0)
    return wall(buf_out, buf_in, buf_edge, o, fr.u, fr.v, s1 - s0, z1 - z0, T,
                [(h[0] - s0, h[1] - z0, h[2] - s0, h[3] - z0) for h in holes],
                cap_top=cap_top, cap_bottom=cap_bottom, cap_left=cap_left,
                cap_right=cap_right)


def fbox(buf, fr, s0, s1, z0, z1, out0, out1):
    """Scatola nelle coordinate della facciata (ascissa, quota, fuori-piano)."""
    lbox(buf, fr.o, fr.u, fr.v, fr.n, min(s0, s1), max(s0, s1), min(z0, z1),
         max(z0, z1), min(out0, out1), max(out0, out1))

# ---------------------------------------------------------------------------
# Materiali procedurali (Cycles)
# ---------------------------------------------------------------------------
def _mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (900, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (600, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m, nt, bsdf


def _noise(nt, scale, detail=8.0, rough=0.55, dist=0.0, loc=(-500, 0), vec=None):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.location = loc
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    n.inputs["Distortion"].default_value = dist
    if vec is not None:
        nt.links.new(_sock(vec), n.inputs["Vector"])
    return n


def _voronoi(nt, scale, loc=(-500, 0), vec=None, randomness=1.0, feature="F1"):
    v = nt.nodes.new("ShaderNodeTexVoronoi")
    v.location = loc
    v.feature = feature
    v.inputs["Scale"].default_value = scale
    v.inputs["Randomness"].default_value = randomness
    if vec is not None:
        nt.links.new(vec, v.inputs["Vector"])
    return v


def _wave(nt, scale, loc=(-500, 0), vec=None, direction="Z", dist=0.0, detail=2.0,
          profile="SIN", wave_type="BANDS"):
    w = nt.nodes.new("ShaderNodeTexWave")
    w.location = loc
    w.wave_type = wave_type
    w.bands_direction = direction
    w.wave_profile = profile
    w.inputs["Scale"].default_value = scale
    w.inputs["Distortion"].default_value = dist
    w.inputs["Detail"].default_value = detail
    if vec is not None:
        nt.links.new(vec, w.inputs["Vector"])
    return w


def _brick(nt, scale, c1=(0.5, 0.5, 0.5), c2=(0.5, 0.5, 0.5), mortar=(0.2, 0.2, 0.2),
           bw=0.5, rh=0.25, loc=(-500, 0), vec=None):
    b = nt.nodes.new("ShaderNodeTexBrick")
    b.location = loc
    b.offset = 0.5
    b.offset_frequency = 2
    b.squash = 1.0
    b.squash_frequency = 2
    b.inputs["Color1"].default_value = (*c1, 1.0)
    b.inputs["Color2"].default_value = (*c2, 1.0)
    b.inputs["Mortar"].default_value = (*mortar, 1.0)
    b.inputs["Scale"].default_value = scale
    b.inputs["Mortar Size"].default_value = 0.012
    b.inputs["Brick Width"].default_value = bw
    b.inputs["Row Height"].default_value = rh
    if vec is not None:
        nt.links.new(vec, b.inputs["Vector"])
    return b


def _math(nt, op, loc, a=None, b=None, c=None, val_a=None, val_b=None, val_c=None,
          clamp_=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.location = loc
    n.use_clamp = clamp_
    for idx, (link, val) in enumerate(((a, val_a), (b, val_b), (c, val_c))):
        if link is not None:
            nt.links.new(link, n.inputs[idx])
        elif val is not None:
            n.inputs[idx].default_value = val
    return n


def _v3(p):
    """Vettore 3D da una tupla di 2 o 3 valori."""
    p = Vector(p)
    if len(p) == 2:
        p = Vector((p[0], p[1], 0.0))
    return p


def _sock(x):
    """Accetta un socket, un nodo (usa la prima uscita) o un valore."""
    if hasattr(x, "outputs"):
        return x.outputs[0]
    return x


def _bump(nt, height_out, bsdf, strength=0.3, distance=0.02, loc=(300, -300)):
    b = nt.nodes.new("ShaderNodeBump")
    b.location = loc
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = distance
    nt.links.new(_sock(height_out), b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    return b


def _ramp(nt, fac_out, stops, loc=(-250, 0)):
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.location = loc
    el = r.color_ramp.elements
    while len(el) > 1:
        el.remove(el[-1])
    el[0].position = stops[0][0]
    el[0].color = (*stops[0][1], 1.0)
    for pos, col in stops[1:]:
        e = el.new(pos)
        e.color = (*col, 1.0)
    nt.links.new(_sock(fac_out), r.inputs["Fac"])
    return r


def _mix(nt, fac_out, col_a, col_b, loc=(0, 0), blend="MIX"):
    """Nodo Mix (RGBA): A e B possono essere colori o uscite di altri nodi."""
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    m.blend_type = blend
    m.location = loc
    if isinstance(fac_out, (int, float)):
        m.inputs[0].default_value = float(fac_out)
    elif fac_out is not None:
        nt.links.new(_sock(fac_out), m.inputs[0])
    for slot, val in ((6, col_a), (7, col_b)):
        val = _sock(val) if not isinstance(val, (tuple, list)) else val
        if isinstance(val, (tuple, list)):
            m.inputs[slot].default_value = (*val, 1.0)
        else:
            nt.links.new(val, m.inputs[slot])
    return m.outputs[2]


def _coord(nt, loc=(-900, 0), kind="Object", scale=1.0):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = loc
    if scale == 1.0:
        return tc.outputs[kind]
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.location = (loc[0] + 180, loc[1])
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs[kind], mp.inputs["Vector"])
    return mp.outputs["Vector"]


def _attr(nt, name, loc=(-600, 240)):
    at = nt.nodes.new("ShaderNodeAttribute")
    at.location = loc
    at.attribute_name = name
    return at


def _moltiplica_attr(nt, col_out, attr_name="Var", loc=(-360, 120)):
    """Moltiplica un colore per l'attributo di colore per vertice `Var`."""
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    mx.blend_type = "MULTIPLY"
    mx.location = loc
    mx.inputs[0].default_value = 1.0
    if isinstance(col_out, (tuple, list)):
        mx.inputs[6].default_value = (*col_out, 1.0)
    else:
        nt.links.new(_sock(col_out), mx.inputs[6])
    nt.links.new(_attr(nt, attr_name, loc=(loc[0] - 260, loc[1] + 120)).outputs["Color"],
                 mx.inputs[7])
    return mx.outputs[2]


def _fori_casseri(nt, vec, passo=0.66, raggio=0.020, loc=(-1150, -760)):
    """Maschera dei fori dei tiranti dei casseri: griglia regolare di punti."""
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = loc
    nt.links.new(vec, sep.inputs["Vector"])
    quad = []
    for i, axis in enumerate(("X", "Z")):
        ly = loc[1] - i * 240
        m = _math(nt, "MULTIPLY", (loc[0] + 180, ly), sep.outputs[axis], val_b=1.0 / passo)
        w = _math(nt, "WRAP", (loc[0] + 320, ly), m.outputs["Value"], val_b=0.0, val_c=1.0)
        s = _math(nt, "SUBTRACT", (loc[0] + 460, ly), w.outputs["Value"], val_b=0.5)
        quad.append(_math(nt, "POWER", (loc[0] + 600, ly), s.outputs["Value"], val_b=2.0))
    a = _math(nt, "ADD", (loc[0] + 740, loc[1] - 120), quad[0].outputs["Value"],
              quad[1].outputs["Value"])
    d = _math(nt, "SQRT", (loc[0] + 880, loc[1] - 120), a.outputs["Value"])
    lt = _math(nt, "LESS_THAN", (loc[0] + 1020, loc[1] - 120), d.outputs["Value"],
               val_b=raggio / passo)
    return lt.outputs["Value"]


HAZE_COL = (208, 216, 224)      # colore della foschia atmosferica (sRGB)


def _foschia(nt, col_out, d0=45.0, d1=230.0, amount=0.42, loc=(-60, -420)):
    """Prospettiva aerea: sfuma il colore verso la foschia con la distanza
    dalla camera (nodo Camera Data / View Distance)."""
    cam = nt.nodes.new("ShaderNodeCameraData")
    cam.location = (loc[0] - 420, loc[1])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.location = (loc[0] - 240, loc[1])
    mr.inputs["From Min"].default_value = d0
    mr.inputs["From Max"].default_value = d1
    mr.inputs["To Min"].default_value = 0.0
    mr.inputs["To Max"].default_value = amount
    mr.interpolation_type = "SMOOTHSTEP"
    mr.clamp = True
    nt.links.new(cam.outputs["View Distance"], mr.inputs["Value"])
    return _mix(nt, mr.outputs["Result"], col_out, srgb(*HAZE_COL), loc=loc)


def _emissivo(nt, bsdf, col, forza, loc=(430, -200)):
    bsdf.inputs["Emission Color"].default_value = (*srgb(*col), 1.0)
    bsdf.inputs["Emission Strength"].default_value = forza
    return bsdf


# --- cemento, intonaco ------------------------------------------------------
def mat_calcestruzzo(name="Calcestruzzo", c0=(172, 170, 164), c1=(140, 138, 132),
                     passo=0.68, fori=True):
    """Calcestruzzo a vista, con le impronte delle tavole dei casseri e i fori
    dei tiranti disposti a griglia."""
    m, nt, b = _mat(name)
    gen = _coord(nt, (-1700, 0), "Object")
    tavole = _wave(nt, 3.7, loc=(-1350, 260), vec=gen, direction="Z", dist=1.6, detail=3.0)
    vena = _noise(nt, 3.2, 8.0, 0.6, 0.4, loc=(-1350, 40), vec=gen)
    grana = _noise(nt, 70.0, 10.0, 0.7, loc=(-1350, -180), vec=gen)
    chiazze = _noise(nt, 0.7, 9.0, 0.55, 0.5, loc=(-1350, -400), vec=gen)
    base = _ramp(nt, chiazze.outputs["Fac"],
                 [(0.32, srgb(*c1)), (0.55, srgb(*c0)),
                  (0.80, srgb(c0[0] + 8, c0[1] + 8, c0[2] + 8))], loc=(-1080, -400))
    col = _mix(nt, 0.32, base.outputs["Color"], vena.outputs["Fac"], loc=(-840, -300))
    h1 = _math(nt, "MULTIPLY_ADD", (-840, 300), tavole.outputs["Fac"], val_a=1.0,
               c=vena.outputs["Fac"])
    h2 = _math(nt, "MULTIPLY_ADD", (-660, 300), grana.outputs["Fac"], val_a=0.25,
               c=h1.outputs["Value"])
    h_fin = h2.outputs["Value"]
    if fori:
        maschera = _fori_casseri(nt, gen, passo=passo)
        h_fin = _math(nt, "MULTIPLY_ADD", (-420, 300), maschera, val_a=-0.9,
                      c=h2.outputs["Value"]).outputs["Value"]
        # i fori dei tiranti sono anche più scuri del cemento
        col = _mix(nt, _math(nt, "MULTIPLY", (-600, -440), maschera, val_b=0.45).outputs["Value"],
                   col, srgb(112, 110, 106), loc=(-420, -340))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.78
    b.inputs["Specular IOR Level"].default_value = 0.3
    _bump(nt, h_fin, b, 0.4, 0.006)
    return m


def mat_intonaco():
    """Intonaco bianco continuo, con una lieve grana e ombreggiature morbide."""
    m, nt, b = _mat("Intonaco_bianco")
    gen = _coord(nt, (-1200, 0), "Object")
    grana = _noise(nt, 90.0, 10.0, 0.7, loc=(-900, 200), vec=gen)
    macchie = _noise(nt, 1.1, 9.0, 0.55, 0.25, loc=(-900, -180), vec=gen)
    base = _ramp(nt, macchie.outputs["Fac"],
                 [(0.30, srgb(232, 230, 225)), (0.55, srgb(243, 241, 236)),
                  (0.80, srgb(226, 224, 218))], loc=(-650, -180))
    col = _mix(nt, 0.30, base.outputs["Color"], grana.outputs["Fac"], loc=(-420, 0))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    b.inputs["Specular IOR Level"].default_value = 0.25
    hm = _math(nt, "MULTIPLY_ADD", (-420, 260), grana.outputs["Fac"], val_a=0.35)
    nt.links.new(macchie.outputs["Fac"], hm.inputs[2])
    _bump(nt, hm.outputs["Value"], b, 0.18, 0.003)
    return m


# --- legno ------------------------------------------------------------------
def mat_legno(name, c0, c1, rough=0.55, scale=(6.0, 6.0, 26.0), coat=0.0, dist=2.5,
              attr=False, bump=0.3):
    """Legno: venatura allungata lungo Z, con colore per vertice opzionale."""
    m, nt, b = _mat(name)
    gen = _coord(nt, (-1200, 0), "Object")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.location = (-1000, 0)
    mp.inputs["Scale"].default_value = scale
    nt.links.new(gen, mp.inputs["Vector"])
    gen = mp.outputs["Vector"]
    fibra = _wave(nt, 1.0, loc=(-800, 200), vec=gen, direction="Z", dist=dist, detail=6.0)
    nodi = _noise(nt, 6.0, 10.0, 0.7, 1.2, loc=(-800, -160), vec=gen)
    col = _ramp(nt, fibra.outputs["Fac"],
                [(0.05, srgb(*c0)), (0.45, srgb(*c1)), (0.95, srgb(*c0))], loc=(-560, 200))
    col2 = _mix(nt, 0.35, col.outputs["Color"], nodi.outputs["Fac"], loc=(-330, 100))
    out = col2
    if attr:
        out = _moltiplica_attr(nt, col2, "Var", loc=(-140, 60))
    nt.links.new(out, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = 0.3
    if coat > 0.0:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.25
    h = _math(nt, "MULTIPLY_ADD", (-330, 300), fibra.outputs["Fac"], val_a=0.5)
    nt.links.new(nodi.outputs["Fac"], h.inputs[2])
    _bump(nt, h.outputs["Value"], b, bump, 0.004)
    return m


# --- metalli, vetri, acqua --------------------------------------------------
def mat_metallo(name, col, rough, metallic=1.0, aniso=0.0, bump=0.12):
    m, nt, b = _mat(name)
    b.inputs["Base Color"].default_value = (*srgb(*col), 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    if aniso > 0.0:
        b.inputs["Anisotropic"].default_value = aniso
    gen = _coord(nt, (-900, -200), "Object")
    n = _noise(nt, 120.0, 8.0, 0.6, loc=(-650, -200), vec=gen)
    _bump(nt, n.outputs["Fac"], b, bump, 0.003)
    return m


def mat_vetro(name="Vetro", col=(228, 238, 236), rough=0.02, ior=1.45, tinta_tr=0.0):
    """Vetro trasparente: i raggi d'ombra attraversano il vetro, così il sole
    entra nelle stanze e illumina gli interni."""
    m, nt, b = _mat(name)
    b.inputs["Base Color"].default_value = (*srgb(*col), 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = ior
    m.use_backface_culling = False
    lp = nt.nodes.new("ShaderNodeLightPath")
    lp.location = (300, 320)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.location = (300, -240)
    tr.inputs["Color"].default_value = (0.9, 0.93, 0.92, 1.0)
    mixs = nt.nodes.new("ShaderNodeMixShader")
    mixs.location = (480, 0)
    outn = [x for x in nt.nodes if x.type == "OUTPUT_MATERIAL"][0]
    outn.location = (700, 0)
    nt.links.new(lp.outputs["Is Shadow Ray"], mixs.inputs[0])
    nt.links.new(b.outputs["BSDF"], mixs.inputs[1])
    nt.links.new(tr.outputs["BSDF"], mixs.inputs[2])
    nt.links.new(mixs.outputs["Shader"], outn.inputs["Surface"])
    return m


def mat_acqua():
    """Acqua della piscina: trasparente, appena increspata, con fondo visibile."""
    m, nt, b = _mat("Acqua")
    b.inputs["Base Color"].default_value = (*srgb(178, 214, 212), 1.0)
    b.inputs["Roughness"].default_value = 0.05
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.333
    gen = _coord(nt, (-900, 0), "Object")
    onde = _wave(nt, 14.0, loc=(-650, 0), vec=gen, direction="Z", dist=3.0, detail=3.0)
    onde2 = _noise(nt, 22.0, 6.0, 0.6, loc=(-650, -260), vec=gen)
    h = _math(nt, "MULTIPLY_ADD", (-420, 0), onde.outputs["Fac"], val_a=0.5)
    nt.links.new(onde2.outputs["Fac"], h.inputs[2])
    _bump(nt, h.outputs["Value"], b, 0.12, 0.01)
    return m


# --- pietre, ghiaia, terreno ------------------------------------------------
def mat_pietra(name="Pietra", c0=(178, 168, 150), c1=(138, 128, 112), scale=3.0,
               attr=False, haze=False):
    m, nt, b = _mat(name)
    gen = _coord(nt, (-1100, 0), "Object")
    vena = _noise(nt, scale, 9.0, 0.6, 0.5, loc=(-850, 200), vec=gen)
    gran = _noise(nt, 60.0, 12.0, 0.7, loc=(-850, -80), vec=gen)
    col = _ramp(nt, vena.outputs["Fac"],
                [(0.28, srgb(*c1)), (0.52, srgb(*c0)), (0.78, srgb(*(c0[0] - 12, c0[1] - 12, c0[2] - 10)))],
                loc=(-600, 200))
    out = _mix(nt, 0.25, col.outputs["Color"], gran.outputs["Fac"], loc=(-380, 100))
    if attr:
        out = _moltiplica_attr(nt, out, "Var", loc=(-160, 60))
    if haze:
        out = _foschia(nt, out, loc=(-60, -320))
    nt.links.new(out, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.72
    b.inputs["Specular IOR Level"].default_value = 0.35
    h = _math(nt, "MULTIPLY_ADD", (-380, 300), vena.outputs["Fac"], val_a=0.6)
    nt.links.new(gran.outputs["Fac"], h.inputs[2])
    _bump(nt, h.outputs["Value"], b, 0.45, 0.008)
    return m


def mat_ghiaia():
    """Ghiaia fine: ciottoli piccoli e fitti, con chiazze più chiare."""
    m, nt, b = _mat("Ghiaia")
    gen = _coord(nt, (-1100, 0), "Object")
    ciottoli = _voronoi(nt, 120.0, loc=(-850, 200), vec=gen, randomness=1.0)
    grande = _noise(nt, 0.55, 8.0, 0.55, 0.4, loc=(-850, -80), vec=gen)
    col = _ramp(nt, ciottoli.outputs["Distance"],
                [(0.05, srgb(176, 168, 154)), (0.35, srgb(126, 120, 108)),
                 (0.75, srgb(88, 84, 76))], loc=(-600, 200))
    col2 = _mix(nt, grande.outputs["Fac"], col.outputs["Color"],
                srgb(158, 150, 138), loc=(-380, 120))
    col2 = _foschia(nt, col2, d0=45.0, d1=220.0, amount=0.45, loc=(-180, -320))
    nt.links.new(col2, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    b.inputs["Specular IOR Level"].default_value = 0.3
    _bump(nt, ciottoli.outputs["Distance"], b, 0.7, 0.02)
    return m


def mat_terra():
    m, nt, b = _mat("Terriccio")
    gen = _coord(nt, (-900, 0), "Object")
    n = _noise(nt, 22.0, 10.0, 0.65, 0.3, loc=(-650, 0), vec=gen)
    col = _ramp(nt, n.outputs["Fac"],
                [(0.25, srgb(58, 44, 34)), (0.6, srgb(86, 66, 48)),
                 (0.85, srgb(112, 92, 70))], loc=(-420, 0))
    col = _foschia(nt, col, loc=(-180, -300))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    _bump(nt, n.outputs["Fac"], b, 0.5, 0.012)
    return m


# --- vegetazione ------------------------------------------------------------
def mat_prato():
    """Prato inglese: verde uniforme con chiazze, fili d'erba e zone più chiare."""
    m, nt, b = _mat("Prato")
    vec = _coord(nt, (-1400, 0), "Object")
    big = _noise(nt, 0.07, 6.0, 0.55, 0.4, loc=(-950, 380), vec=vec)
    mid = _noise(nt, 0.5, 10.0, 0.6, 0.5, loc=(-950, 140), vec=vec)
    fine = _noise(nt, 26.0, 12.0, 0.75, loc=(-950, -120), vec=vec)
    ramp = _ramp(nt, mid.outputs["Fac"],
                 [(0.28, srgb(58, 88, 34)), (0.52, srgb(82, 116, 44)),
                  (0.78, srgb(108, 138, 58))], loc=(-700, 140))
    secca = _ramp(nt, big.outputs["Fac"],
                  [(0.52, (0.0, 0.0, 0.0)), (0.72, (0.6, 0.6, 0.6))], loc=(-700, 380))
    c1 = _mix(nt, secca.outputs["Color"], ramp.outputs["Color"], srgb(146, 146, 84),
              loc=(-460, 200))
    col = _mix(nt, 0.20, c1, fine.outputs["Fac"], loc=(-300, 0))
    col = _foschia(nt, col, d0=55.0, d1=230.0, amount=0.38)
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    b.inputs["Specular IOR Level"].default_value = 0.2
    _bump(nt, fine.outputs["Fac"], b, 0.35, 0.02)
    return m


def mat_fogliame(name="Fogliame", c0=(46, 78, 34), c1=(104, 140, 58), attr=True,
                 haze=True, rough=0.6, sub=0.15, transl=0.22):
    """Fogliame: rumore di colore, tinta per foglia (attributo `Var`),
    traslucenza e foschia in lontananza."""
    m, nt, b = _mat(name)
    gen = _coord(nt, (-1100, 0), "Object")
    n = _noise(nt, 24.0, 12.0, 0.75, 0.4, loc=(-850, 0), vec=gen)
    col = _ramp(nt, n.outputs["Fac"], [(0.3, srgb(*c0)), (0.7, srgb(*c1))], loc=(-600, 0))
    out = col.outputs["Color"]
    if attr:
        out = _moltiplica_attr(nt, out, "Var", loc=(-360, 120))
    if haze:
        out = _foschia(nt, out, loc=(-180, -300))
    nt.links.new(out, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = 0.35
    if sub > 0.0:
        b.inputs["Subsurface Weight"].default_value = sub
        b.inputs["Subsurface Radius"].default_value = (0.03, 0.05, 0.02)
    _bump(nt, n.outputs["Fac"], b, 0.4, 0.01)
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
    tr.location = (300, -260)
    nt.links.new(out, tr.inputs["Color"])
    mixs = nt.nodes.new("ShaderNodeMixShader")
    mixs.location = (480, -60)
    mixs.inputs[0].default_value = transl
    outn = [x for x in nt.nodes if x.type == "OUTPUT_MATERIAL"][0]
    outn.location = (700, 0)
    nt.links.new(b.outputs["BSDF"], mixs.inputs[1])
    nt.links.new(tr.outputs["BSDF"], mixs.inputs[2])
    nt.links.new(mixs.outputs["Shader"], outn.inputs["Surface"])
    return m


def mat_corteccia_betulla():
    """Corteccia di betulla: bianco latte con lenticelle scure orizzontali."""
    m, nt, b = _mat("Corteccia_betulla")
    gen = _coord(nt, (-1100, 0), "Object", scale=1.0)
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.location = (-950, 0)
    mp.inputs["Scale"].default_value = (2.0, 2.0, 8.0)
    nt.links.new(gen, mp.inputs["Vector"])
    gen = mp.outputs["Vector"]
    lent = _wave(nt, 3.0, loc=(-750, 200), vec=gen, direction="Z", dist=2.5, detail=5.0)
    strappi = _noise(nt, 9.0, 10.0, 0.7, 0.6, loc=(-750, -80), vec=gen)
    macchie = _noise(nt, 1.2, 8.0, 0.6, 0.3, loc=(-750, -360), vec=gen)
    bianco = _ramp(nt, macchie.outputs["Fac"],
                   [(0.3, srgb(226, 222, 214)), (0.6, srgb(243, 240, 232)),
                    (0.85, srgb(214, 210, 202))], loc=(-520, -360))
    scuro = _ramp(nt, lent.outputs["Fac"],
                  [(0.30, (0.0, 0.0, 0.0)), (0.44, (0.55, 0.55, 0.55)),
                   (0.62, (1.0, 1.0, 1.0))], loc=(-520, 200))
    col = _mix(nt, scuro.outputs["Color"], bianco.outputs["Color"], srgb(52, 46, 42),
               loc=(-280, -80))
    col = _mix(nt, 0.3, col, strappi.outputs["Fac"], loc=(-100, -80))
    col = _foschia(nt, col, loc=(40, -320))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.72
    b.inputs["Specular IOR Level"].default_value = 0.28
    h = _math(nt, "MULTIPLY_ADD", (-280, 340), strappi.outputs["Fac"], val_a=0.6)
    nt.links.new(lent.outputs["Fac"], h.inputs[2])
    _bump(nt, h.outputs["Value"], b, 0.5, 0.01)
    return m


# --- tessuti, arredi, superfici interne -------------------------------------
def mat_tessuto(name, col, rough=0.9, sheen=0.45, weave=520.0, scale=1.0):
    m, nt, b = _mat(name)
    gen = _coord(nt, (-900, 0), "Object")
    trama = _noise(nt, weave, 4.0, 0.6, loc=(-650, -160), vec=gen)
    lana = _noise(nt, 60.0, 8.0, 0.6, loc=(-650, 120), vec=gen)
    colr = _mix(nt, 0.22, srgb(*col), lana.outputs["Fac"], loc=(-400, 0))
    colr = _mix(nt, 0.10, colr, trama.outputs["Fac"], loc=(-200, 0))
    nt.links.new(colr, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Sheen Weight"].default_value = sheen
    b.inputs["Sheen Roughness"].default_value = 0.4
    _bump(nt, trama.outputs["Fac"], b, 0.25, 0.002)
    return m


def mat_tappeto():
    """Tappeto annodato: fondo chiaro con righe e macchie di colore."""
    m, nt, b = _mat("Tappeto")
    gen = _coord(nt, (-1100, 0), "Object")
    nodi = _noise(nt, 420.0, 4.0, 0.6, loc=(-850, -200), vec=gen)
    disegno = _noise(nt, 6.0, 4.0, 0.5, 0.8, loc=(-850, 200), vec=gen)
    righe = _wave(nt, 5.0, loc=(-850, 460), vec=gen, direction="X", dist=0.0, detail=1.0,
                  profile="SAW")
    col = _ramp(nt, disegno.outputs["Fac"],
                [(0.35, srgb(198, 190, 176)), (0.65, srgb(176, 150, 122))], loc=(-600, 200))
    col2 = _mix(nt, 0.35, col.outputs["Color"], srgb(120, 118, 126), loc=(-380, 300))
    col2 = _mix(nt, righe.outputs["Fac"], col2, srgb(206, 200, 188), loc=(-280, 300))
    col2 = _mix(nt, 0.28, col2, nodi.outputs["Fac"], loc=(-200, 0))
    nt.links.new(col2, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    b.inputs["Sheen Weight"].default_value = 0.3
    _bump(nt, nodi.outputs["Fac"], b, 0.3, 0.002)
    return m


def mat_marmo():
    """Marmo bianco con venature grigie (piano cucina, bagno)."""
    m, nt, b = _mat("Marmo")
    gen = _coord(nt, (-1100, 0), "Object", scale=0.35)
    vene = _wave(nt, 1.6, loc=(-850, 200), vec=gen, direction="Z", dist=6.0, detail=6.0)
    vene2 = _noise(nt, 0.9, 8.0, 0.6, 0.8, loc=(-850, -80), vec=gen)
    base = _ramp(nt, vene.outputs["Fac"],
                 [(0.35, srgb(238, 236, 232)), (0.62, srgb(214, 212, 208)),
                  (0.88, srgb(186, 186, 184))], loc=(-600, 200))
    col = _mix(nt, 0.30, base.outputs["Color"], srgb(122, 124, 128), loc=(-380, 100))
    col = _mix(nt, vene2.outputs["Fac"], col, srgb(236, 234, 230), loc=(-200, 100))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.12
    b.inputs["Specular IOR Level"].default_value = 0.5
    _bump(nt, vene2.outputs["Fac"], b, 0.06, 0.002)
    return m


def mat_ceramica():
    m, nt, b = _mat("Ceramica")
    gen = _coord(nt, (-800, 0), "Object")
    n = _noise(nt, 200.0, 6.0, 0.6, loc=(-560, 0), vec=gen)
    col = _mix(nt, 0.1, srgb(246, 246, 244), n.outputs["Fac"], loc=(-340, 0))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.15
    b.inputs["Specular IOR Level"].default_value = 0.5
    return m


def mat_semplice(name, col, rough=0.6, emit=None, emit_str=0.0, metallic=0.0,
                 spec=0.3, attr=False):
    m, nt, b = _mat(name)
    if attr:
        base = _moltiplica_attr(nt, srgb(*col), "Var", loc=(300, 120))
        nt.links.new(base, b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (*srgb(*col), 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Specular IOR Level"].default_value = spec
    if emit is not None:
        _emissivo(nt, b, emit, emit_str)
    return m


def mat_pannello_fv():
    """Pannello fotovoltaico: celle blu scuro su fondo nero, cornice in alluminio."""
    m, nt, b = _mat("Fotovoltaico")
    gen = _coord(nt, (-900, 0), "Object")
    celle = _brick(nt, 12.0, c1=srgb(18, 26, 56), c2=srgb(24, 34, 70),
                   mortar=srgb(176, 178, 182), bw=0.38, rh=0.14, loc=(-650, 0), vec=gen)
    nt.links.new(celle.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.12
    b.inputs["Metallic"].default_value = 0.35
    b.inputs["Specular IOR Level"].default_value = 0.5
    _bump(nt, celle.outputs["Fac"], b, 0.15, 0.002)
    return m


def mat_libri():
    """Dorso dei libri: colore per volume dall'attributo `Var`."""
    m, nt, b = _mat("Libri")
    base = _moltiplica_attr(nt, srgb(200, 196, 190), "Var", loc=(300, 120))
    nt.links.new(base, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.8
    b.inputs["Specular IOR Level"].default_value = 0.25
    return m

# ---------------------------------------------------------------------------
# Elementi ricorrenti: pavimenti, doghe, deck, ringhiere, vetri
# ---------------------------------------------------------------------------
def pavimento(buf, x0, y0, x1, y1, z, asse="x", larg=0.16, lung=1.35, spess=0.022):
    """Pavimento in listoni di rovere con colore leggermente diverso ognuno."""
    if asse == "x":
        y = y0
        riga = 0
        while y < y1 - 1e-4:
            w = min(larg, y1 - y)
            off = 0.0 if riga % 2 == 0 else lung * 0.5
            x = x0 - off
            while x < x1 - 1e-4:
                l = min(lung, x1 - x)
                if l > 0.08:
                    buf.color = jitter_color((0.72, 0.55, 0.36), 0.22)
                    add_box(buf, (x + 0.004, y + 0.003, z), (x + l - 0.004, y + w - 0.003, z + spess))
                x += lung
            y += larg
            riga += 1
    else:
        x = x0
        col = 0
        while x < x1 - 1e-4:
            w = min(larg, x1 - x)
            off = 0.0 if col % 2 == 0 else lung * 0.5
            y = y0 - off
            while y < y1 - 1e-4:
                l = min(lung, y1 - y)
                if l > 0.08:
                    buf.color = jitter_color((0.72, 0.55, 0.36), 0.22)
                    add_box(buf, (x + 0.003, y + 0.004, z), (x + w - 0.003, y + l - 0.004, z + spess))
                y += lung
            x += larg
            col += 1


def doghe_verticali(buf, fr, s0, s1, z0, z1, passo=0.072, larg=0.055, spess=0.028,
                    tinte=((120, 74, 44), (86, 52, 32), (150, 104, 62))):
    """Rivestimento in doghe verticali di legno (termotrattato)."""
    s = s0 + 0.01
    i = 0
    while s < s1 - 0.02:
        buf.color = jitter_color(srgb(tinte[i % len(tinte)]), 0.16)
        fbox(buf, fr, s, s + larg, z0, z1, 0.0, spess)
        s += passo
        i += 1


def deck(buf, x0, y0, x1, y1, z, asse="x", larg=0.145, giunto=0.008, spess=0.032):
    """Deck in teak: listoni con giunti, su traversine nascoste."""
    if asse == "x":
        y = y0
        while y < y1 - 1e-4:
            w = min(larg, y1 - y)
            buf.color = jitter_color(srgb(158, 112, 68), 0.20)
            add_box(buf, (x0, y + giunto / 2, z), (x1, y + w - giunto / 2, z + spess))
            y += larg
        # traversine di supporto
        yy = y0 + 0.3
        while yy < y1:
            add_box(buf, (x0, yy, z - 0.05), (x1, yy + 0.06, z))
            yy += 0.62
    else:
        x = x0
        while x < x1 - 1e-4:
            w = min(larg, x1 - x)
            buf.color = jitter_color(srgb(158, 112, 68), 0.20)
            add_box(buf, (x + giunto / 2, y0, z), (x + w - giunto / 2, y1, z + spess))
            x += larg
        xx = x0 + 0.3
        while xx < x1:
            add_box(buf, (xx, y0, z - 0.05), (xx + 0.06, y1, z))
            xx += 0.62


def ringhiera_vetro(buf_glass, buf_acc, p0, p1, z_base, h=0.98, n_post=None):
    """Parapetto in vetro temprato con corrimano e montanti in acciaio."""
    p0, p1 = _v3(p0), _v3(p1)
    d = p1 - p0
    L = d.length
    if L < 0.05:
        return
    u = d / L
    n = u.cross(Vector((0, 0, 1)))
    if n.length < 1e-6:
        n = Vector((1, 0, 0))
    n.normalize()
    # profilo di base a U rovesciata
    add_box_v(buf_acc, p0 + Vector((0, 0, z_base)) - n * 0.05,
              u * L, n * 0.10, Vector((0, 0, 0.09)))
    # lastre di vetro
    passo = L / max(1, int(round(L / 1.15)))
    x = 0.0
    while x < L - 0.02:
        l = min(passo, L - x) - 0.02
        a = p0 + u * (x + 0.01)
        b = p0 + u * (x + 0.01 + l)
        add_box_v(buf_glass, a + Vector((0, 0, z_base)) - n * 0.006,
                  u * l, Vector((0, 0, h - 0.09)), n * 0.012)
        x += passo
    # corrimano
    add_tube(buf_acc, [p0 + Vector((0, 0, z_base + h)) - n * 0.02,
                       p1 + Vector((0, 0, z_base + h)) - n * 0.02], 0.026, sides=12)
    # montanti
    n_post = n_post or max(2, int(round(L / 1.6)) + 1)
    for i in range(n_post):
        t = i / float(n_post - 1)
        c = p0 + u * (L * t)
        add_cylinder(buf_acc, c - n * 0.03 + Vector((0, 0, z_base - 0.02)),
                     c - n * 0.03 + Vector((0, 0, z_base + h + 0.01)), 0.022, sides=10)


def vetro(buf, fr, s0, s1, z0, z1, out0, spess=0.012, n_div=0):
    """Lastra di vetro (eventualmente divisa in più campiture)."""
    if n_div <= 0:
        fbox(buf, fr, s0, s1, z0, z1, out0, out0 + spess)
    else:
        passo = (s1 - s0) / (n_div + 1)
        for i in range(n_div + 1):
            a = s0 + i * passo + (0.012 if i > 0 else 0.0)
            b = s0 + (i + 1) * passo - (0.012 if i < n_div else 0.0)
            fbox(buf, fr, a, b, z0, z1, out0, out0 + spess)


def serramento(buf_al, buf_glass, buf_guarn, fr, s0, s1, z0, z1, out0,
               n_montanti=0, traversa=None, apertura=None):
    """Infisso in alluminio a taglio termico: telaio perimetrale, montanti
    verticali, eventuale traversa orizzontale e lastre di vetro.

    out0: posizione del filo esterno del telaio rispetto alla facciata.
    """
    d = 0.075                      # profondità del telaio
    t = 0.055                      # larghezza vista del telaio
    fr_ = (out0, out0 + d)
    # telaio perimetrale
    fbox(buf_al, fr, s0, s1, z0, z0 + t, *fr_)
    fbox(buf_al, fr, s0, s1, z1 - t, z1, *fr_)
    fbox(buf_al, fr, s0, s0 + t, z0 + t, z1 - t, *fr_)
    fbox(buf_al, fr, s1 - t, s1, z0 + t, z1 - t, *fr_)
    # guarnizioni (battuta scura attorno al vetro)
    go = out0 + d * 0.45
    fbox(buf_guarn, fr, s0 + t, s1 - t, z0 + t, z0 + t + 0.016, go, go + 0.03)
    fbox(buf_guarn, fr, s0 + t, s1 - t, z1 - t - 0.016, z1 - t, go, go + 0.03)
    fbox(buf_guarn, fr, s0 + t, s0 + t + 0.016, z0 + t, z1 - t, go, go + 0.03)
    fbox(buf_guarn, fr, s1 - t - 0.016, s1 - t, z0 + t, z1 - t, go, go + 0.03)
    # vetro
    vetro(buf_glass, fr, s0 + t, s1 - t, z0 + t, z1 - t, out0 + d * 0.42)
    # montanti verticali
    for i in range(n_montanti):
        c = s0 + (s1 - s0) * (i + 1) / (n_montanti + 1)
        fbox(buf_al, fr, c - 0.028, c + 0.028, z0 + t, z1 - t, *fr_)
    # traversa orizzontale
    if traversa is not None:
        fbox(buf_al, fr, s0 + t, s1 - t, traversa - 0.03, traversa + 0.03, *fr_)
    # maniglia
    if apertura is not None:
        sm, zm = apertura
        fbox(buf_al, fr, sm - 0.02, sm + 0.02, zm - 0.14, zm + 0.14, out0 - 0.035,
             out0 - 0.005)


def porta_scorrevole(buf_al, buf_glass, buf_guarn, fr, s0, s1, z0, z1, out0,
                     n_ante=2, aperta=True, canale=(0.0, 0.10)):
    """Porta finestra scorrevole: binario a scomparsa, ante con telaio e vetro;
    l'anta più interna resta aperta così si vede l'interno."""
    d = 0.06
    t = 0.06
    # binario di base e di testa
    fbox(buf_al, fr, s0, s1, z0, z0 + 0.035, out0 - 0.02, out0 + n_ante * canale[1] + 0.06)
    fbox(buf_al, fr, s0, s1, z1 - 0.075, z1, out0 - 0.02, out0 + n_ante * canale[1] + 0.06)
    # soglia (a filo pavimento)
    fbox(buf_al, fr, s0, s1, z0 - 0.03, z0, out0 - 0.02, out0 + n_ante * canale[1] + 0.06)
    larga = (s1 - s0) / n_ante
    for i in range(n_ante):
        c_out = out0 + 0.02 + i * canale[1]
        if aperta and i == n_ante - 1:
            a, b = s0 - larga * 0.92, s0 - 0.01        # anta scorrevole aperta
        else:
            a, b = s0 + i * larga, s0 + (i + 1) * larga - 0.012
        fbox(buf_al, fr, a, b, z0 + 0.04, z0 + 0.04 + t, c_out, c_out + d)
        fbox(buf_al, fr, a, b, z1 - 0.115, z1 - 0.115 + t, c_out, c_out + d)
        fbox(buf_al, fr, a, a + t, z0 + 0.04 + t, z1 - 0.115 - t, c_out, c_out + d)
        fbox(buf_al, fr, b - t, b, z0 + 0.04 + t, z1 - 0.115 - t, c_out, c_out + d)
        # vetro dell'anta
        go = c_out + d * 0.45
        fbox(buf_guarn, fr, a + t, b - t, z0 + 0.04 + t, z0 + 0.05 + t, go, go + 0.028)
        fbox(buf_guarn, fr, a + t, b - t, z1 - 0.125 - t, z1 - 0.115 - t, go, go + 0.028)
        vetro(buf_glass, fr, a + t, b - t, z0 + 0.04 + t, z1 - 0.115 - t, c_out + d * 0.42)
        # maniglia a incasso
        if not (aperta and i == n_ante - 1):
            fbox(buf_al, fr, b - 0.03, b - 0.005, z0 + 1.02, z0 + 1.24, c_out - 0.02, c_out)


def frangisole(buf_legno, buf_acc, fr, s0, s1, z0, z1, passo=0.165, larg=0.16,
               spess=0.028, tilt=34.0, z_supporti=None):
    """Brise-soleil in listelli di legno orientabili (lame inclinate)."""
    th = math.radians(tilt)
    ex = Vector(fr.u)
    ey = (Vector(fr.n) * math.cos(th) - Vector(fr.v) * math.sin(th)).normalized()
    ez = (Vector(fr.n) * math.sin(th) + Vector(fr.v) * math.cos(th)).normalized()
    rot = Matrix((ex, ey, ez)).transposed()
    z = z0 + passo * 0.5
    while z < z1:
        c = fr.pt(s0 + (s1 - s0) * 0.5, z, 0.20) + Vector((0, 0, 0))
        c = c + Vector((0, 0, 0))
        add_box_c(buf_legno, c, (s1 - s0, larg, spess), rot)
        buf_legno.color = jitter_color(srgb(150, 108, 66), 0.16)
        z += passo
    # supporti laterali (piatti in acciaio)
    for s in (s0 + 0.05, s1 - 0.05):
        fbox(buf_acc, fr, s - 0.02, s + 0.02, z0, z1, 0.02, 0.06)


# ---------------------------------------------------------------------------
# Platea e solai
# ---------------------------------------------------------------------------
def build_platea(B):
    cls = B["cls"]
    add_box(cls, (AX0 - 0.45, AY0 - 0.45, -0.34), (BX1 + 0.45, AY1 + 0.45, -0.20))
    add_box(cls, (AX0 - 0.13, AY0 - 0.13, -0.32), (BX1 + 0.13, AY1 + 0.13, Z_F0))
    # zoccolo in ghiaia addossato alla platea
    add_box(B["grav"], (AX0 - 0.60, AY0 - 0.60, -0.14), (BX1 + 0.60, AY1 + 0.60, -0.02))


def build_solai(B):
    cls, into = B["cls"], B["into"]
    # solaio intermedio: tre regioni (il vuoto del soggiorno e il vano scala
    # restano aperti)
    regs = [
        (AX0 - 0.06, AY0 - 0.06, AX1 + 0.06, -1.24),      # corpo nord
        (ST_X1, -1.24, AX1 + 0.06, AY1 + 0.06),           # fascia est
        (AX0 - 0.06, -1.24, VOID_X1, AY1 - 0.06),         # fascia ovest (camera)
    ]
    for (x0, y0, x1, y1) in regs:
        add_box(cls, (x0, y0, Z_S0), (x1, y1, Z_F1))
        add_box(into, (x0 + 0.02, y0 + 0.02, Z_S0 - 0.02), (x1 - 0.02, y1 - 0.02, Z_S0))
    # copertura del corpo principale (con foro per il lucernario)
    SK0, SK1 = -0.94, 0.14            # lucernario sul vano scala
    SKY0, SKY1 = -0.62, 0.58
    for (x0, y0, x1, y1) in ((AX0 - 0.10, AY0 - 0.10, AX1 + 0.10, SKY0),
                             (AX0 - 0.10, SKY1, AX1 + 0.10, AY1 + 0.10),
                             (AX0 - 0.10, SKY0, SK0, SKY1),
                             (SK1, SKY0, AX1 + 0.10, SKY1)):
        add_box(cls, (x0, y0, Z_TOP), (x1, y1, Z_ROOF))
    add_box(into, (AX0, AY0, Z_TOP), (AX1, AY1, Z_TOP + 0.02))   # intradosso
    # pozzetto del lucernario (spallette intonacate)
    for (x0, y0, x1, y1) in ((SK0 - 0.06, SKY0 - 0.06, SK1 + 0.06, SKY0),
                             (SK0 - 0.06, SKY1, SK1 + 0.06, SKY1 + 0.06),
                             (SK0 - 0.06, SKY0, SK0, SKY1),
                             (SK1, SKY0, SK1 + 0.06, SKY1)):
        add_box(into, (x0, y0, Z_TOP), (x1, y1, Z_ROOF + 0.06))
    # solaio di copertura dell'ala (terrazza praticabile)
    add_box(cls, (BX0, BY0 - 0.06, Z_WING - T_WING), (BX1 + 0.06, BY1 + 0.06, Z_WING))
    add_box(into, (BX0, BY0, Z_WING - T_WING - 0.02), (BX1, BY1, Z_WING - T_WING))
    # trave di bordo fra il corpo principale e l'ala (sotto la quota del solaio)
    add_box(cls, (AX1 - 0.02, BY0, Z_WING), (AX1 + 0.06, BY1, Z_F1))


# ---------------------------------------------------------------------------
# Muri
# ---------------------------------------------------------------------------
def build_muri_terra(B):
    cls, into = B["cls"], B["into"]

    # --- facciata sud del corpo principale ---------------------------------
    fr = facciata_sud(AX0, AX1, AY1)
    wall_on(cls, into, into, fr, fr.sx(0.20), fr.sx(2.80), Z_F0, Z_TOP, T_W,
            holes=[hole_x(fr, 0.40, 2.40, Z_F0, Z_S0),
                   hole_x(fr, 0.70, 2.30, 4.30, 5.70)])
    wall_on(cls, into, into, fr, fr.sx(-6.80), fr.sx(-6.60), Z_F0, Z_TOP, T_W,
            cap_left=True, cap_right=True)

    # --- nicchia d'ingresso (cemento a vista) ------------------------------
    add_box(cls, (0.20, 2.40, Z_F0), (0.40, AY1, Z_S0))            # spalla ovest
    add_box(cls, (2.40, 2.40, Z_F0), (2.60, AY1, Z_S0))            # spalla est
    fr_n = Frame("nicchia", (2.60, 2.60, 0.0), (-1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    wall_on(cls, into, cls, fr_n, fr_n.sx(2.60), fr_n.sx(0.20), Z_F0, Z_S0, 0.20,
            holes=[hole_x(fr_n, 0.70, 1.90, Z_F0, 2.80)])
    add_box(B["cls"], (0.30, 2.70, Z_F0 - 0.02), (2.50, 3.80, Z_F0 + 0.02))  # soglia

    # --- facciata ovest (cemento a vista) ----------------------------------
    fro = facciata_ovest(AX0, AY0, AY1)
    wall_on(cls, into, into, fro, fro.sy(AY1), fro.sy(AY0), Z_F0, Z_TOP, T_W,
            holes=[hole_y(fro, -3.00, -1.60, 1.45, 2.35),
                   hole_y(fro, -2.60, -0.80, 4.20, 5.60)])

    # --- facciata nord -----------------------------------------------------
    frn = facciata_nord(AX0, AX1, AY0)
    wall_on(into, into, into, frn, frn.sx(AX0), frn.sx(AX1), Z_F0, Z_TOP, T_W,
            holes=[hole_x(frn, -5.60, -2.40, 1.45, 2.35),
                   hole_x(frn, -1.20, -0.40, 1.70, 2.30),
                   hole_x(frn, 1.90, 2.50, 1.60, 2.40),
                   hole_x(frn, -5.40, -3.00, 4.20, 5.60),
                   hole_x(frn, 1.90, 2.50, 4.50, 5.50),
                   hole_x(frn, -2.30, -1.30, 4.50, 5.50)])

    # --- facciata est: tratto a fianco dell'ala ----------------------------
    fre = facciata_est(AX1, AY0, AY1)
    wall_on(cls, into, into, fre, fre.sy(AY0), fre.sy(BY0), Z_F0, Z_WING, T_W,
            holes=[hole_y(fre, -3.00, -2.00, 1.60, 2.40)])

    # --- facciata est sopra la terrazza ------------------------------------
    wall_on(into, into, into, fre, fre.sy(BY0), fre.sy(AY1), Z_F1, Z_TOP, T_W,
            holes=[hole_y(fre, 1.70, 3.50, Z_F1, 6.05),
                   hole_y(fre, -0.80, -0.20, 4.50, 5.60)])

    # --- ala a un piano ----------------------------------------------------
    ws = facciata_sud(BX0, BX1, BY1)
    wall_on(into, into, into, ws, ws.sx(BX1), ws.sx(BX0), Z_F0, Z_WING - T_WING, T_W,
            holes=[hole_x(ws, 2.90, 5.90, Z_F0 - 0.02, 3.00),
                   hole_x(ws, 6.20, 7.10, Z_F0 - 0.02, 3.00)])
    we = facciata_est(BX1, BY0, BY1)
    wall_on(into, into, into, we, we.sy(BY0), we.sy(BY1), Z_F0, Z_WING - T_WING, T_W,
            holes=[hole_y(we, 0.00, 2.60, Z_F0 - 0.02, 2.90),
                   hole_y(we, -0.90, -0.40, 1.50, 2.50)])
    wn = facciata_nord(BX0, BX1, BY0)
    wall_on(cls, into, into, wn, wn.sx(BX0), wn.sx(BX1), Z_F0, Z_WING - T_WING, T_W,
            holes=[hole_x(wn, 3.40, 4.60, 1.60, 2.60)])
    # rivestimento in doghe sul lato nord dell'ala
    doghe_verticali(B["legno"], wn, wn.sx(BX0) + 0.02, wn.sx(3.30), Z_F0 + 0.05,
                    Z_WING - T_WING - 0.05)
    doghe_verticali(B["legno"], wn, wn.sx(4.70), wn.sx(BX1) - 0.02, Z_F0 + 0.05,
                    Z_WING - T_WING - 0.05)


def build_tramezzi(B):
    into = B["into"]

    def muro(x0, y0, x1, y1, z0, z1, sp, holes=()):
        a, b = Vector((x0, y0, 0.0)), Vector((x1, y1, 0.0))
        u = (b - a)
        W = u.length
        u = u / W
        wall(into, into, into, a, u, (0, 0, 1), W, z1 - z0, sp,
             [(h[0], h[1] - z0, h[2], h[3] - z0) for h in holes], cap_top=True,
             cap_bottom=True)

    # --- piano terra: locale di servizio / wc -----------------------------
    muro(1.60, -3.40, 1.60, -1.60, Z_F0, Z_S0, T_I,
         holes=[(0.50, 0.30, 1.30, 2.40)])
    muro(1.60, -1.60, 2.80, -1.60, Z_F0, Z_S0, T_I)
    # --- piano terra: lavanderia ------------------------------------------
    muro(-0.20, -2.40, -0.20, -3.40, Z_F0, Z_S0, T_I)
    muro(-1.40, -2.40, -0.20, -2.40, Z_F0, Z_S0, T_I,
         holes=[(0.15, 0.30, 1.15, 2.40)])
    # --- piano primo: camera, bagno padronale, cabina armadio --------------
    muro(AX0, 1.00, VOID_X1, 1.00, Z_S0, Z_TOP, T_I)          # parete sud camera
    muro(-2.60, -3.40, -2.60, 1.00, Z_F1, Z_TOP, T_I,          # parete est camera
         holes=[(2.80, 0.00, 3.70, 2.10)])
    muro(VOID_X1, -3.40, VOID_X1, -0.90, Z_F1, Z_TOP, T_I,     # bagno / disimpegno
         holes=[(0.50, 0.00, 1.40, 2.10)])
    muro(-2.60, -0.80, VOID_X1, -0.80, Z_F1, Z_TOP, T_I)       # parete sud bagno
    muro(1.60, -3.40, 1.60, -1.60, Z_F1, Z_TOP, T_I,           # cabina armadio
         holes=[(0.50, 0.00, 1.30, 2.10)])
    muro(1.60, -1.60, AX1, -1.60, Z_F1, Z_TOP, T_I)


def build_scala(B):
    """Scala in acciaio e rovere: 17 pedate a sbalzo fra due traversine piatte,
    parapetto in vetro con corrimano in acciaio e luce a LED sotto la rampa."""
    acc, rovere, glass = B["acciaio"], B["rovere"], B["vetro"]
    xa, xb = ST_X0 + 0.06, ST_X1 - 0.10
    for k in range(17):
        y0 = Y_STAIR_BOT - k * T_TREAD
        y1 = y0 - T_TREAD
        z = Z_F0 + (k + 1) * H_RISER
        rovere.color = jitter_color(srgb(178, 134, 86), 0.14)
        add_box(rovere, (ST_X0 + 0.03, y1 - 0.025, z - 0.048), (ST_X1 - 0.03, y0, z))
        for x in (xa, xb):
            add_box(acc, (x, y1 - 0.02, z - 0.34), (x + 0.05, y0, z - 0.045))
    # luce a LED continua sotto le pedate
    for k in range(17):
        y0 = Y_STAIR_BOT - k * T_TREAD
        y1 = y0 - T_TREAD
        z = Z_F0 + (k + 1) * H_RISER
        add_box(B["luce"], (ST_X0 + 0.12, y1 - 0.01, z - 0.395), (ST_X1 - 0.16, y0, z - 0.345))
    # parapetto in vetro e corrimano sul lato est (aperto)
    for k in range(0, 17, 2):
        y0 = Y_STAIR_BOT - k * T_TREAD
        k2 = min(k + 2, 17)
        y1 = Y_STAIR_BOT - k2 * T_TREAD
        z = Z_F0 + k * H_RISER + 0.06
        dz = k2 * H_RISER - k * H_RISER
        add_box_v(glass, (ST_X1 - 0.055, y0 - 0.01, z), Vector((0.014, 0, 0)),
                  Vector((0, y1 - y0 + 0.02, dz)), Vector((0, 0, 0.90)))
        add_cylinder(acc, (ST_X1 - 0.048, y0, Z_F0 + k * H_RISER + 0.04),
                     (ST_X1 - 0.048, y0, Z_F0 + k * H_RISER + 1.00), 0.017, sides=8)
    add_tube(acc, [Vector((ST_X1 - 0.048, Y_STAIR_BOT + 0.02, Z_F0 + 1.02)),
                   Vector((ST_X1 - 0.048, Y_STAIR_BOT - 16.5 * T_TREAD, Z_F0 + 17.5 * H_RISER + 1.02))],
             0.024, sides=10)
    # parapetto in vetro sul lato ovest dove la scala guarda il vuoto
    for k in range(9, 17, 2):
        y0 = Y_STAIR_BOT - k * T_TREAD
        k2 = min(k + 2, 17)
        y1 = Y_STAIR_BOT - k2 * T_TREAD
        z = Z_F0 + k * H_RISER + 0.06
        dz = k2 * H_RISER - k * H_RISER
        add_box_v(glass, (ST_X0 + 0.041, y0 - 0.01, z), Vector((0.014, 0, 0)),
                  Vector((0, y1 - y0 + 0.02, dz)), Vector((0, 0, 0.90)))
        add_cylinder(acc, (ST_X0 + 0.048, y0, Z_F0 + k * H_RISER + 0.04),
                     (ST_X0 + 0.048, y0, Z_F0 + k * H_RISER + 1.00), 0.017, sides=8)
    add_tube(acc, [Vector((ST_X0 + 0.048, Y_STAIR_BOT - 9 * T_TREAD, Z_F0 + 10 * H_RISER + 1.02)),
                   Vector((ST_X0 + 0.048, Y_STAIR_BOT - 16.5 * T_TREAD, Z_F0 + 17.5 * H_RISER + 1.02))],
             0.024, sides=10)

# ---------------------------------------------------------------------------
# Facciata vetrata, infissi, porte
# ---------------------------------------------------------------------------
def build_facciata_vetro(B):
    """Facciata continua a doppia altezza: montanti in alluminio, traversa di
    piano, vetri fissi e un'anta scorrevole che resta aperta."""
    al, glass, guarn = B["serr"], B["vetro"], B["guarn"]
    fr = facciata_sud(AX0, AX1, AY1)
    s0, s1 = fr.sx(0.20), fr.sx(-6.60)      # 2.60 -> 9.40
    z0, z1 = Z_F0 + 0.02, Z_TOP - 0.05
    d, t = 0.075, 0.06
    # traversa inferiore (canaletta a filo pavimento)
    fbox(al, fr, s0, s1, z0 - 0.02, z0 + 0.03, -0.10, 0.0)
    # traversa di testa
    fbox(al, fr, s0, s1, z1 - 0.06, z1, -d, 0.0)
    # traversa di piano, allineata al solaio intermedio
    fbox(al, fr, s0, s1, Z_F1 - 0.05, Z_F1 + 0.06, -d, 0.0)
    # montanti verticali ogni 1,13 m
    n_bay = 6
    for i in range(n_bay + 1):
        s = s0 + (s1 - s0) * i / n_bay
        fbox(al, fr, s - 0.035, s + 0.035, z0, z1, -d - 0.02, 0.0)
    # vetri: campiture fra montanti e traverse
    for i in range(n_bay):
        a = s0 + (s1 - s0) * i / n_bay + 0.035
        b = s0 + (s1 - s0) * (i + 1) / n_bay - 0.035
        # piano terra
        fbox(guarn, fr, a, b, z0 + 0.03, z0 + 0.05, -0.045, -0.02)
        vetro(glass, fr, a, b, z0 + 0.05, Z_F1 - 0.05, -0.030)
        fbox(guarn, fr, a, b, Z_F1 + 0.06, Z_F1 + 0.08, -0.045, -0.02)
        # piano primo
        vetro(glass, fr, a, b, Z_F1 + 0.08, z1 - 0.06, -0.030)
    # l'anta scorrevole all'estremità ovest resta aperta
    i = 0
    a = s0 + (s1 - s0) * i / n_bay + 0.035
    b = s0 + (s1 - s0) * (i + 1) / n_bay - 0.035
    fbox(al, fr, a - 0.02, b + 0.02, z0 + 0.02, z0 + 0.05, 0.02, 0.09)      # soglia
    fbox(al, fr, a - 0.02, b - 0.02, z0 + 0.05, Z_F1 - 0.05, 0.02, 0.11)    # anta aperta
    fbox(guarn, fr, a, b - 0.04, z0 + 0.06, z0 + 0.08, 0.05, 0.075)
    # maniglia a scomparsa sull'anta
    fbox(al, fr, b - 0.05, b - 0.03, Z_F0 + 1.05, Z_F0 + 1.35, 0.09, 0.14)


def build_infissi(B):
    al, glass, guarn = B["serr"], B["vetro"], B["guarn"]

    def finestra(fr, x0, x1, z0, z1, n_mont=0, traversa=None, out0=-0.075, modo="x"):
        h = hole_x(fr, x0, x1, z0, z1) if modo == "x" else hole_y(fr, x0, x1, z0, z1)
        serramento(al, glass, guarn, fr, h[0], h[2], h[1], h[3], out0,
                   n_montanti=n_mont, traversa=traversa)

    # --- piano terra --------------------------------------------------------
    fro = facciata_ovest(AX0, AY0, AY1)
    finestra(fro, -3.00, -1.60, 1.45, 2.35, modo="y")            # cucina
    frn = facciata_nord(AX0, AX1, AY0)
    finestra(frn, -5.60, -2.40, 1.45, 2.35, n_mont=2)            # cucina nord
    finestra(frn, -1.20, -0.40, 1.70, 2.30)                      # lavanderia
    finestra(frn, 1.90, 2.50, 1.60, 2.40)                        # wc piano terra
    fre = facciata_est(AX1, AY0, AY1)
    finestra(fre, -3.00, -2.00, 1.60, 2.40, modo="y")            # wc piano terra est
    # --- piano primo --------------------------------------------------------
    finestra(fro, -2.60, -0.80, 4.20, 5.60, n_mont=1)            # camera ovest
    finestra(frn, -5.40, -3.00, 4.20, 5.60, n_mont=1)            # camera nord
    finestra(frn, 1.90, 2.50, 4.50, 5.50)                        # cabina armadio
    finestra(frn, -2.30, -1.30, 4.50, 5.50)                      # bagno padronale
    frs = facciata_sud(AX0, AX1, AY1)
    finestra(frs, 0.70, 2.30, 4.30, 5.70, n_mont=2)              # ballatoio
    # --- ala: pranzo --------------------------------------------------------
    ws = facciata_sud(BX0, BX1, BY1)
    h = hole_x(ws, 2.90, 5.90, Z_F0 - 0.02, 3.00)
    porta_scorrevole(al, glass, guarn, ws, h[0], h[2], h[1], h[3], -0.075,
                     n_ante=3, aperta=True, canale=(0.0, 0.085))
    h = hole_x(ws, 6.20, 7.10, Z_F0 - 0.02, 3.00)
    serramento(al, glass, guarn, ws, h[0], h[2], h[1], h[3], -0.075)
    we = facciata_est(BX1, BY0, BY1)
    h = hole_y(we, 0.00, 2.60, Z_F0 - 0.02, 2.90)
    serramento(al, glass, guarn, we, h[0], h[2], h[1], h[3], -0.075, n_montanti=1,
               traversa=Z_F0 + 1.60)
    h = hole_y(we, -0.90, -0.40, 1.50, 2.50)
    serramento(al, glass, guarn, we, h[0], h[2], h[1], h[3], -0.075)
    wn = facciata_nord(BX0, BX1, BY0)
    h = hole_x(wn, 3.40, 4.60, 1.60, 2.60)
    serramento(al, glass, guarn, wn, h[0], h[2], h[1], h[3], -0.075)
    # --- porta finestra della terrazza --------------------------------------
    h = hole_y(fre, 1.70, 3.50, Z_F1, 6.05)
    porta_scorrevole(al, glass, guarn, fre, h[0], h[2], h[1], h[3], -0.075,
                     n_ante=2, aperta=True, canale=(0.0, 0.085))


def build_ingresso(B):
    """Porta d'ingresso a bilico in acciaio, maniglione, citofono, applique,
    numero civico e cassetta postale nella nicchia in cemento a vista."""
    acc, ferro, cls = B["acciaio"], B["ferro"], B["cls"]
    fr = Frame("porta", (2.60, 2.60, 0.0), (-1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    # telaio in acciaio
    fbox(acc, fr, 0.70, 1.90, 2.80, 2.90, -0.20, 0.0)
    fbox(acc, fr, 0.68, 0.74, Z_F0, 2.90, -0.20, 0.0)
    fbox(acc, fr, 1.86, 1.92, Z_F0, 2.90, -0.20, 0.0)
    # anta a bilico (acciaio con piastra in legno)
    fbox(ferro, fr, 0.75, 1.85, Z_F0 + 0.01, 2.79, -0.15, -0.09)
    fbox(B["legno"], fr, 1.00, 1.60, Z_F0 + 0.30, 2.50, -0.09, -0.075)
    for k in range(7):
        zz = Z_F0 + 0.35 + k * 0.32
        fbox(B["legno"], fr, 1.00, 1.60, zz, zz + 0.22, -0.075, -0.065)
    # maniglione verticale passante
    add_cylinder(acc, fr.pt(1.78, Z_F0 + 0.75, -0.30), fr.pt(1.78, Z_F0 + 2.05, -0.30),
                 0.019, sides=10)
    for zz in (Z_F0 + 0.80, Z_F0 + 2.00):
        add_cylinder(acc, fr.pt(1.78, zz, -0.30), fr.pt(1.78, zz, -0.15), 0.014, sides=8)
    # cardini
    for (s, zz) in ((0.78, Z_F0 + 2.60), (0.78, Z_F0 + 0.20)):
        add_cylinder(acc, fr.pt(s, zz, -0.14), fr.pt(s, zz, -0.06), 0.022, sides=8)
    # citofono e pulsantiera
    add_box(ferro, (2.44, 2.58, 1.35), (2.52, 2.62, 1.57))
    add_disc(B["luce"], (2.44, 2.60, 1.46), 0.012, (-1, 0, 0), sides=10)
    # cassetta postale e numero civico
    add_box(ferro, (0.34, 3.44, 1.40), (0.42, 3.62, 1.62))
    add_box(B["ottone"], (0.40, 3.44, 1.60), (0.415, 3.56, 1.63))
    add_box(ferro, (2.46, 3.50, 1.75), (2.52, 3.76, 2.20))
    add_box(B["ottone"], (2.455, 3.52, 1.82), (2.46, 3.74, 1.96))
    # applique a parete accanto alla porta
    add_box(ferro, (2.36, 3.30, 2.05), (2.44, 3.50, 2.25))
    add_box(B["luce"], (2.35, 3.32, 2.07), (2.37, 3.48, 2.23))
    # zerbino
    add_box(B["tessuto"], (0.55, 3.00, Z_F0 + 0.005), (2.05, 3.70, Z_F0 + 0.02))


def build_pensilina(B):
    """Pensilina in doghe di legno sospesa sull'ingresso, con tiranti in
    acciaio e due fioriere ai lati."""
    legno, acc, cls = B["legno"], B["acciaio"], B["cls"]
    x0, x1 = 0.25, 2.55
    y0, y1 = 3.80, 5.40
    z = 3.30
    # trave di bordo in acciaio
    add_box(acc, (x0, y1 - 0.06, z), (x1, y1, z + 0.14))
    add_box(acc, (x0, y0, z), (x0 + 0.06, y1, z + 0.14))
    add_box(acc, (x1 - 0.06, y0, z), (x1, y1, z + 0.14))
    # doghe
    yy = y0 + 0.08
    while yy < y1 - 0.10:
        legno.color = jitter_color(srgb(150, 108, 66), 0.16)
        add_box(legno, (x0 + 0.04, yy, z + 0.05), (x1 - 0.04, yy + 0.08, z + 0.145))
        yy += 0.155
    # tiranti diagonali verso la facciata
    for x in (x0 + 0.10, x1 - 0.10):
        add_cylinder(acc, (x, y1 - 0.03, z + 0.10), (x, y0 + 0.05, z + 1.05), 0.014,
                     sides=8)
    # fioriere
    for x in (x0 + 0.35, x1 - 0.55):
        add_box(cls, (x, 3.90, Z_F0), (x + 0.42, 4.32, Z_F0 + 0.42))
        add_box(B["terra"], (x + 0.03, 3.93, Z_F0 + 0.34), (x + 0.39, 4.29, Z_F0 + 0.42))


def build_frangisole(B):
    """Brise-soleil in listelli di legno sulla parte alta della facciata
    vetrata: scherma il sole estivo lasciando la vista libera."""
    fr = facciata_sud(AX0, AX1, AY1)
    frangisole(B["legno"], B["acciaio"], fr, fr.sx(-1.60), fr.sx(-5.20), 4.55, 6.24,
               passo=0.17, larg=0.19, spess=0.03, tilt=32.0)
    # rivestimento in doghe verticali sulla parete della terrazza
    fre = facciata_est(AX1, BY0, AY1)
    doghe_verticali(B["legno"], fre, fre.sy(BY0) + 0.05, fre.sy(1.60), Z_F1 + 0.08,
                    Z_TOP - 0.10, passo=0.078, larg=0.06, spess=0.03)
    doghe_verticali(B["legno"], fre, fre.sy(3.58), fre.sy(AY1) - 0.05, Z_F1 + 0.08,
                    Z_TOP - 0.10, passo=0.078, larg=0.06, spess=0.03)


# ---------------------------------------------------------------------------
# Copertura piana: parapetto, ghiaia, scarichi, camino, lucernario, FV
# ---------------------------------------------------------------------------
def build_tetto(B):
    cls, acc, fv, legno = B["cls"], B["acciaio"], B["fv"], B["legno"]
    # --- parapetto perimetrale con copertina in lamiera --------------------
    p = 0.20
    lati = ((AX0 - 0.05, AY0 - 0.05, AX0 - 0.05 + p, AY1 + 0.05),
            (AX1 + 0.05 - p, AY0 - 0.05, AX1 + 0.05, AY1 + 0.05),
            (AX0 - 0.05, AY0 - 0.05, AX1 + 0.05, AY0 - 0.05 + p),
            (AX0 - 0.05, AY1 + 0.05 - p, AX1 + 0.05, AY1 + 0.05))
    for (x0, y0, x1, y1) in lati:
        add_box(cls, (x0, y0, Z_ROOF), (x1, y1, Z_PARA))
        # copertina in lamiera grecata con gocciolatoio
        add_box(acc, (x0 - 0.05, y0 - 0.05, Z_PARA), (x1 + 0.05, y1 + 0.05, Z_PARA + 0.04))
        add_box(acc, (x0 - 0.05, y0 - 0.05, Z_PARA - 0.06), (x0 - 0.02, y1 + 0.05, Z_PARA))
        add_box(acc, (x1 + 0.02, y0 - 0.05, Z_PARA - 0.06), (x1 + 0.05, y1 + 0.05, Z_PARA))
    # --- massetto in ghiaia (quattro riquadri attorno al lucernario) --------
    SK0, SK1, SKY0, SKY1 = -0.94, 0.14, -0.62, 0.58
    for (x0, y0, x1, y1) in ((AX0 + 0.16, AY0 + 0.16, AX1 - 0.16, SKY0 - 0.10),
                             (AX0 + 0.16, SKY1 + 0.10, AX1 - 0.16, AY1 - 0.16),
                             (AX0 + 0.16, SKY0 - 0.10, SK0 - 0.10, SKY1 + 0.10),
                             (SK1 + 0.10, SKY0 - 0.10, AX1 - 0.16, SKY1 + 0.10)):
        add_box(B["grav"], (x0, y0, Z_ROOF + 0.005), (x1, y1, Z_ROOF + 0.06))
    # --- scarichi pluviali con griglia -------------------------------------
    for (x, y) in ((AX0 + 0.55, AY0 + 0.55), (AX1 - 0.55, AY0 + 0.55)):
        add_cylinder(acc, (x, y, Z_ROOF + 0.05), (x, y, Z_ROOF - 0.28), 0.075, sides=14)
        add_sphere(acc, (x, y, Z_ROOF - 0.24), 0.085, segs=14, rings=6,
                   scale=(1.0, 1.0, 0.55))
        # discendente esterna sulla facciata nord
        add_tube(acc, [Vector((x, AY0 + 0.52, Z_ROOF + 0.02)),
                       Vector((x, AY0 - 0.14, Z_ROOF + 0.02)),
                       Vector((x, AY0 - 0.14, 0.35)),
                       Vector((x, AY0 - 0.32, 0.12))], 0.058, sides=12)
        for zz in (1.2, 2.6, 4.2, 5.6):
            add_cylinder(acc, (x, AY0 - 0.30, zz), (x, AY0, zz), 0.05, sides=8)
    # --- camino della stufa (attraversa il vuoto a doppia altezza) ---------
    add_cylinder(B["ferro"], (-6.20, 2.00, Z_F0 + 0.55), (-6.20, 2.00, Z_ROOF + 0.72),
                 0.075, sides=14)
    add_cylinder(B["ferro"], (-6.20, 2.00, Z_ROOF + 0.10), (-6.20, 2.00, Z_ROOF + 0.16),
                 0.115, sides=14)
    add_sphere(B["ferro"], (-6.20, 2.00, Z_ROOF + 0.78), 0.13, segs=14, rings=6,
               scale=(1.0, 1.0, 0.6))
    add_disc(B["ferro"], (-6.20, 2.00, Z_ROOF + 0.86), 0.20, (0, 0, 1), sides=16)
    add_cylinder(B["ferro"], (-6.20, 2.00, Z_ROOF + 0.86), (-6.20, 2.00, Z_ROOF + 0.92),
                 0.10, sides=12)
    # --- sfiato della colonna di scarico -----------------------------------
    add_cylinder(acc, (2.20, -3.00, Z_ROOF), (2.20, -3.00, Z_ROOF + 0.42), 0.05, sides=10)
    add_sphere(acc, (2.20, -3.00, Z_ROOF + 0.46), 0.07, segs=10, rings=5,
               scale=(1.0, 1.0, 0.7))
    # --- lucernario sul vano scala -----------------------------------------
    al, glass = B["serr"], B["vetro"]
    add_box(al, (SK0 - 0.10, SKY0 - 0.10, Z_ROOF + 0.06), (SK1 + 0.10, SKY0 - 0.03, Z_ROOF + 0.20))
    add_box(al, (SK0 - 0.10, SKY1 + 0.03, Z_ROOF + 0.06), (SK1 + 0.10, SKY1 + 0.10, Z_ROOF + 0.20))
    add_box(al, (SK0 - 0.10, SKY0, Z_ROOF + 0.06), (SK0 - 0.03, SKY1, Z_ROOF + 0.20))
    add_box(al, (SK1 + 0.03, SKY0, Z_ROOF + 0.06), (SK1 + 0.10, SKY1, Z_ROOF + 0.20))
    add_box(glass, (SK0, SKY0, Z_ROOF + 0.10), (SK1, SKY1, Z_ROOF + 0.124))
    # --- pannelli fotovoltaici (due file inclinate) ------------------------
    rot = Matrix.Rotation(math.radians(-22.0), 3, "X")
    for riga, y in enumerate((-2.95, -1.45)):
        for i in range(4):
            x = -5.70 + i * 1.55
            add_box_c(fv, (x + 0.80, y, Z_ROOF + 0.52), (1.60, 1.13, 0.035), rot)
            add_box_c(B["ferro"], (x + 0.80, y + 0.56, Z_ROOF + 0.28), (1.62, 0.06, 0.06))
            add_box_c(B["ferro"], (x + 0.80, y + 0.42, Z_ROOF + 0.30),
                      (0.08, 1.05, 0.06), rot)
            add_box_c(B["ferro"], (x + 0.80, y - 0.42, Z_ROOF + 0.62),
                      (0.08, 1.05, 0.06), rot)
        add_box(B["ferro"], (-5.70, y - 0.05, Z_ROOF + 0.02), (1.10, y + 0.05, Z_ROOF + 0.06))
        add_box(B["ferro"], (-1.10, y - 0.05, Z_ROOF + 0.02), (0.70, y + 0.05, Z_ROOF + 0.06))


# ---------------------------------------------------------------------------
# Terrazza sull'ala: deck, parapetto in vetro, pergola, arredi
# ---------------------------------------------------------------------------
def build_terrazza(B):
    legno, acc, glass, al = B["legno"], B["acciaio"], B["vetro"], B["serr"]
    # --- pavimento in teak -------------------------------------------------
    deck(legno, 2.94, -0.94, 7.14, 3.74, Z_WING + 0.05, asse="x", larg=0.145,
         giunto=0.008, spess=0.032)
    # fascia perimetrale in lamiera (profilo di bordo)
    for (x0, y0, x1, y1) in ((2.88, 3.74, 7.20, 3.80), (7.14, -0.94, 7.20, 3.80),
                             (2.88, -1.00, 7.20, -0.94)):
        add_box(acc, (x0, y0, Z_WING + 0.02), (x1, y1, Z_WING + 0.085))
    # --- parapetti in vetro ------------------------------------------------
    ringhiera_vetro(glass, acc, (2.94, 3.74), (7.14, 3.74), Z_WING + 0.085, 1.00)
    ringhiera_vetro(glass, acc, (7.14, 3.74), (7.14, -0.94), Z_WING + 0.085, 1.00)
    ringhiera_vetro(glass, acc, (7.14, -0.94), (2.94, -0.94), Z_WING + 0.085, 1.00)
    # --- pergola in legno --------------------------------------------------
    px = (4.85, 7.05)
    py = (-0.85, 1.55)
    zt = 5.85
    for x in px:
        for y in py:
            add_box(legno, (x - 0.05, y - 0.05, Z_WING + 0.085), (x + 0.05, y + 0.05, zt))
    for y in py:
        add_box(legno, (px[0], y - 0.06, zt), (px[1], y + 0.06, zt + 0.18))
    yy = py[0]
    while yy < py[1] - 0.02:
        legno.color = jitter_color(srgb(150, 108, 66), 0.16)
        add_box(legno, (px[0] - 0.06, yy, zt + 0.18), (px[1] + 0.06, yy + 0.045,
                                                       zt + 0.28))
        yy += 0.115
    # --- arredi: lettini, tavolino, fioriere -------------------------------
    for i, y in enumerate((2.35, 3.20)):
        bx = 3.55
        add_box(legno, (bx, y, Z_WING + 0.22), (bx + 1.85, y + 0.68, Z_WING + 0.28))
        add_box(B["tessuto"], (bx + 0.06, y + 0.03, Z_WING + 0.28), (bx + 1.79, y + 0.65,
                                                                    Z_WING + 0.36))
        add_box(legno, (bx + 1.75, y + 0.05, Z_WING + 0.28), (bx + 2.10, y + 0.63,
                                                              Z_WING + 0.44))
        for xx in (bx + 0.10, bx + 1.72):
            add_box(legno, (xx, y + 0.08, Z_WING + 0.085), (xx + 0.06, y + 0.60,
                                                            Z_WING + 0.22))
    add_box(legno, (5.55, 2.35, Z_WING + 0.30), (5.95, 3.55, Z_WING + 0.36))
    for (x, y) in ((4.85, 1.55), (7.05, 1.55)):
        add_box(B["tessuto"], (x - 0.22, y - 0.22, Z_WING + 0.085), (x + 0.22, y + 0.22,
                                                                     Z_WING + 0.62))
        add_box(B["terra"], (x - 0.19, y - 0.19, Z_WING + 0.50), (x + 0.19, y + 0.19,
                                                                  Z_WING + 0.62))

# ---------------------------------------------------------------------------
# Interni: pavimenti, soffitti, tramezzi, arredi
# ---------------------------------------------------------------------------
def build_pavimenti(B):
    rov = B["rovere"]
    # piano terra (sotto i muri, così non si vedono fessure)
    pavimento(rov, AX0, AY0, BX1, AY1, Z_F0, asse="x")
    # piano primo (le tre regioni attorno ai vuoti)
    pavimento(rov, AX0, AY0, AX1, -1.24, Z_F1, asse="x")
    pavimento(rov, AX0, -1.24, VOID_X1, 1.00, Z_F1, asse="y")
    pavimento(rov, ST_X1, -1.24, AX1, AY1, Z_F1, asse="y")
    # pavimento della nicchia d'ingresso e del bagno di servizio
    add_box(B["ceramica"], (0.20, 2.60, Z_F0), (2.60, AY1, Z_F0 + 0.025))
    add_box(B["ceramica"], (1.72, -3.40, Z_F0), (2.80, -1.60, Z_F0 + 0.025))
    add_box(B["ceramica"], (1.72, -3.40, Z_F1), (2.80, -1.60, Z_F1 + 0.025))


def build_soffitti(B):
    """Controsoffitti, faretti incassati, plafoniera lineare e lampade a
    sospensione nel vuoto a doppia altezza."""
    luce, ferro, into = B["luce"], B["ferro"], B["into"]

    def faretto(x, y, z, verso="giu"):
        if verso == "giu":
            add_disc(ferro, (x, y, z - 0.004), 0.055, (0, 0, -1), sides=12)
            add_disc(luce, (x, y, z - 0.011), 0.045, (0, 0, -1), sides=12)
        else:
            add_disc(ferro, (x, y, z + 0.004), 0.055, (0, 0, 1), sides=12)
            add_disc(luce, (x, y, z + 0.011), 0.045, (0, 0, 1), sides=12)

    # piano terra: soffitto dell'ala e del solaio intermedio
    for i in range(6):
        faretto(-5.6 + i * 0.95, -2.0, Z_S0 - 0.02)
        faretto(-5.6 + i * 0.95, 0.2, Z_S0 - 0.02)
    for i in range(4):
        faretto(3.7 + i * 0.9, 1.2, Z_WING - T_WING - 0.02)
    for (x, y) in ((1.0, 0.5), (2.2, 0.5), (1.0, -1.0), (2.2, -1.0)):
        faretto(x, y, Z_S0 - 0.02)
    # piano primo
    for i in range(5):
        faretto(-5.6 + i * 0.95, -2.6, Z_TOP + 0.005, "su")
        faretto(-5.6 + i * 0.95, -0.3, Z_TOP + 0.005, "su")
    for i in range(3):
        faretto(0.9, -0.4 + i * 1.4, Z_TOP + 0.005, "su")
    for (x, y) in ((2.0, -2.4), (2.0, -1.9), (2.3, 3.0), (1.0, 3.0)):
        faretto(x, y, Z_TOP + 0.005, "su")
    # plafoniera lineare (profilo a scomparsa) sopra il tavolo da pranzo
    add_box(ferro, (3.95, 1.18, Z_WING - T_WING - 0.06), (5.95, 1.34, Z_WING - T_WING - 0.01))
    add_box(luce, (3.99, 1.21, Z_WING - T_WING - 0.015), (5.91, 1.31, Z_WING - T_WING - 0.008))
    # tre lampade a sospensione nel vuoto del soggiorno
    for x in (-5.4, -4.3, -3.2):
        add_cylinder(ferro, (x, 2.6, 6.31), (x, 2.6, 3.30), 0.008, sides=6)
        add_cylinder(ferro, (x, 2.6, 3.10), (x, 2.6, 3.30), 0.075, sides=14)
        add_disc(luce, (x, 2.6, 3.10), 0.07, (0, 0, -1), sides=14)
    # interruttori e prese a parete
    for (x, y, z, ax) in ((1.9, -1.58, 1.10, (0, -1, 0)), (-1.62, -1.7, 1.10, (1, 0, 0)),
                          (0.35, 2.55, 1.10, (0, 1, 0))):
        add_box(ferro, (x - 0.02, y - 0.02, z - 0.09), (x + 0.02, y + 0.02, z + 0.09))


def build_porta_interna(B, asse, c, a, b, z0, h=2.10, verso="+u"):
    """Porta interna: telaio, anta, maniglia. `asse` = "x" per una porta in un
    muro parallelo a Y, "y" per un muro parallelo a X; (a, b) è il vano."""
    leaf, acc = B["serr"], B["acciaio"]
    t = 0.045
    if asse == "x":      # porta su un muro che corre lungo Y
        add_box(leaf, (c - 0.05, a, z0), (c + 0.05, a + 0.04, z0 + h + 0.05))
        add_box(leaf, (c - 0.05, b - 0.04, z0), (c + 0.05, b, z0 + h + 0.05))
        add_box(leaf, (c - 0.05, a, z0 + h), (c + 0.05, b, z0 + h + 0.05))
        add_box(leaf, (c - 0.022, a + 0.03, z0), (c + 0.022, b - 0.03, z0 + h))
        add_cylinder(acc, (c - 0.11, b - 0.13, z0 + 1.00), (c - 0.11, b - 0.13, z0 + 1.16),
                     0.011, sides=8)
        add_box(acc, (c - 0.115, b - 0.15, z0 + 1.00), (c - 0.105, b - 0.11, z0 + 1.16))
    else:                # porta su un muro che corre lungo X
        add_box(leaf, (a, c - 0.05, z0), (a + 0.04, c + 0.05, z0 + h + 0.05))
        add_box(leaf, (b - 0.04, c - 0.05, z0), (b, c + 0.05, z0 + h + 0.05))
        add_box(leaf, (a, c - 0.05, z0 + h), (b, c + 0.05, z0 + h + 0.05))
        add_box(leaf, (a + 0.03, c - 0.022, z0), (b - 0.03, c + 0.022, z0 + h))
        add_cylinder(acc, (b - 0.13, c - 0.11, z0 + 1.00), (b - 0.13, c - 0.11, z0 + 1.16),
                     0.011, sides=8)
        add_box(acc, (b - 0.15, c - 0.115, z0 + 1.00), (b - 0.11, c - 0.105, z0 + 1.16))


def build_arredi_pt(B):
    """Cucina, soggiorno, pranzo, ingresso, wc e lavanderia."""
    rov, serr, acc, ferro = B["rovere"], B["serr"], B["acciaio"], B["ferro"]
    marmo, tess, noce, luce = B["marmo"], B["tessuto"], B["noce"], B["luce"]

    # ---------------- cucina (angolo nord-ovest) ---------------------------
    # basi sotto la finestra nord
    x0, x1 = -6.70, -2.30
    add_box(serr, (-5.44, -3.30, Z_F0 + 0.10), (x1, -2.68, Z_F0 + 0.86))
    add_box(marmo, (-5.47, -3.32, Z_F0 + 0.86), (x1 + 0.02, -2.62, Z_F0 + 0.90))
    k = 0
    xx = -5.44
    while xx < x1 - 0.05:
        add_box(serr, (xx, -2.72, Z_F0 + 0.14), (xx + 0.60, -2.68, Z_F0 + 0.82))
        add_cylinder(acc, (xx + 0.52, -2.66, Z_F0 + 0.60), (xx + 0.55, -2.66, Z_F0 + 0.78),
                     0.008, sides=6)
        xx += 0.62
    # lavello
    add_box(acc, (-4.35, -3.15, Z_F0 + 0.80), (-3.75, -2.85, Z_F0 + 0.905))
    add_box(ferro, (-4.28, -3.10, Z_F0 + 0.86), (-3.82, -2.90, Z_F0 + 0.90))
    add_cylinder(acc, (-4.05, -3.22, Z_F0 + 0.90), (-4.05, -3.22, Z_F0 + 1.20), 0.016,
                 sides=10)
    add_cylinder(acc, (-4.05, -3.22, Z_F0 + 1.20), (-4.05, -3.00, Z_F0 + 1.20), 0.016,
                 sides=10)
    # contenitori e tagliere sul piano
    for (cx, r) in ((-3.40, 0.05), (-3.20, 0.07), (-2.95, 0.045)):
        add_cylinder(ferro, (cx, -3.05, Z_F0 + 0.90), (cx, -3.05, Z_F0 + 0.90 + r * 4.0), r,
                     sides=12)
    add_box(noce, (-4.80, -3.10, Z_F0 + 0.90), (-4.50, -2.80, Z_F0 + 0.925))
    # colonne frigo e dispensa
    add_box(serr, (x0, -3.32, Z_F0 + 0.10), (x0 + 0.62, -2.68, Z_F0 + 2.20))
    add_box(ferro, (x0 + 0.30, -2.70, Z_F0 + 1.10), (x0 + 0.35, -2.68, Z_F0 + 1.70))
    add_box(serr, (x0 + 0.64, -3.32, Z_F0 + 0.10), (x0 + 1.24, -2.68, Z_F0 + 2.20))
    for zz in (0.5, 1.1, 1.7):
        add_box(ferro, (x0 + 0.95, -2.70, Z_F0 + zz), (x0 + 1.20, -2.68, Z_F0 + zz + 0.03))
    # colonna forno e caffettiera a fine cucina
    add_box(serr, (-2.35, -3.30, Z_F0 + 0.10), (-1.75, -2.68, Z_F0 + 2.20))
    add_box(ferro, (-2.30, -2.70, Z_F0 + 1.35), (-1.80, -2.68, Z_F0 + 1.80))
    add_box(B["vetro_scuro"], (-2.28, -2.69, Z_F0 + 1.40), (-1.82, -2.68, Z_F0 + 1.76))
    add_box(ferro, (-2.30, -2.70, Z_F0 + 0.85), (-1.80, -2.68, Z_F0 + 1.12))
    # isola con piano in marmo e piano cottura
    add_box(serr, (-4.75, -1.95, Z_F0 + 0.10), (-2.55, -1.12, Z_F0 + 0.88))
    add_box(marmo, (-4.82, -2.02, Z_F0 + 0.88), (-2.48, -1.05, Z_F0 + 0.93))
    for i in range(4):
        add_disc(ferro, (-3.95 + (i % 2) * 0.52, -1.62 + (i // 2) * 0.42, Z_F0 + 0.935),
                 0.085, (0, 0, 1), sides=14)
        add_disc(ferro, (-3.95 + (i % 2) * 0.52, -1.62 + (i // 2) * 0.42, Z_F0 + 0.94),
                 0.055, (0, 0, 1), sides=14)
    add_box(ferro, (-3.62, -2.00, Z_F0 + 0.80), (-3.50, -1.95, Z_F0 + 0.88))
    # sgabelli
    for i in range(3):
        sx = -4.35 + i * 0.72
        add_cylinder(acc, (sx, -0.86, Z_F0), (sx, -0.86, Z_F0 + 0.62), 0.03, sides=10)
        add_cylinder(rov, (sx, -0.86, Z_F0 + 0.62), (sx, -0.86, Z_F0 + 0.68), 0.17, sides=14)
        add_disc(ferro, (sx, -0.86, Z_F0), 0.18, (0, 0, -1), sides=14)
    # lampade a sospensione in rame sopra l'isola
    for i in range(3):
        sx = -4.35 + i * 0.72
        add_cylinder(ferro, (sx, -1.53, Z_S0), (sx, -1.53, Z_F0 + 1.85), 0.006, sides=6)
        add_sphere(B["rame"], (sx, -1.53, Z_F0 + 1.72), 0.11, segs=16, rings=8,
                   scale=(1.0, 1.0, 0.75))
        add_disc(luce, (sx, -1.53, Z_F0 + 1.64), 0.09, (0, 0, -1), sides=14)

    # ---------------- soggiorno a doppia altezza ---------------------------
    add_box(B["tappeto"], (-6.30, 1.05, Z_F0 + 0.028), (-2.60, 3.35, Z_F0 + 0.042))
    # divano a L
    def cuscino(x0, y0, x1, y1, z0, z1, col):
        B["tessuto2"].color = col
        add_box(B["tessuto2"], (x0, y0, z0), (x1, y1, z1))
    add_box(tess, (-5.95, 1.10, Z_F0 + 0.05), (-2.60, 2.30, Z_F0 + 0.34))       # seduta
    add_box(tess, (-5.95, 1.10, Z_F0 + 0.34), (-5.55, 2.30, Z_F0 + 0.72))       # bracciolo
    add_box(tess, (-5.95, 1.10, Z_F0 + 0.34), (-2.60, 1.32, Z_F0 + 0.78))       # schienale
    add_box(tess, (-3.35, 1.10, Z_F0 + 0.05), (-2.60, 3.20, Z_F0 + 0.34))       # chaise
    add_box(tess, (-3.35, 3.00, Z_F0 + 0.34), (-2.60, 3.20, Z_F0 + 0.72))
    for (a, b, c, d, col) in ((-5.60, 1.34, -4.85, 1.42, srgb(210, 202, 190)),
                              (-4.70, 1.34, -3.95, 1.42, srgb(120, 132, 120)),
                              (-3.80, 1.34, -3.05, 1.42, srgb(214, 208, 196)),
                              (-3.20, 2.00, -3.12, 2.70, srgb(96, 104, 118))):
        cuscino(a, b, c, d, Z_F0 + 0.34, Z_F0 + 0.72, col)
    # poltrona
    add_box(tess, (-2.30, 2.60, Z_F0 + 0.05), (-1.60, 3.30, Z_F0 + 0.42))
    add_box(tess, (-2.30, 2.60, Z_F0 + 0.42), (-2.05, 3.30, Z_F0 + 0.86))
    add_box(tess, (-2.30, 2.60, Z_F0 + 0.42), (-1.60, 2.85, Z_F0 + 0.72))
    # tavolino rotondo in marmo e tavolino basso
    add_cylinder(marmo, (-4.55, 2.60, Z_F0 + 0.36), (-4.55, 2.60, Z_F0 + 0.40), 0.50,
                 sides=24)
    add_cylinder(ferro, (-4.55, 2.60, Z_F0 + 0.42), (-4.55, 2.60, Z_F0 + 0.46), 0.44,
                 sides=24)
    add_cylinder(ferro, (-4.55, 2.60, Z_F0 + 0.02), (-4.55, 2.60, Z_F0 + 0.36), 0.05,
                 sides=12)
    add_cylinder(ferro, (-4.55, 2.60, Z_F0 + 0.02), (-4.55, 2.60, Z_F0 + 0.04), 0.26,
                 sides=16)
    add_box(noce, (-2.95, 3.02, Z_F0 + 0.30), (-2.02, 3.34, Z_F0 + 0.36))
    for (cx, cy) in ((-2.90, 3.06), (-2.07, 3.30)):
        add_cylinder(ferro, (cx, cy, Z_F0), (cx, cy, Z_F0 + 0.30), 0.016, sides=8)
    # stufa a legna con canna fumaria e catasta di legna
    add_box(ferro, (-6.55, 3.00, Z_F0 + 0.02), (-5.85, 3.70, Z_F0 + 0.10))
    add_box(ferro, (-6.50, 3.06, Z_F0 + 0.10), (-5.90, 3.64, Z_F0 + 0.92))
    add_box(B["vetro_scuro"], (-5.92, 3.14, Z_F0 + 0.28), (-5.90, 3.56, Z_F0 + 0.74))
    add_box(ferro, (-6.35, 3.30, Z_F0 + 0.92), (-6.05, 3.40, Z_F0 + 1.10))
    add_cylinder(ferro, (-6.20, 3.35, Z_F0 + 1.10), (-6.20, 2.00, Z_F0 + 1.55), 0.075,
                 sides=14)
    add_cylinder(ferro, (-6.20, 2.00, Z_F0 + 0.55), (-6.20, 2.00, Z_F0 + 1.55), 0.075,
                 sides=14)
    for i in range(9):
        y = 3.90 + (i % 3) * 0.10
        z = Z_F0 + 0.08 + (i // 3) * 0.115
        add_cylinder(B["tronco"], (-6.52 + 0.02, y, z), (-6.05, y, z), 0.05, sides=10)
    add_box(ferro, (-6.60, 3.84, Z_F0 + 0.02), (-6.02, 4.24, Z_F0 + 0.06))
    for (cx, cy) in ((-6.56, 3.88), (-6.06, 4.20)):
        add_cylinder(ferro, (cx, cy, Z_F0 + 0.06), (cx, cy, Z_F0 + 0.30), 0.012, sides=6)
    # libreria a tutta altezza sulla parete ovest
    add_box(noce, (-6.78, -0.20, Z_F0 + 0.02), (-6.42, 2.60, Z_F0 + 0.04))
    for zz in (0.35, 0.95, 1.55, 2.15, 2.45):
        add_box(noce, (-6.78, -0.20, Z_F0 + zz), (-6.42, 2.60, Z_F0 + zz + 0.03))
    for (yy, zz) in ((-0.15, 0.38), (-0.15, 0.98), (-0.15, 1.58), (-0.15, 2.18),
                     (2.55, 0.38), (2.55, 0.98), (2.55, 1.58), (2.55, 2.18)):
        add_box(noce, (-6.78, yy, Z_F0 + zz), (-6.42, yy + 0.04, Z_F0 + zz + 1.75))
    # libri
    for zz in (0.04, 0.38, 0.98, 1.58, 2.18):
        yy = 0.05
        while yy < 2.35:
            n = random.randint(3, 7)
            L = 0.02 * n + 0.01
            if yy + L > 2.45:
                break
            B["libri"].color = srgb(random.choice(((168, 60, 48), (36, 62, 96), (206, 190, 152),
                                                   (58, 84, 62), (140, 108, 60), (90, 60, 90),
                                                   (30, 30, 34), (188, 120, 70))))
            add_box(B["libri"], (-6.70, yy, Z_F0 + zz + 0.04), (-6.44, yy + L,
                                                                Z_F0 + zz + 0.233))
            yy += L + 0.012
    # pianta grande in vaso nell'angolo nord-ovest
    add_box(B["tessuto2"], (-2.95, -0.45, Z_F0 + 0.02), (-2.45, 0.05, Z_F0 + 0.52))
    for i in range(11):
        a = TAU * i / 11.0
        r = rr(0.1, 0.42)
        px, py = -2.70 + math.cos(a) * r, -0.20 + math.sin(a) * r
        add_cylinder(B["foglia"], (px, py, Z_F0 + 0.45), (px, py + rr(-0.1, 0.1),
                                                          Z_F0 + 1.35 + rr(0, 0.5)),
                     0.012, sides=6)
    # lume da terra e tavolino accanto alla poltrona
    add_cylinder(ferro, (-1.35, 3.45, Z_F0 + 0.02), (-1.35, 3.45, Z_F0 + 1.55), 0.014,
                 sides=8)
    add_cylinder(ferro, (-1.35, 3.45, Z_F0 + 1.55), (-1.35, 3.45, Z_F0 + 1.60), 0.16,
                 sides=16)
    add_disc(luce, (-1.35, 3.45, Z_F0 + 1.595), 0.15, (0, 0, -1), sides=14)
    add_cylinder(ferro, (-1.35, 3.45, Z_F0 + 0.02), (-1.35, 3.45, Z_F0 + 0.04), 0.18,
                 sides=16)

    # ---------------- pranzo nell'ala --------------------------------------
    add_box(B["tappeto"], (3.55, 0.35, Z_F0 + 0.028), (6.45, 2.35, Z_F0 + 0.040))
    add_box(noce, (3.80, 0.85, Z_F0 + 0.72), (6.20, 1.90, Z_F0 + 0.78))
    for (cx, cy) in ((3.95, 1.00), (6.05, 1.00), (3.95, 1.75), (6.05, 1.75)):
        add_box(noce, (cx - 0.025, cy - 0.025, Z_F0 + 0.02), (cx + 0.025, cy + 0.025,
                                                              Z_F0 + 0.72))
    for i in range(3):
        sx = 4.30 + i * 0.70
        for (yy, dy) in ((0.55, -1.0), (2.20, 1.0)):
            add_box(tess, (sx - 0.23, yy - 0.24, Z_F0 + 0.44), (sx + 0.23, yy + 0.24,
                                                                 Z_F0 + 0.48))
            add_box(tess, (sx - 0.23, yy - 0.24 + (0.0 if dy > 0 else 0.0), Z_F0 + 0.48),
                    (sx + 0.23, yy + 0.24, Z_F0 + 0.92))
            for (dx, dy2) in ((-0.19, -0.19), (0.19, -0.19), (-0.19, 0.19), (0.19, 0.19)):
                add_box(ferro, (sx + dx - 0.015, yy + dy2 - 0.015, Z_F0 + 0.02),
                        (sx + dx + 0.015, yy + dy2 + 0.015, Z_F0 + 0.44))
    add_box(noce, (4.40, 1.28, Z_F0 + 0.78), (5.60, 1.50, Z_F0 + 0.795))       # runner
    add_cylinder(B["ceramica"], (4.75, 1.38, Z_F0 + 0.795), (4.75, 1.38, Z_F0 + 1.10),
                 0.075, sides=14)
    add_sphere(B["foglia"], (4.75, 1.38, Z_F0 + 1.16), 0.10, segs=12, rings=6,
               scale=(1.0, 1.0, 0.7))
    add_box(B["ceramica"], (5.20, 1.30, Z_F0 + 0.795), (5.45, 1.48, Z_F0 + 0.83))
    for i in range(3):
        add_cylinder(B["rame"], (5.02 - i * 0.06, 1.62, Z_F0 + 1.28 - i * 0.14),
                     (5.02 - i * 0.06, 1.62, Z_F0 + 1.44 - i * 0.14), 0.055, sides=12)
    # credenza sulla parete nord e quadro
    add_box(noce, (3.30, -0.66, Z_F0 + 0.02), (5.90, -0.24, Z_F0 + 0.72))
    add_box(ferro, (3.60, -0.25, Z_F0 + 0.30), (4.20, -0.24, Z_F0 + 0.44))
    add_box(ferro, (5.00, -0.25, Z_F0 + 0.30), (5.60, -0.24, Z_F0 + 0.44))
    add_box(B["quadro"], (3.60, -0.68, Z_F0 + 1.30), (5.60, -0.66, Z_F0 + 2.60))
    add_box(B["quadro2"], (3.66, -0.665, Z_F0 + 1.36), (5.54, -0.6555, Z_F0 + 2.54))
    # pianta d'angolo
    add_box(B["tessuto2"], (6.35, -0.62, Z_F0 + 0.02), (6.85, -0.12, Z_F0 + 0.50))
    for i in range(9):
        a = TAU * i / 9.0
        r = rr(0.08, 0.34)
        px, py = 6.60 + math.cos(a) * r, -0.37 + math.sin(a) * r
        add_cylinder(B["foglia"], (px, py, Z_F0 + 0.45), (px, py, Z_F0 + 1.25 + rr(0, 0.45)),
                     0.011, sides=6)

    # ---------------- ingresso ---------------------------------------------
    add_box(B["tessuto2"], (1.00, -1.46, Z_F0 + 0.02), (2.40, -1.05, Z_F0 + 0.44))
    add_box(ferro, (1.42, -1.47, Z_F0 + 0.44), (2.00, -1.45, Z_F0 + 0.90))
    add_box(ferro, (1.44, -1.47, Z_F0 + 2.00), (2.02, -1.45, Z_F0 + 2.30))
    for i in range(4):
        add_cylinder(ferro, (1.50 + i * 0.15, -1.46, Z_F0 + 1.30), (1.50 + i * 0.15, -1.41,
                                                                    Z_F0 + 1.30), 0.012,
                     sides=6)
    add_box(noce, (-0.55, -1.46, Z_F0 + 0.02), (0.35, -1.03, Z_F0 + 0.80))
    add_cylinder(B["ceramica"], (-0.10, -1.24, Z_F0 + 0.80), (-0.10, -1.24, Z_F0 + 1.02),
                 0.06, sides=12)

    # ---------------- wc di servizio ---------------------------------------
    add_box(B["ceramica"], (2.02, -1.90, Z_F0 + 0.20), (2.48, -1.46, Z_F0 + 0.62))
    add_box(B["ceramica"], (2.02, -1.90, Z_F0 + 0.62), (2.32, -1.46, Z_F0 + 0.70))
    add_box(ferro, (2.40, -1.86, Z_F0 + 0.62), (2.46, -1.50, Z_F0 + 0.72))
    add_box(B["ceramica"], (1.90, -3.06, Z_F0 + 0.78), (2.50, -2.80, Z_F0 + 0.92))
    add_box(marmo, (1.86, -3.08, Z_F0 + 0.92), (2.54, -2.76, Z_F0 + 0.96))
    add_box(ferro, (1.98, -3.02, Z_F0 + 0.93), (2.42, -2.88, Z_F0 + 0.955))
    add_cylinder(acc, (2.20, -3.02, Z_F0 + 0.96), (2.20, -3.02, Z_F0 + 1.18), 0.012,
                 sides=8)
    add_box(B["marmo"], (1.86, -3.10, Z_F0 + 1.10), (2.54, -3.08, Z_F0 + 2.05))  # specchio
    add_box(ferro, (2.06, -3.09, Z_F0 + 1.55), (2.30, -3.07, Z_F0 + 1.72))        # luce

    # ---------------- lavanderia -------------------------------------------
    add_box(B["serr"], (-1.26, -3.05, Z_F0 + 0.02), (-0.86, -2.45, Z_F0 + 0.86))
    add_box(B["vetro_scuro"], (-0.94, -2.72, Z_F0 + 0.22), (-0.86, -2.98, Z_F0 + 0.62))
    add_box(B["serr"], (-1.26, -3.05, Z_F0 + 0.88), (-0.86, -2.45, Z_F0 + 1.74))
    add_box(B["vetro_scuro"], (-0.94, -2.72, Z_F0 + 1.06), (-0.86, -2.98, Z_F0 + 1.46))
    add_box(marmo, (-1.26, -3.05, Z_F0 + 1.76), (-0.84, -2.45, Z_F0 + 1.80))
    for i in range(5):
        add_cylinder(B["ceramica"], (-1.18 + i * 0.07, -2.85, Z_F0 + 1.80),
                     (-1.18 + i * 0.07, -2.85, Z_F0 + 2.04), 0.035, sides=10)
    add_box(serr, (-1.24, -2.40, Z_F0 + 1.90), (-0.88, -2.38, Z_F0 + 2.30))

def build_arredi_p1(B):
    """Camera, bagno padronale, cabina armadio e ballatoio."""
    rov, serr, acc, ferro = B["rovere"], B["serr"], B["acciaio"], B["ferro"]
    noce, marmo, tess = B["noce"], B["marmo"], B["tessuto"]

    # ---------------- camera (nord-ovest, sopra la cucina) -----------------
    # letto 1.80 x 2.05 con testiera imbottita
    bx0, bx1 = -4.77, -2.74
    by0, by1 = -2.55, -0.75
    add_box(noce, (bx0, by0, Z_F1 + 0.10), (bx1, by1, Z_F1 + 0.32))          # telaio
    add_box(tess, (bx0 + 0.05, by0 + 0.05, Z_F1 + 0.32), (bx1 - 0.05, by1 - 0.05,
                                                         Z_F1 + 0.50))      # materasso
    add_box(B["tessuto2"], (bx0 + 0.10, by0 + 0.10, Z_F1 + 0.50), (bx1 - 0.10, by1 - 0.10,
                                                                   Z_F1 + 0.56))  # copriletto
    add_box(tess, (bx0 + 0.16, by0 + 0.20, Z_F1 + 0.52), (bx0 + 0.75, by1 - 0.20,
                                                          Z_F1 + 0.60))     # cuscini
    add_box(tess, (bx0 + 0.85, by0 + 0.24, Z_F1 + 0.52), (bx0 + 1.40, by1 - 0.24,
                                                          Z_F1 + 0.585))
    add_box(B["tessuto2"], (-3.55, by0 - 0.02, Z_F1 + 0.44), (-2.80, by1 + 0.02,
                                                              Z_F1 + 0.52))  # plaid
    add_box(tess, (-2.80, by0 - 0.06, Z_F1 + 0.10), (-2.68, by1 + 0.06, Z_F1 + 1.10))  # testiera
    for i in range(3):
        yy = by0 + 0.20 + i * 0.58
        add_box(tess, (-2.79, yy, Z_F1 + 0.25), (-2.70, yy + 0.50, Z_F1 + 0.95))
    # comodini e lampade
    for yy in (by0 - 0.42, by1 + 0.08):
        add_box(noce, (-1.60, yy, Z_F1 + 0.02), (-1.14, yy + 0.42, Z_F1 + 0.42))
        add_cylinder(acc, (-1.36, yy + 0.21, Z_F1 + 0.42), (-1.36, yy + 0.21, Z_F1 + 0.58),
                     0.012, sides=8)
        add_cylinder(B["tessuto2"], (-1.36, yy + 0.21, Z_F1 + 0.44), (-1.36, yy + 0.21,
                                                                     Z_F1 + 0.60), 0.10,
                     sides=14)
        add_disc(B["luce"], (-1.36, yy + 0.21, Z_F1 + 0.445), 0.09, (0, 0, -1), sides=12)
    # panca in fondo al letto e tappeto
    add_box(noce, (-5.10, by0 + 0.25, Z_F1 + 0.02), (-4.86, by1 - 0.25, Z_F1 + 0.42))
    add_box(B["tessuto2"], (-5.12, by0 + 0.22, Z_F1 + 0.42), (-4.84, by1 - 0.22,
                                                             Z_F1 + 0.50))
    add_box(B["tappeto"], (-6.20, -2.70, Z_F1 + 0.028), (-4.30, -0.60, Z_F1 + 0.040))
    # armadio a tutta altezza sulla parete sud (con anta a specchio)
    add_box(noce, (-6.20, 0.40, Z_F1 + 0.02), (-3.90, 0.99, Z_F1 + 2.40))
    add_box(ferro, (-6.18, 0.36, Z_F1 + 1.05), (-4.30, 0.38, Z_F1 + 1.30))
    add_box(ferro, (-5.60, 0.36, Z_F1 + 1.05), (-3.92, 0.38, Z_F1 + 1.30))
    add_box(B["marmo"], (-4.22, 0.36, Z_F1 + 0.10), (-3.92, 0.38, Z_F1 + 2.30))
    # scrivania sotto la finestra ovest
    add_box(noce, (-6.48, -2.40, Z_F1 + 0.70), (-5.88, -1.00, Z_F1 + 0.74))
    for (cx, cy) in ((-6.44, -2.36), (-6.44, -1.04), (-5.92, -2.36), (-5.92, -1.04)):
        add_box(ferro, (cx - 0.02, cy - 0.02, Z_F1 + 0.02), (cx + 0.02, cy + 0.02,
                                                             Z_F1 + 0.70))
    add_box(ferro, (-6.30, -2.00, Z_F1 + 0.74), (-6.00, -1.45, Z_F1 + 0.90))   # portatile
    add_box(ferro, (-5.70, -2.30, Z_F1 + 0.74), (-5.30, -2.20, Z_F1 + 0.78))
    add_cylinder(ferro, (-5.48, -2.14, Z_F1 + 0.74), (-5.48, -2.14, Z_F1 + 1.22),
                 0.010, sides=6)
    add_cylinder(ferro, (-5.48, -2.14, Z_F1 + 1.22), (-5.48, -2.02, Z_F1 + 1.22),
                 0.010, sides=6)
    add_disc(B["luce"], (-5.48, -2.02, Z_F1 + 1.21), 0.05, (0, 0, -1), sides=12)
    # sedia da scrivania
    add_box(tess, (-5.60, -1.70, Z_F1 + 0.44), (-5.10, -1.20, Z_F1 + 0.50))
    add_box(tess, (-5.60, -1.70, Z_F1 + 0.50), (-5.50, -1.20, Z_F1 + 0.96))
    for (cx, cy) in ((-5.56, -1.66), (-5.14, -1.66), (-5.56, -1.24), (-5.14, -1.24)):
        add_cylinder(ferro, (cx, cy, Z_F1 + 0.02), (cx, cy, Z_F1 + 0.44), 0.012, sides=6)
    # quadro sopra la testiera e pianta all'angolo
    add_box(B["quadro"], (-1.14, -2.45, Z_F1 + 1.05), (-1.12, -1.35, Z_F1 + 1.85))
    add_box(B["quadro2"], (-1.135, -2.39, Z_F1 + 1.11), (-1.125, -1.41, Z_F1 + 1.79))
    add_box(B["tessuto2"], (-6.42, 0.05, Z_F1 + 0.02), (-5.94, 0.53, Z_F1 + 0.44))
    for i in range(8):
        a = TAU * i / 8.0
        add_cylinder(B["foglia"], (-6.18 + math.cos(a) * 0.18, 0.29 + math.sin(a) * 0.18,
                                   Z_F1 + 0.40),
                     (-6.18 + math.cos(a) * 0.28, 0.29 + math.sin(a) * 0.28,
                      Z_F1 + 1.25 + rr(0.0, 0.35)), 0.011, sides=6)

    # ---------------- bagno padronale --------------------------------------
    add_box(B["ceramica"], (-2.48, -3.10, Z_F1 + 0.02), (-1.12, -0.92, Z_F1 + 0.03))
    # rivestimento in gres sulle pareti
    for (x0, y0, x1, y1) in ((-2.49, -3.10, -2.47, -0.92), (-1.14, -3.10, -1.12, -0.92),
                             (-2.49, -3.11, -1.12, -3.09)):
        add_box(B["ceramica"], (x0, y0, Z_F1 + 0.03), (x1, y1, Z_F1 + 2.30))
    # doccia filo pavimento con piatto e soffione
    add_box(B["ceramica"], (-2.45, -3.05, Z_F1 + 0.03), (-1.15, -2.10, Z_F1 + 0.05))
    add_box(B["vetro"], (-1.20, -2.10, Z_F1 + 0.03), (-1.18, -2.08, Z_F1 + 2.10))
    add_box(B["vetro"], (-2.45, -2.12, Z_F1 + 0.03), (-1.18, -2.10, Z_F1 + 2.10))
    add_cylinder(acc, (-1.80, -2.40, Z_F1 + 2.30), (-1.80, -2.40, Z_F1 + 2.24), 0.10,
                 sides=16)
    add_cylinder(acc, (-1.80, -3.05, Z_F1 + 2.30), (-1.80, -2.40, Z_F1 + 2.30), 0.016,
                 sides=10)
    # wc sospeso e lavabo con specchio
    add_box(B["ceramica"], (-2.20, -1.02, Z_F1 + 0.40), (-1.68, -0.94, Z_F1 + 0.78))
    add_box(B["ceramica"], (-2.20, -1.12, Z_F1 + 0.40), (-1.68, -1.02, Z_F1 + 0.80))
    add_box(ferro, (-2.30, -1.00, Z_F1 + 0.62), (-1.58, -0.93, Z_F1 + 0.70))
    add_box(marmo, (-2.48, -2.00, Z_F1 + 0.78), (-1.94, -1.25, Z_F1 + 0.84))
    add_box(B["marmo"], (-2.44, -1.96, Z_F1 + 0.74), (-1.98, -1.29, Z_F1 + 0.79))
    add_cylinder(acc, (-2.20, -1.94, Z_F1 + 0.84), (-2.20, -1.94, Z_F1 + 1.06), 0.012,
                 sides=8)
    add_disc(B["marmo"], (-2.42, -1.62, Z_F1 + 1.55), 0.24, (1, 0, 0), sides=20)
    add_box(ferro, (-2.46, -1.80, Z_F1 + 1.90), (-2.44, -1.44, Z_F1 + 2.10))
    add_cylinder(acc, (-1.30, -1.40, Z_F1 + 1.05), (-1.30, -1.40, Z_F1 + 1.65), 0.014,
                 sides=8)
    add_cylinder(acc, (-1.24, -1.40, Z_F1 + 1.05), (-1.30, -1.40, Z_F1 + 1.05), 0.014,
                 sides=8)
    add_box(B["tessuto2"], (-2.00, -1.60, Z_F1 + 0.03), (-1.50, -1.20, Z_F1 + 0.05))
    add_box(B["tessuto2"], (-1.30, -1.50, Z_F1 + 0.03), (-1.16, -1.10, Z_F1 + 0.05))

    # ---------------- cabina armadio ---------------------------------------
    add_box(noce, (1.76, -3.05, Z_F1 + 0.02), (2.44, -2.80, Z_F1 + 2.30))
    add_box(noce, (1.76, -2.05, Z_F1 + 0.02), (2.44, -1.80, Z_F1 + 2.30))
    for zz in (0.40, 0.95, 1.50, 2.05):
        add_box(noce, (1.80, -3.00, Z_F1 + zz), (2.42, -1.85, Z_F1 + zz + 0.03))
    for i in range(6):
        zz = 0.45 + (i % 3) * 0.55
        yy = -2.90 + (i // 3) * 0.9
        B["libri"].color = srgb(random.choice(((196, 190, 180), (120, 96, 70), (60, 70, 84),
                                               (150, 60, 52))))
        add_box(B["libri"], (1.95, yy, Z_F1 + zz), (2.30, yy + 0.34, Z_F1 + zz + 0.28))
    add_box(B["tessuto2"], (2.00, -2.72, Z_F1 + 0.60), (2.30, -2.74, Z_F1 + 1.20))

    # ---------------- ballatoio --------------------------------------------
    # parapetto in vetro lungo il vano scala
    ringhiera_vetro(B["vetro"], acc, (ST_X1, -1.24), (ST_X1, AY1 - 0.02), Z_F1, 0.98)
    # libreria a tutta altezza contro la parete della cabina armadio
    add_box(noce, (1.16, -3.20, Z_F1 + 0.02), (1.48, -1.80, Z_F1 + 2.35))
    for zz in (0.34, 0.84, 1.34, 1.84):
        add_box(noce, (1.16, -3.20, Z_F1 + zz), (1.48, -1.80, Z_F1 + zz + 0.03))
    for zz in (0.05, 0.37, 0.87, 1.37, 1.87):
        yy = -3.14
        while yy < -1.95:
            n = random.randint(3, 6)
            L = 0.019 * n + 0.01
            if yy + L > -1.90:
                break
            B["libri"].color = srgb(random.choice(((176, 148, 96), (52, 74, 96), (150, 58, 50),
                                                   (206, 198, 178), (44, 44, 48),
                                                   (96, 120, 74))))
            add_box(B["libri"], (1.22, yy, Z_F1 + zz + 0.04), (1.44, yy + L,
                                                              Z_F1 + zz + 0.225))
            yy += L + 0.012
    # angolo lettura vicino alla finestra a nastro
    add_box(tess, (0.95, 2.70, Z_F1 + 0.05), (1.60, 3.30, Z_F1 + 0.40))
    add_box(tess, (0.95, 2.70, Z_F1 + 0.40), (1.18, 3.30, Z_F1 + 0.82))
    add_box(tess, (0.95, 3.06, Z_F1 + 0.40), (1.60, 3.30, Z_F1 + 0.74))
    add_box(noce, (1.75, 2.95, Z_F1 + 0.02), (2.25, 3.35, Z_F1 + 0.42))
    add_cylinder(B["ceramica"], (2.00, 3.15, Z_F1 + 0.42), (2.00, 3.15, Z_F1 + 0.62), 0.05,
                 sides=12)
    add_box(B["tappeto"], (0.80, 2.45, Z_F1 + 0.028), (1.75, 3.40, Z_F1 + 0.040))
    # scultura e pianta sul ballatoio
    add_box(B["tessuto2"], (0.35, -1.55, Z_F1 + 0.02), (0.75, -1.15, Z_F1 + 0.46))
    for i in range(7):
        a = TAU * i / 7.0
        add_cylinder(B["foglia"], (0.55 + math.cos(a) * 0.14, -1.35 + math.sin(a) * 0.14,
                                   Z_F1 + 0.42),
                     (0.55 + math.cos(a) * 0.22, -1.35 + math.sin(a) * 0.22,
                      Z_F1 + 1.15 + rr(0.0, 0.3)), 0.010, sides=6)
    add_box(B["quadro"], (1.63, -1.30, Z_F1 + 1.15), (1.65, -0.20, Z_F1 + 2.05))
    add_box(B["quadro2"], (1.625, -1.24, Z_F1 + 1.21), (1.635, -0.26, Z_F1 + 1.99))

# ---------------------------------------------------------------------------
# Giardino: terreno, deck, piscina, vialetto, ghiaia, siepi, erba, alberi
# ---------------------------------------------------------------------------
TERR_R = 170.0
PISC_X0, PISC_X1 = -5.30, -0.50          # vasca della piscina
PISC_Y0, PISC_Y1 = 6.80, 8.40
PISC_APRON = 0.80                        # larghezza dell'orlo in cemento


def terrain_z(x, y):
    """Quota del terreno: spianata attorno alla casa, poi prato ondulato e
    colline che chiudono l'orizzonte."""
    d = math.hypot(x / 1.15, y / 1.15)
    flat = clamp((d - 10.5) / 9.0, 0.0, 1.0)
    n1 = noise.noise(Vector((x * 0.021, y * 0.021, 3.1))) * 1.15
    n2 = noise.noise(Vector((x * 0.072, y * 0.072, 7.7))) * 0.26
    n3 = noise.noise(Vector((x * 0.3, y * 0.3, 1.3))) * 0.05
    dd = math.hypot(x, y)
    far = clamp((dd - 34.0) / 62.0, 0.0, 1.0)
    far = far * far * (3.0 - 2.0 * far)
    hill = ((noise.noise(Vector((x * 0.0105, y * 0.0105, 11.3))) * 0.5 + 0.55) * 17.0
            + noise.noise(Vector((x * 0.035, y * 0.035, 4.2))) * 2.4)
    return 0.14 + (n1 + n2 + n3) * flat + far * max(0.0, hill)


def build_terreno(B):
    """Prato a maglia polare: fitto vicino alla casa, rado all'orizzonte."""
    terra = B["prato"]
    radii = [0.0]
    r = 0.0
    while r < 20.0:
        r += 0.60
        radii.append(r)
    step = 0.95
    while r < TERR_R:
        step *= 1.13
        r += step
        radii.append(min(r, TERR_R))
    segs = 176
    rings = []
    for r in radii:
        row = []
        for j in range(segs):
            a = TAU * j / segs
            x, y = math.cos(a) * r, math.sin(a) * r
            row.append(Vector((x, y, terrain_z(x, y) if r > 0.01 else 0.14)))
        rings.append(terra.add(row))
    xa, xb = PISC_X0 - PISC_APRON, PISC_X1 + PISC_APRON
    ya, yb = PISC_Y0 - PISC_APRON, PISC_Y1 + PISC_APRON
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for j in range(segs):
            k = (j + 1) % segs
            cx = (terra.V[a + j][0] + terra.V[a + k][0] + terra.V[b + k][0]
                  + terra.V[b + j][0]) * 0.25
            cy = (terra.V[a + j][1] + terra.V[a + k][1] + terra.V[b + k][1]
                  + terra.V[b + j][1]) * 0.25
            if xa < cx < xb and ya < cy < yb:
                continue                     # sede della piscina
            terra.face((a + j, a + k, b + k, b + j), True)


def build_deck_esterno(B):
    legno, acc = B["legno"], B["acciaio"]
    # deck davanti al soggiorno
    deck(legno, -7.55, 3.86, 0.70, 6.70, 0.28, asse="x")
    # deck davanti al padiglione del pranzo
    deck(legno, 2.90, 3.86, 7.45, 5.70, 0.28, asse="x")
    # fascioni di bordo
    add_box(acc, (-7.55, 3.86, 0.22), (-7.51, 6.70, 0.315))
    add_box(acc, (-7.55, 6.66, 0.22), (0.70, 6.70, 0.315))
    add_box(acc, (-7.55, 3.86, 0.22), (0.70, 3.90, 0.315))
    add_box(acc, (2.90, 5.66, 0.22), (7.45, 5.70, 0.315))
    add_box(acc, (7.41, 3.86, 0.22), (7.45, 5.70, 0.315))
    add_box(acc, (2.90, 3.86, 0.22), (7.45, 3.90, 0.315))


def build_piscina(B):
    """Piscina a sfioro: orlo in cemento gettato, cordolo, vasca con pareti e
    fondo, gradino sommerso, acqua e scaletta in acciaio."""
    cls, acqua, sm = B["cls"], B["acqua"], B["smalto"]
    x0, x1 = PISC_X0, PISC_X1
    y0, y1 = PISC_Y0, PISC_Y1
    ap = PISC_APRON
    # orlo in cemento attorno alla vasca (copre il bordo del terreno)
    for (a, b, c, d) in ((x0 - ap, y0 - ap, x1 + ap, y0 - 0.02),
                         (x0 - ap, y1 + 0.02, x1 + ap, y1 + ap),
                         (x0 - ap, y0 - 0.02, x0 - 0.02, y1 + 0.02),
                         (x1 + 0.02, y0 - 0.02, x1 + ap, y1 + 0.02)):
        add_box(sm, (a, b, 0.02), (c, d, 0.20))
    # cordolo a filo (leggermente rilevato)
    for (a, b, c, d) in ((x0 - 0.18, y0 - 0.18, x1 + 0.18, y0),
                         (x0 - 0.18, y1, x1 + 0.18, y1 + 0.18),
                         (x0 - 0.18, y0, x0, y1),
                         (x1, y0, x1 + 0.18, y1)):
        add_box(cls, (a, b, 0.05), (c, d, 0.38))
    # vasca: pareti e fondo
    add_box(B["piscina"], (x0, y0, -0.55), (x1, y1, -0.42))
    for (a, b, c, d) in ((x0, y0, x0 + 0.03, y1), (x1 - 0.03, y0, x1, y1),
                         (x0, y0, x1, y0 + 0.03), (x0, y1 - 0.03, x1, y1)):
        add_box(B["piscina"], (a, b, -0.42), (c, d, 0.30))
    # gradino sommerso
    add_box(B["piscina"], (x0 + 0.10, y1 - 0.60, -0.42), (x1 - 0.10, y1 - 0.06, -0.16))
    add_box(B["piscina"], (x0 + 0.10, y1 - 0.60, -0.16), (x1 - 0.10, y1 - 0.06, -0.03))
    # acqua (pelo libero leggermente sotto il cordolo)
    add_box(acqua, (x0 + 0.03, y0 + 0.03, 0.30), (x1 - 0.03, y1 - 0.03, 0.325))
    # scaletta in acciaio
    acc = B["acciaio"]
    for dx in (-0.18, 0.18):
        add_tube(acc, [Vector((-1.10 + dx, y1 - 0.05, 0.42)),
                       Vector((-1.10 + dx, y1 - 0.05, 0.80)),
                       Vector((-1.10 + dx, y1 - 0.45, 0.86)),
                       Vector((-1.10 + dx, y1 - 0.75, 0.12))], 0.020, sides=10)
    for i in range(3):
        add_cylinder(acc, (-1.28, y1 - 0.75 + i * 0.22, 0.12 + i * 0.09),
                     (-0.92, y1 - 0.75 + i * 0.22, 0.12 + i * 0.09), 0.016, sides=8)


def build_vialetto(B):
    """Vialetto in lastre di calcestruzzo con fughe d'erba, piazzale
    d'ingresso, gradini e luci a paletto."""
    sm = B["smalto"]
    acc, luce = B["acciaio"], B["luce"]
    # lastre del vialetto
    y = 15.5
    while y > 5.60:
        n = 2
        for i in range(n):
            cx = 1.15 + (i + 0.5) * (1.40 / n)
            add_box(sm, (cx - 0.62, y - 0.58, terrain_z(cx, y) + 0.02),
                    (cx + 0.62, y - 0.04, terrain_z(cx, y) + 0.14))
        y -= 0.66
    # piazzale davanti all'ingresso (quota del pavimento interno)
    add_box(sm, (0.10, 3.86, 0.02), (2.72, 5.60, Z_F0))
    add_box(B["cls"], (0.10, 3.86, -0.10), (2.72, 5.60, 0.04))
    # gradino fra piazzale e vialetto
    add_box(sm, (0.24, 5.60, 0.02), (2.58, 5.92, 0.20))
    # luci a paletto lungo il vialetto
    for y in (6.6, 8.4, 10.2, 12.0):
        z = terrain_z(2.85, y)
        add_cylinder(B["ferro"], (2.85, y, z - 0.05), (2.85, y, z + 0.62), 0.030, sides=12)
        add_cylinder(luce, (2.85, y, z + 0.60), (2.85, y, z + 0.66), 0.036, sides=12)


def build_ghiaione(B):
    """Aiuole di ghiaia con massi, graminacee, lavande e una panca in
    calcestruzzo."""
    grav, cls, pietra = B["grav"], B["cls"], B["pietra"]
    aiuole = [(-12.4, -2.6, -7.62, 6.4),
              (-7.62, -4.9, 3.2, -3.46),
              (-7.55, 6.70, 0.70, 8.90),
              (2.90, 5.70, 8.60, 9.60)]
    for (x0, y0, x1, y1) in aiuole:
        add_box(grav, (x0, y0, 0.10), (x1, y1, 0.20))
    # massi
    for (x, y, r) in ((-9.30, 1.10, 0.42), (-10.60, 2.60, 0.55), (-8.60, -1.40, 0.34),
                      (-11.30, -0.60, 0.46), (-9.90, 4.40, 0.38), (-8.30, 5.30, 0.30),
                      (-6.90, -4.00, 0.36), (-3.20, -4.20, 0.30), (6.20, 6.40, 0.34),
                      (7.80, 7.40, 0.42)):
        add_sphere(pietra, (x, y, 0.16 + r * 0.25), r, segs=18, rings=10, amp=0.30,
                   nscale=1.4, scale=(1.0, 0.85, 0.62), seed_off=x)
    # panca in calcestruzzo
    add_box(cls, (-9.60, -0.30, 0.20), (-8.10, 0.10, 0.62))
    for dx in (0.10, 1.30):
        add_box(cls, (-9.60 + dx, -0.35, -0.10), (-9.50 + dx, 0.15, 0.20))


def build_erba(B, count=11000):
    """Ciuffi d'erba: 4-7 lamine piegate a raggiera, più fitti vicino a casa."""
    erba = B["erba"]
    placed, guard = 0, 0
    while placed < count and guard < count * 8:
        guard += 1
        a = rr(0, TAU)
        r = (random.random() ** 0.60) * 22.0
        x, y = math.cos(a) * r, math.sin(a) * r
        if (AX0 - 0.7) < x < (BX1 + 0.7) and (AY0 - 0.7) < y < (AY1 + 0.7):
            continue
        if (-7.55) < x < 0.70 and 3.80 < y < 6.70:
            continue
        if 2.90 < x < 7.45 and 3.80 < y < 5.70:
            continue
        if (-5.50) < x < -0.30 and 6.60 < y < 8.60:
            continue
        if 0.10 < x < 2.75 and 3.50 < y < 16.0:
            continue
        if (-12.4) < x < -7.62 and (-2.6) < y < 6.4:
            continue
        z = terrain_z(x, y)
        segs = 3 if r < 7.0 else 2
        secca = random.random() < 0.10
        hbase = rr(0.10, 0.28)
        for _ in range(random.randint(4, 7)):
            if secca and random.random() < 0.6:
                erba.color = (rr(0.95, 1.0), rr(0.80, 0.88), rr(0.40, 0.52))
            else:
                k = rr(0.60, 0.95)
                erba.color = (k * rr(0.85, 1.0), k, k * rr(0.72, 1.0))
            ang = rr(0, TAU)
            d = Vector((math.cos(ang), math.sin(ang), 0.0))
            side = Vector((-d.y, d.x, 0.0))
            p = Vector((x, y, z)) + d * rr(0.0, 0.03)
            h = hbase * rr(0.7, 1.3)
            wdt = rr(0.010, 0.017)
            bend = rr(0.2, 0.85)
            bi = erba.add([p - side * (wdt / 2.0), p + side * (wdt / 2.0)])
            for s_ in range(1, segs + 1):
                t = s_ / float(segs)
                off = d * (h * bend * t * t)
                w2 = wdt * (1.0 - 0.85 * t)
                c = p + Vector((off.x, off.y, h * t - h * 0.13 * t * t))
                ni = erba.add([c - side * (w2 / 2.0), c + side * (w2 / 2.0)])
                erba.face((bi, bi + 1, ni + 1, ni), True)
                bi = ni
        placed += 1


def add_foglia(buf, p, nrm, up, size, aspect=0.45):
    """Foglia a losanga piegata lungo la nervatura (2 triangoli)."""
    nrm = _v3(nrm).normalized()
    up = _v3(up)
    t = up - nrm * up.dot(nrm)
    if t.length < 1e-4:
        t = nrm.orthogonal()
    t.normalize()
    a = rr(-0.9, 0.9)
    s_ = nrm.cross(t)
    t = t * math.cos(a) + s_ * math.sin(a)
    s_ = nrm.cross(t)
    hw = size * aspect * 0.5
    curl = nrm * (size * 0.13)
    base = p - t * (size * 0.5)
    tip = p + t * (size * 0.5) - curl * 0.6
    l = p - s_ * hw + t * (size * 0.06) - curl
    r = p + s_ * hw + t * (size * 0.06) - curl
    i = buf.add((base, r, tip, l))
    buf.face((i, i + 1, i + 2))
    buf.face((i, i + 2, i + 3))


def build_graminacee(B, punti):
    """Graminacee ornamentali: ciuffi alti con foglie arcuate e spighe."""
    fo, erba = B["foglia"], B["erba"]
    for (x, y, scala) in punti:
        z = terrain_z(x, y) + 0.06
        n = int(70 * scala)
        for i in range(n):
            a = rr(0, TAU)
            d = Vector((math.cos(a), math.sin(a), 0.0))
            side = Vector((-d.y, d.x, 0.0))
            h = rr(0.45, 1.15) * scala
            wdt = rr(0.008, 0.016)
            fold = rr(0.4, 1.5)
            p = Vector((x, y, z)) + d * rr(0.0, 0.34 * scala)
            k = rr(0.7, 1.05)
            col = (k * rr(0.85, 1.0), k * rr(0.95, 1.05), k * rr(0.5, 0.75))
            erba.color = col
            bi = erba.add([p - side * (wdt / 2.0), p + side * (wdt / 2.0)])
            segs = 4
            for s_ in range(1, segs + 1):
                t = s_ / float(segs)
                off = d * (h * fold * t * t)
                w2 = wdt * (1.0 - 0.9 * t)
                c = p + Vector((off.x, off.y, h * (t - 0.35 * t * t)))
                ni = erba.add([c - side * (w2 / 2.0), c + side * (w2 / 2.0)])
                erba.face((bi, bi + 1, ni + 1, ni), True)
                bi = ni
        # spighe
        for i in range(int(14 * scala)):
            a = rr(0, TAU)
            d = Vector((math.cos(a), math.sin(a), 0.0))
            p = Vector((x, y, z)) + d * rr(0.0, 0.26 * scala)
            h = rr(0.75, 1.25) * scala
            fo.color = (rr(0.85, 1.0), rr(0.85, 1.0), rr(0.55, 0.8))
            add_foglia(fo, p + Vector((0, 0, h)), Vector((0, 0, 1)),
                       Vector((rr(-1, 1), rr(-1, 1), 0.4)).normalized(), 0.10, 0.28)


def build_lavanda(B, punti):
    """Cespugli di lavanda: fogliame grigio-verde e spighe fiorite."""
    fo, fi = B["foglia"], B["lavanda"]
    for (x, y, r) in punti:
        z = terrain_z(x, y) + 0.04
        for i in range(int(120 * r * 3)):
            a = rr(0, TAU)
            rr_ = (random.random() ** 0.5) * r
            p = Vector((x + math.cos(a) * rr_, y + math.sin(a) * rr_, z))
            h = rr(0.18, 0.42)
            fo.color = (rr(0.72, 0.95), rr(0.78, 1.0), rr(0.72, 0.95))
            side = Vector((rr(-1, 1), rr(-1, 1), 0)).normalized()
            bi = fo.add([p - side * 0.007, p + side * 0.007])
            ni = fo.add([p - side * 0.004 + Vector((rr(-0.06, 0.06), rr(-0.06, 0.06), h)),
                         p + side * 0.004 + Vector((rr(-0.06, 0.06), rr(-0.06, 0.06), h))])
            fo.face((bi, bi + 1, ni + 1, ni), True)
        for i in range(int(30 * r * 3)):
            a = rr(0, TAU)
            rr_ = (random.random() ** 0.5) * r * 0.9
            p = Vector((x + math.cos(a) * rr_, y + math.sin(a) * rr_, z + 0.22))
            fi.color = (rr(0.75, 1.0), rr(0.6, 0.85), rr(0.85, 1.1))
            add_foglia(fi, p, Vector((0, 0, 1)), Vector((rr(-0.3, 0.3), rr(-0.3, 0.3), 1.0)),
                       0.075, 0.22)


def build_siepe(B, p0, p1, h=0.95, sp=0.75, dens=1500.0):
    """Siepe potata: anima scura e foglie disposte sulla superficie."""
    fo = B["siepe"]
    p0, p1 = _v3(p0), _v3(p1)
    d = p1 - p0
    L = d.length
    u = d / L
    n = Vector((-u.y, u.x, 0.0))
    add_box(B["siepe2"], (min(p0.x, p1.x) - sp / 2, min(p0.y, p1.y) - sp / 2, 0.04),
            (max(p0.x, p1.x) + sp / 2, max(p0.y, p1.y) + sp / 2, h + 0.05))
    guard = 0
    target = int(L * dens)
    placed = 0
    while placed < target and guard < target * 6:
        guard += 1
        t = rr(0.0, 1.0) * L
        c = p0 + u * t
        # posizione sulla superficie del volume
        face = random.randint(0, 4)
        if face == 0:
            p = c + n * (sp / 2.0) + Vector((0, 0, rr(0.06, h - 0.05)))
            nrm = n
        elif face == 1:
            p = c - n * (sp / 2.0) + Vector((0, 0, rr(0.06, h - 0.05)))
            nrm = -n
        elif face == 2:
            p = c + Vector((0, 0, h - rr(0.0, 0.06))) + n * rr(-sp / 2, sp / 2)
            nrm = Vector((0, 0, 1))
        elif face == 3:
            p = c + u * rr(-0.04, 0.04) + n * rr(-sp / 2, sp / 2) + Vector((0, 0, rr(0.2, h)))
            nrm = u if random.random() < 0.5 else -u
        else:
            p = c + u * rr(-0.04, 0.04) + n * (sp / 2.0)
            nrm = Vector((rr(-1, 1), rr(-1, 1), 0.25)).normalized()
        k = rr(0.5, 0.9)
        fo.color = (k * rr(0.7, 1.0), k, k * rr(0.5, 0.85))
        add_foglia(fo, p, nrm, Vector((0, 0, 1)), rr(0.10, 0.17), 0.55)
        placed += 1


def build_albero(B, x, y, h=6.5, fusti=3, foglie=1600, r_chioma=2.4, taglio=0.0,
                 betulla=False, seed=0):
    """Albero a più fusti (betulla): fusti snelli e inclinati, rametti e
    foglie posate una a una. Se `taglio` > 0 il fusto parte da quella quota."""
    corteccia = B["corteccia"] if betulla else B["tronco"]
    fo = B["foglia"]
    random.seed(SEED + seed)
    z0 = terrain_z(x, y) + taglio - 0.05
    base = Vector((x, y, z0))
    punte = []
    for i in range(fusti):
        a = TAU * i / fusti + rr(-0.3, 0.3)
        d0 = Vector((math.cos(a), math.sin(a), 0.0)) * rr(0.05, 0.22)
        hh = h * rr(0.72, 1.05)
        pts = []
        for k in range(6):
            t = k / 5.0
            bend = Vector((math.sin(t * 2.4) * 0.35, math.cos(t * 1.7) * 0.28, 0.0))
            pts.append(base + d0 * (t * 1.6) + bend * (t * t * hh * 0.12)
                       + Vector((0, 0, hh * t)))
        r0 = 0.11 if betulla else 0.16
        for k in range(len(pts) - 1):
            t = k / float(len(pts) - 1)
            add_cylinder(corteccia, pts[k], pts[k + 1], r0 * (1.0 - 0.75 * t), sides=9)
        punte.append((pts[-1], pts[-2]))
        # rametti secondari
        for k in range(2, 5):
            t = k / 5.0
            orig = pts[k]
            for j in range(2):
                aa = rr(0, TAU)
                dd = (Vector((math.cos(aa), math.sin(aa), rr(0.5, 1.4)))).normalized()
                L = hh * rr(0.18, 0.34)
                q = orig + dd * L
                add_cylinder(corteccia, orig, q, r0 * 0.30 * (1.0 - 0.4 * t), sides=6)
                punte.append((q, orig))
                for _ in range(2):
                    aa2 = rr(0, TAU)
                    dd2 = (Vector((math.cos(aa2), math.sin(aa2), rr(0.3, 1.1)))).normalized()
                    q2 = q + dd2 * L * rr(0.4, 0.7)
                    add_cylinder(corteccia, q, q2, r0 * 0.16, sides=5)
                    punte.append((q2, q))
    # foglie sui rametti
    n_foglie = 0
    while n_foglie < foglie:
        p, q = random.choice(punte)
        t = random.random() ** 0.7
        pos = q + (p - q) * t
        # foglie distribuite attorno alla punta del rametto
        s = (random.random() ** 0.6)
        pos = pos + Vector((rr(-1, 1), rr(-1, 1), rr(-1, 1))) * (0.06 + s * 0.34)
        nrm = Vector((rr(-1, 1), rr(-1, 1), rr(-0.4, 0.6))).normalized()
        k = rr(0.6, 1.0)
        fo.color = (k * rr(0.85, 1.15), k * rr(0.95, 1.05), k * rr(0.45, 0.7))
        add_foglia(fo, pos, nrm, Vector((rr(-0.4, 0.4), rr(-0.4, 0.4), 1.0)),
                   rr(0.055, 0.095) if betulla else rr(0.075, 0.125), 0.62)
        n_foglie += 1
    random.seed(SEED)


def build_cipresso(B, x, y, h=7.0, r=0.75):
    """Cipresso: cono irregolare di foglie scure."""
    fo = B["cipresso"]
    z0 = terrain_z(x, y)
    prof = []
    n = 9
    for i in range(n + 1):
        t = i / float(n)
        rr_ = r * math.sin(PI * (t ** 0.72)) * (1.0 - 0.15 * t) + 0.05
        prof.append((rr_, z0 + h * t))
    for i in range(n):
        r0, zz0 = prof[i]
        r1, zz1 = prof[i + 1]
        anelli = 7
        for j in range(anelli):
            a = TAU * j / anelli + i * 0.4
            p = Vector((x + math.cos(a) * r0, y + math.sin(a) * r0, zz0))
            k = rr(0.55, 0.95)
            fo.color = (k * 0.75, k * 0.9, k * 0.7)
            add_foglia(fo, p, Vector((math.cos(a), math.sin(a), rr(-0.3, 0.3))).normalized(),
                       Vector((0, 0, 1)), rr(0.13, 0.22), 0.5)


def build_sfondo(B):
    """Paesaggio di fondo: macchie di alberi e filari di cipressi sulle colline,
    con chiome semplificate (bozzoli di foglie) sfumate dalla foschia."""
    chioma, corteccia = B["chioma"], B["tronco"]
    for i in range(150):
        a = rr(0, TAU)
        d = rr(42.0, 165.0)
        x, y = math.cos(a) * d, math.sin(a) * d
        z = terrain_z(x, y)
        if z < 1.5 and random.random() < 0.5:
            continue
        h = rr(4.5, 11.0)
        add_cylinder(corteccia, (x, y, z - 0.2), (x, y, z + h * 0.45), rr(0.10, 0.22),
                     sides=6)
        for j in range(random.randint(3, 6)):
            c = Vector((x + rr(-0.6, 0.6) * h * 0.14, y + rr(-0.6, 0.6) * h * 0.14,
                        z + h * rr(0.45, 0.95)))
            r = rr(0.8, 2.0) * (h / 8.0)
            k = rr(0.45, 0.85)
            chioma.color = (k * rr(0.7, 1.0), k, k * rr(0.6, 0.9))
            add_sphere(chioma, c, r, segs=10, rings=6, amp=0.36, nscale=2.1,
                       scale=(1.0, 1.0, 0.85), seed_off=x + y + j)
    for i in range(60):
        a = rr(0, TAU)
        d = rr(35.0, 150.0)
        x, y = math.cos(a) * d, math.sin(a) * d
        if terrain_z(x, y) < 0.8:
            continue
        build_cipresso(B, x, y, h=rr(5.0, 9.0), r=rr(0.55, 0.85))


def build_giardino(B):
    build_terreno(B)
    build_deck_esterno(B)
    build_piscina(B)
    build_vialetto(B)
    build_ghiaione(B)
    # siepi di confine
    build_siepe(B, (-13.6, -9.0), (-13.6, 7.5))
    build_siepe(B, (-13.6, -9.4), (3.4, -9.4))
    build_siepe(B, (14.2, -6.0), (14.2, 13.0))
    build_siepe(B, (-13.6, 7.5), (-9.0, 7.5), h=0.75)
    # aiuola di lavande lungo il vialetto
    build_lavanda(B, [(0.55, 6.2, 0.30), (0.55, 7.6, 0.34), (0.55, 9.0, 0.30),
                      (0.55, 10.4, 0.32), (2.90, 5.9, 0.28), (2.90, 7.3, 0.30),
                      (2.90, 10.0, 0.30), (3.05, 13.6, 0.32), (0.55, 13.6, 0.30)])
    # graminacee nelle aiuole di ghiaia
    build_graminacee(B, [(-8.60, 2.10, 1.0), (-9.70, -0.90, 1.25), (-11.00, 1.60, 1.15),
                         (-8.40, -1.60, 0.9), (-10.20, 3.90, 1.0), (-7.90, 4.60, 0.85),
                         (-8.90, -4.10, 0.95), (-2.40, -4.20, 0.9), (6.90, 6.30, 1.0),
                         (8.30, 7.60, 1.1), (-6.80, 7.60, 0.95), (6.60, 8.90, 0.9)])
    # alberi nel giardino: tenuti fuori dal cono della camera di presentazione
    build_albero(B, -10.30, -0.20, h=7.4, fusti=4, foglie=2400, betulla=True, seed=1)
    build_albero(B, -3.60, 17.20, h=7.8, fusti=3, foglie=2600, betulla=True, seed=2)
    build_albero(B, -6.20, -13.40, h=8.6, fusti=3, foglie=3000, seed=3)
    build_albero(B, 1.60, -15.20, h=9.4, fusti=2, foglie=3400, seed=4)
    build_albero(B, 10.20, -9.60, h=8.0, fusti=3, foglie=2600, betulla=True, seed=5)
    build_albero(B, 13.80, 6.40, h=8.4, fusti=2, foglie=2800, seed=6)
    build_albero(B, -14.60, -8.20, h=9.0, fusti=2, foglie=3000, seed=7)
    build_albero(B, 14.60, 15.60, h=7.5, fusti=2, foglie=2200, seed=8)
    build_albero(B, -16.20, 12.80, h=8.2, fusti=2, foglie=2400, betulla=True, seed=9)
    build_cipresso(B, -13.40, -11.60, h=8.0)
    build_cipresso(B, 16.40, 9.60, h=7.0)
    build_erba(B, count=11000)
    build_sfondo(B)

def mat_quadro():
    """Dipinto astratto: campiture di colore con texture di tela."""
    m, nt, b = _mat("Dipinto")
    gen = _coord(nt, (-1100, 0), "Object")
    tela = _noise(nt, 320.0, 5.0, 0.6, loc=(-850, -220), vec=gen)
    macchia = _noise(nt, 2.2, 6.0, 0.55, 1.4, loc=(-850, 180), vec=gen)
    segno = _wave(nt, 4.0, loc=(-850, 420), vec=gen, direction="X", dist=6.0, detail=4.0)
    col = _ramp(nt, macchia.outputs["Fac"],
                [(0.28, srgb(196, 88, 62)), (0.45, srgb(232, 214, 190)),
                 (0.62, srgb(58, 74, 104)), (0.80, srgb(214, 176, 96))], loc=(-560, 180))
    col2 = _mix(nt, 0.35, col.outputs["Color"], srgb(40, 46, 58), loc=(-320, 100))
    col2 = _mix(nt, segno.outputs["Fac"], col2, srgb(226, 214, 198), loc=(-240, 100))
    col3 = _mix(nt, 0.18, col2, tela.outputs["Fac"], loc=(-120, 0))
    nt.links.new(col3, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.62
    _bump(nt, tela.outputs["Fac"], b, 0.3, 0.002)
    return m


def make_materials():
    return {
        "cls": mat_calcestruzzo("Calcestruzzo"),
        "smalto": mat_calcestruzzo("Calcestruzzo_pavimento", (206, 202, 192),
                                   (176, 172, 162), passo=1.35, fori=False),
        "into": mat_intonaco(),
        "legno": mat_legno("Legno_doghe", (152, 108, 66), (94, 62, 38), 0.52,
                           (5.0, 5.0, 22.0), coat=0.15, dist=2.2, attr=True),
        "rovere": mat_legno("Rovere", (188, 140, 82), (138, 96, 54), 0.40,
                            (7.0, 7.0, 30.0), coat=0.35, dist=2.0, attr=True),
        "noce": mat_legno("Noce", (124, 86, 54), (76, 50, 32), 0.44, (4.0, 4.0, 14.0),
                          coat=0.25, dist=3.0, attr=True),
        "tronco": mat_legno("Tronco", (118, 96, 72), (74, 58, 44), 0.78, (2.4, 2.4, 9.0),
                            dist=4.5),
        "corteccia": mat_corteccia_betulla(),
        "serr": mat_metallo("Alluminio", (88, 90, 92), 0.35, metallic=0.8),
        "ferro": mat_metallo("Ferro_nero", (38, 38, 40), 0.42, 0.9),
        "acciaio": mat_metallo("Acciaio_inox", (154, 156, 158), 0.26, 1.0, aniso=0.4),
        "ottone": mat_metallo("Ottone", (176, 134, 58), 0.26, 1.0),
        "rame": mat_metallo("Rame", (188, 108, 62), 0.30, 1.0),
        "vetro": mat_vetro(),
        "vetro_scuro": mat_semplice("Vetro_scuro", (16, 18, 20), 0.12, spec=0.5),
        "guarn": mat_semplice("Guarnizioni", (28, 28, 30), 0.72),
        "marmo": mat_marmo(),
        "ceramica": mat_ceramica(),
        "tessuto": mat_tessuto("Tessuto_chiaro", (198, 194, 184), 0.92, 0.5, 520.0),
        "tessuto2": mat_tessuto("Tessuto_scuro", (104, 110, 118), 0.9, 0.4, 430.0),
        "tappeto": mat_tappeto(),
        "libri": mat_libri(),
        "quadro": mat_semplice("Cornici", (46, 44, 42), 0.5),
        "quadro2": mat_quadro(),
        "luce": mat_semplice("Luci_calde", (255, 236, 206), 0.5, emit=(255, 224, 182),
                             emit_str=30.0),
        "fv": mat_pannello_fv(),
        "grav": mat_ghiaia(),
        "terra": mat_terra(),
        "piscina": mat_semplice("Fondo_piscina", (152, 172, 164), 0.72),
        "acqua": mat_acqua(),
        "prato": mat_prato(),
        "erba": mat_fogliame("Erba_ciuffi", (72, 104, 38), (142, 168, 74), transl=0.30),
        "foglia": mat_fogliame("Fogliame", (56, 92, 44), (126, 160, 76), transl=0.25),
        "lavanda": mat_fogliame("Lavanda", (116, 108, 148), (178, 152, 200), transl=0.20),
        "siepe": mat_fogliame("Siepe", (34, 64, 28), (78, 112, 44), transl=0.20),
        "siepe2": mat_semplice("Siepe_interna", (22, 38, 18), 0.95),
        "cipresso": mat_fogliame("Cipresso", (30, 52, 30), (62, 88, 48), transl=0.20),
        "chioma": mat_fogliame("Chioma", (44, 74, 34), (104, 134, 58), transl=0.20),
        "pietra": mat_pietra("Pietra_naturale"),
    }


BUF_SPEC = [
    # chiave,        nome oggetto,           collezione,   colore per vertice
    ("cls",         "Calcestruzzo",         "Edificio",   False),
    ("into",        "Intonaco",             "Edificio",   False),
    ("legno",       "Doghe_e_deck",         "Edificio",   True),
    ("serr",        "Infissi_alluminio",    "Serramenti", False),
    ("guarn",       "Guarnizioni",          "Serramenti", False),
    ("vetro",       "Vetri",                "Serramenti", False),
    ("vetro_scuro", "Vetri_scuri",          "Serramenti", False),
    ("ferro",       "Ferro_e_ferramenta",   "Serramenti", False),
    ("acciaio",     "Acciaio_inox",         "Serramenti", False),
    ("ottone",      "Ottoni",               "Serramenti", False),
    ("rame",        "Lampade_in_rame",      "Serramenti", False),
    ("luce",        "Corpi_illuminanti",    "Serramenti", False),
    ("fv",          "Pannelli_fotovoltaici", "Tetto",     False),
    ("rovere",      "Pavimenti_in_rovere",  "Interni",    True),
    ("noce",        "Arredi_in_legno",      "Interni",    True),
    ("marmo",       "Marmi",                "Interni",    False),
    ("ceramica",    "Ceramiche",            "Interni",    False),
    ("tessuto",     "Tessuti_chiari",       "Interni",    False),
    ("tessuto2",    "Tessuti_scuri",        "Interni",    False),
    ("tappeto",     "Tappeti",              "Interni",    False),
    ("libri",       "Libri",                "Interni",    True),
    ("quadro",      "Cornici",              "Interni",    False),
    ("quadro2",     "Dipinti",              "Interni",    False),
    ("grav",        "Ghiaia",               "Giardino",   False),
    ("terra",       "Terriccio",            "Giardino",   False),
    ("smalto",      "Pavimentazioni",       "Giardino",   False),
    ("piscina",     "Vasca_piscina",        "Giardino",   False),
    ("acqua",       "Acqua",                "Giardino",   False),
    ("prato",       "Prato",                "Giardino",   False),
    ("erba",        "Erba",                 "Giardino",   True),
    ("foglia",      "Fogliame",             "Giardino",   True),
    ("lavanda",     "Lavande",              "Giardino",   True),
    ("siepe",       "Siepi",                "Giardino",   True),
    ("siepe2",      "Siepi_anima",          "Giardino",   False),
    ("cipresso",    "Cipressi",             "Giardino",   True),
    ("chioma",      "Chiome",               "Giardino",   True),
    ("corteccia",   "Betulle",              "Giardino",   False),
    ("tronco",      "Tronchi",              "Giardino",   False),
    ("pietra",      "Massi",                "Giardino",   False),
]


def make_buffers(mats):
    B = {}
    for key, name, coll, usec in BUF_SPEC:
        B[key] = new_buf(name, mats[key], usec)
    return B


def buf_to_object(buf, coll):
    if not buf.F:
        return None
    me = bpy.data.meshes.new(buf.name)
    me.from_pydata(buf.V, [], buf.F)
    me.validate(verbose=False)
    me.update()
    if len(me.polygons) == len(buf.S):
        me.polygons.foreach_set("use_smooth", buf.S)
    if buf.use_color and buf.C:
        att = me.color_attributes.new("Var", "BYTE_COLOR", "POINT")
        flat = []
        for c in buf.C:
            flat.extend((c[0], c[1], c[2], 1.0))
        att.data.foreach_set("color", flat)
    ob = bpy.data.objects.new(buf.name, me)
    me.materials.append(buf.mat)
    coll.objects.link(ob)
    return ob


# ---------------------------------------------------------------------------
# Scena: cielo, sole, camera, render
# ---------------------------------------------------------------------------
SUN_ELEV = 26.0
SUN_AZ = 34.0               # direzione da cui arriva la luce (gradi)


def sun_vector():
    """Direzione di propagazione della luce solare (vettore unitario)."""
    el, az = math.radians(SUN_ELEV), math.radians(SUN_AZ)
    # azimut misurato dall'asse +Y (facciata principale) verso +X
    return Vector((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az),
                   -math.sin(el))).normalized()


def setup_scena(root):
    scene = bpy.context.scene
    sd = sun_vector()

    # --- cielo (Nishita) ---------------------------------------------------
    world = bpy.data.worlds.new("Cielo")
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.location = (-700, 0)
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(SUN_ELEV)
    sky.sun_rotation = math.radians(180.0 - SUN_AZ)
    sky.sun_disc = False
    sky.altitude = 200
    sky.air_density = 0.70
    sky.dust_density = 0.30
    sky.ozone_density = 2.0
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    bg_cam.location = (-380, 120)
    bg_cam.inputs["Strength"].default_value = 0.86
    bg_amb = nt.nodes.new("ShaderNodeBackground")
    bg_amb.location = (-380, -80)
    bg_amb.inputs["Strength"].default_value = 0.11
    lp = nt.nodes.new("ShaderNodeLightPath")
    lp.location = (-380, 420)
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.location = (-120, 0)
    nt.links.new(sky.outputs["Color"], bg_cam.inputs["Color"])
    nt.links.new(sky.outputs["Color"], bg_amb.inputs["Color"])
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(bg_amb.outputs["Background"], mix.inputs[1])
    nt.links.new(bg_cam.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    scene.world = world

    # --- sole --------------------------------------------------------------
    light = bpy.data.lights.new("Sole", "SUN")
    light.energy = 11.0
    light.angle = math.radians(0.7)
    light.color = (1.0, 0.93, 0.82)
    lob = bpy.data.objects.new("Sole", light)
    lob.location = -sd * 80.0
    lob.rotation_euler = sd.to_track_quat("-Z", "Y").to_euler()
    root.objects.link(lob)

    # --- camera ------------------------------------------------------------
    cam = bpy.data.cameras.new("Camera")
    cam.lens = 38.0
    cam.clip_end = 500.0
    cam.dof.use_dof = True
    pos = Vector((-13.60, 15.40, 4.70))
    target = Vector((-0.30, 1.10, 3.00))
    cam.dof.focus_distance = (target - pos).length
    cam.dof.aperture_fstop = 11.0
    cob = bpy.data.objects.new("Camera", cam)
    cob.location = pos
    cob.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    root.objects.link(cob)
    scene.camera = cob

    # --- render -------------------------------------------------------------
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 96
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    scene.cycles.max_bounces = 10
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 8
    scene.cycles.transparent_max_bounces = 8
    scene.cycles.caustics_reflective = False
    scene.cycles.caustics_refractive = False
    scene.render.resolution_x = 1500
    scene.render.resolution_y = 1050
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.filepath = OUT_PNG
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.compression = 15
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.0
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0


def argomenti():
    opts = {"render": False, "samples": None, "res": None, "quick": False,
            "cam": None}
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = argv[1:]
    for i, a in enumerate(argv):
        if a == "--render":
            opts["render"] = True
        elif a == "--quick":
            opts["quick"] = True
            opts["render"] = True
        elif a == "--samples" and i + 1 < len(argv):
            opts["samples"] = int(argv[i + 1])
        elif a == "--cam" and i + 1 < len(argv):
            v = [float(t) for t in argv[i + 1].split(",")]
            opts["cam"] = (v[0:3], v[3:6])
        elif a == "--res" and i + 1 < len(argv):
            w, h = argv[i + 1].lower().split("x")
            opts["res"] = (int(w), int(h))
    return opts


def main():
    import time
    t0 = time.time()
    opts = argomenti()
    bpy.ops.wm.read_factory_settings(use_empty=True)

    root = bpy.data.collections.new("Villa_2")
    bpy.context.scene.collection.children.link(root)
    subs = {}
    for nome in ("Edificio", "Serramenti", "Tetto", "Interni", "Giardino"):
        c = bpy.data.collections.new(nome)
        root.children.link(c)
        subs[nome] = c

    mats = make_materials()
    B = make_buffers(mats)

    print("» platea, solai, muri ...")
    build_platea(B)
    build_solai(B)
    build_muri_terra(B)
    build_tramezzi(B)
    print("» vetrate, infissi, ingresso, frangisole ...")
    build_facciata_vetro(B)
    build_infissi(B)
    build_ingresso(B)
    build_pensilina(B)
    build_frangisole(B)
    print("» scala, tetto e terrazza ...")
    build_scala(B)
    build_tetto(B)
    build_terrazza(B)
    print("» interni e arredi ...")
    build_pavimenti(B)
    build_soffitti(B)
    build_arredi_pt(B)
    build_arredi_p1(B)
    build_porta_interna(B, "x", 1.60, -2.90, -2.10, Z_F0)      # wc di servizio
    build_porta_interna(B, "y", -2.40, -1.25, -0.25, Z_F0)     # lavanderia
    build_porta_interna(B, "x", -2.60, -0.60, 0.30, Z_F1)      # camera
    build_porta_interna(B, "x", -1.00, -2.90, -2.00, Z_F1)     # bagno padronale
    build_porta_interna(B, "x", 1.60, -2.90, -2.00, Z_F1)      # cabina armadio
    print("» giardino, piscina, piante ...")
    build_giardino(B)

    nv = sum(b.nverts for b in BUFS)
    nf = sum(len(b.F) for b in BUFS)
    print("   geometria: %d vertici, %d facce" % (nv, nf))

    print("» creazione oggetti ...")
    for key, name, coll, usec in BUF_SPEC:
        buf_to_object(B[key], subs[coll])

    setup_scena(root)
    if opts["samples"]:
        bpy.context.scene.cycles.samples = opts["samples"]
    if opts["res"]:
        bpy.context.scene.render.resolution_x = opts["res"][0]
        bpy.context.scene.render.resolution_y = opts["res"][1]
    if opts["cam"]:
        cob = bpy.data.objects["Camera"]
        p, t = Vector(opts["cam"][0]), Vector(opts["cam"][1])
        cob.location = p
        cob.rotation_euler = (t - p).to_track_quat("-Z", "Y").to_euler()
        cob.data.dof.focus_distance = (t - p).length
    print("» salvataggio %s" % OUT_BLEND)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("   fatto in %.1f s (%.1f MB)" % (time.time() - t0,
                                            os.path.getsize(OUT_BLEND) / 1e6))

    if opts["render"]:
        print("» render anteprima ...")
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        print("   render in %.1f s -> %s" % (time.time() - t1, OUT_PNG))


if __name__ == "__main__":
    main()
