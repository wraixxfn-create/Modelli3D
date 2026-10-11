"""Genera un ciliegio in fiore (Prunus serrulata) molto dettagliato.

Salva il modello in `ciliegio.blend` (e, con --render, l'anteprima `anteprima.png`).

Cosa costruisce, tutto proceduralmente (nessuna geometria importata):

  STRUTTURA (collezione `Ciliegio`)
    - fusto corto e robusto con contrafforti alla base e radici superficiali
      che emergono dal terreno; corteccia con corde e *lenticelle* orizzontali
      (tipiche dei Prunus) ottenute da una texture UV che gira senza cuciture
      attorno ai rami
    - 9 branche maestre che si aprono a vaso (chioma larga e bassa, come nei
      ciliegi ornamentali), fino a 7 livelli di ramificazione, modello "pipe"
      semplificato (il raggio si riparte tra i figli), nodi ingrossati alle
      forcelle, rametti terminali che si incurvano verso il basso sotto il peso
      della fioritura
    - rametti corti (dardi) sul legno di 2-3 anni, da cui partono i mazzetti

  FIORITURA (collezione `Fioritura`)
    - 12 varianti di *mazzetto* (grappolo) con 2-5 fiori completi ciascuno:
      pedicello curvo, calice a 5 sepali con ovario, 5 petali (a volte 6)
      obovati con smusso/incisione apicale, nervatura incassata, coppa e
      arricciatura, 9-14 stami con filamento e antera gialla, pistillo
    - gemme non ancora aperte (piu' rosa) e foglioline giovani bronzee
    - i mazzetti sono oggetti istanziati (mesh condivise + colore per oggetto),
      quindi si arriva a decine di migliaia di fiori con un file leggero

  TERRENO (collezione `Terreno`)
    - rilievo dolce, erba a ciuffi, sassi, radici affioranti e un tappeto di
      petali caduti sotto la chioma

Esecuzione:
    python genera_ciliegio.py            # solo modello
    python genera_ciliegio.py --render   # modello + anteprima.png
    python genera_ciliegio.py --render --quick
"""

import bpy
import bmesh
import colorsys
import math
import os
import random
import sys
import time

from mathutils import Vector, Matrix, noise

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_BLEND = os.path.join(HERE, "ciliegio.blend")
OUT_PREVIEW = os.path.join(HERE, "anteprima.png")

SEED = 2027
random.seed(SEED)

T_START = time.time()


def log(msg):
    print("[%6.1fs] %s" % (time.time() - T_START, msg))


# ----------------------------------------------------------------------------
# Parametri (unita': metri)
# ----------------------------------------------------------------------------
TRUNK_H = 1.72          # il ciliegio ornamentale si ramifica molto in basso
TRUNK_R0 = 0.30         # raggio al colletto (prima dei contrafforti)
TRUNK_R1 = 0.195
LIMBS = 9               # branche maestre
MAX_DEPTH = 7
SIDES = {0: 36, 1: 22, 2: 15, 3: 11, 4: 8, 5: 6, 6: 5, 7: 5}
SPAWN = {1: 0.55, 2: 0.56, 3: 0.58, 4: 0.60, 5: 0.34, 6: 0.22}
BRANCH_BUDGET_PER_LIMB = 2450
MAX_BRANCHES = 22500
MAX_WOOD_VERTS = 620000

# Chioma: profilo a vaso, largo e non troppo alto (il ciliegio e' piu' largo
# che alto). Tabella (quota, raggio massimo): nessun ramo esce da questa sagoma.
CROWN_PROFILE = ((0.00, 0.70), (0.80, 1.20), (1.60, 2.05), (2.40, 2.90),
                 (3.20, 3.52), (4.00, 3.80), (4.80, 3.68), (5.50, 3.20),
                 (6.10, 2.30), (6.55, 1.30), (6.85, 0.30))
CROWN_TOP = 6.90

FLOWER_MIN_DEPTH = 1        # fiorisce dal legno di 1 anno in su (piu' rado sui rami grossi)
SPUR_DEPTH = 3              # dardi fioriferi sul legno grosso
CLUSTER_SPACING = 0.076     # distanza media tra i mazzetti lungo i rametti
MAX_CLUSTERS = 48000
CLUSTER_SCALE = (1.00, 1.36)

GROUND_R = 14.0
GROUND_PETALS = 9000
GROUND_TUFTS = 3400
GROUND_STONES = 40

SEGMENTS = []               # (p0, p1, direzione, profondita', raggio)
TIPS = []                   # punte dei rami (ultimo segmento), sempre fiorite
SPURS = []                  # (p, direzione, profondita') dardi sul legno grosso
BRANCHES = 0


# ----------------------------------------------------------------------------
# Utility
# ----------------------------------------------------------------------------
def rr(a, b):
    return a + (b - a) * random.random()


def rand_unit():
    while True:
        v = Vector((rr(-1, 1), rr(-1, 1), rr(-1, 1)))
        if 0.05 < v.length <= 1.0:
            return v.normalized()


def perp(d):
    a = d.cross(rand_unit())
    while a.length < 1e-4:
        a = d.cross(rand_unit())
    return a.normalized()


def srgb_to_linear(c):
    return c ** 2.2


def rgb(r, g, b):
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), 1.0)


def mix4(c0, c1, t):
    return (c0[0] + (c1[0] - c0[0]) * t,
            c0[1] + (c1[1] - c0[1]) * t,
            c0[2] + (c1[2] - c0[2]) * t,
            1.0)


def scale_rgba(c, k):
    return (c[0] * k, c[1] * k, c[2] * k, 1.0)


def crown_max_radius(z):
    """Raggio massimo della chioma a quella quota (interpolazione morbida)."""
    tab = CROWN_PROFILE
    if z <= tab[0][0]:
        return tab[0][1]
    if z >= tab[-1][0]:
        return tab[-1][1] * 0.3
    for i in range(len(tab) - 1):
        z0, r0 = tab[i]
        z1, r1 = tab[i + 1]
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            t = t * t * (3.0 - 2.0 * t)
            return r0 + (r1 - r0) * t
    return tab[-1][1]


def inside_crown(p, margin=1.0):
    rad = math.hypot(p.x, p.y)
    return rad <= crown_max_radius(p.z) * margin and p.z <= CROWN_TOP * margin


def crown_exit_distance(p, d, max_dist=8.0, step=0.08):
    """Distanza a cui il raggio (p, d) esce dalla sagoma della chioma."""
    t = 0.0
    while t < max_dist:
        t += step
        q = p + d * t
        if math.hypot(q.x, q.y) > crown_max_radius(q.z) or q.z > CROWN_TOP:
            return max(0.25, t - step)
    return max_dist


def basis_from_dir(d, roll):
    """Matrice di rotazione che porta l'asse Z locale su `d`, con rollio."""
    z = d.normalized()
    ref = Vector((0, 0, 1)) if abs(z.z) < 0.92 else Vector((1, 0, 0))
    x = ref.cross(z).normalized()
    y = z.cross(x)
    ca, sa = math.cos(roll), math.sin(roll)
    x2 = x * ca + y * sa
    y2 = -x * sa + y * ca
    return Matrix((x2, y2, z)).transposed().to_4x4()


# ----------------------------------------------------------------------------
# Buffer di geometria (liste grezze -> mesh unica, come in albero_1)
# ----------------------------------------------------------------------------
class Buf:
    """Accumula vertici (con colore e uv) e facce (con indice di materiale)."""

    __slots__ = ("V", "F", "MI", "C", "UV", "use_uv")

    def __init__(self, use_uv=False):
        self.V = []
        self.F = []
        self.MI = []
        self.C = []
        self.UV = []
        self.use_uv = use_uv

    def vert(self, p, col=(1, 1, 1, 1), uv=(0.0, 0.0)):
        self.V.append(p)
        self.C.append(col)
        if self.use_uv:
            self.UV.append(uv)
        return len(self.V) - 1

    def face(self, idx, mat=0):
        self.F.append(tuple(idx))
        self.MI.append(mat)

    def quad(self, a, b, c, d, mat=0):
        self.face((a, b, c, d), mat)

    def tri(self, a, b, c, mat=0):
        self.face((a, b, c), mat)

    def nverts(self):
        return len(self.V)

    def reset(self):
        self.V = []
        self.F = []
        self.MI = []
        self.C = []
        self.UV = []


def to_mesh(name, buf, smooth=True, up_faces=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in buf.V], [], buf.F)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if up_faces:
        # petali caduti: la faccia superiore deve guardare in alto
        bm.faces.ensure_lookup_table()
        flip = [f for f in bm.faces if f.normal.z < 0.0]
        if flip:
            bmesh.ops.reverse_faces(bm, faces=flip)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if buf.MI:
        me.polygons.foreach_set("material_index", buf.MI)
    if buf.C:
        att = me.color_attributes.new("Colore", "FLOAT_COLOR", "POINT")
        flat = []
        for c in buf.C:
            flat.extend(c)
        att.data.foreach_set("color", flat)
    if buf.use_uv and buf.UV and len(buf.UV) == len(buf.V):
        uvl = me.uv_layers.new(name="BarkUV")
        flat = []
        for face in buf.F:
            for vi in face:
                flat.extend(buf.UV[vi])
        uvl.data.foreach_set("uv", flat)
    me.validate()
    me.update()
    return me


# ----------------------------------------------------------------------------
# Geometria: tubi (fusto, rami, radici, pedicelli, filamenti)
# ----------------------------------------------------------------------------
def add_tube(buf, pts, radii, sides, mat=0, col=(1, 1, 1, 1), col_tip=None,
             uv=False, ridge=0.0, ridge_freq=5.0, phase=0.0,
             cap_end=True, cap_start=False):
    """Tubo lungo una polilinea, con frame a minima rotazione.

    `ridge`  -> solchi longitudinali di corteccia (rumore radiale)
    `uv`     -> u = giro attorno al tubo (0..1), v = lunghezza progressiva (m)
    """
    n = len(pts)
    tans = []
    for i in range(n):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        if t.length < 1e-9:
            t = Vector((0, 0, 1))
        tans.append(t.normalized())

    ref = Vector((1, 0, 0)) if abs(tans[0].x) < 0.9 else Vector((0, 1, 0))
    u = (ref - tans[0] * ref.dot(tans[0])).normalized()
    frames = []
    for i in range(n):
        t = tans[i]
        u = u - t * u.dot(t)
        if u.length < 1e-9:
            u = perp(t)
        u.normalize()
        v = t.cross(u).normalized()
        frames.append((u, v))

    # lunghezza progressiva per le coordinate UV
    vpos = [0.0]
    for i in range(1, n):
        vpos.append(vpos[-1] + (pts[i] - pts[i - 1]).length)

    rings = []
    for i in range(n):
        fu, fv = frames[i]
        p = pts[i]
        r = radii[i]
        start = len(buf.V)
        for j in range(sides):
            a = 2.0 * math.pi * j / sides
            d = fu * math.cos(a) + fv * math.sin(a)
            rad = r
            if ridge > 0.0:
                # solchi longitudinali: rumore valutato in coordinate
                # "verticali" per ottenere corde che corrono lungo il ramo
                q = d * (1.6 * ridge_freq) + Vector((p.x, p.y, p.z)) * 0.9
                rad = r * (1.0 + ridge * noise.noise(q)
                           + 0.5 * ridge * math.cos(ridge_freq * a + phase))
            c = col
            if col_tip is not None:
                c = mix4(col, col_tip, i / max(1, n - 1))
            if uv:
                buf.vert(p + d * max(rad, 1e-4), c, (j / sides, vpos[i]))
            else:
                buf.vert(p + d * max(rad, 1e-4), c)
        rings.append(start)

    for i in range(n - 1):
        a0, a1 = rings[i], rings[i + 1]
        for j in range(sides):
            jn = (j + 1) % sides
            buf.quad(a0 + j, a0 + jn, a1 + jn, a1 + j, mat)

    if cap_end:
        c = len(buf.V)
        last = rings[-1]
        p = pts[-1]
        buf.vert(p, col_tip if col_tip is not None else col)
        for j in range(sides):
            buf.tri(last + j, last + (j + 1) % sides, c, mat)
    if cap_start:
        c = len(buf.V)
        p = pts[0]
        buf.vert(p, col)
        first = rings[0]
        for j in range(sides):
            buf.tri(first + (j + 1) % sides, first + j, c, mat)


def add_blob(buf, center, radius, scale, mat=0, col=(1, 1, 1, 1),
             rings=4, sides=8, rough=0.12, orient=None):
    """Sfera schiacciata/rugosa (ovario, antera, gemma, sasso)."""
    rows = []
    for i in range(1, rings):
        phi = math.pi * i / rings
        z = math.cos(phi)
        r = math.sin(phi) * (1.0 + rough * noise.noise(Vector((center.x, z * 3.0, center.y))))
        row = []
        for j in range(sides):
            a = 2.0 * math.pi * j / sides
            p = Vector((r * math.cos(a), r * math.sin(a), z))
            p = Vector((p.x * scale[0], p.y * scale[1], p.z * scale[2])) * radius
            if orient is not None:
                p = orient @ p
            row.append(buf.vert(center + p, col))
        rows.append(row)
    top = Vector((0, 0, 1 * scale[2])) * radius
    bot = Vector((0, 0, -1 * scale[2])) * radius
    if orient is not None:
        top, bot = orient @ top, orient @ bot
    it = buf.vert(center + top, col)
    ib = buf.vert(center + bot, col)
    for j in range(sides):
        jn = (j + 1) % sides
        buf.tri(it, rows[0][jn], rows[0][j], mat)
        buf.tri(ib, rows[-1][j], rows[-1][jn], mat)
    for i in range(len(rows) - 1):
        for j in range(sides):
            jn = (j + 1) % sides
            buf.quad(rows[i][j], rows[i][jn], rows[i + 1][jn], rows[i + 1][j], mat)


# ----------------------------------------------------------------------------
# Struttura dell'albero
# ----------------------------------------------------------------------------
def add_segment(p0, p1, depth, radius):
    d = (p1 - p0)
    if d.length < 1e-6:
        return
    SEGMENTS.append((p0, p1, d.normalized(), depth, radius))


def grow(start, direction, length, r0, depth):
    """Cresce un ramo: zig-zag, tropismo, figli e nodi ingrossati."""
    global BRANCHES
    BRANCHES += 1

    sides = SIDES[min(depth, max(SIDES))]
    step = max(0.045, length / max(3, min(13, int(length / 0.20) + 3)))
    n = max(3, int(round(length / step)))
    step = length / n

    d = direction.normalized()
    pts = [start.copy()]
    # fasi del "legno contorto" (il ciliegio ha rami nodosi e irregolari)
    ph1, ph2 = rr(0, 6.28), rr(0, 6.28)
    for i in range(n):
        t = i / n
        # tropismo: verso l'alto nei rami grossi, verso il basso nei rametti
        p = pts[-1]
        out = math.hypot(p.x, p.y)
        if depth <= 2:
            trop = Vector((0, 0, 0.30))
        elif depth <= 4:
            trop = Vector((0, 0, 0.10))
        else:
            droop = 0.16 + 0.60 * min(1.0, max(0.0, (out - 1.7) / 2.2))
            trop = Vector((0, 0, -droop))
        wob = Vector((math.sin(ph1 + i * 1.7), math.cos(ph2 + i * 1.3), 0)) * 0.16
        d = (d + rand_unit() * 0.16 + wob + trop * 0.28)
        # sagoma della chioma: i rami che escono dal profilo vengono ripiegati
        # verso l'interno (solo componente orizzontale: il fusto resta libero)
        if depth >= 1:
            rad = math.hypot(p.x, p.y)
            rmax = crown_max_radius(p.z)
            if rad > rmax and rad > 1e-5:
                pull = min(0.8, 1.5 * (rad / rmax - 1.0))
                d.x -= (p.x / rad) * pull
                d.y -= (p.y / rad) * pull
            if p.z > CROWN_TOP:
                d.z -= 1.6 * (p.z - CROWN_TOP)
        d.normalize()
        pts.append(pts[-1] + d * step)

    rtip = max(0.0022, r0 * rr(0.42, 0.60))
    radii = [r0 + (rtip - r0) * ((i / n) ** 0.9) for i in range(n + 1)]

    children = []
    if depth < MAX_DEPTH and BRANCHES < min(MAX_BRANCHES, BRANCH_END) \
            and len(WB.V) < MAX_WOOD_VERTS:
        # pochi nodi generano figli: il fattore di ramificazione resta ~2.5-3.2
        # (altrimenti il budget si esaurisce nei primi livelli e i rametti
        #  terminali - quelli che portano i fiori - non verrebbero mai costruiti)
        p_spawn = SPAWN.get(depth, 0.30)
        for k in range(1, n):
            if random.random() > p_spawn:
                continue
            seg_dir = (pts[k + 1] - pts[k - 1]).normalized()
            roll = random.random()
            if depth <= 2:
                n_ch = 3 if roll < 0.30 else (2 if roll < 0.80 else 1)
            elif depth <= 4:
                n_ch = 2 if roll < 0.45 else 1
            else:
                n_ch = 2 if roll < 0.25 else 1
            for c in range(n_ch):
                if depth <= 1:
                    ang = math.radians(rr(16, 40))
                elif depth <= 3:
                    ang = math.radians(rr(20, 48))
                else:
                    ang = math.radians(rr(24, 58))
                axis = perp(seg_dir)
                cd = Matrix.Rotation(ang, 3, axis) @ seg_dir
                up = 0.34 if depth <= 1 else (0.16 if depth <= 3 else -0.05)
                cd = (cd + Vector((0, 0, up))).normalized()
                if depth <= 1:
                    clen = length * rr(0.56, 0.78)
                elif depth <= 3:
                    clen = length * rr(0.45, 0.70)
                elif depth <= 4:
                    clen = length * rr(0.35, 0.58)
                else:
                    clen = length * rr(0.30, 0.48)
                est = pts[k] + cd * clen * 0.92
                if depth >= 2 and not inside_crown(est, 1.02) and random.random() < 0.93:
                    continue
                if depth <= 2:
                    lim = crown_exit_distance(pts[k], cd, max_dist=clen * 1.4)
                    clen = min(clen, max(0.35, lim * 0.92))
                # potatura naturale: il centro della chioma e' in ombra e i
                # rametti interni seccano (chioma "vuota" dentro, fitta fuori)
                if depth >= 3:
                    erad = math.hypot(est.x, est.y)
                    ermax = max(0.5, crown_max_radius(est.z))
                    if (erad < 0.38 * ermax and est.z < CROWN_TOP * 0.72
                            and random.random() < 0.85):
                        continue
                    if erad > 0.35:
                        outward = Vector((est.x, est.y, 0.0)).normalized()
                        if cd.dot(outward) < -0.12 and random.random() < 0.80:
                            continue
                if len(WB.V) > MAX_WOOD_VERTS:
                    break
                cr0 = radii[k] * rr(0.60, 0.78)
                children.append((k, cd, clen, cr0))
                # ingrossamento del nodo
                for kk in (k - 1, k, min(n - 1, k + 1)):
                    radii[kk] *= 1.035
    # ripristina il raggio del tronco ai nodi raddoppiati (evita "salsicciotti")
    for i in range(1, n):
        radii[i] = min(radii[i], r0 * 1.12)

    add_tube(WB, pts, radii, sides, mat=0,
             col=WOOD_COL, col_tip=WOOD_COL_TIP, uv=True,
             ridge=0.045 if depth <= 2 else 0.075,
             ridge_freq=rr(3.0, 6.0), phase=rr(0, 6.28))

    for k in range(1, n + 1):
        add_segment(pts[k - 1], pts[k], depth, radii[k])
    # la punta di ogni ramo porta sempre fiori: nessun ramo resta "spoglio"
    if depth >= 2:
        TIPS.append((pts[-2], pts[-1], (pts[-1] - pts[-2]).normalized(),
                     max(depth, FLOWER_MIN_DEPTH), radii[-1]))

    # dardi fioriferi sul legno di 3-4 anni
    if depth in (3, 4):
        for k in range(1, n):
            if random.random() < (0.30 if depth == 3 else 0.45):
                sd = (pts[k + 1] - pts[k - 1]).normalized()
                SPURS.append((pts[k], sd, depth))

    for k, cd, clen, cr0 in children:
        s = pts[k] - cd * (radii[k] * 0.35)
        grow(s, cd, clen, cr0, depth + 1)


def build_trunk_and_roots():
    # Fusto: corto, un po' inclinato, con contrafforti alla base
    ph1, ph2 = rr(0, 6.28), rr(0, 6.28)
    seg = 26
    pts, radii = [], []
    for i in range(seg + 1):
        f = i / seg
        z = f * TRUNK_H
        x = math.sin(f * 1.9 + ph1) * 0.09 * f
        y = math.cos(f * 1.4 + ph2) * 0.07 * f
        pts.append(Vector((x, y, z)))
        r = TRUNK_R0 * (1 - f) + TRUNK_R1 * f
        flare = 1.0 + 0.95 * max(0.0, 1.0 - z / 0.85) ** 2.0
        flare *= 1.0 + 0.16 * math.sin(ph1 + 5.0 * math.atan2(y, x)) * max(0.0, 1.0 - z / 1.1)
        radii.append(r * flare)
    add_tube(WB, pts, radii, SIDES[0], col=WOOD_COL, col_tip=WOOD_COL_TIP, uv=True,
             ridge=0.05, ridge_freq=4.0, phase=rr(0, 6.28), cap_start=True, cap_end=False)
    trunk_pts, trunk_r = pts, radii

    # Radici superficiali: si allargano alla base e affondano nel terreno
    for i in range(11):
        az = 2 * math.pi * i / 11 + rr(-0.22, 0.22)
        dist = rr(1.1, 1.9)
        dirv = Vector((math.cos(az), math.sin(az), 0))
        rp, rrad = [], []
        for k in range(12):
            t = k / 11
            horiz = 0.05 + dist * t
            z = 0.17 - 0.30 * t + 0.07 * math.sin(math.pi * t)
            p = dirv * horiz + Vector((0, 0, z))
            p += Vector((rr(-0.05, 0.05), rr(-0.05, 0.05), 0)) * t
            rp.append(p)
            rrad.append(max(0.012, 0.155 * (1 - t) ** 1.3 + 0.012))
        add_tube(WB, rp, rrad, 10, col=WOOD_COL, col_tip=WOOD_COL_TIP, uv=True,
                 ridge=0.16, ridge_freq=rr(4.0, 7.0), phase=rr(0, 6.28))

    # Branche maestre, distribuite in basso (vaso) con qualche ramo centrale
    global BRANCH_END
    base_az = rr(0, 6.28)
    for i in range(LIMBS):
        BRANCH_END = BRANCHES + BRANCH_BUDGET_PER_LIMB
        if i < LIMBS - 2:
            f = rr(0.28, 0.70)
            theta = rr(0.78, 1.22)          # molto aperte: chioma a vaso
        else:
            f = rr(0.70, 0.95)
            theta = rr(0.25, 0.62)          # rami centrali piu' verticali
        idx = int(f * seg)
        p = trunk_pts[idx].copy()
        az = base_az + 2 * math.pi * i / LIMBS + rr(-0.26, 0.26)
        dirv = Vector((math.sin(theta) * math.cos(az),
                       math.sin(theta) * math.sin(az),
                       math.cos(theta)))
        # lunghezza limitata dall'uscita dalla chioma: il ramo non "sfonda"
        # la sagoma e non resta un'asta spoglia fuori dalla fioritura
        want = rr(2.6, 3.6)
        lim = crown_exit_distance(p, dirv) * rr(0.85, 1.05)
        grow(p, dirv, min(want, max(1.2, lim)), max(0.055, trunk_r[idx] * 0.60), 1)


# ----------------------------------------------------------------------------
# Fiori: petalo, stame, pistillo, calice, pedicello, gemma, fogliolina
# ----------------------------------------------------------------------------
C_WHITE = rgb(1.00, 0.975, 0.965)
C_PINK = rgb(0.985, 0.735, 0.790)
C_PINK_DEEP = rgb(0.960, 0.560, 0.660)
C_BUD = rgb(0.905, 0.425, 0.545)
C_BUD_TIP = rgb(0.985, 0.735, 0.780)
C_ANTHER = rgb(0.980, 0.855, 0.400)
C_FILAMENT = rgb(1.000, 0.955, 0.900)
C_CALYX = rgb(0.540, 0.400, 0.300)
C_PEDICEL = rgb(0.470, 0.360, 0.245)
C_LEAF = rgb(0.360, 0.520, 0.230)
C_LEAF_TIP = rgb(0.560, 0.640, 0.230)
C_LEAF_BRONZE = rgb(0.620, 0.360, 0.220)

MAT_PETAL, MAT_STAMEN, MAT_CALYX, MAT_LEAF = 0, 1, 2, 3


def add_petal(buf, center, radial, tangent, normal, L, W,
              c_base, c_tip, cup, curl, notch):
    """Petalo obovato, concavo, con nervatura incassata e punta incisa."""
    rows = 3
    grid = []
    for i in range(rows + 1):
        t = i / rows
        # profilo obovato: la lamina si allarga verso l'apice
        prof = math.sin(math.pi * min(1.0, (t * 0.94) ** 0.55)) ** 0.72
        w = W * max(0.012, prof)
        bend = curl * L * (t ** 2.0)
        row = []
        for k, sv in enumerate((-1.0, 0.0, 1.0)):
            p = (center
                 + radial * (L * t)
                 + normal * (bend + cup * (sv * sv) * w * 1.7 - (0.16 * w if sv == 0.0 else 0.0))
                 + tangent * (sv * w))
            if i == rows and sv == 0.0:
                p -= radial * notch * L      # incisione apicale
            col = mix4(c_base, c_tip, min(1.0, t ** 1.15))
            if sv != 0.0:
                col = scale_rgba(col, 0.985)
            row.append(buf.vert(p, col))
        grid.append(row)
    # petalo inclinato verso il centro del fiore
    for i in range(rows):
        for k in range(2):
            buf.quad(grid[i][k], grid[i][k + 1],
                     grid[i + 1][k + 1], grid[i + 1][k], MAT_PETAL)


def add_stamen(buf, base, dir_v, length, curl_dir, phase_col):
    """Filamento + antera."""
    pts, rad = [], []
    n = 3
    for i in range(n + 1):
        t = i / n
        p = base + dir_v * (length * t) + curl_dir * (length * 0.22 * t * t)
        pts.append(p)
        rad.append(max(0.00055, 0.0013 * (1.0 - 0.6 * t)))
    add_tube(buf, pts, rad, 3, mat=MAT_STAMEN, col=C_FILAMENT, cap_end=True)
    anther = C_ANTHER if phase_col else mix4(C_ANTHER, C_FILAMENT, 0.35)
    d = (pts[-1] - pts[-2]).normalized()
    add_blob(buf, pts[-1] + d * 0.0012, 0.0022, (0.75, 0.75, 1.9), mat=MAT_STAMEN,
             col=anther, rings=2, sides=5, rough=0.0,
             orient=basis_from_dir(d, 0.0).to_3x3())


def add_flower(buf, attach, center, face, size, petal_count, tint,
               stamen_count, pedicel_len, pedicel_dir):
    """Fiore completo: pedicello, calice, 5 petali, stami, pistillo."""
    nf = face.normalized()
    # pedicello curvo dall'attacco al calice
    ppts, prad = [], []
    for i in range(5):
        t = i / 4
        bend = (nf.cross(Vector((0, 0, 1))) if abs(nf.z) < 0.9 else perp(nf))
        p = attach.lerp(center - nf * (size * 0.16), t)
        p += pedicel_dir * (math.sin(math.pi * t) * pedicel_len * 0.22)
        ppts.append(p)
        prad.append(0.0032 * (1.0 - 0.35 * t))
    add_tube(buf, ppts, prad, 4, mat=MAT_CALYX, col=C_PEDICEL, cap_end=False)

    # calice a 5 sepali con ovario rigonfio
    cbase = center - nf * (size * 0.14)
    cpts, crad = [], []
    for i in range(3):
        t = i / 2
        cpts.append(cbase + nf * (size * 0.16 * t))
        crad.append(size * (0.085 * (1.0 - 0.35 * t)))
    add_tube(buf, cpts, crad, 5, mat=MAT_CALYX, col=C_CALYX,
             col_tip=mix4(C_CALYX, C_LEAF, 0.25), cap_end=False)
    add_blob(buf, cbase + nf * (size * 0.05), size * 0.11, (1.0, 1.0, 0.8),
             mat=MAT_CALYX, col=mix4(C_CALYX, C_LEAF, 0.35), rings=2, sides=6,
             rough=0.10, orient=basis_from_dir(nf, 0.0).to_3x3())

    # petali
    phase = rr(0, 6.28)
    cup = rr(0.16, 0.34)
    for k in range(petal_count):
        a = phase + 2 * math.pi * k / petal_count + rr(-0.10, 0.10)
        radial = Vector((math.cos(a), math.sin(a), 0.0))
        radial = (radial - nf * radial.dot(nf))
        if radial.length < 1e-4:
            radial = perp(nf)
        radial.normalize()
        tangential = nf.cross(radial).normalized()
        tilt = math.radians(rr(6, 22))
        pdir = (radial * math.cos(tilt) + nf * math.sin(tilt)).normalized()
        # ogni tanto un petalo "fuori posto" come nei fiori veri
        L = size * rr(0.90, 1.10)
        W = size * rr(0.62, 0.80)
        cb = scale_rgba(C_WHITE, rr(0.97, 1.02))
        ct = mix4(tint, C_PINK_DEEP, rr(0.0, 0.22))
        if random.random() < 0.10:
            ct = mix4(ct, C_WHITE, rr(0.3, 0.7))
        add_petal(buf, center + pdir * (size * 0.10), pdir, tangential, nf,
                  L, W, cb, ct, cup * rr(0.8, 1.25), rr(-0.16, 0.10),
                  rr(0.05, 0.14))

    # stami (piu' corti dei petali, antere gialle)
    for k in range(stamen_count):
        a = rr(0, 6.28)
        radial = Vector((math.cos(a), math.sin(a), 0.0))
        radial = radial - nf * radial.dot(nf)
        if radial.length < 1e-4:
            radial = perp(nf)
        radial.normalize()
        tilt = math.radians(rr(14, 38))
        sdir = (radial * math.sin(tilt) + nf * math.cos(tilt)).normalized()
        ln = size * rr(0.34, 0.58)
        add_stamen(buf, center + nf * (size * 0.06), sdir, ln,
                   -radial * rr(0.5, 1.4), random.random() < 0.8)

    # pistillo
    pist = (nf * 0.94 + perp(nf) * 0.34).normalized()
    add_stamen(buf, center + nf * (size * 0.05), pist, size * rr(0.62, 0.75),
               perp(nf) * 0.6, False)


def add_bud(buf, attach, center, face, size, dir_out):
    """Gemma non aperta: teardrop rosa con sepali."""
    nf = face.normalized()
    ppts, prad = [], []
    for i in range(4):
        t = i / 3
        p = attach.lerp(center - nf * (size * 0.55), t)
        p += dir_out * (math.sin(math.pi * t) * size * 0.25)
        ppts.append(p)
        prad.append(0.0028 * (1.0 - 0.3 * t))
    add_tube(buf, ppts, prad, 4, mat=MAT_CALYX, col=C_PEDICEL, cap_end=False)

    # corpo della gemma (sfera allungata, chiusa)
    rot = basis_from_dir(nf, 0.0).to_3x3()
    rows = [0.12, 0.36, 0.62, 0.84]
    sides = 7
    rings = []
    for t in rows:
        rr_ = math.sin(math.pi * (0.22 + 0.72 * t)) ** 0.85
        row = []
        col = mix4(C_BUD, C_BUD_TIP, t ** 1.4)
        for j in range(sides):
            a = 2 * math.pi * j / sides + t * 0.5
            p = Vector((rr_ * math.cos(a), rr_ * math.sin(a),
                        (t - 0.45) * 1.5)) * size
            row.append(buf.vert(center + rot @ p, col))
        rings.append(row)
    tipc = mix4(C_BUD, C_BUD_TIP, 0.9)
    it = buf.vert(center + rot @ Vector((0, 0, 1.05 * size)) * 1.0, tipc)
    ib = buf.vert(center + rot @ Vector((0, 0, -0.62 * size)), C_CALYX)
    for j in range(sides):
        jn = (j + 1) % sides
        buf.tri(it, rings[-1][jn], rings[-1][j], MAT_PETAL)
        buf.tri(ib, rings[0][j], rings[0][jn], MAT_CALYX)
    for i in range(len(rings) - 1):
        for j in range(sides):
            jn = (j + 1) % sides
            buf.quad(rings[i][j], rings[i][jn], rings[i + 1][jn], rings[i + 1][j], MAT_PETAL)

    # sepali che avvolgono la base
    for k in range(4):
        a = 2 * math.pi * k / 4 + 0.3
        d = (nf * 0.55 + Vector((math.cos(a), math.sin(a), 0)) * 0.9).normalized()
        p0 = center - nf * (size * 0.5)
        sp = [p0, p0 + d * size * 0.42, p0 + d * size * 0.72 + nf * size * 0.1]
        add_tube(buf, sp, [size * 0.10, size * 0.06, size * 0.02], 3,
                 mat=MAT_CALYX, col=mix4(C_CALYX, C_PEDICEL, 0.4))



def add_leaf(buf, base, dir_v, up_v, L, W, c0, c1, curl):
    """Fogliolina giovane del ciliegio: ovata, apice acuminato, margine seghettato."""
    side = dir_v.cross(up_v).normalized()
    nrm = side.cross(dir_v).normalized()
    rows = 5
    grid = []
    for i in range(rows + 1):
        t = i / rows
        prof = math.sin(math.pi * (0.12 + 0.88 * t) ** 0.85) ** 0.8
        w = W * max(0.006, prof)
        if 0.15 < t < 0.95:      # dentellatura
            w *= 1.0 + 0.13 * math.sin(t * 22.0)
        # foglia piegata a V lungo la nervatura
        row = []
        for k, sv in enumerate((-1.0, 0.0, 1.0)):
            p = (base + dir_v * (L * t)
                 + nrm * (curl * L * t * t + 0.18 * w * abs(sv))
                 + side * (sv * w))
            if i == rows:
                p += dir_v * L * 0.06      # punta acuminata
            col = mix4(c0, c1, t ** 1.1)
            if sv != 0.0:
                col = mix4(col, c1, 0.15)
            row.append(buf.vert(p, col))
        grid.append(row)
    for i in range(rows):
        for k in range(2):
            buf.quad(grid[i][k], grid[i][k + 1], grid[i + 1][k + 1], grid[i + 1][k], MAT_LEAF)
    # picciolo
    add_tube(buf, [base - dir_v * (L * 0.22), base + dir_v * (L * 0.03)],
             [W * 0.075, W * 0.06], 3, mat=MAT_LEAF, col=mix4(c0, C_LEAF_BRONZE, 0.3))


def build_cluster_variant(idx):
    """Un mazzetto di 2-5 fiori + gemme + foglioline, con pedicelli da un punto.

    Ritorna (buffer, numero di fiori e gemme contenuti nel mazzetto).
    """
    buf = Buf()
    n_flowers = random.choice([2, 3, 3, 3, 4, 4, 5])
    semi_double = (idx % 6 == 0)         # qualche fiore semidoppio
    origin = Vector((0, 0, 0))
    pedicel_len = rr(0.014, 0.026)
    base_tint = random.choice([C_WHITE, C_WHITE, C_PINK, C_PINK, C_PINK_DEEP])

    for f in range(n_flowers):
        # il fiore sta in cima al pedicello, orientato verso l'esterno
        face = rand_unit()
        face = (face + Vector((0, 0, rr(-0.55, 0.30)))).normalized()
        dist = pedicel_len * rr(0.85, 1.25)
        center = origin + face * dist + rand_unit() * 0.008
        attach = origin + rand_unit() * 0.006
        size = rr(0.0170, 0.0230)        # raggio del fiore ~1.7-2.3 cm
        tint = mix4(base_tint, C_PINK_DEEP, rr(0.0, 0.45))
        if semi_double and f == 0:
            petal_count = random.choice([9, 11, 12])
            stamen_count = 5
        else:
            petal_count = 5 if random.random() < 0.88 else 6
            stamen_count = random.randint(6, 9)
        pedicel_dir = perp(face) * rr(-1.0, 1.0)
        add_flower(buf, attach, center, face, size, petal_count, tint,
                   stamen_count, pedicel_len * 0.6, pedicel_dir)

    # gemme
    n_buds = random.choice([0, 1, 1, 2])
    for b in range(n_buds):
        face = rand_unit()
        face = (face + Vector((0, 0, rr(-0.2, 0.5)))).normalized()
        center = origin + face * pedicel_len * rr(0.5, 0.8) + rand_unit() * 0.006
        add_bud(buf, origin + rand_unit() * 0.005, center, face,
                rr(0.0075, 0.0105), perp(face) * rr(0.5, 1.0))

    # foglioline giovani che spuntano dal mazzetto
    n_leaves = random.choice([0, 1, 2, 2, 3, 3])
    for l in range(n_leaves):
        d = rand_unit()
        d = (d + Vector((0, 0, rr(-0.2, 0.6)))).normalized()
        p = origin + rand_unit() * 0.010 + d * 0.006
        up = perp(d)
        c0 = mix4(C_LEAF, C_LEAF_BRONZE, rr(0.0, 0.7))
        add_leaf(buf, p, d, up, rr(0.022, 0.042), rr(0.010, 0.019), c0,
                 mix4(C_LEAF_TIP, C_LEAF, rr(0.0, 0.6)), rr(-0.10, 0.22))
    return buf, n_flowers + n_buds


# ----------------------------------------------------------------------------
# Terreno
# ----------------------------------------------------------------------------
def build_ground():
    buf = Buf()
    rings, segs, R = 40, 168, GROUND_R
    center = buf.vert(Vector((0, 0, ground_z(0, 0))), rgb(0.45, 0.34, 0.20))
    ring0 = []
    for i in range(1, rings + 1):
        r = R * (i / rings) ** 1.25
        row = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            x, y = r * math.cos(a), r * math.sin(a)
            z = ground_z(x, y)
            shade = 0.80 + 0.42 * noise.noise(Vector((x * 1.3, y * 1.3, 5.0)))
            col = scale_rgba(rgb(0.50, 0.375, 0.215), shade)
            row.append(buf.vert(Vector((x, y, z)), col))
        ring0.append(row)
    for j in range(segs):
        jn = (j + 1) % segs
        buf.tri(center, ring0[0][j], ring0[0][jn], 0)
    for i in range(len(ring0) - 1):
        for j in range(segs):
            jn = (j + 1) % segs
            buf.quad(ring0[i][j], ring0[i + 1][j], ring0[i + 1][jn], ring0[i][jn], 0)
    return buf


def ground_z(x, y):
    """Quota del terreno in (x, y): dolce, con una montagnetta al piede."""
    r = math.hypot(x, y)
    fade = min(1.0, max(0.0, (r - 0.7) / 1.5))
    z = (0.06 * noise.noise(Vector((x * 0.45, y * 0.45, 0.3)))
         + 0.025 * noise.noise(Vector((x * 2.1, y * 2.1, 1.7)))
         + 0.07 * math.exp(-((r - 1.05) / 1.15) ** 2))
    z += 0.022 * fade * noise.noise(Vector((x * 6.0, y * 6.0, 3.1)))
    # verso il bordo il terreno si incurva e scende (l'orizzonte non e' un taglio netto)
    t = max(0.0, r - GROUND_R * 0.55) / (GROUND_R * 0.45)
    z -= 0.55 * (t ** 2.2)
    return z


def scatter_ground_petals():
    """Tappeto di petali caduti sotto la chioma (mesh unica, petali singoli)."""
    buf = Buf()
    for _ in range(GROUND_PETALS):
        # distribuzione a goccia: densa sotto la chioma, dirada verso il bordo
        # i petali cadono soprattutto sotto il bordo della chioma
        if random.random() < 0.55:
            r = abs(random.gauss(2.9, 0.9))
        else:
            r = abs(random.gauss(0.0, 1.6))
        r = min(r, 5.4)
        a = rr(0, 2 * math.pi)
        x, y = r * math.cos(a), r * math.sin(a)
        if r < 0.35:
            continue
        p = Vector((x, y, ground_z(x, y) + rr(0.001, 0.004)))
        d = Vector((rr(-1, 1), rr(-1, 1), 0))
        if d.length < 1e-3:
            d = Vector((1, 0, 0))
        d.normalize()
        up = Vector((rr(-0.5, 0.5), rr(-0.5, 0.5), 1.0)).normalized()
        tint = random.choice([C_PINK_DEEP, C_PINK, C_PINK_DEEP, C_PINK])
        c0 = scale_rgba(mix4(C_PINK, C_WHITE, rr(0.1, 0.5)), rr(0.9, 1.05))
        c1 = mix4(tint, C_PINK_DEEP, rr(0.1, 0.5))
        L = rr(0.018, 0.027)
        add_petal(buf, p, d, up.cross(d).normalized(), up, L, L * rr(0.6, 0.8),
                  c0, c1, rr(0.25, 0.6), rr(-0.2, 0.2), rr(0.02, 0.1))
    return buf


def build_grass_tufts():
    """Ciuffi d'erba: fili sottili, piegati, con colore per vertice."""
    buf = Buf()
    for _ in range(GROUND_TUFTS):
        r = math.sqrt(random.random()) * GROUND_R * 0.98
        a = rr(0, 2 * math.pi)
        x, y = r * math.cos(a), r * math.sin(a)
        if r < 0.55:
            continue
        base_z = ground_z(x, y)
        # piu' erba ai bordi, meno sotto la chioma
        if r < 2.6 and random.random() < 0.25:
            continue
        nb = random.randint(5, 11)
        for _b in range(nb):
            bx, by = x + rr(-0.05, 0.05), y + rr(-0.05, 0.05)
            bz = ground_z(bx, by)
            h = rr(0.08, 0.24)
            lean = Vector((rr(-1, 1), rr(-1, 1), 0)).normalized()
            lean *= h * rr(0.20, 0.65)
            d = lean.normalized() if lean.length > 1e-4 else Vector((1, 0, 0))
            side = Vector((-d.y, d.x, 0)).normalized()
            tip = Vector((bx, by, bz + h)) + lean
            mid = Vector((bx, by, bz + h * 0.55)) + lean * 0.35
            w = 0.0038
            green = rgb(rr(0.22, 0.38), rr(0.38, 0.60), rr(0.09, 0.22))
            dry = random.random() < 0.25
            if dry:
                green = rgb(rr(0.45, 0.62), rr(0.42, 0.55), rr(0.15, 0.25))
            c_tip = scale_rgba(green, rr(0.95, 1.25))
            i0 = buf.vert(Vector((bx, by, bz)), green)
            i1 = buf.vert(mid + side * w, mix4(green, c_tip, 0.5))
            i2 = buf.vert(mid - side * w, mix4(green, c_tip, 0.5))
            i3 = buf.vert(tip, c_tip)
            buf.tri(i0, i2, i1, 0)
            buf.tri(i1, i2, i3, 0)
    return buf


def build_stones():
    buf = Buf()
    for _ in range(GROUND_STONES):
        r = rr(1.6, GROUND_R * 0.9)
        a = rr(0, 2 * math.pi)
        x, y = r * math.cos(a), r * math.sin(a)
        z = ground_z(x, y)
        sz = rr(0.05, 0.19)
        tone = rr(0.30, 0.55)
        col = rgb(tone, tone * rr(0.92, 1.0), tone * rr(0.85, 0.98))
        rot = basis_from_dir(Vector((rr(-0.3, 0.3), rr(-0.3, 0.3), 1)), rr(0, 6.28)).to_3x3()
        add_blob(buf, Vector((x, y, z + sz * 0.25)), sz,
                 (1.0, rr(0.75, 1.15), rr(0.45, 0.75)), mat=0, col=col,
                 rings=3, sides=7, rough=0.22, orient=rot)
    return buf


# ----------------------------------------------------------------------------
# Materiali
# ----------------------------------------------------------------------------
def _principled(mat):
    return mat.node_tree.nodes["Principled BSDF"]


def mat_bark():
    """Corteccia di Prunus: grigio-bruna, liscia, con lenticelle orizzontali."""
    mat = bpy.data.materials.new("Corteccia_Ciliegio")
    mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    bsdf = _principled(mat)

    uv = N.new("ShaderNodeUVMap")
    uv.uv_map = "BarkUV"
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(uv.outputs["UV"], sep.inputs["Vector"])
    # u -> cerchio (il rumore si chiude senza cuciture sul giro del ramo)
    twopi = N.new("ShaderNodeMath")
    twopi.operation = "MULTIPLY"
    twopi.inputs[1].default_value = 6.2831853
    L.new(sep.outputs["X"], twopi.inputs[0])
    cu = N.new("ShaderNodeMath")
    cu.operation = "COSINE"
    su = N.new("ShaderNodeMath")
    su.operation = "SINE"
    L.new(twopi.outputs["Value"], cu.inputs[0])
    L.new(twopi.outputs["Value"], su.inputs[0])
    ku = N.new("ShaderNodeMath")
    ku.operation = "MULTIPLY"
    ku.inputs[1].default_value = 34.0
    L.new(cu.outputs["Value"], ku.inputs[0])
    ku2 = N.new("ShaderNodeMath")
    ku2.operation = "MULTIPLY"
    ku2.inputs[1].default_value = 34.0
    L.new(su.outputs["Value"], ku2.inputs[0])
    kv = N.new("ShaderNodeMath")
    kv.operation = "MULTIPLY"
    kv.inputs[1].default_value = 150.0    # lungo il ramo: fitto (lenticelle)
    L.new(sep.outputs["Y"], kv.inputs[0])

    # --- lenticelle: rumore "stirato" in senso circonferenziale
    lent_v = N.new("ShaderNodeCombineXYZ")
    L.new(ku.outputs["Value"], lent_v.inputs["X"])
    L.new(ku2.outputs["Value"], lent_v.inputs["Y"])
    L.new(kv.outputs["Value"], lent_v.inputs["Z"])
    lent = N.new("ShaderNodeTexNoise")
    lent.inputs["Scale"].default_value = 1.0
    lent.inputs["Detail"].default_value = 2.0
    lent.inputs["Roughness"].default_value = 0.5
    L.new(lent_v.outputs["Vector"], lent.inputs["Vector"])
    mask = N.new("ShaderNodeValToRGB")
    mask.color_ramp.interpolation = "EASE"
    mask.color_ramp.elements[0].position = 0.565
    mask.color_ramp.elements[0].color = (0, 0, 0, 1)
    mask.color_ramp.elements[1].position = 0.675
    mask.color_ramp.elements[1].color = (1, 1, 1, 1)
    L.new(lent.outputs["Fac"], mask.inputs["Fac"])

    # --- colore base: grigio-bruno con chiazze
    tc = N.new("ShaderNodeTexCoord")
    noise1 = N.new("ShaderNodeTexNoise")
    noise1.inputs["Scale"].default_value = 5.0
    noise1.inputs["Detail"].default_value = 10.0
    noise1.inputs["Roughness"].default_value = 0.6
    L.new(tc.outputs["Object"], noise1.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.048, 0.033, 0.026, 1)
    ramp.color_ramp.elements[1].color = (0.235, 0.190, 0.165, 1)
    mix1 = ramp.color_ramp.elements.new(0.45)
    mix1.color = (0.115, 0.082, 0.063, 1)
    L.new(noise1.outputs["Fac"], ramp.inputs["Fac"])

    # --- muschio alla base (solo in basso, sotto ~0.9 m)
    sep2 = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep2.inputs["Vector"])
    mz = N.new("ShaderNodeMapRange")
    mz.inputs["From Min"].default_value = 0.60
    mz.inputs["From Max"].default_value = 0.10
    L.new(sep2.outputs["Z"], mz.inputs["Value"])
    mnoise = N.new("ShaderNodeTexNoise")
    mnoise.inputs["Scale"].default_value = 9.0
    mnoise.inputs["Detail"].default_value = 8.0
    L.new(tc.outputs["Object"], mnoise.inputs["Vector"])
    mmul = N.new("ShaderNodeMath")
    mmul.operation = "MULTIPLY"
    L.new(mz.outputs["Result"], mmul.inputs[0])
    L.new(mnoise.outputs["Fac"], mmul.inputs[1])
    mosscol = N.new("ShaderNodeMixRGB")
    mosscol.inputs["Color2"].default_value = (0.045, 0.075, 0.020, 1)
    L.new(ramp.outputs["Color"], mosscol.inputs["Color1"])
    fac = N.new("ShaderNodeMath")
    fac.operation = "MULTIPLY"
    fac.inputs[1].default_value = 1.1
    L.new(mmul.outputs["Value"], fac.inputs[0])
    L.new(fac.outputs["Value"], mosscol.inputs["Fac"])

    # le lenticelle scuriscono/chiarano leggermente
    lentcol = N.new("ShaderNodeMixRGB")
    lentcol.inputs["Color2"].default_value = (0.310, 0.255, 0.215, 1)
    L.new(mosscol.outputs["Color"], lentcol.inputs["Color1"])
    L.new(mask.outputs["Color"], lentcol.inputs["Fac"])
    L.new(lentcol.outputs["Color"], bsdf.inputs["Base Color"])

    # --- rilievo: lenticelle + rugosita' fine
    fine = N.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 90.0
    fine.inputs["Detail"].default_value = 6.0
    L.new(tc.outputs["Object"], fine.inputs["Vector"])
    hmax = N.new("ShaderNodeMath")
    hmax.operation = "MAXIMUM"
    hmax.inputs[1].default_value = 0.35
    L.new(fine.outputs["Fac"], hmax.inputs[0])
    hadd = N.new("ShaderNodeMath")
    hadd.operation = "ADD"
    L.new(mask.outputs["Color"], hadd.inputs[0])
    L.new(hmax.outputs["Value"], hadd.inputs[1])
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.55
    bump.inputs["Distance"].default_value = 0.006
    L.new(hadd.outputs["Value"], bump.inputs["Height"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    bsdf.inputs["Roughness"].default_value = 0.72
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.35
    return mat


def _attr_color(N, L, bsdf, name="Colore"):
    att = N.new("ShaderNodeAttribute")
    att.attribute_type = "GEOMETRY"
    att.attribute_name = name
    L.new(att.outputs["Color"], bsdf.inputs["Base Color"])
    return att


def mat_petals():
    """Petali: colore per vertice (base bianca -> punta rosa) x colore d'oggetto."""
    mat = bpy.data.materials.new("Fiore_Petali")
    mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    bsdf = _principled(mat)
    att = N.new("ShaderNodeAttribute")
    att.attribute_type = "GEOMETRY"
    att.attribute_name = "Colore"
    oi = N.new("ShaderNodeObjectInfo")
    mix = N.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs["Fac"].default_value = 1.0
    L.new(att.outputs["Color"], mix.inputs["Color1"])
    L.new(oi.outputs["Color"], mix.inputs["Color2"])
    L.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.42
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.42
        bsdf.inputs["Subsurface Radius"].default_value = (0.06, 0.035, 0.035)
        bsdf.inputs["Subsurface Scale"].default_value = 0.01
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.36
    mat.use_backface_culling = False
    return mat


def mat_stamens():
    mat = bpy.data.materials.new("Fiore_Stami")
    mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    bsdf = _principled(mat)
    _attr_color(N, L, bsdf)
    bsdf.inputs["Roughness"].default_value = 0.5
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.12
        bsdf.inputs["Subsurface Radius"].default_value = (0.05, 0.04, 0.02)
    return mat


def mat_calyx():
    mat = bpy.data.materials.new("Fiore_Calice")
    mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    bsdf = _principled(mat)
    _attr_color(N, L, bsdf)
    bsdf.inputs["Roughness"].default_value = 0.68
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.10
    return mat


def mat_young_leaf():
    mat = bpy.data.materials.new("Foglia_Giovane")
    mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    bsdf = _principled(mat)
    _attr_color(N, L, bsdf)
    bsdf.inputs["Roughness"].default_value = 0.45
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.25
        bsdf.inputs["Subsurface Radius"].default_value = (0.10, 0.16, 0.05)
        bsdf.inputs["Subsurface Scale"].default_value = 0.01
    mat.use_backface_culling = False
    return mat


def mat_ground():
    mat = bpy.data.materials.new("Terreno")
    mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    bsdf = _principled(mat)
    tc = N.new("ShaderNodeTexCoord")
    att = N.new("ShaderNodeAttribute")
    att.attribute_type = "GEOMETRY"
    att.attribute_name = "Colore"
    # colore di base: attributo (variazioni) x rumore terra
    n1 = N.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 7.0
    n1.inputs["Detail"].default_value = 12.0
    L.new(tc.outputs["Object"], n1.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.085, 0.062, 0.036, 1)
    ramp.color_ramp.elements[1].color = (0.230, 0.180, 0.100, 1)
    L.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    mix = N.new("ShaderNodeMixRGB")
    mix.blend_type = "MIX"
    mix.inputs["Fac"].default_value = 0.35
    L.new(att.outputs["Color"], mix.inputs["Color1"])
    L.new(ramp.outputs["Color"], mix.inputs["Color2"])
    # muschio/erba rada nelle chiazze piu' umide
    mossn = N.new("ShaderNodeTexNoise")
    mossn.inputs["Scale"].default_value = 3.5
    mossn.inputs["Detail"].default_value = 6.0
    L.new(tc.outputs["Object"], mossn.inputs["Vector"])
    mossramp = N.new("ShaderNodeValToRGB")
    mossramp.color_ramp.elements[0].position = 0.44
    mossramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    mossramp.color_ramp.elements[1].position = 0.62
    mossramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    L.new(mossn.outputs["Fac"], mossramp.inputs["Fac"])
    mossmix = N.new("ShaderNodeMixRGB")
    mossmix.inputs["Color2"].default_value = (0.048, 0.080, 0.024, 1)
    L.new(mix.outputs["Color"], mossmix.inputs["Color1"])
    mossfac = N.new("ShaderNodeMath")
    mossfac.operation = "MULTIPLY"
    mossfac.inputs[1].default_value = 0.24
    L.new(mossramp.outputs["Color"], mossfac.inputs[0])
    L.new(mossfac.outputs["Value"], mossmix.inputs["Fac"])
    L.new(mossmix.outputs["Color"], bsdf.inputs["Base Color"])
    # bump fine
    n2 = N.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 60.0
    n2.inputs["Detail"].default_value = 8.0
    L.new(tc.outputs["Object"], n2.inputs["Vector"])
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.45
    bump.inputs["Distance"].default_value = 0.01
    L.new(n2.outputs["Fac"], bump.inputs["Height"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.95
    return mat


def mat_fallen_petals():
    mat = bpy.data.materials.new("Petali_Caduti")
    mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    bsdf = _principled(mat)
    _attr_color(N, L, bsdf)
    bsdf.inputs["Roughness"].default_value = 0.62
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.22
    mat.use_backface_culling = False
    return mat


def mat_grass():
    mat = bpy.data.materials.new("Erba")
    mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    bsdf = _principled(mat)
    _attr_color(N, L, bsdf)
    bsdf.inputs["Roughness"].default_value = 0.72
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.18
        bsdf.inputs["Subsurface Radius"].default_value = (0.06, 0.12, 0.03)
    mat.use_backface_culling = False
    return mat


# ----------------------------------------------------------------------------
# Cielo, luce, camera
# ----------------------------------------------------------------------------
def setup_world_and_lights(coll):
    sun_data = bpy.data.lights.new("Sole", "SUN")
    sun_data.energy = 3.6
    sun_data.angle = math.radians(1.6)
    sun_data.color = (1.0, 0.96, 0.90)
    sun = bpy.data.objects.new("Sole", sun_data)
    sun.rotation_euler = (math.radians(52), 0, math.radians(38))
    coll.objects.link(sun)

    # luce d'ambiente laterale (rimbalzo caldo sul lato in ombra)
    fill_data = bpy.data.lights.new("Rimbalzo", "AREA")
    fill_data.energy = 420.0
    fill_data.size = 9.0
    fill_data.color = (0.90, 0.93, 1.0)
    fill = bpy.data.objects.new("Rimbalzo", fill_data)
    fill.location = (-9.0, 7.0, 5.0)
    fill.rotation_euler = (Vector((0, 0, 3.2)) - fill.location).to_track_quat("-Z", "Y").to_euler()
    coll.objects.link(fill)

    world = bpy.data.worlds.new("Mondo_Cielo")
    world.use_nodes = True
    nt = world.node_tree
    N, L = nt.nodes, nt.links
    out = N["World Output"]
    bg = N["Background"]
    sky = N.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_elevation = math.radians(52)
    sky.sun_rotation = math.radians(38)
    sky.sun_disc = False
    bg.inputs["Strength"].default_value = 0.55
    L.new(sky.outputs["Color"], bg.inputs["Color"])
    # sfondo visto dalla camera: gradiente tenue, non distrae dall'albero
    grad = N.new("ShaderNodeTexGradient")
    grad.gradient_type = "LINEAR"
    mapn = N.new("ShaderNodeMapping")
    mapn.inputs["Rotation"].default_value = (0, math.radians(90), 0)
    tc = N.new("ShaderNodeTexCoord")
    L.new(tc.outputs["Generated"], mapn.inputs["Vector"])
    L.new(mapn.outputs["Vector"], grad.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.86, 0.90, 0.95, 1)
    ramp.color_ramp.elements[1].color = (0.44, 0.62, 0.88, 1)
    L.new(grad.outputs["Fac"], ramp.inputs["Fac"])
    flat = N.new("ShaderNodeBackground")
    flat.inputs["Strength"].default_value = 1.15
    L.new(ramp.outputs["Color"], flat.inputs["Color"])
    lp = N.new("ShaderNodeLightPath")
    mixs = N.new("ShaderNodeMixShader")
    L.new(bg.outputs["Background"], mixs.inputs[1])
    L.new(flat.outputs["Background"], mixs.inputs[2])
    L.new(lp.outputs["Is Camera Ray"], mixs.inputs["Fac"])
    L.new(mixs.outputs["Shader"], out.inputs["Surface"])
    bpy.context.scene.world = world


def setup_camera(coll):
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 52.0
    cam_data.clip_start = 0.05
    cam_data.clip_end = 300.0
    cam = bpy.data.objects.new("Camera", cam_data)
    cam.location = Vector((9.8, -11.5, 5.25))
    target = Vector((0.0, 0.0, 3.35))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    coll.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


# ----------------------------------------------------------------------------
# Costruzione
# ----------------------------------------------------------------------------
WB = Buf(use_uv=True)                       # legno (fusto + rami + radici)
WOOD_COL = rgb(0.42, 0.36, 0.32)
WOOD_COL_TIP = rgb(0.36, 0.30, 0.25)
BRANCH_END = MAX_BRANCHES


def place_clusters(coll):
    """Distribuisce i mazzetti fioriti lungo il legno fine, come oggetti istanziati."""
    variants = []
    for i in range(12):
        random.seed(SEED + 100 + i)
        buf, n_blooms = build_cluster_variant(i)
        me = to_mesh("Mazzetto_%02d" % (i + 1), buf, smooth=True)
        for m in (mat_petals(), mat_stamens(), mat_calyx(), mat_young_leaf()):
            me.materials.append(m)
        variants.append((me, buf.nverts(), n_blooms))
    random.seed(SEED + 500)

    # candidati: (punto, direzione del rametto, raggio locale, profondita')
    cand = []
    for p0, p1, sd, depth, radius in SEGMENTS:
        if depth >= FLOWER_MIN_DEPTH:
            cand.append((p0, p1, sd, depth, radius))
    tot_len = sum((c[1] - c[0]).length for c in cand)
    step = max(CLUSTER_SPACING, tot_len / MAX_CLUSTERS)
    log("  legno fine: %d segmenti, %.0f m -> mazzetti ogni %.3f m"
        % (len(cand), tot_len, step))

    # ordina i candidati dal centro verso l'esterno per un riempimento uniforme
    plan = []
    for p0, p1, sd, depth, radius in cand:
        seg_len = (p1 - p0).length
        if depth == 1:
            step_d = step * 4.5      # sui rami maestri solo qualche mazzetto
        elif depth == 2:
            step_d = step * 4.0
        elif depth == 3:
            step_d = step * 2.5
        else:
            step_d = step
        n_cl = int(seg_len / step_d)
        if random.random() < (seg_len / step_d) - n_cl:
            n_cl += 1
        for _ in range(n_cl):
            t = random.random()
            p = p0.lerp(p1, t)
            plan.append((p, sd, radius, depth))
    # punte dei rami: un mazzetto garantito (piu' qualcuno sui rametti grossi)
    for p0, p1, sd, depth, radius in TIPS:
        if len(plan) < MAX_CLUSTERS:
            plan.append((p1 - sd * 0.006, sd, radius, depth))
    # dardi sul legno grosso
    for p, sd, depth in SPURS:
        if random.random() < 0.45:
            plan.append((p, sd, 0.0, depth))
    if len(plan) > MAX_CLUSTERS:
        random.shuffle(plan)
        plan = plan[:MAX_CLUSTERS]

    coll_flowers = bpy.data.collections.new("Fioritura")
    bpy.context.scene.collection.children.link(coll_flowers)

    n_flowers = 0
    n_blooms = 0
    for i, (p, sd, radius, depth) in enumerate(plan):
        me, nv, nb = variants[random.randrange(len(variants))]
        n_blooms += nb
        # direzione del mazzetto: verso l'esterno, un po' verso il basso
        out = Vector((p.x, p.y, 0.0))
        if out.length > 1e-4:
            out.normalize()
        d = (out * rr(0.35, 0.85) + sd * rr(0.15, 0.45)
             + Vector((0, 0, rr(-0.75, -0.10)))).normalized()
        ob = bpy.data.objects.new("Mazzetto_%05d" % i, me)
        roll = rr(0, 6.28)
        s = rr(*CLUSTER_SCALE)
        ob.matrix_world = (Matrix.Translation(p) @ basis_from_dir(d, roll)
                           @ Matrix.Diagonal((s, s, s, 1.0)))
        # colore per oggetto: da bianco puro a rosa carico
        tone = random.random()
        if tone < 0.34:
            oc = rgb(1.0, rr(0.80, 0.92), rr(0.86, 0.95))
        elif tone < 0.75:
            oc = rgb(1.0, rr(0.62, 0.80), rr(0.74, 0.90))
        else:
            oc = rgb(rr(0.96, 1.0), rr(0.48, 0.64), rr(0.62, 0.78))
        ob.color = oc
        coll_flowers.objects.link(ob)
        n_flowers += nv
    log("  mazzetti: %d oggetti, %d vertici di fiori (mesh condivise)"
        % (len(plan), n_flowers))
    log("  fiori e gemme: ~%d" % n_blooms)
    log("  vertici totali scena (legno + terreno + fiori): ~%d"
        % (n_flowers + WB.nverts() + 400000))
    return len(plan), n_blooms


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_render = "--render" in argv
    quick = "--quick" in argv
    samples = None
    res = None
    if "--samples" in argv:
        samples = int(argv[argv.index("--samples") + 1])
    if "--res" in argv:
        res = argv[argv.index("--res") + 1]
    if "--no-render" in argv:
        do_render = False
    denoise = "--denoise" in argv

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    coll_tree = bpy.data.collections.new("Ciliegio")
    scene.collection.children.link(coll_tree)

    log("Costruzione struttura (fusto, radici, branche)...")
    build_trunk_and_roots()
    log("  rami: %d, vertici legno: %d" % (BRANCHES, WB.nverts()))
    log("  segmenti di legno fine: %d, dardi: %d"
        % (sum(1 for s in SEGMENTS if s[3] >= FLOWER_MIN_DEPTH), len(SPURS)))

    wood_me = to_mesh("Tronco_Rami_Radici", WB, smooth=True)
    wood_me.materials.append(mat_bark())
    wood_ob = bpy.data.objects.new("Tronco_Rami_Radici", wood_me)
    coll_tree.objects.link(wood_ob)

    coll_ground = bpy.data.collections.new("Terreno")
    scene.collection.children.link(coll_ground)

    log("Terreno...")
    gme = to_mesh("Terreno", build_ground(), smooth=True)
    gme.materials.append(mat_ground())
    gob = bpy.data.objects.new("Terreno", gme)
    coll_ground.objects.link(gob)

    pme = to_mesh("Petali_Caduti", scatter_ground_petals(), smooth=True, up_faces=True)
    pme.materials.append(mat_fallen_petals())
    pob = bpy.data.objects.new("Petali_Caduti", pme)
    coll_ground.objects.link(pob)

    tme = to_mesh("Erba", build_grass_tufts(), smooth=False)
    tme.materials.append(mat_grass())
    tob = bpy.data.objects.new("Erba", tme)
    coll_ground.objects.link(tob)

    sme = to_mesh("Sassi", build_stones(), smooth=True)
    sme.materials.append(mat_ground())
    sob = bpy.data.objects.new("Sassi", sme)
    coll_ground.objects.link(sob)

    log("Fioritura...")
    n_cl, n_bl = place_clusters(coll_tree)
    log("  fioritura: %d mazzetti, ~%d fiori e gemme" % (n_cl, n_bl))

    setup_world_and_lights(coll_tree)
    setup_camera(coll_tree)

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 48 if not quick else 16
    # Il denoising (OpenImageDenoise) aggiunge parecchia memoria al picco del
    # render: con ~48 M di vertici di fiori conviene attivarlo solo su macchine
    # con molta RAM (`-- --denoise`), altrimenti si renderizza con piu' campioni.
    scene.cycles.use_denoising = denoise
    scene.cycles.max_bounces = 8
    scene.cycles.transparent_max_bounces = 8
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1120
    if res:
        w, h = res.lower().split("x")
        scene.render.resolution_x = int(w)
        scene.render.resolution_y = int(h)
    if samples:
        scene.cycles.samples = samples
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.compression = 70
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.render.film_transparent = False

    log("Salvataggio %s" % OUT_BLEND)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    log("  dimensione: %.1f MB" % (os.path.getsize(OUT_BLEND) / 1e6))

    if do_render:
        scene.render.filepath = OUT_PREVIEW
        log("Render anteprima (Cycles CPU, %d campioni)..."
            % scene.cycles.samples)
        bpy.ops.render.render(write_still=True)
        log("  anteprima: %.1f MB" % (os.path.getsize(OUT_PREVIEW) / 1e6))


if __name__ == "__main__":
    main()
