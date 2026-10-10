"""
Genera un albero 3D molto dettagliato e salva il file Blender `albero.blend`.

Versione 2 (migliorata):
  - tronco con base allargata (contrafforti), corteccia a solchi (bump Voronoi + rumore)
    e colore procedurale; radici superficiali che emergono dal terreno
  - struttura ramificata ricorsiva: 7 branche principali, fino a 6 livelli di ramificazione,
    rami che si assottigliano (modello "pipe" semplificato), tendono verso l'alto e
    restano dentro una "busta" ellissoidale che da' alla chioma una forma naturale e densa
  - decine di migliaia di foglie con forma a V, nervatura centrale, arricciatura,
    piccola variazione di colore per foglia e per vertice (attributo di colore);
    le foglie sono concentrate sui rametti terminali
  - foglie secche sparse sul terreno
  - terreno con rilievo, transizione terra -> erba e materiale procedurale
  - camera di presentazione, cielo procedurale (Nishita) e luce solare

Esecuzione (con il modulo bpy di Blender 5.x):
    python genera_albero.py
"""

import bpy
import bmesh
import colorsys
import math
import os
import random

from mathutils import Vector, Matrix, noise

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_BLEND = os.path.join(HERE, "albero.blend")

SEED = 2026
random.seed(SEED)

# ----------------------------------------------------------------------------
# Parametri (unita: metri)
# ----------------------------------------------------------------------------
TRUNK_H = 3.6
TRUNK_R0 = 0.30
TRUNK_R1 = 0.17
TRUNK_SEG = 30
LIMBS = 7
MAX_DEPTH = 6
SIDES = {0: 32, 1: 18, 2: 12, 3: 9, 4: 7, 5: 6, 6: 5}
SPAWN = {1: 0.75, 2: 0.55, 3: 0.42, 4: 0.36, 5: 0.30}
MAX_BRANCHES = 16000   # limite di sicurezza (memoria)
BRANCH_BUDGET_PER_LIMB = 1800  # ogni branca maestra ha un proprio budget di rami
MAX_LEAVES = 150000    # limite di sicurezza (memoria/dimensione file): campionamento uniforme
_branch_count = 0
_branch_end = 0       # limite di rami per la branca maestra corrente
SEGMENTS = []          # (p0, p1, direzione, profondita) di tutti i rami

# Busta della chioma (ellissoide): i rami non escono troppo da questa forma
CROWN_C = Vector((0.0, 0.0, 4.5))
CROWN_R = Vector((2.9, 2.9, 2.5))

LEAF_MIN_DEPTH = 3
LEAVES_PER_SEG = {3: 2, 4: 5, 5: 8, 6: 11}
LEAF_LEN = 0.11
LEAF_WID = 0.05
LEAF_ROWS = 3
GROUND_LEAVES = 420
GROUND_R = 4.5


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


def inside_crown(p, margin=1.0):
    q = Vector(((p.x - CROWN_C.x) / (CROWN_R.x * margin),
                (p.y - CROWN_C.y) / (CROWN_R.y * margin),
                (p.z - CROWN_C.z) / (CROWN_R.z * margin)))
    return q.length <= 1.0


# Buffer geometrici (liste grezze, poi convertite in mesh una volta sola)
wood_V, wood_F = [], []
leaf_V, leaf_F, leaf_C = [], [], []


# ----------------------------------------------------------------------------
# Geometria: tubi (rami/tronco/radici)
# ----------------------------------------------------------------------------
def add_tube(V, F, pts, radii, sides, bark=0.0, bark_scale=1.0):
    n = len(pts)
    tans = []
    for i in range(n):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        tans.append(t.normalized())

    # Frame a minima rotazione (evita torsioni)
    ref = Vector((1, 0, 0)) if abs(tans[0].x) < 0.9 else Vector((0, 1, 0))
    u = (ref - tans[0] * ref.dot(tans[0])).normalized()
    frames = []
    for i in range(n):
        t = tans[i]
        u = u - t * u.dot(t)
        u.normalize()
        v = t.cross(u).normalized()
        frames.append((u, v))

    rings = []
    for i in range(n):
        u, v = frames[i]
        p = pts[i]
        r = radii[i]
        start = len(V)
        for j in range(sides):
            a = 2.0 * math.pi * j / sides
            d = u * math.cos(a) + v * math.sin(a)
            rad = r
            if bark > 0.0:
                q = d * (2.2 * bark_scale) + Vector((p.x, p.y, p.z * 2.5)) * 1.7
                rad = r * (1.0 + bark * noise.noise(q))
            V.append(p + d * rad)
        rings.append(start)

    for i in range(n - 1):
        a0 = rings[i]
        a1 = rings[i + 1]
        for j in range(sides):
            jn = (j + 1) % sides
            F.append((a0 + j, a0 + jn, a1 + jn, a1 + j))

    # Tappo finale
    c = len(V)
    V.append(pts[-1].copy())
    last = rings[-1]
    for j in range(sides):
        F.append((last + j, last + (j + 1) % sides, c))


# ----------------------------------------------------------------------------
# Geometria: foglie
# ----------------------------------------------------------------------------
def leaf_color(autumn=False):
    if autumn:
        h = rr(0.07, 0.13)
        s = rr(0.55, 0.85)
        v = rr(0.35, 0.6)
    else:
        # Varieta' tra verde chiaro (giovani) e verde scuro (mature)
        h = rr(0.19, 0.30)
        s = rr(0.40, 0.85)
        v = rr(0.20, 0.55)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), 1.0)


def add_leaf(p, ldir, flat=False, autumn=False):
    """Foglia a V con nervatura, arricciatura e colore per vertice."""
    L = LEAF_LEN * rr(0.8, 1.25)
    W = LEAF_WID * rr(0.8, 1.2)
    curl = rr(-0.35, 0.35)
    if flat:
        nrm = Vector((0, 0, 1))
        ldir = Vector((ldir.x, ldir.y, 0)).normalized()
        side = nrm.cross(ldir).normalized()
    else:
        ldir = ldir.normalized()
        side = ldir.cross(rand_unit()).normalized()
        nrm = side.cross(ldir).normalized()
    col = leaf_color(autumn)
    base = len(leaf_V)
    for i in range(LEAF_ROWS + 1):
        t = i / LEAF_ROWS
        w = W * math.sin(math.pi * (t ** 0.75))
        center = p + ldir * (L * t) + nrm * (curl * L * t * t)
        fold = nrm * (0.18 * w)
        leaf_V.append(center + side * w + fold)
        leaf_V.append(center)
        leaf_V.append(center - side * w + fold)
        # la punta della foglia e' un po' piu' chiara/gialla: sfumatura lungo la lamina
        shade = 1.0 - 0.18 * t
        c = (col[0] * shade, col[1] * shade, col[2] * shade, 1.0)
        leaf_C.extend([c, c, c])
    for i in range(LEAF_ROWS):
        a = base + 3 * i
        b = a + 3
        leaf_F.append((a, a + 1, b + 1, b))
        leaf_F.append((a + 1, a + 2, b + 2, b + 1))


def place_leaves_on_segment(p0, p1, seg_dir, count):
    for _ in range(count):
        t = random.random()
        p = p0.lerp(p1, t) + rand_unit() * 0.05
        ldir = seg_dir * 0.45 + rand_unit() * 0.9 + Vector((0, 0, 0.25))
        add_leaf(p, ldir, autumn=(random.random() < 0.03))


def place_all_leaves():
    """Distribuisce le foglie su tutti i segmenti, senza favorire i rami generati prima.

    Se il numero totale supera MAX_LEAVES, ogni foglia viene mantenuta con
    probabilita' uniforme, cosi' la chioma resta densa e omogenea ovunque.
    """
    plan = []
    for p0, p1, sd, depth in SEGMENTS:
        if depth >= LEAF_MIN_DEPTH and depth in LEAVES_PER_SEG:
            cnt = max(0, LEAVES_PER_SEG[depth] + random.randint(-1, 2))
            plan.append((p0, p1, sd, cnt))
    total = sum(c for *_, c in plan)
    keep = min(1.0, MAX_LEAVES / max(1, total))
    print("  foglie richieste: %d (fattore di campionamento %.2f)" % (total, keep))
    for p0, p1, sd, cnt in plan:
        # arrotonda in modo stocastico per mantenere il valore atteso
        m = cnt * keep
        m = int(m) + (1 if random.random() < (m - int(m)) else 0)
        place_leaves_on_segment(p0, p1, sd, m)


# ----------------------------------------------------------------------------
# Ramificazione ricorsiva
# ----------------------------------------------------------------------------
def grow(start, direction, length, r0, depth):
    global _branch_count
    _branch_count += 1
    sides = SIDES[depth]
    n = max(3, min(14, int(length / 0.25) + 3))
    step = length / n
    pts = [start.copy()]
    d = direction.normalized()
    for _ in range(n):
        jit = rand_unit() * 0.10
        d = (d + jit + Vector((0, 0, -0.03))).normalized()
        pts.append(pts[-1] + d * step)

    rtip = max(0.002, r0 * 0.12)
    radii = [r0 + (rtip - r0) * (i / n) ** 0.85 for i in range(n + 1)]
    add_tube(wood_V, wood_F, pts, radii, sides)

    # Le foglie vengono piazzate dopo, su tutti i segmenti (vedi place_all_leaves)
    for k in range(1, n + 1):
        seg_dir = (pts[k] - pts[k - 1]).normalized()
        SEGMENTS.append((pts[k - 1], pts[k], seg_dir, depth))

    if depth < MAX_DEPTH and _branch_count < min(MAX_BRANCHES, _branch_end):
        for k in range(1, n):
            if random.random() > SPAWN.get(depth, 0.5):
                continue
            seg_dir = (pts[k + 1] - pts[k - 1]).normalized()
            roll = random.random()
            n_children = 3 if (roll < 0.15 and depth <= 2) else (2 if roll < 0.55 else 1)
            for _ in range(n_children):
                ang = math.radians(rr(25, 52))
                axis = perp(seg_dir)
                cd = Matrix.Rotation(ang, 3, axis) @ seg_dir
                cd = (cd + Vector((0, 0, 0.45))).normalized()  # fototropismo
                clen = length * rr(0.45, 0.68)
                # Se il ramo esce troppo dalla chioma, quasi sempre lo scartiamo
                if depth >= 2:
                    est = pts[k] + cd * clen * 0.6
                    if not inside_crown(est, 1.05) and random.random() < 0.95:
                        continue
                cr0 = radii[k] * rr(0.55, 0.75)
                grow(pts[k], cd, clen, cr0, depth + 1)


# ----------------------------------------------------------------------------
# Costruzione albero
# ----------------------------------------------------------------------------
def build_tree():
    # Tronco: linea leggermente curva
    phase1, phase2 = rr(0, 6.28), rr(0, 6.28)
    trunk_pts, trunk_r = [], []
    for i in range(TRUNK_SEG + 1):
        f = i / TRUNK_SEG
        z = f * TRUNK_H
        x = math.sin(f * 2.2 + phase1) * 0.12 * f
        y = math.cos(f * 1.6 + phase2) * 0.10 * f
        trunk_pts.append(Vector((x, y, z)))
        r = TRUNK_R0 * (1 - f) + TRUNK_R1 * f
        # contrafforti alla base (flare non uniforme)
        flare = 1.0 + 0.85 * max(0.0, 1.0 - z / 0.7) ** 2
        flare *= 1.0 + 0.12 * math.sin(phase1 + 5.0 * math.atan2(y, x)) * max(0.0, 1.0 - z / 0.9)
        trunk_r.append(r * flare)
    add_tube(wood_V, wood_F, trunk_pts, trunk_r, SIDES[0], bark=0.05, bark_scale=1.6)

    # Radici superficiali
    for i in range(9):
        az = 2 * math.pi * i / 9 + rr(-0.25, 0.25)
        dist = rr(1.0, 1.8)
        dirv = Vector((math.cos(az), math.sin(az), 0))
        pts, rad = [], []
        for k in range(11):
            t = k / 10
            horiz = 0.04 + dist * t
            z = 0.12 - 0.12 * t * 1.5 + 0.06 * math.sin(math.pi * t)
            pts.append(dirv * horiz + Vector((0, 0, z)))
            rad.append(max(0.010, 0.14 * (1 - t) ** 1.2 + 0.010))
        add_tube(wood_V, wood_F, pts, rad, 8, bark=0.25, bark_scale=2.0)

    # Branche principali: distribuite lungo il fusto, in alto la chioma e' piu' fitta
    global _branch_end
    base_az = rr(0, 2 * math.pi)
    for i in range(LIMBS):
        _branch_end = _branch_count + BRANCH_BUDGET_PER_LIMB
        f = rr(0.58, 0.95)
        idx = int(f * TRUNK_SEG)
        p = trunk_pts[idx].copy()
        az = base_az + 2 * math.pi * i / LIMBS + rr(-0.30, 0.30)
        theta = rr(0.35, 0.90)  # angolo dalla verticale
        dirv = Vector((math.sin(theta) * math.cos(az),
                       math.sin(theta) * math.sin(az),
                       math.cos(theta)))
        grow(p, dirv, rr(2.6, 3.6), trunk_r[idx] * 0.70, 1)


# ----------------------------------------------------------------------------
# Terreno e foglie secche
# ----------------------------------------------------------------------------
def build_ground(R=GROUND_R, rings=22, segs=140):
    V = [Vector((0, 0, 0))]
    F = []
    for i in range(1, rings + 1):
        r = R * (i / rings) ** 1.15
        for j in range(segs):
            a = 2 * math.pi * j / segs
            x, y = r * math.cos(a), r * math.sin(a)
            # zona vicino al tronco piu' piatta, poi rilievo dolce
            fade = min(1.0, max(0.0, (r - 0.8) / 1.4))
            z = (0.05 * noise.noise(Vector((x * 0.6, y * 0.6, 0.3)))
                 + 0.015 * noise.noise(Vector((x * 2.5, y * 2.5, 1.7)))) * fade
            V.append(Vector((x, y, z)))
    for j in range(segs):
        F.append((0, 1 + (j + 1) % segs, 1 + j))
    for i in range(1, rings):
        a0 = 1 + (i - 1) * segs
        a1 = 1 + i * segs
        for j in range(segs):
            jn = (j + 1) % segs
            F.append((a0 + j, a0 + jn, a1 + jn, a1 + j))
    return V, F


def scatter_ground_leaves():
    for _ in range(GROUND_LEAVES):
        r = math.sqrt(random.random()) * GROUND_R * 0.9
        if r < 0.5:
            r = rr(0.5, 1.0)
        a = rr(0, 2 * math.pi)
        p = Vector((r * math.cos(a), r * math.sin(a), 0.008))
        add_leaf(p, Vector((rr(-1, 1), rr(-1, 1), 0)), flat=True,
                 autumn=(random.random() < 0.45))


# ----------------------------------------------------------------------------
# Materiali
# ----------------------------------------------------------------------------
def mat_bark():
    mat = bpy.data.materials.new("Corteccia")
    mat.use_nodes = True
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    n1 = N.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 3.0
    n1.inputs["Detail"].default_value = 12.0
    n1.inputs["Roughness"].default_value = 0.65
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.04, 0.024, 0.012, 1)
    ramp.color_ramp.elements[1].color = (0.25, 0.165, 0.095, 1)
    mid = ramp.color_ramp.elements.new(0.5)
    mid.color = (0.11, 0.065, 0.032, 1)
    # Rilievo: rugosita' fine + solchi (celle Voronoi allungate)
    n2 = N.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 22.0
    n2.inputs["Detail"].default_value = 8.0
    vor = N.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 4.5
    add = N.new("ShaderNodeMath")
    add.operation = "ADD"
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.1
    bump.inputs["Distance"].default_value = 0.02
    L.new(tc.outputs["Object"], n1.inputs["Vector"])
    L.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    L.new(tc.outputs["Object"], n2.inputs["Vector"])
    L.new(tc.outputs["Object"], vor.inputs["Vector"])
    L.new(n2.outputs["Fac"], add.inputs[0])
    L.new(vor.outputs["Distance"], add.inputs[1])
    L.new(add.outputs["Value"], bump.inputs["Height"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.85
    return mat


def mat_leaves():
    mat = bpy.data.materials.new("Foglie")
    mat.use_nodes = True
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    attr = N.new("ShaderNodeAttribute")
    attr.attribute_type = "GEOMETRY"
    attr.attribute_name = "LeafColor"
    L.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.45
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.2
    if "Subsurface Radius" in bsdf.inputs:
        bsdf.inputs["Subsurface Radius"].default_value = (0.4, 0.7, 0.2)
    mat.use_backface_culling = False
    return mat


def mat_ground():
    mat = bpy.data.materials.new("Terreno")
    mat.use_nodes = True
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    # Terra (rumore + ramp)
    n1 = N.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 6.0
    n1.inputs["Detail"].default_value = 10.0
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.035, 0.022, 0.012, 1)
    ramp.color_ramp.elements[1].color = (0.13, 0.095, 0.05, 1)
    L.new(tc.outputs["Object"], n1.inputs["Vector"])
    L.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    # Erba secca che sfuma verso i bordi (distanza dal tronco)
    vlen = N.new("ShaderNodeVectorMath")
    vlen.operation = "LENGTH"
    L.new(tc.outputs["Object"], vlen.inputs[0])
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 3.0
    mr.inputs["From Max"].default_value = 6.0
    L.new(vlen.outputs["Value"], mr.inputs["Value"])
    grass = N.new("ShaderNodeTexNoise")
    grass.inputs["Scale"].default_value = 18.0
    grass.inputs["Detail"].default_value = 6.0
    L.new(tc.outputs["Object"], grass.inputs["Vector"])
    mix = N.new("ShaderNodeMixRGB")
    mix.inputs["Color2"].default_value = (0.06, 0.07, 0.02, 1)
    L.new(ramp.outputs["Color"], mix.inputs["Color1"])
    L.new(mr.outputs["Result"], mix.inputs["Fac"])
    L.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    return mat


# ----------------------------------------------------------------------------
# Creazione oggetti Blender
# ----------------------------------------------------------------------------
def to_mesh(name, V, F):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in V], [], F)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    return me


def smooth(me):
    for p in me.polygons:
        p.use_smooth = True


def setup_lighting_and_camera(coll):
    # Camera: inquadratura piu' ampia dell'albero, leggermente dall'alto
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 50
    cam_data.dof.use_dof = False
    cam = bpy.data.objects.new("Camera", cam_data)
    coll.objects.link(cam)
    cam.location = Vector((14.5, -17.5, 6.8))
    target = Vector((0.0, 0.0, 4.4))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam

    # Sole (luce diretta con ombre morbide)
    sun_data = bpy.data.lights.new("Sole", "SUN")
    sun_data.energy = 3.2
    sun_data.angle = math.radians(1.2)
    sun = bpy.data.objects.new("Sole", sun_data)
    coll.objects.link(sun)
    sun.rotation_euler = (math.radians(42), 0, math.radians(35))

    # Cielo procedurale (luce ambientale naturale e sfondo)
    world = bpy.data.worlds.new("Mondo")
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_elevation = math.radians(42)
    sky.sun_rotation = math.radians(35)
    sky.sun_disc = False
    # luce del cielo moderata: evita di sbiadire i colori del tronco e del terreno
    bg.inputs["Strength"].default_value = 0.45
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    # Sfondo visibile di fondo piatto (come nella versione precedente); il cielo
    # procedurale resta solo per l'illuminazione indiretta
    flat = nt.nodes.new("ShaderNodeBackground")
    flat.inputs["Color"].default_value = (0.55, 0.70, 0.90, 1.0)
    flat.inputs["Strength"].default_value = 1.0
    lp = nt.nodes.new("ShaderNodeLightPath")
    mixs = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes["World Output"]
    nt.links.new(bg.outputs["Background"], mixs.inputs[1])
    nt.links.new(flat.outputs["Background"], mixs.inputs[2])
    nt.links.new(lp.outputs["Is Camera Ray"], mixs.inputs["Fac"])
    nt.links.new(mixs.outputs["Shader"], out.inputs["Surface"])
    bpy.context.scene.world = world


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)

    coll = bpy.data.collections.new("Albero_1")
    bpy.context.scene.collection.children.link(coll)

    print("Costruzione albero...")
    build_tree()
    print("  rami/tronco: %d vertici, %d facce, branche=%d"
          % (len(wood_V), len(wood_F), _branch_count))
    place_all_leaves()
    print("  foglie albero: %d" % (len(leaf_F) // 8))
    scatter_ground_leaves()
    print("  foglie totali (albero + terreno): %d" % (len(leaf_F) // 8))

    # Oggetti
    wood_me = to_mesh("Tronco_e_Rami", wood_V, wood_F)
    smooth(wood_me)
    leaf_me = to_mesh("Foglie", leaf_V, leaf_F)
    att = leaf_me.color_attributes.new("LeafColor", "BYTE_COLOR", "POINT")
    flat = []
    for c in leaf_C:
        flat.extend(c)
    att.data.foreach_set("color", flat)

    ground_V, ground_F = build_ground()
    ground_me = to_mesh("Terreno", ground_V, ground_F)
    smooth(ground_me)

    mats = {"wood": mat_bark(), "leaf": mat_leaves(), "ground": mat_ground()}

    for name, me, mat_key in (("Tronco_e_Rami", wood_me, "wood"),
                              ("Foglie", leaf_me, "leaf"),
                              ("Terreno", ground_me, "ground")):
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        ob.data.materials.append(mats[mat_key])

    setup_lighting_and_camera(coll)

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 960
    scene.view_settings.view_transform = "AgX"
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    print("Salvataggio:", OUT_BLEND)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("Fatto.")


if __name__ == "__main__":
    main()
