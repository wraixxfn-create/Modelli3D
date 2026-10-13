"""Genera il Borgo delle Querce, una piccola città italiana in Blender.

Il nucleo residenziale riutilizza i modelli Blender di casa_1, casa_2 e casa_3;
il viale alberato include anche il ciliegio procedurale di albero_2. La scena
aggiunge piazza, municipio, palazzi, negozi, viabilità, verde e arredo urbano,
e nella seconda versione anche pieve romanica con campanile, mercato
settimanale in piazza, rotatorie fiorite, laghetto con anatre, parco giochi,
pedoni e ciclisti, panni stesi, giardini privati e una campagna collinare
con colture, cipressi e un borgo lontano sul colle.

Richiede Blender 5.0+ e i modelli originali presenti nelle cartelle sorelle.

    python3 genera_citta.py                 # salva citta.blend
    python3 genera_citta.py --quick          # salva e renderizza anteprima rapida
    python3 genera_citta.py --render         # render finale Cycles
"""

import math
import os
import random
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT_BLEND = os.path.join(HERE, "citta.blend")
OUT_PNG = os.path.join(HERE, "anteprima.png")
SEED = 20261012
random.seed(SEED)
PI = math.pi
TAU = 2.0 * PI
# Sole basso da sud-ovest: ombre lunghe e luce dorata sulle facciate.
SUN_ELEVATION = 19.0
SUN_ROTATION = 140.0
# Materiali usati dai batch della "vita di strada" e dei nuovi landmark.
LIFE_KEYS = ("asphalt", "curb", "grass", "grass_light", "leaf", "leaf_light",
             "bark", "flower", "road_white", "water", "wood", "wood_light",
             "metal", "metal_gold", "lamp", "trim", "concrete", "terracotta",
             "cream", "brick", "white", "glass", "cypress", "sand", "rubber",
             "plastic", "duck", "beak", "bird", "skin", "hair_dark",
             "hair_light", "cloth_red", "cloth_blue", "cloth_green",
             "cloth_yellow", "cloth_violet", "cloth_white", "canvas_green",
             "canvas_blue", "canvas_red", "canvas_yellow", "produce_red",
             "produce_green", "produce_orange", "produce_yellow", "roof_dark")
COUNTRY_KEYS = ("ground", "ground_far", "wheat", "grass", "grass_light", "olive", "bark",
                "cypress", "cream", "ochre", "terracotta", "brick")


# ---------------------------------------------------------------------------
# Materiali e geometria riutilizzabile
# ---------------------------------------------------------------------------
def srgb(rgb):
    return tuple((v / 255.0) ** 2.2 for v in rgb)


def make_material(name, color, roughness=0.75, metallic=0.0, *,
                  noise_scale=0.0, bump_strength=0.0, emission=None,
                  transmission=0.0, wave_bump=0.0, brick=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*srgb(color), 1.0)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*srgb(color), 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if transmission:
        bsdf.inputs["Transmission Weight"].default_value = transmission
        bsdf.inputs["IOR"].default_value = 1.33 if transmission > 0.5 else 1.45
    if wave_bump:
        # Filari di coppi: onde regolari usate come bump sulla falda.
        wave = nodes.new("ShaderNodeTexWave")
        wave.inputs["Scale"].default_value = wave_bump
        wave.inputs["Distortion"].default_value = 1.6
        wave.inputs["Detail"].default_value = 2.0
        coord = nodes.new("ShaderNodeTexCoord")
        links.new(coord.outputs["Object"], wave.inputs["Vector"])
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.42
        bump.inputs["Distance"].default_value = 0.05
        links.new(wave.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    if brick:
        # Pavimentazione in pietra: mattoncini procedurali con fughe scure.
        tex = nodes.new("ShaderNodeTexBrick")
        tex.inputs["Scale"].default_value = brick
        tex.inputs["Color1"].default_value = (*srgb(color), 1.0)
        tex.inputs["Color2"].default_value = (
            *srgb(tuple(max(0, int(c * 0.82)) for c in color)), 1.0)
        tex.inputs["Mortar"].default_value = (*srgb((96, 92, 86)), 1.0)
        tex.inputs["Mortar Size"].default_value = 0.012
        tex.offset = 0.5
        coord = nodes.new("ShaderNodeTexCoord")
        links.new(coord.outputs["Object"], tex.inputs["Vector"])
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.25
        bump.inputs["Distance"].default_value = 0.02
        links.new(tex.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    if emission:
        ecolor, strength = emission
        bsdf.inputs["Emission Color"].default_value = (*srgb(ecolor), 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
    if noise_scale:
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = noise_scale
        tex.inputs["Detail"].default_value = 3.0
        tex.inputs["Roughness"].default_value = 0.72
        coord = nodes.new("ShaderNodeTexCoord")
        links.new(coord.outputs["Generated"], tex.inputs["Vector"])
        if bump_strength:
            bump = nodes.new("ShaderNodeBump")
            bump.inputs["Strength"].default_value = bump_strength
            bump.inputs["Distance"].default_value = 0.035
            links.new(tex.outputs["Fac"], bump.inputs["Height"])
            links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        if name in ("Asfalto", "Intonaco caldo", "Calce avorio",
                    "Ocra chiara", "Rosa antico", "Verde salvia"):
            ramp = nodes.new("ShaderNodeValToRGB")
            c0 = (*srgb(color), 1.0)
            c1 = (*srgb(tuple(min(255, int(c * 1.12)) for c in color)), 1.0)
            ramp.color_ramp.elements[0].position = 0.16
            ramp.color_ramp.elements[0].color = c0
            ramp.color_ramp.elements[1].position = 0.84
            ramp.color_ramp.elements[1].color = c1
            links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
            links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


class Batch:
    """Accumula scatole e superfici in una mesh per materiale."""
    FACES = ((0, 2, 6, 4), (1, 5, 7, 3), (0, 4, 5, 1),
             (2, 3, 7, 6), (0, 1, 3, 2), (4, 6, 7, 5))

    def __init__(self, name, material, collection):
        self.name = name
        self.material = material
        self.collection = collection
        self.verts = []
        self.faces = []
        self.smooth = []

    def poly(self, points, smooth=False):
        start = len(self.verts)
        self.verts.extend(tuple(p) for p in points)
        self.faces.append(tuple(range(start, start + len(points))))
        self.smooth.append(bool(smooth))

    def box(self, center, size, yaw=0.0):
        cx, cy, cz = center
        sx, sy, sz = size
        co, si = math.cos(yaw), math.sin(yaw)
        pts = []
        for ix, iy, iz in ((0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1),
                           (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1)):
            x = (ix - 0.5) * sx
            y = (iy - 0.5) * sy
            pts.append((cx + x * co - y * si,
                        cy + x * si + y * co,
                        cz + (iz - 0.5) * sz))
        start = len(self.verts)
        self.verts.extend(pts)
        for f in self.FACES:
            self.faces.append(tuple(start + i for i in f))
            self.smooth.append(False)

    def quad(self, p0, p1, p2, p3):
        self.poly((p0, p1, p2, p3))

    def tri(self, p0, p1, p2):
        self.poly((p0, p1, p2))

    def cylinder(self, center, radius, depth, segments=16, axis="Z", radius2=None):
        cx, cy, cz = center
        r2 = radius if radius2 is None else radius2
        rings = []
        for side, r in ((-0.5, radius), (0.5, r2)):
            ring = []
            for i in range(segments):
                a = TAU * i / segments
                u, v = r * math.cos(a), r * math.sin(a)
                if axis == "Z":
                    p = (cx + u, cy + v, cz + side * depth)
                elif axis == "Y":
                    p = (cx + u, cy + side * depth, cz + v)
                else:
                    p = (cx + side * depth, cy + u, cz + v)
                ring.append(p)
            rings.append(ring)
        low, high = rings
        for i in range(segments):
            j = (i + 1) % segments
            self.poly((low[i], low[j], high[j], high[i]), smooth=True)
        self.poly(low[::-1])
        self.poly(high)

    def cone(self, center, radius_bottom, radius_top, depth, segments=16, axis="Z"):
        self.cylinder(center, radius_bottom, depth, segments, axis, radius_top)

    def sphere(self, center, radius, scale=(1.0, 1.0, 1.0),
               segments=12, rings=8):
        cx, cy, cz = center
        rx, ry, rz = (radius * scale[0], radius * scale[1], radius * scale[2])
        rows = []
        for j in range(rings + 1):
            phi = PI * j / rings
            row = []
            for i in range(segments):
                theta = TAU * i / segments
                row.append((cx + rx * math.sin(phi) * math.cos(theta),
                            cy + ry * math.sin(phi) * math.sin(theta),
                            cz + rz * math.cos(phi)))
            rows.append(row)
        for j in range(rings):
            for i in range(segments):
                k = (i + 1) % segments
                self.poly((rows[j][i], rows[j][k], rows[j + 1][k], rows[j + 1][i]), True)

    def ring(self, center, radius, tube, segments=40, tube_segments=8):
        cx, cy, cz = center
        rows = []
        for i in range(segments):
            a = TAU * i / segments
            row = []
            for j in range(tube_segments):
                b = TAU * j / tube_segments
                r = radius + tube * math.cos(b)
                row.append((cx + r * math.cos(a), cy + r * math.sin(a),
                            cz + tube * math.sin(b)))
            rows.append(row)
        for i in range(segments):
            ni = (i + 1) % segments
            for j in range(tube_segments):
                nj = (j + 1) % tube_segments
                self.poly((rows[i][j], rows[ni][j], rows[ni][nj], rows[i][nj]), True)

    def flush(self):
        if not self.faces:
            return None
        mesh = bpy.data.meshes.new(self.name + " mesh")
        mesh.from_pydata(self.verts, [], self.faces)
        mesh.materials.append(self.material)
        mesh.update()
        if len(mesh.polygons) == len(self.smooth):
            mesh.polygons.foreach_set("use_smooth", self.smooth)
        obj = bpy.data.objects.new(self.name, mesh)
        self.collection.objects.link(obj)
        return obj


def make_cube(name, location, dimensions, material, collection, yaw=0.0, bevel=0.0):
    verts = [(-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5),
             (-0.5, 0.5, -0.5), (-0.5, 0.5, 0.5),
             (0.5, -0.5, -0.5), (0.5, -0.5, 0.5),
             (0.5, 0.5, -0.5), (0.5, 0.5, 0.5)]
    sx, sy, sz = dimensions
    mesh = bpy.data.meshes.new(name + " mesh")
    mesh.from_pydata([(x * sx, y * sy, z * sz) for x, y, z in verts], [], Batch.FACES)
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    obj.rotation_euler.z = yaw
    collection.objects.link(obj)
    if bevel:
        mod = obj.modifiers.new("Bordi smussati", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        mod.limit_method = "ANGLE"
        normal = obj.modifiers.new("Normali ponderate", "WEIGHTED_NORMAL")
        normal.keep_sharp = True
    return obj


def add_text(body, name, location, size, material, collection, yaw=0.0,
             align="CENTER", extrude=0.005):
    curve = bpy.data.curves.new(name + " lettering", "FONT")
    curve.body = body
    curve.align_x = align
    curve.align_y = "CENTER"
    curve.size = size
    curve.extrude = extrude
    curve.bevel_depth = 0.001
    curve.bevel_resolution = 1
    obj = bpy.data.objects.new(name, curve)
    obj.location = location
    obj.rotation_euler = (PI / 2, 0, yaw)
    curve.materials.append(material)
    collection.objects.link(obj)
    return obj


def child_collection(parent, name):
    col = bpy.data.collections.new(name)
    parent.children.link(col)
    return col


def create_materials():
    mats = {}
    defs = {
        "ground": ("Terreno verde", (92, 116, 66), 0.95, 0.0, 6, 0.12),
        "ground_far": ("Campagna lontana", (118, 138, 104), 0.95, 0.0, 4, 0.08),
        "grass": ("Prato", (84, 126, 66), 0.92, 0.0, 18, 0.08),
        "grass_light": ("Prato chiaro", (126, 160, 97), 0.90, 0.0, 16, 0.06),
        "asphalt": ("Asfalto", (46, 50, 52), 0.88, 0.0, 125, 0.14),
        "sidewalk": ("Pietra marciapiede", (181, 174, 158), 0.82, 0.0, 22, 0.06),
        "curb": ("Cordolo in granito", (115, 117, 112), 0.72, 0.0, 28, 0.05),
        "road_white": ("Segnaletica bianca", (238, 234, 218), 0.55, 0.0, 0, 0),
        "road_yellow": ("Segnaletica gialla", (239, 189, 64), 0.55, 0.0, 0, 0),
        "tile_a": ("Pavé avorio", (188, 177, 154), 0.78, 0.0, 36, 0.04),
        "tile_b": ("Pavé sabbia", (207, 194, 170), 0.78, 0.0, 34, 0.04),
        "tile_c": ("Pavé chiaro", (224, 213, 191), 0.80, 0.0, 26, 0.03),
        "stucco": ("Intonaco caldo", (207, 187, 152), 0.78, 0.0, 30, 0.08),
        "cream": ("Calce avorio", (227, 213, 184), 0.80, 0.0, 28, 0.06),
        "ochre": ("Ocra chiara", (195, 148, 99), 0.82, 0.0, 24, 0.07),
        "rose": ("Rosa antico", (184, 126, 108), 0.82, 0.0, 26, 0.06),
        "sage": ("Verde salvia", (145, 164, 139), 0.82, 0.0, 25, 0.06),
        "terracotta": ("Coppi e laterizio", (158, 75, 47), 0.82, 0.0, 20, 0.05,
                       None, 0.0, 2.2),
        "roof_dark": ("Ardesia", (70, 78, 82), 0.72, 0.0, 20, 0.04),
        "trim": ("Pietra chiara", (225, 215, 193), 0.70, 0.0, 18, 0.03),
        "brick": ("Mattone", (128, 76, 60), 0.85, 0.0, 22, 0.05),
        "glass": ("Vetri blu fumo", (50, 87, 102), 0.10, 0.0, 0, 0, None, 0.82),
        "glass_warm": ("Vetri illuminati", (144, 157, 139), 0.22, 0.14, 0, 0,
                       ((255, 214, 150), 0.9)),
        "wood": ("Legno noce", (103, 64, 39), 0.63, 0.0, 26, 0.05),
        "wood_light": ("Larice chiaro", (181, 125, 68), 0.63, 0.0, 30, 0.04),
        "metal": ("Metallo antracite", (39, 46, 48), 0.36, 0.72, 0, 0),
        "metal_gold": ("Ottone", (181, 132, 57), 0.30, 0.77, 0, 0),
        "concrete": ("Calcestruzzo chiaro", (172, 174, 164), 0.78, 0.0, 30, 0.05),
        "water": ("Acqua della fontana", (38, 137, 154), 0.06, 0.0, 0, 0, None,
                  0.88),
        "basolato": ("Basolato in pietra", (152, 148, 140), 0.84, 0.0, 0, 0,
                     None, 0.0, 0.0, 3.2),
        "sand": ("Sabbia del parco", (214, 196, 150), 0.95, 0.0, 40, 0.10),
        "leaf": ("Chioma verde", (63, 110, 58), 0.8, 0.0, 0, 0),
        "leaf_light": ("Foglie giovani", (105, 145, 70), 0.8, 0.0, 0, 0),
        "bark": ("Corteccia", (87, 57, 36), 0.84, 0.0, 0, 0),
        "cypress": ("Cipresso", (45, 88, 62), 0.82, 0.0, 0, 0),
        "olive": ("Olivo", (112, 128, 92), 0.85, 0.0, 0, 0),
        "wheat": ("Grano maturo", (196, 168, 96), 0.9, 0.0, 30, 0.08),
        "flower": ("Fiori lilla", (190, 116, 163), 0.65, 0.0, 0, 0),
        "red": ("Rosso corallo", (162, 53, 45), 0.4, 0.25, 0, 0),
        "blue": ("Blu petrolio", (42, 93, 120), 0.4, 0.25, 0, 0),
        "white": ("Bianco avorio", (237, 231, 213), 0.45, 0.0, 0, 0),
        "skin": ("Incarnato", (206, 160, 128), 0.62, 0.0, 0, 0),
        "hair_dark": ("Capelli scuri", (48, 36, 28), 0.7, 0.0, 0, 0),
        "hair_light": ("Capelli chiari", (168, 132, 78), 0.7, 0.0, 0, 0),
        "cloth_red": ("Veste rossa", (168, 52, 48), 0.75, 0.0, 0, 0),
        "cloth_blue": ("Veste blu", (48, 78, 128), 0.75, 0.0, 0, 0),
        "cloth_green": ("Veste verde", (72, 118, 74), 0.75, 0.0, 0, 0),
        "cloth_yellow": ("Veste gialla", (214, 168, 62), 0.75, 0.0, 0, 0),
        "cloth_violet": ("Veste viola", (110, 74, 128), 0.75, 0.0, 0, 0),
        "cloth_white": ("Veste chiara", (228, 224, 214), 0.75, 0.0, 0, 0),
        "canvas_green": ("Tela verde", (58, 118, 88), 0.8, 0.0, 0, 0),
        "canvas_blue": ("Tela azzurra", (66, 118, 158), 0.8, 0.0, 0, 0),
        "canvas_red": ("Tela rossa", (178, 66, 58), 0.8, 0.0, 0, 0),
        "canvas_yellow": ("Tela gialla", (222, 178, 74), 0.8, 0.0, 0, 0),
        "produce_red": ("Pomodori", (188, 44, 36), 0.5, 0.0, 0, 0),
        "produce_green": ("Insalate", (108, 158, 66), 0.6, 0.0, 0, 0),
        "produce_orange": ("Agrumi", (222, 138, 42), 0.5, 0.0, 0, 0),
        "produce_yellow": ("Frutta gialla", (226, 196, 74), 0.5, 0.0, 0, 0),
        "duck": ("Piumaggio bianco", (238, 236, 228), 0.7, 0.0, 0, 0),
        "beak": ("Becco", (222, 148, 44), 0.6, 0.0, 0, 0),
        "bird": ("Piumaggio grigio", (122, 124, 128), 0.7, 0.0, 0, 0),
        "rubber": ("Gomma rossa", (146, 84, 76), 0.9, 0.0, 0, 0),
        "plastic": ("Plastica azzurra", (72, 148, 178), 0.5, 0.0, 0, 0),
        "lamp": ("Luce calda", (255, 220, 143), 0.22, 0.0, 0, 0,
                 ((255, 181, 82), 2.3)),
    }
    for key, args in defs.items():
        mats[key] = make_material(args[0], args[1], args[2], args[3],
                                  noise_scale=args[4], bump_strength=args[5],
                                  emission=args[6] if len(args) > 6 else None,
                                  transmission=args[7] if len(args) > 7 else 0.0,
                                  wave_bump=args[8] if len(args) > 8 else 0.0,
                                  brick=args[9] if len(args) > 9 else 0.0)
    return mats


# ---------------------------------------------------------------------------
# Import dei modelli esistenti come librerie Blender
# ---------------------------------------------------------------------------
def load_collection_assets(path, collection_names, template_name, excluded=()):
    """Appende alcune collezioni esistenti e prepara un prototipo istanziabile."""
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        selected = [name for name in collection_names if name in src.collections]
        if not selected:
            raise RuntimeError("Nessuna collezione valida in " + path)
        dst.collections = selected
    template = bpy.data.collections.new(template_name)
    objects = {}
    for col in dst.collections:
        if not col:
            continue
        for obj in col.objects:
            if obj.type != "MESH" or obj.name in excluded:
                continue
            objects[obj.as_pointer()] = obj
    for obj in objects.values():
        template.objects.link(obj)
    return template, list(objects.values())


SOURCE_MODELS = (
    os.path.join("casa_1", "casa.blend"),
    os.path.join("casa_2", "villa.blend"),
    os.path.join("casa_3", "chalet.blend"),
    os.path.join("albero_2", "ciliegio.blend"),
)


def check_source_models():
    """Verifica che i modelli di casa_1, casa_2, casa_3 e albero_2 siano presenti."""
    missing = [rel for rel in SOURCE_MODELS
               if not os.path.isfile(os.path.join(REPO, rel))]
    if missing:
        raise FileNotFoundError(
            "Modelli sorgente mancanti in %s: %s. Lo script va eseguito dentro "
            "il repository Modelli3D, con le cartelle originali accanto a "
            "prova_citta_1." % (REPO, ", ".join(missing)))


def import_city_assets():
    check_source_models()
    houses = {}
    houses["casale"], _ = load_collection_assets(
        os.path.join(REPO, "casa_1", "casa.blend"),
        ("Edificio", "Tetto", "Serramenti"), "Modello sorgente — casale",
        excluded=("Orditura_tetto",))
    houses["villa"], _ = load_collection_assets(
        os.path.join(REPO, "casa_2", "villa.blend"),
        ("Edificio", "Tetto", "Serramenti", "Interni"),
        "Modello sorgente — villa")
    houses["chalet"], _ = load_collection_assets(
        os.path.join(REPO, "casa_3", "chalet.blend"),
        ("Edificio", "Tetto", "Serramenti", "Interni"),
        "Modello sorgente — chalet")
    # Il ciliegio originale è un albero Geometry Nodes: le varianti restano
    # caricate come dipendenza del nodo, ma non vengono mostrate a terra.
    cherry, cherry_objs = load_collection_assets(
        os.path.join(REPO, "albero_2", "ciliegio.blend"),
        ("Ciliegio", "Mazzetti_Varianti"), "Modello sorgente — ciliegio",
        excluded=("Terreno.001", "Sassi", "Petali_Caduti", "Petali_in_aria",
                  "Erba", "Mazzetto_01", "Mazzetto_02", "Mazzetto_03",
                  "Mazzetto_04", "Mazzetto_05", "Mazzetto_06", "Mazzetto_07",
                  "Mazzetto_08", "Mazzetto_09", "Mazzetto_10", "Mazzetto_11",
                  "Mazzetto_12"))
    return houses, cherry


def create_instance(name, template, collection, location, yaw=0.0, scale=1.0):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "CUBE"
    obj.empty_display_size = 1.0
    obj.instance_type = "COLLECTION"
    obj.instance_collection = template
    obj.location = location
    obj.rotation_euler.z = yaw
    obj.scale = (scale, scale, scale)
    collection.objects.link(obj)
    return obj


# ---------------------------------------------------------------------------
# Strade, marciapiedi e piazza
# ---------------------------------------------------------------------------
def make_batch_set(mats, col, keys):
    return {key: Batch("Geometria — " + key, mats[key], col) for key in keys}


def add_road_h(B, y, x0=-100, x1=100, width=8.0, sidewalk=True):
    B["asphalt"].box(((x0 + x1) / 2, y, 0.005), (x1 - x0, width, 0.045))
    # Cordoli e marciapiedi su entrambi i lati.
    for sign in (-1, 1):
        edge_y = y + sign * width / 2
        B["curb"].box(((x0 + x1) / 2, edge_y + sign * 0.12, 0.07),
                      (x1 - x0, 0.24, 0.14))
        if sidewalk:
            B["sidewalk"].box(((x0 + x1) / 2, edge_y + sign * 1.25, 0.055),
                              (x1 - x0, 2.25, 0.11))


def add_road_v(B, x, y0=-100, y1=100, width=8.0, sidewalk=True):
    B["asphalt"].box((x, (y0 + y1) / 2, 0.005), (width, y1 - y0, 0.045))
    for sign in (-1, 1):
        edge_x = x + sign * width / 2
        B["curb"].box((edge_x + sign * 0.12, (y0 + y1) / 2, 0.07),
                      (0.24, y1 - y0, 0.14))
        if sidewalk:
            B["sidewalk"].box((edge_x + sign * 1.25, (y0 + y1) / 2, 0.055),
                              (2.25, y1 - y0, 0.11))


def add_zebra_h(B, x, y, road_width=8.0):
    # Attraversamento che taglia una strada nord-sud.
    for i in range(9):
        xx = x - 3.4 + i * 0.85
        B["road_white"].box((xx, y, 0.041), (0.48, road_width - 1.1, 0.025))


def add_zebra_v(B, x, y, road_width=8.0):
    # Attraversamento che taglia una strada est-ovest.
    for i in range(9):
        yy = y - 3.4 + i * 0.85
        B["road_white"].box((x, yy, 0.041), (road_width - 1.1, 0.48, 0.025))


def build_roads(mats, road_col, plaza_col):
    keys = ("asphalt", "sidewalk", "curb", "road_white", "road_yellow",
            "tile_a", "tile_b", "tile_c")
    B = make_batch_set(mats, road_col, keys)
    # Rete leggibile: due anelli, quattro assi di quartiere e viale centrale.
    for y in (-70, 70):
        add_road_h(B, y, -100, 100, 8.0)
    for x in (-70, 70):
        add_road_v(B, x, -100, 100, 8.0)
    for y in (-32, 32):
        add_road_h(B, y, -100, 100, 8.0)
    for x in (-23, 23):
        add_road_v(B, x, -100, 100, 8.0)
    # Viale Roma: la piazza e il municipio interrompono il tratto centrale.
    add_road_v(B, 0, -100, -16, 10.0)
    add_road_v(B, 0, 29, 100, 10.0)
    # Raccordi leggermente rialzati: evitano la sovrapposizione coplanare delle
    # superfici nei nodi della griglia, lasciando leggibili le strisce pedonali.
    crossings_x = (-70, -23, 0, 23, 70)
    crossings_y = (-70, -32, 32, 70)
    roundabouts = ((23, 32), (-23, -32))
    for ix in crossings_x:
        for iy in crossings_y:
            if (ix, iy) in roundabouts:
                continue  # qui subentra la rotatoria fiorita
            B["asphalt"].box((ix, iy, 0.034), (8.0, 8.0, 0.014))
            for sx in (-1, 1):
                for sy in (-1, 1):
                    B["sidewalk"].box((ix + sx * 5.25, iy + sy * 5.25, 0.122),
                                      (2.18, 2.18, 0.024))
                    B["curb"].box((ix + sx * 4.12, iy + sy * 4.12, 0.078),
                                  (0.24, 0.24, 0.16))
    # Linee di mezzeria discontinue sugli assi principali.
    def in_roundabout(x, y):
        return (x - 23) ** 2 + (y - 32) ** 2 < 100 or \
               (x + 23) ** 2 + (y + 32) ** 2 < 100

    for y in (-70, 70, -32, 32):
        for x in range(-96, 97, 11):
            if y in (-32, 32) and -28 < x < 28:
                continue
            if in_roundabout(x, y):
                continue
            B["road_white"].box((x, y, 0.039), (4.5, 0.13, 0.025))
    for x in (-70, 70, -23, 23, 0):
        if x == 0:
            ranges = [(-98, -18), (30, 98)]
        else:
            ranges = [(-98, 98)]
        for y0, y1 in ranges:
            for y in range(int(y0) + 3, int(y1) - 2, 11):
                if in_roundabout(x, y):
                    continue
                B["road_white"].box((x, y, 0.039), (0.13, 4.5, 0.025))
    # Strisce di arresto e attraversamenti negli incroci del viale.
    for y in (-70, 70):
        add_zebra_h(B, 0, y, 10)
        add_zebra_h(B, -70, y, 8)
        add_zebra_h(B, 70, y, 8)
    for x, y in ((-70, 32), (70, 32), (-23, 32), (23, -32)):
        add_zebra_v(B, x, y, 8)
    add_zebra_v(B, 0, -32, 10)
    # Strisce gialle ai margini della piazza e stalli di sosta.
    for x in (-23, 23):
        B["road_yellow"].box((x, 0, 0.04), (0.12, 16, 0.025))
    for x, y, yaw in [(-39, -12, 0), (-39, -17, 0), (39, 12, 0), (39, 17, 0)]:
        B["road_white"].box((x, y, 0.04), (2.2, 0.12, 0.025), yaw)
    # Piazza centrale in pietra: cornice, letto e mosaico di lastre.
    make_cube("Basamento della piazza", (0, 0, -0.04), (31.8, 27.8, 0.20),
              mats["curb"], plaza_col, bevel=0.08)
    make_cube("Pavimentazione piazza", (0, 0, 0.08), (30.8, 26.8, 0.16),
              mats["tile_a"], plaza_col, bevel=0.05)
    tile_mats = ("tile_a", "tile_b", "tile_c")
    tile_batches = {k: Batch("Lastre piazza " + k, mats[k], plaza_col)
                    for k in tile_mats}
    for ix, x in enumerate([i * 0.92 - 14.26 for i in range(32)]):
        for iy, y in enumerate([i * 0.92 - 12.42 for i in range(28)]):
            key = tile_mats[(ix + iy + random.randrange(3)) % 3]
            tile_batches[key].box((x, y, 0.185), (0.875, 0.875, 0.055))
    for batch in tile_batches.values():
        batch.flush()
    # Inserti perimetrali e fasce che guidano verso il municipio.
    band = Batch("Fasce decorative in pietra", mats["trim"], plaza_col)
    for x in (-14.7, 14.7):
        band.box((x, 0, 0.23), (0.28, 25.7, 0.06))
    for y in (-12.8, 12.8):
        band.box((0, y, 0.23), (29.5, 0.28, 0.06))
    for x in (-8.4, -7.8, 7.8, 8.4):
        band.box((x, -2.0, 0.24), (0.20, 17.0, 0.05))
    band.flush()
    for batch in B.values():
        batch.flush()
    return B


# ---------------------------------------------------------------------------
# Municipio, palazzi e negozi
# ---------------------------------------------------------------------------
def lbox(batch, cx, cy, yaw, x, y, z, sx, sy, sz):
    wx = cx + x * math.cos(yaw) - y * math.sin(yaw)
    wy = cy + x * math.sin(yaw) + y * math.cos(yaw)
    batch.box((wx, wy, z), (sx, sy, sz), yaw)


def add_hip_roof(batch, cx, cy, width, depth, z0, z1, material_yaw=0.0):
    # Tetto a padiglione con colmo trasversale: quattro falde pulite.
    co, si = math.cos(material_yaw), math.sin(material_yaw)
    def p(x, y, z):
        return (cx + x * co - y * si, cy + x * si + y * co, z)
    ox, oy = width / 2 + 0.8, depth / 2 + 0.8
    ridge = max(0.5, width / 2 - 4.0)
    zpeak = z1
    front_l, front_r = p(-ox, -oy, z0), p(ox, -oy, z0)
    back_l, back_r = p(-ox, oy, z0), p(ox, oy, z0)
    ridge_l, ridge_r = p(-ridge, 0, zpeak), p(ridge, 0, zpeak)
    batch.poly((front_l, front_r, ridge_r, ridge_l))
    batch.poly((back_r, back_l, ridge_l, ridge_r))
    batch.poly((front_l, ridge_l, back_l))
    batch.poly((front_r, back_r, ridge_r))
    # Fascia di gronda e colmo.
    for a, b in ((front_l, front_r), (back_l, back_r),
                 (front_l, back_l), (front_r, back_r)):
        batch.poly((a, b, (b[0], b[1], z0 - 0.17), (a[0], a[1], z0 - 0.17)))
    batch.poly((ridge_l, ridge_r, (ridge_r[0], ridge_r[1], zpeak + 0.14),
                (ridge_l[0], ridge_l[1], zpeak + 0.14)))


def add_front_window(B, cx, cy, yaw, local_x, zc, width, height,
                     facade_depth, balcony=False, shutter=False,
                     glass_key="glass", frame_key="trim"):
    # La facciata principale locale è sul lato -Y.
    face = -facade_depth / 2
    lbox(B[glass_key], cx, cy, yaw, local_x, face - 0.055, zc,
         width, 0.085, height)
    fw = 0.12
    # Cornice, montanti e davanzale.
    for sx in (-1, 1):
        lbox(B[frame_key], cx, cy, yaw, local_x + sx * (width / 2 + fw / 2),
             face - 0.12, zc, fw, 0.18, height + 0.20)
    for sz in (-1, 1):
        lbox(B[frame_key], cx, cy, yaw, local_x, face - 0.12,
             zc + sz * (height / 2 + fw / 2), width + 0.24, 0.18, fw)
    lbox(B["metal"], cx, cy, yaw, local_x, face - 0.16, zc,
         0.055, 0.055, height)
    if balcony:
        slab_z = zc - height / 2 - 0.26
        lbox(B["concrete"], cx, cy, yaw, local_x, face - 0.52, slab_z,
             width + 0.78, 1.0, 0.20)
        # Balaustra e corrimano in metallo; aste a passo regolare.
        rail_y = face - 1.04
        rail_h = 0.58
        lbox(B["metal"], cx, cy, yaw, local_x, rail_y,
             slab_z + 0.20 + rail_h, width + 0.75, 0.085, 0.09)
        lbox(B["metal"], cx, cy, yaw, local_x, rail_y,
             slab_z + 0.26, width + 0.75, 0.075, 0.075)
        for i in range(6):
            bx = local_x - (width + 0.58) / 2 + i * (width + 0.58) / 5
            lbox(B["metal"], cx, cy, yaw, bx, rail_y,
                 slab_z + 0.49, 0.045, 0.05, 0.52)
        for side in (-1, 1):
            lbox(B["metal"], cx, cy, yaw, local_x + side * (width / 2 + 0.35),
                 face - 0.54, slab_z + 0.47, 0.06, 0.95, 0.055)
    if shutter:
        for side in (-1, 1):
            lbox(B["wood"], cx, cy, yaw, local_x + side * (width / 2 + 0.31),
                 face - 0.16, zc, 0.30, 0.11, height * 0.92)
            for j in range(5):
                z = zc - height * 0.38 + j * (height * 0.19)
                lbox(B["wood_light"], cx, cy, yaw,
                     local_x + side * (width / 2 + 0.31), face - 0.23, z,
                     0.29, 0.045, 0.045)


def add_shop_awning(B, cx, cy, yaw, lx, face_y, width, height, color_key):
    # Tenda inclinata, suddivisa in fasce colorate.
    ztop = height
    back_y = face_y - 0.18
    front_y = face_y - 1.05
    front_z = ztop - 0.62
    n = 8
    for i in range(n):
        xa = lx - width / 2 + width * i / n
        xb = lx - width / 2 + width * (i + 1) / n
        col = color_key if i % 2 == 0 else "white"
        pts = []
        for x, y, z in ((xa, back_y, ztop), (xb, back_y, ztop),
                        (xb, front_y, front_z), (xa, front_y, front_z)):
            wx = cx + x * math.cos(yaw) - y * math.sin(yaw)
            wy = cy + x * math.sin(yaw) + y * math.cos(yaw)
            pts.append((wx, wy, z))
        B[col].quad(*pts)
    lbox(B["wood"], cx, cy, yaw, lx, front_y,
         front_z - 0.02, width + 0.08, 0.08, 0.12)


def build_apartment(B, mats, decor_col, cx, cy, yaw, width, depth,
                    floors, facade_key, shop_names, title, modern=False):
    base_z = 0.30
    ground_h = 3.45
    upper_h = 2.85
    height = ground_h + (floors - 1) * upper_h
    bodymat = mats[facade_key]
    mass = make_cube(title + " — corpo", (cx, cy, base_z + height / 2),
                     (width, depth, height), bodymat, decor_col, yaw=yaw, bevel=0.10)
    face_y = -depth / 2
    # Zoccolo, marcapiani e cornicione continuo.
    for z, h, out in ((0.63, 0.28, 0.25), (ground_h, 0.18, 0.24),
                      (height - 0.3, 0.30, 0.38), (height + 0.48, 0.16, 0.40)):
        lbox(B["concrete" if z < 1 else "trim"], cx, cy, yaw, 0, 0, z,
             width + out, depth + out, h)
    # Pilastri d'angolo appena sporgenti.
    for x in (-width / 2 + 0.22, width / 2 - 0.22):
        lbox(B["trim"], cx, cy, yaw, x, face_y - 0.075,
             base_z + height / 2, 0.20, 0.13, height - 0.05)
    # Vetrine del piano terra.
    bay_count = 3
    bay_w = (width - 2.2) / bay_count
    shop_xs = [-width / 2 + 1.1 + bay_w * (i + 0.5) for i in range(bay_count)]
    for i, x in enumerate(shop_xs):
        if i == bay_count - 1:
            # Ingresso vetrato con montante e pannello della porta.
            glassw = bay_w - 0.45
            lbox(B["glass"], cx, cy, yaw, x, face_y - 0.07, 1.92,
                 glassw, 0.11, 2.25)
            lbox(B["wood"], cx, cy, yaw, x, face_y - 0.15, 1.55,
                 0.78, 0.14, 1.52)
            lbox(B["metal_gold"], cx, cy, yaw, x + 0.22, face_y - 0.25,
                 1.55, 0.045, 0.05, 0.20)
        else:
            lbox(B["glass"], cx, cy, yaw, x, face_y - 0.075, 1.95,
                 bay_w - 0.48, 0.12, 2.30)
        for edge in (-1, 1):
            lx = x + edge * (bay_w - 0.34) / 2
            lbox(B["trim"], cx, cy, yaw, lx, face_y - 0.15, 1.96,
                 0.12, 0.16, 2.52)
        lbox(B["trim"], cx, cy, yaw, x, face_y - 0.15, 0.68,
             bay_w - 0.34, 0.16, 0.12)
        lbox(B["trim"], cx, cy, yaw, x, face_y - 0.15, 3.20,
             bay_w - 0.34, 0.16, 0.12)
        sign_z = 3.05
        lbox(B["wood"], cx, cy, yaw, x, face_y - 0.22, sign_z,
             min(2.8, bay_w - 0.5), 0.10, 0.42)
        if i < len(shop_names):
            wx = cx + x * math.cos(yaw) - (face_y - 0.29) * math.sin(yaw)
            wy = cy + x * math.sin(yaw) + (face_y - 0.29) * math.cos(yaw)
            add_text(shop_names[i], title + " — insegna " + str(i + 1),
                     (wx, wy, sign_z), 0.27, mats["cream"], decor_col, yaw=yaw)
        add_shop_awning(B, cx, cy, yaw, x, face_y, min(3.6, bay_w - 0.25), 3.57,
                        "red" if i == 0 else ("sage" if i == 1 else "blue"))
    # Finestre residenziali e balconi dei piani superiori.
    upper_floors = floors - 1
    cols = 5 if width > 17 else 4
    usable = width - 3.2
    x_positions = [-usable / 2 + usable * (i + 0.5) / cols for i in range(cols)]
    for level in range(upper_floors):
        zc = ground_h + 0.26 + level * upper_h + 1.10
        for col, x in enumerate(x_positions):
            bal = (col + level) % 2 == 0
            add_front_window(B, cx, cy, yaw, x, zc, 1.28, 1.72, depth,
                             balcony=bal, shutter=not modern and col in (0, cols - 1),
                             frame_key="trim")
        # Fascia marcapiano che varia leggermente la luce delle facciate.
        lbox(B["trim"], cx, cy, yaw, 0, face_y - 0.12,
             ground_h + level * upper_h + 0.10,
             width + 0.20, 0.19, 0.13)
    # Finestre sui fianchi visibili: vetro, cornice e davanzale.
    side_x = width / 2
    for sign in (-1, 1):
        for level in range(upper_floors):
            zc = ground_h + 0.25 + level * upper_h + 1.1
            for y in (-depth * 0.33, -depth * 0.11,
                      depth * 0.11, depth * 0.33):
                lbox(B["glass"], cx, cy, yaw, sign * (side_x + 0.055), y, zc,
                     0.12, 1.20, 1.62)
                for edge in (-1, 1):
                    lbox(B["trim"], cx, cy, yaw,
                         sign * (side_x + 0.14), y + edge * 0.67, zc,
                         0.16, 0.12, 1.78)
                lbox(B["trim"], cx, cy, yaw, sign * (side_x + 0.14), y,
                     zc - 0.90, 0.16, 1.46, 0.12)
    # Corpo scala vetrato sul fianco: rompe le pareti cieche.
    for sign in (-1, 1):
        lbox(B["glass"], cx, cy, yaw, sign * (width / 2 + 0.07), -depth * 0.02,
             base_z + height / 2, 0.10, 2.6, height - 0.6)
        for level in range(floors):
            lbox(B["trim"], cx, cy, yaw, sign * (width / 2 + 0.13), -depth * 0.02,
                 0.5 + level * upper_h + 0.2, 0.16, 2.9, 0.16)
    # Parapetto e terrazza tecnica con fotovoltaico, scale e sfiati.
    ztop = base_z + height + 0.56
    for x in (-width / 2, width / 2):
        lbox(B["trim"], cx, cy, yaw, x, 0, ztop + 0.47, 0.20, depth + 0.2, 0.90)
    for y in (-depth / 2, depth / 2):
        lbox(B["trim"], cx, cy, yaw, 0, y, ztop + 0.47, width + 0.2, 0.20, 0.90)
    # Pannelli solari inclinati, nella parte posteriore della copertura.
    for i in range(3):
        lbox(B["roof_dark"], cx, cy, yaw, -width * 0.25 + i * 2.4,
             depth * 0.18, ztop + 0.14, 1.95, 2.6, 0.13)
        lbox(B["glass"], cx, cy, yaw, -width * 0.25 + i * 2.4,
             depth * 0.18, ztop + 0.23, 1.78, 2.38, 0.035)
    for i in range(2):
        lbox(B["concrete"], cx, cy, yaw, width * 0.27, -depth * 0.10 + i * 2.0,
             ztop + 0.65, 0.85, 1.0, 0.62)
    # Pluviali verticali e applique sulle facciate.
    for side in (-1, 1):
        lbox(B["metal"], cx, cy, yaw, side * (width / 2 + 0.12),
             face_y - 0.08, base_z + height / 2, 0.12, 0.12, height)
        lbox(B["lamp"], cx, cy, yaw, -width * 0.42, face_y - 0.28, 3.65,
             0.19, 0.08, 0.30)
    return mass


def build_town_hall(B, mats, col):
    cx, cy, w, d, h = 0.0, 20.0, 22.0, 12.0, 9.8
    make_cube("Municipio — volume principale", (cx, cy, h / 2), (w, d, h),
              mats["cream"], col, bevel=0.10)
    # Basamento in pietra, cornici marcapiano e cornicione.
    B["concrete"].box((cx, cy, 0.47), (w + 0.55, d + 0.45, 0.48))
    for z, thick, ext in ((3.4, 0.17, 0.35), (6.55, 0.18, 0.36),
                          (9.72, 0.34, 0.65)):
        B["trim"].box((cx, cy, z), (w + ext, d + ext, thick))
    # Lesene angolari e serramenti sul fronte principale (-Y).
    for x in (-9.7, -5.0, 5.0, 9.7):
        B["trim"].box((x, cy - d / 2 - 0.10, 5.0), (0.30, 0.18, 9.3))
    front = cy - d / 2
    for zc in (1.95, 4.92, 8.0):
        for x in (-8.0, -4.8, 4.8, 8.0):
            add_front_window(B, cx, cy, 0.0, x, zc, 1.36, 1.96, d,
                             balcony=(zc > 4.0 and abs(x) in (4.8,)),
                             frame_key="trim")
    # Portale centrale con doppia porta, lunetta e due rampe di gradini.
    B["wood"].box((0, front - 0.11, 1.72), (2.55, 0.22, 3.1))
    B["metal_gold"].box((-0.18, front - 0.25, 1.72), (0.045, 0.06, 0.27))
    B["trim"].box((-1.53, front - 0.16, 1.78), (0.32, 0.34, 3.7))
    B["trim"].box((1.53, front - 0.16, 1.78), (0.32, 0.34, 3.7))
    B["trim"].box((0, front - 0.16, 3.58), (3.38, 0.34, 0.36))
    B["trim"].box((0, front - 0.16, 0.14), (3.44, 0.34, 0.22))
    B["wood"].box((0, front - 0.36, 1.73), (2.35, 0.10, 3.00))
    for i in range(4):
        B["concrete"].box((0, front - 0.50 - i * 0.50, 0.13 + i * 0.13),
                           (4.3 + i * 0.65, 0.54, 0.26))
    # Portico: cinque colonne scanalate, capitelli e architrave.
    portico_y = front - 2.05
    for x in (-5.5, -2.75, 0, 2.75, 5.5):
        B["trim"].cylinder((x, portico_y, 2.55), 0.24, 4.4, 16)
        B["concrete"].box((x, portico_y, 0.46), (0.72, 0.72, 0.42))
        B["trim"].box((x, portico_y, 4.80), (0.68, 0.68, 0.32))
    B["trim"].box((0, portico_y, 5.10), (13.2, 0.88, 0.70))
    B["trim"].box((0, portico_y, 5.55), (13.9, 1.02, 0.20))
    # Balcone centrale e ringhiera.
    B["concrete"].box((0, front - 1.28, 5.75), (8.6, 1.7, 0.26))
    B["metal_gold"].box((0, front - 2.08, 6.27), (8.5, 0.08, 0.10))
    B["metal"].box((0, front - 2.08, 5.98), (8.4, 0.06, 0.07))
    for x in [i * 0.42 - 4.0 for i in range(20)]:
        B["metal"].box((x, front - 2.08, 6.12), (0.045, 0.055, 0.32))
    # Targa istituzionale sopra il portico.
    B["roof_dark"].box((0, front - 0.32, 7.22), (5.7, 0.14, 0.72))
    add_text("MUNICIPIO", "Targa municipio", (0, front - 0.42, 7.22),
             0.56, mats["cream"], col)
    # Finestre laterali e lucernari del tetto.
    for side in (-1, 1):
        for level in range(3):
            zc = 1.95 + level * 3.0
            for yy in (cy - 3.7, cy, cy + 3.7):
                B["glass"].box((side * (w / 2 + 0.07), yy, zc),
                               (0.10, 1.35, 1.8))
                B["trim"].box((side * (w / 2 + 0.13), yy, zc - 0.98),
                              (0.18, 1.52, 0.14))
    add_hip_roof(B["terracotta"], cx, cy, w, d, 9.96, 13.25)
    # Abbaini e tegole a fascia sul tetto.
    for x in (-7.5, -3.8, 0, 3.8, 7.5):
        B["terracotta"].box((x, cy - 2.2, 11.05), (0.80, 1.10, 1.15))
        B["glass"].box((x, cy - 2.79, 11.12), (0.48, 0.045, 0.58))
    # Torre civica con loggia campanaria e orologio.
    tx, ty = 0.0, cy + 0.5
    B["cream"].box((tx, ty, 11.72), (3.45, 3.45, 3.5))
    for z in (10.2, 13.25, 13.6):
        B["trim"].box((tx, ty, z), (3.9, 3.9, 0.22))
    # Aperture scure e colonnine della cella campanaria.
    for front_sign in (-1, 1):
        y = ty + front_sign * 1.78
        B["glass"].box((tx, y, 12.55), (1.35, 0.06, 1.35))
        for x in (-0.88, 0.88):
            B["trim"].box((x, y - front_sign * 0.06, 12.55), (0.16, 0.16, 1.65))
    for xsign in (-1, 1):
        B["glass"].box((tx + xsign * 1.78, ty, 12.55), (0.06, 1.35, 1.35))
        for yoff in (-0.88, 0.88):
            B["trim"].box((tx + xsign * 1.84, ty + yoff, 12.55), (0.16, 0.16, 1.65))
    # Quadranti sul fronte e sul retro (asse Y), con bordo, numeri e lancette.
    for face_sign in (-1, 1):
        fy = ty + face_sign * 1.91
        B["trim"].cylinder((tx, fy, 11.35), 0.78, 0.13, 40, axis="Y")
        B["white"].cylinder((tx, fy - face_sign * 0.08, 11.35), 0.66, 0.035,
                            40, axis="Y")
        B["metal_gold"].box((tx, fy - face_sign * 0.12, 11.45),
                            (0.055, 0.035, 0.48))
        B["metal_gold"].box((tx + 0.17, fy - face_sign * 0.12, 11.35),
                            (0.39, 0.035, 0.05))
    # Tetto della torre, banderuola e tricolore.
    B["terracotta"].cone((tx, ty, 14.18), 2.0, 0.08, 1.15, 4)
    B["metal_gold"].cylinder((tx, ty, 15.12), 0.065, 1.05, 12)
    B["metal_gold"].cone((tx, ty, 15.76), 0.20, 0.015, 0.40, 12)
    # Pennone con bandiera sul colmo.
    B["metal"].cylinder((8.9, cy + 1.2, 14.05), 0.055, 2.4, 12)
    B["brick"].quad((8.95, cy + 1.2, 15.1), (10.7, cy + 1.2, 14.8),
                    (10.7, cy + 1.2, 14.0), (8.95, cy + 1.2, 14.1))
    # Lampioni simmetrici all'ingresso.
    for x in (-8.2, 8.2):
        add_lamp(B, x, front - 1.1, height=4.2, ornate=True)


def build_street_lamp(B, x, y, height=5.4, yaw=0.0, ornate=False):
    B["metal"].cylinder((x, y, height / 2), 0.11, height, 12)
    B["metal_gold"].cylinder((x, y, 0.32), 0.22, 0.18, 12)
    arm_len = 0.72 if ornate else 0.50
    B["metal"].box((x + arm_len * 0.30, y, height - 0.28),
                   (arm_len, 0.075, 0.09), yaw)
    B["metal"].box((x + arm_len * 0.65, y, height - 0.02),
                   (0.10, 0.10, 0.35))
    B["lamp"].box((x + arm_len * 0.65, y, height - 0.25),
                  (0.48 if ornate else 0.35, 0.42 if ornate else 0.34, 0.36))
    B["metal"].cone((x + arm_len * 0.65, y, height - 0.01), 0.35, 0.12, 0.16, 12)


def add_lamp(B, x, y, height=5.0, ornate=False):
    build_street_lamp(B, x, y, height, ornate=ornate)


def build_trees_and_park(B, mats, green_col, road_col):
    # Un piccolo parco-giardino con aiuole geometriche e sentieri diagonali.
    parks = [(-52, 52, "Parco delle Rose"), (52, -52, "Giardino del Borgo")]
    for cx, cy, name in parks:
        make_cube(name + " — prato", (cx, cy, 0.03), (28, 28, 0.10),
                  mats["grass"], green_col, bevel=0.15)
        # Camminamenti incrociati e piastrelle d'accesso.
        B["tile_b"].box((cx, cy, 0.12), (2.4, 28, 0.12))
        B["tile_b"].box((cx, cy, 0.12), (28, 2.4, 0.12))
        for sign in (-1, 1):
            B["curb"].box((cx + sign * 12.7, cy, 0.18), (0.18, 24, 0.18))
            B["curb"].box((cx, cy + sign * 12.7, 0.18), (24, 0.18, 0.18))
        spots = ((cx + 8, cy + 8), (cx - 8, cy + 8), (cx + 8, cy - 8))
        if cx < 0:
            spots = ((cx + 8, cy + 8), (cx + 8, cy - 8), (cx - 10, cy + 8))
        for px, py in spots:
            B["wood"].box((px, py, 0.56), (2.3, 0.55, 0.12))
            for legx in (-0.8, 0.8):
                B["metal"].box((px + legx, py, 0.31), (0.10, 0.48, 0.48))
        # Aiuole con bordo, lavanda e arbusti.
        for dx, dy in ((-10, 0), (10, 0), (0, -10), (0, 10)):
            B["curb"].box((cx + dx, cy + dy, 0.27), (5.0, 1.45, 0.25))
            for j in range(7):
                px = cx + dx + (j - 3) * 0.55
                py = cy + dy + random.uniform(-0.32, 0.32)
                B["leaf_light"].sphere((px, py, 0.68), 0.28,
                                       (0.85, 0.85, 1.0), 8, 5)
        # Fontanella da parco.
        if cx < 0:
            B["concrete"].cylinder((cx, cy, 0.40), 1.15, 0.60, 24)
            B["water"].cylinder((cx, cy, 0.72), 0.90, 0.05, 24)
            B["metal_gold"].cylinder((cx, cy, 1.0), 0.12, 0.65, 12)
    # Aiuole triangolari alla piazza con piante fiorite.
    for cx, cy in ((-12, -10), (12, -10), (-12, 10), (12, 10)):
        B["concrete"].box((cx, cy, 0.36), (3.2, 1.45, 0.42))
        B["grass"].box((cx, cy, 0.59), (2.95, 1.20, 0.10))
        for j in range(5):
            x = cx - 1.0 + j * 0.5
            B["leaf"].cylinder((x, cy, 0.90), 0.035, 0.55, 7)
            B["flower"].sphere((x, cy, 1.20 + 0.05 * (j % 2)), 0.16,
                               (1.0, 0.7, 0.45), 8, 5)
    # Filare alberato lungo viali e piazzole.
    positions = [(-18.5, -11), (18.5, -11), (-18.5, 11), (18.5, 11),
                 (-52, 44), (-59, 52), (-45, 58), (43, -44), (59, -57)]
    for x, y in positions:
        # Cerchio/aiuola alla base degli alberi.
        B["curb"].cylinder((x, y, 0.12), 1.05, 0.18, 20, radius2=0.95)
        B["grass"].cylinder((x, y, 0.21), 0.90, 0.05, 20)
    # Siepi basse e bordi verdi del centro civico.
    for x in (-17.2, 17.2):
        B["leaf"].box((x, 0, 0.72), (0.48, 21, 1.1))
    for y in (-15.6, 15.6):
        if y != 15.6:
            B["leaf"].box((0, y, 0.70), (25, 0.5, 1.0))


def build_town_square(B, mats, furnishing_col):
    # Fontana centrale a due vasche concentriche.
    fx, fy = 0.0, -0.4
    B["concrete"].cylinder((fx, fy, 0.48), 4.0, 0.60, 64)
    B["trim"].ring((fx, fy, 0.82), 3.76, 0.25, 64, 10)
    B["water"].cylinder((fx, fy, 0.80), 3.50, 0.035, 64)
    B["concrete"].cylinder((fx, fy, 1.06), 1.38, 0.45, 48)
    B["trim"].ring((fx, fy, 1.28), 1.34, 0.18, 48, 8)
    B["water"].cylinder((fx, fy, 1.28), 1.13, 0.035, 48)
    B["concrete"].cylinder((fx, fy, 1.64), 0.48, 0.70, 32)
    B["metal_gold"].cylinder((fx, fy, 2.22), 0.18, 0.48, 18)
    B["metal_gold"].sphere((fx, fy, 2.72), 0.48, (0.65, 0.65, 1.15), 16, 10)
    # Zampilli e piccoli getti.
    for i in range(8):
        a = TAU * i / 8
        x, y = fx + math.cos(a) * 2.05, fy + math.sin(a) * 2.05
        B["water"].cylinder((x, y, 1.15), 0.035, 0.70, 8)
        B["water"].sphere((x, y, 1.54), 0.11, (0.8, 0.8, 1.4), 8, 5)
    # Dodici lampioni su bordo piazza e viali.
    for x, y in ((-14, -11), (14, -11), (-14, 11), (14, 11),
                 (-19, -19), (19, -19), (-19, 19), (19, 19),
                 (-44, -31), (44, -31), (-44, 31), (44, 31)):
        add_lamp(B, x, y, 5.6, ornate=(abs(x) < 20))
    # Panchine e tavolini all'aperto.
    for x, y, yaw in ((-8, 0, 0), (8, 0, PI), (0, 9, PI / 2), (0, -9, -PI / 2)):
        make_bench(B, x, y, yaw)
    # Chioschetto/caffè scenografico presso il lato sud della piazza.
    make_cube("Gazebo caffè — pavimento", (0, -11.4, 0.45), (5.2, 3.8, 0.20),
              mats["wood_light"], furnishing_col, bevel=0.04)
    for x in (-2.2, 2.2):
        for y in (-12.8, -10.0):
            B["wood"].box((x, y, 2.05), (0.16, 0.16, 3.2))
    B["terracotta"].box((0, -11.4, 3.72), (5.8, 4.3, 0.25))
    for x in (-1.2, 1.2):
        make_cafe_table(B, x, -11.5, 0.78)
    add_text("CAFFÈ DEL BORGO", "Insegna caffè", (0, -13.37, 2.42),
             0.32, mats["cream"], furnishing_col)
    # Paletti e catena bassa a protezione del bordo della piazza.
    for x in range(-15, 16, 3):
        for y in (-13.7, 13.7):
            B["metal"].cylinder((x, y, 0.50), 0.045, 0.68, 10)
            B["metal_gold"].sphere((x, y, 0.86), 0.09, segments=10, rings=6)
    for y in range(-10, 11, 5):
        for x in (-15.8, 15.8):
            B["metal"].cylinder((x, y, 0.50), 0.045, 0.68, 10)


def make_bench(B, x, y, yaw=0.0):
    # Assi locali X lungo la seduta, fronte lungo -Y.
    for i in range(4):
        lbox(B["wood_light"], x, y, yaw, 0, -0.06 + i * 0.14, 0.60,
             2.25, 0.12, 0.10)
    for i in range(3):
        lbox(B["wood"], x, y, yaw, 0, 0.38 + i * 0.13, 1.05,
             2.25, 0.12, 0.10)
    for side in (-1, 1):
        lbox(B["metal"], x, y, yaw, side * 0.83, 0.0, 0.37,
             0.12, 0.62, 0.62)
        lbox(B["metal"], x, y, yaw, side * 0.83, 0.42, 0.78,
             0.10, 0.10, 0.92)


def make_cafe_table(B, x, y, z):
    B["metal"].cylinder((x, y, z - 0.23), 0.055, 0.55, 10)
    B["wood_light"].cylinder((x, y, z + 0.08), 0.53, 0.12, 24)
    for a in range(4):
        angle = a * PI / 2 + PI / 4
        B["metal"].box((x + 0.24 * math.cos(angle), y + 0.24 * math.sin(angle),
                        z - 0.43), (0.06, 0.06, 0.42))


def build_crosswalk_signals(B, mats, sign_col):
    for x, y in ((-70, -70), (70, -70), (-70, 70), (70, 70),
                 (-23, 32), (23, 32), (-23, -32), (23, -32)):
        # Segnale verticale con pannello e simbolo semplice.
        B["metal"].cylinder((x + 4.7, y + 4.7, 2.2), 0.06, 4.3, 10)
        B["metal"].box((x + 4.7, y + 4.7, 4.5), (0.80, 0.24, 1.10))
        B["road_white"].sphere((x + 4.7, y + 4.54, 4.55), 0.24,
                               (0.72, 0.12, 0.12), 12, 6)
    # Cartelli direzionali all'ingresso della piazza.
    for x, yaw in ((-23, 0), (23, PI)):
        B["metal"].cylinder((x, -19.8, 2.0), 0.065, 3.9, 10)
        B["blue"].box((x, -19.8, 3.75), (1.55, 0.18, 0.56), yaw)
    add_text("PIAZZA", "Cartello Piazza", (-23.0, -19.93, 3.76),
             0.22, mats["white"], sign_col)
    add_text("CENTRO", "Cartello Centro", (23.0, -19.93, 3.76),
             0.22, mats["white"], sign_col)


# ---------------------------------------------------------------------------
# Pieve romanica con campanile e sagrato
# ---------------------------------------------------------------------------
def build_church(B, mats, col):
    """Pieve con navata, abside, rosone, campanile e sagrato in basolato."""
    cx, cy, yaw = -50.0, -16.0, PI / 2  # fronte verso est, sul viale
    w, d, h = 13.0, 24.0, 9.6
    make_cube("Pieve — navata", (cx, cy, 0.35 + h / 2), (d, w, h),
              mats["cream"], col, yaw=yaw, bevel=0.10)
    # Falde del tetto a capanna con colmo lungo l'asse locale Y.
    ridge = h + 0.35 + 3.1
    eave = h + 0.35
    for side in (-1, 1):
        p0 = (side * (w / 2 + 0.7), -d / 2 - 0.7, eave)
        p1 = (side * (w / 2 + 0.7), d / 2 + 0.7, eave)
        p2 = (0.0, d / 2 + 0.7, ridge)
        p3 = (0.0, -d / 2 - 0.7, ridge)
        pts = [lbox_point(cx, cy, yaw, *p) for p in (p0, p1, p2, p3)]
        B["terracotta"].quad(*pts)
    for sy in (-1, 1):
        a = lbox_point(cx, cy, yaw, -w / 2 - 0.7, sy * (d / 2 + 0.7), eave)
        b = lbox_point(cx, cy, yaw, w / 2 + 0.7, sy * (d / 2 + 0.7), eave)
        c = lbox_point(cx, cy, yaw, 0.0, sy * (d / 2 + 0.7), ridge)
        B["cream"].tri(a, b, c)
    lbox(B["terracotta"], cx, cy, yaw, 0, 0, ridge + 0.10, 0.5, d + 1.5, 0.22)
    # Lesene, cornici e zoccolo sulla navata.
    for lx in (-w / 2 - 0.10, w / 2 + 0.10):
        for ly in (-8.0, -2.6, 2.6, 8.0):
            lbox(B["trim"], cx, cy, yaw, lx, ly, 0.35 + h / 2, 0.22, 1.1, h)
    lbox(B["concrete"], cx, cy, yaw, 0, 0, 0.42, w + 0.5, d + 0.5, 0.5)
    lbox(B["trim"], cx, cy, yaw, 0, 0, eave - 0.25, w + 0.5, d + 0.5, 0.34)
    # Facciata: portale strombato, rosone e croce di colmo.
    face = -d / 2
    lbox(B["wood"], cx, cy, yaw, 0, face - 0.12, 2.1, 2.6, 0.24, 4.0)
    lbox(B["trim"], cx, cy, yaw, 0, face - 0.20, 4.35, 3.6, 0.4, 0.5)
    for side in (-1, 1):
        lbox(B["trim"], cx, cy, yaw, side * 1.55, face - 0.20, 2.1, 0.42, 0.42, 4.2)
        lbox(B["trim"], cx, cy, yaw, side * 2.1, face - 0.14, 2.1, 0.36, 0.30, 4.0)
    B["trim"].cylinder(lbox_point(cx, cy, yaw, 0, face - 0.16, 4.35), 1.30, 0.34,
                       24, axis="Y")
    B["glass"].cylinder(lbox_point(cx, cy, yaw, 0, face - 0.30, 4.35), 1.02,
                        0.10, 24, axis="Y")
    for i in range(8):
        a = TAU * i / 8
        p = lbox_point(cx, cy, yaw, math.cos(a) * 0.9, face - 0.34,
                       4.35 + math.sin(a) * 0.9)
        B["trim"].box(p, (0.10, 0.10, 0.10))
    lbox(B["trim"], cx, cy, yaw, 0, face + 0.6, ridge + 0.75, 0.16, 0.16, 1.5)
    lbox(B["trim"], cx, cy, yaw, 0, face + 0.6, ridge + 0.95, 0.9, 0.16, 0.16)
    # Finestre laterali ad arco (termali) lungo la navata.
    for sy in (-7.0, -2.3, 2.3, 7.0):
        for side in (-1, 1):
            lbox(B["glass"], cx, cy, yaw, side * (w / 2 + 0.06), sy, 5.6,
                 0.12, 1.5, 2.6)
            lbox(B["trim"], cx, cy, yaw, side * (w / 2 + 0.12), sy, 4.22,
                 0.18, 1.8, 0.22)
    # Abside semicircolare con calotta sul retro.
    B["cream"].cylinder(lbox_point(cx, cy, yaw, 0, d / 2 + 1.6, 0.35 + h * 0.42),
                        4.4, h * 0.84, 24)
    B["terracotta"].cone(lbox_point(cx, cy, yaw, 0, d / 2 + 1.6, eave - 0.1),
                         4.7, 0.4, 2.6, 24)
    for i in range(5):
        a = PI * (0.2 + 0.15 * i)
        lbox(B["glass"], cx, cy, yaw, math.cos(a) * 4.42, d / 2 + 1.6 +
             math.sin(a) * 4.42 - (d / 2 + 1.6) + (d / 2 + 1.6), 5.4,
             0.10, 1.1, 2.2)
    # Campanile in mattoni con cella campanaria, orologio e guglia.
    tx, ty = 7.9, -13.6
    lbox(B["brick"], cx, cy, yaw, tx, ty, 10.5, 3.4, 3.4, 20.6)
    for zz in (0.9, 7.4, 15.2, 20.4):
        lbox(B["trim"], cx, cy, yaw, tx, ty, zz, 3.8, 3.8, 0.34)
    for side in (-1, 1):
        lbox(B["trim"], cx, cy, yaw, tx + side * 1.72, ty, 10.5, 0.24, 0.24, 20.4)
        lbox(B["trim"], cx, cy, yaw, tx, ty + side * 1.72, 10.5, 0.24, 0.24, 20.4)
    for side in (-1, 1):
        lbox(B["glass"], cx, cy, yaw, tx + side * 1.74, ty, 18.0, 0.12, 1.2, 2.2)
        lbox(B["glass"], cx, cy, yaw, tx, ty + side * 1.74, 18.0, 1.2, 0.12, 2.2)
    lbox(B["white"], cx, cy, yaw, tx, ty - 1.78, 14.2, 1.2, 0.10, 1.2)
    B["metal_gold"].cylinder(lbox_point(cx, cy, yaw, tx, ty - 1.86, 14.2),
                             0.07, 0.10, 12, axis="Y")
    B["metal_gold"].box(lbox_point(cx, cy, yaw, tx, ty - 1.90, 14.5),
                        (0.05, 0.05, 0.5))
    B["terracotta"].cone(lbox_point(cx, cy, yaw, tx, ty, 22.2), 2.6, 0.1, 3.0, 4)
    lbox(B["metal_gold"], cx, cy, yaw, tx, ty, 24.1, 0.09, 0.09, 1.0)
    lbox(B["metal_gold"], cx, cy, yaw, tx, ty, 24.3, 0.56, 0.09, 0.09)
    # Sagrato in basolato con sagrestia, cipressi e lampioni.
    make_cube("Sagrato della pieve", (-33.6, -16.0, 0.10), (11.6, 17.5, 0.18),
              mats["basolato"], col, bevel=0.05)
    for px, py in ((-29.0, -22.6), (-29.0, -9.4)):
        B["cypress"].cylinder((px, py, 3.4), 0.24, 6.4, 10)
        B["cypress"].cone((px, py, 5.6), 1.15, 0.0, 7.4, 12)
    for px, py in ((-29.6, -19.5), (-29.6, -12.5)):
        add_lamp(B, px, py, height=4.4, ornate=True)
    # Panche del sagrato e piccola edicola votiva.
    for py in (-19.0, -13.0):
        lbox(B["wood_light"], -34.5, -16.0, PI / 2, 0, py + 16.0, 0.55,
             2.0, 0.5, 0.10)
    lbox(B["trim"], cx, cy, yaw, 6.9, -6.0, 1.5, 0.5, 0.9, 1.9)
    lbox(B["metal_gold"], cx, cy, yaw, 6.62, -6.0, 1.6, 0.10, 0.5, 0.7)


def lbox_point(cx, cy, yaw, x, y, z):
    wx = cx + x * math.cos(yaw) - y * math.sin(yaw)
    wy = cy + x * math.sin(yaw) + y * math.cos(yaw)
    return (wx, wy, z)


# ---------------------------------------------------------------------------
# Piazza del Mercato: bancarelle, casse di ortaggi e ombrelloni
# ---------------------------------------------------------------------------
def build_market_stall(B, x, y, yaw, canvas_key):
    w, d, htop = 3.4, 2.5, 2.5
    for sx in (-1, 1):
        for sy in (-1, 1):
            lbox(B["wood"], x, y, yaw, sx * (w / 2 - 0.1), sy * (d / 2 - 0.1),
                 htop / 2, 0.09, 0.09, htop)
    # Tenda a righe leggermente inclinata verso il fronte.
    n = 6
    for i in range(n):
        xa = -w / 2 - 0.25 + (w + 0.5) * i / n
        xb = -w / 2 - 0.25 + (w + 0.5) * (i + 1) / n
        key = canvas_key if i % 2 == 0 else "white"
        pts = [lbox_point(x, y, yaw, *p) for p in
               ((xa, -d / 2 - 0.35, htop - 0.42), (xb, -d / 2 - 0.35, htop - 0.42),
                (xb, d / 2 + 0.25, htop), (xa, d / 2 + 0.25, htop))]
        B[key].quad(*pts)
    # Banco con merce esposta in cassette.
    lbox(B["wood_light"], x, y, yaw, 0, -0.2, 0.86, w - 0.3, 1.1, 0.10)
    for side in (-1, 1):
        lbox(B["wood_light"], x, y, yaw, side * (w / 2 - 0.35), -0.2, 0.44,
             0.10, 1.0, 0.86)
    produce = ("produce_red", "produce_green", "produce_orange",
               "produce_yellow")
    for i in range(4):
        px = -w / 2 + 0.55 + i * (w - 1.1) / 3
        key = produce[(i + int(x)) % 4]
        lbox(B["wood"], x, y, yaw, px, -0.2, 1.0, 0.72, 0.85, 0.18)
        for j in range(6):
            ox = px + random.uniform(-0.24, 0.24)
            oy = -0.2 + random.uniform(-0.28, 0.28)
            lbox(B[key], x, y, yaw, ox, oy, 1.16, 0.16, 0.16, 0.12)
    # Cassette impilate a terra accanto al banco.
    for k in range(2):
        lbox(B["wood"], x, y, yaw, w / 2 + 0.45, 0.5 - k * 0.05,
             0.16 + k * 0.30, 0.7, 0.9, 0.28)


def build_market_square(B, mats, col):
    """Mercato settimanale sul lato nord della piazza, verso il municipio."""
    canvases = ("canvas_red", "canvas_green", "canvas_blue", "canvas_yellow")
    for row, ry in enumerate((6.6, 10.9)):
        for i, x in enumerate((-8.6, -4.3, 0.0, 4.3, 8.6)):
            build_market_stall(B, x, ry, PI if row else 0.0,
                               canvases[(i + row) % 4])
    # Ombrelloni con palo e stecche agli angoli del mercato.
    for ux, uy, key in ((-13, 5, "canvas_red"), (13, 5, "canvas_yellow"),
                        (0, 13.0, "canvas_green")):
        B["metal"].cylinder((ux, uy, 1.25), 0.055, 2.5, 10)
        B[key].cone((ux, uy, 2.62), 1.75, 0.12, 0.60, 12)
    # Carretto con cassette e lavagna dei prezzi.
    lbox(B["wood"], -13.6, 9.5, PI / 2, 0, 0, 0.62, 1.7, 1.1, 0.5)
    for side in (-1, 1):
        B["metal"].cylinder(lbox_point(-13.6, 9.5, PI / 2, side * 0.55, -0.6,
                                       0.42), 0.42, 0.08, 14, axis="Y")
    lbox(B["roof_dark"], -13.6, 9.5, PI / 2, 0, -0.72, 1.15, 1.15, 0.06, 0.9)
    lbox(B["wood"], -13.6, 9.5, PI / 2, 0, -0.78, 0.55, 0.06, 0.06, 1.3)
    add_text("MERCATO", "Insegna mercato", (-12.85, 9.5, 1.62), 0.26,
             mats["cream"], col, yaw=PI / 2)


# ---------------------------------------------------------------------------
# Rotatorie fiorite al posto di due incroci
# ---------------------------------------------------------------------------
def build_roundabout(B, x, y):
    r = 7.6
    B["asphalt"].cylinder((x, y, 0.028), r, 0.05, 40)
    B["curb"].ring((x, y, 0.10), 4.3, 0.16, 40, 8)
    B["grass"].cylinder((x, y, 0.16), 4.15, 0.16, 40)
    B["concrete"].cylinder((x, y, 0.42), 1.15, 0.5, 24)
    B["water"].cylinder((x, y, 0.66), 0.95, 0.04, 24)
    B["trim"].cylinder((x, y, 1.05), 0.28, 0.8, 16)
    B["metal_gold"].sphere((x, y, 1.62), 0.34, (0.8, 0.8, 1.1), 14, 8)
    for i in range(14):
        a = TAU * i / 14
        fx, fy = x + math.cos(a) * 3.3, y + math.sin(a) * 3.3
        B["flower"].sphere((fx, fy, 0.42), 0.20, (1.0, 0.8, 0.55), 8, 5)
        B["leaf_light"].sphere((fx, fy, 0.30), 0.17, (1.0, 1.0, 0.7), 8, 5)
    # Isole salvagente negli approcci.
    for a in range(4):
        ang = a * PI / 2 + PI / 4
        ix, iy = x + math.cos(ang) * 6.0, y + math.sin(ang) * 6.0
        B["curb"].box((ix, iy, 0.10), (1.5, 0.5, 0.16), ang + PI / 2)
        B["road_white"].box((ix, iy, 0.19), (1.3, 0.3, 0.04), ang + PI / 2)


# ---------------------------------------------------------------------------
# Laghetto con anatre e canne nel parco
# ---------------------------------------------------------------------------
def build_pond(B, cx, cy):
    B["curb"].cylinder((cx, cy, 0.10), 4.4, 0.22, 36, radius2=4.1)
    B["asphalt"].cylinder((cx, cy, 0.05), 4.0, 0.16, 36)
    B["water"].cylinder((cx, cy, 0.17), 3.85, 0.06, 36)
    for i in range(14):
        a = TAU * i / 14 + random.uniform(-0.1, 0.1)
        rx, ry = cx + math.cos(a) * 4.05, cy + math.sin(a) * 4.05
        for k in range(3):
            B["leaf_light"].cone((rx + random.uniform(-0.2, 0.2),
                                  ry + random.uniform(-0.2, 0.2),
                                  0.55 + 0.12 * k), 0.05, 0.01, 0.8, 6)
    # Ninfee e anatre.
    for i in range(6):
        a = random.uniform(0, TAU)
        rr = random.uniform(1.0, 3.0)
        B["leaf"].cylinder((cx + math.cos(a) * rr, cy + math.sin(a) * rr, 0.21),
                           0.30, 0.03, 10)
    for i, (dx, dy, yaw) in enumerate(((-1.0, 0.5, 0.6), (1.3, -0.8, 2.4),
                                       (0.2, 1.8, 4.1))):
        B["duck"].sphere((cx + dx, cy + dy, 0.32), 0.22, (1.35, 0.9, 0.8), 10, 6)
        B["duck"].cylinder((cx + dx + 0.20 * math.cos(yaw),
                            cy + dy + 0.20 * math.sin(yaw), 0.48), 0.07,
                           0.32, 8)
        B["duck"].sphere((cx + dx + 0.24 * math.cos(yaw),
                          cy + dy + 0.24 * math.sin(yaw), 0.64), 0.09,
                         segments=10, rings=6)
        B["beak"].cone((cx + dx + 0.35 * math.cos(yaw),
                        cy + dy + 0.35 * math.sin(yaw), 0.62), 0.045, 0.0,
                       0.13, 6, axis="Y")
    # Pontile in legno sul bordo.
    for i in range(4):
        B["wood_light"].box((cx + 3.3 + i * 0.40, cy - 1.8, 0.24),
                            (0.36, 1.7, 0.08))
    for px, py in ((cx + 3.2, cy - 2.5), (cx + 4.6, cy - 2.5),
                   (cx + 3.2, cy - 1.1), (cx + 4.6, cy - 1.1)):
        B["wood"].cylinder((px, py, 0.10), 0.06, 0.7, 8)


# ---------------------------------------------------------------------------
# Parco giochi nel Giardino del Borgo
# ---------------------------------------------------------------------------
def build_playground(B, cx, cy):
    B["rubber"].box((cx, cy, 0.14), (12.0, 9.0, 0.10))
    # Altalena doppia: montanti a A, traversa, catene e sedute.
    ax, ay = cx - 3.4, cy + 1.6
    for side in (-1, 1):
        for lean in (-1, 1):
            lbox(B["metal"], ax, ay, 0.0, side * 2.6, lean * 0.55, 1.05,
                 0.10, 0.10, 2.3)
    lbox(B["metal"], ax, ay, 0.0, 0, 0, 2.16, 5.4, 0.12, 0.12)
    for sx in (-1.1, 1.1):
        for chain in (-0.18, 0.18):
            lbox(B["metal"], ax, ay, 0.0, sx, chain, 1.45, 0.03, 0.03, 1.4)
        lbox(B["plastic" if sx < 0 else "canvas_yellow"], ax, ay, 0.0, sx, 0,
             0.72, 0.55, 0.28, 0.06)
    # Scivolo con scaletta e sponde.
    sx0, sy0 = cx + 2.6, cy + 2.4
    lbox(B["plastic"], sx0, sy0, -0.5, 0, 0, 0.62, 0.7, 2.6, 0.08)
    for side in (-1, 1):
        lbox(B["plastic"], sx0, sy0, -0.5, side * 0.38, 0, 0.78, 0.06, 2.6, 0.34)
    lbox(B["metal"], sx0, sy0, -0.5, 0, 1.42, 1.05, 0.7, 0.5, 0.10)
    for i in range(4):
        lbox(B["metal"], sx0, sy0, -0.5, 0, 1.05 + i * 0.28, 0.62 + i * 0.22,
             0.6, 0.05, 0.05)
    for side in (-1, 1):
        lbox(B["metal"], sx0, sy0, -0.5, side * 0.3, 1.42, 1.5, 0.08, 0.08, 1.0)
    # Sabbiera con bordo in legno e secchiello.
    bx, by = cx + 2.2, cy - 2.6
    for side in (-1, 1):
        lbox(B["wood_light"], bx, by, 0.0, 0, side * 1.5, 0.28, 3.2, 0.22, 0.18)
        lbox(B["wood_light"], bx, by, 0.0, side * 1.5, 0, 0.28, 0.22, 3.2, 0.18)
    lbox(B["sand"], bx, by, 0.0, 0, 0, 0.22, 2.9, 2.9, 0.12)
    lbox(B["canvas_red"], bx + 0.7, by - 0.6, 0.0, 0, 0, 0.36, 0.24, 0.24, 0.22)
    # Gioco a molla e panchina dei genitori.
    B["plastic"].sphere((cx - 2.6, cy - 2.8, 0.62), 0.30, (1.2, 0.8, 0.9), 10, 6)
    B["metal"].cylinder((cx - 2.6, cy - 2.8, 0.32), 0.07, 0.4, 8)
    make_bench(B, cx - 0.2, cy - 4.0, 0.0)


# ---------------------------------------------------------------------------
# Vita di strada: persone, bici, scooter, furgone, piccioni e panni stesi
# ---------------------------------------------------------------------------
def add_person(B, x, y, yaw, shirt, pants, scale=1.0, seated=False):
    s = scale
    z0 = 0.0
    if seated:
        z0 = 0.42
    lbox(B[pants], x, y, yaw, -0.09, 0, z0 + 0.40 * s, 0.15 * s, 0.17 * s,
         0.80 * s)
    lbox(B[pants], x, y, yaw, 0.09, 0, z0 + 0.40 * s, 0.15 * s, 0.17 * s,
         0.80 * s)
    lbox(B[shirt], x, y, yaw, 0, 0, z0 + 1.06 * s, 0.40 * s, 0.24 * s, 0.60 * s)
    for side in (-1, 1):
        lbox(B[shirt], x, y, yaw, side * 0.25 * s, 0.02, z0 + 1.04 * s,
             0.10 * s, 0.12 * s, 0.56 * s)
    B["skin"].sphere(lbox_point(x, y, yaw, 0, 0, z0 + 1.52 * s), 0.115 * s,
                     (0.92, 1.0, 1.12), 10, 7)
    hair = "hair_dark" if (int(x * 7 + y * 3) % 2) else "hair_light"
    B[hair].sphere(lbox_point(x, y, yaw, 0, 0.015 * s, z0 + 1.58 * s),
                   0.115 * s, (0.95, 1.0, 0.72), 10, 6)


def add_bicycle(B, x, y, yaw, frame_key):
    for wx in (-0.55, 0.55):
        p = lbox_point(x, y, yaw, wx, 0, 0.34)
        B["metal"].cylinder(p, 0.34, 0.045, 16, axis="Y")
    lbox(B[frame_key], x, y, yaw, 0, 0, 0.62, 0.95, 0.06, 0.06)
    lbox(B[frame_key], x, y, yaw, -0.28, 0, 0.80, 0.5, 0.05, 0.05)
    lbox(B[frame_key], x, y, yaw, 0.34, 0, 0.80, 0.06, 0.05, 0.42)
    lbox(B["metal"], x, y, yaw, 0.42, 0, 1.02, 0.34, 0.05, 0.05)
    lbox(B["metal"], x, y, yaw, -0.42, 0, 0.98, 0.22, 0.06, 0.05)


def add_scooter(B, x, y, yaw, body_key):
    for wx in (-0.62, 0.62):
        p = lbox_point(x, y, yaw, wx, 0, 0.26)
        B["metal"].cylinder(p, 0.26, 0.08, 14, axis="Y")
    lbox(B[body_key], x, y, yaw, -0.15, 0, 0.62, 1.05, 0.34, 0.36)
    lbox(B[body_key], x, y, yaw, 0.55, 0, 0.95, 0.30, 0.30, 0.75)
    lbox(B["metal"], x, y, yaw, 0.62, 0, 1.32, 0.42, 0.06, 0.06)
    lbox(B["metal"], x, y, yaw, -0.35, 0, 0.86, 0.55, 0.30, 0.10)


def add_van(B, x, y, yaw, body_key):
    lbox(B[body_key], x, y, yaw, -0.55, 0, 1.35, 3.4, 1.95, 2.0)
    lbox(B[body_key], x, y, yaw, 1.75, 0, 0.95, 1.5, 1.9, 1.5)
    lbox(B["glass"], x, y, yaw, 2.1, 0, 1.42, 0.7, 1.7, 0.7)
    lbox(B["glass"], x, y, yaw, 1.35, 0, 1.5, 0.12, 1.7, 0.6)
    for wx in (-1.5, 1.5):
        for side in (-1, 1):
            p = lbox_point(x, y, yaw, wx, side * 0.95, 0.45)
            B["metal"].cylinder(p, 0.45, 0.20, 16, axis="Y")


def build_street_life(B, mats, col):
    """Pedoni, ciclisti, animali e micro-dettagli che animano la scena."""
    shirts = ("cloth_red", "cloth_blue", "cloth_green", "cloth_yellow",
              "cloth_violet", "cloth_white")
    pants = ("cloth_blue", "hair_dark", "cloth_green", "cloth_red")
    crowd = [(-6, -6, 0.7), (3.5, -8, 2.2), (9, 4, 4.0), (-9, 6, 1.2),
             (0, 6.5, 3.4), (-4.5, 10.5, 5.2), (6.5, -3.5, 0.4), (12, -8, 2.8),
             (-12, -4, 1.9), (2.0, -12.5, 0.2), (-2.5, -13.0, 3.0),
             (28.5, 14.0, 1.6), (32.2, 18.2, 4.4), (36.5, 13.5, 0.9),
             (40.4, 18.6, 2.6), (44.0, 14.2, 5.0), (33.0, 22.5, 3.6),
             (-31.5, -14.0, 1.4), (-33.0, -18.5, 4.2), (-19.5, -20.5, 0.8),
             (19.0, 20.0, 2.0), (-60, -30.6, 1.1), (52, 30.6, 3.9),
             (48.5, -50.0, 2.3)]
    for i, (x, y, yaw) in enumerate(crowd):
        add_person(B, x, y, yaw, shirts[i % 6], pants[i % 4],
                   scale=random.uniform(0.94, 1.04))
    # Coppia seduta su una panchina della piazza e bimbo al parco giochi.
    add_person(B, -8.6, 0.4, PI, "cloth_violet", "cloth_blue", 0.98, seated=True)
    add_person(B, -7.4, 0.4, PI, "cloth_green", "hair_dark", 0.96, seated=True)
    add_person(B, 50.6, -53.4, 2.4, "cloth_yellow", "cloth_blue", 0.62)
    add_person(B, -54.5, 50.0, 1.2, "cloth_white", "cloth_green", 0.95)
    # Ciclisti in movimento e bici parcheggiate.
    for x, y, yaw in ((-14.0, -24.0, 0.4), (12.5, 26.0, 3.5), (24.5, -12.0, 1.7)):
        add_bicycle(B, x, y, yaw, "cloth_red" if yaw < 2 else "cloth_blue")
        add_person(B, x, y, yaw, "cloth_blue" if yaw < 2 else "cloth_yellow",
                   "hair_dark", 0.98, seated=True)
    for x, y, yaw in ((-16.6, -14.6, PI / 2), (-16.6, -13.4, PI / 2),
                      (16.8, 12.6, -PI / 2), (26.2, 9.4, 0.0),
                      (-38.6, -20.0, PI / 2), (44.2, 22.6, PI)):
        add_bicycle(B, x, y, yaw, ("cloth_green", "cloth_red", "cloth_blue",
                                   "cloth_yellow", "cloth_violet",
                                   "cloth_white")[int(abs(x)) % 6])
    # Scooter e furgone del mercato.
    add_scooter(B, -18.4, -16.6, PI / 2, "cloth_green")
    add_scooter(B, 18.4, 14.6, -PI / 2, "cloth_red")
    add_scooter(B, -36.0, -24.6, 0.3, "cloth_blue")
    add_van(B, 24.5, -24.0, PI / 2, "white")
    # Piccioni sulla piazza e in volo.
    for x, y in ((-3.0, -4.0), (-2.2, -3.4), (4.6, 2.2), (5.2, 2.8),
                 (-8.0, 8.0), (7.5, -7.5), (-11.0, -9.0), (10.5, 9.5)):
        B["bird"].sphere((x, y, 0.24), 0.10, (1.4, 0.85, 0.8), 8, 5)
        B["bird"].sphere((x + 0.12, y, 0.34), 0.055, segments=8, rings=5)
        B["beak"].cone((x + 0.19, y, 0.33), 0.02, 0.0, 0.06, 6, axis="Y")
    for x, y, z, yaw in ((-30, 10, 26, 0.6), (12, 34, 31, 2.1), (40, -20, 24, 4.0),
                         (-8, -40, 28, 1.2), (60, 40, 34, 3.0)):
        for side in (-1, 1):
            p0 = lbox_point(x, y, yaw, 0, 0, z)
            p1 = lbox_point(x, y, yaw, side * 0.9, 0.25, z + 0.34)
            p2 = lbox_point(x, y, yaw, side * 0.9, -0.25, z + 0.34)
            p3 = lbox_point(x, y, yaw, 0, 0.0, z + 0.02)
            B["bird"].quad(p0, p1, p2, p3)
    # Panni stesi sui balconi di due palazzi: fili e tessuti colorati.
    for bx, by, yaw in ((-46, 0, PI / 2), (46, 0, -PI / 2)):
        for level in (1, 2):
            z = 3.45 + 0.26 + level * 2.85 - 0.35
            face = -7.0
            p0 = lbox_point(bx, by, yaw, -3.4, face - 0.9, z)
            p1 = lbox_point(bx, by, yaw, 3.4, face - 0.9, z)
            B["metal"].cylinder(((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, z),
                                0.012, 6.8, 6, axis="Y")
            for i in range(5):
                t = -2.8 + i * 1.4
                key = shirts[(i + level) % 6]
                lbox(B[key], bx, by, yaw, t, face - 0.92, z - 0.34,
                     0.62, 0.03, 0.66)
    # Cassonetti, edicola e tombini: micro-arredo diffuso.
    for x, y, yaw, key in ((-20.4, -26.4, 0.0, "canvas_green"),
                           (-19.6, -26.4, 0.0, "canvas_yellow"),
                           (20.4, 26.4, PI, "canvas_green"),
                           (21.2, 26.4, PI, "canvas_blue")):
        lbox(B[key], x, y, yaw, 0, 0, 0.62, 0.75, 0.62, 1.15)
        lbox(B["metal"], x, y, yaw, 0, 0, 1.24, 0.78, 0.65, 0.10)
    lbox(B["cloth_blue"], 17.2, -19.2, 0.0, 0, 0, 1.35, 2.6, 2.2, 2.5)
    lbox(B["canvas_red"], 17.2, -19.2, 0.0, 0, -1.25, 1.5, 2.8, 0.5, 0.5)
    for i in range(6):
        lbox(B["white"], 17.2, -19.2, 0.0, -0.9 + i * 0.36, -1.52, 1.2,
             0.24, 0.04, 0.34)
    for x, y in ((-11, -24), (8, 24), (30, -12), (-30, 12), (0, -40)):
        B["metal"].cylinder((x, y, 0.045), 0.42, 0.03, 16)
    for x, y in ((-27.4, -10), (-27.4, 10), (27.4, -10), (27.4, 10)):
        B["metal"].box((x, y, 0.06), (0.35, 0.9, 0.05))
    # Festoni colorati tesi sopra la piazza, tra i lampioni.
    for (x0, y0), (x1, y1) in (((-14, -11), (14, -11)), ((-14, 11), (14, 11)),
                               ((-14, -11), (-14, 11))):
        n = 16
        for i in range(n + 1):
            t = i / n
            px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            pz = 5.3 - math.sin(t * PI) * 0.85
            if i < n:
                t2 = (i + 1) / n
                qx, qy = x0 + (x1 - x0) * t2, y0 + (y1 - y0) * t2
                qz = 5.3 - math.sin(t2 * PI) * 0.85
                B["metal"].box(((px + qx) / 2, (py + qy) / 2, (pz + qz) / 2),
                               (math.dist((px, py), (qx, qy)) + 0.05, 0.02, 0.02),
                               math.atan2(qy - py, qx - px))
            if i % 2 == 1:
                key = shirts[(i // 2) % 6]
                B[key].tri((px, py, pz), (px + 0.16, py + 0.16, pz),
                           (px + 0.08, py + 0.08, pz - 0.42))


# ---------------------------------------------------------------------------
# Giardini privati, orti e frutteti negli isolati
# ---------------------------------------------------------------------------
def build_gardens(B):
    """Siepi, frutteti e orti domestici a corredo delle case riutilizzate."""
    lots = [(-12, 44, 12, 12), (12, 44, 12, 12), (-12, -44, 12, 12),
            (12, -44, 12, 12), (-6, 61, 14, 7), (6, -61, 14, 7),
            (-59, 15, 10, 12), (57, 16, 10, 12), (33.5, -24, 9, 8), (40, 17, 20, 15),
            (-49, 71, 16, 8), (49, 71, 16, 8), (-49, -71, 16, 8),
            (49, -71, 16, 8), (-71, -48, 8, 14), (71, 48, 8, 14)]
    for lx, ly, lw, ld in lots:
        B["grass"].box((lx, ly, 0.02), (lw, ld, 0.08))
        B["leaf"].box((lx, ly + ld / 2, 0.36), (lw, 0.32, 0.6))
        for side in (-1, 1):
            B["leaf"].box((lx + side * lw / 2, ly, 0.36), (0.32, ld, 0.6))
        # Filare di frutta nana e aiuole di ortaggi.
        for i in range(4):
            px = lx - lw / 2 + lw * (i + 0.5) / 4
            B["bark"].cylinder((px, ly - ld * 0.22, 0.5), 0.06, 0.9, 6)
            B["leaf_light"].sphere((px, ly - ld * 0.22, 1.15), 0.62,
                                   (1.0, 0.9, 0.8), 10, 6)
            B["produce_red"].sphere((px + 0.3, ly - ld * 0.22 + 0.2, 1.1),
                                    0.07, segments=6, rings=4)
        for i in range(3):
            py = ly + ld * 0.12 + i * 0.55
            B["grass"].box((lx, py, 0.13), (lw * 0.7, 0.34, 0.10))
    # Vasi fioriti agli ingressi e pergolati nei cortili maggiori.
    for px, py in ((-40.5, -16), (-28.5, -22), (26.5, 9.5), (45.5, 22.5),
                   (-64, 40), (64, -40)):
        for k in range(3):
            B["terracotta"].cylinder((px + k * 0.7, py, 0.30), 0.22, 0.42, 10)
            B["flower"].sphere((px + k * 0.7, py, 0.62), 0.24,
                               (1.0, 0.9, 0.8), 8, 5)
    for px, py, yaw in ((-52, 26, 0.0), (52, -26, PI / 2)):
        for i in range(4):
            lbox(B["wood"], px, py, yaw, -1.8 + i * 1.2, 0, 1.15,
                 0.10, 0.10, 2.3)
        lbox(B["wood"], px, py, yaw, 0, 0, 2.32, 4.0, 1.6, 0.10)
        lbox(B["leaf"], px, py, yaw, 0, 0, 2.46, 4.2, 1.8, 0.22)


# ---------------------------------------------------------------------------
# Campagna attorno al borgo: colline, campi, filari e borgo lontano
# ---------------------------------------------------------------------------
HILLS = ((-260, 240, 20, 80), (230, 250, 18, 75), (-260, -240, 17, 80),
         (270, -210, 15, 75), (-40, 310, 19, 90), (60, -310, 16, 90),
         (-310, 20, 15, 80), (310, 60, 13, 80),
         (-170, 205, 10, 45), (160, 185, 9, 42), (-200, -150, 9, 45),
         (195, -140, 8, 42), (-95, 215, 8, 38), (100, -210, 7, 38),
         (-140, 165, 6, 30), (120, 150, 5, 28), (-160, -120, 6, 30),
         (150, -110, 5, 28), (-60, 175, 5, 26), (40, -170, 5, 26))


def hill_height(x, y):
    """Quota della campagna: piana dentro il borgo, colline oltre gli orti."""
    r = math.hypot(x, y)
    t = min(1.0, max(0.0, (r - 125.0) / 45.0))
    t = t * t * (3 - 2 * t)
    h = 0.0
    for cx, cy, amp, rad in HILLS:
        d2 = (x - cx) ** 2 + (y - cy) ** 2
        h += amp * math.exp(-d2 / (rad * rad))
    h += 2.0 * math.sin(x * 0.03 + 1.1) * math.cos(y * 0.027 + 0.4)
    theta = math.atan2(y, x)
    wob = 0.72 + 0.34 * math.sin(3.0 * theta + 1.2) + \
          0.22 * math.sin(7.0 * theta - 0.6) + 0.16 * math.sin(13.0 * theta + 2.0) + \
          0.10 * math.sin(23.0 * theta - 1.1)
    rim = min(1.0, max(0.0, (r - 150.0) / 60.0))
    rim = rim * rim * (3 - 2 * rim)
    return t * h + 15.0 * rim * wob


def build_countryside(B, mats, col):
    """Anello di campagna con colline dolci, colture e un borgo sul colle."""
    # Griglia a passo 5.4 m: dossi morbidi, senza le facce a bande visibili
    # sulle colline a distanza.
    half, step = 215.0, 5.375
    n = int(half * 2 / step)
    rows = []
    for j in range(n + 1):
        row = []
        for i in range(n + 1):
            x, y = -half + i * step, -half + j * step
            row.append((x, y, hill_height(x, y) - 0.06))
        rows.append(row)
    for j in range(n):
        for i in range(n):
            cxm = -half + (i + 0.5) * step
            cym = -half + (j + 0.5) * step
            key = "ground_far" if math.hypot(cxm, cym) > 148 else "ground"
            B[key].poly((rows[j][i], rows[j][i + 1],
                         rows[j + 1][i + 1], rows[j + 1][i]), smooth=True)
    # Pianura sconfinata oltre le colline: chiude l'orizzonte senza "mare".
    ring = [(math.cos(TAU * i / 72) * 6000.0,
             math.sin(TAU * i / 72) * 6000.0, -0.55) for i in range(72)]
    B["ground_far"].poly(ring)
    # Campi coltivati con colori diversi sulla piana esterna al borgo.
    fields = [(-124, 42, 34, 46, "wheat"), (-124, -58, 32, 44, "grass_light"),
              (124, -42, 34, 44, "wheat"), (124, 58, 32, 42, "grass"),
              (42, 124, 44, 32, "grass_light"), (-58, 124, 44, 32, "wheat"),
              (58, -124, 42, 32, "grass"), (-42, -124, 44, 32, "olive")]
    for fx, fy, fw, fd, key in fields:
        B[key].box((fx, fy, -0.03), (fw, fd, 0.08))
    # Filari di vite e ulivi ordinati nei campi dedicati.
    for fx, fy, fw, fd, key in fields:
        if key not in ("wheat", "olive"):
            continue
        for row in range(5):
            ry = fy - fd / 2 + fd * (row + 0.5) / 5
            for k in range(int(fw / 3)):
                px = fx - fw / 2 + 2 + k * 3
                B["olive"].sphere((px, ry, 0.42), 0.55, (1.0, 0.8, 0.7), 8, 5)
                B["bark"].cylinder((px, ry, 0.16), 0.06, 0.34, 6)
    # Cipressi isolati sulla piana e filari sui primi pendii.
    for x, y, s in ((-112, 92, 1.0), (-95, 118, 0.9), (112, 100, 1.1),
                    (100, -112, 1.0), (-115, -100, 0.95), (118, 20, 1.05),
                    (-20, 116, 1.0), (24, -116, 0.9)):
        B["cypress"].cylinder((x, y, 3.0 * s), 0.22 * s, 5.6 * s, 8)
        B["cypress"].cone((x, y, 4.6 * s), 1.05 * s, 0.0, 6.6 * s, 10)
    for x, y in ((-160, 150), (-140, 168), (150, -160), (168, 140), (-170, -140)):
        z = hill_height(x, y)
        B["cypress"].cylinder((x, y, z + 3.2), 0.24, 6.0, 8)
        B["cypress"].cone((x, y, z + 5.0), 1.15, 0.0, 7.0, 10)
    # Borgo lontano sul colle a nord-ovest: campanile e tetti minuti.
    hx, hy = -168.0, 152.0
    hz = hill_height(hx, hy)
    B["cream"].box((hx, hy, hz + 3.0), (7.0, 11.0, 6.0))
    B["terracotta"].cone((hx, hy, hz + 7.4), 6.4, 0.4, 3.2, 4)
    B["brick"].box((hx + 5.5, hy - 4.0, hz + 7.0), (2.6, 2.6, 14.0))
    B["terracotta"].cone((hx + 5.5, hy - 4.0, hz + 15.2), 2.0, 0.1, 2.4, 4)
    for i, (ox, oy, ow, od) in enumerate(((-6, 8, 5, 4), (7, 6, 4, 5),
                                          (-8, -6, 4, 4), (6, -7, 5, 4))):
        B["cream" if i % 2 else "ochre"].box((hx + ox, hy + oy, hz + 1.6),
                                             (ow, od, 3.2))
        B["terracotta"].cone((hx + ox, hy + oy, hz + 3.9),
                             max(ow, od) * 0.78, 0.3, 1.9, 4)


# ---------------------------------------------------------------------------
# Alberi procedurali di città e istanze di modelli preesistenti
# ---------------------------------------------------------------------------
def make_local_tree_template(mats):
    col = bpy.data.collections.new("Prototipo — albero urbano")
    trunk = Batch("Tronco albero urbano", mats["bark"], col)
    leaves = Batch("Chioma albero urbano", mats["leaf"], col)
    leaves2 = Batch("Foglie illuminate", mats["leaf_light"], col)
    trunk.cylinder((0, 0, 2.6), 0.22, 5.2, 14)
    for angle, start, end, rad in ((0.5, 2.7, 4.2, 0.11), (2.1, 2.8, 4.3, 0.12),
                                   (3.8, 3.0, 4.6, 0.12), (5.3, 2.8, 4.1, 0.10)):
        p0 = (math.cos(angle) * 0.10, math.sin(angle) * 0.10, start)
        p1 = (math.cos(angle) * 1.5, math.sin(angle) * 1.5, end)
        trunk.cylinder(((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2,
                        (p0[2] + p1[2]) / 2), rad, math.dist(p0, p1), 10, axis="Z")
    for idx, (x, y, z, r) in enumerate((
            (0, 0, 5.25, 1.9), (-1.15, -0.2, 4.75, 1.45), (1.10, 0.1, 4.78, 1.45),
            (0.0, 1.05, 4.82, 1.45), (-0.2, -1.0, 4.75, 1.42),
            (-0.75, 0.62, 5.85, 1.15), (0.85, -0.55, 5.72, 1.18))):
        target = leaves if idx % 2 == 0 else leaves2
        target.sphere((x, y, z), r, (1.0, 0.92, 0.78), 14, 8)
    trunk.flush()
    leaves.flush()
    leaves2.flush()
    return col


def add_city_trees(tree_template, blossom_template, mats, tree_col, green_col):
    broad_positions = [(-52, 44), (-59, 52), (-45, 58), (43, -44), (59, -57)]
    for i, (x, y) in enumerate(broad_positions):
        create_instance("Albero urbano %02d" % (i + 1), tree_template, tree_col,
                        (x, y, 0.02), yaw=random.uniform(0, TAU),
                        scale=random.uniform(0.78, 1.05))
    # Ciliegio fiorito: ripreso direttamente dal modello esistente albero_2.
    blossoms = [(-18.1, -9.4), (18.1, -9.4), (-18.1, 9.4), (18.1, 9.4),
                (-62, 59), (62, -59)]
    for i, (x, y) in enumerate(blossoms):
        create_instance("Ciliegio in fiore %02d" % (i + 1), blossom_template,
                        tree_col, (x, y, 0.04), yaw=random.uniform(0, TAU),
                        scale=0.72 if i < 4 else 0.82)
    # Cipressi a gruppi: colonne verdi e sottili ai margini della città.
    cones = Batch("Cipressi e verde verticale", mats["cypress"], green_col)
    for x, y, h in ((-89, -62, 10), (-91, -36, 9), (-90, 12, 11), (-90, 54, 10),
                    (89, -55, 11), (90, -22, 9), (91, 19, 10), (90, 57, 12),
                    (-48, 92, 9), (0, 92, 11), (48, 92, 9), (-45, -93, 10),
                    (0, -93, 9), (47, -92, 11)):
        cones.cylinder((x, y, h * 0.42), 0.20, h * 0.84, 10)
        cones.cone((x, y, h * 0.58), 1.25, 0.0, h * 0.78, 12)
    cones.flush()


def build_tree_beds(B):
    # Bordure e terreno sotto gli alberi della piazza.
    for x, y in ((-18.1, -9.4), (18.1, -9.4), (-18.1, 9.4), (18.1, 9.4)):
        B["curb"].cylinder((x, y, 0.16), 1.15, 0.22, 24)
        B["grass"].cylinder((x, y, 0.28), 0.98, 0.06, 24)


# ---------------------------------------------------------------------------
# Veicoli, pensiline e segnaletica
# ---------------------------------------------------------------------------
def build_car(B, cx, cy, yaw, body_key="blue", name="Auto"):
    # Il muso guarda lungo X locale positivo.
    def box(key, x, y, z, sx, sy, sz):
        lbox(B[key], cx, cy, yaw, x, y, z, sx, sy, sz)
    box(body_key, 0, 0, 0.78, 4.25, 1.82, 1.05)
    box(body_key, -0.15, 0.0, 1.35, 2.35, 1.52, 0.82)
    box("glass", -0.14, 0.0, 1.43, 2.10, 1.39, 0.63)
    # Montanti centrali e parabrezza.
    for x in (-1.20, -0.10, 0.83):
        box("metal", x, 0, 1.43, 0.065, 1.47, 0.72)
    box("white", 2.06, -0.52, 0.84, 0.13, 0.22, 0.30)
    box("red", -2.06, -0.52, 0.84, 0.12, 0.20, 0.30)
    for x in (-1.35, 1.35):
        for side in (-1, 1):
            B["metal"].cylinder((cx + x * math.cos(yaw) - side * 0.90 * math.sin(yaw),
                                 cy + x * math.sin(yaw) + side * 0.90 * math.cos(yaw), 0.46),
                                0.43, 0.20, 16, axis="Y")
            B["metal"].cylinder((cx + x * math.cos(yaw) - side * 1.01 * math.sin(yaw),
                                 cy + x * math.sin(yaw) + side * 1.01 * math.cos(yaw), 0.46),
                                0.20, 0.205, 16, axis="Y")
    return name


def build_bus_shelter(B, x, y, yaw=0):
    for dx in (-2.7, 2.7):
        lbox(B["metal"], x, y, yaw, dx, 0, 1.65, 0.12, 0.12, 3.3)
    lbox(B["glass"], x, y, yaw, -1.3, 0, 1.55, 2.5, 0.07, 2.55)
    lbox(B["glass"], x, y, yaw, 1.4, -1.0, 1.55, 0.07, 2.0, 2.55)
    lbox(B["metal"], x, y, yaw, 0, -0.10, 3.30, 5.8, 2.35, 0.18)
    lbox(B["glass"], x, y, yaw, 0, 0, 0.76, 4.8, 0.06, 1.45)
    lbox(B["wood_light"], x, y, yaw, -0.1, -0.3, 0.56, 2.2, 0.58, 0.12)


def build_transport(B, mats, traffic_col):
    # Automobili parcheggiate e bus di linea, con dettagli leggibili dall'alto.
    build_car(B, -45, -30.6, 0, "red", "Auto rossa")
    build_car(B, -58, -30.6, 0, "white", "Auto avorio")
    build_car(B, 49, 30.6, PI, "blue", "Auto blu")
    build_car(B, 55, -66.5, PI / 2, "white", "Auto bianca")
    # Sosta lungo i viali e traffico leggero sul viale centrale.
    build_car(B, -12, -34.5, 0, "blue", "Auto blu in sosta")
    build_car(B, -6.5, -34.5, 0, "white", "Auto bianca in sosta")
    build_car(B, 34, 34.5, PI, "red", "Auto rossa in sosta")
    build_car(B, 58, 34.5, PI, "white", "Auto avorio in sosta")
    build_car(B, 2.6, -22, PI / 2, "blue", "Auto sul viale")
    build_car(B, -2.6, 44, -PI / 2, "red", "Auto sul viale nord")
    # Autobus urbano sul viale a sud.
    yaw = PI / 2
    def busbox(key, x, y, z, sx, sy, sz):
        lbox(B[key], 1.6, -51.5, yaw, x, y, z, sx, sy, sz)
    busbox("sage", 0, 0, 1.45, 10.2, 2.45, 2.7)
    busbox("glass", 0, -0.01, 2.1, 8.6, 2.25, 1.35)
    busbox("cream", -1.9, -1.27, 1.45, 3.9, 0.08, 1.38)
    busbox("cream", 1.8, -1.27, 1.45, 3.4, 0.08, 1.38)
    busbox("white", 5.00, -1.22, 1.28, 0.25, 0.08, 0.32)
    busbox("red", -5.00, -1.22, 1.25, 0.20, 0.08, 0.30)
    for x in (-3.2, 3.2):
        for side in (-1, 1):
            lx = 1.6 + x * math.cos(yaw) - side * 1.2 * math.sin(yaw)
            ly = -51.5 + x * math.sin(yaw) + side * 1.2 * math.cos(yaw)
            B["metal"].cylinder((lx, ly, 0.68), 0.58, 0.22, 18, axis="Y")
            B["metal"].cylinder((lx, ly + 0.13, 0.68), 0.26, 0.235, 18, axis="Y")
    build_bus_shelter(B, -3.0, -62, 0)
    add_text("FERMATA  •  LINEA 1", "Insegna fermata autobus",
             (-3.0, -63.22, 3.70), 0.24, bpy.data.materials["Bianco avorio"],
             traffic_col)


# ---------------------------------------------------------------------------
# Allestimento finale, illuminazione e camera
# ---------------------------------------------------------------------------
def setup_world_and_camera(root, mats):
    scene = bpy.context.scene
    world = bpy.data.worlds.new("Cielo del borgo")
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    # Cielo fisico a scattering multiplo: tardo pomeriggio limpido e caldo.
    try:
        sky.sky_type = "MULTIPLE_SCATTERING"
    except TypeError:  # Blender 4.x
        sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(SUN_ELEVATION)
    sky.sun_rotation = math.radians(SUN_ROTATION)
    sky.sun_disc = False
    sky.altitude = 260
    sky.air_density = 1.15
    if hasattr(sky, "aerosol_density"):
        sky.aerosol_density = 2.6
    else:
        sky.dust_density = 2.6
    sky.ozone_density = 1.25
    bg.inputs["Strength"].default_value = 0.13
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    scene.world = world
    sun_data = bpy.data.lights.new("Sole pomeridiano", "SUN")
    sun_data.energy = 9.0
    sun_data.angle = math.radians(1.6)
    sun_data.color = (1.0, 0.80, 0.58)
    sun = bpy.data.objects.new("Sole pomeridiano", sun_data)
    elev = math.radians(SUN_ELEVATION)
    rot = math.radians(SUN_ROTATION)
    direction = Vector((math.sin(rot) * math.cos(elev),
                        -math.cos(rot) * math.cos(elev),
                        -math.sin(elev)))
    sun.location = (-100, -130, 160)
    sun.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    root.objects.link(sun)
    area_data = bpy.data.lights.new("Rimbalzo piazza", "AREA")
    area_data.energy = 350
    area_data.shape = "DISK"
    area_data.size = 70
    area_data.color = (1.0, 0.93, 0.82)
    area = bpy.data.objects.new("Rimbalzo piazza", area_data)
    area.location = (-18, -45, 105)
    area.rotation_euler = (Vector((0, 0, 0)) - area.location).to_track_quat("-Z", "Y").to_euler()
    root.objects.link(area)
    # Camera panoramica a tre quarti: inquadra piazza, pieve e mercato con le
    # colline sullo sfondo.
    cam_data = bpy.data.cameras.new("Camera — veduta del borgo")
    cam_data.lens = 46
    cam_data.clip_end = 1600
    cam_data.dof.use_dof = False
    cam = bpy.data.objects.new("Camera — veduta del borgo", cam_data)
    cam.location = (118, -138, 46)
    target = Vector((-4, 6, 6.0))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    root.objects.link(cam)
    scene.camera = cam
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 96
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 8
    scene.cycles.transparent_max_bounces = 8
    scene.cycles.caustics_reflective = False
    scene.cycles.caustics_refractive = False
    scene.render.resolution_x = 2000
    scene.render.resolution_y = 1500
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.compression = 18
    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    scene.view_settings.exposure = 0.1
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.filepath = OUT_PNG
    scene.render.film_transparent = False


def options_from_argv():
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    return {"render": ("--render" in args or "--quick" in args),
            "quick": ("--quick" in args)}


def main():
    started = time.time()
    opts = options_from_argv()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    root = bpy.data.collections.new("Borgo_delle_Querce")
    scene.collection.children.link(root)
    terrain_col = child_collection(root, "01 — Terreno e rete stradale")
    road_col = child_collection(root, "02 — Strade, marciapiedi e piazza")
    house_col = child_collection(root, "03 — Case esistenti, riutilizzate")
    architecture_col = child_collection(root, "04 — Municipio e palazzi")
    green_col = child_collection(root, "05 — Giardini e alberature")
    furnishing_col = child_collection(root, "06 — Arredo urbano")
    traffic_col = child_collection(root, "07 — Mobilità e fermate")
    sign_col = child_collection(root, "08 — Insegne e segnaletica")
    mats = create_materials()
    # Il suolo continuo evita un orizzonte tagliato attorno alla città.
    make_cube("Terreno del borgo", (0, 0, -0.42), (214, 214, 0.80),
              mats["ground"], terrain_col, bevel=0.20)
    # Importa i modelli originali, poi li istanzia in lotti urbani.
    house_templates, cherry_template = import_city_assets()
    # Viabilità e piazza.
    road_batches = build_roads(mats, road_col, furnishing_col)
    # Aree verdi, alberi urbani e ciliegi provenienti dal repository.
    green_batches = make_batch_set(mats, green_col,
                                   ("grass", "tile_b", "curb", "leaf", "leaf_light",
                                    "flower", "concrete", "water", "wood", "wood_light",
                                    "metal", "metal_gold"))
    build_trees_and_park(green_batches, mats, green_col, road_col)
    build_tree_beds(green_batches)
    # Alberi generici a chioma ampia + istanze del modello di ciliegio già esistente.
    urban_tree = make_local_tree_template(mats)
    add_city_trees(urban_tree, cherry_template, mats, green_col, green_col)
    # Case: orientamento frontale calibrato sui modelli sorgente.
    front_angle = {"casale": -PI / 2, "villa": PI / 2, "chalet": -PI / 2}
    directions = {"N": PI / 2, "S": -PI / 2, "E": 0.0, "W": PI}
    def place_house(model, x, y, direction, scale, label):
        yaw = directions[direction] - front_angle[model]
        create_instance(label, house_templates[model], house_col, (x, y, 0.03), yaw, scale)
    top_row = [(-49, "casale", 0.86), (-19, "chalet", 0.74),
               (19, "villa", 0.66), (49, "casale", 0.82)]
    south_row = [(-49, "chalet", 0.78), (-19, "casale", 0.86),
                 (19, "villa", 0.62), (49, "chalet", 0.77)]
    for x, model, scale in top_row:
        place_house(model, x, 80, "S", scale, "Casa nord — " + model)
    for x, model, scale in south_row:
        place_house(model, x, -80, "N", scale, "Casa sud — " + model)
    for i, y in enumerate((-48, -17, 17, 48)):
        model = ("casale", "villa", "chalet", "casale")[i]
        scale = (0.84, 0.62, 0.76, 0.82)[i]
        place_house(model, -80, y, "E", scale, "Casa ovest — " + model)
        model2 = ("chalet", "casale", "villa", "chalet")[i]
        scale2 = (0.76, 0.84, 0.63, 0.78)[i]
        place_house(model2, 80, y, "W", scale2, "Casa est — " + model2)
    # Secondo tessuto residenziale: isolati interni e casali di campagna.
    inner_lots = [(-12, 44, "chalet", 0.70, "S"), (12, 44, "villa", 0.58, "S"),
                  (-12, -44, "casale", 0.70, "N"), (12, -44, "chalet", 0.66, "N"),
                  (-59, 15, "casale", 0.66, "E"), (-34, 4, "chalet", 0.60, "E"),
                  (57, 16, "casale", 0.70, "W"), (33.5, -16, "chalet", 0.66, "W"),
                  (59, -16, "casale", 0.70, "W")]
    rural_lots = [(-96, 40, "casale", 0.90, "E"), (96, 40, "chalet", 0.88, "W"),
                  (-96, -40, "villa", 0.72, "E"), (96, -40, "casale", 0.88, "W"),
                  (40, 96, "chalet", 0.84, "S"), (-40, 96, "casale", 0.86, "S"),
                  (40, -96, "villa", 0.68, "N"), (-40, -96, "chalet", 0.84, "N")]
    for x, y, model, scale, direction in inner_lots + rural_lots:
        tag = "Campagna" if abs(x) > 90 or abs(y) > 90 else "Isolato"
        place_house(model, x, y, direction, scale,
                    "%s %d,%d — %s" % (tag, x, y, model))
    # Palazzi d'affaccio e un fronte commerciale più moderno lungo il viale.
    detail_batches = make_batch_set(mats, architecture_col,
        ("glass", "glass_warm", "metal", "metal_gold", "wood", "wood_light",
         "trim", "concrete", "terracotta", "roof_dark", "cream", "red", "blue",
         "sage", "white", "lamp", "brick", "flower", "leaf", "leaf_light"))
    build_town_hall(detail_batches, mats, architecture_col)
    build_apartment(detail_batches, mats, architecture_col, -46, 0, PI / 2,
                    18, 14, 5, "ochre", ("LIBRI", "CAFFÈ", "BOTTEGA"),
                    "Palazzo delle Logge")
    build_apartment(detail_batches, mats, architecture_col, 46, 0, -PI / 2,
                    18, 14, 5, "rose", ("FARMACIA", "ALIMENTARI", "FIORI"),
                    "Casa del Mercato")
    build_apartment(detail_batches, mats, architecture_col, 0, 51, 0,
                    20, 15, 5, "sage", ("PANETTERIA", "POSTA", "BAR"),
                    "Residenza Aurora", modern=True)
    build_apartment(detail_batches, mats, architecture_col, 0, -51, PI,
                    20, 15, 5, "cream", ("HOTEL", "TRATTORIA", "GELATERIA"),
                    "Albergo del Borgo")
    # Due palazzine di quartiere riempiono gli isolati diagonalmente opposti.
    build_apartment(detail_batches, mats, architecture_col, 51, 51, 0,
                    16, 11, 3, "cream", ("FORNO", "EDICOLA", "ORTOFRUTTA"),
                    "Casa delle Vigne")
    build_apartment(detail_batches, mats, architecture_col, -51, -51, PI,
                    16, 11, 3, "ochre", ("CIRCOLO", "PANIFICIO", "EMPORIO"),
                    "Corte Nuova")
    # Unità commerciali più basse agli imbocchi dei viali, con portici e insegne.
    for bx, by, yaw, facade, title in ((-47, 15, PI / 2, "rose", "Botteghe Ovest"),
                                       (47, -15, -PI / 2, "sage", "Botteghe Est")):
        build_apartment(detail_batches, mats, architecture_col, bx, by, yaw,
                        16, 11, 3, facade, ("CAFFÈ", "MERCATO", "ARTIGIANI"),
                        title, modern=False)
    # Piazzetta, fontana, panchine, pensilina e lampioni.
    civic_batches = make_batch_set(mats, furnishing_col,
        ("water", "concrete", "trim", "metal", "metal_gold", "lamp", "wood",
         "wood_light", "terracotta", "glass", "glass_warm", "grass", "leaf",
         "leaf_light", "flower", "blue", "white", "curb"))
    build_town_square(civic_batches, mats, furnishing_col)
    # Arredi del parco e aiuole creati sopra, più segnaletica e veicoli.
    traffic_batches = make_batch_set(mats, traffic_col,
        ("metal", "metal_gold", "glass", "white", "red", "blue", "sage", "cream",
         "wood", "wood_light", "road_white", "lamp"))
    build_crosswalk_signals(traffic_batches, mats, sign_col)
    build_transport(traffic_batches, mats, traffic_col)
    # Nuovi landmark: pieve, mercato, rotatorie, laghetto, parco giochi,
    # vita di strada e giardini privati degli isolati.
    life_batches = make_batch_set(mats, furnishing_col, LIFE_KEYS)
    build_church(life_batches, mats, architecture_col)
    build_market_square(life_batches, mats, furnishing_col)
    for rx, ry in ((23, 32), (-23, -32)):
        build_roundabout(life_batches, rx, ry)
    build_pond(life_batches, -60, 44)
    build_playground(life_batches, 52, -50)
    build_street_life(life_batches, mats, furnishing_col)
    build_gardens(life_batches)
    # Campagna circostante: colline, colture, cipressi e borgo sul colle.
    country_batches = make_batch_set(mats, terrain_col, COUNTRY_KEYS)
    build_countryside(country_batches, mats, terrain_col)
    # Chiude tutte le mesh batch per materiale.
    for group in (green_batches, detail_batches, civic_batches, traffic_batches,
                  life_batches, country_batches):
        for batch in group.values():
            batch.flush()
    # Alcune aree verdi sono state popolate con le stesse mesh in due momenti:
    # l'operazione di flush sopra include tutto il contenuto accumulato.
    setup_world_and_camera(root, mats)
    # Raccoglie in un'unica vista di apertura della scena il borgo intero.
    bpy.context.view_layer.objects.active = bpy.data.objects.get("Camera — veduta del borgo")
    bpy.ops.object.select_all(action="DESELECT")
    cam = bpy.data.objects.get("Camera — veduta del borgo")
    if cam:
        cam.select_set(True)
    scene.render.filepath = OUT_PNG
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("Salvato %s (%.1f MB)" % (OUT_BLEND, os.path.getsize(OUT_BLEND) / 1e6))
    print("Oggetti: %d | mesh: %d | materiali: %d" %
          (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.materials)))
    if opts["render"]:
        if opts["quick"]:
            scene.cycles.samples = 16
            scene.render.resolution_x = 1280
            scene.render.resolution_y = 960
        print("Render in corso: %dx%d, %d campioni" %
              (scene.render.resolution_x, scene.render.resolution_y,
               scene.cycles.samples))
        render_started = time.time()
        bpy.ops.render.render(write_still=True)
        print("Anteprima: %s (%.1fs)" % (OUT_PNG, time.time() - render_started))
    print("Completato in %.1fs" % (time.time() - started))


if __name__ == "__main__":
    main()
