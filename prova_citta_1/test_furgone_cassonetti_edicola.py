"""Tre dettagli della versione 14, verificabili anche senza Blender.

Le funzioni geometriche sono estratte dal generatore via AST; i tubi vengono
intercettati prima della tessellazione, come negli altri test leggeri della
città. Nessun file .blend viene aperto o modificato.
"""
import ast
from collections import defaultdict
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


def load_geometry():
    source = Path(__file__).with_name("genera_citta.py").read_text()
    names = {"Batch", "lbox", "lbox_tilt", "lbox_point", "add_van",
             "add_waste_container", "build_newsstand"}
    tree = ast.parse(source)
    tree.body = [node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                 and node.name in names]
    scope = {"math": math, "PI": math.pi, "TAU": math.tau,
             "add_tube": Mock(), "add_text": Mock()}
    exec(compile(tree, "genera_citta.py", "exec"), scope)
    return scope, SimpleNamespace(**scope)


scope, city = load_geometry()


def batches():
    return defaultdict(lambda: city.Batch("Test", None, None))


def assert_valid(test, group):
    for batch in group.values():
        test.assertEqual(len(batch.faces), len(batch.smooth))
        test.assertTrue(all(math.isfinite(c) for p in batch.verts for c in p))
        test.assertTrue(all(0 <= i < len(batch.verts)
                            for face in batch.faces for i in face))


def assert_rotates(test, build):
    """Confronta due costruzioni che differiscono solo per roto-traslazione."""
    base, rotated = batches(), batches()
    scope["add_tube"].reset_mock()
    build(base, 0, 0, 0.0)
    original_tubes = [call.args[1:] for call in scope["add_tube"].call_args_list]
    scope["add_tube"].reset_mock()
    angle, tx, ty = 0.73, 12.0, -6.0
    build(rotated, tx, ty, angle)
    transformed_tubes = [call.args[1:] for call in scope["add_tube"].call_args_list]

    test.assertEqual(len(original_tubes), len(transformed_tubes))
    co, si = math.cos(angle), math.sin(angle)
    for (points, *params), (other_points, *other_params) in zip(
            original_tubes, transformed_tubes):
        test.assertEqual(params, other_params)
        test.assertEqual(len(points), len(other_points))
        for (x, y, z), actual in zip(points, other_points):
            expected = (tx + x * co - y * si, ty + x * si + y * co, z)
            for got, wanted in zip(actual, expected):
                test.assertAlmostEqual(got, wanted)

    test.assertEqual(set(base), set(rotated))
    for key, batch in base.items():
        other = rotated[key]
        test.assertEqual(batch.faces, other.faces)
        test.assertEqual(batch.smooth, other.smooth)
        for (x, y, z), actual in zip(batch.verts, other.verts):
            expected = (tx + x * co - y * si, ty + x * si + y * co, z)
            for got, wanted in zip(actual, expected):
                test.assertAlmostEqual(got, wanted)
    assert_valid(test, base)
    assert_valid(test, rotated)


class FurgoneTests(unittest.TestCase):
    def test_quattro_pneumatici_ad_anello_e_mozzi_locali(self):
        group = batches()
        with patch.dict(scope, add_tube=Mock()):
            city.add_van(group, 0, 0, 0.0, "white")
            calls = [call.args for call in scope["add_tube"].call_args_list]
        rings = [args for args in calls
                 if args[0] is group["roof_dark"] and len(args[1]) == 25]
        self.assertEqual(len(rings), 4)
        for _, points, radius, *_ in rings:
            for first, last in zip(points[0], points[-1]):
                self.assertAlmostEqual(first, last)
            self.assertAlmostEqual(radius, 0.055)
            self.assertEqual(len({round(p[1], 6) for p in points}), 1)
            self.assertAlmostEqual(min(p[2] for p in points) - radius, 0.04)
        hubs = [args for args in calls if len(args[1]) == 2 and args[2] == 0.115]
        self.assertEqual(len(hubs), 4)
        self.assertTrue(all(a[1][0][0] == a[1][1][0] and
                            a[1][0][2] == a[1][1][2] for a in hubs))

    def test_cabina_aperture_portelloni_e_fanaleria(self):
        group = batches()
        city.add_van(group, 0, 0, 0.0, "white")
        self.assertEqual(len(group["glass"].faces), 3 * 6)  # parabrezza + lati
        self.assertEqual(len(group["lamp"].faces), 2 * 6)
        self.assertEqual(len(group["red"].faces), 2 * 6)
        self.assertEqual(len(group["white"].faces), 4 * 6)  # quattro volumi opachi
        # Guide laterali, giunto centrale e bordi dei due portelloni.
        self.assertGreaterEqual(len(group["metal"].faces), 12 * 6)
        self.assertGreater(min(v[0] for v in group["red"].verts), -2.40)
        assert_valid(self, group)

    def test_tutto_il_furgone_ruota_con_lo_yaw(self):
        assert_rotates(self, lambda b, x, y, a: city.add_van(
            b, x, y, a, "white"))


class CassonettiTests(unittest.TestCase):
    def test_quattro_ruote_coperchio_maniglia_e_pedale(self):
        group = batches()
        with patch.dict(scope, add_tube=Mock()):
            city.add_waste_container(group, 0, 0, 0.0, "canvas_green")
            calls = [call.args for call in scope["add_tube"].call_args_list]
        wheels = [args for args in calls if len(args[1]) == 2 and args[2] == 0.075]
        self.assertEqual(len(wheels), 4)
        self.assertTrue(all(p[2] == 0.12 for args in wheels for p in args[1]))
        self.assertEqual(len([a for a in calls if len(a[1]) == 4]), 1)  # maniglia
        self.assertEqual(len(group["roof_dark"].faces), 6)             # coperchio
        self.assertGreaterEqual(min(v[2] for batch in group.values()
                                    for v in batch.verts), 0.0)

    def test_raccolta_differenziata_e_coperchio_inclinato(self):
        group = batches()
        city.add_waste_container(group, 0, 0, 0.0, "canvas_blue")
        # Corpo + tre tacche della stessa frazione; etichetta bianca separata.
        self.assertEqual(len(group["canvas_blue"].faces), 4 * 6)
        self.assertEqual(len(group["white"].faces), 6)
        lid = group["roof_dark"].verts
        front = [v[2] for v in lid if v[1] == min(p[1] for p in lid)]
        back = [v[2] for v in lid if v[1] == max(p[1] for p in lid)]
        self.assertNotAlmostEqual(sum(front) / len(front), sum(back) / len(back))
        assert_valid(self, group)

    def test_tutto_il_cassonetto_ruota_con_lo_yaw(self):
        assert_rotates(self, lambda b, x, y, a: city.add_waste_container(
            b, x, y, a, "canvas_green"))


class EdicolaTests(unittest.TestCase):
    def build(self, group, x=0, y=0, yaw=0.0):
        mats = defaultdict(object)
        city.build_newsstand(group, mats, object(), x, y, yaw)

    def test_chiosco_vetrato_con_vano_di_vendita_aperto(self):
        group = batches()
        self.build(group)
        self.assertEqual(len(group["glass"].faces), 4 * 6)
        front = [v for v in group["glass"].verts if v[1] < -1.0]
        self.assertTrue(front)
        self.assertTrue(all(abs(x) >= 0.55 for x, _, _ in front))
        self.assertEqual(len(group["concrete"].faces), 6)
        self.assertEqual(len(group["roof_dark"].faces), 6)
        self.assertGreaterEqual(min(v[2] for batch in group.values()
                                    for v in batch.verts), 0.0)
        assert_valid(self, group)

    def test_tenda_contigua_insegna_e_stampa_esposta(self):
        group = batches()
        scope["add_text"].reset_mock()
        self.build(group)
        awning = []
        for key in ("canvas_red", "white"):
            batch = group[key]
            for face in batch.faces:
                points = [batch.verts[i] for i in face]
                if (len(face) == 4 and
                        math.isclose(max(p[1] for p in points) -
                                     min(p[1] for p in points), 0.59) and
                        math.isclose(max(p[2] for p in points) -
                                     min(p[2] for p in points), 0.30)):
                    awning.append(points)
        self.assertEqual(len(awning), 6)
        spans = sorted((min(p[0] for p in face), max(p[0] for p in face))
                       for face in awning)
        self.assertAlmostEqual(spans[0][0], -1.45)
        self.assertAlmostEqual(spans[-1][1], 1.45)
        for left, right in zip(spans, spans[1:]):
            self.assertAlmostEqual(left[1], right[0])
        scope["add_text"].assert_called_once()
        self.assertEqual(scope["add_text"].call_args.args[0], "EDICOLA")
        # Cinque riviste (una per colore) e tre quotidiani bianchi.
        for key in ("cloth_red", "cloth_yellow", "cloth_green", "cloth_violet"):
            self.assertEqual(len(group[key].faces), 6)
        self.assertGreaterEqual(len(group["white"].faces), 8 * 6)

    def test_tutta_ledicola_ruota_con_lo_yaw(self):
        scope["add_text"].reset_mock()
        assert_rotates(self, lambda b, x, y, a: self.build(b, x, y, a))
        # Verifica anche l'oggetto testo, escluso dai batch geometrici.
        calls = scope["add_text"].call_args_list
        self.assertEqual(len(calls), 2)
        base, rotated = calls
        x, y, z = base.args[2]
        angle = 0.73
        expected = (12 + x * math.cos(angle) - y * math.sin(angle),
                    -6 + x * math.sin(angle) + y * math.cos(angle), z)
        for got, wanted in zip(rotated.args[2], expected):
            self.assertAlmostEqual(got, wanted)
        self.assertAlmostEqual(rotated.kwargs["yaw"], angle)


if __name__ == "__main__":
    unittest.main()
