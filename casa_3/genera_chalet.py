"""
Genera la BASE di uno chalet alpino 3D e salva il file Blender `chalet.blend`.

Modello: chalet di montagna a due piani — zoccolo in pietra, corpo in legno
con tavole orizzontali e grande tetto a due falde con gronde sporgenti.
Questa è la prima versione del modello: contiene solo la base della casa,
senza troppi dettagli (niente balconi, persiane, comignolo, interni o
giardino). La geometria e i pochi materiali sono tutti procedurali:
nessuna geometria importata, nessuna texture esterna.

Contenuto del modello (per ora)
-------------------------------
  * zoccolo in pietra (sporge 6 cm dal filo dei muri) con gradinata
    d'ingresso in pietra
  * corpo in legno su due piani: muri con spessore reale di 28 cm e vani
    passanti (finestre e porta con spalle vere), timpani in legno
  * tetto a due falde con tavole scure, gronde sporgenti (95 cm sulle
    facciate, 60 cm sui timpani) e colmo in legno
  * serramenti ridotti all'essenziale: vetri scuri incassati, telai piatti
    in legno scuro e porta d'ingresso massiccia in legno
  * terreno a prato, cielo procedurale (Nishita), sole, camera, Cycles + AgX

Esecuzione (richiede il modulo `bpy` di Blender 4.x):
    python3 genera_chalet.py            # costruisce e salva chalet.blend
    python3 genera_chalet.py --render   # ... e renderizza anche anteprima.png
    python3 genera_chalet.py --quick    # render veloce di controllo
"""

import math
import os
import random
import sys
import time

import bpy
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_BLEND = os.path.join(HERE, "chalet.blend")
OUT_PNG = os.path.join(HERE, "anteprima.png")

SEED = 20261013          # seme casuale (per ora poca casualita', ma deterministica)
random.seed(SEED)

PI = math.pi

# ---------------------------------------------------------------------------
# Parametri del progetto (unita': metri)
# ---------------------------------------------------------------------------
W_X = 9.00               # larghezza del corpo (facciata principale, asse X)
D_Y = 7.00               # profondita' del corpo (asse Y)
T_WALL = 0.28            # spessore dei muri di legno

Z_PLINTH = 0.84          # quota del piano terra = sommita' dello zoccolo
Z_TOP = 7.24             # sommita' dei muri (due piani)

PITCH = math.radians(26.0)         # pendenza delle falde
T_ROOF = 0.22            # spessore delle falde
EAVES_F = 0.95           # sporto di gronda sulle facciate (direzione Y)
EAVES_G = 0.60           # sporto del tetto sui timpani (direzione X)

TAN_P = math.tan(PITCH)
COS_P = math.cos(PITCH)
SIN_P = math.sin(PITCH)
Z_RIDGE_B = Z_TOP + (D_Y / 2.0) * TAN_P      # quota inferiore del colmo


# ---------------------------------------------------------------------------
# Piccoli strumenti: buffer di mesh
# ---------------------------------------------------------------------------
class Buf:
    """Accumula vertici e facce per un oggetto con un solo materiale."""

    def __init__(self, name, mat):
        self.name = name
        self.mat = mat
        self.V = []
        self.F = []

    def vert(self, p):
        self.V.append((p.x, p.y, p.z))
        return len(self.V) - 1

    def quad(self, a, b, c, d):
        if len({a, b, c, d}) == 4:
            self.F.append((a, b, c, d))

    def tri(self, a, b, c):
        if len({a, b, c}) == 3:
            self.F.append((a, b, c))


def add_box(buf, center, size, rot=None):
    """Parallelepipedo centrato in `center`, semi-dimensioni `size`, opz. ruotato."""
    hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    pts = []
    for sz in (-1, 1):
        for sy in (-1, 1):
            for sx in (-1, 1):
                p = Vector((sx * hx, sy * hy, sz * hz))
                if rot is not None:
                    p = rot @ p
                pts.append(p + Vector(center))
    # indici: 0(-,-,-) 1(+,-,-) 2(-,+,-) 3(+,+,-) 4(-,-,+) 5(+,-,+) 6(-,+,+) 7(+,+,+)
    idx = [buf.vert(p) for p in pts]
    buf.quad(idx[4], idx[5], idx[7], idx[6])   # +z
    buf.quad(idx[0], idx[2], idx[3], idx[1])   # -z
    buf.quad(idx[3], idx[7], idx[5], idx[1])   # +x
    buf.quad(idx[2], idx[0], idx[4], idx[6])   # -x
    buf.quad(idx[6], idx[7], idx[3], idx[2])   # +y
    buf.quad(idx[0], idx[1], idx[5], idx[4])   # -y


def box_mm(buf, pa, pb):
    """Parallelepipedo asse-allineato definito da due angoli opposti."""
    p0 = Vector((min(pa.x, pb.x), min(pa.y, pb.y), min(pa.z, pb.z)))
    p1 = Vector((max(pa.x, pb.x), max(pa.y, pb.y), max(pa.z, pb.z)))
    center = (p0 + p1) / 2.0
    size = p1 - p0
    if size.x > 1e-9 and size.y > 1e-9 and size.z > 1e-9:
        add_box(buf, center, size)


def rot_from_basis(xa, ya, za):
    """Matrice 3x3 con colonne xa, ya, za (base destrorsa)."""
    return Matrix((xa, ya, za)).transposed()


# ---------------------------------------------------------------------------
# Muri con spessore e vani passanti
# ---------------------------------------------------------------------------
def split_rects(rects, hole):
    """Sottrae il rettangolo `hole` (u0,u1,v0,v1) dall'elenco di rettangoli."""
    h0, h1, k0, k1 = hole
    out = []
    for (r0, r1, v0, v1) in rects:
        if h1 <= r0 or h0 >= r1 or k1 <= v0 or k0 >= v1:
            out.append((r0, r1, v0, v1))
            continue
        lo, hi = max(r0, h0), min(r1, h1)
        if h0 > r0:
            out.append((r0, h0, v0, v1))
        if h1 < r1:
            out.append((h1, r1, v0, v1))
        if k0 > v0:
            out.append((lo, hi, v0, k0))
        if k1 < v1:
            out.append((lo, hi, k1, v1))
    return out


def wall(buf, o, u_ax, w_ax, L, z0, z1, holes):
    """Muro da `z0` a `z1`, spessore T_WALL, con fori passanti (u0,u1,z0,z1).

    `o` e' il punto medio del filo esterno inferiore della facciata, `u_ax` la
    direzione della facciata (lunghezza L, con u centrata su 0), `w_ax` il
    verso verso l'interno del muro.
    """
    rects = [(-L / 2.0, L / 2.0, z0, z1)]
    for h in holes:
        rects = split_rects(rects, h)
    for (r0, r1, v0, v1) in rects:
        pa = o + u_ax * r0 + Vector((0.0, 0.0, v0))
        pb = o + u_ax * r1 + w_ax * T_WALL + Vector((0.0, 0.0, v1))
        box_mm(buf, pa, pb)


def opening_fill(buf_frame, buf_glass, o, u_ax, n_out, u0, u1, z0, z1,
                 glass=True, bottom=True):
    """Telaio piatto attorno al vano + vetro incassato (o nulla per la porta)."""
    bw, proud, back = 0.09, 0.05, 0.03

    def band(ua, ub, za, zb):
        pa = o + u_ax * ua + n_out * (-back) + Vector((0.0, 0.0, za))
        pb = o + u_ax * ub + n_out * proud + Vector((0.0, 0.0, zb))
        box_mm(buf_frame, pa, pb)

    band(u0 - bw, u1 + bw, z1, z1 + bw)            # sopra
    if bottom:
        band(u0 - bw, u1 + bw, z0 - bw, z0)        # sotto
    band(u0 - bw, u0, z0, z1 + bw)                 # sinistra
    band(u1, u1 + bw, z0, z1 + bw)                 # destra
    if glass:
        recess = 0.14
        pa = o + u_ax * (u0 + 0.05) + n_out * (-recess) + Vector((0.0, 0.0, z0 + 0.05))
        pb = o + u_ax * (u1 - 0.05) + n_out * (-(recess + 0.04)) + Vector((0.0, 0.0, z1 - 0.05))
        box_mm(buf_glass, pa, pb)


# ---------------------------------------------------------------------------
# Materiali procedurali
# ---------------------------------------------------------------------------
def principled(name, base, rough, metallic=0.0, ior=1.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["IOR"].default_value = ior
    return m, nt, bsdf


def node(nt, ntype, x, y):
    n = nt.nodes.new(ntype)
    n.location = (x, y)
    return n


def ramp(nt, stops, x, y):
    """ColorRamp con coppie (posizione, colore rgb)."""
    n = node(nt, "ShaderNodeValToRGB", x, y)
    cr = n.color_ramp
    cr.elements[0].position = stops[0][0]
    cr.elements[0].color = (*stops[0][1], 1.0)
    for pos, col in stops[1:]:
        e = cr.elements.new(pos)
        e.color = (*col, 1.0)
    return n


def make_materials():
    mats = {}

    # --- pietra dello zoccolo ------------------------------------------------
    m, nt, b = principled("Pietra", (0.45, 0.43, 0.40), 0.92)
    co = node(nt, "ShaderNodeTexCoord", -900, 0)
    vo = node(nt, "ShaderNodeTexVoronoi", -650, 120)
    vo.feature = "F1"
    vo.inputs["Scale"].default_value = 2.6
    vo.inputs["Randomness"].default_value = 1.0
    rp = ramp(nt, [(0.0, (0.30, 0.29, 0.27)), (1.0, (0.52, 0.50, 0.46))], -360, 120)
    bp = node(nt, "ShaderNodeBump", 20, -260)
    bp.inputs["Strength"].default_value = 0.55
    bp.inputs["Distance"].default_value = 0.12
    nt.links.new(co.outputs["Object"], vo.inputs["Vector"])
    nt.links.new(vo.outputs["Distance"], rp.inputs["Fac"])
    nt.links.new(rp.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(vo.outputs["Distance"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    mats["pietra"] = m

    # --- legno delle pareti: tavole orizzontali ------------------------------
    m, nt, b = principled("Legno_pareti", (0.36, 0.235, 0.14), 0.62)
    co = node(nt, "ShaderNodeTexCoord", -900, 0)
    wv = node(nt, "ShaderNodeTexWave", -650, 120)
    wv.wave_type = "BANDS"
    wv.bands_direction = "Z"
    wv.inputs["Scale"].default_value = 2.7          # tavola alta ~37 cm
    wv.inputs["Distortion"].default_value = 0.30
    wv.inputs["Detail"].default_value = 3.0
    rw = ramp(nt, [(0.00, (0.285, 0.180, 0.103)),
                   (0.485, (0.285, 0.180, 0.103)),
                   (0.515, (0.395, 0.260, 0.152)),
                   (1.00, (0.395, 0.260, 0.152))], -380, 120)
    mp = node(nt, "ShaderNodeMapping", -650, -160)
    mp.inputs["Scale"].default_value = (60.0, 3.0, 3.0)
    nz = node(nt, "ShaderNodeTexNoise", -440, -160)     # venature lunghe
    nz.inputs["Scale"].default_value = 1.0
    nz.inputs["Detail"].default_value = 6.0
    mr = node(nt, "ShaderNodeMapRange", -160, -160)
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 1.0
    mr.inputs["To Min"].default_value = 0.55
    mr.inputs["To Max"].default_value = 0.72
    bw_ = node(nt, "ShaderNodeBump", 20, -300)
    bw_.inputs["Strength"].default_value = 0.28
    bw_.inputs["Distance"].default_value = 0.03
    nt.links.new(co.outputs["Object"], wv.inputs["Vector"])
    nt.links.new(co.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(wv.outputs["Fac"], rw.inputs["Fac"])
    nt.links.new(rw.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    nt.links.new(wv.outputs["Fac"], bw_.inputs["Height"])
    nt.links.new(bw_.outputs["Normal"], b.inputs["Normal"])
    mats["legno"] = m

    # --- legno scuro: falde del tetto e telai --------------------------------
    m, nt, b = principled("Legno_scuro", (0.155, 0.108, 0.075), 0.70)
    co = node(nt, "ShaderNodeTexCoord", -900, 0)
    wv = node(nt, "ShaderNodeTexWave", -650, 120)
    wv.wave_type = "BANDS"
    wv.bands_direction = "Y"
    wv.inputs["Scale"].default_value = 5.5          # tavola larga ~18 cm
    wv.inputs["Distortion"].default_value = 0.20
    rw = ramp(nt, [(0.00, (0.120, 0.082, 0.056)),
                   (0.485, (0.120, 0.082, 0.056)),
                   (0.515, (0.180, 0.125, 0.086)),
                   (1.00, (0.180, 0.125, 0.086))], -380, 120)
    bp = node(nt, "ShaderNodeBump", 20, -260)
    bp.inputs["Strength"].default_value = 0.30
    bp.inputs["Distance"].default_value = 0.03
    nt.links.new(co.outputs["Object"], wv.inputs["Vector"])
    nt.links.new(wv.outputs["Fac"], rw.inputs["Fac"])
    nt.links.new(rw.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    mats["legno_scuro"] = m

    # --- legno della porta ----------------------------------------------------
    m, nt, b = principled("Legno_porta", (0.33, 0.20, 0.115), 0.50)
    co = node(nt, "ShaderNodeTexCoord", -900, 0)
    wv = node(nt, "ShaderNodeTexWave", -650, 120)
    wv.wave_type = "BANDS"
    wv.bands_direction = "X"
    wv.inputs["Scale"].default_value = 8.0
    wv.inputs["Distortion"].default_value = 1.6
    wv.inputs["Detail"].default_value = 6.0
    rw = ramp(nt, [(0.0, (0.255, 0.150, 0.082)), (1.0, (0.375, 0.235, 0.132))],
              -380, 120)
    nt.links.new(co.outputs["Object"], wv.inputs["Vector"])
    nt.links.new(wv.outputs["Fac"], rw.inputs["Fac"])
    nt.links.new(rw.outputs["Color"], b.inputs["Base Color"])
    mats["legno_porta"] = m

    # --- vetro scuro ----------------------------------------------------------
    m, nt, b = principled("Vetro", (0.055, 0.075, 0.085), 0.06, ior=1.45)
    mats["vetro"] = m

    # --- prato ----------------------------------------------------------------
    m, nt, b = principled("Prato", (0.16, 0.22, 0.08), 1.0)
    co = node(nt, "ShaderNodeTexCoord", -900, 0)
    n1 = node(nt, "ShaderNodeTexNoise", -650, 120)
    n1.inputs["Scale"].default_value = 7.0
    n1.inputs["Detail"].default_value = 8.0
    n2 = node(nt, "ShaderNodeTexNoise", -650, -140)
    n2.inputs["Scale"].default_value = 0.55           # macchie piu' ampie
    n2.inputs["Detail"].default_value = 4.0
    mix = node(nt, "ShaderNodeMath", -420, 40)
    mix.operation = "MULTIPLY"
    mix.inputs[0].default_value = 0.7
    rg = ramp(nt, [(0.00, (0.085, 0.135, 0.045)),
                   (0.45, (0.150, 0.215, 0.070)),
                   (0.75, (0.205, 0.255, 0.095)),
                   (1.00, (0.290, 0.295, 0.125))], -220, 40)
    nt.links.new(co.outputs["Object"], n1.inputs["Vector"])
    nt.links.new(co.outputs["Object"], n2.inputs["Vector"])
    nt.links.new(n1.outputs["Fac"], mix.inputs[1])
    nt.links.new(n2.outputs["Fac"], mix.inputs[0])
    nt.links.new(mix.outputs["Value"], rg.inputs["Fac"])
    nt.links.new(rg.outputs["Color"], b.inputs["Base Color"])
    mats["prato"] = m

    return mats


# ---------------------------------------------------------------------------
# Costruzione della geometria
# ---------------------------------------------------------------------------
def build_zoccolo(B):
    """Basamento in pietra sporgente e gradinata d'ingresso."""
    buf = B["pietra"]
    out = 0.06
    box_mm(buf,
           Vector((-(W_X / 2 + out), -(D_Y / 2 + out), -0.60)),
           Vector(((W_X / 2 + out), (D_Y / 2 + out), Z_PLINTH)))
    # gradinata: 4 gradini davanti alla porta (alzata 21 cm, pedata 38 cm)
    rise, tread, wstep = Z_PLINTH / 4.0, 0.38, 1.80
    yf = -(D_Y / 2 + out)
    for i in range(4):
        box_mm(buf,
               Vector((-wstep / 2, yf - (i + 1) * tread, -0.20)),
               Vector((wstep / 2, yf - i * tread, Z_PLINTH - (i + 1) * rise)))


def facciate():
    """Definizione delle quattro facciate e dei loro vani.

    Ogni facciata: origine `o` (punto medio del filo esterno inferiore),
    direzione `u` (lungo la facciata, coordinate centrate su 0), `n` (normale
    uscente), `w` (verso l'interno). I fori sono (u0, u1, z0, z1, tipo) con
    tipo "finestra" o "porta".
    """
    z_wg0, z_wg1 = 2.09, 4.19        # finestre piano terra
    z_wu0, z_wu1 = 4.99, 6.69        # finestre piano primo
    door = (-0.62, 0.62, Z_PLINTH, Z_PLINTH + 2.10, "porta")

    front = {
        "o": Vector((0.0, -(D_Y / 2), 0.0)),
        "u": Vector((1, 0, 0)), "n": Vector((0, -1, 0)),
        "w": Vector((0, 1, 0)), "L": W_X,
        "fori": [door,
                 (-3.95, -2.15, z_wg0, z_wg1, "finestra"),
                 (2.15, 3.95, z_wg0, z_wg1, "finestra"),
                 (-3.55, -2.15, z_wu0, z_wu1, "finestra"),
                 (-0.70, 0.70, z_wu0, z_wu1, "finestra"),
                 (2.15, 3.55, z_wu0, z_wu1, "finestra")],
    }
    back = {
        "o": Vector((0.0, (D_Y / 2), 0.0)),
        "u": Vector((1, 0, 0)), "n": Vector((0, 1, 0)),
        "w": Vector((0, -1, 0)), "L": W_X,
        "fori": [(-3.30, -1.70, z_wg0, z_wg1, "finestra"),
                 (1.70, 3.30, z_wg0, z_wg1, "finestra"),
                 (-3.40, -2.00, z_wu0, z_wu1, "finestra"),
                 (-0.70, 0.70, z_wu0, z_wu1, "finestra"),
                 (2.00, 3.40, z_wu0, z_wu1, "finestra")],
    }
    west = {
        "o": Vector((-(W_X / 2), 0.0, 0.0)),
        "u": Vector((0, 1, 0)), "n": Vector((-1, 0, 0)),
        "w": Vector((1, 0, 0)), "L": D_Y,
        "fori": [(-1.50, 0.30, z_wg0, z_wg1, "finestra"),
                 (-2.70, -1.30, z_wu0, z_wu1, "finestra"),
                 (1.00, 2.40, z_wu0, z_wu1, "finestra")],
    }
    east = {
        "o": Vector(((W_X / 2), 0.0, 0.0)),
        "u": Vector((0, 1, 0)), "n": Vector((1, 0, 0)),
        "w": Vector((-1, 0, 0)), "L": D_Y,
        "fori": [(-0.30, 1.50, z_wg0, z_wg1, "finestra"),
                 (-2.40, -1.00, z_wu0, z_wu1, "finestra"),
                 (1.30, 2.70, z_wu0, z_wu1, "finestra")],
    }
    return [front, back, west, east]


def build_muri(B):
    """Muri di legno con vani passanti, tamponamenti e porta."""
    for fr in facciate():
        o, u_ax, w_ax = fr["o"], fr["u"], fr["w"]
        wall(B["legno_muri"], o, u_ax, w_ax, fr["L"],
             Z_PLINTH - 0.03, Z_TOP,
             [(h[0], h[1], h[2], h[3]) for h in fr["fori"]])
        for (u0, u1, z0, z1, tipo) in fr["fori"]:
            if tipo == "porta":
                opening_fill(B["telai"], None, o, u_ax, fr["n"],
                             u0, u1, z0, z1, glass=False, bottom=False)
                # anta massiccia in legno
                pa = o + u_ax * (u0 + 0.05) + fr["n"] * (-0.05) + Vector((0, 0, z0 + 0.02))
                pb = o + u_ax * (u1 - 0.05) + fr["n"] * (-0.16) + Vector((0, 0, z1))
                box_mm(B["porta"], pa, pb)
            else:
                opening_fill(B["telai"], B["vetro"], o, u_ax, fr["n"],
                             u0, u1, z0, z1)


def build_timpani(B):
    """Timpani di legno sui due prospetti corti (sotto le falde)."""
    buf = B["legno_timp"]
    zb = Z_TOP - 0.02
    za = Z_RIDGE_B + 0.02          # si incastra sotto le falde
    for sign in (1.0, -1.0):       # 1: timpano est (+X), -1: ovest (-X)
        x_out = sign * (W_X / 2)
        x_in = sign * (W_X / 2 - T_WALL)
        a0, b0, c0 = (buf.vert(Vector((x_in, -D_Y / 2, zb))),
                      buf.vert(Vector((x_in, D_Y / 2, zb))),
                      buf.vert(Vector((x_in, 0.0, za))))
        a1, b1, c1 = (buf.vert(Vector((x_out, -D_Y / 2, zb))),
                      buf.vert(Vector((x_out, D_Y / 2, zb))),
                      buf.vert(Vector((x_out, 0.0, za))))
        if sign > 0:
            buf.tri(a1, b1, c1)                 # faccia esterna
            buf.tri(a0, c0, b0)                 # faccia interna
            buf.quad(a0, b0, b1, a1)            # base (nascosta)
            buf.quad(a0, a1, c1, c0)            # spiovente sud
            buf.quad(c0, c1, b1, b0)            # spiovente nord
        else:
            buf.tri(a1, c1, b1)
            buf.tri(a0, b0, c0)
            buf.quad(a0, a1, b1, b0)
            buf.quad(a0, c0, c1, a1)
            buf.quad(c0, b0, b1, c1)


def build_tetto(B):
    """Due falde in tavole con gronde sporgenti e colmo in legno."""
    buf = B["legno_scuro"]
    for sign in (-1.0, 1.0):       # -1: falda sud (fronte), +1: nord
        e = Vector((0.0, sign * (D_Y / 2 + EAVES_F), Z_TOP - EAVES_F * TAN_P))
        r = Vector((0.0, 0.0, Z_RIDGE_B))
        d = (r - e).normalized()                       # direzione della pendenza
        n = Vector((0.0, sign * SIN_P, COS_P))          # normale (verso l'alto)
        ls = (D_Y / 2 + EAVES_F) / COS_P + 0.06         # lunghezza along-pendenza
        center = (e + r) / 2.0 + n * (T_ROOF / 2.0) + d * 0.03
        rot = rot_from_basis(Vector((-sign, 0.0, 0.0)), d, n)
        add_box(buf, center, (W_X + 2.0 * EAVES_G, ls, T_ROOF), rot)
    # colmo
    zc = Z_RIDGE_B + T_ROOF * COS_P + 0.04
    add_box(buf, Vector((0.0, 0.0, zc)),
            (W_X + 2.0 * EAVES_G + 0.04, 0.34, 0.15))


def build_terreno(B):
    """Prato pianeggiante."""
    add_box(B["prato"], Vector((0.0, 0.0, -0.10)), (600.0, 600.0, 0.20))


# ---------------------------------------------------------------------------
# Scena: cielo, sole, camera, render
# ---------------------------------------------------------------------------
SUN_ELEV = 34.0
SUN_AZ = 210.0              # direzione da cui arriva la luce (gradi)


def sun_vector():
    """Direzione di propagazione della luce solare (vettore unitario)."""
    el, az = math.radians(SUN_ELEV), math.radians(SUN_AZ)
    return Vector((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az),
                   -math.sin(el))).normalized()


def setup_scena(root):
    scene = bpy.context.scene
    sd = sun_vector()

    # --- cielo (Nishita, quota di montagna) ----------------------------------
    world = bpy.data.worlds.new("Cielo")
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.location = (-700, 0)
    # Blender 4.x chiama il modello fisico "NISHITA", Blender 5.x lo ha
    # rinominato "MULTIPLE_SCATTERING" (stessi parametri)
    if "NISHITA" in [i.identifier for i in sky.bl_rna.properties["sky_type"].enum_items]:
        sky.sky_type = "NISHITA"
    else:
        sky.sky_type = "MULTIPLE_SCATTERING"
    for attr, val in (("sun_elevation", math.radians(SUN_ELEV)),
                      ("sun_rotation", math.radians(180.0 - SUN_AZ)),
                      ("sun_disc", False),
                      ("altitude", 1200.0),
                      ("air_density", 0.60),
                      ("dust_density", 0.20),      # Blender 4.x
                      ("aerosol_density", 0.20),   # Blender 5.x
                      ("ozone_density", 2.5)):
        if hasattr(sky, attr):
            setattr(sky, attr, val)
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    bg_cam.location = (-380, 120)
    bg_cam.inputs["Strength"].default_value = 0.07
    bg_amb = nt.nodes.new("ShaderNodeBackground")
    bg_amb.location = (-380, -80)
    bg_amb.inputs["Strength"].default_value = 0.012
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

    # --- sole ----------------------------------------------------------------
    light = bpy.data.lights.new("Sole", "SUN")
    light.energy = 11.0
    light.angle = math.radians(0.7)
    light.color = (1.0, 0.94, 0.85)
    lob = bpy.data.objects.new("Sole", light)
    lob.location = -sd * 80.0
    lob.rotation_euler = sd.to_track_quat("-Z", "Y").to_euler()
    root.objects.link(lob)

    # --- camera --------------------------------------------------------------
    cam = bpy.data.cameras.new("Camera")
    cam.lens = 38.0
    cam.clip_end = 800.0
    cam.dof.use_dof = True
    pos = Vector((19.00, -17.00, 7.20))
    target = Vector((0.0, 0.40, 2.90))
    cam.dof.focus_distance = (target - pos).length
    cam.dof.aperture_fstop = 11.0
    cob = bpy.data.objects.new("Camera", cam)
    cob.location = pos
    cob.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    root.objects.link(cob)
    scene.camera = cob

    # --- render --------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Oggetti e buffer
# ---------------------------------------------------------------------------
BUF_SPEC = [
    # (chiave, nome oggetto, materiale, collezione)
    ("pietra", "Zoccolo", "pietra", "Edificio"),
    ("legno_muri", "Muri_legno", "legno", "Edificio"),
    ("legno_timp", "Timpani", "legno", "Edificio"),
    ("telai", "Telai_infissi", "legno_scuro", "Serramenti"),
    ("vetro", "Vetri", "vetro", "Serramenti"),
    ("porta", "Porta_ingresso", "legno_porta", "Serramenti"),
    ("legno_scuro", "Falde", "legno_scuro", "Tetto"),
    ("prato", "Terreno", "prato", "Terreno"),
]


def make_buffers(mats):
    bufs = {}
    for key, name, mat, _coll in BUF_SPEC:
        bufs.setdefault(key, Buf(name, mats[mat]))
    return bufs


def flush_buffers(bufs, colls):
    nv = nf = 0
    for key, name, mat, coll in BUF_SPEC:
        buf = bufs[key]
        me = bpy.data.meshes.new(name)
        me.from_pydata(buf.V, [], buf.F)
        me.validate()
        me.update()
        ob = bpy.data.objects.new(name, me)
        ob.data.materials.append(buf.mat)
        colls[coll].objects.link(ob)
        nv += len(buf.V)
        nf += len(buf.F)
    return nv, nf


# ---------------------------------------------------------------------------
# Righe di comando
# ---------------------------------------------------------------------------
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
    t0 = time.time()
    opts = argomenti()
    bpy.ops.wm.read_factory_settings(use_empty=True)

    root = bpy.data.collections.new("Chalet")
    bpy.context.scene.collection.children.link(root)
    colls = {}
    for nome in ("Edificio", "Tetto", "Serramenti", "Terreno"):
        c = bpy.data.collections.new(nome)
        root.children.link(c)
        colls[nome] = c

    mats = make_materials()
    B = make_buffers(mats)

    print("» zoccolo in pietra e gradinata ...")
    build_zoccolo(B)
    print("» muri di legno con vani, timpani ...")
    build_muri(B)
    build_timpani(B)
    print("» tetto a due falde ...")
    build_tetto(B)
    print("» terreno ...")
    build_terreno(B)

    nv, nf = flush_buffers(B, colls)
    print("   geometria: %d vertici, %d facce" % (nv, nf))

    setup_scena(root)
    if opts["quick"]:
        bpy.context.scene.render.resolution_x = 840
        bpy.context.scene.render.resolution_y = 588
        bpy.context.scene.cycles.samples = 20
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
