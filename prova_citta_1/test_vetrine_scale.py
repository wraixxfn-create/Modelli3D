"""Tre migliorie della versione 17 su vetrate e corpi scala, senza Blender.

Le funzioni geometriche sono estratte dal generatore via AST, come negli altri
test leggeri della città. Ogni scatola `lbox` produce sei facce: i conteggi
per materiale verificano quante scatole finiscono in ciascuna batch.
Nessun file .blend viene aperto o modificato.
"""
from __future__ import annotations

from collections import defaultdict
import __future__
import ast
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


FACES_PER_BOX = 6


def load_geometry():
    source = Path(__file__).with_name("genera_citta.py").read_text()
    names = {"Batch", "lbox", "add_shop_awning", "_apartment_ground_floor",
             "_apartment_elevator_shaft"}
    tree = ast.parse(source)
    tree.body = [node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                 and node.name in names]
    scope = {"math": math, "PI": math.pi, "TAU": math.tau,
             "add_tube": Mock(), "add_text": Mock()}
    try:
        import bpy
    except ImportError:
        pass
    else:
        scope["bpy"] = bpy
    import collections.abc
    scope.setdefault("collections", collections)
    # Le annotazioni di `Batch` citano `bpy.types`: come stringhe non vengono
    # valutate, quindi il caricamento funziona anche senza Blender.
    code = compile(tree, "genera_citta.py", "exec",
                   flags=__future__.annotations.compiler_flag, dont_inherit=True)
    exec(code, scope)
    return scope, SimpleNamespace(**scope)


scope, city = load_geometry()


def batches():
    return defaultdict(lambda: city.Batch("Test", None, None))


def count_boxes(batch):
    return len(batch.faces) // FACES_PER_BOX


def assert_valid(test, group):
    for batch in group.values():
        test.assertEqual(len(batch.faces), len(batch.smooth))
        test.assertTrue(all(math.isfinite(c) for p in batch.verts for c in p))
        test.assertTrue(all(0 <= i < len(batch.verts)
                            for face in batch.faces for i in face))


class ElevatorShaftTests(unittest.TestCase):
    FLOORS = 5

    def build(self, yaw=0.0, cx=0.0, cy=0.0):
        B = batches()
        city._apartment_elevator_shaft(B, cx, cy, yaw, 14.0, 11.0,
                                       0.0, 16.0, 3.2, self.FLOORS)
        return B

    def test_glass_is_lit_not_smoked(self):
        B = self.build()
        # Due pannelli vetrati, uno per fianco, illuminati.
        self.assertEqual(count_boxes(B["glass_warm"]), 2)
        # Il vetro fumé non viene più usato per il corpo scala.
        self.assertEqual(len(B["glass"].faces), 0)
        assert_valid(self, B)

    def test_vertical_mullions_divide_each_face(self):
        B = self.build()
        # Per fianco: un vetro, due montanti verticali e un traverso per piano.
        expected_trim = 2 * (2 + self.FLOORS)
        self.assertEqual(count_boxes(B["trim"]), expected_trim)

    def test_mullions_sit_outside_the_glass_plane(self):
        B = self.build()
        # Il vetro sta fra x = 7.02 e 7.12 (width/2 + 0.07 ± 0.05); i montanti
        # sporgono fino a 7.21 (width/2 + 0.13 + 0.08), quindi sono più esterni.
        glass_outer = max(v[0] for v in B["glass_warm"].verts)
        trim_outer = max(v[0] for v in B["trim"].verts)
        self.assertAlmostEqual(glass_outer, 7.12, places=6)
        self.assertAlmostEqual(trim_outer, 7.21, places=6)
        self.assertGreater(trim_outer, glass_outer)

    def test_rotation_keeps_the_shaft_on_its_side(self):
        base = self.build(0.0)
        rotated = self.build(math.pi / 2, 10.0, -4.0)
        for key in ("glass_warm", "trim"):
            self.assertEqual(len(base[key].faces), len(rotated[key].faces))
        assert_valid(self, rotated)


class GroundFloorShopfrontTests(unittest.TestCase):
    SHOP_BAYS = 2  # tre campate: due vetrine e un ingresso vetrato

    def build(self, yaw=0.0, cx=0.0, cy=0.0):
        B = batches()
        mats = defaultdict(lambda: None)
        city._apartment_ground_floor(B, mats, cx, cy, yaw, 18.0, 14.0, -7.0,
                                     ("A", "B", "C"), "Test", None)
        return B

    def test_shop_glass_is_lit(self):
        B = self.build()
        # Due vetrine e l'ingresso vetrato: tre pannelli illuminati.
        self.assertEqual(count_boxes(B["glass_warm"]), 3)
        self.assertEqual(len(B["glass"].faces), 0)
        assert_valid(self, B)

    def test_shop_bays_have_central_mullion(self):
        B = self.build()
        # Per campata: due montanti laterali e due traversi = 4 scatole trim;
        # le due vetrine aggiungono il montante centrale.
        bays = 3
        expected = bays * 4 + self.SHOP_BAYS
        self.assertEqual(count_boxes(B["trim"]), expected)

    def test_rotation_preserves_structure(self):
        base = self.build(0.0)
        rotated = self.build(math.pi / 2, 5.0, 3.0)
        for key in ("glass_warm", "trim"):
            self.assertEqual(len(base[key].faces), len(rotated[key].faces))
        assert_valid(self, rotated)


if __name__ == "__main__":
    unittest.main()
