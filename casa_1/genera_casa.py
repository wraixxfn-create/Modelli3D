"""
Genera una casa 3D molto dettagliata e salva il file Blender `casa.blend`.

Modello: casale/villetta di campagna a due piani con tetto a falde in coppi.
Tutta la geometria e' costruita proceduralmente, elemento per elemento
(nessun oggetto primitivo "finto"): muratura con spessore reale e vani passanti,
infissi, persiane a lamelle, coppi posati uno a uno, travatura del tetto, ecc.

Contenuto del modello
---------------------
  * muri perimetrali spessi 35 cm con vani (finestre/porte) passanti,
    spalle (sguinci) e facce interne; solai e tramezzi interni cosi' che
    attraverso i vetri si veda un interno e non il vuoto
  * zoccolo in pietra, cantonali bugnati agli angoli, marcapiano,
    cornicione con dentelli
  * 18 finestre con davanzale in pietra, mostra con chiave di volta, telaio,
    ante con traversi, vetri, maniglie in ottone e persiane alla romana
    a lamelle (aperte, socchiuse o chiuse) complete di cardini
  * portone d'ingresso a due battenti con pannelli a bugna, battacchio,
    pomoli e bocchette in ottone, sopraluce a raggiera, portale in pietra
    e gradinata; porta secondaria sul retro
  * balcone con mensole in pietra e ringhiera in ferro battuto
  * tetto a due falde: trave di colmo, arcarecci, travetti, tavolato,
    ~3650 coppi posati uno a uno con variazione di colore e posa,
    colmo in coppi, tavole di bordo, grondaie, pluviali e staffe
  * comignolo in mattoni (posati uno a uno) con mitra in cotto
  * timpani con occhio in pietra e grata di aerazione in legno
  * lanterna da esterno accesa, cassette fiorite sui davanzali e tende in
    lino (a velo o a teli raccolti) dietro i vetri
  * marciapiede perimetrale in lastre di pietra con cordolo; pluviali sui
    cantonali con collari e pozzetto a griglia
  * giardino: terreno ondulato (170 m di raggio, con colline all'orizzonte),
    22000 ciuffi d'erba a raggiera con fili secchi, vialetto in lastre di
    pietra, cespugli e cipressi rivestiti di foglie (tinta per foglia),
    alberi a foglia larga e vasi in cotto con gerani
  * paesaggio di fondo: filari di cipressi e macchie d'alberi sulle colline,
    con prospettiva aerea (foschia in funzione della distanza dalla camera)
  * cielo procedurale (Nishita), sole, camera di presentazione

Esecuzione (richiede il modulo `bpy` di Blender 4.x):
    python3 genera_casa.py            # costruisce e salva casa.blend
    python3 genera_casa.py --render   # ... e renderizza anche anteprima.png
"""

import math
import os
import random
import sys

import bpy
from mathutils import Vector, Matrix, noise

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_BLEND = os.path.join(HERE, "casa.blend")
OUT_PNG = os.path.join(HERE, "anteprima.png")

SEED = 20261010
random.seed(SEED)

PI = math.pi
TAU = 2.0 * math.pi

# ---------------------------------------------------------------------------
# Parametri generali (unita': metri)
# ---------------------------------------------------------------------------
W_X = 9.00              # larghezza del corpo di fabbrica (facciata principale)
D_Y = 7.00              # profondita'
T_W = 0.35              # spessore dei muri perimetrali

Z_PLINTH = 0.52         # altezza dello zoccolo in pietra / quota pavimento
H_F0 = 2.88             # altezza interna piano terra
Z_F1 = Z_PLINTH + H_F0  # quota pavimento primo piano  (3.40)
H_F1 = 2.80             # altezza interna primo piano
Z_TOP = Z_F1 + H_F1     # sommita' dei muri                (6.20)

Z_CORN0 = 5.98          # cornicione
Z_CORN1 = 6.20
CORN_OUT = 0.11

PITCH = math.radians(25.0)
TANP = math.tan(PITCH)
COSP = math.cos(PITCH)
Z_RIDGE_STRUCT = 8.00   # quota del piano estradosso travetti sull'asse del colmo
OVH_EAVE = 0.70         # sporto di gronda (lati lunghi)
OVH_RAKE = 0.55         # sporto sui timpani
PLANK_T = 0.035 / COSP  # spessore verticale del tavolato

HALF_X = W_X / 2.0
HALF_Y = D_Y / 2.0


def roof_z(y):
    """Quota del piano di appoggio dei travetti (estradosso) a distanza y dal colmo."""
    return Z_RIDGE_STRUCT - abs(y) * TANP


def plank_z(y):
    """Quota della faccia superiore del tavolato (= piano di posa dei coppi)."""
    return roof_z(y) + PLANK_T


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def rr(a, b):
    return a + (b - a) * random.random()


def clamp(x, a, b):
    return a if x < a else (b if x > b else x)


def srgb(r, g, b):
    """Colore sRGB 0-255 -> lineare."""
    return tuple((c / 255.0) ** 2.2 for c in (r, g, b))


def jitter_color(col, amount):
    return tuple(clamp(c * (1.0 + rr(-amount, amount)), 0.0, 1.0) for c in col)


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
    # indice = i*4 + j*2 + k
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

    frames: lista di (origine, asse_x, asse_y, scala)  -- la direzione di
            avanzamento deve essere asse_x cross asse_y
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
        fr = frames[0]
        o, xa, ya, s = fr
        sx, sy = (s, s) if isinstance(s, (int, float)) else s
        pts = [o + xa * (p[0] * sx) + ya * (p[1] * sy) for p in profile]
        buf.poly(pts[::-1])
        fr = frames[-1]
        o, xa, ya, s = fr
        sx, sy = (s, s) if isinstance(s, (int, float)) else s
        pts = [o + xa * (p[0] * sx) + ya * (p[1] * sy) for p in profile]
        buf.poly(pts)


def circle_profile(n, r=1.0, phase=0.0):
    return [(r * math.cos(phase + TAU * i / n), r * math.sin(phase + TAU * i / n))
            for i in range(n)]


def add_cylinder(buf, p0, p1, r, sides=12, caps=True):
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0)
    L = d.length
    if L < 1e-9:
        return
    zax = d / L
    ref = Vector((0, 0, 1)) if abs(zax.z) < 0.9 else Vector((1, 0, 0))
    xa = zax.cross(ref).normalized()
    ya = zax.cross(xa).normalized()
    if xa.cross(ya).dot(zax) < 0:
        ya = -ya
    prof = circle_profile(sides, r)
    sweep(buf, [(p0, xa, ya, 1.0), (p1, xa, ya, 1.0)], prof, True, caps)


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


# ---------------------------------------------------------------------------
# Pannelli murari con vani
# ---------------------------------------------------------------------------
def panel(buf, o, u, v, W, H, holes, flip=False, v0=0.0):
    """Pannello rettangolare (W x H) con fori rettangolari.

    holes: lista di (u0, z0, u1, z1) in coordinate locali del pannello.
    """
    cuts = {0.0, H}
    for (a0, b0, a1, b1) in holes:
        cuts.add(clamp(b0 - v0, 0.0, H))
        cuts.add(clamp(b1 - v0, 0.0, H))
    cuts = sorted(cuts)
    for i in range(len(cuts) - 1):
        y0, y1 = cuts[i], cuts[i + 1]
        if y1 - y0 < 1e-6:
            continue
        ym = 0.5 * (y0 + y1) + v0
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


def add_wall(buf_out, buf_in, buf_rev, o, u, v, W, H, T, holes,
             cap_top=True, cap_bottom=False, cap_sides=False):
    """Muro con spessore e vani passanti.

    o: angolo esterno in basso a sinistra; u: direzione larghezza;
    v: direzione altezza; la normale esterna e' u x v.
    """
    o = Vector(o)
    u, v = Vector(u).normalized(), Vector(v).normalized()
    n = u.cross(v).normalized()
    oi = o - n * T                     # faccia interna
    panel(buf_out, o, u, v, W, H, holes, flip=False)
    panel(buf_in, oi, u, v, W, H, holes, flip=True)
    # sguinci (spalle, architrave e soglia di ogni vano)
    for (a0, b0, a1, b1) in holes:
        P = [o + u * a0 + v * b0, o + u * a1 + v * b0,
             o + u * a1 + v * b1, o + u * a0 + v * b1]
        Q = [p - n * T for p in P]
        buf_rev.quad_dir(P[0], P[1], Q[1], Q[0], v)            # soglia (verso l'alto)
        buf_rev.quad_dir(P[3], P[2], Q[2], Q[3], -v)           # architrave
        buf_rev.quad_dir(P[0], P[3], Q[3], Q[0], u)            # spalla sinistra
        buf_rev.quad_dir(P[1], P[2], Q[2], Q[1], -u)           # spalla destra
    if cap_top:
        buf_rev.quad_dir(o + v * H, o + u * W + v * H,
                         o + u * W + v * H - n * T, o + v * H - n * T, v)
    if cap_bottom:
        buf_rev.quad_dir(o, o + u * W, o + u * W - n * T, o - n * T, -v)
    if cap_sides:
        buf_rev.quad_dir(o, o + v * H, o + v * H - n * T, o - n * T, -u)
        buf_rev.quad_dir(o + u * W, o + u * W + v * H,
                         o + u * W + v * H - n * T, o + u * W - n * T, u)


# ---------------------------------------------------------------------------
# Materiali procedurali (Cycles)
# ---------------------------------------------------------------------------
def _mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
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
        nt.links.new(vec, n.inputs["Vector"])
    return n


def _bump(nt, height_out, bsdf, strength=0.3, distance=0.02, loc=(60, -260)):
    b = nt.nodes.new("ShaderNodeBump")
    b.location = loc
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = distance
    nt.links.new(height_out, b.inputs["Height"])
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
    nt.links.new(fac_out, r.inputs["Fac"])
    return r


def _mix(nt, fac_out, col_a, col_b, loc=(0, 0)):
    """Nodo Mix (RGBA): A e B possono essere colori o uscite di altri nodi."""
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    m.location = loc
    if isinstance(fac_out, (int, float)):
        m.inputs[0].default_value = float(fac_out)
    elif fac_out is not None:
        nt.links.new(fac_out, m.inputs[0])
    for slot, val in ((6, col_a), (7, col_b)):
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


def mat_intonaco():
    """Intonaco a calce color sabbia, con grana, scrostature e sporco in basso."""
    m, nt, b = _mat("Intonaco")
    gen = _coord(nt, (-1200, 0), "Object")
    grana = _noise(nt, 55.0, 12.0, 0.7, loc=(-900, 200), vec=gen)
    macchie = _noise(nt, 1.4, 9.0, 0.55, 0.3, loc=(-900, -200), vec=gen)
    base = _ramp(nt, macchie.outputs["Fac"],
                 [(0.30, srgb(205, 184, 146)), (0.52, srgb(214, 195, 158)),
                  (0.76, srgb(196, 174, 138))], loc=(-650, -200))
    # sporco/umidita' verso il basso (coordinata Z oggetto)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-900, -520)
    nt.links.new(gen, sep.inputs["Vector"])
    zmap = nt.nodes.new("ShaderNodeMapRange")
    zmap.location = (-700, -520)
    zmap.inputs["From Min"].default_value = 0.4
    zmap.inputs["From Max"].default_value = 1.9
    zmap.inputs["To Min"].default_value = 1.0
    zmap.inputs["To Max"].default_value = 0.0
    zmap.clamp = True
    nt.links.new(sep.outputs["Z"], zmap.inputs["Value"])
    chiazze = _noise(nt, 6.0, 6.0, 0.6, loc=(-900, -760), vec=gen)
    sporco_f = nt.nodes.new("ShaderNodeMath")
    sporco_f.operation = "MULTIPLY"
    sporco_f.location = (-480, -620)
    nt.links.new(zmap.outputs["Result"], sporco_f.inputs[0])
    nt.links.new(chiazze.outputs["Fac"], sporco_f.inputs[1])
    sporco_g = nt.nodes.new("ShaderNodeMath")
    sporco_g.operation = "MULTIPLY"
    sporco_g.location = (-330, -620)
    sporco_g.inputs[1].default_value = 0.55
    nt.links.new(sporco_f.outputs["Value"], sporco_g.inputs[0])
    col = _mix(nt, sporco_g.outputs["Value"], base.outputs["Color"], srgb(164, 150, 126),
               loc=(-200, -200))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.92
    b.inputs["Specular IOR Level"].default_value = 0.25
    mixh = nt.nodes.new("ShaderNodeMath")
    mixh.operation = "ADD"
    mixh.location = (-200, 260)
    nt.links.new(grana.outputs["Fac"], mixh.inputs[0])
    nt.links.new(macchie.outputs["Fac"], mixh.inputs[1])
    _bump(nt, mixh.outputs["Value"], b, 0.28, 0.006)
    return m


def mat_interno():
    m, nt, b = _mat("Intonaco_interno")
    b.inputs["Base Color"].default_value = (*srgb(232, 226, 214), 1.0)
    b.inputs["Roughness"].default_value = 0.95
    b.inputs["Specular IOR Level"].default_value = 0.15
    return m


def mat_pietra(name="Pietra", c0=(178, 166, 140), c1=(140, 128, 106), scale=3.0,
               use_attr=False):
    """Pietra calcarea per zoccolo, cantonali, davanzali, portale."""
    m, nt, b = _mat(name)
    gen = _coord(nt, (-1200, 0), "Object")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.location = (-900, 220)
    vor.inputs["Scale"].default_value = 14.0
    vor.inputs["Randomness"].default_value = 1.0
    nt.links.new(gen, vor.inputs["Vector"])
    gran = _noise(nt, 90.0, 10.0, 0.75, loc=(-900, -40), vec=gen)
    ven = _noise(nt, scale, 10.0, 0.6, 1.2, loc=(-900, -320), vec=gen)
    col = _ramp(nt, ven.outputs["Fac"],
                [(0.3, srgb(*c1)), (0.5, srgb(*c0)),
                 (0.72, srgb(min(255, c0[0] + 22), min(255, c0[1] + 22), min(255, c0[2] + 20)))],
                loc=(-620, -320))
    base_col = col.outputs["Color"]
    if use_attr:
        at = nt.nodes.new("ShaderNodeAttribute")
        at.location = (-620, 20)
        at.attribute_name = "Var"
        mixn = nt.nodes.new("ShaderNodeMix")
        mixn.data_type = "RGBA"
        mixn.blend_type = "MIX"
        mixn.location = (-380, -200)
        mixn.inputs[0].default_value = 0.5
        nt.links.new(base_col, mixn.inputs[6])
        nt.links.new(at.outputs["Color"], mixn.inputs[7])
        base_col = mixn.outputs[2]
    nt.links.new(base_col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    b.inputs["Specular IOR Level"].default_value = 0.3
    h = nt.nodes.new("ShaderNodeMath")
    h.operation = "MULTIPLY_ADD"
    h.location = (-500, 140)
    h.inputs[1].default_value = 0.5
    nt.links.new(vor.outputs["Distance"], h.inputs[0])
    nt.links.new(gran.outputs["Fac"], h.inputs[2])
    _bump(nt, h.outputs["Value"], b, 0.45, 0.012)
    return m


def mat_cotto():
    """Cotto dei coppi: colore per-tegola da attributo + patina e muschio."""
    m, nt, b = _mat("Cotto_coppi")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.location = (-900, 200)
    attr.attribute_name = "Var"
    gen = _coord(nt, (-1200, -300), "Object")
    patina = _noise(nt, 18.0, 10.0, 0.7, loc=(-900, -300), vec=gen)
    muschio = _noise(nt, 4.0, 8.0, 0.75, 0.6, loc=(-900, -560), vec=gen)
    mr = _ramp(nt, muschio.outputs["Fac"],
               [(0.58, (0.0, 0.0, 0.0)), (0.74, (0.75, 0.75, 0.75))], loc=(-640, -560))
    c1 = _mix(nt, patina.outputs["Fac"], attr.outputs["Color"], srgb(118, 58, 36), loc=(-380, 0))
    c2 = _mix(nt, mr.outputs["Color"], c1, srgb(112, 104, 72), loc=(-150, -140))
    nt.links.new(c2, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.78
    rug = _noise(nt, 160.0, 6.0, 0.6, loc=(-900, 460), vec=gen)
    _bump(nt, rug.outputs["Fac"], b, 0.35, 0.004)
    return m


def mat_mattoni():
    m, nt, b = _mat("Mattoni")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.location = (-600, 200)
    attr.attribute_name = "Var"
    gen = _coord(nt, (-1200, -200), "Object")
    gran = _noise(nt, 120.0, 8.0, 0.7, loc=(-900, -200), vec=gen)
    col = _mix(nt, gran.outputs["Fac"], attr.outputs["Color"], srgb(120, 66, 46), loc=(-300, 0))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.88
    _bump(nt, gran.outputs["Fac"], b, 0.3, 0.004)
    return m


def mat_legno(name, c0, c1, rough=0.55, scale=(6.0, 6.0, 26.0), coat=0.0, dist=2.5):
    """Legno con venature (onda distorta) orientata lungo Y oggetto."""
    m, nt, b = _mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-1200, 0)
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.location = (-1000, 0)
    mp.inputs["Scale"].default_value = scale
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.location = (-800, 120)
    wave.wave_type = "BANDS"
    wave.bands_direction = "Z"
    wave.wave_profile = "SIN"
    wave.inputs["Scale"].default_value = 1.4
    wave.inputs["Distortion"].default_value = dist
    wave.inputs["Detail"].default_value = 6.0
    wave.inputs["Detail Scale"].default_value = 2.2
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    fibre = _noise(nt, 220.0, 6.0, 0.7, loc=(-800, -240), vec=mp.outputs["Vector"])
    col = _ramp(nt, wave.outputs["Fac"], [(0.15, srgb(*c0)), (0.75, srgb(*c1))], loc=(-520, 120))
    col2 = _mix(nt, 0.09, col.outputs["Color"], fibre.outputs["Color"], loc=(-260, 0))
    nt.links.new(col2, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.18
    hsum = nt.nodes.new("ShaderNodeMath")
    hsum.operation = "MULTIPLY_ADD"
    hsum.location = (-300, 300)
    hsum.inputs[1].default_value = 0.4
    nt.links.new(wave.outputs["Fac"], hsum.inputs[0])
    nt.links.new(fibre.outputs["Fac"], hsum.inputs[2])
    _bump(nt, hsum.outputs["Value"], b, 0.22, 0.003)
    return m


def mat_vetro():
    m, nt, b = _mat("Vetro")
    b.inputs["Base Color"].default_value = (0.82, 0.88, 0.86, 1.0)
    b.inputs["Roughness"].default_value = 0.03
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.45
    m.use_backface_culling = False
    # i raggi d'ombra attraversano il vetro (caustiche disattivate): cosi' il
    # sole entra nelle stanze e illumina tende e davanzali interni
    lp = nt.nodes.new("ShaderNodeLightPath")
    lp.location = (300, 300)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.location = (300, -240)
    tr.inputs["Color"].default_value = (0.86, 0.9, 0.88, 1.0)
    mixs = nt.nodes.new("ShaderNodeMixShader")
    mixs.location = (480, 0)
    outn = [x for x in nt.nodes if x.type == "OUTPUT_MATERIAL"][0]
    outn.location = (700, 0)
    nt.links.new(lp.outputs["Is Shadow Ray"], mixs.inputs[0])
    nt.links.new(b.outputs["BSDF"], mixs.inputs[1])
    nt.links.new(tr.outputs["BSDF"], mixs.inputs[2])
    nt.links.new(mixs.outputs["Shader"], outn.inputs["Surface"])
    return m


def mat_metallo(name, col, rough, metallic=1.0):
    m, nt, b = _mat(name)
    b.inputs["Base Color"].default_value = (*srgb(*col), 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    nt_ = nt
    gen = _coord(nt_, (-900, -200), "Object")
    n = _noise(nt_, 70.0, 8.0, 0.6, loc=(-650, -200), vec=gen)
    _bump(nt_, n.outputs["Fac"], b, 0.12, 0.004)
    return m


HAZE_COL = (206, 216, 222)      # colore della foschia atmosferica (sRGB)


def _foschia(nt, col_out, d0=35.0, d1=190.0, amount=0.46, loc=(-60, -420)):
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


def mat_erba():
    """Prato: verde variegato, chiazze di erba secca e terra nelle zone rade."""
    m, nt, b = _mat("Prato")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-1400, 0)
    vec = tc.outputs["Object"]
    big = _noise(nt, 0.08, 6.0, 0.55, 0.4, loc=(-950, 380), vec=vec)
    mid = _noise(nt, 0.6, 10.0, 0.6, 0.5, loc=(-950, 140), vec=vec)
    small = _noise(nt, 14.0, 12.0, 0.7, loc=(-950, -120), vec=vec)
    ramp = _ramp(nt, mid.outputs["Fac"],
                 [(0.28, srgb(52, 78, 24)), (0.52, srgb(78, 108, 34)),
                  (0.78, srgb(104, 126, 44))], loc=(-700, 140))
    # chiazze di erba secca (scala grande)
    secca = _ramp(nt, big.outputs["Fac"],
                  [(0.50, (0.0, 0.0, 0.0)), (0.68, (0.55, 0.55, 0.55))], loc=(-700, 380))
    c1 = _mix(nt, secca.outputs["Color"], ramp.outputs["Color"], srgb(150, 140, 78),
              loc=(-460, 200))
    col = _mix(nt, 0.16, c1, small.outputs["Color"], loc=(-300, 0))
    col = _foschia(nt, col)
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    b.inputs["Specular IOR Level"].default_value = 0.2
    _bump(nt, small.outputs["Fac"], b, 0.3, 0.02)
    return m


def mat_fogliame(name="Fogliame", c0=(42, 70, 30), c1=(86, 120, 44), use_attr=False,
                 haze=True):
    """Fogliame: rumore di colore, eventuale tinta per foglia (attributo `Var`),
    leggera traslucenza e foschia in lontananza."""
    m, nt, b = _mat(name)
    gen = _coord(nt, (-1100, 0), "Object")
    n = _noise(nt, 26.0, 12.0, 0.75, 0.4, loc=(-850, 0), vec=gen)
    col = _ramp(nt, n.outputs["Fac"], [(0.3, srgb(*c0)), (0.7, srgb(*c1))], loc=(-600, 0))
    out = col.outputs["Color"]
    if use_attr:
        at = nt.nodes.new("ShaderNodeAttribute")
        at.location = (-600, 240)
        at.attribute_name = "Var"
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "MULTIPLY"
        mx.location = (-360, 120)
        mx.inputs[0].default_value = 1.0
        nt.links.new(out, mx.inputs[6])
        nt.links.new(at.outputs["Color"], mx.inputs[7])
        out = mx.outputs[2]
    if haze:
        out = _foschia(nt, out, loc=(-180, -300))
    nt.links.new(out, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.62
    b.inputs["Specular IOR Level"].default_value = 0.35
    b.inputs["Subsurface Weight"].default_value = 0.15
    b.inputs["Subsurface Radius"].default_value = (0.03, 0.05, 0.02)
    _bump(nt, n.outputs["Fac"], b, 0.4, 0.01)
    # le foglie sono superfici sottili: un po' di luce passa dal retro
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
    tr.location = (300, -260)
    nt.links.new(out, tr.inputs["Color"])
    mixs = nt.nodes.new("ShaderNodeMixShader")
    mixs.location = (480, -60)
    mixs.inputs[0].default_value = 0.22
    outn = [x for x in nt.nodes if x.type == "OUTPUT_MATERIAL"][0]
    outn.location = (700, 0)
    nt.links.new(b.outputs["BSDF"], mixs.inputs[1])
    nt.links.new(tr.outputs["BSDF"], mixs.inputs[2])
    nt.links.new(mixs.outputs["Shader"], outn.inputs["Surface"])
    return m


def mat_tende():
    """Tende in lino chiaro, semitrasparenti in controluce."""
    m, nt, b = _mat("Tende_lino")
    gen = _coord(nt, (-900, 0), "Object")
    trama = _noise(nt, 420.0, 4.0, 0.6, loc=(-650, -160), vec=gen)
    b.inputs["Base Color"].default_value = (*srgb(238, 232, 218), 1.0)
    b.inputs["Roughness"].default_value = 0.9
    b.inputs["Sheen Weight"].default_value = 0.4
    _bump(nt, trama.outputs["Fac"], b, 0.15, 0.002)
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
    tr.location = (300, -260)
    tr.inputs["Color"].default_value = (*srgb(244, 236, 214), 1.0)
    mixs = nt.nodes.new("ShaderNodeMixShader")
    mixs.location = (480, -60)
    mixs.inputs[0].default_value = 0.4
    outn = [x for x in nt.nodes if x.type == "OUTPUT_MATERIAL"][0]
    outn.location = (700, 0)
    nt.links.new(b.outputs["BSDF"], mixs.inputs[1])
    nt.links.new(tr.outputs["BSDF"], mixs.inputs[2])
    nt.links.new(mixs.outputs["Shader"], outn.inputs["Surface"])
    return m


def mat_semplice(name, col, rough=0.6, emit=None, emit_str=0.0, metallic=0.0):
    m, nt, b = _mat(name)
    b.inputs["Base Color"].default_value = (*srgb(*col), 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*srgb(*emit), 1.0)
        b.inputs["Emission Strength"].default_value = emit_str
    return m


# ---------------------------------------------------------------------------
# Muri: sistemi di riferimento e vani
# ---------------------------------------------------------------------------
# o = angolo esterno in basso "a sinistra", u = larghezza, v = altezza,
# normale esterna = u x v
WALLS = {
    "S": (Vector((-HALF_X, -HALF_Y, 0.0)), Vector((1, 0, 0)), Vector((0, 0, 1)), W_X),
    "E": (Vector((HALF_X, -HALF_Y + T_W, 0.0)), Vector((0, 1, 0)), Vector((0, 0, 1)), D_Y - 2 * T_W),
    "N": (Vector((HALF_X, HALF_Y, 0.0)), Vector((-1, 0, 0)), Vector((0, 0, 1)), W_X),
    "O": (Vector((-HALF_X, HALF_Y - T_W, 0.0)), Vector((0, -1, 0)), Vector((0, 0, 1)), D_Y - 2 * T_W),
}


def wall_frame(w):
    o, u, v, W = WALLS[w]
    return o, u, v, u.cross(v), W


OPENINGS = []


def op(wall, uc, w, z0, z1, kind="finestra", shut="aperte", sill=True,
       mostra=True, fiori=False, ante=2, traversi=1):
    d = dict(wall=wall, uc=uc, w=w, z0=z0, z1=z1, kind=kind, shut=shut,
             sill=sill, mostra=mostra, fiori=fiori, ante=ante, traversi=traversi)
    OPENINGS.append(d)
    return d


# --- facciata principale (Sud) -------------------------------------------
op("S", 1.65, 1.20, 1.42, 2.82, shut="aperte", fiori=True)
op("S", 4.50, 1.30, Z_PLINTH, 2.82, kind="portone", shut=None, sill=False)
op("S", 7.35, 1.20, 1.42, 2.82, shut="socchiuse")
op("S", 1.65, 1.20, 4.30, 5.60, shut="aperte", fiori=True)
op("S", 4.50, 1.30, Z_F1, 5.60, kind="portafinestra", shut="aperte", sill=False, traversi=2)
op("S", 7.35, 1.20, 4.30, 5.60, shut="chiuse")
# --- lato Est ------------------------------------------------------------
op("E", 1.85, 1.20, 1.42, 2.82, shut="aperte")
op("E", 4.45, 1.20, 1.42, 2.82, shut="chiuse")
op("E", 1.85, 1.00, 4.30, 5.60, shut="socchiuse")
op("E", 4.45, 1.00, 4.30, 5.60, shut="aperte")
# --- retro (Nord) --------------------------------------------------------
op("N", 1.90, 1.20, 1.42, 2.82, shut="aperte")
op("N", 4.50, 0.75, 1.95, 2.82, shut=None, traversi=0)
op("N", 7.10, 1.00, Z_PLINTH, 2.62, kind="porta", shut=None, sill=False)
op("N", 1.90, 1.00, 4.30, 5.60, shut="chiuse")
op("N", 4.50, 0.70, 4.85, 5.55, shut=None, traversi=0)
op("N", 7.10, 1.00, 4.30, 5.60, shut="aperte")
# --- lato Ovest ----------------------------------------------------------
op("O", 1.85, 1.20, 1.42, 2.82, shut="chiuse")
op("O", 4.45, 1.20, 1.42, 2.82, shut="aperte", fiori=True)
op("O", 1.85, 1.00, 4.30, 5.60, shut="aperte")
op("O", 4.45, 1.00, 4.30, 5.60, shut="socchiuse")


def holes_of(wall):
    return [(o["uc"] - o["w"] / 2.0, o["z0"], o["uc"] + o["w"] / 2.0, o["z1"])
            for o in OPENINGS if o["wall"] == wall]


# ---------------------------------------------------------------------------
# Fasce/cornici continue con profilo modanato e angoli a 45 gradi
# ---------------------------------------------------------------------------
def band(buf, profile, inset=0.0, z_off=0.0):
    """Sweep di un profilo (sporgenza, quota) lungo tutto il perimetro.

    L'angolo di ogni spigolo e' risolto con un telaio diagonale (miter).
    """
    prof = ensure_ccw([(p[0], p[1] + z_off) for p in profile])
    hx, hy = HALF_X - inset, HALF_Y - inset
    s2 = math.sqrt(2.0)
    corners = [
        (Vector((hx, -hy, 0)), Vector((1, -1, 0)).normalized()),
        (Vector((-hx, -hy, 0)), Vector((-1, -1, 0)).normalized()),
        (Vector((-hx, hy, 0)), Vector((-1, 1, 0)).normalized()),
        (Vector((hx, hy, 0)), Vector((1, 1, 0)).normalized()),
    ]
    frames = [(c, d, Vector((0, 0, 1)), (s2, 1.0)) for c, d in corners]
    frames.append(frames[0])
    sweep(buf, frames, prof, closed=True, caps=False)


def add_prism_poly(buf, pts, nrm, depth):
    """Prisma: poligono `pts` (faccia esterna, normale `nrm`) estruso di `depth`
    in direzione -nrm."""
    nrm = Vector(nrm).normalized()
    pts = [Vector(p) for p in pts]
    # orientamento della faccia esterna
    acc = Vector((0, 0, 0))
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        acc += a.cross(b)
    if acc.dot(nrm) < 0:
        pts = pts[::-1]
    inner = [p - nrm * depth for p in pts]
    buf.poly(pts)
    buf.poly(inner[::-1])
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        buf.poly((pts[i], inner[i], inner[j], pts[j]))


# ---------------------------------------------------------------------------
# Involucro murario
# ---------------------------------------------------------------------------
def build_shell(B):
    muri, interni, pietra = B["muri"], B["interni"], B["pietra"]

    # --- muri perimetrali con vani ----------------------------------------
    for w in ("S", "E", "N", "O"):
        o, u, v, n, W = wall_frame(w)
        add_wall(muri, interni, muri, o, u, v, W, Z_TOP, T_W, holes_of(w),
                 cap_top=True, cap_sides=(w in ("E", "O")))

    # --- timpani (frontoni) sui lati corti --------------------------------
    for sx in (-1, 1):
        x = sx * HALF_X
        pts = [Vector((x, -HALF_Y, Z_TOP)), Vector((x, HALF_Y, Z_TOP)),
               Vector((x, HALF_Y, roof_z(HALF_Y))), Vector((x, 0.0, roof_z(0.0))),
               Vector((x, -HALF_Y, roof_z(HALF_Y)))]
        add_prism_poly(muri, pts, Vector((sx, 0, 0)), T_W)

    # --- zoccolo in pietra -------------------------------------------------
    zoc = [(0.0, 0.0), (0.075, 0.0), (0.075, Z_PLINTH - 0.10),
           (0.035, Z_PLINTH - 0.02), (0.035, Z_PLINTH), (0.0, Z_PLINTH)]
    band(pietra, zoc)

    # --- marcapiano --------------------------------------------------------
    mc = [(0.0, 3.08), (0.045, 3.12), (0.075, 3.18), (0.075, 3.30),
          (0.045, 3.36), (0.0, 3.40)]
    band(pietra, mc)

    # --- cornicione: dentelli + fascia modanata ----------------------------
    corn = [(0.0, 5.86), (0.055, 5.90), (0.055, 5.96), (0.13, 6.02),
            (0.13, 6.14), (0.09, 6.20), (0.0, 6.20)]
    band(pietra, corn)

    # dentelli sotto il cornicione
    dz0, dz1 = 5.62, 5.86
    dw, dd = 0.10, 0.075
    for (p0, p1, outv) in (
            (Vector((-HALF_X, -HALF_Y, 0)), Vector((HALF_X, -HALF_Y, 0)), Vector((0, -1, 0))),
            (Vector((-HALF_X, HALF_Y, 0)), Vector((HALF_X, HALF_Y, 0)), Vector((0, 1, 0))),
            (Vector((HALF_X, -HALF_Y, 0)), Vector((HALF_X, HALF_Y, 0)), Vector((1, 0, 0))),
            (Vector((-HALF_X, -HALF_Y, 0)), Vector((-HALF_X, HALF_Y, 0)), Vector((-1, 0, 0)))):
        d = p1 - p0
        L = d.length
        dirv = d / L
        step = 0.26
        count = int(L / step)
        start = (L - (count - 1) * step) / 2.0
        for i in range(count):
            c = p0 + dirv * (start + i * step) + Vector((0, 0, dz0))
            add_box_v(pietra, c - dirv * (dw / 2.0), dirv * dw, outv * dd,
                      Vector((0, 0, dz1 - dz0)))

    # --- cantonali bugnati agli angoli -------------------------------------
    for (cx, cy) in ((-HALF_X, -HALF_Y), (HALF_X, -HALF_Y), (HALF_X, HALF_Y), (-HALF_X, HALF_Y)):
        sx = 1 if cx > 0 else -1
        sy = 1 if cy > 0 else -1
        z = Z_PLINTH
        i = 0
        while z < 5.58:
            h = 0.36
            if z + h > 5.58:
                break
            lung, corto = (0.82, 0.46) if i % 2 == 0 else (0.46, 0.82)
            e = 0.035          # sporgenza del bugnato
            # blocco sulla facciata lunga (direzione X)
            add_box(pietra,
                    (min(cx, cx - sx * lung), min(cy, cy + sy * e), z + 0.02),
                    (max(cx, cx - sx * lung), max(cy, cy + sy * e), z + h - 0.02))
            # blocco sul fianco (direzione Y)
            add_box(pietra,
                    (min(cx, cx + sx * e), min(cy, cy - sy * corto), z + 0.02),
                    (max(cx, cx + sx * e), max(cy, cy - sy * corto), z + h - 0.02))
            z += h
            i += 1

    # --- solai e tramezzi interni (perche' dalle finestre si veda un interno)
    ix0, ix1 = -HALF_X + T_W, HALF_X - T_W
    iy0, iy1 = -HALF_Y + T_W, HALF_Y - T_W
    add_box(interni, (ix0, iy0, 0.20), (ix1, iy1, Z_PLINTH))
    add_box(interni, (ix0, iy0, Z_F1 - 0.24), (ix1, iy1, Z_F1))
    add_box(interni, (ix0, iy0, Z_TOP - 0.24), (ix1, iy1, Z_TOP))
    for (z0, z1) in ((Z_PLINTH, Z_F1 - 0.24), (Z_F1, Z_TOP - 0.24)):
        add_box(interni, (0.55, iy0, z0), (0.67, 1.2, z1))
        add_box(interni, (ix0, 0.9, z0), (0.67, 1.02, z1))
        add_box(interni, (-2.4, iy0, z0), (-2.28, -0.6, z1))


# ---------------------------------------------------------------------------
# Helper in coordinate locali
# ---------------------------------------------------------------------------
def wp(fr, u, z, out=0.0):
    o, ud, vd, n, W = fr
    return o + ud * u + vd * z + n * out


def wbox(buf, fr, u0, u1, z0, z1, o0, o1):
    """Scatola in coordinate muro: u = ascissa sul muro, z = quota,
    o = sporgenza rispetto alla faccia esterna (positiva verso l'esterno)."""
    o, ud, vd, n, W = fr
    p = o + ud * u0 + vd * z0 + n * o0
    add_box_v(buf, p, ud * (u1 - u0), n * (o1 - o0), vd * (z1 - z0))


def lbox(buf, O, eu, et, ez, u0, u1, t0, t1, z0, z1):
    """Scatola in un sistema locale arbitrario (ante, persiane, ...)."""
    p = O + eu * u0 + et * t0 + ez * z0
    add_box_v(buf, p, eu * (u1 - u0), et * (t1 - t0), ez * (z1 - z0))


def add_torus(buf, center, au, av, R, r, nseg=18, nsec=7):
    au, av = Vector(au).normalized(), Vector(av).normalized()
    nrm = au.cross(av).normalized()
    prof = circle_profile(nsec, r)
    frames = []
    for i in range(nseg + 1):
        a = TAU * i / nseg
        rad = au * math.cos(a) + av * math.sin(a)
        frames.append((Vector(center) + rad * R, nrm, rad, 1.0))
    sweep(buf, frames, prof, closed=True, caps=False)


# ---------------------------------------------------------------------------
# Serramenti: finestre, persiane, porte
# ---------------------------------------------------------------------------
SET_BACK = 0.135        # arretramento del telaio dalla faccia esterna


def add_anta(B, fr, u0, u1, z0, z1, out_c, traversi):
    """Anta vetrata con montanti, traversi e vetri."""
    legno, vetro = B["infissi"], B["vetro"]
    s, d = 0.052, 0.044
    o0, o1 = out_c - d / 2.0, out_c + d / 2.0
    wbox(legno, fr, u0, u1, z0, z0 + s, o0, o1)
    wbox(legno, fr, u0, u1, z1 - s, z1, o0, o1)
    wbox(legno, fr, u0, u0 + s, z0 + s, z1 - s, o0, o1)
    wbox(legno, fr, u1 - s, u1, z0 + s, z1 - s, o0, o1)
    cuts = [z0 + s]
    for i in range(1, traversi + 1):
        zc = (z0 + s) + ((z1 - s) - (z0 + s)) * i / float(traversi + 1)
        wbox(legno, fr, u0 + s, u1 - s, zc - 0.021, zc + 0.021, o0, o1)
        cuts.append(zc - 0.021)
        cuts.append(zc + 0.021)
    cuts.append(z1 - s)
    for i in range(0, len(cuts), 2):
        za, zb = cuts[i], cuts[i + 1]
        if zb - za > 0.03:
            wbox(B["vetro"], fr, u0 + s - 0.008, u1 - s + 0.008, za - 0.005, zb + 0.005,
                 out_c - 0.004, out_c + 0.004)


def add_persiana(B, fr, uc, w, z0, z1, side, angle):
    """Persiana alla romana con lamelle inclinate, cardini e maniglietta."""
    legno, ferro = B["persiane"], B["ferro"]
    o, ud, vd, n, W = fr
    ez = vd
    hw = w / 2.0 + 0.035
    h = (z1 - z0) + 0.075
    zb = z0 - 0.038
    s = 1.0 if side > 0 else -1.0
    uh = uc + s * (w / 2.0 + 0.03)
    ew0 = ud * (-s)
    ca, sa = math.cos(angle), math.sin(angle)
    ew = ew0 * ca + n * sa
    et = ew0 * (-sa) + n * ca
    O = o + ud * uh + vd * zb + n * 0.055
    th = 0.034
    mont = 0.085
    rail = 0.105
    # montanti e traversi
    lbox(legno, O, ew, et, ez, 0.0, mont, 0.0, th, 0.0, h)
    lbox(legno, O, ew, et, ez, hw - mont, hw, 0.0, th, 0.0, h)
    lbox(legno, O, ew, et, ez, mont, hw - mont, 0.0, th, 0.0, rail)
    lbox(legno, O, ew, et, ez, mont, hw - mont, 0.0, th, h - rail, h)
    zmid = h * 0.46
    lbox(legno, O, ew, et, ez, mont, hw - mont, 0.0, th, zmid, zmid + 0.11)
    # lamelle
    ang = math.radians(34.0)
    wv = (et * math.sin(ang) - ez * math.cos(ang)) * 0.062
    tv = (et * math.cos(ang) + ez * math.sin(ang)) * 0.011
    for (za, zb_) in ((rail, zmid), (zmid + 0.11, h - rail)):
        nl = max(1, int((zb_ - za) / 0.052))
        for i in range(nl):
            zz = za + 0.035 + i * (zb_ - za - 0.045) / max(1, nl - 1)
            p = O + ew * mont + ez * zz + et * 0.004
            add_box_v(legno, p, ew * (hw - 2 * mont), wv, tv)
    # cardini
    for zz in (0.14, h - 0.14):
        p0 = O + ew * 0.03 + ez * zz
        add_cylinder(ferro, p0 - et * 0.02 - ew * 0.07, p0 + et * 0.035, 0.016, 8)
    # maniglia
    p = O + ew * (hw - 0.05) + ez * (zmid + 0.2) + et * th
    add_cylinder(ferro, p, p + et * 0.055, 0.012, 8)
    add_box_v(ferro, p + et * 0.05 - ew * 0.015 - ez * 0.06,
              ew * 0.03, et * 0.018, ez * 0.14)


def add_cassetta_fiori(B, fr, uc, w, z):
    """Cassetta portafiori in legno con gerani."""
    legno, terra = B["persiane"], B["terra"]
    o, ud, vd, n, W = fr
    u0, u1 = uc - w / 2.0 + 0.06, uc + w / 2.0 - 0.06
    h = 0.20
    for (a, b, c, d) in ((u0, u1, 0.10, 0.125), (u0, u1, 0.36, 0.385)):
        wbox(legno, fr, a, b, z, z + h, c, d)
    wbox(legno, fr, u0, u0 + 0.025, z, z + h, 0.10, 0.385)
    wbox(legno, fr, u1 - 0.025, u1, z, z + h, 0.10, 0.385)
    wbox(legno, fr, u0, u1, z, z + 0.025, 0.10, 0.385)
    wbox(terra, fr, u0 + 0.02, u1 - 0.02, z + h - 0.045, z + h - 0.02, 0.125, 0.36)
    # vegetazione
    nflow = 7
    for i in range(nflow):
        uu = u0 + 0.07 + (u1 - u0 - 0.14) * i / float(nflow - 1) + rr(-0.02, 0.02)
        base = wp(fr, uu, z + h - 0.03, 0.24 + rr(-0.05, 0.05))
        add_sphere(B["foglie"], base + Vector((0, 0, 0.055)), rr(0.075, 0.105), 10, 7,
                   amp=0.4, nscale=6.0, scale=(1.0, 1.0, 0.8), seed_off=rr(0, 20))
        for k in range(2):
            c = base + Vector((rr(-0.07, 0.07), rr(-0.07, 0.07), rr(0.10, 0.17)))
            add_sphere(B["fiori"], c, rr(0.035, 0.055), 8, 6, amp=0.45, nscale=9.0,
                       scale=(1.0, 1.0, 0.75), seed_off=rr(0, 20))


def add_tenda(B, fr, ua, ub, za, zb, stile):
    """Tenda in lino appesa a un bastoncino, con pieghe ondulate.

    stile = "velo"     : un unico telo leggero su tutta la luce
            "laterali" : due teli raccolti ai lati da una fascetta
    """
    tende = B["tende"]
    oc = -T_W + 0.075                       # piano medio della tenda
    zr = zb - 0.035
    add_cylinder(B["ferro"], wp(fr, ua - 0.03, zr, oc), wp(fr, ub + 0.03, zr, oc), 0.009, 6)
    for uu in (ua - 0.03, ub + 0.03):
        add_sphere(B["ottone"], wp(fr, uu, zr, oc), 0.016, 8, 6)
    if stile == "velo":
        teli = [(ua, ub, 0.012, 1.0)]
    else:
        lw = (ub - ua) * 0.34
        teli = [(ua, ua + lw, 0.026, 1.0), (ub, ub - lw, 0.026, 1.0)]
    z_top, z_bot = zr - 0.01, za + 0.03
    H = z_top - z_bot
    for (u_est, u_int, amp, _) in teli:
        span = u_int - u_est
        ncol = max(10, int(abs(span) / 0.010))
        nrow = 14
        ph = rr(0, TAU)
        wl = rr(0.060, 0.080)
        rows = []
        for i in range(nrow + 1):
            t = i / float(nrow)
            z = z_bot + H * t
            if stile == "laterali":
                # strozzatura della fascetta a circa 40% dell'altezza
                g = math.exp(-((t - 0.40) / 0.22) ** 2)
                wfac = 1.0 - 0.55 * g
                a_amp = amp * (1.0 + 0.9 * g)
            else:
                wfac, a_amp = 1.0, amp
            row = []
            for j in range(ncol + 1):
                f = j / float(ncol)
                u = u_est + span * f * wfac
                k = TAU * (abs(span) * f) / wl + ph
                off = a_amp * math.sin(k) * (0.6 + 0.4 * t if stile == "velo" else 1.0)
                row.append(wp(fr, u, z, oc + off))
            rows.append(tende.add(row))
        for i in range(nrow):
            a, b = rows[i], rows[i + 1]
            for j in range(ncol):
                tende.face((a + j, a + j + 1, b + j + 1, b + j), True)
        if stile == "laterali":
            # fascetta che raccoglie il telo
            zt = z_bot + H * 0.40
            uw = abs(span) * 0.45
            u0 = min(u_est, u_est + math.copysign(uw, span))
            wbox(tende, fr, u0, u0 + uw, zt - 0.02, zt + 0.02, oc - 0.05, oc + 0.05)


def build_finestra(B, spec):
    fr = wall_frame(spec["wall"])
    uc, w, z0, z1 = spec["uc"], spec["w"], spec["z0"], spec["z1"]
    o, ud, vd, n, W = fr
    pietra, legno = B["pietra"], B["infissi"]

    # davanzale in pietra, con gocciolatoio e leggera pendenza
    if spec["sill"]:
        p = wp(fr, uc - w / 2.0 - 0.13, z0 - 0.065, -0.14)
        add_box_v(pietra, p, ud * (w + 0.26), n * 0.30 + vd * (-0.022), vd * 0.062)
        p2 = wp(fr, uc - w / 2.0 - 0.10, z0 - 0.088, 0.055)
        add_box_v(pietra, p2, ud * (w + 0.20), n * 0.075, vd * 0.028)

    # mostra/cornice intorno al vano
    if spec["mostra"]:
        mw, mo = 0.14, 0.028
        wbox(pietra, fr, uc - w / 2.0 - mw, uc - w / 2.0, z0 - 0.02, z1 + mw, 0.0, mo)
        wbox(pietra, fr, uc + w / 2.0, uc + w / 2.0 + mw, z0 - 0.02, z1 + mw, 0.0, mo)
        wbox(pietra, fr, uc - w / 2.0 - mw, uc + w / 2.0 + mw, z1, z1 + mw, 0.0, mo)
        # chiave di volta
        wbox(pietra, fr, uc - 0.11, uc + 0.11, z1 - 0.02, z1 + mw + 0.08, 0.0, mo + 0.018)

    # telaio fisso
    t, d = 0.07, 0.085
    o0, o1 = -SET_BACK - d, -SET_BACK
    wbox(legno, fr, uc - w / 2.0, uc + w / 2.0, z1 - t, z1, o0, o1)
    wbox(legno, fr, uc - w / 2.0, uc - w / 2.0 + t, z0, z1 - t, o0, o1)
    wbox(legno, fr, uc + w / 2.0 - t, uc + w / 2.0, z0, z1 - t, o0, o1)
    if spec["kind"] == "finestra":
        wbox(legno, fr, uc - w / 2.0, uc + w / 2.0, z0, z0 + t * 0.7, o0, o1)
        za = z0 + t * 0.7
    else:
        za = z0 + 0.02
    zb = z1 - t
    ua, ub = uc - w / 2.0 + t, uc + w / 2.0 - t
    out_c = -SET_BACK - d / 2.0 + 0.012
    if spec["ante"] == 2:
        um = (ua + ub) / 2.0
        add_anta(B, fr, ua, um + 0.004, za, zb, out_c, spec["traversi"])
        add_anta(B, fr, um - 0.004, ub, za, zb, out_c, spec["traversi"])
        # maniglie
        for s in (-1, 1):
            p = wp(fr, um + s * 0.035, (za + zb) / 2.0, out_c + 0.025)
            add_cylinder(B["ottone"], p, p + n * 0.03, 0.013, 8)
            add_sphere(B["ottone"], p + n * 0.045, 0.019, 8, 6)
    else:
        add_anta(B, fr, ua, ub, za, zb, out_c, spec["traversi"])

    # tende interne: a velo intero oppure a teli laterali raccolti
    tenda = {"aperte": "laterali", "socchiuse": "velo", None: "velo"}.get(spec["shut"])
    if spec["kind"] == "portafinestra":
        tenda = "laterali"
    if tenda:
        add_tenda(B, fr, ua, ub, za, zb, tenda)

    if spec["fiori"]:
        add_cassetta_fiori(B, fr, uc, w, z0 - 0.02)

    ang = {"aperte": math.radians(163.0), "socchiuse": math.radians(38.0),
           "chiuse": 0.0}
    if spec["shut"] in ang:
        a = ang[spec["shut"]]
        for side in (-1, 1):
            jitter = rr(-0.05, 0.05) if a > 0.1 else 0.0
            add_persiana(B, fr, uc, w, z0, z1, side, a + jitter)


def add_pannello_bugnato(buf, O, eu, et, ez, u0, u1, z0, z1, d0, d1):
    """Pannello a bugna con cornicetta (per i battenti del portone)."""
    m = 0.055
    lbox(buf, O, eu, et, ez, u0 + m, u1 - m, d0, d1 + 0.016, z0 + m, z1 - m)
    for (a0, a1, b0, b1) in ((u0, u1, z0, z0 + m), (u0, u1, z1 - m, z1),
                             (u0, u0 + m, z0 + m, z1 - m), (u1 - m, u1, z0 + m, z1 - m)):
        lbox(buf, O, eu, et, ez, a0, a1, d0, d1 + 0.008, b0, b1)


def build_porta(B, spec, principale=False):
    fr = wall_frame(spec["wall"])
    uc, w, z0, z1 = spec["uc"], spec["w"], spec["z0"], spec["z1"]
    o, ud, vd, n, W = fr
    pietra, legno, ott, ferro = B["pietra"], B["legno_porta"], B["ottone"], B["ferro"]

    # portale in pietra
    jw = 0.26 if principale else 0.18
    wbox(pietra, fr, uc - w / 2.0 - jw, uc - w / 2.0, 0.0, z1, 0.0, 0.07)
    wbox(pietra, fr, uc + w / 2.0, uc + w / 2.0 + jw, 0.0, z1, 0.0, 0.07)
    wbox(pietra, fr, uc - w / 2.0 - jw, uc + w / 2.0 + jw, z1, z1 + 0.17, 0.0, 0.085)
    if principale:
        wbox(pietra, fr, uc - w / 2.0 - jw - 0.13, uc + w / 2.0 + jw + 0.13,
             z1 + 0.17, z1 + 0.27, 0.0, 0.135)
        wbox(pietra, fr, uc - 0.13, uc + 0.13, z1 - 0.05, z1 + 0.17, 0.0, 0.105)

    # telaio
    t, d = 0.08, 0.10
    o0, o1 = -SET_BACK - d, -SET_BACK
    wbox(legno, fr, uc - w / 2.0, uc + w / 2.0, z1 - t, z1, o0, o1)
    wbox(legno, fr, uc - w / 2.0, uc - w / 2.0 + t, z0, z1 - t, o0, o1)
    wbox(legno, fr, uc + w / 2.0 - t, uc + w / 2.0, z0, z1 - t, o0, o1)

    ua, ub = uc - w / 2.0 + t, uc + w / 2.0 - t
    zt = z1 - t
    # sopraluce con raggiera
    zs = zt - 0.26
    wbox(legno, fr, ua, ub, zs, zs + 0.06, o0, o1)
    wbox(B["vetro"], fr, ua, ub, zs + 0.05, zt, -SET_BACK - 0.055, -SET_BACK - 0.049)
    nb = 4
    for i in range(1, nb):
        uu = ua + (ub - ua) * i / float(nb)
        wbox(ferro, fr, uu - 0.012, uu + 0.012, zs + 0.05, zt, -SET_BACK - 0.07, -SET_BACK - 0.035)
    wbox(ferro, fr, ua, ub, (zs + zt) / 2.0 - 0.012, (zs + zt) / 2.0 + 0.012,
         -SET_BACK - 0.07, -SET_BACK - 0.035)

    # battenti
    nante = 2 if principale else 1
    zb0, zb1 = z0, zs + 0.05
    th = 0.058
    oc = -SET_BACK - 0.055
    eu, et, ez = ud, n, vd
    for k in range(nante):
        if nante == 2:
            a0 = ua + (ub - ua) * k / 2.0 + (0.004 if k else 0.0)
            a1 = ua + (ub - ua) * (k + 1) / 2.0 - (0.004 if k == 0 else 0.0)
        else:
            a0, a1 = ua + 0.004, ub - 0.004
        O = o + vd * zb0 + n * oc
        lbox(legno, O, eu, et, ez, a0, a1, -th / 2.0, th / 2.0, 0.0, zb1 - zb0)
        hgt = zb1 - zb0
        npan = 3 if principale else 2
        pad = 0.085
        for p_ in range(npan):
            pz0 = pad + (hgt - 2 * pad) * p_ / float(npan) + 0.03
            pz1 = pad + (hgt - 2 * pad) * (p_ + 1) / float(npan) - 0.03
            add_pannello_bugnato(legno, O, eu, et, ez, a0 + pad, a1 - pad,
                                 pz0, pz1, -th / 2.0 - 0.018, th / 2.0)
        # cardini
        hu = a0 if k == 0 else a1
        for zz in (0.22, hgt / 2.0, hgt - 0.22):
            p = O + eu * hu + ez * zz
            add_cylinder(ferro, p - et * 0.03, p + et * 0.05, 0.018, 8)
    # maniglie / battacchio
    um = (ua + ub) / 2.0
    for k in range(nante):
        s = -1 if k == 0 else 1
        uu = (um + s * 0.11) if nante == 2 else (ub - 0.14)
        p = wp(fr, uu, zb0 + 1.02, oc + th / 2.0)
        add_cylinder(ott, p, p + n * 0.07, 0.016, 8)
        add_sphere(ott, p + n * 0.095, 0.036, 12, 8)
        wbox(ott, fr, uu - 0.045, uu + 0.045, zb0 + 0.86, zb0 + 1.18,
             oc + th / 2.0, oc + th / 2.0 + 0.012)
        # bocchetta della serratura
        wbox(ott, fr, uu - 0.022 + s * 0.005, uu + 0.022 + s * 0.005,
             zb0 + 0.90, zb0 + 0.97, oc + th / 2.0, oc + th / 2.0 + 0.009)
    if principale:
        pc = wp(fr, um - 0.33, zb0 + 1.50, oc + th / 2.0 + 0.045)
        add_torus(ott, pc, ud, vd, 0.075, 0.015, 20, 8)
        pp = wp(fr, um - 0.33, zb0 + 1.60, oc + th / 2.0)
        add_sphere(ott, pp + n * 0.035, 0.040, 12, 8)
        add_cylinder(ott, pp, pp + n * 0.04, 0.018, 8)
    # gradinata d'accesso
    nst = 3 if principale else 2
    wsteps = w + 2 * jw + (0.5 if principale else 0.2)
    for i in range(nst):
        zz0 = Z_PLINTH * i / float(nst)
        zz1 = Z_PLINTH * (i + 1) / float(nst)
        dd = (0.34 if principale else 0.30) * (nst - i)
        wbox(pietra, fr, uc - wsteps / 2.0 - 0.06 * (nst - i),
             uc + wsteps / 2.0 + 0.06 * (nst - i), zz0 - 0.001, zz1, 0.0, dd)


# ---------------------------------------------------------------------------
# Balcone, lanterna, dettagli dei timpani
# ---------------------------------------------------------------------------
def build_balcone(B):
    fr = wall_frame("S")
    o, ud, vd, n, W = fr
    pietra, ferro = B["pietra"], B["ferro"]
    uc, bw, bd = 4.50, 3.10, 1.18
    u0, u1 = uc - bw / 2.0, uc + bw / 2.0

    # mensole a voluta
    for du in (-1.22, 0.0, 1.22):
        um = uc + du
        wbox(pietra, fr, um - 0.12, um + 0.12, 3.06, 3.22, 0.0, 0.66)
        wbox(pietra, fr, um - 0.11, um + 0.11, 2.94, 3.06, 0.0, 0.42)
        wbox(pietra, fr, um - 0.10, um + 0.10, 2.82, 2.94, 0.0, 0.22)
        p = wp(fr, um, 3.14, 0.60)
        add_cylinder(pietra, p - ud * 0.12, p + ud * 0.12, 0.075, 12)

    # soletta con gocciolatoio
    wbox(pietra, fr, u0 + 0.04, u1 - 0.04, 3.16, 3.22, 0.0, bd - 0.05)
    wbox(pietra, fr, u0, u1, 3.22, 3.36, 0.0, bd)
    wbox(pietra, fr, u0 + 0.02, u1 - 0.02, 3.36, 3.39, 0.0, bd - 0.02)

    # ringhiera in ferro
    zb, zt = 3.39, 4.37
    ins = 0.07
    a0, a1 = u0 + ins, u1 - ins
    d1 = bd - ins
    corners = [(a0, 0.0), (a0, d1), (a1, d1), (a1, 0.0)]
    # correnti orizzontali
    for (zz, sec) in ((zb + 0.07, 0.030), (zt - 0.06, 0.042), (zt - 0.42, 0.022)):
        wbox(ferro, fr, a0, a1, zz - sec / 2.0, zz + sec / 2.0, d1 - sec / 2.0, d1 + sec / 2.0)
        for uu in (a0, a1):
            wbox(ferro, fr, uu - sec / 2.0, uu + sec / 2.0, zz - sec / 2.0, zz + sec / 2.0,
                 0.0, d1)
    # montanti d'angolo
    for (uu, dd) in corners:
        wbox(ferro, fr, uu - 0.026, uu + 0.026, zb, zt, dd - 0.026, dd + 0.026)
        p = wp(fr, uu, zt + 0.02, dd)
        add_sphere(ferro, p + Vector((0, 0, 0.03)), 0.042, 10, 7)
    # balaustrini
    def balaustri(pa, pb, count):
        for i in range(1, count):
            t = i / float(count)
            uu = pa[0] + (pb[0] - pa[0]) * t
            dd = pa[1] + (pb[1] - pa[1]) * t
            p0 = wp(fr, uu, zb, dd)
            p1 = wp(fr, uu, zt - 0.06, dd)
            add_cylinder(ferro, p0, p1, 0.011, 8)
            if i % 2 == 1:
                add_sphere(ferro, wp(fr, uu, (zb + zt) / 2.0 - 0.18, dd), 0.030, 8, 6,
                           scale=(1.0, 1.0, 1.6))
    balaustri((a0, 0.0), (a0, d1), 10)
    balaustri((a0, d1), (a1, d1), 26)
    balaustri((a1, d1), (a1, 0.0), 10)


def build_lanterna(B, fr, uc, z):
    """Lanterna da esterno in ferro battuto, accesa."""
    ferro, vetro, luce = B["ferro"], B["vetro"], B["luce"]
    o, ud, vd, n, W = fr
    # piastra e braccio
    wbox(ferro, fr, uc - 0.06, uc + 0.06, z + 0.28, z + 0.52, 0.0, 0.03)
    p0 = wp(fr, uc, z + 0.46, 0.02)
    p1 = wp(fr, uc, z + 0.46, 0.30)
    add_cylinder(ferro, p0, p1, 0.016, 8)
    add_cylinder(ferro, p1, p1 - vd * 0.10, 0.016, 8)
    p2 = wp(fr, uc, z + 0.20, 0.30)
    # corpo esagonale
    prof = circle_profile(6, 0.105, phase=math.radians(30))
    base = p2 - vd * 0.02
    frames = [(base, ud, n, 1.0), (base - vd * 0.26, ud, n, 0.86)]
    sweep(ferro, frames, [(p[0], p[1]) for p in prof], closed=True, caps=False)
    pv = circle_profile(6, 0.088, phase=math.radians(30))
    sweep(vetro, [(base - vd * 0.02, ud, n, 1.0), (base - vd * 0.24, ud, n, 0.88)],
          [(p[0], p[1]) for p in pv], closed=True, caps=False)
    add_sphere(luce, base - vd * 0.13, 0.042, 10, 7)
    # tettuccio e pomello
    sweep(ferro, [(base + vd * 0.005, ud, n, 1.22), (base + vd * 0.09, ud, n, 0.25)],
          [(p[0], p[1]) for p in prof], closed=True, caps=False)
    add_sphere(ferro, base + vd * 0.115, 0.026, 8, 6)
    # fondo
    sweep(ferro, [(base - vd * 0.25, ud, n, 0.88), (base - vd * 0.30, ud, n, 0.3)],
          [(p[0], p[1]) for p in prof], closed=True, caps=False)


def build_timpani(B):
    """Occhio in pietra su un timpano, grata di aerazione sull'altro."""
    pietra, legno, ferro = B["pietra"], B["legno"], B["ferro"]
    # occhio (lato Est)
    c = Vector((HALF_X, 0.0, 7.00))
    au, av = Vector((0, 1, 0)), Vector((0, 0, 1))
    prof = [(0.0, -0.17), (0.085, -0.17), (0.085, 0.17), (0.0, 0.17)]
    frames = []
    nseg = 28
    for i in range(nseg + 1):
        a = TAU * i / nseg
        rad = au * math.cos(a) + av * math.sin(a)
        frames.append((c + rad * 0.46 + Vector((0.0, 0, 0)), Vector((1, 0, 0)), rad, 1.0))
    sweep(pietra, frames, ensure_ccw(prof), closed=True, caps=False)
    add_cylinder(B["vetro_scuro"], c + Vector((-0.02, 0, 0)), c + Vector((0.03, 0, 0)), 0.45, 28)
    for a in (0.0, PI / 2.0):
        d = au * math.cos(a) + av * math.sin(a)
        add_cylinder(ferro, c - d * 0.45 + Vector((0.04, 0, 0)),
                     c + d * 0.45 + Vector((0.04, 0, 0)), 0.012, 6)
    # grata di aerazione (lato Ovest)
    fr = (Vector((-HALF_X, HALF_Y - T_W, 0.0)), Vector((0, -1, 0)), Vector((0, 0, 1)),
          Vector((-1, 0, 0)), D_Y - 2 * T_W)
    o, ud, vd, n, W = fr
    uc, zc, gw, gh = 3.15, 6.95, 0.80, 0.56
    wbox(B["vetro_scuro"], fr, uc - gw / 2.0, uc + gw / 2.0, zc - gh / 2.0, zc + gh / 2.0,
         0.0, 0.015)
    for (a0, a1, b0, b1) in ((uc - gw / 2.0 - 0.07, uc + gw / 2.0 + 0.07, zc + gh / 2.0, zc + gh / 2.0 + 0.07),
                             (uc - gw / 2.0 - 0.07, uc + gw / 2.0 + 0.07, zc - gh / 2.0 - 0.07, zc - gh / 2.0),
                             (uc - gw / 2.0 - 0.07, uc - gw / 2.0, zc - gh / 2.0, zc + gh / 2.0),
                             (uc + gw / 2.0, uc + gw / 2.0 + 0.07, zc - gh / 2.0, zc + gh / 2.0)):
        wbox(legno, fr, a0, a1, b0, b1, 0.0, 0.055)
    nl = 7
    for i in range(nl):
        zz = zc - gh / 2.0 + 0.05 + i * (gh - 0.08) / (nl - 1)
        p = o + ud * (uc - gw / 2.0) + vd * zz + n * 0.012
        add_box_v(legno, p, ud * gw, (n * 0.72 - vd * 0.69) * 0.055, (n * 0.69 + vd * 0.72) * 0.014)


# ---------------------------------------------------------------------------
# Tetto: orditura, tavolato, coppi, colmo, gronde, pluviali
# ---------------------------------------------------------------------------
X_RAKE = HALF_X + OVH_RAKE
Y_EAVE = HALF_Y + OVH_EAVE


def _tile_profile(R, t, vscale, a0, a1, nseg=6):
    """Profilo a C (coppo/canale): arco esterno + arco interno, in senso antiorario."""
    pts_o, pts_i = [], []
    for i in range(nseg + 1):
        a = a0 + (a1 - a0) * i / nseg
        pts_o.append((R * math.cos(a), R * vscale * math.sin(a)))
        pts_i.append(((R - t) * math.cos(a), (R - t) * vscale * math.sin(a)))
    return ensure_ccw(pts_o + pts_i[::-1])


# canale (tegola concava verso l'alto)
R_CAN, V_CAN = 0.092, 0.80
PROF_CAN = _tile_profile(R_CAN, 0.013, V_CAN, math.radians(205), math.radians(335), 6)
CAN_H = R_CAN * V_CAN            # altezza del centro sopra il piano di posa
# coppo (tegola convessa verso l'alto)
R_COP, V_COP = 0.098, 0.70
PROF_COP = _tile_profile(R_COP, 0.013, V_COP, math.radians(18), math.radians(162), 6)
COP_H = 0.030

STEP_X = 0.178                   # interasse delle file di coppi
EXPO = 0.285                     # scoprimento (passo lungo la falda)
TILE_L = 0.40


def place_tile(buf, origin, ex, es, en, profile, base_h, length, scale_top=0.9):
    """Posa una tegola: origin = punto di gronda sul piano di posa,
    ex = trasversale, es = su falda, en = normale al tetto."""
    rot = rr(-0.022, 0.022)
    exr = (ex * math.cos(rot) + es * math.sin(rot)).normalized()
    esr = (es * math.cos(rot) - ex * math.sin(rot)).normalized()
    sc = rr(0.97, 1.02)
    o0 = origin + en * (base_h + rr(-0.002, 0.004))
    top = o0 + esr * length
    f_bot = (o0, exr, en, (sc, sc))
    f_top = (top, exr, en, (sc * scale_top, sc * scale_top))
    frames = [f_bot, f_top] if exr.cross(en).dot(esr) > 0 else [f_top, f_bot]
    buf.color = jitter_color(srgb(160, 74, 40), 0.38)
    sweep(buf, frames, profile, closed=True, caps=True)


def build_tetto(B):
    legno, cotto, ferro, zinco = B["legno"], B["cotto"], B["ferro"], B["zinco"]

    for sgn in (-1, 1):
        ey = sgn * Y_EAVE
        es = Vector((0.0, -sgn * COSP, math.sin(PITCH)))           # verso il colmo
        en = Vector((0.0, sgn * math.sin(PITCH), COSP))            # normale esterna
        ex = Vector((1.0, 0.0, 0.0))
        L = Y_EAVE / COSP
        eave = Vector((0.0, ey, roof_z(Y_EAVE)))

        # travetti
        nt = int((2 * X_RAKE) / 0.52) + 1
        for i in range(nt):
            x = -X_RAKE + 0.06 + i * (2 * X_RAKE - 0.12) / (nt - 1)
            p = eave + Vector((x - 0.045, 0, 0))
            add_box_v(legno, p, ex * 0.09, es * L, -en * 0.13)
        # arcarecci sporgenti e trave di colmo
        for yy in (-1.95, 1.95):
            if yy * sgn < 0:
                continue
            ztop = roof_z(yy) - 0.13
            add_box(legno, (-X_RAKE, yy - 0.09, ztop - 0.22), (X_RAKE, yy + 0.09, ztop))
        if sgn < 0:
            ztop = roof_z(0.0) - 0.13
            add_box(legno, (-X_RAKE, -0.11, ztop - 0.27), (X_RAKE, 0.11, ztop))
        # tavolato
        nb = int(L / 0.246) + 1
        for i in range(nb):
            s0 = i * 0.246
            ln = min(0.24, L - s0)
            if ln < 0.03:
                break
            p = eave + es * s0 + Vector((-X_RAKE, 0, 0))
            add_box_v(legno, p, ex * (2 * X_RAKE), es * ln, en * 0.035)
        # frontalino di gronda
        p = eave + Vector((-X_RAKE, 0, 0)) - en * 0.135
        add_box_v(legno, p, ex * (2 * X_RAKE), es * 0.032, Vector((0, 0, 0.21)))
        # tavole di bordo sui timpani
        for sx in (-1, 1):
            p = eave + Vector((sx * X_RAKE - (0.03 if sx > 0 else 0.0), 0, 0)) + en * 0.036
            add_box_v(legno, p, ex * 0.03, es * L, -en * 0.20)

        # --- coppi -------------------------------------------------------
        ncol = int((2 * X_RAKE) / STEP_X)
        x0 = -X_RAKE + ((2 * X_RAKE) - (ncol - 1) * STEP_X) / 2.0
        nrow = int((L + 0.10 - TILE_L) / EXPO) + 1
        plane0 = eave + en * 0.035          # piano di posa (estradosso tavolato)
        for r in range(nrow):
            s = -0.085 + r * EXPO
            for c in range(ncol):
                x = x0 + c * STEP_X + rr(-0.004, 0.004)
                org = plane0 + ex * x + es * (s + rr(-0.006, 0.006))
                place_tile(cotto, org, ex, es, en, PROF_CAN, CAN_H, TILE_L, 0.9)
            for c in range(ncol + 1):
                x = x0 + (c - 0.5) * STEP_X + rr(-0.004, 0.004)
                org = plane0 + ex * x + es * (s + 0.01 + rr(-0.006, 0.006))
                place_tile(cotto, org, ex, es, en, PROF_COP, COP_H, TILE_L - 0.01, 0.9)

        # --- grondaia ----------------------------------------------------
        gy = ey + sgn * 0.055
        gz = roof_z(Y_EAVE) - 0.075
        gp = []
        n_arc = 10
        for i in range(n_arc + 1):
            a = math.radians(190) + math.radians(160) * i / n_arc
            gp.append((0.075 * math.cos(a), 0.075 * math.sin(a)))
        for i in range(n_arc, -1, -1):
            a = math.radians(190) + math.radians(160) * i / n_arc
            gp.append((0.068 * math.cos(a), 0.068 * math.sin(a)))
        gp = ensure_ccw(gp)
        gf = [(Vector((-X_RAKE - 0.04, gy, gz)), Vector((0, 1, 0)), Vector((0, 0, 1)), 1.0),
              (Vector((X_RAKE + 0.04, gy, gz)), Vector((0, 1, 0)), Vector((0, 0, 1)), 1.0)]
        sweep(zinco, gf, gp, closed=True, caps=True)
        # staffe
        ns = int((2 * X_RAKE) / 0.75)
        for i in range(ns + 1):
            x = -X_RAKE + i * (2 * X_RAKE) / ns
            add_box(zinco, (x - 0.02, min(ey, gy) - 0.09, gz - 0.10),
                    (x + 0.02, max(ey, gy) + 0.02, gz - 0.07))
            add_box(zinco, (x - 0.02, ey - 0.03 * sgn, gz - 0.10),
                    (x + 0.02, ey + 0.03 * sgn, gz + 0.16))

    # --- pluviali ---------------------------------------------------------
    for (sx, sy) in ((-1, -1), (1, 1)):
        gy = sy * (Y_EAVE + 0.055)
        gz = roof_z(Y_EAVE) - 0.075
        # sul cantonale d'angolo: cosi' le persiane aperte della finestra
        # vicina non urtano il tubo
        x = sx * (HALF_X - 0.22)
        wy = sy * (HALF_Y + 0.13)
        pts = [Vector((x, gy, gz - 0.02)), Vector((x, gy, gz - 0.32)),
               Vector((x, wy, gz - 0.72)), Vector((x, wy, 0.52)),
               Vector((x, sy * (HALF_Y + 0.34), 0.20))]
        for i in range(len(pts) - 1):
            add_cylinder(zinco, pts[i], pts[i + 1], 0.045, 10)
            add_sphere(zinco, pts[i + 1], 0.05, 10, 7)
        for zz in (1.1, 2.6, 4.2, 5.4):
            add_box(zinco, (x - 0.02, min(wy, sy * HALF_Y), zz - 0.02),
                    (x + 0.02, max(wy, sy * HALF_Y), zz + 0.02))
            add_torus(zinco, Vector((x, wy, zz)), (1, 0, 0), (0, 1, 0), 0.05, 0.008, 14, 5)
        # pozzetto con griglia sotto la scarpa del pluviale
        yc = sy * (HALF_Y + 0.40)
        add_box(B["pietra"], (x - 0.17, yc - 0.17, -0.05), (x + 0.17, yc + 0.17, 0.05))
        for k in range(5):
            xx = x - 0.10 + k * 0.05
            add_box(ferro, (xx - 0.008, yc - 0.12, 0.05), (xx + 0.008, yc + 0.12, 0.058))


def build_colmo(B):
    """Coppi di colmo lungo la linea di cresta."""
    cotto = B["cotto"]
    zb = plank_z(0.0) + 0.052
    ey, ez = Vector((0, 1, 0)), Vector((0, 0, 1))
    n = int((2 * X_RAKE) / 0.30)
    for i in range(n + 1):
        x = -X_RAKE + i * (2 * X_RAKE) / n
        o = Vector((x, rr(-0.006, 0.006), zb + rr(-0.004, 0.004)))
        cotto.color = jitter_color(srgb(158, 76, 42), 0.28)
        sc = rr(0.97, 1.02)
        frames = [(o, ey, ez, (1.34 * sc, 1.34 * sc)),
                  (o + Vector((0.42, 0, 0)), ey, ez, (1.24 * sc, 1.24 * sc))]
        sweep(cotto, frames, PROF_COP, closed=True, caps=True)


def build_comignolo(B):
    """Comignolo in mattoni con mitra in cotto."""
    mat, cotto, buio = B["mattoni"], B["terracotta"], B["buio"]
    cx, cy = 2.40, 1.30
    half = 0.40
    z0 = 7.05
    z_top = 9.05
    bh = 0.072                     # altezza del corso
    bl = 0.255                     # lunghezza del mattone
    z = z0
    row = 0
    while z < z_top:
        off = (bl / 2.0) if row % 2 else 0.0
        for side in range(4):
            if side == 0:
                a, b = Vector((cx - half, cy - half, z)), Vector((1, 0, 0))
                nrm = Vector((0, 1, 0))
            elif side == 1:
                a, b = Vector((cx + half, cy - half, z)), Vector((0, 1, 0))
                nrm = Vector((-1, 0, 0))
            elif side == 2:
                a, b = Vector((cx + half, cy + half, z)), Vector((-1, 0, 0))
                nrm = Vector((0, -1, 0))
            else:
                a, b = Vector((cx - half, cy + half, z)), Vector((0, -1, 0))
                nrm = Vector((1, 0, 0))
            L = 2 * half
            t = -off
            while t < L - 0.02:
                ln = min(bl, L - t) if t >= 0 else min(bl + t, L)
                st = max(t, 0.0)
                if ln > 0.03:
                    mat.color = jitter_color(srgb(158, 86, 60), 0.3)
                    add_box_v(mat, a + b * st + Vector((0, 0, 0.006)),
                              b * (ln - 0.012), nrm * 0.125, Vector((0, 0, bh - 0.012)))
                t += bl
        z += bh
        row += 1
    # cornice a sbalzo
    for (e, zz, hh) in ((0.055, z, 0.075), (0.10, z + 0.075, 0.075)):
        mat.color = srgb(150, 82, 56)
        add_box(mat, (cx - half - e, cy - half - e, zz), (cx + half + e, cy + half + e, zz + hh))
    ztop = z + 0.15
    add_box(buio, (cx - half + 0.12, cy - half + 0.12, z0), (cx + half - 0.12, cy + half - 0.12, ztop + 0.3))
    # mitra: pilastrini + lastra
    for (dx, dy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        add_box(cotto, (cx + dx * (half + 0.04) - 0.09 if dx > 0 else cx + dx * (half + 0.04),
                        cy + dy * (half + 0.04) - 0.09 if dy > 0 else cy + dy * (half + 0.04),
                        ztop),
                (cx + dx * (half + 0.04) + 0.09 if dx < 0 else cx + dx * (half + 0.04),
                 cy + dy * (half + 0.04) + 0.09 if dy < 0 else cy + dy * (half + 0.04),
                 ztop + 0.30))
    add_box(cotto, (cx - half - 0.18, cy - half - 0.18, ztop + 0.30),
            (cx + half + 0.18, cy + half + 0.18, ztop + 0.38))
    add_box(cotto, (cx - half - 0.12, cy - half - 0.12, ztop + 0.38),
            (cx + half + 0.12, cy + half + 0.12, ztop + 0.44))


# ---------------------------------------------------------------------------
# Ambiente: terreno, erba, vialetto, siepi, cipressi, vasi
# ---------------------------------------------------------------------------
TERR_R = 170.0


def terrain_z(x, y):
    d = math.hypot(x / 1.25, y / 1.25)
    flat = clamp((d - 7.2) / 6.5, 0.0, 1.0)
    n1 = noise.noise(Vector((x * 0.022, y * 0.022, 3.1))) * 2.6
    n2 = noise.noise(Vector((x * 0.075, y * 0.075, 7.7))) * 0.55
    n3 = noise.noise(Vector((x * 0.30, y * 0.30, 1.3))) * 0.08
    # colline lontane che chiudono l'orizzonte
    dd = math.hypot(x, y)
    far = clamp((dd - 36.0) / 70.0, 0.0, 1.0)
    far = far * far * (3.0 - 2.0 * far)
    hill = ((noise.noise(Vector((x * 0.0105, y * 0.0105, 11.3))) * 0.5 + 0.55) * 17.0
            + noise.noise(Vector((x * 0.035, y * 0.035, 4.2))) * 2.4)
    return (n1 + n2 + n3) * flat - 0.03 + far * max(0.0, hill)


def build_terreno(B):
    """Terreno a maglia polare: fitta vicino alla casa, rada all'orizzonte."""
    terra = B["prato"]
    radii = [0.0]
    r = 0.0
    while r < 17.0:
        r += 0.55
        radii.append(r)
    step = 0.9
    while r < TERR_R:
        step *= 1.13
        r += step
        radii.append(min(r, TERR_R))
    segs = 168
    rings = []
    for r in radii:
        row = []
        for j in range(segs):
            a = TAU * j / segs
            x, y = math.cos(a) * r, math.sin(a) * r
            row.append(Vector((x, y, terrain_z(x, y) if r > 0.01 else -0.03)))
        rings.append(terra.add(row))
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for j in range(segs):
            k = (j + 1) % segs
            terra.face((a + j, a + k, b + k, b + j), True)


MARC_W = 0.70           # larghezza del marciapiede perimetrale
MARC_Z = 0.035          # quota del piano di calpestio del marciapiede


def build_marciapiede(B):
    """Marciapiede perimetrale in lastre di pietra con fughe, che raccorda la
    casa al prato (le lastre hanno quota e colore leggermente variati)."""
    sasso = B["lastre"]
    gap = 0.012

    def lastra(x0, x1, y0, y1):
        sasso.color = jitter_color(srgb(166, 158, 144), 0.12)
        zt = MARC_Z + rr(-0.004, 0.004)
        add_box(sasso, (x0 + gap / 2, y0 + gap / 2, -0.10), (x1 - gap / 2, y1 - gap / 2, zt))

    def fila(a0, a1, b0, b1, lungo_x):
        L = a1 - a0
        n = max(1, int(round(L / 0.58)))
        cuts = [a0] + [a0 + L * i / n + rr(-0.05, 0.05) for i in range(1, n)] + [a1]
        for i in range(n):
            if lungo_x:
                lastra(cuts[i], cuts[i + 1], b0, b1)
            else:
                lastra(b0, b1, cuts[i], cuts[i + 1])

    X0, X1 = -HALF_X - MARC_W, HALF_X + MARC_W
    fila(X0, X1, -HALF_Y - MARC_W, -HALF_Y, True)             # fronte (Sud)
    fila(X0, X1, HALF_Y, HALF_Y + MARC_W, True)               # retro (Nord)
    fila(-HALF_Y, HALF_Y, HALF_X, HALF_X + MARC_W, False)     # Est
    fila(-HALF_Y, HALF_Y, -HALF_X - MARC_W, -HALF_X, False)   # Ovest
    # cordolo esterno in pietra
    c = 0.07
    for (a, b_) in (((X0 - c, -HALF_Y - MARC_W - c), (X1 + c, -HALF_Y - MARC_W)),
                    ((X0 - c, HALF_Y + MARC_W), (X1 + c, HALF_Y + MARC_W + c)),
                    ((X0 - c, -HALF_Y - MARC_W), (X0, HALF_Y + MARC_W)),
                    ((X1, -HALF_Y - MARC_W), (X1 + c, HALF_Y + MARC_W))):
        sasso.color = jitter_color(srgb(150, 144, 132), 0.08)
        add_box(sasso, (a[0], a[1], -0.10), (b_[0], b_[1], MARC_Z + 0.012))


def build_vialetto(B):
    """Vialetto in lastre di pietra irregolari davanti all'ingresso."""
    sasso = B["lastre"]
    y = -4.66
    while y > -11.5:
        w = 1.75 if y > -9.0 else 1.5
        nst = 3
        for i in range(nst):
            cx = -w / 2.0 + (i + 0.5) * (w / nst) + rr(-0.05, 0.05)
            cy = y - rr(0.0, 0.06)
            sx = (w / nst) * rr(0.76, 0.92)
            sy = rr(0.34, 0.46)
            zz = terrain_z(cx, cy)
            a = rr(-0.18, 0.18)
            rot = Matrix.Rotation(a, 3, 'Z')
            sasso.color = jitter_color(srgb(158, 152, 140), 0.16)
            add_box_c(sasso, (cx, cy, zz + 0.015), (sx, sy, 0.10), rot)
        y -= 0.52 + rr(0.0, 0.05)
    # ghiaia ai bordi
    for i in range(320):
        t = rr(0.0, 1.0)
        yy = -4.62 - t * 6.9
        side = 1 if random.random() < 0.5 else -1
        xx = side * (0.92 + rr(0.0, 0.42))
        zz = terrain_z(xx, yy)
        sasso.color = jitter_color(srgb(150, 144, 132), 0.2)
        add_box_c(sasso, (xx, yy, zz + 0.012), (rr(0.06, 0.13), rr(0.06, 0.13), 0.05),
                  Matrix.Rotation(rr(0, TAU), 3, 'Z'))


def build_erba(B, count=22000):
    """Ciuffi d'erba: 4-7 lamine piegate a raggiera da un unico cespo,
    piu' fitti vicino alla casa, con qualche filo secco."""
    erba = B["erba"]
    placed = 0
    guard = 0
    while placed < count and guard < count * 6:
        guard += 1
        a = rr(0, TAU)
        r = (random.random() ** 0.62) * 19.0
        x, y = math.cos(a) * r, math.sin(a) * r
        if abs(x) < HALF_X + MARC_W + 0.05 and abs(y) < HALF_Y + MARC_W + 0.05:
            continue
        if abs(x) < 1.35 and -11.8 < y < -3.5:
            continue
        z = terrain_z(x, y)
        segs = 3 if r < 6.5 else 2
        secca = random.random() < 0.12
        hbase = rr(0.10, 0.30)
        for _ in range(random.randint(4, 7)):
            if secca and random.random() < 0.6:
                erba.color = (rr(0.95, 1.0), rr(0.82, 0.9), rr(0.42, 0.55))
            else:
                k = rr(0.62, 0.92)
                erba.color = (k * rr(0.85, 1.0), k, k * rr(0.75, 1.0))
            ang = rr(0, TAU)
            d = Vector((math.cos(ang), math.sin(ang), 0.0))
            side = Vector((-d.y, d.x, 0.0))
            p = Vector((x, y, z)) + d * rr(0.0, 0.035)
            h = hbase * rr(0.7, 1.25)
            wdt = rr(0.010, 0.018)
            bend = rr(0.2, 0.8)
            bi = erba.add([p - side * (wdt / 2.0), p + side * (wdt / 2.0)])
            for s_ in range(1, segs + 1):
                t = s_ / float(segs)
                off = d * (h * bend * t * t)
                w2 = wdt * (1.0 - 0.85 * t)
                c = p + Vector((off.x, off.y, h * t - h * 0.12 * t * t))
                ni = erba.add([c - side * (w2 / 2.0), c + side * (w2 / 2.0)])
                erba.face((bi, bi + 1, ni + 1, ni), True)
                bi = ni
        placed += 1


def add_foglia(buf, p, nrm, up, size, aspect=0.45):
    """Foglia a losanga, piegata lungo la nervatura centrale (2 triangoli)."""
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


def tinta_foglia():
    """Moltiplicatore di colore per foglia: verdi variati, qualche foglia ingiallita."""
    q = random.random()
    if q < 0.07:
        return (1.0, rr(0.85, 0.95), rr(0.45, 0.6))
    if q < 0.22:
        k = rr(0.55, 0.7)
        return (k, k * rr(1.0, 1.08), k * rr(0.85, 1.0))
    return (rr(0.75, 0.95), rr(0.85, 1.0), rr(0.7, 0.95))


def build_cespuglio(B, c, r, n=4, col="siepe", leaf=0.085, dens=560.0, max_leaves=7500):
    """Cespuglio: nucleo a masse irregolari (in ombra) rivestito di foglie."""
    buf = B[col]
    c = Vector(c)
    blobs = []
    for i in range(n):
        off = Vector((rr(-r * 0.55, r * 0.55), rr(-r * 0.55, r * 0.55), rr(-r * 0.2, r * 0.35)))
        rad = r * rr(0.6, 0.85)
        sz = rr(0.75, 1.0)
        so = rr(0, 50)
        buf.color = (0.40, 0.44, 0.38)
        add_sphere(buf, c + off, rad * 0.94, 14, 9, amp=0.33, nscale=5.0,
                   scale=(1.0, 1.0, sz), seed_off=so)
        blobs.append((c + off, rad, sz, so))
    if leaf <= 0.0:
        return
    area = sum(4.0 * PI * b[1] * b[1] for b in blobs)
    nl = min(max_leaves, int(area * dens))
    zmin = terrain_z(c.x, c.y) + 0.03
    for k in range(nl):
        cc, rad, sz, so = blobs[random.randrange(len(blobs))]
        d = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1)))
        if d.length < 1e-6:
            continue
        d.normalize()
        if d.z < -0.4:
            d.z = -d.z
        nz = noise.noise(d * 5.0 + Vector((so, so, so)))
        rs = rad * (1.0 + 0.33 * nz) * rr(0.97, 1.07)
        p = cc + Vector((d.x * rs, d.y * rs, d.z * rs * sz))
        if p.z < zmin:
            continue
        # scarta le foglie che finirebbero sepolte dentro un'altra massa
        sepolta = False
        for (c2, r2, s2, _) in blobs:
            if c2 is cc:
                continue
            q = p - c2
            if (q.x * q.x + q.y * q.y + (q.z / s2) ** 2) < (r2 * 0.78) ** 2:
                sepolta = True
                break
        if sepolta:
            continue
        nrm = (d + Vector((rr(-0.5, 0.5), rr(-0.5, 0.5), rr(-0.2, 0.6)))).normalized()
        buf.color = tinta_foglia()
        add_foglia(buf, p, nrm, Vector((0, 0, 1)), leaf * rr(0.75, 1.25))


def build_cipresso(B, x, y, h=6.6, rametti=0):
    chioma, legno = B["cipresso"], B["legno"]
    chioma.color = (0.5, 0.54, 0.5) if rametti else (1.0, 1.0, 1.0)
    z0 = terrain_z(x, y)
    add_cylinder(legno, (x, y, z0 - 0.1), (x, y, z0 + 0.7), 0.1, 10)
    R = h * 0.115
    rings = 26
    segs = 18
    grid = []
    for i in range(rings + 1):
        t = i / float(rings)
        rad = R * (1.0 - t ** 2.3) * min(1.0, 3.4 * t + 0.10)
        row = []
        for j in range(segs):
            a = TAU * j / segs
            d = Vector((math.cos(a), math.sin(a), 0.0))
            nz = noise.noise(Vector((math.cos(a) * 2.2, math.sin(a) * 2.2, t * 7.0 + x)))
            rr_ = max(0.01, rad * (1.0 + 0.22 * nz))
            row.append(Vector((x + d.x * rr_, y + d.y * rr_, z0 + 0.45 + t * h)))
        grid.append(row)
    idx = [chioma.add(row) for row in grid]
    for i in range(rings):
        a, b = idx[i], idx[i + 1]
        for j in range(segs):
            k = (j + 1) % segs
            chioma.face((a + j, a + k, b + k, b + j), True)
    # rametti: piccole squame allungate rivolte verso l'alto
    for _ in range(rametti):
        t = rr(0.02, 0.97)
        a = rr(0, TAU)
        rad = R * (1.0 - t ** 2.3) * min(1.0, 3.4 * t + 0.10)
        nz = noise.noise(Vector((math.cos(a) * 2.2, math.sin(a) * 2.2, t * 7.0 + x)))
        rad = max(0.01, rad * (1.0 + 0.22 * nz)) * rr(0.98, 1.06)
        d = Vector((math.cos(a), math.sin(a), 0.0))
        p = Vector((x + d.x * rad, y + d.y * rad, z0 + 0.45 + t * h))
        nrm = (d + Vector((rr(-0.4, 0.4), rr(-0.4, 0.4), rr(0.1, 0.7)))).normalized()
        chioma.color = tinta_foglia()
        add_foglia(chioma, p, nrm, Vector((0, 0, 1)), rr(0.09, 0.15), 0.32)


def build_albero(B, x, y, h=7.0, seed=0, foglie=2500):
    """Albero a foglia larga: tronco, branche e chioma a masse irregolari,
    rivestita di foglie (grandi, pensate per la visione da lontano)."""
    legno, chioma = B["legno"], B["chioma"]
    masse = []
    z0 = terrain_z(x, y)
    base = Vector((x, y, z0 - 0.2))
    trunk_h = h * 0.42
    lean = Vector((rr(-0.25, 0.25), rr(-0.25, 0.25), 0.0))
    top = base + Vector((0, 0, trunk_h)) + lean
    prof = circle_profile(10, 1.0)
    frames = [(base, Vector((1, 0, 0)), Vector((0, 1, 0)), h * 0.052),
              (base + Vector((0, 0, trunk_h * 0.35)) + lean * 0.3, Vector((1, 0, 0)),
               Vector((0, 1, 0)), h * 0.040),
              (top, Vector((1, 0, 0)), Vector((0, 1, 0)), h * 0.033)]
    sweep(legno, frames, prof, closed=True, caps=False)
    for i in range(5):
        a = TAU * i / 5.0 + rr(-0.3, 0.3)
        d = Vector((math.cos(a), math.sin(a), rr(0.9, 1.6))).normalized()
        e = top + d * (h * rr(0.22, 0.33))
        add_cylinder(legno, top, e, h * 0.016, 7)
        masse.append((e + d * h * 0.07, h * rr(0.14, 0.2), 3.6, 0.85, rr(0, 40) + seed))
    for i in range(4):
        c = top + Vector((rr(-0.9, 0.9), rr(-0.9, 0.9), h * rr(0.18, 0.42)))
        masse.append((c, h * rr(0.15, 0.22), 3.4, 0.82, rr(0, 40) + seed))
    chioma.color = (0.5, 0.54, 0.48) if foglie else (1.0, 1.0, 1.0)
    for (c, rad, ns, sz, so) in masse:
        add_sphere(chioma, c, rad, 16, 11, amp=0.34, nscale=ns, scale=(1.0, 1.0, sz),
                   seed_off=so)
    for _ in range(foglie):
        c, rad, ns, sz, so = masse[random.randrange(len(masse))]
        d = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1)))
        if d.length < 1e-6:
            continue
        d.normalize()
        nz = noise.noise(d * ns + Vector((so, so, so)))
        rs = rad * (1.0 + 0.34 * nz) * rr(0.98, 1.10)
        p = c + Vector((d.x * rs, d.y * rs, d.z * rs * sz))
        nrm = (d + Vector((rr(-0.6, 0.6), rr(-0.6, 0.6), rr(-0.2, 0.6)))).normalized()
        chioma.color = tinta_foglia()
        add_foglia(chioma, p, nrm, Vector((0, 0, 1)), h * rr(0.035, 0.05))


def build_vaso(B, x, y, scale=1.0, z0=None):
    """Vaso in cotto con geranio."""
    cotto, terra = B["terracotta"], B["terra"]
    if z0 is None:
        z0 = terrain_z(x, y)
    nseg = 16
    hs = 0.42 * scale
    rings = [(0.0, 0.17), (0.08, 0.182), (0.74, 0.248), (0.86, 0.252),
             (0.88, 0.283), (1.0, 0.283)]
    frames = []
    for (t, r) in rings:
        frames.append((Vector((x, y, z0 + t * hs)), Vector((1, 0, 0)), Vector((0, 1, 0)),
                       r * scale))
    prof = circle_profile(nseg, 1.0)
    sweep(cotto, frames, prof, closed=True, caps=False)
    # bordo interno e terriccio
    frames2 = [(Vector((x, y, z0 + hs)), Vector((1, 0, 0)), Vector((0, 1, 0)), 0.265 * scale),
               (Vector((x, y, z0 + hs - 0.06)), Vector((1, 0, 0)), Vector((0, 1, 0)), 0.245 * scale)]
    sweep(cotto, frames2, prof, closed=True, caps=False)
    add_cylinder(terra, (x, y, z0 + hs - 0.10), (x, y, z0 + hs - 0.055), 0.245 * scale, nseg)
    for i in range(6):
        c = Vector((x + rr(-0.16, 0.16), y + rr(-0.16, 0.16), z0 + hs + rr(0.05, 0.16)))
        add_sphere(B["foglie"], c, rr(0.09, 0.14), 10, 7, amp=0.38, nscale=6.0,
                   scale=(1.0, 1.0, 0.8), seed_off=rr(0, 30))
    for i in range(4):
        c = Vector((x + rr(-0.14, 0.14), y + rr(-0.14, 0.14), z0 + hs + rr(0.18, 0.30)))
        add_sphere(B["fiori"], c, rr(0.045, 0.065), 8, 6, amp=0.4, nscale=8.0,
                   scale=(1.0, 1.0, 0.8), seed_off=rr(0, 30))


def build_sfondo(B):
    """Paesaggio di fondo: filari di cipressi e macchie d'alberi sulle colline
    (sfumati dalla foschia) per chiudere l'orizzonte dietro la casa."""
    # filari di cipressi lungo strade bianche immaginarie
    for (x0, y0, ang, n, passo) in ((22.0, 52.0, 0.35, 9, 6.5), (-30.0, 70.0, -0.2, 11, 7.0),
                                    (58.0, 30.0, 1.25, 8, 6.0), (70.0, 92.0, 0.6, 10, 7.5),
                                    (-6.0, 112.0, 0.05, 12, 8.0)):
        d = Vector((math.cos(ang), math.sin(ang), 0.0))
        for i in range(n):
            x = x0 + d.x * passo * i + rr(-0.6, 0.6)
            y = y0 + d.y * passo * i + rr(-0.6, 0.6)
            build_cipresso(B, x, y, rr(6.5, 9.5))
    # macchie di alberi a foglia larga e cipressi sparsi
    for i in range(46):
        a = math.radians(rr(-5.0, 125.0))
        dist = rr(50.0, 135.0)
        x, y = math.cos(a) * dist, math.sin(a) * dist
        if random.random() < 0.35:
            build_cipresso(B, x, y, rr(6.0, 9.0))
        else:
            build_albero(B, x, y, rr(6.5, 10.5), int(rr(0, 99)), foglie=1300)
            if random.random() < 0.5:
                build_albero(B, x + rr(-5, 5), y + rr(-5, 5), rr(5.5, 9.0), int(rr(0, 99)),
                             foglie=1100)


def build_giardino(B):
    build_terreno(B)
    build_marciapiede(B)
    build_vialetto(B)
    # siepi lungo la facciata (fuori dal marciapiede)
    for x in (-3.55, -2.05):
        build_cespuglio(B, (x, -4.78 + rr(-0.1, 0.1), terrain_z(x, -4.8) + 0.38), 0.75, 4)
    for x in (2.15, 3.65):
        build_cespuglio(B, (x, -4.78 + rr(-0.1, 0.1), terrain_z(x, -4.8) + 0.34), 0.7, 4)
    build_cespuglio(B, (-6.0, -2.2, terrain_z(-6.0, -2.2) + 0.45), 0.9, 5)
    build_cespuglio(B, (6.05, -1.4, terrain_z(6.05, -1.4) + 0.42), 0.85, 5)
    build_cespuglio(B, (-6.5, 2.4, terrain_z(-6.5, 2.4) + 0.5), 1.0, 5)
    build_cipresso(B, 7.6, -6.2, 7.1, rametti=9000)
    build_cipresso(B, 9.0, -4.4, 6.0, rametti=7000)
    build_cipresso(B, -9.4, 2.2, 6.6, rametti=7000)
    # vegetazione di sfondo
    for (bx, by, bh) in ((-21.0, -14.0, 5.6), (-26.0, -4.0, 6.4), (24.0, -18.0, 6.0),
                         (30.0, 4.0, 5.2), (-32.0, 12.0, 6.8), (18.0, 16.0, 5.8)):
        build_cipresso(B, bx, by, bh, rametti=2500)
    for i in range(26):
        a = rr(0, TAU)
        d = rr(16.0, 40.0)
        bx, by = math.cos(a) * d, math.sin(a) * d
        build_cespuglio(B, (bx, by, terrain_z(bx, by) + rr(0.5, 1.1)), rr(0.9, 1.9), 4,
                        leaf=0.17, dens=95.0, max_leaves=3000)
    build_albero(B, 12.2, -13.0, 8.2, 3)
    build_albero(B, -17.5, -6.0, 7.0, 11)
    build_sfondo(B)
    # gerani in vaso ai lati della gradinata, appoggiati sul marciapiede
    build_vaso(B, -1.66, -3.93, 1.0, z0=MARC_Z)
    build_vaso(B, 1.66, -3.93, 1.0, z0=MARC_Z)


# ---------------------------------------------------------------------------
# Assemblaggio della scena
# ---------------------------------------------------------------------------
BUF_SPEC = [
    # chiave,        nome oggetto,           collezione,   colore per vertice
    ("muri",         "Muratura",             "Edificio",   False),
    ("interni",      "Solai_e_tramezzi",     "Edificio",   False),
    ("pietra",       "Pietre_lavorate",      "Edificio",   False),
    ("infissi",      "Infissi",              "Serramenti", False),
    ("vetro",        "Vetri",                "Serramenti", False),
    ("vetro_scuro",  "Vetri_scuri",          "Serramenti", False),
    ("persiane",     "Persiane",             "Serramenti", False),
    ("legno_porta",  "Portoni",              "Serramenti", False),
    ("ferro",        "Ferro_battuto",        "Serramenti", False),
    ("ottone",       "Ottoni",               "Serramenti", False),
    ("luce",         "Lanterna_luce",        "Serramenti", False),
    ("tende",        "Tende",                "Serramenti", False),
    ("legno",        "Orditura_tetto",       "Tetto",      False),
    ("cotto",        "Coppi",                "Tetto",      True),
    ("zinco",        "Grondaie_e_pluviali",  "Tetto",      False),
    ("mattoni",      "Comignolo_mattoni",    "Tetto",      True),
    ("terracotta",   "Cotto_vari",           "Tetto",      False),
    ("buio",         "Interno_scuro",        "Edificio",   False),
    ("prato",        "Terreno",              "Giardino",   False),
    ("erba",         "Erba",                 "Giardino",   True),
    ("lastre",       "Vialetto",             "Giardino",   True),
    ("siepe",        "Siepi",                "Giardino",   True),
    ("cipresso",     "Cipressi",             "Giardino",   True),
    ("chioma",       "Chiome_alberi",        "Giardino",   True),
    ("foglie",       "Fogliame_vasi",        "Giardino",   False),
    ("fiori",        "Fiori",                "Giardino",   False),
    ("terra",        "Terriccio",            "Giardino",   False),
]


def make_materials():
    return {
        "muri": mat_intonaco(),
        "interni": mat_interno(),
        "pietra": mat_pietra("Pietra"),
        "lastre": mat_pietra("Pietra_vialetto", (172, 164, 148), (130, 124, 112), 5.0,
                             use_attr=True),
        "infissi": mat_legno("Legno_infissi", (232, 228, 216), (206, 200, 186), 0.32,
                             (7.0, 7.0, 34.0), coat=0.4, dist=1.6),
        "persiane": mat_legno("Legno_persiane", (96, 116, 92), (62, 82, 64), 0.40,
                              (7.0, 7.0, 30.0), coat=0.3, dist=1.8),
        "legno_porta": mat_legno("Legno_portone", (122, 76, 40), (74, 44, 22), 0.40,
                                 (5.0, 5.0, 16.0), coat=0.2, dist=3.0),
        "tende": mat_tende(),
        "legno": mat_legno("Legno_strutture", (132, 98, 62), (88, 60, 38), 0.66,
                           (3.0, 3.0, 11.0), dist=4.0),
        "vetro": mat_vetro(),
        "vetro_scuro": mat_semplice("Vetro_scuro", (16, 18, 20), 0.12),
        "ferro": mat_metallo("Ferro_battuto", (42, 42, 44), 0.44, 0.9),
        "ottone": mat_metallo("Ottone", (176, 134, 58), 0.26, 1.0),
        "zinco": mat_metallo("Zinco", (142, 144, 146), 0.34, 1.0),
        "luce": mat_semplice("Luce_lanterna", (255, 220, 160), 0.5, (255, 198, 124), 24.0),
        "cotto": mat_cotto(),
        "mattoni": mat_mattoni(),
        "terracotta": mat_semplice("Terracotta", (182, 100, 62), 0.78),
        "buio": mat_semplice("Interno_scuro", (10, 10, 11), 0.9),
        "prato": mat_erba(),
        "erba": mat_fogliame("Erba_ciuffi", (70, 100, 32), (128, 152, 60), use_attr=True),
        "siepe": mat_fogliame("Siepe", (52, 84, 30), (104, 138, 50), use_attr=True),
        "cipresso": mat_fogliame("Cipresso", (34, 60, 34), (70, 100, 52), use_attr=True),
        "chioma": mat_fogliame("Chioma_albero", (44, 72, 28), (110, 140, 54), use_attr=True),
        "foglie": mat_fogliame("Fogliame", (44, 76, 32), (96, 128, 52)),
        "fiori": mat_semplice("Gerani", (186, 36, 32), 0.55),
        "terra": mat_semplice("Terriccio", (64, 50, 38), 0.96),
    }


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


def setup_scena(root):
    scene = bpy.context.scene

    # --- cielo (Nishita) ---------------------------------------------------
    world = bpy.data.worlds.new("Cielo")
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.location = (-700, 0)
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(26.0)
    sky.sun_rotation = math.radians(334.0)
    sky.sun_disc = False
    sky.altitude = 220
    sky.air_density = 1.0
    sky.dust_density = 0.7
    sky.ozone_density = 1.4
    # il cielo visibile in camera resta luminoso, la luce ambiente e' ridotta
    # cosi' il sole domina e le ombre restano leggibili
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    bg_cam.location = (-380, 120)
    bg_cam.inputs["Strength"].default_value = 1.0
    bg_amb = nt.nodes.new("ShaderNodeBackground")
    bg_amb.location = (-380, -80)
    bg_amb.inputs["Strength"].default_value = 0.15
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
    el, az = math.radians(26.0), math.radians(334.0)
    sdir = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    light = bpy.data.lights.new("Sole", "SUN")
    light.energy = 9.5
    light.angle = math.radians(0.75)
    light.color = (1.0, 0.91, 0.78)
    lob = bpy.data.objects.new("Sole", light)
    lob.location = sdir * 40.0
    lob.rotation_euler = (-sdir).to_track_quat("-Z", "Y").to_euler()
    root.objects.link(lob)

    # --- camera ------------------------------------------------------------
    cam = bpy.data.cameras.new("Camera")
    cam.lens = 40.0
    cam.clip_end = 400.0
    cam.dof.use_dof = True
    cam.dof.focus_distance = 19.0
    cam.dof.aperture_fstop = 11.0
    cob = bpy.data.objects.new("Camera", cam)
    pos = Vector((-10.8, -15.8, 5.05))
    target = Vector((0.0, -0.9, 3.75))
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
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.filepath = OUT_PNG
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.0
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0


def main():
    import time
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)

    root = bpy.data.collections.new("Casa_1")
    bpy.context.scene.collection.children.link(root)
    subs = {}
    for nome in ("Edificio", "Serramenti", "Tetto", "Giardino"):
        c = bpy.data.collections.new(nome)
        root.children.link(c)
        subs[nome] = c

    mats = make_materials()
    B = make_buffers(mats)

    print("» muratura, cornici, solai ...")
    build_shell(B)
    print("» serramenti, persiane, portoni ...")
    for spec in OPENINGS:
        if spec["kind"] in ("portone", "porta"):
            build_porta(B, spec, principale=(spec["kind"] == "portone"))
        else:
            build_finestra(B, spec)
    build_lanterna(B, wall_frame("S"), 3.42, 1.95)
    print("» balcone e timpani ...")
    build_balcone(B)
    build_timpani(B)
    print("» tetto (orditura, tavolato, coppi) ...")
    build_tetto(B)
    build_colmo(B)
    build_comignolo(B)
    print("» comignolo, giardino, erba ...")
    build_giardino(B)
    build_erba(B)

    nv = sum(b.nverts for b in BUFS)
    nf = sum(len(b.F) for b in BUFS)
    print("   geometria: %d vertici, %d facce" % (nv, nf))

    print("» creazione oggetti ...")
    for key, name, coll, usec in BUF_SPEC:
        buf_to_object(B[key], subs[coll])

    setup_scena(root)
    print("» salvataggio %s" % OUT_BLEND)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("   fatto in %.1f s (%.1f MB)"
          % (time.time() - t0, os.path.getsize(OUT_BLEND) / 1e6))

    if "--render" in sys.argv:
        print("» render anteprima ...")
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        print("   render in %.1f s -> %s" % (time.time() - t1, OUT_PNG))


if __name__ == "__main__":
    main()
