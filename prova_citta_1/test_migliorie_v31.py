"""Esattamente tre migliorie della trentunesima versione; non richiede Blender.

Le funzioni reali sono estratte dal generatore via AST e le primitive vengono
verificate con `Batch`: non si apre né si sovrascrive `citta.blend`.

1. L'edicola del giornalaio si libera dal lampione d'angolo di levante: dopo
   il trentesimo intervento il palo le era piantato dentro, dal basamento
   alla copertura. Ora risale lungo lo stesso marciapiede verso la piazza.
2. I cartelli direzionali PIAZZA e CENTRO escono dal centro delle carreggiate
   di via ±23 e tornano sui marciapiedi, con il piede a filo del pavimento.
3. L'insegna del caffè, prima testo sospeso nel vuoto fra la platea e la
   gronda, poggia su un cartello ligneo appeso alla gronda con due tiranti.
"""
from __future__ import annotations

import ast
import __future__
from collections import defaultdict
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


FUNCTIONS = {
    "Batch", "lbox", "lbox_tilt", "lbox_point", "surface_z",
    "build_town_square", "build_newsstand", "build_crosswalk_signals",
}
CONSTANTS = {
    "ROAD_X", "ROAD_Y", "VIALE_SPANS", "ROAD_WIDTH", "VIALE_WIDTH",
    "SIDEWALK_REACH", "MOWN_BLOCKS", "PRIVATE_GARDENS", "PARKS",
    "PLAYGROUND_CENTER", "PLAYGROUND_DECK", "ROAD_TOP", "SIDEWALK_TOP",
    "LAWN_Z", "PARK_LAWN_Z", "GARDEN_Z", "PIAZZA_Z", "PIAZZA_RING_Z",
    "MAT_Z", "RELIEF_Z", "CAFFE_FLOOR_Z", "CAFFE_TABLES", "CAFFE_CHAIRS",
    "CROSSWALK_JUNCTIONS", "SIGNAL_CORNER_OFFSET",
}


def load_geometry():
    tree = ast.parse(Path(__file__).with_name("genera_citta.py").read_text())
    tree.body = [node for node in tree.body
                 if (isinstance(node, (ast.FunctionDef, ast.ClassDef))
                     and node.name in FUNCTIONS)
                 or (isinstance(node, ast.Assign) and any(
                     isinstance(target, ast.Name) and target.id in CONSTANTS
                     for target in node.targets))]
    scope = {
        "math": math, "random": __import__("random"),
        "PI": math.pi, "TAU": math.tau,
        # Estranee ai tre interventi: intercettate dove servono i richiami.
        "make_cube": Mock(), "add_text": Mock(), "add_tube": Mock(),
        "make_bench": Mock(), "make_cafe_table": Mock(),
        "make_cafe_chair": Mock(), "add_person": Mock(),
        "add_lamp": Mock(), "build_crosswalk_signal": Mock(),
    }
    code = compile(tree, "genera_citta.py", "exec",
                   flags=__future__.annotations.compiler_flag, dont_inherit=True)
    exec(code, scope)
    return scope, SimpleNamespace(**scope)


scope, city = load_geometry()


class RecordingBatch(city.Batch):
    """`Batch` che annota anche le primitive, per poterle verificare."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []

    def box(self, center, size, yaw=0.0):
        self.calls.append({"kind": "box", "center": center, "size": size})
        return super().box(center, size, yaw)

    def cylinder(self, center, radius, depth, segments=16, axis="Z", radius2=None):
        self.calls.append({"kind": "cylinder", "center": center,
                           "radius": radius, "depth": depth})
        return super().cylinder(center, radius, depth, segments, axis, radius2)


def batches():
    return defaultdict(lambda: RecordingBatch("Test", None, None))


def plan_bounds(group, extra_points=()):
    """Ingombro in pianta di tutti i batch, con eventuali tubi annotati."""
    points = [v for batch in group.values() for v in batch.verts]
    points.extend(extra_points)
    return (min(p[0] for p in points), max(p[0] for p in points),
            min(p[1] for p in points), max(p[1] for p in points))


def point_rect_distance(x, y, rect):
    """Distanza fra un punto e un rettangolo in pianta (0 se interno)."""
    x0, x1, y0, y1 = rect
    dx = max(x0 - x, 0.0, x - x1)
    dy = max(y0 - y, 0.0, y - y1)
    return math.hypot(dx, dy)


def rects_disjoint(a, b):
    return a[1] < b[0] or a[0] > b[1] or a[3] < b[2] or a[2] > b[3]


# --- Costruzione una tantum delle geometrie dei tre interventi ---------------

# 1. Edicola con le posizioni di default del generatore.
kiosk = batches()
kiosk_tubes = []


def record_kiosk_tube(batch, points, radius, segments=8):
    kiosk_tubes.extend(tuple(p) for p in points)


with patch.dict(scope, add_tube=record_kiosk_tube):
    city.build_newsstand(kiosk, defaultdict(lambda: None), None)
KIOSK_RECT = plan_bounds(kiosk, kiosk_tubes)
KIOSK_BASE = [c for c in kiosk["concrete"].calls if c["kind"] == "box"][0]

# 2. Lampioni reali della piazza, per il confronto con l'edicola e i cartelli.
lamps = []
square = batches()


def record_lamp(_b, x, y, height=5.0, ornate=False, yaw=0.0):
    lamps.append((x, y))


with patch.dict(scope, add_lamp=record_lamp):
    city.build_town_square(square, defaultdict(lambda: None), None)

# 3. Cartelli direzionali, isolati dai semafori (mockati in scope).
signs = batches()
scope["add_text"].reset_mock()
with patch.dict(scope, add_tube=Mock()):
    city.build_crosswalk_signals(signs, defaultdict(lambda: None), None)
SIGN_TEXTS = list(scope["add_text"].call_args_list)
SIGN_POLES = [c for c in signs["metal"].calls
              if c["kind"] == "cylinder" and c["radius"] == 0.065]
SIGN_BOARDS = [c for c in signs["blue"].calls if c["kind"] == "box"]

# 4. Cartello e tiranti dell'insegna del caffè.
scope["add_text"].reset_mock()
scope["add_tube"].reset_mock()
city.build_town_square(batches(), defaultdict(lambda: None), None)
CAFFE_TEXTS = list(scope["add_text"].call_args_list)
TUBES = list(scope["add_tube"].call_args_list)


class EdicolaLampioneTests(unittest.TestCase):
    """Miglioria 1: l'edicola e il lampione d'angolo non si occupano più."""

    def test_il_lampione_non_e_piu_dentro_ledicola(self):
        # Il palo del lampione di levante era nel vano di vendita: adesso
        # nessun lampione tocca nemmeno di sfioro l'ingombro dell'edicola.
        self.assertEqual(len(lamps), 12)
        for x, y in lamps:
            with self.subTest(lampione=(x, y)):
                self.assertGreater(point_rect_distance(x, y, KIOSK_RECT), 0.35,
                                   "il lampione tocca l'edicola")
        # Quello che ci stava dentro è ora a più di un metro dal tendone.
        self.assertGreater(point_rect_distance(17.75, -19.0, KIOSK_RECT), 1.0)

    def test_ledicola_resta_sullo_stesso_marciapiede_verso_la_piazza(self):
        cx, cy = KIOSK_BASE["center"][0], KIOSK_BASE["center"][1]
        # Stesso filo di prima (x = 17,2) e quota del marciapiede di via 23.
        self.assertAlmostEqual(cx, 17.2, places=6)
        self.assertAlmostEqual(cy, -15.9, places=6)
        self.assertAlmostEqual(city.surface_z(cx, cy), city.SIDEWALK_TOP,
                               places=9)
        # Risale verso la piazza, non scende verso l'incrocio.
        x0, x1, y0, y1 = KIOSK_RECT
        self.assertLess(cy, -14.0)
        self.assertGreater(cy, -18.0)
        self.assertLess(y1, -13.9)     # libera dal basamento della piazza

    def test_ledicola_fuori_dalla_carreggiata_e_dal_nodo_semaforico(self):
        x0, x1, y0, y1 = KIOSK_RECT
        # Via 23: la carreggiata comincia a x = 19 e va fino a x = 27.
        self.assertLess(x1, 19.0 - 0.20)
        # Libera dalla rampa d'angolo e dalla zebra del nodo (23, -32).
        ramp = (23 - 4.125 - 2.25, 23 - 4.125, -32 + 4.125, -32 + 4.125 + 2.25)
        zebra = (23 - 8 / 2, 23 + 8 / 2, -26.65 - 1.4, -26.65 + 1.4)
        for name, rect in (("rampa", ramp), ("zebra", zebra)):
            with self.subTest(vincolo=name):
                self.assertTrue(rects_disjoint(KIOSK_RECT, rect),
                                "l'edicola invade " + name)


class CartelliTests(unittest.TestCase):
    """Miglioria 2: i cartelli direzionali non stanno più in carreggiata."""

    def test_i_cartelli_sui_marciapiedi_non_in_carreggiata(self):
        self.assertEqual(len(SIGN_POLES), 2)
        for c in SIGN_POLES:
            x, y = c["center"][0], c["center"][1]
            with self.subTest(cartello=(x, y)):
                # Fuori dalle carreggiate di via ±23 (mezzeria a x = ±23).
                self.assertGreater(abs(abs(x) - 23.0), city.ROAD_WIDTH / 2)
                # Sulla superficie del marciapiede, non sull'asfalto.
                self.assertAlmostEqual(city.surface_z(x, y), city.SIDEWALK_TOP,
                                       places=9)

    def test_il_piede_del_palo_poggia_sul_pavimento(self):
        for c in SIGN_POLES:
            x, y, z = c["center"]
            with self.subTest(palo=(x, y)):
                bottom = z - c["depth"] / 2
                self.assertAlmostEqual(bottom, city.SIDEWALK_TOP, places=6)

    def test_cartelli_e_testi_sui_pali(self):
        self.assertEqual(len(SIGN_BOARDS), 2)
        for c in SIGN_BOARDS:
            (x, y, z), (sx, sy, sz) = c["center"], c["size"]
            pole = next(p for p in SIGN_POLES
                        if abs(p["center"][0] - x) < 1e-9)
            self.assertAlmostEqual(y, pole["center"][1], places=9)
            self.assertAlmostEqual(sx, 1.55, places=9)
            self.assertAlmostEqual(sz, 0.56, places=9)
            self.assertGreater(z, 3.0)     # cartello sopra l'orizzonte visivo
        bodies = {c.args[0]: c.args[2] for c in SIGN_TEXTS}
        self.assertEqual(set(bodies), {"PIAZZA", "CENTRO"})
        for body, position in bodies.items():
            x = -17.75 if body == "PIAZZA" else 17.75
            with self.subTest(testo=body):
                self.assertAlmostEqual(position[0], x, places=9)
                self.assertAlmostEqual(position[1], -19.93, places=9)

    def test_cartelli_liberi_dai_lampioni(self):
        for c in SIGN_POLES:
            px, py = c["center"][0], c["center"][1]
            for lx, ly in lamps:
                with self.subTest(palo=(px, py), lampione=(lx, ly)):
                    self.assertGreater(math.hypot(px - lx, py - ly), 0.5)


class InsegnaCaffeTests(unittest.TestCase):
    """Miglioria 3: l'insegna del caffè poggia su un cartello appeso."""

    @staticmethod
    def boards():
        return [c for c in square["wood_light"].calls if c["kind"] == "box"]

    def find_caffe_text(self):
        texts = [c for c in CAFFE_TEXTS if c.args[0] == "CAFFÈ DEL BORGO"]
        self.assertEqual(len(texts), 1)
        return texts[0]

    def test_linsegna_non_fluttua_piu_nel_vuoto(self):
        text = self.find_caffe_text()
        tx, ty, tz = text.args[2]
        boards = self.boards()
        self.assertEqual(len(boards), 1)
        (bx, by, bz), (sx, sy, sz) = boards[0]["center"], boards[0]["size"]
        # Il testo resta alla stessa quota e in asse con il cartello.
        self.assertAlmostEqual(tx, bx, places=9)
        self.assertAlmostEqual(tz, bz, places=9)
        self.assertGreaterEqual(sx, 2.5)          # regge tutta la scritta
        self.assertGreaterEqual(sz, 0.50)
        # Le lettere stanno appena davanti alla faccia del cartello.
        front = by - sy / 2
        self.assertGreater(front - ty, 0.01)
        self.assertLess(front - ty, 0.08)

    def test_il_cartello_e_appeso_alla_gronda(self):
        hangers = [c for c in TUBES
                   if c.args[2] == 0.028 and len(c.args[1]) == 2]
        self.assertEqual(len(hangers), 2)
        (bx, by, bz), (_sx, _sy, sz) = (
            self.boards()[0]["center"], self.boards()[0]["size"])
        top = bz + sz / 2
        for call in hangers:
            (x0, y0, z0), (x1, y1, z1) = call.args[1]
            with self.subTest(tirante=x0):
                self.assertAlmostEqual(x0, x1, places=9)
                self.assertAlmostEqual(y0, by, places=9)
                self.assertAlmostEqual(abs(x0), 1.50, places=9)
                # La sommità è dentro il sottotetto della gronda (3,595-3,845)
                # e il piede tocca la sommità del cartello.
                self.assertGreaterEqual(max(z0, z1), 3.60)
                self.assertLessEqual(max(z0, z1), 3.845)
                self.assertLessEqual(min(z0, z1), top)
                self.assertGreater(min(z0, z1), top - 0.06)


if __name__ == "__main__":
    unittest.main()
