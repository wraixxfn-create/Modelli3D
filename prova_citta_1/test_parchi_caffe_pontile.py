"""Esattamente i tre interventi della ventitreesima versione; non richiede Blender.

Le funzioni geometriche sono estratte dal generatore via AST, come negli altri
test leggeri della città: nessun file .blend viene aperto o modificato. Una
sotto classe di `Batch` annota le primitive ricevute e `make_cube` è
intercettato, così ogni verifica confronta quote e ingombri con quello che lo
script costruisce davvero.

1. `build_trees_and_park`: le quattro aiuole di ciascun parco cadevano sui due
   assi dei camminamenti incrociati (fasce da 2,40 m col piano a 0,18 m):
   quelle a `dx = ±10` correvano per cinque metri dentro la banda
   orizzontale, quelle a `dy = ±10` la attraversavano da parte a parte,
   piantate tre centimetri nel lastricato e alte fino a 0,40 m. Ora ogni
   aiuola è girata sul lato lungo e spostata nel quadrante libero, con il
   bordo a 37 cm dal ciglio; la fontanella del Parco delle Rose, che coi suoi
   2,30 m di diametro occupava 2,40 m di croce, è accostata al braccio nord.
2. `build_town_square`: la platea del chiosco del caffè era sospesa — il
   fondo a 0,35 m, quattordici centimetri sopra il lastricato della piazza
   (0,21 m) — e mostrava la fessura sotto tutto il perimetro. Ora lo zoccolo
   scende a 0,15 m dentro la pavimentazione e il calpestio resta a 0,55 m.
3. `build_pond`: i quattro pali del pontile salivano da -0,25 a 0,45 m
   mentre il tavolato sta fra 0,20 e 0,28 m: ogni fusto spuntava così
   diciassette centimetri sopra il calpestio. Ora si ferma a 0,22 m, due
   centimetri dentro lo spessore delle tavole.
"""
from __future__ import annotations

from collections import defaultdict
import __future__
import ast
from contextlib import contextmanager
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class Vector:
    """Sottoinsieme di `mathutils.Vector`, sufficiente a `add_tube`."""

    __slots__ = ("x", "y", "z")

    def __init__(self, values):
        self.x, self.y, self.z = (float(v) for v in values)

    def __iter__(self):
        return iter((self.x, self.y, self.z))

    def __add__(self, other):
        return Vector((self.x + other.x, self.y + other.y, self.z + other.z))

    def __sub__(self, other):
        return Vector((self.x - other.x, self.y - other.y, self.z - other.z))

    def __mul__(self, scalar):
        return Vector((self.x * scalar, self.y * scalar, self.z * scalar))

    __rmul__ = __mul__

    def cross(self, other):
        return Vector((self.y * other.z - self.z * other.y,
                       self.z * other.x - self.x * other.z,
                       self.x * other.y - self.y * other.x))

    def normalized(self):
        length = math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
        if not length:
            return Vector((0.0, 0.0, 0.0))
        return Vector((self.x / length, self.y / length, self.z / length))


class _BpyStub:
    """Sostituisce `bpy` solo per le annotazioni di tipo di `Batch`."""

    class types:
        Material = object
        Collection = object
        Object = object


FUNCTIONS = {
    "Batch", "lbox", "lbox_tilt", "lbox_point", "add_tube", "make_bench",
    "build_street_lamp", "add_lamp", "build_trees_and_park", "spans_outside",
    "add_oriented_cone", "build_pond", "build_pond_bridge", "bridge_point", "in_bridge_corridor",
    "build_town_square", "make_cafe_table", "make_cafe_chair", "add_person",
}
CONSTANTS = {"POND_CENTER", "BRIDGE_HALF_SPAN", "BRIDGE_Y_OFFSET",
             "BRIDGE_HALF_WIDTH", "CAFFE_FLOOR_Z", "CAFFE_TABLES",
             "CAFFE_CHAIRS"}


def load_geometry():
    source = Path(__file__).with_name("genera_citta.py").read_text()
    tree = ast.parse(source)
    kept = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in FUNCTIONS:
            kept.append(node)
        elif isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in CONSTANTS for t in node.targets):
            kept.append(node)
    tree.body = kept
    import random
    scope = {"math": math, "random": random, "PI": math.pi, "TAU": math.tau,
             "Vector": Vector, "bpy": _BpyStub,
             "make_cube": Mock(), "add_text": Mock()}
    code = compile(tree, "genera_citta.py", "exec",
                   flags=__future__.annotations.compiler_flag, dont_inherit=True)
    exec(code, scope)
    return scope, SimpleNamespace(**scope)


scope, city = load_geometry()


class RecordingBatch(city.Batch):
    """`Batch` che annota anche le primitive ricevute, per poterle verificare."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []

    def box(self, center, size, yaw=0.0):
        self.calls.append({"kind": "box", "center": center, "size": size,
                           "yaw": yaw})
        return super().box(center, size, yaw)

    def cylinder(self, center, radius, depth, segments=16, axis="Z", radius2=None):
        self.calls.append({"kind": "cylinder", "center": center, "radius": radius,
                           "depth": depth, "axis": axis})
        return super().cylinder(center, radius, depth, segments, axis, radius2)

    def cone(self, center, radius_bottom, radius_top, depth, segments=16, axis="Z"):
        self.calls.append({"kind": "cylinder", "center": center,
                           "radius": radius_bottom, "depth": depth, "axis": axis})
        return super().cone(center, radius_bottom, radius_top, depth, segments, axis)

    def ring(self, center, radius, tube, segments=40, tube_segments=8):
        self.calls.append({"kind": "ring", "center": center, "radius": radius,
                           "tube": tube})
        return super().ring(center, radius, tube, segments, tube_segments)

    def sphere(self, center, radius, scale=(1.0, 1.0, 1.0), segments=16, rings=8):
        self.calls.append({"kind": "sphere", "center": center, "radius": radius})
        return super().sphere(center, radius, scale, segments, rings)


def batches():
    return defaultdict(lambda: RecordingBatch("Test", None, None))


def pick(calls, shape, **filters):
    """Chiamate di una primitiva, filtrate campo per campo."""
    out = []
    for call in calls:
        if call["kind"] != shape:
            continue
        if any(abs(call[name] - value) > 1e-9 for name, value in filters.items()):
            continue
        out.append(call)
    return out


@contextmanager
def recorded_cubes():
    """Azzera e restituisce il Mock di `make_cube` per la durata del blocco."""
    make_cube = scope["make_cube"]
    make_cube.reset_mock()
    yield make_cube


def cubes_named(make_cube, name):
    return [c for c in make_cube.call_args_list if c.args and c.args[0] == name]


def spans(center, size):
    """Intervalli (x, y, z) occupati da una scatola."""
    sx, sy, sz = size
    return ((center[0] - sx / 2, center[0] + sx / 2),
            (center[1] - sy / 2, center[1] + sy / 2),
            (center[2] - sz / 2, center[2] + sz / 2))


def overlaps_xy(a, b):
    """Sovrapposizione in pianta di due ingombri (tolleranza nulla)."""
    return (min(a[0][1], b[0][1]) - max(a[0][0], b[0][0]) > 1e-9 and
            min(a[1][1], b[1][1]) - max(a[1][0], b[1][0]) > 1e-9)


def clearance_xy(box, point):
    """Distanza in pianta fra un rettangolo e un punto."""
    dx = max(box[0][0] - point[0], 0.0, point[0] - box[0][1])
    dy = max(box[1][0] - point[1], 0.0, point[1] - box[1][1])
    return math.hypot(dx, dy)


def clearance_xy_circle(box, center, radius):
    """Distanza in pianta fra un rettangolo e un cerchio."""
    return clearance_xy(box, center) - radius


class ParchiTests(unittest.TestCase):
    """Aiuole e fontanella lasciano libera la croce dei camminamenti."""

    PARKS = ((-52.0, 52.0), (52.0, -52.0))   # Parco delle Rose, Giardino del Borgo
    PATH_HALF = 1.2        # metà larghezza dei due camminamenti incrociati
    PATH_TOP = 0.18        # quota del piano dei camminamenti
    CLEARANCE = 0.35       # distanza minima fra bordo dell'aiuola e ciglio
    CURB_INNER = 12.61     # filo interno del cordolo di perimetro (12,7 - 0,09)
    POND = (-60.0, 44.0)   # centro del laghetto, dentro il Parco delle Rose
    POND_RADIUS = 4.60     # bacino più la corona di massi di sponda
    FOUNTAIN_RADIUS = 1.15

    @classmethod
    def setUpClass(cls):
        cls.B = batches()
        city.build_trees_and_park(cls.B, defaultdict(lambda: None), None, None)

    @staticmethod
    def in_park(cx, cy, center):
        """Vero se il pezzo è di quel parco: i due prati distano 104 m."""
        return max(abs(center[0] - cx), abs(center[1] - cy)) <= 14.0

    def park_calls(self, key, shape, cx, cy):
        return [call for call in pick(self.B[key].calls, shape)
                if self.in_park(cx, cy, call["center"])]

    def beds(self, cx, cy):
        """Le quattro aiuole di un parco, come (dx, dy, larghezza, profondità)."""
        return [(call["center"][0] - cx, call["center"][1] - cy,
                 call["size"][0], call["size"][1])
                for call in self.park_calls("curb", "box", cx, cy)
                if abs(call["size"][2] - 0.25) < 1e-9
                and abs(call["center"][2] - 0.205) < 1e-9]

    def benches(self, cx, cy):
        return [spans(call["center"], (2.30, 0.55, 0.12))
                for call in self.park_calls("wood", "box", cx, cy)]

    def bollards(self, cx, cy):
        return [call["center"] for call in
                pick(self.B["metal"].calls, "cylinder", radius=0.075, depth=0.72)
                if self.in_park(cx, cy, call["center"])]

    def test_quattro_aiuole_per_parco_con_lo_stesso_ingombro(self):
        for cx, cy in self.PARKS:
            with self.subTest(parco=(cx, cy)):
                beds = self.beds(cx, cy)
                self.assertEqual(len(beds), 4)
                sizes = sorted((round(bw, 2), round(bd, 2)) for _dx, _dy, bw, bd in beds)
                self.assertEqual(sizes, [(1.45, 5.0), (1.45, 5.0),
                                         (5.0, 1.45), (5.0, 1.45)])
                # Dalla venticinquesima versione il cordolo è piantato nel
                # prato: il bordo resta fra 0,080 e 0,330 m.
                self.assertTrue(all(abs(bd - 5.0) < 1e-9 or abs(bw - 5.0) < 1e-9
                                    for _dx, _dy, bw, bd in beds))

    def test_le_aiuole_sono_fuori_da_entrambi_i_camminamenti(self):
        for cx, cy in self.PARKS:
            with self.subTest(parco=(cx, cy)):
                for dx, dy, bw, bd in self.beds(cx, cy):
                    with self.subTest(aiuola=(dx, dy)):
                        # La croce è l'unione di due fasce larghe 2,40 m che
                        # attraversano il parco da parte a parte: un'aiuola è
                        # fuori solo se è fuori da tutte e due.
                        self.assertGreaterEqual(
                            abs(dy) - bd / 2 - self.PATH_HALF, self.CLEARANCE)
                        self.assertGreaterEqual(
                            abs(dx) - bw / 2 - self.PATH_HALF, self.CLEARANCE)

    def test_le_aiuole_restano_dentro_il_cordolo_di_perimetro(self):
        for cx, cy in self.PARKS:
            with self.subTest(parco=(cx, cy)):
                for dx, dy, bw, bd in self.beds(cx, cy):
                    with self.subTest(aiuola=(dx, dy)):
                        self.assertLessEqual(abs(dx) + bw / 2, self.CURB_INNER)
                        self.assertLessEqual(abs(dy) + bd / 2, self.CURB_INNER)
                        # Restano nel quadrante periferico, non addossate
                        # all'incrocio: dodici metri dal centro del parco.
                        self.assertGreater(abs(dx) + abs(dy), 11.0)

    def test_le_aiuole_non_toccano_panchine_paletti_e_laghetto(self):
        for cx, cy in self.PARKS:
            with self.subTest(parco=(cx, cy)):
                benches = self.benches(cx, cy)
                bollards = self.bollards(cx, cy)
                self.assertEqual(len(benches), 3)
                self.assertEqual(len(bollards), 4)
                for dx, dy, bw, bd in self.beds(cx, cy):
                    with self.subTest(aiuola=(dx, dy)):
                        bed = spans((cx + dx, cy + dy, 0.205), (bw, bd, 0.25))
                        for bench in benches:
                            self.assertFalse(overlaps_xy(bed, bench),
                                             "aiuola dentro una panca")
                        for center in bollards:
                            self.assertGreaterEqual(clearance_xy(bed, center), 0.20)
                        if (cx, cy) == self.PARKS[0]:
                            self.assertGreaterEqual(
                                clearance_xy_circle(bed, self.POND, self.POND_RADIUS),
                                0.15)

    def test_la_lavanda_segue_l_asse_lungo_dell_aiuola(self):
        for cx, cy in self.PARKS:
            with self.subTest(parco=(cx, cy)):
                total = [call["center"] for call in
                         pick(self.B["leaf_light"].calls, "sphere")
                         if self.in_park(cx, cy, call["center"])]
                self.assertEqual(len(total), 4 * 7)   # quattro aiuole, sette a testa
                for dx, dy, bw, bd in self.beds(cx, cy):
                    with self.subTest(aiuola=(dx, dy)):
                        near = [center for center in total
                                if abs(center[0] - (cx + dx)) <= bw / 2 + 0.30
                                and abs(center[1] - (cy + dy)) <= bd / 2 + 0.30]
                        self.assertEqual(len(near), 7)
                        for center in near:
                            self.assertLessEqual(abs(center[0] - (cx + dx)), bw / 2 - 0.20)
                            self.assertLessEqual(abs(center[1] - (cy + dy)), bd / 2 - 0.20)
                            # Gli arbusti appoggiano sul cordolo dell'aiuola,
                            # piantata nel prato: centro a quota 0,61 m.
                            self.assertAlmostEqual(center[2], 0.61)

    def test_la_fontanella_lascia_libero_l_incrocio(self):
        fountains = [call["center"] for call in
                     pick(self.B["concrete"].calls, "cylinder",
                          radius=self.FOUNTAIN_RADIUS)]
        # Una sola fontanella: quella del Parco delle Rose.
        self.assertEqual(len(fountains), 1)
        cx, cy = self.PARKS[0]
        fx, fy = fountains[0][0], fountains[0][1]
        self.assertNotAlmostEqual(fx, cx)
        self.assertNotAlmostEqual(fy, cy)
        self.assertGreaterEqual(
            abs(fx - cx) - self.FOUNTAIN_RADIUS - self.PATH_HALF, 0.60)
        self.assertGreaterEqual(
            abs(fy - cy) - self.FOUNTAIN_RADIUS - self.PATH_HALF, 0.60)
        # Resta dentro il parco e lontana dal laghetto, dalle aiuole e dai paletti.
        self.assertLess(abs(fx - cx) + self.FOUNTAIN_RADIUS, self.CURB_INNER)
        self.assertLess(abs(fy - cy) + self.FOUNTAIN_RADIUS, self.CURB_INNER)
        self.assertGreater(math.hypot(fx - self.POND[0], fy - self.POND[1]),
                           self.FOUNTAIN_RADIUS + self.POND_RADIUS)
        fountain = spans((fx, fy, 0.38), (2 * self.FOUNTAIN_RADIUS,
                                          2 * self.FOUNTAIN_RADIUS, 0.60))
        for dx, dy, bw, bd in self.beds(cx, cy):
            bed = spans((cx + dx, cy + dy, 0.205), (bw, bd, 0.25))
            self.assertFalse(overlaps_xy(bed, fountain))
        for center in self.bollards(cx, cy):
            self.assertGreater(clearance_xy(fountain, center), 0.20)
        # Vasca, acqua e colonnina conservano le quote di prima.
        self.assertAlmostEqual(fountains[0][2], 0.38)
        water = pick(self.B["water"].calls, "cylinder", radius=0.90)
        self.assertEqual(len(water), 1)
        self.assertAlmostEqual(water[0]["center"][2], 0.70)
        self.assertAlmostEqual(water[0]["center"][0], fx)
        self.assertAlmostEqual(water[0]["center"][1], fy)


class CaffeTests(unittest.TestCase):
    """La platea del chiosco poggia sul lastricato della piazza."""

    PAVING_TOP = 0.2125        # piano delle lastre della piazza
    FLOOR = 0.55               # quota di calpestio del chiosco
    NAME = "Gazebo caffè — pavimento"

    @classmethod
    def setUpClass(cls):
        cls.B = batches()
        with recorded_cubes() as make_cube:
            city.build_town_square(cls.B, defaultdict(lambda: None), None)
            cls.platform = cubes_named(make_cube, cls.NAME)

    def test_la_platea_scende_dentro_la_pavimentazione(self):
        self.assertEqual(len(self.platform), 1)
        call = self.platform[0]
        _name, location, size = call.args[:3]
        bottom = location[2] - size[2] / 2
        top = location[2] + size[2] / 2
        self.assertLessEqual(bottom, self.PAVING_TOP)     # non più sospesa
        self.assertGreaterEqual(bottom, -0.05)            # senza affondare nel suolo
        self.assertAlmostEqual(top, self.FLOOR)           # calpestio invariato
        self.assertAlmostEqual(top, city.CAFFE_FLOOR_Z)

    def test_ingombro_e_posizione_del_chiosco_invariati(self):
        call = self.platform[0]
        _name, location, size = call.args[:3]
        self.assertEqual(tuple(location[:2]), (0.0, -11.4))
        self.assertAlmostEqual(size[0], 5.2)
        self.assertAlmostEqual(size[1], 3.8)
        self.assertAlmostEqual(call.kwargs.get("bevel", 0.0), 0.04)

    def test_tavoli_e_sedie_restano_sul_calpestio(self):
        # Piani dei tavolini a 0,55 + 0,76 m: bordo superiore a 1,31 m.
        tops = [call["center"] for call in
                pick(self.B["wood_light"].calls, "cylinder", radius=0.53)]
        self.assertEqual(len(tops), len(city.CAFFE_TABLES))
        for center in tops:
            self.assertAlmostEqual(center[2], self.FLOOR + 0.76 - 0.06)
            self.assertGreater(center[2] - 0.06, self.PAVING_TOP)
        # Sedute a 46 cm dal calpestio del chiosco, non dal lastricato.
        self.assertAlmostEqual(city.CAFFE_FLOOR_Z, self.FLOOR)
        self.assertEqual(len(city.CAFFE_CHAIRS), 4)


class PontileTests(unittest.TestCase):
    """I pali del pontile sorreggono il tavolato senza spuntarvi sopra."""

    CX, CY = city.POND_CENTER
    DECK_BOTTOM, DECK_TOP = 0.20, 0.28
    PILE_RADIUS = 0.06

    @classmethod
    def setUpClass(cls):
        cls.B = batches()
        city.build_pond(cls.B, cls.CX, cls.CY)

    def deck(self):
        return [spans(call["center"], call["size"])
                for call in pick(self.B["wood_light"].calls, "box")
                if abs(call["size"][2] - 0.08) < 1e-9
                and abs(call["center"][2] - 0.24) < 1e-9]

    def piles(self):
        return [(call["center"], call["radius"], call["depth"]) for call in
                pick(self.B["wood"].calls, "cylinder", radius=self.PILE_RADIUS)]

    def test_il_tavolato_resta_quello_di_prima(self):
        deck = self.deck()
        self.assertEqual(len(deck), 4)
        xs = [s[0] for s in deck]
        ys = [s[1] for s in deck]
        zs = [s[2] for s in deck]
        self.assertAlmostEqual(min(x[0] for x in xs), self.CX + 3.12)
        self.assertAlmostEqual(max(x[1] for x in xs), self.CX + 4.68)
        self.assertAlmostEqual(min(y[0] for y in ys), self.CY - 2.65)
        self.assertAlmostEqual(max(y[1] for y in ys), self.CY - 0.95)
        for z in zs:
            self.assertAlmostEqual(z[0], self.DECK_BOTTOM)
            self.assertAlmostEqual(z[1], self.DECK_TOP)

    def test_i_pali_non_spuntano_sopra_le_tavole(self):
        piles = self.piles()
        self.assertEqual(len(piles), 4)
        deck = self.deck()
        deck_x = (min(s[0][0] for s in deck), max(s[0][1] for s in deck))
        deck_y = (min(s[1][0] for s in deck), max(s[1][1] for s in deck))
        for center, radius, depth in piles:
            with self.subTest(palo=(round(center[0], 2), round(center[1], 2))):
                top = center[2] + depth / 2
                bottom = center[2] - depth / 2
                self.assertLessEqual(top, self.DECK_TOP)         # niente ceppi
                self.assertGreaterEqual(top, self.DECK_BOTTOM)   # regge il tavolato
                self.assertLessEqual(bottom, -0.25)              # infisso nel fondo
                self.assertGreaterEqual(center[0] - radius, deck_x[0] - 1e-9)
                self.assertLessEqual(center[0] + radius, deck_x[1] + 1e-9)
                self.assertGreaterEqual(center[1] - radius, deck_y[0] - 1e-9)
                self.assertLessEqual(center[1] + radius, deck_y[1] + 1e-9)

    def test_il_ponte_e_il_bacino_sono_invariati(self):
        # Acqua a 0,14-0,20 m e cordolo ad anello: nessuna quota toccata.
        water = pick(self.B["water"].calls, "cylinder", radius=3.85)
        self.assertEqual(len(water), 1)
        self.assertAlmostEqual(water[0]["center"][2], 0.17)
        rims = pick(self.B["curb"].calls, "ring")
        self.assertEqual(len(rims), 1)
        self.assertAlmostEqual(rims[0]["radius"], 4.25)
        self.assertAlmostEqual(rims[0]["tube"], 0.15)


class MeshTests(unittest.TestCase):
    def test_mesh_parchi_caffe_e_laghetto_valide(self):
        cases = (("build_trees_and_park", (defaultdict(lambda: None), None, None)),
                 ("build_pond", city.POND_CENTER),
                 ("build_town_square", (defaultdict(lambda: None), None)))
        for function, args in cases:
            with self.subTest(function=function):
                group = batches()
                with recorded_cubes():
                    getattr(city, function)(group, *args)
                self.assertTrue(group)
                for batch in group.values():
                    self.assertEqual(len(batch.faces), len(batch.smooth))
                    self.assertTrue(all(math.isfinite(c)
                                        for v in batch.verts for c in v))
                    for face in batch.faces:
                        self.assertGreaterEqual(len(face), 3)
                        self.assertTrue(all(0 <= i < len(batch.verts)
                                            for i in face))


if __name__ == "__main__":
    unittest.main()
