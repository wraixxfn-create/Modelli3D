"""Esattamente i tre interventi della versione 15; non richiede Blender.

Esegue le funzioni reali estratte via AST; intercetta le polilinee dei tubi
come i test delle versioni 12–14, senza dipendere da mathutils.
"""
import ast
from collections import defaultdict
import math
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


def load_geometry():
    names = {"Batch", "lbox", "lbox_point", "build_street_lamp",
             "build_sandbox", "build_spring_ride"}
    scope = {"math": math, "PI": math.pi, "TAU": math.tau, "add_tube": Mock()}
    try:
        from mathutils import Vector
    except ImportError:
        pass
    else:
        # Con Blender disponibile verifica anche la tessellazione reale.
        names.add("add_tube")
        scope["Vector"] = Vector
    tree = ast.parse(Path(__file__).with_name("genera_citta.py").read_text())
    tree.body = [n for n in tree.body
                 if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    exec(compile(tree, "genera_citta.py", "exec"), scope)
    return scope


city = load_geometry()


def batches():
    return defaultdict(lambda: city["Batch"]("Test", None, None))


def center(vertices):
    return tuple(sum(p[i] for p in vertices) / len(vertices) for i in range(3))


class LampioniTests(unittest.TestCase):
    def test_braccio_lanterna_e_cappello_ruotano_insieme(self):
        for ornate in (False, True):
            for angle in (0, .73, math.pi / 2, math.pi):
                group = batches()
                with patch.object(group["metal"], "cone", wraps=group["metal"].cone) as cap:
                    city["build_street_lamp"](group, 12, -7, yaw=angle, ornate=ornate)
                reach = (.72 if ornate else .50) * .65
                expected = (12 + reach * math.cos(angle), -7 + reach * math.sin(angle))
                for actual in (center(group["lamp"].verts), cap.call_args.args[0]):
                    for got, wanted in zip(actual[:2], expected):
                        self.assertAlmostEqual(got, wanted)
                # Il montante della lanterna occupa lo stesso centro XY.
                for got, wanted in zip(center(group["metal"].verts[80:88])[:2], expected):
                    self.assertAlmostEqual(got, wanted)

    def test_lanterna_intelaiata_con_diffusore_invariato(self):
        group = batches()
        with patch.dict(city, lbox=Mock(wraps=city["lbox"])):
            city["build_street_lamp"](group, 0, 0)
            calls = city["lbox"].call_args_list
        self.assertEqual(len(calls), 8)  # braccio, montante, luce, basetta e 4 angoli
        uprights = [call.args for call in calls[-4:]]
        self.assertEqual(len({(b[4], b[5]) for b in uprights}), 4)
        for b in uprights:
            self.assertAlmostEqual(abs(b[4] - .325), .175)
            self.assertAlmostEqual(abs(b[5]), .17)
            self.assertAlmostEqual(b[9], .36)
        self.assertEqual(len(group["lamp"].faces), 6)
        self.assertAlmostEqual(center(group["lamp"].verts)[0], .325)
        self.assertAlmostEqual(min(v[2] for v in group["lamp"].verts), 4.97)
        self.assertAlmostEqual(max(v[2] for v in group["lamp"].verts), 5.33)

    def test_mesh_lampioni_valide(self):
        assert_valid(self, "build_street_lamp")


class SecchielloTests(unittest.TestCase):
    def test_apertura_cava_e_fondo_sulla_sabbia(self):
        group = batches()
        city["build_sandbox"](group, 0, 0)
        red = group["canvas_red"]
        # Prime 60 facce: esterno, interno e anello del bordo per 20 settori.
        self.assertEqual(len(red.faces[:60]), 60)
        for i in range(20):
            outer, inner, rim = [
                [red.verts[j] for j in f] for f in red.faces[3*i:3*i+3]]
            self.assertEqual({round(p[2], 2) for p in outer}, {.29, .55})
            self.assertEqual({round(p[2], 2) for p in inner}, {.29, .55})
            self.assertTrue(all(abs(p[2] - .55) < 1e-9 for p in rim))
            self.assertTrue(all(math.hypot(p[0] - .7, p[1] + .6) >= .12 - 1e-9
                                for p in rim))
        # Il fondo chiuso tocca il piano superiore della sabbia, quota .28.
        bottom = red.verts[240:360]
        self.assertAlmostEqual(min(p[2] for p in bottom), .28)
        self.assertAlmostEqual(max(p[2] for p in bottom), .30)

    def test_manico_collegato_al_bordo_e_ruotato(self):
        group = batches()
        with patch.dict(city, add_tube=Mock(wraps=city["add_tube"])):
            city["build_sandbox"](group, 4, -3, .73)
            points = city["add_tube"].call_args.args[1]
        self.assertEqual(len(points), 17)
        self.assertAlmostEqual(points[0][2], .55)
        self.assertAlmostEqual(points[-1][2], .55)
        self.assertAlmostEqual(max(p[2] for p in points), .695)
        for point, lx in ((points[0], .845), (points[-1], .555)):
            expected = city["lbox_point"](4, -3, .73, lx, -.6, .55)
            for got, wanted in zip(point, expected):
                self.assertAlmostEqual(got, wanted)

    def test_mesh_sabbiera_valide(self):
        assert_valid(self, "build_sandbox")


class MollaTests(unittest.TestCase):
    def test_spirale_quattro_giri_collegata_ai_supporti(self):
        group = batches()
        with patch.dict(city, add_tube=Mock(wraps=city["add_tube"])):
            city["build_spring_ride"](group, 0, 0)
            calls = city["add_tube"].call_args_list
        spring = [c.args[1] for c in calls if len(c.args[1]) == 97][0]
        self.assertAlmostEqual(spring[0][2], .26)
        self.assertAlmostEqual(spring[-1][2], .58)
        for i, (x, y, z) in enumerate(spring):
            self.assertAlmostEqual(math.hypot(x, y), .10)
            self.assertAlmostEqual(x, .10 * math.cos(i * math.tau / 24))
            self.assertAlmostEqual(y, .10 * math.sin(i * math.tau / 24))
            self.assertAlmostEqual(z, .26 + .32 * i / 96)
        self.assertEqual(calls[0].args[1][-1], spring[0])
        for actual, expected in zip(calls[2].args[1][0], spring[-1]):
            self.assertAlmostEqual(actual, expected)
        self.assertAlmostEqual(min(v[2] for v in group["metal"].verts), .19)

    def test_seduta_impugnature_e_poggiapiedi_nel_riferimento_locale(self):
        base, rotated = batches(), batches()
        with patch.dict(city, add_tube=Mock(wraps=city["add_tube"])):
            city["build_spring_ride"](base, 0, 0)
            original = city["add_tube"].call_args_list[:]
            city["add_tube"].reset_mock()
            city["build_spring_ride"](rotated, 12, -7, .73)
            transformed = city["add_tube"].call_args_list
        self.assertEqual(len(original), 6)
        for first, second in zip(original, transformed):
            for p, q in zip(first.args[1], second.args[1]):
                expected = city["lbox_point"](12, -7, .73, *p)
                for got, wanted in zip(q, expected):
                    self.assertAlmostEqual(got, wanted)
        self.assertEqual(len(base["wood_light"].verts), 24)  # seduta e due manopole
        for p, q in zip(base["wood_light"].verts, rotated["wood_light"].verts):
            for got, wanted in zip(q, city["lbox_point"](12, -7, .73, *p)):
                self.assertAlmostEqual(got, wanted)

    def test_mesh_cavallino_valide_e_dentro_il_tappeto(self):
        group = assert_valid(self, "build_spring_ride")
        for batch in group.values():
            for x, y, z in batch.verts:
                self.assertLess(abs(x - 12), .65)
                self.assertLess(abs(y + 7), .65)
                self.assertGreaterEqual(z, .19 - 1e-9)


def assert_valid(test, function):
    group = batches()
    city[function](group, 12, -7, yaw=.73)
    for batch in group.values():
        test.assertTrue(all(math.isfinite(c) for v in batch.verts for c in v))
        test.assertEqual(len(batch.faces), len(batch.smooth))
        for face in batch.faces:
            test.assertGreaterEqual(len(face), 3)
            test.assertTrue(all(0 <= index < len(batch.verts) for index in face))
    return group


if __name__ == "__main__":
    unittest.main()
