"""Tre dettagli della versione 12, verificabili anche senza Blender.

Si eseguono le stesse funzioni del generatore, estratte via AST senza caricare
bpy. I tubi sono intercettati: si controllano le polilinee e i raggi, non la
tessellazione (già coperta dai test Blender). Per i box si verificano le mesh.
"""
import ast
import math
from pathlib import Path
from collections import defaultdict
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


def load_geometry():
    source = Path(__file__).with_name("genera_citta.py").read_text()
    names = {"Batch", "lbox", "lbox_point", "add_tube", "make_bench",
             "add_bicycle", "build_car"} - {"add_tube"}
    tree = ast.parse(source)
    tree.body = [node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]
    scope = {"math": math, "PI": math.pi, "TAU": math.tau, "add_tube": Mock()}
    exec(compile(tree, "genera_citta.py", "exec"), scope)
    return scope, SimpleNamespace(**scope)


scope, city = load_geometry()


def batches():
    return defaultdict(lambda: city.Batch("Test", None, None))


class ArrediMobilitaTests(unittest.TestCase):
    def test_schienale_verticale_collegato_ai_montanti(self):
        group = batches()
        with patch.dict(scope, lbox=Mock(wraps=city.lbox)):
            city.make_bench(group, 0, 0)
            boxes = [call.args for call in scope['lbox'].call_args_list]
        slats = [b for b in boxes if b[0] is group['wood']]
        self.assertEqual(len(slats), 3)
        self.assertEqual([round(b[6], 2) for b in slats], [.82, .99, 1.16])
        for b in slats:
            self.assertEqual(b[5], .42)
            self.assertLessEqual(b[6] + b[9] / 2, 1.24)
        self.assertEqual(len(group['wood'].faces), 18)

    def test_auto_vetri_esterni_e_fanali_su_entrambi_i_lati(self):
        group = batches()
        city.build_car(group, 0, 0, 0)
        glass = group['glass'].verts
        self.assertEqual(len(glass), 6 * 8)
        # Le quattro vetrature laterali emergono dalla sagoma del tetto/cabina.
        for i in range(0, 32, 8):
            self.assertGreater(min(abs(v[1]) for v in glass[i:i+8]), .74)
        self.assertEqual(len(group['white'].verts), 16)
        self.assertEqual(len(group['red'].verts), 16)

    def test_auto_e_biciclette_ruotano_tutta_la_geometria(self):
        for build in (lambda b, x, y, a: city.build_car(b, x, y, a),
                      lambda b, x, y, a: city.add_bicycle(b, x, y, a, 'blue'),
                      city.make_bench):
            base, rotated = batches(), batches()
            scope["add_tube"].reset_mock()
            build(base, 0, 0, 0)
            original_tubes = [c.args[1:] for c in scope["add_tube"].call_args_list]
            scope["add_tube"].reset_mock()
            angle = .73
            build(rotated, 12, -7, angle)
            transformed_tubes = [c.args[1:] for c in scope["add_tube"].call_args_list]
            self.assertEqual(len(original_tubes), len(transformed_tubes))
            for (points, *params), (other_points, *other_params) in zip(original_tubes, transformed_tubes):
                self.assertEqual(params, other_params)
                for (x, y, z), actual in zip(points, other_points):
                    expected = (12+x*math.cos(angle)-y*math.sin(angle),
                                -7+x*math.sin(angle)+y*math.cos(angle), z)
                    for got, wanted in zip(actual, expected):
                        self.assertAlmostEqual(got, wanted)
            for key, batch in base.items():
                other = rotated[key]
                self.assertEqual(batch.faces, other.faces)
                for (x, y, z), actual in zip(batch.verts, other.verts):
                    expected = (12+x*math.cos(angle)-y*math.sin(angle),
                                -7+x*math.sin(angle)+y*math.cos(angle), z)
                    for got, wanted in zip(actual, expected):
                        self.assertAlmostEqual(got, wanted)
                self.assertEqual(len(batch.faces), len(batch.smooth))
                self.assertTrue(all(math.isfinite(c) for v in other.verts for c in v))
                self.assertTrue(all(0 <= i < len(other.verts)
                                    for f in other.faces for i in f))

    def test_bici_ruote_aperte_raggi_e_telaio_connesso(self):
        group = batches()
        tube = Mock()
        with patch.dict(scope, add_tube=tube):
            city.add_bicycle(group, 0, 0, 0, 'blue')
        calls = [c.args for c in tube.call_args_list]
        rings = [c[1] for c in calls if len(c[1]) == 25]
        self.assertEqual(len(rings), 2)
        for points in rings:
            for a, b in zip(points[0], points[-1]):
                self.assertAlmostEqual(a, b)
            self.assertAlmostEqual(min(p[2] for p in points) - .03, 0)
        spokes = [c for c in calls if c[2] == .008]
        self.assertEqual(len(spokes), 16)
        edges = [c[1] for c in calls if c[0] is group['blue']]
        self.assertEqual(len(edges), 6)
        from collections import Counter
        degree = Counter(p for edge in edges for p in edge)
        self.assertEqual(sorted(degree.values()), [1, 2, 3, 3, 3])


if __name__ == '__main__':
    unittest.main()
