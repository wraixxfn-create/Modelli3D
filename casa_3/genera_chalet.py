"""
Genera uno chalet alpino (baita di montagna) 3D altamente rifinito e salva il
file Blender `chalet.blend`.

Tutta la geometria e i materiali sono generati proceduralmente:
  * Muratura del piano terra in pietra rustica alpina con vani passanti,
    cantonali squadrati, architravi in legno massello e davanzali in pietra.
  * Piano superiore e sottotetto in legno di larice a tronchi/travi incastrate
    (costruzione Blockbau tradizionale con incastri d'angolo sporgenti).
  * Balconata panoramica avvolgente con pavimento in tavole di larice,
    balaustre sagomate e traforate con motivi alpini tradizionali, saettoni
    di supporto sagomati e fioriere ricolme di gerani cascanti.
  * Portico d'ingresso coperto con pilastri in legno intagliato, legnaia con
    ciocchi di legna spaccata accatastati, panca rustica in massello, antichi
    sci in legno con bastoncini, slitta alpina e lanterne in ferro battuto.
  * Tetto a due falde con ampia orditura a vista (colmo intagliato, arcarecci,
    travetti sagomati, tavolato), migliaia di scandole in legno posate una a una,
    fermaneve in tronchi con staffe in ferro, grondaie e pluviali in rame,
    grande comignolo in pietra con banderuola segnavento e timpano con trafori.
  * Interni accoglienti visibili attraverso i vetri: Stube con stufa in maiolica
    verde e fuoco/brace accesa, tavolo tirolese con sedie intagliate, giropanca,
    credenza alpina, lampadario in corna, camera da letto con piumone e lampade.
  * Serramenti rifiniti: infissi a riquadri con vetri doppi, scuri a Z in legno,
    ferramenta forgiata, tendine a quadretti tirolesi e pizzo ricamato.
  * Paesaggio alpino: terreno ondulato con rocce e massi di granito con muschio,
    fontana a tronco scavato con cannella in rame e acqua corrente, staccionata
    in tronchi, vialetto in beole irregolari, ciuffi d'erba montana, fiori alpini
    (stelle alpine, genziane, margherite), rododendri, abeti e pini cembri,
    più catena montuosa alpina di sfondo con foschia atmosferica.
  * Cielo procedurale Nishita ad alta quota, sole radente, luci interne e lanterne,
    camera prospettica 42 mm, motore Cycles + AgX.

Esecuzione:
    python3 genera_chalet.py                 # genera chalet.blend
    python3 genera_chalet.py --render        # ... e renderizza anteprima.png
    python3 genera_chalet.py --quick         # render rapido di controllo
    python3 genera_chalet.py --render --samples 80 --res 1500x1050
"""

import math
import os
import random
import sys
import time

import bpy
from mathutils import Vector, Matrix, noise

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_BLEND = os.path.join(HERE, "chalet.blend")
OUT_PNG = os.path.join(HERE, "anteprima.png")

SEED = 20261013
random.seed(SEED)

PI = math.pi
TAU = 2.0 * math.pi

# ---------------------------------------------------------------------------
# Dimensioni e parametri generali del progetto (unità: metri)
# ---------------------------------------------------------------------------
W_X = 9.20               # larghezza del corpo principale (asse X)
D_Y = 7.40               # profondità del corpo (asse Y)
HALF_X = W_X / 2.0       # 4.60
HALF_Y = D_Y / 2.0       # 3.70

T_WALL_STONE = 0.40      # spessore muri in pietra al piano terra
T_WALL_WOOD = 0.28       # spessore pareti in legno al primo piano

Z_GROUND = 0.00          # quota terreno di riferimento
Z_PLINTH = 0.40          # quota pavimento piano terra (sopra lo zoccolo)
H_F0 = 2.80              # altezza interna piano terra
Z_F1 = Z_PLINTH + H_F0   # quota solaio / pavimento primo piano (3.20)
H_F1 = 2.70              # altezza pareti verticali primo piano
Z_EAVE_WALL = Z_F1 + H_F1 # sommità muri perimetrali sotto la gronda (5.90)

# Tetto
PITCH = math.radians(28.0)         # pendenza falde alpine (28 gradi)
TAN_P = math.tan(PITCH)
COS_P = math.cos(PITCH)
SIN_P = math.sin(PITCH)

EAVES_FRONT = 1.35       # sporto di gronda sulle facciate principali (Y)
EAVES_GABLE = 0.95       # sporto del tetto sui timpani (X)
Z_RIDGE_STRUCT = Z_EAVE_WALL + (HALF_Y * TAN_P)   # colmo strutturale (~7.87)

# Balconata panoramica
BALCONY_Z = Z_F1
BALCONY_FRONT_Y = -(HALF_Y + 1.25)   # aggetto verso sud (-4.95)
BALCONY_SIDE_X = -(HALF_X + 1.20)    # aggetto verso ovest (-5.80)

# Portico d'ingresso
PORCH_X0 = -1.20
PORCH_X1 = 1.80
PORCH_Y_FRONT = -(HALF_Y + 1.45)
PORCH_Z_ROOF = Z_F1 + 0.15


# ---------------------------------------------------------------------------
# Utility matematiche e di colore
# ---------------------------------------------------------------------------
def rr(a, b):
    return a + (b - a) * random.random()


def clamp(x, a, b):
    return a if x < a else (b if x > b else x)


def srgb(r, g, b):
    """Conversione da sRGB 0-255 a lineare 0.0-1.0."""
    return tuple((c / 255.0) ** 2.2 for c in (r, g, b))


def jitter_color(col, amount):
    return tuple(clamp(c * (1.0 + rr(-amount, amount)), 0.0, 1.0) for c in col)


def roof_struct_z(y):
    """Quota estradosso travetti a distanza y dal colmo."""
    return Z_RIDGE_STRUCT - abs(y) * TAN_P


def roof_top_z(y):
    """Quota superiore del tavolato / posa scandole."""
    return roof_struct_z(y) + 0.04 / COS_P


def terrain_z(x, y):
    """Quota naturale del terreno alpino con pendenza montuosa e ondulazioni."""
    base = 0.06 * (y + 4.0) + 0.03 * (x - 2.0)
    nz = 0.18 * math.sin(x * 0.18 + 0.4) * math.cos(y * 0.14 - 0.2)
    nz += 0.08 * math.sin(x * 0.42 + y * 0.35)
    dx = max(0.0, abs(x) - (HALF_X + 0.8))
    dy = max(0.0, abs(y) - (HALF_Y + 0.8))
    dist_house = math.sqrt(dx * dx + dy * dy)
    flat_w = clamp(dist_house / 3.0, 0.0, 1.0)
    return (base + nz) * flat_w - 0.04 * (1.0 - flat_w)


# ---------------------------------------------------------------------------
# Contenitore di geometria e facce (Buf)
# ---------------------------------------------------------------------------
class Buf:
    """Buffer di vertici, facce e attributi colore associato a un materiale."""

    __slots__ = ("name", "mat", "V", "F", "S", "C", "use_color", "color")

    def __init__(self, name, mat, use_color=False):
        self.name = name
        self.mat = mat
        self.V = []
        self.F = []
        self.S = []
        self.C = []
        self.use_color = use_color
        self.color = (1.0, 1.0, 1.0)

    def add(self, pts):
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
        b = self.add(pts)
        self.face(range(b, b + len(pts)), smooth)

    def quad_dir(self, p0, p1, p2, p3, want, smooth=False):
        n = (p1 - p0).cross(p3 - p0)
        if n.dot(want) < 0.0:
            p0, p1, p2, p3 = p0, p3, p2, p1
        self.poly((p0, p1, p2, p3), smooth)

    @property
    def nverts(self):
        return len(self.V)


_BOX_FACES = (
    ("-z", (0, 2, 6, 4)),
    ("+z", (1, 5, 7, 3)),
    ("-x", (0, 1, 3, 2)),
    ("+x", (4, 6, 7, 5)),
    ("-y", (0, 4, 5, 1)),
    ("+y", (2, 3, 7, 6)),
)


def add_box_v(buf, o, ax, ay, az, skip=()):
    """Parallelepipedo orientato con origine e tre vettori spigolo."""
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
    """Parallelepipedo allineato agli assi cartesiani."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    add_box_v(buf, p0, (d.x, 0, 0), (0, d.y, 0), (0, 0, d.z), skip)


def add_box_c(buf, center, size, rot=None, skip=()):
    """Parallelepipedo dato centro, dimensioni e rotazione."""
    center = Vector(center)
    sx, sy, sz = size
    ax, ay, az = Vector((sx, 0, 0)), Vector((0, sy, 0)), Vector((0, 0, sz))
    if rot is not None:
        ax, ay, az = rot @ ax, rot @ ay, rot @ az
    o = center - (ax + ay + az) * 0.5
    add_box_v(buf, o, ax, ay, az, skip)


def circle_profile(n, r=1.0, phase=0.0):
    return [
        (math.cos(phase + TAU * i / n) * r, math.sin(phase + TAU * i / n) * r)
        for i in range(n)
    ]


def sweep(buf, frames, profile, closed=True, caps=True, seg_smooth=None):
    """Estrusione di un profilo lungo una sequenza di frame di riferimento."""
    npf = len(profile)
    rings = []
    for fr in frames:
        o, xa, ya, s = fr
        if isinstance(s, (int, float)):
            sx = sy = float(s)
        else:
            sx, sy = float(s[0]), float(s[1])
        rings.append(buf.add([o + xa * (p[0] * sx) + ya * (p[1] * sy) for p in profile]))
    nseg = npf if closed else npf - 1
    for r in range(len(rings) - 1):
        a, b = rings[r], rings[r + 1]
        for i in range(nseg):
            j = (i + 1) % npf
            sm = True if seg_smooth is None else seg_smooth[i]
            buf.face((a + i, a + j, b + j, b + i), sm)
    if caps and closed:
        fr0, fr1 = frames[0], frames[-1]
        o0, xa0, ya0, s0 = fr0
        o1, xa1, ya1, s1 = fr1
        if isinstance(s0, (int, float)):
            sx0 = sy0 = float(s0)
        else:
            sx0, sy0 = float(s0[0]), float(s0[1])
        if isinstance(s1, (int, float)):
            sx1 = sy1 = float(s1)
        else:
            sx1, sy1 = float(s1[0]), float(s1[1])
        pts0 = [o0 + xa0 * (p[0] * sx0) + ya0 * (p[1] * sy0) for p in profile]
        buf.poly(pts0[::-1])
        pts1 = [o1 + xa1 * (p[0] * sx1) + ya1 * (p[1] * sy1) for p in profile]
        buf.poly(pts1)


def add_cylinder(buf, p0, p1, r, sides=12, caps=True):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
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


def add_cone(buf, p0, p1, r0, r1, sides=12, caps=True):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    if L < 1e-9:
        return
    zax = d / L
    ref = Vector((0, 0, 1)) if abs(zax.z) < 0.9 else Vector((1, 0, 0))
    xa = zax.cross(ref).normalized()
    ya = zax.cross(xa).normalized()
    if xa.cross(ya).dot(zax) < 0:
        ya = -ya
    prof = circle_profile(sides, 1.0)
    sweep(buf, [(p0, xa, ya, r0), (p1, xa, ya, r1)], prof, True, caps)


def add_sphere(buf, center, radius, segs=14, rings=8, amp=0.0, nscale=2.0,
               scale=(1.0, 1.0, 1.0), seed_off=0.0):
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
                buf.face((a + j, a + k, b + k), True)
            else:
                buf.face((a + j, a + k, b + k, b + j), True)


# ---------------------------------------------------------------------------
# Helper per nodi di materiale procedurale
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


def _voronoi(nt, scale, rand=1.0, loc=(-500, 0), vec=None):
    v = nt.nodes.new("ShaderNodeTexVoronoi")
    v.location = loc
    v.inputs["Scale"].default_value = scale
    v.inputs["Randomness"].default_value = rand
    if vec is not None:
        nt.links.new(vec, v.inputs["Vector"])
    return v


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
    els = r.color_ramp.elements
    while len(els) < len(stops):
        els.new(0.5)
    while len(els) > len(stops):
        els.remove(els[-1])
    for el, (pos, col) in zip(els, stops):
        el.position = pos
        if len(col) == 3:
            el.color = (col[0], col[1], col[2], 1.0)
        else:
            el.color = col
    if fac_out is not None:
        nt.links.new(fac_out, r.inputs["Fac"])
    return r


def _coord(nt, loc=(-1100, 0), out="Object"):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = loc
    return tc.outputs[out]


def _mapping(nt, vec_in, scale=(1.0, 1.0, 1.0), loc=(-900, 0)):
    m = nt.nodes.new("ShaderNodeMapping")
    m.location = loc
    m.inputs["Scale"].default_value = scale
    nt.links.new(vec_in, m.inputs["Vector"])
    return m.outputs["Vector"]


def mat_semplice(name, color_srgb, rough=0.5, emit_srgb=None, emit_str=0.0):
    m, nt, b = _mat(name)
    b.inputs["Base Color"].default_value = (*srgb(*color_srgb), 1.0)
    b.inputs["Roughness"].default_value = rough
    if emit_srgb and emit_str > 0.0:
        b.inputs["Emission Color"].default_value = (*srgb(*emit_srgb), 1.0)
        b.inputs["Emission Strength"].default_value = emit_str
    return m


def mat_metallo(name, col_srgb=(120, 120, 124), rough=0.35, metal=1.0):
    m, nt, b = _mat(name)
    b.inputs["Base Color"].default_value = (*srgb(*col_srgb), 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def mat_vetro():
    m, nt, b = _mat("Vetro")
    b.inputs["Base Color"].default_value = (0.95, 0.98, 1.0, 1.0)
    b.inputs["Roughness"].default_value = 0.02
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.52
    b.inputs["Specular IOR Level"].default_value = 0.5
    return m


def mat_legno_alpino(name="Legno_Larice", c0=(182, 126, 72), c1=(88, 52, 26),
                     scale_wood=(2.2, 2.2, 14.0), rough=0.58, bump_str=0.35,
                     use_attr=False):
    """Legno di larice alpino invecchiato con venature, nodi e microfibra."""
    m, nt, b = _mat(name)
    vec = _coord(nt, (-1100, 0), "Object")
    mapped = _mapping(nt, vec, scale_wood, (-920, 0))

    n_fibra = _noise(nt, 32.0, 6.0, 0.72, dist=1.4, loc=(-680, 120), vec=mapped)
    n_anelli = _noise(nt, 3.8, 8.0, 0.55, dist=2.6, loc=(-680, -160), vec=mapped)

    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "FLOAT"
    mix.location = (-460, 0)
    mix.inputs[0].default_value = 0.40
    nt.links.new(n_fibra.outputs["Fac"], mix.inputs[2])
    nt.links.new(n_anelli.outputs["Fac"], mix.inputs[3])

    c_dark = srgb(*c1)
    c_light = srgb(*c0)
    c_mid = ((c_dark[0] + c_light[0]) * 0.5, (c_dark[1] + c_light[1]) * 0.5, (c_dark[2] + c_light[2]) * 0.5)

    ramp = _ramp(nt, mix.outputs[0], [(0.12, c_dark), (0.48, c_mid), (0.88, c_light)], (-260, 0))
    base_col = ramp.outputs["Color"]

    if use_attr:
        att = nt.nodes.new("ShaderNodeAttribute")
        att.location = (-260, 240)
        att.attribute_name = "Var"
        mix_col = nt.nodes.new("ShaderNodeMix")
        mix_col.data_type = "RGBA"
        mix_col.blend_type = "MULTIPLY"
        mix_col.location = (-40, 120)
        mix_col.inputs[0].default_value = 1.0
        nt.links.new(base_col, mix_col.inputs[6])
        nt.links.new(att.outputs["Color"], mix_col.inputs[7])
        base_col = mix_col.outputs[2]

    nt.links.new(base_col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = 0.35
    _bump(nt, mix.outputs[0], b, strength=bump_str, distance=0.018, loc=(60, -220))
    return m


def mat_pietra_alpina(name="Pietra_Alpina", c0=(168, 160, 148), c1=(108, 102, 92),
                      scale=4.5, bump_str=0.48, use_attr=False):
    """Pietra naturale alpina con conci e giunti di malta."""
    m, nt, b = _mat(name)
    vec = _coord(nt, (-1100, 0), "Object")
    vor = _voronoi(nt, scale, 1.0, (-880, 180), vec)
    nz = _noise(nt, scale * 3.5, 8.0, 0.65, loc=(-880, -120), vec=vec)

    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "FLOAT"
    mix.location = (-620, 40)
    mix.inputs[0].default_value = 0.4
    nt.links.new(vor.outputs["Distance"], mix.inputs[2])
    nt.links.new(nz.outputs["Fac"], mix.inputs[3])

    col0 = srgb(*c1)
    col1 = srgb(*c0)
    col2 = srgb(min(255, c0[0] + 25), min(255, c0[1] + 22), min(255, c0[2] + 20))
    ramp = _ramp(nt, mix.outputs[0], [(0.15, col0), (0.55, col1), (0.85, col2)], (-380, 40))
    base_col = ramp.outputs["Color"]

    if use_attr:
        att = nt.nodes.new("ShaderNodeAttribute")
        att.location = (-380, 260)
        att.attribute_name = "Var"
        mix_col = nt.nodes.new("ShaderNodeMix")
        mix_col.data_type = "RGBA"
        mix_col.blend_type = "MULTIPLY"
        mix_col.location = (-120, 140)
        mix_col.inputs[0].default_value = 1.0
        nt.links.new(base_col, mix_col.inputs[6])
        nt.links.new(att.outputs["Color"], mix_col.inputs[7])
        base_col = mix_col.outputs[2]

    nt.links.new(base_col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.88
    b.inputs["Specular IOR Level"].default_value = 0.25
    _bump(nt, mix.outputs[0], b, strength=bump_str, distance=0.025, loc=(60, -220))
    return m


def mat_fogliame(name="Fogliame", c0=(22, 48, 20), c1=(52, 92, 32), use_attr=False):
    m, nt, b = _mat(name)
    vec = _coord(nt, (-900, 0), "Object")
    nz = _noise(nt, 16.0, 6.0, 0.6, loc=(-650, 0), vec=vec)
    ramp = _ramp(nt, nz.outputs["Fac"], [(0.25, srgb(*c0)), (0.75, srgb(*c1))], (-400, 0))
    base_col = ramp.outputs["Color"]
    if use_attr:
        att = nt.nodes.new("ShaderNodeAttribute")
        att.location = (-400, 220)
        att.attribute_name = "Var"
        mix_col = nt.nodes.new("ShaderNodeMix")
        mix_col.data_type = "RGBA"
        mix_col.blend_type = "MULTIPLY"
        mix_col.location = (-150, 100)
        mix_col.inputs[0].default_value = 1.0
        nt.links.new(base_col, mix_col.inputs[6])
        nt.links.new(att.outputs["Color"], mix_col.inputs[7])
        base_col = mix_col.outputs[2]
    nt.links.new(base_col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.55
    b.inputs["Specular IOR Level"].default_value = 0.30
    return m


def mat_prato():
    """Terreno alpino con erba, terra e chiazze di roccia/muschio."""
    m, nt, b = _mat("Prato_Alpino")
    vec = _coord(nt, (-1100, 0), "Object")
    nz1 = _noise(nt, 1.8, 8.0, 0.6, loc=(-850, 120), vec=vec)
    nz2 = _noise(nt, 16.0, 6.0, 0.55, loc=(-850, -120), vec=vec)

    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "FLOAT"
    mix.location = (-600, 0)
    mix.inputs[0].default_value = 0.5
    nt.links.new(nz1.outputs["Fac"], mix.inputs[2])
    nt.links.new(nz2.outputs["Fac"], mix.inputs[3])

    c_erba_scura = srgb(42, 74, 26)
    c_erba_chiara = srgb(82, 124, 38)
    c_terra = srgb(74, 56, 38)
    ramp = _ramp(nt, mix.outputs[0], [(0.18, c_terra), (0.45, c_erba_scura), (0.82, c_erba_chiara)], (-360, 0))
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    _bump(nt, nz2.outputs["Fac"], b, strength=0.3, distance=0.03, loc=(60, -220))
    return m


def mat_scandole():
    """Scandole in larice alpino con forte variazione per tegola."""
    m, nt, b = _mat("Scandole_Larice")
    vec = _coord(nt, (-1100, 0), "Object")
    mapped = _mapping(nt, vec, (1.8, 14.0, 1.8), (-900, 0))
    nz = _noise(nt, 22.0, 6.0, 0.7, dist=1.5, loc=(-650, 0), vec=mapped)

    c0 = srgb(112, 94, 76)
    c1 = srgb(154, 124, 88)
    c2 = srgb(78, 62, 48)
    ramp = _ramp(nt, nz.outputs["Fac"], [(0.2, c2), (0.55, c0), (0.85, c1)], (-400, 0))

    att = nt.nodes.new("ShaderNodeAttribute")
    att.location = (-400, 240)
    att.attribute_name = "Var"

    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.location = (-150, 100)
    mix.inputs[0].default_value = 1.0
    nt.links.new(ramp.outputs["Color"], mix.inputs[6])
    nt.links.new(att.outputs["Color"], mix.inputs[7])

    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.75
    b.inputs["Specular IOR Level"].default_value = 0.25
    _bump(nt, nz.outputs["Fac"], b, strength=0.35, distance=0.015, loc=(60, -220))
    return m


def mat_stube():
    """Maiolica verde bosco smaltata e lucida per la Stube tirolese."""
    m, nt, b = _mat("Stube_Maiolica")
    vec = _coord(nt, (-900, 0), "Object")
    vor = _voronoi(nt, 18.0, 0.1, (-650, 0), vec)
    c_giunto = srgb(22, 38, 20)
    c_piastrella = srgb(38, 82, 42)
    ramp = _ramp(nt, vor.outputs["Distance"], [(0.05, c_giunto), (0.12, c_piastrella)], (-400, 0))
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.15
    b.inputs["Specular IOR Level"].default_value = 0.65
    b.inputs["Coat Weight"].default_value = 0.8
    b.inputs["Coat Roughness"].default_value = 0.08
    _bump(nt, vor.outputs["Distance"], b, strength=0.25, distance=0.01, loc=(60, -220))
    return m


def mat_tessuto_tirolese():
    """Tessuto a quadretti tradizionali rossi e bianchi per tendine."""
    m, nt, b = _mat("Tende_Tirolesi")
    vec = _coord(nt, (-1000, 0), "Object")
    mapped = _mapping(nt, vec, (40.0, 40.0, 40.0), (-800, 0))
    chk = nt.nodes.new("ShaderNodeTexChecker")
    chk.location = (-550, 0)
    chk.inputs["Scale"].default_value = 1.0
    chk.inputs["Color1"].default_value = (*srgb(205, 42, 38), 1.0)
    chk.inputs["Color2"].default_value = (*srgb(238, 234, 222), 1.0)
    nt.links.new(mapped, chk.inputs["Vector"])
    nt.links.new(chk.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    b.inputs["Sheen Weight"].default_value = 0.6
    return m


def mat_acqua():
    """Acqua limpida di sorgente montana con rifrazione."""
    m, nt, b = _mat("Acqua_Sorgente")
    b.inputs["Base Color"].default_value = (0.9, 0.96, 1.0, 1.0)
    b.inputs["Roughness"].default_value = 0.01
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.333
    return m


def mat_montagne():
    """Pareti rocciose e vette alpine di sfondo con foschia."""
    m, nt, b = _mat("Montagne_Sfondo")
    vec = _coord(nt, (-1100, 0), "Object")
    nz = _noise(nt, 2.5, 10.0, 0.6, loc=(-850, 0), vec=vec)
    c_roccia = srgb(92, 98, 108)
    c_neve = srgb(228, 235, 248)
    c_bosco = srgb(38, 58, 34)
    ramp = _ramp(nt, nz.outputs["Fac"], [(0.32, c_bosco), (0.58, c_roccia), (0.78, c_neve)], (-450, 0))
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    return m


def make_materials():
    return {
        "legno_larice": mat_legno_alpino("Legno_Larice", (182, 126, 72), (92, 54, 28),
                                         (2.2, 2.2, 14.0), 0.58, 0.35, use_attr=True),
        "legno_scuro": mat_legno_alpino("Legno_Strutturale", (118, 80, 48), (68, 42, 22),
                                        (2.0, 2.0, 10.0), 0.70, 0.38),
        "legno_intaglio": mat_legno_alpino("Legno_Cirmolo_Intagliato", (195, 152, 104), (138, 102, 66),
                                           (4.0, 4.0, 18.0), 0.52, 0.18),
        "legno_scuri": mat_legno_alpino("Legno_Scuri", (52, 82, 48), (32, 52, 30),
                                        (3.0, 3.0, 12.0), 0.45, 0.20),
        "legno_porta": mat_legno_alpino("Legno_Porta_Massello", (128, 80, 44), (78, 46, 24),
                                        (3.0, 3.0, 14.0), 0.48, 0.25),
        "legno_pavimento": mat_legno_alpino("Legno_Pavimento", (168, 126, 82), (115, 80, 48),
                                            (1.5, 8.0, 1.5), 0.42, 0.15, use_attr=True),
        "legno_tronco": mat_legno_alpino("Legno_Tronco_Rustico", (108, 76, 48), (62, 42, 26),
                                         (1.8, 1.8, 8.0), 0.78, 0.45),
        "legno_spaccato": mat_legno_alpino("Legno_Spaccato_Legnaia", (205, 168, 118), (128, 90, 52),
                                           (4.0, 4.0, 16.0), 0.80, 0.35, use_attr=True),
        "scandole": mat_scandole(),

        "pietra_muri": mat_pietra_alpina("Pietra_Muratura", (162, 154, 142), (112, 106, 96), 4.2, 0.48),
        "pietra_zoccolo": mat_pietra_alpina("Pietra_Zoccolo_Cantonali", (148, 142, 132), (102, 98, 90), 3.2, 0.38),
        "pietra_lastre": mat_pietra_alpina("Pietra_Lastre_Sentiero", (174, 168, 156), (128, 122, 112), 5.5, 0.40, use_attr=True),
        "pietra_masso": mat_pietra_alpina("Pietra_Massi_Naturali", (138, 142, 134), (88, 92, 84), 2.2, 0.55),

        "rame": mat_metallo("Rame_Invecchiato", (168, 102, 78), 0.38, 0.95),
        "ferro": mat_metallo("Ferro_Battuto", (38, 40, 42), 0.52, 0.9),
        "ottone": mat_metallo("Ottone_Brunito", (178, 138, 62), 0.32, 1.0),

        "vetro": mat_vetro(),
        "vetro_lanterna": mat_semplice("Vetro_Lanterna", (255, 235, 195), 0.25, (255, 220, 150), 4.0),
        "luce_fuoco": mat_semplice("Luce_Fuoco_Stube", (255, 140, 40), 0.5, (255, 130, 30), 45.0),
        "luce_calda": mat_semplice("Luce_Interna_Calda", (255, 215, 145), 0.5, (255, 210, 140), 18.0),
        "luce_lanterna": mat_semplice("Luce_Lanterna_Esterna", (255, 190, 95), 0.5, (255, 180, 80), 32.0),

        "stube": mat_stube(),
        "tende": mat_tessuto_tirolese(),
        "pizzo": mat_semplice("Pizzo_Bianco", (245, 245, 240), 0.8),
        "lana": mat_semplice("Lana_Piumone", (228, 224, 212), 0.9),
        "intonaco_int": mat_semplice("Intonaco_Interno", (232, 228, 218), 0.88),

        "prato": mat_prato(),
        "erba": mat_fogliame("Erba_Alpina", (52, 88, 24), (105, 142, 42), use_attr=True),
        "aghi_pino": mat_fogliame("Aghi_Abete", (18, 42, 16), (42, 78, 28), use_attr=True),
        "corteccia_pino": mat_legno_alpino("Corteccia_Abete", (82, 60, 42), (48, 34, 24), (2.0, 2.0, 12.0), 0.92, 0.6),
        "stella_alpina": mat_semplice("Fiore_Stella_Alpina", (242, 244, 238), 0.85),
        "stella_centro": mat_semplice("Centro_Stella_Alpina", (212, 178, 48), 0.7),
        "genziana": mat_semplice("Fiore_Genziana", (22, 58, 192), 0.45),
        "margherita": mat_semplice("Fiore_Margherita", (248, 248, 242), 0.5),
        "gerani_fiori": mat_fogliame("Gerani_Fiori", (228, 22, 36), (248, 42, 58), use_attr=True),
        "gerani_foglie": mat_fogliame("Gerani_Foglie", (38, 72, 24), (68, 108, 38)),
        "rododendro_fiori": mat_semplice("Rododendro_Fiori", (218, 48, 132), 0.48),
        "foglie_arbusto": mat_fogliame("Foglie_Rododendro", (32, 65, 26), (65, 102, 38)),
        "terra": mat_semplice("Terra_Sottobosco", (68, 52, 38), 0.95),
        "acqua": mat_acqua(),
        "montagne": mat_montagne(),
    }


BUF_SPEC = [
    ("pietra_muri",         "Muratura_Pietra",         "Edificio",   False),
    ("pietra_zoccolo",      "Zoccolo_e_Cantonali",     "Edificio",   False),
    ("legno_larice",        "Struttura_Legno_Larice",  "Edificio",   True),
    ("legno_scuro",         "Travature_e_Carpenteria", "Edificio",   False),
    ("legno_intaglio",      "Intagli_e_Balaustre",     "Edificio",   False),
    ("legno_scuri",         "Scuri_Finestre",          "Serramenti", False),
    ("legno_porta",         "Portone_Massello",        "Serramenti", False),
    ("vetro",               "Vetri_Serramenti",        "Serramenti", False),
    ("ferro",               "Ferro_Battuto_Dettagli",  "Serramenti", False),
    ("ottone",              "Ottoni_Maniglie",         "Serramenti", False),
    ("tende",               "Tende_Tirolesi",          "Serramenti", False),
    ("pizzo",               "Tende_Pizzo",             "Serramenti", False),

    ("scandole",            "Copertura_Scandole",      "Tetto",      True),
    ("rame",                "Lattoneria_Rame",         "Tetto",      False),

    ("legno_pavimento",     "Pavimenti_Interni",       "Interni",    True),
    ("intonaco_int",        "Muri_Interni",            "Interni",    False),
    ("stube",               "Stube_Maiolica",          "Interni",    False),
    ("luce_fuoco",          "Fuoco_Braci_Stube",       "Interni",    False),
    ("luce_calda",          "Luci_Punti_Luce",         "Interni",    False),
    ("lana",                "Arredi_Tessili",          "Interni",    False),

    ("legno_tronco",        "Legno_Rustico_Esterni",   "Esterni",    False),
    ("legno_spaccato",      "Legnaia_Ciocchi",         "Esterni",    True),
    ("vetro_lanterna",      "Vetro_Lanterne",          "Esterni",    False),
    ("luce_lanterna",       "Luce_Lanterne",           "Esterni",    False),
    ("acqua",               "Acqua_Fontana",           "Esterni",    False),

    ("prato",               "Terreno_Alpino",          "Giardino",   False),
    ("pietra_lastre",       "Sentiero_Beole",          "Giardino",   True),
    ("pietra_masso",        "Massi_Rocce_Naturali",    "Giardino",   False),
    ("erba",                "Erba_Ciuffi_Alpini",      "Giardino",   True),
    ("aghi_pino",           "Chiome_Abeti_Pini",       "Giardino",   True),
    ("corteccia_pino",      "Tronchi_Abeti",           "Giardino",   False),
    ("gerani_fiori",        "Gerani_Fioriere",         "Giardino",   True),
    ("gerani_foglie",       "Gerani_Fogliame",         "Giardino",   False),
    ("stella_alpina",       "Fiori_Stelle_Alpine",     "Giardino",   False),
    ("stella_centro",       "Centri_Stelle_Alpine",    "Giardino",   False),
    ("genziana",            "Fiori_Genziane",          "Giardino",   False),
    ("margherita",          "Fiori_Margherite",        "Giardino",   False),
    ("rododendro_fiori",    "Rododendri_Fiori",        "Giardino",   False),
    ("foglie_arbusto",      "Rododendri_Foglie",       "Giardino",   False),
    ("terra",               "Terriccio_Aiuole",        "Giardino",   False),
    ("montagne",            "Catena_Alpina_Sfondo",    "Giardino",   False),
]


def make_buffers(mats):
    B = {}
    for key, name, coll, usec in BUF_SPEC:
        B[key] = Buf(name, mats[key], usec)
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
# 1. STRUTTURA EDIFICIO: Basamento in Pietra e Blockbau in Legno
# ---------------------------------------------------------------------------
OPENINGS = [
    # Facciata Sud (frontale, Y = -HALF_Y)
    {"facciata": "S", "kind": "portone", "x": 0.30, "z0": Z_PLINTH, "w": 1.25, "h": 2.25},
    {"facciata": "S", "kind": "finestra_pt", "x": -2.60, "z0": Z_PLINTH + 0.85, "w": 1.15, "h": 1.40},
    {"facciata": "S", "kind": "finestra_pt", "x": 2.80, "z0": Z_PLINTH + 0.85, "w": 1.15, "h": 1.40},
    {"facciata": "S", "kind": "portafinestra_p1", "x": 0.00, "z0": Z_F1, "w": 1.35, "h": 2.25},
    {"facciata": "S", "kind": "finestra_p1", "x": -2.55, "z0": Z_F1 + 0.82, "w": 1.15, "h": 1.35},
    {"facciata": "S", "kind": "finestra_p1", "x": 2.55, "z0": Z_F1 + 0.82, "w": 1.15, "h": 1.35},

    # Facciata Nord (retro, Y = +HALF_Y)
    {"facciata": "N", "kind": "finestra_pt", "x": -2.20, "z0": Z_PLINTH + 0.95, "w": 1.10, "h": 1.25},
    {"facciata": "N", "kind": "finestra_pt", "x": 1.80, "z0": Z_PLINTH + 0.95, "w": 1.10, "h": 1.25},
    {"facciata": "N", "kind": "porta_retro", "x": 3.20, "z0": Z_PLINTH, "w": 1.00, "h": 2.15},
    {"facciata": "N", "kind": "finestra_p1", "x": -2.20, "z0": Z_F1 + 0.85, "w": 1.10, "h": 1.25},
    {"facciata": "N", "kind": "finestra_p1", "x": 1.80, "z0": Z_F1 + 0.85, "w": 1.10, "h": 1.25},

    # Facciata Ovest (timpano ovest, X = -HALF_X)
    {"facciata": "W", "kind": "finestra_pt", "y": 0.00, "z0": Z_PLINTH + 0.85, "w": 1.15, "h": 1.40},
    {"facciata": "W", "kind": "portafinestra_p1", "y": -1.20, "z0": Z_F1, "w": 1.20, "h": 2.20},
    {"facciata": "W", "kind": "finestra_p1", "y": 1.20, "z0": Z_F1 + 0.85, "w": 1.10, "h": 1.30},
    {"facciata": "W", "kind": "finestra_attic", "y": 0.00, "z0": Z_EAVE_WALL + 0.55, "w": 1.10, "h": 1.10},

    # Facciata Est (timpano est, X = +HALF_X)
    {"facciata": "E", "kind": "finestra_pt", "y": -0.80, "z0": Z_PLINTH + 0.85, "w": 1.15, "h": 1.40},
    {"facciata": "E", "kind": "finestra_p1", "y": 0.00, "z0": Z_F1 + 0.85, "w": 1.15, "h": 1.30},
    {"facciata": "E", "kind": "finestra_attic", "y": 0.00, "z0": Z_EAVE_WALL + 0.55, "w": 1.10, "h": 1.10},
]


def build_struttura(B):
    """Costruisce muratura in pietra del piano terra e struttura in legno del primo piano."""
    b_pietra = B["pietra_muri"]
    b_zoccolo = B["pietra_zoccolo"]
    b_legno = B["legno_larice"]
    b_scuro = B["legno_scuro"]
    b_intaglio = B["legno_intaglio"]

    h_zoccolo = Z_PLINTH + 0.12
    add_box(b_zoccolo, (-HALF_X - 0.12, -HALF_Y - 0.12, -0.40),
                       ( HALF_X + 0.12,  HALF_Y + 0.12, h_zoccolo))
    add_box(b_zoccolo, (-HALF_X - 0.15, -HALF_Y - 0.15, h_zoccolo - 0.08),
                       ( HALF_X + 0.15,  HALF_Y + 0.15, h_zoccolo))

    quoin_w, quoin_d, quoin_h = 0.44, 0.44, 0.28
    for z in range(int(h_zoccolo * 100), int(Z_F1 * 100), int(quoin_h * 100)):
        zq0 = z / 100.0
        zq1 = min(Z_F1, zq0 + quoin_h - 0.02)
        for sx in (-1, 1):
            for sy in (-1, 1):
                qx0 = (HALF_X - 0.05) * sx - (quoin_w / 2 if sx > 0 else -quoin_w / 2)
                qx1 = (HALF_X + 0.06) * sx
                qy0 = (HALF_Y - 0.05) * sy - (quoin_d / 2 if sy > 0 else -quoin_d / 2)
                qy1 = (HALF_Y + 0.06) * sy
                add_box(b_zoccolo, (min(qx0, qx1), min(qy0, qy1), zq0),
                                   (max(qx0, qx1), max(qy0, qy1), zq1))

    # Muri in pietra del Piano Terra (con vani passanti)
    add_box(b_pietra, (-HALF_X, -HALF_Y, h_zoccolo), (-3.25, -HALF_Y + T_WALL_STONE, Z_F1))
    add_box(b_pietra, (-1.95, -HALF_Y, h_zoccolo), (-0.40, -HALF_Y + T_WALL_STONE, Z_F1))
    add_box(b_pietra, ( 1.00, -HALF_Y, h_zoccolo), ( 2.15, -HALF_Y + T_WALL_STONE, Z_F1))
    add_box(b_pietra, ( 3.45, -HALF_Y, h_zoccolo), ( HALF_X, -HALF_Y + T_WALL_STONE, Z_F1))
    add_box(b_pietra, (-3.25, -HALF_Y, h_zoccolo), (-1.95, -HALF_Y + T_WALL_STONE, Z_PLINTH + 0.85))
    add_box(b_pietra, ( 2.15, -HALF_Y, h_zoccolo), ( 3.45, -HALF_Y + T_WALL_STONE, Z_PLINTH + 0.85))
    add_box(b_pietra, (-3.25, -HALF_Y, Z_PLINTH + 2.25), (-1.95, -HALF_Y + T_WALL_STONE, Z_F1))
    add_box(b_pietra, (-0.40, -HALF_Y, Z_PLINTH + 2.25), ( 1.00, -HALF_Y + T_WALL_STONE, Z_F1))
    add_box(b_pietra, ( 2.15, -HALF_Y, Z_PLINTH + 2.25), ( 3.45, -HALF_Y + T_WALL_STONE, Z_F1))

    add_box(b_pietra, (-HALF_X, HALF_Y - T_WALL_STONE, h_zoccolo), (-2.80, HALF_Y, Z_F1))
    add_box(b_pietra, (-1.60, HALF_Y - T_WALL_STONE, h_zoccolo), ( 1.20, HALF_Y, Z_F1))
    add_box(b_pietra, ( 2.40, HALF_Y - T_WALL_STONE, h_zoccolo), ( 2.65, HALF_Y, Z_F1))
    add_box(b_pietra, ( 3.75, HALF_Y - T_WALL_STONE, h_zoccolo), ( HALF_X, HALF_Y, Z_F1))
    add_box(b_pietra, (-2.80, HALF_Y - T_WALL_STONE, h_zoccolo), (-1.60, HALF_Y, Z_PLINTH + 0.95))
    add_box(b_pietra, (-2.80, HALF_Y - T_WALL_STONE, Z_PLINTH + 2.20), (-1.60, HALF_Y, Z_F1))
    add_box(b_pietra, ( 1.20, HALF_Y - T_WALL_STONE, h_zoccolo), ( 2.40, HALF_Y, Z_PLINTH + 0.95))
    add_box(b_pietra, ( 1.20, HALF_Y - T_WALL_STONE, Z_PLINTH + 2.20), ( 2.40, HALF_Y, Z_F1))
    add_box(b_pietra, ( 2.65, HALF_Y - T_WALL_STONE, Z_PLINTH + 2.15), ( 3.75, HALF_Y, Z_F1))

    add_box(b_pietra, (-HALF_X, -HALF_Y + T_WALL_STONE, h_zoccolo), (-HALF_X + T_WALL_STONE, -0.65, Z_F1))
    add_box(b_pietra, (-HALF_X,  0.65, h_zoccolo), (-HALF_X + T_WALL_STONE,  HALF_Y - T_WALL_STONE, Z_F1))
    add_box(b_pietra, (-HALF_X, -0.65, h_zoccolo), (-HALF_X + T_WALL_STONE,  0.65, Z_PLINTH + 0.85))
    add_box(b_pietra, (-HALF_X, -0.65, Z_PLINTH + 2.25), (-HALF_X + T_WALL_STONE, 0.65, Z_F1))

    add_box(b_pietra, (HALF_X - T_WALL_STONE, -HALF_Y + T_WALL_STONE, h_zoccolo), (HALF_X, -1.45, Z_F1))
    add_box(b_pietra, (HALF_X - T_WALL_STONE, -0.15, h_zoccolo), (HALF_X, HALF_Y - T_WALL_STONE, Z_F1))
    add_box(b_pietra, (HALF_X - T_WALL_STONE, -1.45, h_zoccolo), (HALF_X, -0.15, Z_PLINTH + 0.85))
    add_box(b_pietra, (HALF_X - T_WALL_STONE, -1.45, Z_PLINTH + 2.25), (HALF_X, -0.15, Z_F1))

    lintel_h = 0.22
    lintel_t = 0.44
    for op in OPENINGS:
        if "pt" in op["kind"] or op["kind"] == "portone":
            if op["facciata"] in ("S", "N"):
                y_pos = -HALF_Y + T_WALL_STONE / 2 if op["facciata"] == "S" else HALF_Y - T_WALL_STONE / 2
                add_box_c(b_scuro, (op["x"], y_pos, op["z0"] + op["h"] + lintel_h / 2),
                          (op["w"] + 0.35, lintel_t, lintel_h))
            else:
                x_pos = -HALF_X + T_WALL_STONE / 2 if op["facciata"] == "W" else HALF_X - T_WALL_STONE / 2
                add_box_c(b_scuro, (x_pos, op["y"], op["z0"] + op["h"] + lintel_h / 2),
                          (lintel_t, op["w"] + 0.35, lintel_h))

    # Fascia marcapiano intagliata di divisione tra pietra e legno
    add_box_c(b_intaglio, (0, -HALF_Y - 0.04, Z_F1 - 0.05), (W_X + 0.25, 0.12, 0.12))
    add_box_c(b_intaglio, (-HALF_X - 0.04, 0, Z_F1 - 0.05), (0.12, D_Y + 0.25, 0.12))

    # Travi portanti del solaio intermedio sporgenti (fondamento del balcone)
    beam_w, beam_h = 0.22, 0.28
    for x in (-4.2, -3.1, -1.9, -0.7, 0.5, 1.7, 2.9, 4.1):
        add_box(b_scuro, (x - beam_w / 2, BALCONY_FRONT_Y - 0.15, Z_F1 - beam_h),
                         (x + beam_w / 2, HALF_Y + 0.45, Z_F1))

    for y in (-4.5, -3.2, -1.9, -0.6, 0.8):
        add_box(b_scuro, (BALCONY_SIDE_X - 0.15, y - beam_w / 2, Z_F1 - beam_h),
                         (-HALF_X + 0.5, y + beam_w / 2, Z_F1))

    # Struttura in Legno del Primo Piano (Blockbau a tronchi con rilievo 3D)
    log_h = 0.20
    n_logs = int((Z_EAVE_WALL - Z_F1) / log_h) + 1

    for i in range(n_logs):
        z_log0 = Z_F1 + i * log_h
        z_log1 = min(Z_EAVE_WALL, z_log0 + log_h)
        if z_log1 <= z_log0:
            continue
        zc = (z_log0 + z_log1) / 2.0
        zh = z_log1 - z_log0

        b_legno.color = jitter_color((1.0, 0.98, 0.92), 0.12)

        # Muro Sud (P1)
        add_box(b_legno, (-HALF_X - 0.35, -HALF_Y - 0.02, z_log0), (-3.20, -HALF_Y + T_WALL_WOOD, z_log1 - 0.01))
        add_box(b_legno, (-1.90, -HALF_Y - 0.02, z_log0), (-0.75, -HALF_Y + T_WALL_WOOD, z_log1 - 0.01))
        add_box(b_legno, ( 0.75, -HALF_Y - 0.02, z_log0), ( 1.90, -HALF_Y + T_WALL_WOOD, z_log1 - 0.01))
        add_box(b_legno, ( 3.20, -HALF_Y - 0.02, z_log0), ( HALF_X + 0.35, -HALF_Y + T_WALL_WOOD, z_log1 - 0.01))
        if zc < Z_F1 + 0.82:
            add_box(b_legno, (-3.20, -HALF_Y, z_log0), (-1.90, -HALF_Y + T_WALL_WOOD, z_log1 - 0.01))
            add_box(b_legno, ( 1.90, -HALF_Y, z_log0), ( 3.20, -HALF_Y + T_WALL_WOOD, z_log1 - 0.01))
        if zc > Z_F1 + 2.20:
            add_box(b_legno, (-3.20, -HALF_Y, z_log0), (-1.90, -HALF_Y + T_WALL_WOOD, z_log1 - 0.01))
            add_box(b_legno, (-0.75, -HALF_Y, z_log0), ( 0.75, -HALF_Y + T_WALL_WOOD, z_log1 - 0.01))
            add_box(b_legno, ( 1.90, -HALF_Y, z_log0), ( 3.20, -HALF_Y + T_WALL_WOOD, z_log1 - 0.01))

        # Muro Nord (P1)
        add_box(b_legno, (-HALF_X - 0.35, HALF_Y - T_WALL_WOOD, z_log0), (-2.80, HALF_Y + 0.02, z_log1 - 0.01))
        add_box(b_legno, (-1.60, HALF_Y - T_WALL_WOOD, z_log0), ( 1.20, HALF_Y + 0.02, z_log1 - 0.01))
        add_box(b_legno, ( 2.40, HALF_Y - T_WALL_WOOD, z_log0), ( HALF_X + 0.35, HALF_Y + 0.02, z_log1 - 0.01))
        if zc < Z_F1 + 0.85:
            add_box(b_legno, (-2.80, HALF_Y - T_WALL_WOOD, z_log0), (-1.60, HALF_Y, z_log1 - 0.01))
            add_box(b_legno, ( 1.20, HALF_Y - T_WALL_WOOD, z_log0), ( 2.40, HALF_Y, z_log1 - 0.01))
        if zc > Z_F1 + 2.15:
            add_box(b_legno, (-2.80, HALF_Y - T_WALL_WOOD, z_log0), (-1.60, HALF_Y, z_log1 - 0.01))
            add_box(b_legno, ( 1.20, HALF_Y - T_WALL_WOOD, z_log0), ( 2.40, HALF_Y, z_log1 - 0.01))

        # Muro Ovest (P1)
        add_box(b_legno, (-HALF_X - 0.02, -HALF_Y - 0.35, z_log0), (-HALF_X + T_WALL_WOOD, -1.85, z_log1 - 0.01))
        add_box(b_legno, (-HALF_X - 0.02, -0.55, z_log0), (-HALF_X + T_WALL_WOOD,  0.60, z_log1 - 0.01))
        add_box(b_legno, (-HALF_X - 0.02,  1.80, z_log0), (-HALF_X + T_WALL_WOOD,  HALF_Y + 0.35, z_log1 - 0.01))
        if zc < Z_F1 + 0.85:
            add_box(b_legno, (-HALF_X, 0.60, z_log0), (-HALF_X + T_WALL_WOOD, 1.80, z_log1 - 0.01))
        if zc > Z_F1 + 2.20:
            add_box(b_legno, (-HALF_X, -1.85, z_log0), (-HALF_X + T_WALL_WOOD, -0.55, z_log1 - 0.01))
            add_box(b_legno, (-HALF_X, 0.60, z_log0), (-HALF_X + T_WALL_WOOD, 1.80, z_log1 - 0.01))

        # Muro Est (P1)
        add_box(b_legno, (HALF_X - T_WALL_WOOD, -HALF_Y - 0.35, z_log0), (HALF_X + 0.02, -0.65, z_log1 - 0.01))
        add_box(b_legno, (HALF_X - T_WALL_WOOD,  0.65, z_log0), (HALF_X + 0.02,  HALF_Y + 0.35, z_log1 - 0.01))
        if zc < Z_F1 + 0.85 or zc > Z_F1 + 2.20:
            add_box(b_legno, (HALF_X - T_WALL_WOOD, -0.65, z_log0), (HALF_X + 0.02, 0.65, z_log1 - 0.01))

        # Teste dei tronchi incrociati che sporgono agli angoli
        overhang_log = 0.35
        for sx in (-1, 1):
            for sy in (-1, 1):
                add_box_c(b_scuro, ((HALF_X + overhang_log / 2) * sx, (HALF_Y - T_WALL_WOOD / 2) * sy, zc),
                          (overhang_log, T_WALL_WOOD + 0.04, zh * 0.92))
                add_box_c(b_scuro, ((HALF_X - T_WALL_WOOD / 2) * sx, (HALF_Y + overhang_log / 2) * sy, zc),
                          (T_WALL_WOOD + 0.04, overhang_log, zh * 0.92))

    build_timpani(B)


def build_timpani(B):
    """Costruisce i timpani in legno con finestre bifore alpine e trafori."""
    b_legno = B["legno_larice"]
    b_scuro = B["legno_scuro"]
    b_intaglio = B["legno_intaglio"]

    log_h = 0.18
    n_gable = int((Z_RIDGE_STRUCT - Z_EAVE_WALL) / log_h) + 1

    for side_x in (-HALF_X, HALF_X):
        x_in = side_x + (T_WALL_WOOD if side_x < 0 else -T_WALL_WOOD)
        x0 = min(side_x, x_in)
        x1 = max(side_x, x_in)

        for i in range(n_gable):
            z0 = Z_EAVE_WALL + i * log_h
            z1 = min(Z_RIDGE_STRUCT, z0 + log_h)
            if z1 <= z0:
                continue
            zc = (z0 + z1) / 2.0
            max_y = max(0.2, (Z_RIDGE_STRUCT - zc) / TAN_P)

            b_legno.color = jitter_color((1.0, 0.98, 0.92), 0.10)

            if Z_EAVE_WALL + 0.45 <= zc <= Z_EAVE_WALL + 1.65:
                w_attic = 0.60
                add_box(b_legno, (x0, -max_y, z0), (x1, -w_attic, z1 - 0.01))
                add_box(b_legno, (x0,  w_attic, z0), (x1,  max_y, z1 - 0.01))
            else:
                add_box(b_legno, (x0, -max_y, z0), (x1, max_y, z1 - 0.01))

        # Travatura decorativa sul timpano
        z_base = Z_EAVE_WALL + 0.05
        z_peak = Z_RIDGE_STRUCT - 0.12
        x_face = side_x + (-0.08 if side_x < 0 else 0.08)

        add_box_c(b_scuro, (x_face, 0.0, z_base + 0.10), (0.16, (HALF_Y - 0.2) * 2, 0.20))
        add_box_c(b_scuro, (x_face, 0.0, (z_base + z_peak) / 2), (0.16, 0.22, z_peak - z_base))
        for sy in (-1, 1):
            p0 = Vector((x_face, (HALF_Y - 0.3) * sy, z_base + 0.15))
            p1 = Vector((x_face, 0.0, z_peak - 0.05))
            add_cylinder(b_scuro, p0, p1, 0.085, sides=8)

        add_cylinder(b_intaglio, Vector((x_face - 0.04 if side_x < 0 else x_face + 0.04, 0.0, Z_RIDGE_STRUCT - 0.85)),
                     Vector((x_face + 0.04 if side_x < 0 else x_face - 0.04, 0.0, Z_RIDGE_STRUCT - 0.85)),
                     0.32, sides=16)


# ---------------------------------------------------------------------------
# 2. BALCONATA PANORAMICA (Ballatoio alpino con balaustre intagliate e fiori)
# ---------------------------------------------------------------------------
def build_balcone(B):
    """Costruisce la grande balconata panoramica avvolgente con intagli tirolesi."""
    b_scuro = B["legno_scuro"]
    b_larice = B["legno_larice"]
    b_intaglio = B["legno_intaglio"]

    z_floor = BALCONY_Z
    rail_h = 1.05
    z_rail_top = z_floor + rail_h

    # 1. Pavimento in tavole di larice
    plank_w = 0.18
    plank_t = 0.045

    # Fronte Sud
    y_min = BALCONY_FRONT_Y
    y_max = -HALF_Y
    n_planks_s = int((y_max - y_min) / plank_w)
    for i in range(n_planks_s):
        y0 = y_min + i * plank_w + 0.008
        y1 = y0 + plank_w - 0.016
        b_larice.color = jitter_color((1.0, 1.0, 1.0), 0.12)
        add_box(b_larice, (BALCONY_SIDE_X - 0.10, y0, z_floor),
                          (HALF_X + 0.45, y1, z_floor + plank_t))

    # Risvolto Ovest
    x_min = BALCONY_SIDE_X
    x_max = -HALF_X
    n_planks_w = int((x_max - x_min) / plank_w)
    for i in range(n_planks_w):
        x0 = x_min + i * plank_w + 0.008
        x1 = x0 + plank_w - 0.016
        b_larice.color = jitter_color((1.0, 1.0, 1.0), 0.12)
        add_box(b_larice, (x0, -HALF_Y, z_floor),
                          (x1, 0.85, z_floor + plank_t))

    # 2. Saettoni e mensole sagomate di supporto sotto il balcone
    bracket_xs = (-4.2, -3.1, -1.9, -0.7, 0.5, 1.7, 2.9, 4.1)
    for bx in bracket_xs:
        p_top = Vector((bx, BALCONY_FRONT_Y + 0.15, z_floor - 0.05))
        p_bot = Vector((bx, -HALF_Y + 0.10, z_floor - 1.25))
        add_cylinder(b_scuro, p_bot, p_top, 0.08, sides=8)
        add_box_c(b_scuro, (bx, (BALCONY_FRONT_Y - HALF_Y) / 2, z_floor - 0.12),
                  (0.18, abs(BALCONY_FRONT_Y - (-HALF_Y)), 0.18))

    bracket_ys = (-4.2, -3.0, -1.8, -0.6, 0.6)
    for by in bracket_ys:
        p_top = Vector((BALCONY_SIDE_X + 0.15, by, z_floor - 0.05))
        p_bot = Vector((-HALF_X + 0.10, by, z_floor - 1.25))
        add_cylinder(b_scuro, p_bot, p_top, 0.08, sides=8)

    # 3. Parapetto in legno con corrimano e balaustre traforate
    handrail_w = 0.16
    handrail_h = 0.09
    add_box_c(b_intaglio, ((BALCONY_SIDE_X + HALF_X + 0.45) / 2, BALCONY_FRONT_Y + 0.08, z_rail_top - handrail_h / 2),
              (abs(HALF_X + 0.45 - BALCONY_SIDE_X) + 0.15, handrail_w, handrail_h))
    add_box_c(b_scuro, ((BALCONY_SIDE_X + HALF_X + 0.45) / 2, BALCONY_FRONT_Y + 0.08, z_floor + 0.14),
              (abs(HALF_X + 0.45 - BALCONY_SIDE_X) + 0.15, 0.12, 0.08))

    add_box_c(b_intaglio, (BALCONY_SIDE_X + 0.08, (BALCONY_FRONT_Y + 0.85) / 2, z_rail_top - handrail_h / 2),
              (handrail_w, abs(0.85 - BALCONY_FRONT_Y) + 0.15, handrail_h))
    add_box_c(b_scuro, (BALCONY_SIDE_X + 0.08, (BALCONY_FRONT_Y + 0.85) / 2, z_floor + 0.14),
              (0.12, abs(0.85 - BALCONY_FRONT_Y) + 0.15, 0.08))

    add_box_c(b_intaglio, (HALF_X + 0.45, (BALCONY_FRONT_Y - HALF_Y) / 2, z_rail_top - handrail_h / 2),
              (handrail_w, abs(-HALF_Y - BALCONY_FRONT_Y), handrail_h))
    add_box_c(b_intaglio, ((BALCONY_SIDE_X - HALF_X) / 2, 0.85, z_rail_top - handrail_h / 2),
              (abs(-HALF_X - BALCONY_SIDE_X), handrail_w, handrail_h))

    post_pos = [
        (BALCONY_SIDE_X + 0.08, BALCONY_FRONT_Y + 0.08),
        (HALF_X + 0.45, BALCONY_FRONT_Y + 0.08),
        (HALF_X + 0.45, -HALF_Y),
        (BALCONY_SIDE_X + 0.08, 0.85),
        (-HALF_X, 0.85),
        (-2.4, BALCONY_FRONT_Y + 0.08),
        ( 0.0, BALCONY_FRONT_Y + 0.08),
        ( 2.4, BALCONY_FRONT_Y + 0.08),
        (BALCONY_SIDE_X + 0.08, -2.4),
        (BALCONY_SIDE_X + 0.08, -0.8),
    ]
    for px, py in post_pos:
        add_box_c(b_scuro, (px, py, z_floor + rail_h / 2), (0.15, 0.15, rail_h + 0.08))
        add_cone(b_intaglio, (px, py, z_rail_top + 0.04), (px, py, z_rail_top + 0.12), 0.11, 0.01, sides=4)

    bal_w = 0.14
    bal_t = 0.035
    bal_step = 0.18

    x_curr = BALCONY_SIDE_X + 0.22
    while x_curr < HALF_X + 0.35:
        if not any(abs(x_curr - px) < 0.12 for px, py in post_pos if abs(py - (BALCONY_FRONT_Y + 0.08)) < 0.1):
            build_singola_balaustra(B, Vector((x_curr, BALCONY_FRONT_Y + 0.08, z_floor + 0.18)),
                                    bal_w, bal_t, rail_h - 0.26, axis="X")
        x_curr += bal_step

    y_curr = BALCONY_FRONT_Y + 0.22
    while y_curr < 0.72:
        if not any(abs(y_curr - py) < 0.12 for px, py in post_pos if abs(px - (BALCONY_SIDE_X + 0.08)) < 0.1):
            build_singola_balaustra(B, Vector((BALCONY_SIDE_X + 0.08, y_curr, z_floor + 0.18)),
                                    bal_w, bal_t, rail_h - 0.26, axis="Y")
        y_curr += bal_step

    build_fioriere_balcone(B, z_rail_top)


def build_singola_balaustra(B, pos, w, t, h, axis="X"):
    b_int = B["legno_intaglio"]
    if axis == "X":
        add_box_c(b_int, pos + Vector((0, 0, h / 2)), (w, t, h))
        add_box_c(b_int, pos + Vector((0, 0, h * 0.50)), (w * 0.65, t * 1.35, h * 0.28))
    else:
        add_box_c(b_int, pos + Vector((0, 0, h / 2)), (t, w, h))
        add_box_c(b_int, pos + Vector((0, 0, h * 0.50)), (t * 1.35, w * 0.65, h * 0.28))


def build_fioriere_balcone(B, z_top):
    b_larice = B["legno_larice"]
    b_terra = B["terra"]

    box_h = 0.22
    box_d = 0.24

    box_specs = [
        (-4.8, -2.6),
        (-2.2, -0.2),
        ( 0.2,  2.2),
        ( 2.6,  4.8),
    ]
    for x0, x1 in box_specs:
        bx_w = x1 - x0
        bx_c = (x0 + x1) / 2
        add_box_c(b_larice, (bx_c, BALCONY_FRONT_Y - 0.05, z_top - box_h * 0.4),
                  (bx_w, box_d, box_h))
        add_box_c(b_terra, (bx_c, BALCONY_FRONT_Y - 0.05, z_top - 0.02),
                  (bx_w - 0.05, box_d - 0.05, 0.06))
        build_grappolo_gerani(B, Vector((bx_c, BALCONY_FRONT_Y - 0.08, z_top + 0.02)), bx_w)


def build_grappolo_gerani(B, center, width):
    b_fiori = B["gerani_fiori"]
    b_foglie = B["gerani_foglie"]

    n_plants = int(width * 18)
    for i in range(n_plants):
        px = center.x - width / 2 + (i + 0.5) * (width / n_plants) + rr(-0.04, 0.04)
        py = center.y + rr(-0.06, 0.06)
        pz = center.z + rr(-0.02, 0.04)
        pos = Vector((px, py, pz))

        for _ in range(8):
            ang = rr(0, TAU)
            dist = rr(0.04, 0.20)
            drop = rr(0.02, 0.28)
            leaf_p = pos + Vector((math.cos(ang) * dist, math.sin(ang) * dist - drop * 0.5, -drop))
            add_sphere(b_foglie, leaf_p, rr(0.035, 0.055), segs=6, rings=4,
                       scale=(1.2, 1.2, 0.3))

        if random.random() < 0.92:
            b_fiori.color = jitter_color((1.0, 1.0, 1.0), 0.15)
            f_drop = rr(-0.02, 0.22)
            f_pos = pos + Vector((rr(-0.06, 0.06), rr(-0.08, 0.02), -f_drop + 0.04))
            add_sphere(b_fiori, f_pos, rr(0.036, 0.056), segs=8, rings=6,
                       scale=(1.0, 1.0, 0.85))


# ---------------------------------------------------------------------------
# 3. PORTICO D'INGRESSO, LEGNAIA E ACCESSORI ALPINI
# ---------------------------------------------------------------------------
def build_portico_e_accessori(B):
    """Costruisce il portico coperto, la legnaia con ciocchi spaccati, panca, sci e slitta."""
    b_scuro = B["legno_scuro"]
    b_zoccolo = B["pietra_zoccolo"]
    b_lastre = B["pietra_lastre"]
    b_larice = B["legno_larice"]
    b_spaccato = B["legno_spaccato"]
    b_tronco = B["legno_tronco"]
    b_ferro = B["ferro"]
    b_ottone = B["ottone"]
    b_vlanterna = B["vetro_lanterna"]
    b_llanterna = B["luce_lanterna"]

    z_porch = Z_PLINTH
    add_box(b_zoccolo, (PORCH_X0 - 0.25, PORCH_Y_FRONT - 0.15, -0.30),
                       (PORCH_X1 + 0.25, -HALF_Y, z_porch))

    for ix in range(6):
        for iy in range(4):
            x0 = PORCH_X0 + ix * 0.50 + 0.02
            x1 = x0 + 0.46
            y0 = PORCH_Y_FRONT + iy * 0.35 + 0.02
            y1 = y0 + 0.31
            b_lastre.color = jitter_color((1.0, 1.0, 1.0), 0.12)
            add_box(b_lastre, (x0, y0, z_porch), (x1, y1, z_porch + 0.04))

    for step in range(2):
        sz0 = z_porch - (step + 1) * 0.16
        sz1 = z_porch - step * 0.16
        sy0 = PORCH_Y_FRONT - 0.15 - (2 - step) * 0.32
        sy1 = PORCH_Y_FRONT - 0.15 - (1 - step) * 0.32
        add_box(b_zoccolo, (PORCH_X0 - 0.10, sy0, sz0), (PORCH_X1 + 0.10, sy1, sz1))

    col_xs = (PORCH_X0 + 0.15, PORCH_X1 - 0.15)
    for cx in col_xs:
        add_box_c(b_zoccolo, (cx, PORCH_Y_FRONT + 0.15, z_porch + 0.22), (0.32, 0.32, 0.44))
        add_box_c(b_scuro, (cx, PORCH_Y_FRONT + 0.15, (z_porch + 0.44 + PORCH_Z_ROOF) / 2),
                  (0.22, 0.22, PORCH_Z_ROOF - (z_porch + 0.44)))
        add_box_c(b_scuro, (cx, PORCH_Y_FRONT + 0.15, PORCH_Z_ROOF - 0.10), (0.34, 0.34, 0.16))
        p_top = Vector((cx, PORCH_Y_FRONT + 0.15, PORCH_Z_ROOF - 0.08))
        p_wall = Vector((cx, -HALF_Y, PORCH_Z_ROOF - 0.65))
        add_cylinder(b_scuro, p_wall, p_top, 0.07, sides=8)

    add_box(b_scuro, (PORCH_X0 - 0.10, PORCH_Y_FRONT + 0.05, PORCH_Z_ROOF - 0.20),
                     (PORCH_X1 + 0.10, PORCH_Y_FRONT + 0.25, PORCH_Z_ROOF))

    # Legnaia alpina
    stack_x0, stack_x1 = -4.20, -2.80
    stack_y0, stack_y1 = -HALF_Y - 0.65, -HALF_Y
    stack_z0 = Z_PLINTH
    stack_z1 = Z_PLINTH + 1.85

    add_box(b_tronco, (stack_x0 - 0.10, stack_y0 - 0.08, stack_z0),
                      (stack_x0 + 0.05, stack_y1, stack_z1 + 0.10))
    add_box(b_tronco, (stack_x1 - 0.05, stack_y0 - 0.08, stack_z0),
                      (stack_x1 + 0.10, stack_y1, stack_z1 + 0.10))
    add_box(b_larice, (stack_x0 - 0.20, stack_y0 - 0.18, stack_z1),
                      (stack_x1 + 0.20, stack_y1 + 0.05, stack_z1 + 0.12))

    log_len = 0.55
    log_rad = 0.075
    n_layers = int((stack_z1 - stack_z0) / (log_rad * 1.7))
    n_cols = int((stack_x1 - stack_x0) / (log_rad * 2.2))

    for ly in range(n_layers):
        lz = stack_z0 + 0.08 + ly * (log_rad * 1.65)
        for lc in range(n_cols):
            lx = stack_x0 + 0.10 + lc * (log_rad * 2.1) + rr(-0.02, 0.02)
            p0 = Vector((lx, stack_y0 + 0.06, lz))
            p1 = Vector((lx, stack_y0 + 0.06 + log_len, lz))
            b_spaccato.color = jitter_color((1.0, 0.95, 0.85), 0.18)
            add_cylinder(b_spaccato, p0, p1, log_rad, sides=6)

    # Panca rustica
    bench_x = 1.80
    bench_y = -HALF_Y - 0.55
    bench_z = Z_PLINTH
    add_box_c(b_larice, (bench_x, bench_y, bench_z + 0.46), (1.50, 0.42, 0.08))
    add_box_c(b_larice, (bench_x, bench_y + 0.18, bench_z + 0.82), (1.50, 0.06, 0.65))
    add_cylinder(B["legno_intaglio"], Vector((bench_x, bench_y + 0.16, bench_z + 0.92)),
                 Vector((bench_x, bench_y + 0.20, bench_z + 0.92)), 0.10, sides=12)
    for gx in (-0.55, 0.55):
        add_box_c(b_scuro, (bench_x + gx, bench_y, bench_z + 0.23), (0.08, 0.38, 0.46))

    # Antichi sci e bastoncini
    ski_x = 1.05
    for sx in (-0.06, 0.06):
        p_bot = Vector((ski_x + sx, -HALF_Y - 0.42, Z_PLINTH))
        p_top = Vector((ski_x + sx, -HALF_Y - 0.08, Z_PLINTH + 2.10))
        add_box_c(b_larice, (p_bot + p_top) / 2, (0.09, 0.025, 2.12))
        add_cylinder(b_larice, p_top, p_top + Vector((0, -0.08, 0.12)), 0.035, sides=6)
        add_box_c(b_ferro, (p_bot + p_top) * 0.48, (0.11, 0.05, 0.14))

    for bx in (-0.14, 0.14):
        p_bot = Vector((ski_x + bx, -HALF_Y - 0.38, Z_PLINTH))
        p_top = Vector((ski_x + bx * 0.8, -HALF_Y - 0.10, Z_PLINTH + 1.45))
        add_cylinder(b_scuro, p_bot, p_top, 0.012, sides=6)
        add_cylinder(b_ferro, p_bot + Vector((0, 0, 0.18)), p_bot + Vector((0, 0, 0.20)), 0.07, sides=10)

    # Slitta da neve
    sled_c = Vector((2.85, -HALF_Y - 0.70, Z_PLINTH + 0.18))
    for sy in (-0.18, 0.18):
        add_box_c(b_larice, sled_c + Vector((0, sy, 0)), (0.95, 0.04, 0.12))
        add_box_c(b_ferro, sled_c + Vector((0, sy, -0.06)), (0.95, 0.045, 0.015))
    for lx in (-0.25, -0.10, 0.05, 0.20):
        add_box_c(b_larice, sled_c + Vector((lx, 0, 0.10)), (0.10, 0.44, 0.025))

    # Lanterne in ferro battuto
    lantern_positions = [
        Vector((PORCH_X0 + 0.15, PORCH_Y_FRONT + 0.15, PORCH_Z_ROOF - 0.45)),
        Vector((-0.55, -HALF_Y - 0.12, Z_PLINTH + 1.95)),
        Vector((BALCONY_SIDE_X + 0.08, BALCONY_FRONT_Y + 0.08, BALCONY_Z + 1.25)),
    ]
    for lpos in lantern_positions:
        add_cylinder(b_ferro, lpos + Vector((0, 0.12, 0.20)), lpos + Vector((0, 0, 0.15)), 0.018, sides=6)
        add_cylinder(b_ferro, lpos - Vector((0, 0, 0.18)), lpos + Vector((0, 0, 0.18)), 0.09, sides=6, caps=False)
        add_cone(b_ferro, lpos + Vector((0, 0, 0.18)), lpos + Vector((0, 0, 0.28)), 0.10, 0.01, sides=6)
        add_cylinder(b_vlanterna, lpos - Vector((0, 0, 0.14)), lpos + Vector((0, 0, 0.14)), 0.08, sides=6)
        add_sphere(b_llanterna, lpos, 0.035, segs=8, rings=6)


# ---------------------------------------------------------------------------
# 4. SERRAMENTI, FINESTRE CON SCURI E PORTONE IN MASSELLO
# ---------------------------------------------------------------------------
def build_finestra_aperta(B, fac, xc, yc, z0, w, h, kind="finestra", has_shutters=True, curtain_type="tende"):
    b_scuro = B["legno_scuro"]
    b_scuri = B["legno_scuri"]
    b_vetro = B["vetro"]
    b_ferro = B["ferro"]
    b_tende = B["tende"]
    b_pizzo = B["pizzo"]
    b_zoccolo = B["pietra_zoccolo"]
    b_intaglio = B["legno_intaglio"]

    z1 = z0 + h
    zc = (z0 + z1) / 2.0
    tf = 0.065
    df = 0.080

    if fac == "S":
        wall_y = -HALF_Y
        y_frame = wall_y + 0.08

        if "pt" in kind:
            add_box_c(b_zoccolo, (xc, wall_y - 0.08, z0 - 0.05), (w + 0.22, 0.32, 0.10))

        add_box_c(b_scuro, (xc, y_frame, z1 - tf / 2), (w, df, tf))
        if "portafinestra" not in kind:
            add_box_c(b_scuro, (xc, y_frame, z0 + tf / 2), (w, df, tf))
            add_box_c(b_scuro, (xc - w / 2 + tf / 2, y_frame, zc), (tf, df, h - 2 * tf))
            add_box_c(b_scuro, (xc + w / 2 - tf / 2, y_frame, zc), (tf, df, h - 2 * tf))
            add_box_c(b_scuro, (xc, y_frame, zc), (0.045, df * 0.8, h - 2 * tf))
            add_box_c(b_scuro, (xc, y_frame, zc + 0.10), (w - 2 * tf, df * 0.8, 0.045))
        else:
            add_box_c(b_scuro, (xc - w / 2 + tf / 2, y_frame, zc), (tf, df, h - tf))
            add_box_c(b_scuro, (xc + w / 2 - tf / 2, y_frame, zc), (tf, df, h - tf))
            add_box_c(b_scuro, (xc, y_frame, zc), (0.05, df * 0.8, h - tf))
            for ry in (zc - 0.45, zc + 0.45):
                add_box_c(b_scuro, (xc, y_frame, ry), (w - 2 * tf, df * 0.8, 0.045))

        add_box_c(b_vetro, (xc, y_frame, zc), (w - 2 * tf + 0.02, 0.012, h - (2 * tf if "portafinestra" not in kind else tf) + 0.02))

        if curtain_type == "pizzo":
            add_box_c(b_pizzo, (xc, y_frame + 0.06, zc + 0.05), (w - 2 * tf - 0.04, 0.008, h * 0.75))
        elif curtain_type == "tende":
            tw = (w - 2 * tf) * 0.42
            add_box_c(b_tende, (xc - (w - 2 * tf) * 0.28, y_frame + 0.06, zc), (tw, 0.008, h - 2 * tf - 0.08))
            add_box_c(b_tende, (xc + (w - 2 * tf) * 0.28, y_frame + 0.06, zc), (tw, 0.008, h - 2 * tf - 0.08))

        if has_shutters:
            shutter_w = (w - 0.04) / 2.0
            shutter_t = 0.035
            for s_sgn in (-1, 1):
                sx_pos = xc + (w / 2 + shutter_w / 2 + 0.02) * s_sgn
                sy_pos = wall_y - 0.03
                add_box_c(b_scuri, (sx_pos, sy_pos, zc), (shutter_w, shutter_t, h - 0.04))
                add_box_c(b_scuri, (sx_pos, sy_pos - 0.02, z0 + 0.15), (shutter_w, 0.02, 0.08))
                add_box_c(b_scuri, (sx_pos, sy_pos - 0.02, z1 - 0.15), (shutter_w, 0.02, 0.08))
                add_box_c(b_scuri, (sx_pos, sy_pos - 0.02, zc), (shutter_w * 0.85, 0.02, 0.06),
                          rot=Matrix.Rotation(math.radians(35.0 * s_sgn), 3, "Y"))
                add_box_c(b_ferro, (sx_pos - s_sgn * shutter_w * 0.15, sy_pos - 0.025, z0 + 0.15),
                          (shutter_w * 0.7, 0.015, 0.04))
                add_box_c(b_ferro, (sx_pos - s_sgn * shutter_w * 0.15, sy_pos - 0.025, z1 - 0.15),
                          (shutter_w * 0.7, 0.015, 0.04))

    elif fac == "W":
        wall_x = -HALF_X
        x_frame = wall_x + 0.08

        if "pt" in kind:
            add_box_c(b_zoccolo, (wall_x - 0.08, yc, z0 - 0.05), (0.32, w + 0.22, 0.10))

        add_box_c(b_scuro, (x_frame, yc, z1 - tf / 2), (df, w, tf))
        if "portafinestra" not in kind and "attic" not in kind:
            add_box_c(b_scuro, (x_frame, yc, z0 + tf / 2), (df, w, tf))
            add_box_c(b_scuro, (x_frame, yc - w / 2 + tf / 2, zc), (df, tf, h - 2 * tf))
            add_box_c(b_scuro, (x_frame, yc + w / 2 - tf / 2, zc), (df, tf, h - 2 * tf))
            add_box_c(b_scuro, (x_frame, yc, zc), (df * 0.8, 0.045, h - 2 * tf))
            add_box_c(b_scuro, (x_frame, yc, zc + 0.10), (df * 0.8, w - 2 * tf, 0.045))
        elif "attic" in kind:
            add_box_c(b_scuro, (x_frame, yc, z0 + tf / 2), (df, w, tf))
            add_box_c(b_scuro, (x_frame, yc - w / 2 + tf / 2, zc), (df, tf, h - 2 * tf))
            add_box_c(b_scuro, (x_frame, yc + w / 2 - tf / 2, zc), (df, tf, h - 2 * tf))
            add_cylinder(b_intaglio, Vector((x_frame, yc, z0 + tf)), Vector((x_frame, yc, z1 - tf)), 0.045, sides=8)
        else:
            add_box_c(b_scuro, (x_frame, yc - w / 2 + tf / 2, zc), (df, tf, h - tf))
            add_box_c(b_scuro, (x_frame, yc + w / 2 - tf / 2, zc), (df, tf, h - tf))
            add_box_c(b_scuro, (x_frame, yc, zc), (df * 0.8, 0.05, h - tf))

        add_box_c(b_vetro, (x_frame, yc, zc), (0.012, w - 2 * tf + 0.02, h - (2 * tf if "portafinestra" not in kind else tf) + 0.02))

        if curtain_type == "pizzo":
            add_box_c(b_pizzo, (x_frame + 0.06, yc, zc + 0.05), (0.008, w - 2 * tf - 0.04, h * 0.75))
        elif curtain_type == "tende":
            tw = (w - 2 * tf) * 0.42
            add_box_c(b_tende, (x_frame + 0.06, yc - (w - 2 * tf) * 0.28, zc), (0.008, tw, h - 2 * tf - 0.08))
            add_box_c(b_tende, (x_frame + 0.06, yc + (w - 2 * tf) * 0.28, zc), (0.008, tw, h - 2 * tf - 0.08))

        if has_shutters and "attic" not in kind and "portafinestra" not in kind:
            shutter_w = (w - 0.04) / 2.0
            shutter_t = 0.035
            for s_sgn in (-1, 1):
                sy_pos = yc + (w / 2 + shutter_w / 2 + 0.02) * s_sgn
                sx_pos = wall_x - 0.03
                add_box_c(b_scuri, (sx_pos, sy_pos, zc), (shutter_t, shutter_w, h - 0.04))
                add_box_c(b_scuri, (sx_pos - 0.02, sy_pos, z0 + 0.15), (0.02, shutter_w, 0.08))
                add_box_c(b_scuri, (sx_pos - 0.02, sy_pos, z1 - 0.15), (0.02, shutter_w, 0.08))
                add_box_c(b_ferro, (sx_pos - 0.025, sy_pos - s_sgn * shutter_w * 0.15, z0 + 0.15),
                          (0.015, shutter_w * 0.7, 0.04))
                add_box_c(b_ferro, (sx_pos - 0.025, sy_pos - s_sgn * shutter_w * 0.15, z1 - 0.15),
                          (0.015, shutter_w * 0.7, 0.04))


def build_serramenti(B):
    """Costruisce finestre con vetri doppi, scuri alpini a Z, tendine e portoni."""
    b_porta = B["legno_porta"]
    b_ferro = B["ferro"]
    b_ottone = B["ottone"]

    for op in OPENINGS:
        fac = op["facciata"]
        k = op["kind"]
        w, h = op["w"], op["h"]
        z0 = op["z0"]
        zc = z0 + h / 2.0

        if k == "portone":
            xc = op["x"]
            wall_y = -HALF_Y
            yc = wall_y + T_WALL_STONE / 2.0
            add_box_c(b_porta, (xc, yc, zc), (w - 0.08, 0.08, h - 0.08))
            add_box_c(b_porta, (xc - 0.28, yc - 0.045, zc), (w * 0.40, 0.03, h * 0.85))
            add_box_c(b_porta, (xc + 0.28, yc - 0.045, zc), (w * 0.40, 0.03, h * 0.85))
            for bx in (-0.45, -0.15, 0.15, 0.45):
                for bz in (z0 + 0.3, z0 + 0.8, z0 + 1.3, z0 + 1.8, z0 + 2.1):
                    add_sphere(b_ferro, (xc + bx, yc - 0.065, bz), 0.018, segs=6, rings=4)
            add_cylinder(b_ottone, Vector((xc + 0.42, yc - 0.08, z0 + 1.05)),
                         Vector((xc + 0.42, yc - 0.08, z0 + 1.25)), 0.016, sides=8)

        elif fac == "S":
            curt = "pizzo" if "portafinestra" in k else "tende"
            shutters = "portafinestra" not in k
            build_finestra_aperta(B, "S", op["x"], 0, z0, w, h, k, shutters, curt)

        elif fac == "W":
            curt = "pizzo" if "portafinestra" in k else ("pizzo" if "attic" in k else "tende")
            shutters = "portafinestra" not in k and "attic" not in k
            build_finestra_aperta(B, "W", 0, op["y"], z0, w, h, k, shutters, curt)

        elif fac in ("N", "E"):
            if fac == "N":
                b_scuro, b_vetro, b_tende = B["legno_scuro"], B["vetro"], B["tende"]
                xc = op["x"]
                yc = HALF_Y - 0.15
                add_box_c(b_scuro, (xc, yc, zc), (w, 0.08, h))
                add_box_c(b_vetro, (xc, yc, zc), (w - 0.12, 0.015, h - 0.12))
                add_box_c(b_tende, (xc, yc - 0.04, zc), (w - 0.16, 0.01, h - 0.16))
            else:
                b_scuro, b_vetro, b_pizzo = B["legno_scuro"], B["vetro"], B["pizzo"]
                xc = HALF_X - 0.15
                yc = op["y"]
                add_box_c(b_scuro, (xc, yc, zc), (0.08, w, h))
                add_box_c(b_vetro, (xc, yc, zc), (0.015, w - 0.12, h - 0.12))
                add_box_c(b_pizzo, (xc - 0.04, yc, zc), (0.01, w - 0.16, h - 0.16))


# ---------------------------------------------------------------------------
# 5. TETTO ALPINO: Carpenteria a vista, Scandole, Fermaneve, Rame e Comignolo
# ---------------------------------------------------------------------------
def build_tetto_e_copertura(B):
    """Costruisce orditura completa del tetto, tavolato, scandole in larice, fermaneve, rame e comignolo."""
    b_scuro = B["legno_scuro"]
    b_larice = B["legno_larice"]
    b_scandole = B["scandole"]
    b_intaglio = B["legno_intaglio"]
    b_ferro = B["ferro"]
    b_rame = B["rame"]
    b_zoccolo = B["pietra_zoccolo"]

    Y_EAVE = HALF_Y + EAVES_FRONT    # 3.70 + 1.35 = 5.05
    X_RAKE = HALF_X + EAVES_GABLE    # 4.60 + 0.95 = 5.55
    L = Y_EAVE / COS_P               # lunghezza falda ~ 5.72 m

    ridge_z = Z_RIDGE_STRUCT
    add_box(b_scuro, (-X_RAKE - 0.20, -0.16, ridge_z - 0.32),
                     ( X_RAKE + 0.20,  0.16, ridge_z))
    for rx in (-X_RAKE - 0.10, X_RAKE + 0.10):
        add_box_c(b_intaglio, (rx, 0.0, ridge_z - 0.16), (0.24, 0.38, 0.36))

    chimney_x = 2.10
    chimney_y = 1.20

    for sgn in (-1, 1):
        ey = sgn * Y_EAVE
        es = Vector((0.0, -sgn * COS_P, SIN_P))   # verso il colmo
        en = Vector((0.0, sgn * SIN_P, COS_P))    # normale esterna falda
        ex = Vector((1.0, 0.0, 0.0))              # lungo la facciata
        eave_pt = Vector((0.0, ey, ridge_z - L * SIN_P))

        # Arcarecci intermedi longitudinali
        for f_purlin in (0.35, 0.70):
            purl_pt = eave_pt + es * (L * f_purlin) - en * 0.18
            add_box_v(b_scuro, purl_pt - ex * (X_RAKE + 0.15),
                      ex * (2 * X_RAKE + 0.30), es * 0.20, -en * 0.22)

        # Travetti sagomati a vista (rafters)
        rafter_w = 0.12
        rafter_h = 0.18
        rafter_step = 0.48
        nt = int((2 * X_RAKE) / rafter_step) + 1
        for i in range(nt):
            x = -X_RAKE + 0.08 + i * (2 * X_RAKE - 0.16) / (nt - 1)
            p = eave_pt + ex * (x - rafter_w / 2)
            add_box_v(b_scuro, p, ex * rafter_w, es * L, -en * rafter_h)
            p_head = p - es * 0.02 - en * (rafter_h * 0.5)
            add_cone(b_intaglio, p_head + ex * (rafter_w / 2),
                     p_head + ex * (rafter_w / 2) - es * 0.12,
                     rafter_w * 0.45, 0.02, sides=6)

        # Tavolato in larice continuo sopra i travetti
        tavolato_t = 0.038
        p_deck = eave_pt - ex * X_RAKE
        b_larice.color = jitter_color((1.0, 1.0, 1.0), 0.10)
        add_box_v(b_larice, p_deck, ex * (2 * X_RAKE), es * L, en * tavolato_t)

        # Frontalino intagliato di gronda
        p_fascia = eave_pt - ex * X_RAKE - en * (rafter_h - 0.02)
        add_box_v(b_intaglio, p_fascia, ex * (2 * X_RAKE), -es * 0.035, en * (rafter_h + tavolato_t + 0.04))

        # Tavole di bordo sagomate sui timpani (bargeboards)
        for sx in (-1, 1):
            p_barge = eave_pt + ex * (sx * X_RAKE - (0.04 if sx > 0 else 0.0)) - en * (rafter_h + 0.02)
            add_box_v(b_intaglio, p_barge, ex * 0.04, es * (L + 0.05), en * (rafter_h + tavolato_t + 0.06))

        # Scandole di larice alpino posate una ad una
        STEP_X = 0.132
        TILE_L = 0.42
        EXPO = 0.140
        T_SHINGLE = 0.022
        plane0 = eave_pt + en * tavolato_t

        nrow = int((L - 0.10) / EXPO) + 1
        ncol = int((2 * X_RAKE + 0.10) / STEP_X)
        x0 = -X_RAKE + 0.02 + ((2 * X_RAKE + 0.10) - (ncol - 1) * STEP_X) / 2.0

        for r in range(nrow):
            s = -0.04 + r * EXPO
            off_x = (STEP_X * 0.5) if (r % 2 == 1) else 0.0
            for c in range(ncol):
                x = x0 + c * STEP_X + off_x + rr(-0.003, 0.003)
                if abs(x) > X_RAKE + 0.02:
                    continue
                # Salto del comignolo SOLO sul lato Nord dove si trova il comignolo
                if sgn > 0 and (chimney_x - 0.55 <= x <= chimney_x + 0.55) and (0.6 <= abs(ey - sgn * s * COS_P) <= 1.8):
                    continue
                b_scandole.color = jitter_color((1.0, 0.94, 0.86), 0.20)
                yaw = rr(-0.018, 0.018)
                exr = (ex * math.cos(yaw) + es * math.sin(yaw)).normalized()
                esr = (es * math.cos(yaw) - ex * math.sin(yaw)).normalized()
                org = plane0 + exr * (x - STEP_X * 0.52) + esr * (s + rr(-0.004, 0.004)) + en * (0.002 + (r % 2) * 0.004)
                add_box_v(b_scandole, org, exr * (STEP_X * 1.04), esr * TILE_L, en * T_SHINGLE)

        # Fermaneve in tronchi con staffe in ferro battuto
        for f_snow in (0.22, 0.48):
            p_snow_0 = eave_pt + es * (L * f_snow) + en * 0.08 - ex * (X_RAKE - 0.25)
            p_snow_1 = eave_pt + es * (L * f_snow) + en * 0.08 + ex * (X_RAKE - 0.25)
            add_cylinder(b_larice, p_snow_0, p_snow_1, 0.065, sides=8)
            for bx in range(int(-X_RAKE + 0.8), int(X_RAKE - 0.4), 1):
                p_b0 = eave_pt + es * (L * f_snow - 0.15) + en * (tavolato_t + 0.02) + ex * bx
                p_b1 = eave_pt + es * (L * f_snow + 0.08) + en * 0.14 + ex * bx
                add_cylinder(b_ferro, p_b0, p_b1, 0.016, sides=6)

        # Grondaia in rame sagomata
        gy = ey + sgn * 0.06
        gz = (ridge_z - L * SIN_P) - 0.06
        g_start = Vector((-X_RAKE - 0.05, gy, gz))
        g_end = Vector((X_RAKE + 0.05, gy, gz))
        add_cylinder(b_rame, g_start, g_end, 0.075, sides=12)

        for bx in range(int(-X_RAKE + 0.6), int(X_RAKE), 1):
            p_roof = eave_pt + ex * bx - en * 0.02
            p_gut = Vector((bx, gy, gz))
            add_cylinder(b_ferro, p_roof, p_gut, 0.014, sides=6)

        # Pluviali verticali in rame
        for px in (-HALF_X - 0.25, HALF_X + 0.25):
            p_top = Vector((px, gy, gz))
            p_wall = Vector((px, gy - sgn * 0.45, gz - 0.45))
            p_ground = Vector((px, gy - sgn * 0.45, Z_GROUND + 0.12))
            add_cylinder(b_rame, p_top, p_wall, 0.045, sides=10)
            add_cylinder(b_rame, p_wall, p_ground, 0.045, sides=10)
            for cz in (Z_PLINTH + 0.6, Z_F1 + 0.5, Z_F1 + 2.1):
                add_cylinder(b_ferro, Vector((px - 0.06, p_wall.y, cz)),
                             Vector((px + 0.06, p_wall.y, cz)), 0.015, sides=6)

    # Fila di colmo superiore (scandole di colmo)
    x_curr = -X_RAKE - 0.05
    while x_curr <= X_RAKE + 0.05:
        b_scandole.color = jitter_color((0.92, 0.88, 0.82), 0.15)
        zc = ridge_z + 0.04
        add_box_c(b_scandole, (x_curr, 0.0, zc), (0.14, 0.32, 0.025),
                  rot=Matrix.Rotation(math.radians(12.0), 3, "Y"))
        x_curr += 0.11

    # Comignolo monumentale in pietra
    chimney_w, chimney_d = 0.85, 0.85
    z_chimney_bot = Z_RIDGE_STRUCT - (abs(chimney_y) / COS_P) * SIN_P - 0.25
    z_chimney_top = Z_RIDGE_STRUCT + 1.75

    add_box_c(b_zoccolo, (chimney_x, chimney_y, (z_chimney_bot + z_chimney_top) / 2),
              (chimney_w, chimney_d, z_chimney_top - z_chimney_bot))
    add_box_c(b_rame, (chimney_x, chimney_y, z_chimney_bot + 0.28),
              (chimney_w + 0.16, chimney_d + 0.16, 0.14))
    add_box_c(b_zoccolo, (chimney_x, chimney_y, z_chimney_top + 0.06),
              (chimney_w + 0.20, chimney_d + 0.20, 0.12))
    for cx in (-chimney_w * 0.35, chimney_w * 0.35):
        for cy in (-chimney_d * 0.35, chimney_d * 0.35):
            add_box_c(b_zoccolo, (chimney_x + cx, chimney_y + cy, z_chimney_top + 0.25),
                      (0.15, 0.15, 0.26))
    add_box_c(b_zoccolo, (chimney_x, chimney_y, z_chimney_top + 0.44),
              (chimney_w + 0.24, chimney_d + 0.24, 0.10))
    p_vane_bot = Vector((chimney_x, chimney_y, z_chimney_top + 0.49))
    p_vane_top = p_vane_bot + Vector((0, 0, 0.70))
    add_cylinder(b_ferro, p_vane_bot, p_vane_top, 0.016, sides=8)
    add_cylinder(b_ferro, p_vane_top - Vector((0.28, 0, 0.12)), p_vane_top + Vector((0.28, 0, -0.12)), 0.012, sides=6)
    add_cone(b_ferro, p_vane_top + Vector((0.28, 0, -0.12)), p_vane_top + Vector((0.40, 0, -0.12)), 0.035, 0.005, sides=6)


# ---------------------------------------------------------------------------
# 6. INTERNI: Stube Tirolese, Focolare, Tavolo, Giropanca e Camera
# ---------------------------------------------------------------------------
def build_interni(B):
    """Costruisce interni caldi alpini visibili attraverso le finestre."""
    b_pav = B["legno_pavimento"]
    b_scuro = B["legno_scuro"]
    b_stube = B["stube"]
    b_fuoco = B["luce_fuoco"]
    b_luce = B["luce_calda"]
    b_larice = B["legno_larice"]
    b_intaglio = B["legno_intaglio"]
    b_lana = B["lana"]
    b_ferro = B["ferro"]

    for ix in range(int(W_X / 0.22)):
        px0 = -HALF_X + 0.20 + ix * 0.22
        px1 = px0 + 0.21
        b_pav.color = jitter_color((1.0, 1.0, 1.0), 0.12)
        add_box(b_pav, (px0, -HALF_Y + 0.20, Z_PLINTH), (px1, HALF_Y - 0.20, Z_PLINTH + 0.03))

    for ix in range(int(W_X / 0.22)):
        px0 = -HALF_X + 0.20 + ix * 0.22
        px1 = px0 + 0.21
        b_pav.color = jitter_color((1.0, 1.0, 1.0), 0.12)
        add_box(b_pav, (px0, -HALF_Y + 0.20, Z_F1), (px1, HALF_Y - 0.20, Z_F1 + 0.03))

    for beam_x in (-3.0, -1.5, 0.0, 1.5, 3.0):
        add_box_c(b_scuro, (beam_x, 0, Z_F1 - 0.12), (0.20, D_Y - 0.6, 0.24))
        add_box_c(b_scuro, (beam_x, 0, Z_EAVE_WALL - 0.12), (0.20, D_Y - 0.6, 0.24))

    # Stube Tirolese
    stube_x, stube_y = -2.60, -1.60
    stube_z = Z_PLINTH + 0.03
    add_box_c(b_larice, (stube_x, stube_y, stube_z + 0.22), (1.80, 1.80, 0.44))
    add_box_c(b_stube, (stube_x, stube_y, stube_z + 1.10), (1.25, 1.25, 1.35))
    add_box_c(b_stube, (stube_x, stube_y, stube_z + 1.95), (0.95, 0.95, 0.45))
    add_box_c(b_ferro, (stube_x, stube_y - 0.64, stube_z + 0.45), (0.45, 0.08, 0.45))
    add_sphere(b_fuoco, (stube_x, stube_y - 0.55, stube_z + 0.42), 0.14, segs=8, rings=6)

    # Tavolo da baita
    table_x, table_y = 2.40, -1.80
    table_z = Z_PLINTH + 0.03
    add_box_c(b_larice, (table_x, table_y, table_z + 0.76), (1.90, 1.10, 0.08))
    for tx in (-0.65, 0.65):
        add_box_c(b_scuro, (table_x + tx, table_y, table_z + 0.38), (0.10, 0.85, 0.68))

    add_box(b_larice, (table_x - 1.20, table_y - 0.85, table_z),
                      (table_x + 1.20, table_y - 0.55, table_z + 0.46))
    add_box(b_larice, (table_x + 0.95, table_y - 0.85, table_z),
                      (table_x + 1.25, table_y + 0.85, table_z + 0.46))

    for cy in (-0.35, 0.35):
        cx = table_x - 0.85
        add_box_c(b_intaglio, (cx, table_y + cy, table_z + 0.45), (0.42, 0.42, 0.06))
        add_box_c(b_intaglio, (cx - 0.18, table_y + cy, table_z + 0.72), (0.05, 0.38, 0.50))
        for sx in (-0.15, 0.15):
            for sy in (-0.15, 0.15):
                add_cylinder(b_scuro, Vector((cx + sx, table_y + cy + sy, table_z)),
                             Vector((cx + sx * 0.7, table_y + cy + sy * 0.7, table_z + 0.45)), 0.025, sides=6)

    # Credenza
    cred_x, cred_y = 3.60, 1.20
    add_box_c(b_larice, (cred_x, cred_y, Z_PLINTH + 0.90), (0.65, 1.60, 1.70))
    add_box_c(b_intaglio, (cred_x - 0.34, cred_y, Z_PLINTH + 0.90), (0.04, 1.45, 1.50))

    # Lampadario
    lamp_x, lamp_y = 2.40, -1.80
    lamp_z = Z_F1 - 0.75
    add_cylinder(b_ferro, Vector((lamp_x, lamp_y, Z_F1)), Vector((lamp_x, lamp_y, lamp_z + 0.25)), 0.015, sides=6)
    add_cylinder(b_scuro, Vector((lamp_x, lamp_y, lamp_z)), Vector((lamp_x, lamp_y, lamp_z + 0.08)), 0.35, sides=8)
    for ang in (0, PI * 0.5, PI, PI * 1.5):
        lx = lamp_x + math.cos(ang) * 0.35
        ly = lamp_y + math.sin(ang) * 0.35
        add_sphere(b_luce, (lx, ly, lamp_z + 0.12), 0.045, segs=8, rings=6)

    # Camera P1
    bed_x, bed_y = -2.20, -1.60
    bed_z = Z_F1 + 0.03
    add_box_c(b_larice, (bed_x, bed_y, bed_z + 0.30), (1.90, 2.10, 0.45))
    add_box_c(b_intaglio, (bed_x, bed_y - 1.02, bed_z + 0.65), (1.90, 0.08, 1.15))
    add_box_c(b_lana, (bed_x, bed_y + 0.15, bed_z + 0.52), (1.75, 1.65, 0.22))
    add_box_c(b_lana, (bed_x - 0.45, bed_y - 0.65, bed_z + 0.58), (0.65, 0.45, 0.15))
    add_box_c(b_lana, (bed_x + 0.45, bed_y - 0.65, bed_z + 0.58), (0.65, 0.45, 0.15))
    add_box_c(b_larice, (bed_x + 1.25, bed_y - 0.80, bed_z + 0.30), (0.50, 0.50, 0.60))
    add_sphere(b_luce, (bed_x + 1.25, bed_y - 0.80, bed_z + 0.72), 0.04, segs=8, rings=6)


# ---------------------------------------------------------------------------
# 7. GIARDINO ALPINO: Terreno, Fontana, Sentiero, Flora, Alberi e Montagne
# ---------------------------------------------------------------------------
def build_giardino_e_paesaggio(B):
    """Costruisce terreno alpino, fontana a tronco, staccionata, abeti, flora e montagne."""
    build_terreno_alpino(B)
    build_sentiero_beole(B)
    build_fontana_tronco(B)
    build_staccionata_alpina(B)
    build_massi_granito(B)
    build_flora_alpina(B)
    build_abeti_e_pini(B)
    build_rododendri_arbusti(B)
    build_erba_fitta(B)
    build_catena_alpina_sfondo(B)


def build_terreno_alpino(B):
    """Genera la mesh del terreno montuoso circostante."""
    b_prato = B["prato"]

    rings = 36
    segs = 48
    r_max = 135.0

    grid = []
    for ir in range(rings + 1):
        t = ir / rings
        rad = (t ** 1.8) * r_max
        row = []
        for iseg in range(segs):
            ang = TAU * iseg / segs
            gx = math.cos(ang) * rad
            gy = math.sin(ang) * rad
            gz = terrain_z(gx, gy)
            row.append(Vector((gx, gy, gz)))
        grid.append(row)

    base = [b_prato.add(row) for row in grid]
    for r in range(rings):
        a, b = base[r], base[r + 1]
        for s in range(segs):
            s_next = (s + 1) % segs
            b_prato.face((a + s, a + s_next, b + s_next, b + s), smooth=True)


def build_sentiero_beole(B):
    """Costruisce il sentiero in lastre di pietra irregolari (beole)."""
    b_lastre = B["pietra_lastre"]

    path_points = [
        ( 0.30, -5.2),
        ( 0.20, -5.8),
        (-0.10, -6.5),
        (-0.60, -7.3),
        (-1.20, -8.1),
        (-2.00, -8.9),
        (-3.00, -9.8),
        (-4.20, -10.8),
        (-5.60, -11.8),
        (-2.2, -6.2),
        (-3.4, -5.8),
        (-4.6, -5.2),
        (-5.8, -4.6),
        (-1.8, -4.8),
        (-2.8, -4.6),
        (-3.6, -4.5),
    ]

    for px, py in path_points:
        pz = terrain_z(px, py)
        for _ in range(3):
            lx = px + rr(-0.45, 0.45)
            ly = py + rr(-0.45, 0.45)
            lz = terrain_z(lx, ly)
            lw = rr(0.42, 0.68)
            ld = rr(0.38, 0.62)
            rot_z = Matrix.Rotation(rr(0, TAU), 3, "Z")
            b_lastre.color = jitter_color((1.0, 1.0, 1.0), 0.12)
            add_box_c(b_lastre, (lx, ly, lz + 0.02), (lw, ld, 0.05), rot=rot_z)


def build_fontana_tronco(B):
    """Costruisce la fontana rustica a tronco scavato con cannella in rame."""
    b_tronco = B["legno_tronco"]
    b_rame = B["rame"]
    b_acqua = B["acqua"]
    b_ferro = B["ferro"]
    b_lastre = B["pietra_lastre"]

    fx, fy = -5.40, -6.20
    fz = terrain_z(fx, fy)

    for _ in range(12):
        bx = fx + rr(-1.2, 1.2)
        by = fy + rr(-0.8, 0.8)
        bz = terrain_z(bx, by)
        add_sphere(b_lastre, (bx, by, bz + 0.02), rr(0.12, 0.22), segs=8, rings=6)

    t_len = 2.20
    t_rad = 0.42
    p0 = Vector((fx - t_len / 2, fy, fz + t_rad * 0.8))
    p1 = Vector((fx + t_len / 2, fy, fz + t_rad * 0.8))
    add_cylinder(b_tronco, p0, p1, t_rad, sides=12)
    add_box_c(b_tronco, (fx, fy, fz + t_rad * 0.8 + 0.15), (t_len - 0.40, t_rad * 1.3, 0.35))

    for cx in (-0.75, 0.75):
        add_cylinder(b_ferro, Vector((fx + cx - 0.02, fy, fz + t_rad * 0.8)),
                     Vector((fx + cx + 0.02, fy, fz + t_rad * 0.8)), t_rad + 0.02, sides=12)

    add_box_c(b_acqua, (fx, fy, fz + t_rad * 0.8 + 0.08), (t_len - 0.45, t_rad * 1.25, 0.02))

    p_post_bot = Vector((fx - 0.85, fy, fz))
    p_post_top = Vector((fx - 0.85, fy, fz + 1.25))
    add_cylinder(b_tronco, p_post_bot, p_post_top, 0.14, sides=10)
    add_cone(B["legno_intaglio"], p_post_top, p_post_top + Vector((0, 0, 0.18)), 0.16, 0.02, sides=8)

    p_spout0 = p_post_top - Vector((0, 0, 0.35))
    p_spout1 = p_spout0 + Vector((0.45, 0, -0.05))
    p_spout2 = p_spout1 + Vector((0.10, 0, -0.22))
    add_cylinder(b_rame, p_spout0, p_spout1, 0.025, sides=8)
    add_cylinder(b_rame, p_spout1, p_spout2, 0.022, sides=8)
    add_cylinder(b_acqua, p_spout2, Vector((p_spout2.x, p_spout2.y, fz + t_rad * 0.8 + 0.08)),
                 0.015, sides=6)


def build_staccionata_alpina(B):
    """Costruisce la staccionata tradizionale in tronchi grezzi."""
    b_tronco = B["legno_tronco"]

    fence_posts = [
        (-8.5, -12.0), (-6.5, -11.0), (-4.5, -10.2), (-2.5, -9.6), (-0.5, -9.2),
        ( 1.5,  -9.0), ( 3.5,  -9.0), ( 5.5,  -9.2), ( 7.5,  -9.6), ( 9.5, -10.2),
        (-8.5, -12.0), (-8.8,  -9.5), (-9.0,  -7.0), (-9.2,  -4.5), (-9.4,  -2.0),
        (-9.5,   0.5), (-9.6,   3.0), (-9.8,   5.5),
    ]

    for i in range(len(fence_posts)):
        px, py = fence_posts[i]
        pz = terrain_z(px, py)
        p_bot = Vector((px, py, pz - 0.20))
        p_top = Vector((px + rr(-0.04, 0.04), py + rr(-0.04, 0.04), pz + 1.15))
        add_cylinder(b_tronco, p_bot, p_top, 0.065, sides=8)

        if i + 1 < len(fence_posts) and (i != 9):
            nx, ny = fence_posts[i + 1]
            nz = terrain_z(nx, ny)
            p_next_bot = Vector((nx, ny, nz))
            p_next_top = Vector((nx, ny, nz + 1.15))

            for frac in (0.42, 0.82):
                pt0 = p_bot + (p_top - p_bot) * frac + Vector((0, 0, rr(-0.03, 0.03)))
                pt1 = p_next_bot + (p_next_top - p_next_bot) * frac + Vector((0, 0, rr(-0.03, 0.03)))
                add_cylinder(b_tronco, pt0, pt1, 0.045, sides=6)


def build_massi_granito(B):
    """Costruisce massi ed emergenze rocciose alpine."""
    b_masso = B["pietra_masso"]

    boulder_specs = [
        (-7.8, -7.5, 1.45, (1.3, 1.1, 0.85)),
        (-6.8, -8.2, 0.95, (1.1, 1.2, 0.75)),
        ( 6.8, -6.5, 1.65, (1.4, 1.2, 0.90)),
        ( 7.9, -5.2, 1.10, (1.0, 1.3, 0.80)),
        (-8.2,  3.5, 1.85, (1.5, 1.3, 0.95)),
        ( 8.5,  2.8, 2.10, (1.6, 1.4, 1.05)),
        ( 2.2, -8.2, 0.75, (1.2, 1.1, 0.70)),
        (-4.5, -1.8, 0.85, (1.1, 1.3, 0.75)),
    ]

    for bx, by, br, bscale in boulder_specs:
        bz = terrain_z(bx, by) + br * bscale[2] * 0.35
        add_sphere(b_masso, (bx, by, bz), br, segs=12, rings=8,
                   amp=0.22, nscale=1.8, scale=bscale, seed_off=bx)


def build_flora_alpina(B):
    """Costruisce stelle alpine, genziane blu e margherite montane."""
    b_stella = B["stella_alpina"]
    b_scentro = B["stella_centro"]
    b_genziana = B["genziana"]
    b_margherita = B["margherita"]

    for i in range(120):
        ang = rr(0, TAU)
        dist = rr(3.5, 16.0)
        fx = math.cos(ang) * dist
        fy = math.sin(ang) * dist
        if abs(fx) < HALF_X + 0.8 and abs(fy) < HALF_Y + 0.8:
            continue
        fz = terrain_z(fx, fy) + 0.05

        f_type = random.random()
        if f_type < 0.35:
            for _ in range(int(rr(2, 5))):
                ofx, ofy = fx + rr(-0.15, 0.15), fy + rr(-0.15, 0.15)
                ofz = terrain_z(ofx, ofy) + 0.06
                add_sphere(b_scentro, (ofx, ofy, ofz), 0.022, segs=6, rings=4)
                for p_ang in range(8):
                    pa = TAU * p_ang / 8.0
                    p_pos = Vector((ofx + math.cos(pa) * 0.045, ofy + math.sin(pa) * 0.045, ofz - 0.005))
                    add_sphere(b_stella, p_pos, 0.024, segs=5, rings=3, scale=(1.4, 0.8, 0.4))

        elif f_type < 0.70:
            for _ in range(int(rr(3, 7))):
                ofx, ofy = fx + rr(-0.20, 0.20), fy + rr(-0.20, 0.20)
                ofz = terrain_z(ofx, ofy) + 0.08
                p_bot = Vector((ofx, ofy, ofz - 0.06))
                p_top = Vector((ofx + rr(-0.02, 0.02), ofy + rr(-0.02, 0.02), ofz + 0.06))
                add_cone(b_genziana, p_bot, p_top, 0.015, 0.045, sides=6)

        else:
            for _ in range(int(rr(3, 8))):
                ofx, ofy = fx + rr(-0.25, 0.25), fy + rr(-0.25, 0.25)
                ofz = terrain_z(ofx, ofy) + 0.07
                add_sphere(b_scentro, (ofx, ofy, ofz), 0.018, segs=6, rings=4)
                add_sphere(b_margherita, (ofx, ofy, ofz - 0.004), 0.042, segs=8, rings=4, scale=(1.2, 1.2, 0.2))


def build_abeti_e_pini(B):
    """Costruisce maestosi abeti rossi e pini cembri alpini."""
    tree_specs = [
        (-11.8, -11.0, 10.8, "abete"),
        (-13.2,  -3.2, 12.0, "abete"),
        (-10.2,   4.5, 10.5, "abete"),
        (  8.5,  -5.2,  9.2, "pino_cembro"),
        ( 10.2,  -1.2, 11.5, "abete"),
        (  9.2,   5.2, 12.8, "abete"),
        (-16.0, -12.0, 13.5, "abete"),
        ( 15.0, -10.0, 12.0, "abete"),
        (-18.0,   8.0, 14.0, "abete"),
        ( 16.0,  12.0, 15.0, "abete"),
    ]

    for tx, ty, th, ttype in tree_specs:
        build_singolo_abete(B, tx, ty, th, ttype)


def build_singolo_abete(B, x, y, h, ttype="abete"):
    b_corteccia = B["corteccia_pino"]
    b_aghi = B["aghi_pino"]

    z_base = terrain_z(x, y)
    r_trunk_bot = h * 0.038
    r_trunk_top = h * 0.008

    p_bot = Vector((x, y, z_base - 0.40))
    p_top = Vector((x, y, z_base + h))
    add_cone(b_corteccia, p_bot, p_top, r_trunk_bot, r_trunk_top, sides=10)

    z_branch_start = z_base + h * 0.18
    n_tiers = int(h * 2.6)

    for i in range(n_tiers):
        frac = i / n_tiers
        bz = z_branch_start + frac * (h * 0.78)
        tier_rad = (1.0 - frac) * (h * 0.28)
        n_branches = int(5 + (1.0 - frac) * 3)

        for b in range(n_branches):
            ang = TAU * (b / n_branches + frac * 2.3) + rr(-0.12, 0.12)
            br_len = tier_rad * rr(0.88, 1.12)
            droop = br_len * (0.22 if ttype == "abete" else 0.10)

            p_start = Vector((x + math.cos(ang) * (r_trunk_bot * (1.0 - frac)),
                              y + math.sin(ang) * (r_trunk_bot * (1.0 - frac)), bz))
            p_end = Vector((x + math.cos(ang) * br_len, y + math.sin(ang) * br_len, bz - droop))

            add_cylinder(b_corteccia, p_start, p_end, 0.030 * (1.0 - frac * 0.6), sides=5)

            b_aghi.color = jitter_color((1.0, 1.0, 1.0), 0.12)
            n_tufts = int(br_len * 4.5)
            for t in range(n_tufts):
                tf = (t + 1) / (n_tufts + 1)
                tuft_p = p_start + (p_end - p_start) * tf
                tuft_rad = 0.16 * (1.0 - frac * 0.45)
                add_sphere(b_aghi, tuft_p, tuft_rad, segs=6, rings=4,
                           scale=(1.2, 1.2, 0.38), amp=0.10)


def build_rododendri_arbusti(B):
    b_fiori = B["rododendro_fiori"]
    b_foglie = B["foglie_arbusto"]

    shrub_pos = [
        (-5.2, -6.8, 0.85),
        (-6.2, -7.5, 0.75),
        ( 5.5, -5.8, 0.90),
        ( 6.5, -4.8, 0.80),
        (-7.5,  2.2, 1.10),
        ( 7.2,  1.8, 1.05),
    ]

    for sx, sy, sr in shrub_pos:
        sz = terrain_z(sx, sy) + sr * 0.5
        add_sphere(b_foglie, (sx, sy, sz), sr, segs=10, rings=6, amp=0.25,
                   scale=(1.3, 1.3, 0.85))
        for _ in range(16):
            ang = rr(0, TAU)
            dist = rr(sr * 0.4, sr * 0.95)
            fp = Vector((sx + math.cos(ang) * dist, sy + math.sin(ang) * dist, sz + rr(0.0, sr * 0.4)))
            add_sphere(b_fiori, fp, rr(0.045, 0.075), segs=6, rings=4)


def build_erba_fitta(B):
    b_erba = B["erba"]

    n_tufts = 14000
    for _ in range(n_tufts):
        ang = rr(0, TAU)
        dist = (random.random() ** 0.6) * 28.0
        gx = math.cos(ang) * dist
        gy = math.sin(ang) * dist

        if abs(gx) < HALF_X + 0.3 and abs(gy) < HALF_Y + 0.3:
            continue
        if abs(gx) < 1.0 and -HALF_Y - 2.5 <= gy <= -HALF_Y:
            continue

        gz = terrain_z(gx, gy)
        b_erba.color = jitter_color((1.0, 1.0, 1.0), 0.20)

        tuft_h = rr(0.12, 0.26)
        n_blades = random.randint(4, 6)
        for b in range(n_blades):
            b_ang = rr(0, TAU)
            b_len = tuft_h * rr(0.8, 1.2)
            bend = rr(0.04, 0.12)
            p0 = Vector((gx, gy, gz))
            p1 = Vector((gx + math.cos(b_ang) * bend * 0.5, gy + math.sin(b_ang) * bend * 0.5, gz + b_len * 0.6))
            p2 = Vector((gx + math.cos(b_ang) * bend, gy + math.sin(b_ang) * bend, gz + b_len))
            b_erba.poly([p0, p1 + Vector((0.01, 0.01, 0)), p2])


def build_catena_alpina_sfondo(B):
    b_mont = B["montagne"]

    n_peaks = 24
    r_mount = 125.0

    for i in range(n_peaks):
        ang = math.radians(rr(-30.0, 190.0))
        dist = r_mount + rr(-15.0, 25.0)
        mx = math.cos(ang) * dist
        my = math.sin(ang) * dist
        peak_h = rr(38.0, 68.0)
        peak_w = rr(28.0, 48.0)

        p_base = Vector((mx, my, terrain_z(mx, my) - 5.0))
        p_top = Vector((mx + rr(-6.0, 6.0), my + rr(-6.0, 6.0), peak_h))
        add_cone(b_mont, p_base, p_top, peak_w, 0.5, sides=7)


# ---------------------------------------------------------------------------
# 8. SETUP DELLA SCENA, LUCI, CAMERA E RENDERING CYCLES
# ---------------------------------------------------------------------------
def setup_scena(root):
    scene = bpy.context.scene

    world = bpy.data.worlds.new("Cielo_Alpino")
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    out.location = (600, 0)

    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.location = (-650, 0)
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(24.0)
    sky.sun_rotation = math.radians(328.0)
    sky.altitude = 1650.0
    sky.air_density = 0.80
    sky.dust_density = 0.30
    sky.ozone_density = 1.85

    bg_cam = nt.nodes.new("ShaderNodeBackground")
    bg_cam.location = (-280, 120)
    bg_cam.inputs["Strength"].default_value = 1.10
    nt.links.new(sky.outputs["Color"], bg_cam.inputs["Color"])

    bg_light = nt.nodes.new("ShaderNodeBackground")
    bg_light.location = (-280, -120)
    bg_light.inputs["Strength"].default_value = 0.48
    nt.links.new(sky.outputs["Color"], bg_light.inputs["Color"])

    light_path = nt.nodes.new("ShaderNodeLightPath")
    light_path.location = (-280, 320)

    mix_world = nt.nodes.new("ShaderNodeMixShader")
    mix_world.location = (150, 0)
    nt.links.new(light_path.outputs["Is Camera Ray"], mix_world.inputs["Fac"])
    nt.links.new(bg_light.outputs["Background"], mix_world.inputs[1])
    nt.links.new(bg_cam.outputs["Background"], mix_world.inputs[2])
    nt.links.new(mix_world.outputs["Shader"], out.inputs["Surface"])
    scene.world = world

    el, az = math.radians(24.0), math.radians(328.0)
    sdir = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    sun_data = bpy.data.lights.new("Sole_Alpino", "SUN")
    sun_data.energy = 10.5
    sun_data.angle = math.radians(0.85)
    sun_data.color = (1.0, 0.94, 0.82)
    sun_obj = bpy.data.objects.new("Sole_Alpino", sun_data)
    sun_obj.location = sdir * 50.0
    sun_obj.rotation_euler = (-sdir).to_track_quat("-Z", "Y").to_euler()
    root.objects.link(sun_obj)

    point_lights = [
        ("Luce_Stube", Vector((-2.60, -1.60, Z_PLINTH + 0.45)), (1.0, 0.55, 0.15), 220.0, 0.15),
        ("Luce_Soggiorno", Vector((2.40, -1.80, Z_F1 - 0.70)), (1.0, 0.82, 0.55), 140.0, 0.25),
        ("Luce_Camera_P1", Vector((-2.20, -1.60, Z_F1 + 1.20)), (1.0, 0.85, 0.60), 90.0, 0.20),
        ("Luce_Attic_W", Vector((-3.80, 0.0, Z_EAVE_WALL + 0.90)), (1.0, 0.80, 0.50), 75.0, 0.20),
        ("Luce_Lanterna_Ingresso", Vector((-0.55, -HALF_Y - 0.15, Z_PLINTH + 1.95)), (1.0, 0.72, 0.35), 55.0, 0.08),
        ("Luce_Lanterna_Portico", Vector((PORCH_X0 + 0.15, PORCH_Y_FRONT + 0.15, PORCH_Z_ROOF - 0.45)), (1.0, 0.72, 0.35), 55.0, 0.08),
        ("Luce_Lanterna_Balcone", Vector((BALCONY_SIDE_X + 0.08, BALCONY_FRONT_Y + 0.08, BALCONY_Z + 1.25)), (1.0, 0.72, 0.35), 45.0, 0.08),
    ]
    for name, pos, col, energy, radius in point_lights:
        pdata = bpy.data.lights.new(name, "POINT")
        pdata.energy = energy
        pdata.color = col
        pdata.shadow_soft_size = radius
        pobj = bpy.data.objects.new(name, pdata)
        pobj.location = pos
        root.objects.link(pobj)

    cam_data = bpy.data.cameras.new("Camera_Chalet")
    cam_data.lens = 42.0
    cam_data.clip_end = 450.0
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = 18.5
    cam_data.dof.aperture_fstop = 11.0

    cam_obj = bpy.data.objects.new("Camera", cam_data)
    cam_pos = Vector((-12.8, -16.8, 5.10))
    cam_target = Vector((0.2, -0.6, 3.40))
    cam_obj.location = cam_pos
    cam_obj.rotation_euler = (cam_target - cam_pos).to_track_quat("-Z", "Y").to_euler()
    root.objects.link(cam_obj)
    scene.camera = cam_obj

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
    opts = {"render": False, "samples": None, "res": None, "quick": False, "cam": None}
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

    root = bpy.data.collections.new("Chalet_3")
    bpy.context.scene.collection.children.link(root)
    subs = {}
    for nome in ("Edificio", "Serramenti", "Tetto", "Interni", "Esterni", "Giardino"):
        c = bpy.data.collections.new(nome)
        root.children.link(c)
        subs[nome] = c

    mats = make_materials()
    B = make_buffers(mats)

    print("» basamento in pietra, muratura e struttura Blockbau ...")
    build_struttura(B)

    print("» balconata panoramica avvolgente, intagli e gerani ...")
    build_balcone(B)

    print("» portico d'ingresso, legnaia con ciocchi, panca, sci e lanterne ...")
    build_portico_e_accessori(B)

    print("» serramenti con vetri doppi, scuri alpini, portoni e tendine ...")
    build_serramenti(B)

    print("» carpenteria tetto, orditura, scandole, fermaneve e comignolo ...")
    build_tetto_e_copertura(B)

    print("» interni: Stube tirolese con fuoco, tavolo, sedie e camera ...")
    build_interni(B)

    print("» paesaggio alpino: terreno, fontana a tronco, rocce, flora, abeti e montagne ...")
    build_giardino_e_paesaggio(B)

    nv = sum(len(b.V) for b in B.values())
    nf = sum(len(b.F) for b in B.values())
    print("   geometria totale: %d vertici, %d facce" % (nv, nf))

    print("» generazione oggetti Blender nelle collezioni ...")
    for key, name, coll, usec in BUF_SPEC:
        buf_to_object(B[key], subs[coll])

    setup_scena(root)

    if opts["quick"]:
        bpy.context.scene.cycles.samples = 20
        bpy.context.scene.render.resolution_x = 840
        bpy.context.scene.render.resolution_y = 588
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
    print("   salvato in %.1f s (%.1f MB)" % (time.time() - t0, os.path.getsize(OUT_BLEND) / 1e6))

    if opts["render"]:
        print("» render anteprima Cycles (%d campioni, %dx%d) ..." % (
            bpy.context.scene.cycles.samples,
            bpy.context.scene.render.resolution_x,
            bpy.context.scene.render.resolution_y
        ))
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        print("   render completato in %.1f s -> %s" % (time.time() - t1, OUT_PNG))


if __name__ == "__main__":
    main()
