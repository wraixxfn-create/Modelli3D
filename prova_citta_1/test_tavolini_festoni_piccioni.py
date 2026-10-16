"""Tre interventi della versione 27: test geometrici senza dipendenze Blender."""
import __future__
import ast
from collections import defaultdict
import math
from pathlib import Path
import random
import unittest
from unittest.mock import Mock, patch


def load_geometry():
    tree = ast.parse(Path(__file__).with_name("genera_citta.py").read_text())
    functions = {"Batch", "make_cafe_table", "build_street_life", "surface_z", "lbox_point"}
    # Le costanti del generatore non accedono a Blender; si tengono soltanto
    # quelle necessarie alla classificazione delle superfici.
    constants = {"ROAD_X", "ROAD_Y", "VIALE_SPANS", "ROAD_WIDTH", "VIALE_WIDTH",
                 "SIDEWALK_REACH", "MOWN_BLOCKS", "PRIVATE_GARDENS", "PARKS",
                 "PLAYGROUND_CENTER", "PLAYGROUND_DECK", "ROAD_TOP", "SIDEWALK_TOP",
                 "LAWN_Z", "PARK_LAWN_Z", "GARDEN_Z", "PIAZZA_Z", "PIAZZA_RING_Z",
                 "MAT_Z", "RELIEF_Z"}
    tree.body = [node for node in tree.body
                 if (isinstance(node, (ast.FunctionDef, ast.ClassDef))
                     and node.name in functions)
                 or (isinstance(node, ast.Assign) and any(
                     isinstance(t, ast.Name) and t.id in constants for t in node.targets))]
    scope = {"math": math, "random": random, "PI": math.pi, "TAU": math.tau}
    for name in ("add_tube", "add_person", "add_bicycle", "add_scooter", "add_van",
                 "add_waste_container", "build_newsstand", "add_balcony_laundry"):
        scope[name] = Mock()
    exec(compile(tree, "genera_citta.py", "exec",
                 flags=__future__.annotations.compiler_flag, dont_inherit=True), scope)
    return scope


city = load_geometry()
COLORS = ("cloth_red", "cloth_blue", "cloth_green", "cloth_yellow",
          "cloth_violet", "cloth_white")


def batches():
    return defaultdict(lambda: city["Batch"]("Test", None, None))


def street_life():
    group = batches()
    tubes = Mock()
    with patch.dict(city, add_tube=tubes):
        city["build_street_life"](group, {}, None)
    return group, tubes.call_args_list


class TavoliniTests(unittest.TestCase):
    def test_base_a_croce_poggia_sul_pavimento(self):
        for floor in (0.0, 0.55, 1.7):
            group = batches()
            city["make_cafe_table"](group, 7, -4, floor)
            feet = group["metal"].verts[-32:]
            self.assertAlmostEqual(min(v[2] for v in feet), floor)
            self.assertAlmostEqual(max(v[2] for v in feet), floor + .06)

    def test_quattro_bracci_connessi_al_fusto(self):
        group = batches()
        with patch.object(group["metal"], "box", wraps=group["metal"].box) as boxes:
            city["make_cafe_table"](group, 7, -4, .55)
        self.assertEqual(boxes.call_count, 4)
        for call in boxes.call_args_list:
            (x, y, z), (length, width, height), angle = call.args
            # L'estremità interna di ciascun braccio coincide con l'asse.
            self.assertAlmostEqual(x - length / 2 * math.cos(angle), 7)
            self.assertAlmostEqual(y - length / 2 * math.sin(angle), -4)
            self.assertGreater(height, 0)
            self.assertGreater(width, 0)
            self.assertLess(z, .55 + .64)  # sotto la sommità del fusto

    def test_piano_e_altezza_invariati(self):
        group = batches()
        city["make_cafe_table"](group, 0, 0, .55)
        self.assertAlmostEqual(max(v[2] for v in group["wood_light"].verts), 1.31)
        self.assertAlmostEqual(max(v[2] for v in group["metal"].verts), 1.19)


class FestoniTests(unittest.TestCase):
    def setUp(self):
        self.group, tubes = street_life()
        self.cables = [c.args[1] for c in tubes if c.args[2] == .01]
        self.flags = [tuple(self.group[k].verts[i] for i in face)
                      for k in COLORS for face in self.group[k].faces if len(face) == 3]

    def test_tre_cavi_continui_con_attacchi_e_freccia(self):
        self.assertEqual(len(self.cables), 3)
        for points in self.cables:
            self.assertEqual(len(points), 17)
            self.assertAlmostEqual(points[0][2], 5.3)
            self.assertAlmostEqual(points[-1][2], 5.3)
            self.assertAlmostEqual(points[8][2], 4.45)
            self.assertTrue(all(math.dist(p, q) > 0 for p, q in zip(points, points[1:])))

    def test_ventiquattro_bandierine_con_superficie_reale(self):
        self.assertEqual(len(self.flags), 24)
        for a, b, tip in self.flags:
            self.assertAlmostEqual(math.dist(a[:2], b[:2]), .36)
            self.assertAlmostEqual((a[2] + b[2]) / 2 - tip[2], .42)
            self.assertAlmostEqual(tip[0], (a[0] + b[0]) / 2)
            self.assertAlmostEqual(tip[1], (a[1] + b[1]) / 2)

    def test_orli_superiori_attaccati_ai_cavi_in_entrambe_le_direzioni(self):
        def on_segment(v, p, q):
            delta = [q[j] - p[j] for j in range(3)]
            axis = max(range(3), key=lambda j: abs(delta[j]))
            t = (v[axis] - p[axis]) / delta[axis]
            return 0 <= t <= 1 and all(
                abs(v[j] - p[j] - t * delta[j]) < 1e-9 for j in range(3))
        for a, b, _ in self.flags:
            self.assertTrue(any(on_segment(a, p, q) and on_segment(b, p, q)
                                for cable in self.cables for p, q in zip(cable, cable[1:])))


class PiccioniTests(unittest.TestCase):
    def test_otto_corpi_fuori_dal_lastricato(self):
        group, _ = street_life()
        # Batch.poly duplica i quattro vertici di ciascuna delle 8 * 5 facce.
        verts = group["bird"].verts[:8 * 320]
        self.assertEqual(len(verts), 2560)
        for i in range(0, len(verts), 320):
            body = verts[i:i + 160]
            x = sum(v[0] for v in body) / 160
            y = sum(v[1] for v in body) / 160
            floor = city["surface_z"](x, y)
            self.assertAlmostEqual(min(v[2] for v in body), floor + .06)

    def test_zampe_collegate_e_piedi_sul_piano(self):
        group, tubes = street_life()
        legs = [c.args[1] for c in tubes if c.args[0] is group["beak"] and c.args[2] == .009]
        feet = [c.args[1] for c in tubes if c.args[0] is group["beak"] and c.args[2] == .007]
        self.assertEqual(len(legs), 16)
        self.assertEqual(len(feet), 16)
        for leg, foot in zip(legs, feet):
            floor = city["surface_z"](*leg[0][:2])
            self.assertAlmostEqual(foot[0][2] - .007, floor)
            self.assertLess(leg[0][2], foot[0][2] + .007)
            self.assertGreater(leg[-1][2], floor + .06)  # dentro il corpo

    def test_becchi_lungo_x_collegati_alla_testa(self):
        group = batches()
        with patch.object(group["beak"], "cone", wraps=group["beak"].cone) as beaks:
            city["build_street_life"](group, {}, None)
        self.assertEqual(beaks.call_count, 8)
        for call in beaks.call_args_list:
            center, radius, tip_radius, depth, _ = call.args
            self.assertEqual(call.kwargs["axis"], "X")
            self.assertEqual(tip_radius, 0)
            # La base del becco rientra nel raggio della testa, non resta sospesa.
            self.assertLess(.195 - depth / 2, .12 + .055)
            self.assertAlmostEqual(center[2], city["surface_z"](center[0] - .195, center[1]) + .24)


if __name__ == "__main__":
    unittest.main()
