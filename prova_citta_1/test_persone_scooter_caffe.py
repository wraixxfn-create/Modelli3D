"""Tre dettagli della versione 13, verificabili anche senza Blender.

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
    names = {"Batch", "lbox", "lbox_point", "add_person", "add_scooter",
             "make_cafe_chair", "make_cafe_table"}
    consts = {"CAFFE_FLOOR_Z", "CAFFE_TABLES", "CAFFE_CHAIRS", "GAZEBO_POSTS"}
    tree = ast.parse(source)
    tree.body = [node for node in tree.body
                 if (isinstance(node, (ast.FunctionDef, ast.ClassDef))
                     and node.name in names)
                 or (isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id in consts
                             for t in node.targets))]
    scope = {"math": math, "PI": math.pi, "TAU": math.tau, "add_tube": Mock()}
    exec(compile(tree, "genera_citta.py", "exec"), scope)
    return scope, SimpleNamespace(**scope)


scope, city = load_geometry()


def batches():
    return defaultdict(lambda: city.Batch("Test", None, None))


def assert_rotates(test, build):
    """La stessa costruzione a due yaw diversi differisce solo per la rotazione.

    La posizione di confronto mantiene il colore dei capelli deterministico
    (parità di int(7x + 3y)), così anche le parti condizionali coincidono.
    """
    base, rotated = batches(), batches()
    scope["add_tube"].reset_mock()
    build(base, 0, 0, 0.0)
    original_tubes = [c.args[1:] for c in scope["add_tube"].call_args_list]
    scope["add_tube"].reset_mock()
    angle = .73
    build(rotated, 12, -6, angle)
    transformed_tubes = [c.args[1:] for c in scope["add_tube"].call_args_list]
    test.assertEqual(len(original_tubes), len(transformed_tubes))
    for (points, *params), (other_points, *other_params) in zip(original_tubes,
                                                                transformed_tubes):
        test.assertEqual(params, other_params)
        for (x, y, z), actual in zip(points, other_points):
            expected = (12 + x * math.cos(angle) - y * math.sin(angle),
                        -6 + x * math.sin(angle) + y * math.cos(angle), z)
            for got, wanted in zip(actual, expected):
                test.assertAlmostEqual(got, wanted)
    for key, batch in base.items():
        other = rotated[key]
        test.assertEqual(batch.faces, other.faces)
        for (x, y, z), actual in zip(batch.verts, other.verts):
            expected = (12 + x * math.cos(angle) - y * math.sin(angle),
                        -6 + x * math.sin(angle) + y * math.cos(angle), z)
            for got, wanted in zip(actual, expected):
                test.assertAlmostEqual(got, wanted)
        test.assertEqual(len(batch.faces), len(batch.smooth))
        test.assertTrue(all(math.isfinite(c) for v in other.verts for c in v))
        test.assertTrue(all(0 <= i < len(other.verts)
                            for f in other.faces for i in f))


class PersoneSeduteTests(unittest.TestCase):
    def boxes(self, **kwargs):
        group = batches()
        with patch.dict(scope, lbox=Mock(wraps=city.lbox)):
            city.add_person(group, 0, 0, 0.0, "cloth_red", "cloth_blue", 1.0,
                            **kwargs)
            calls = [call.args for call in scope['lbox'].call_args_list]
        return calls, group

    def test_coscie_orizzontali_stinchi_verticali_busto_sulla_seduta(self):
        for seat_z, foot_z in ((0.65, 0.21), (0.98, 0.38), (1.01, 0.55)):
            with self.subTest(seat_z=seat_z, foot_z=foot_z):
                calls, group = self.boxes(seated=True, seat_z=seat_z,
                                          foot_z=foot_z)
                # lbox(batch, cx, cy, yaw, x, y, z, sx, sy, sz)
                legs = [b for b in calls if b[0] is group['cloth_blue']]
                self.assertEqual(len(legs), 4)
                thighs = [b for b in legs if b[8] > b[9]]
                shins = [b for b in legs if b[9] > b[8]]
                self.assertEqual((len(thighs), len(shins)), (2, 2))
                for b in thighs:
                    self.assertAlmostEqual(b[6] - b[9] / 2, seat_z)  # sulla seduta
                    self.assertAlmostEqual(b[5], 0.17)               # in avanti
                for b in shins:
                    self.assertAlmostEqual(b[6] - b[9] / 2, foot_z)  # piedi giù
                    self.assertAlmostEqual(b[6] + b[9] / 2, seat_z + 0.09)
                    self.assertAlmostEqual(b[5], 0.34)               # al ginocchio
                torso = [b for b in calls if b[0] is group['cloth_red']
                         and b[7] > b[8]]
                self.assertEqual(len(torso), 1)
                # il busto poggia sulle cosce senza attraversare la seduta
                self.assertGreaterEqual(torso[0][6] - torso[0][9] / 2, seat_z)
                # la testa sta sopra l'anca, non mezza metro per aria
                head = group['skin'].verts
                self.assertAlmostEqual(sum(v[2] for v in head) / len(head),
                                       seat_z + 0.88, places=3)

    def test_persona_in_piedi_invariata(self):
        calls, group = self.boxes()
        legs = [b for b in calls if b[0] is group['cloth_blue']]
        self.assertEqual(len(legs), 2)                  # niente cosce aggiunte
        for b in legs:
            self.assertAlmostEqual(b[6] - b[9] / 2, 0.0)
            self.assertAlmostEqual(b[6] + b[9] / 2, 0.80)
        self.assertEqual(len([b for b in calls
                              if b[0] is group['cloth_red']]), 3)
        head = group['skin'].verts
        self.assertAlmostEqual(sum(v[2] for v in head) / len(head), 1.52,
                               places=3)

    def test_la_posa_seduta_ruota_con_lo_yaw(self):
        # Le teste sono ellissoidi quasi assialsimmetrici: di box si verifica
        # la mesh intera, delle sfere il centro (che ruota come il resto).
        base, rotated = batches(), batches()
        with patch.dict(scope, lbox=Mock(wraps=city.lbox)):
            city.add_person(base, 0, 0, 0.0, "cloth_red", "cloth_blue", 1.0,
                            seated=True, seat_z=0.65, foot_z=0.21)
            boxes = [call.args for call in scope['lbox'].call_args_list]
        angle = .73
        with patch.dict(scope, lbox=Mock(wraps=city.lbox)):
            city.add_person(rotated, 12, -6, angle, "cloth_red", "cloth_blue",
                            1.0, seated=True, seat_z=0.65, foot_z=0.21)
            other_boxes = [call.args for call in scope['lbox'].call_args_list]
        self.assertEqual(len(boxes), len(other_boxes))
        for b, o in zip(boxes, other_boxes):
            self.assertEqual(b[4:], o[4:])     # stesse dimensioni e quote locali
        angle_sin, angle_cos = math.sin(angle), math.cos(angle)
        for key in ("cloth_blue", "cloth_red"):
            self.assertEqual(base[key].faces, rotated[key].faces)
            for (x, y, z), actual in zip(base[key].verts, rotated[key].verts):
                expected = (12 + x * angle_cos - y * angle_sin,
                            -6 + x * angle_sin + y * angle_cos, z)
                for got, wanted in zip(actual, expected):
                    self.assertAlmostEqual(got, wanted)
        for key in ("skin", "hair_light"):
            self.assertEqual(len(base[key].verts), len(rotated[key].verts))
            for group in (base[key], rotated[key]):
                self.assertEqual(len(group.faces), len(group.smooth))
            base_center = [sum(v[i] for v in base[key].verts) /
                           len(base[key].verts) for i in range(3)]
            other_center = [sum(v[i] for v in rotated[key].verts) /
                            len(rotated[key].verts) for i in range(3)]
            expected = (12 + base_center[0] * angle_cos - base_center[1] * angle_sin,
                        -6 + base_center[0] * angle_sin + base_center[1] * angle_cos,
                        base_center[2])
            for got, wanted in zip(other_center, expected):
                self.assertAlmostEqual(got, wanted, places=3)


class ScooterTests(unittest.TestCase):
    def test_ruote_ad_anello_mozzi_e_manubrio_nel_piano_locale(self):
        group = batches()
        tube = Mock()
        with patch.dict(scope, add_tube=tube):
            city.add_scooter(group, 0, 0, 0.0, 'cloth_green')
        calls = [c.args for c in tube.call_args_list]
        rings = [c[1] for c in calls if len(c[1]) == 21]
        self.assertEqual(len(rings), 2)             # due pneumatici ad anello
        for points in rings:
            for a, b in zip(points[0], points[-1]):
                self.assertAlmostEqual(a, b)        # anelli chiusi
            for x, y, z in points:
                self.assertAlmostEqual(y, 0.0)      # nel piano locale XZ
            # il bordo esterno tocca il suolo (raggio anello + sezione)
            self.assertAlmostEqual(min(p[2] for p in points), 0.05)
        # mozzi e manubrio attraversano il mezzo lungo Y locale
        crossing = [c for c in calls if len(c[1]) == 2 and
                    math.hypot(c[1][0][0] - c[1][1][0],
                               c[1][0][2] - c[1][1][2]) < 1e-9 and
                    abs(c[1][0][1]) > 0.04 and abs(c[1][1][1]) > 0.04]
        self.assertEqual(len(crossing), 3)          # due mozzi + manubrio
        handlebar = [c for c in crossing if abs(c[1][0][1]) > 0.2]
        self.assertEqual(len(handlebar), 1)
        self.assertGreater(abs(handlebar[0][1][0][1]), 0.27)

    def test_faro_fanale_e_corpo_colorato(self):
        group = batches()
        city.add_scooter(group, 0, 0, 0.0, 'cloth_green')
        self.assertTrue(group['lamp'].verts)        # faro anteriore
        self.assertTrue(group['red'].verts)         # fanale posteriore
        self.assertTrue(group['roof_dark'].verts)   # sella e manopole
        # piano d'appoggio, codone e scudo nello stesso colore del mezzo
        self.assertEqual(len(group['cloth_green'].faces), 18)

    def test_lo_scooter_ruota_tutta_la_geometria(self):
        assert_rotates(self, lambda b, x, y, a: city.add_scooter(
            b, x, y, a, 'cloth_green'))


class CaffeTests(unittest.TestCase):
    def test_sedie_con_quattro_gambe_seduta_e_schienale(self):
        group = batches()
        with patch.dict(scope, lbox=Mock(wraps=city.lbox)):
            city.make_cafe_chair(group, 0, 0, 0.0, 0.55)
            calls = [call.args for call in scope['lbox'].call_args_list]
        legs = [b for b in calls if b[0] is group['metal']]
        self.assertEqual(len(legs), 4)
        for b in legs:
            # appoggiate sul calpestio: leggermente incassate, non sporgono
            # sotto la platea e non galleggiano sopra
            self.assertGreaterEqual(b[6] - b[9] / 2, 0.55 - 0.05)
            self.assertLessEqual(b[6] - b[9] / 2, 0.55)
        wood = [b for b in calls if b[0] is group['wood_light']]
        self.assertEqual(len(wood), 5)              # seduta, montanti, listelli
        seat = [b for b in wood if abs(b[6] + b[9] / 2 - 1.01) < 1e-9]
        self.assertEqual(len(seat), 1)              # seduta a 46 cm da terra
        back = [b for b in wood if b[5] > 0.1 and b[7] > b[8]]
        self.assertEqual(len(back), 2)              # schienale a due listelli
        self.assertLessEqual(max(b[6] + b[9] / 2 for b in back), 0.55 + 0.90)

    def test_la_sedia_ruota_con_lo_yaw(self):
        assert_rotates(self, lambda b, x, y, a: city.make_cafe_chair(
            b, x, y, a, 0.55))

    def test_tavoli_sopra_la_platea_con_piano_alla_quota_da_bar(self):
        group = batches()
        city.make_cafe_table(group, 0, 0, 0.55)
        # piedino e gambe non scendono sotto la platea del chiosco
        self.assertGreaterEqual(min(v[2] for v in group['metal'].verts), 0.54)
        # piano a 76 cm dal calpestio: 30 cm sopra la seduta delle sedie
        self.assertAlmostEqual(max(v[2] for v in group['wood_light'].verts),
                               0.55 + 0.76, places=3)

    def test_sedie_verso_il_tavolo_e_passaggio_lungo_i_montanti(self):
        self.assertAlmostEqual(city.CAFFE_FLOOR_Z, 0.55)
        tables = list(city.CAFFE_TABLES)
        self.assertEqual(len(tables), 2)
        self.assertEqual(len(city.CAFFE_CHAIRS), 4)
        for x, y, yaw in city.CAFFE_CHAIRS:
            with self.subTest(chair=(x, y)):
                near = min(tables,
                           key=lambda t: math.hypot(t[0] - x, t[1] - y))
                self.assertLess(math.hypot(near[0] - x, near[1] - y), 1.0)
                # la sedia guarda il proprio tavolo
                fx, fy = -math.sin(yaw), math.cos(yaw)
                self.assertGreater((near[0] - x) * fx + (near[1] - y) * fy, 0.5)
                # passaggio libero fra i montanti del gazebo
                for px, py in city.GAZEBO_POSTS:
                    self.assertGreater(math.hypot(px - x, py - y), 0.85)
                # dentro la platea del chiosco (5.2 × 3.8 in (0, -11.4))
                self.assertTrue(-2.3 <= x <= 2.3)
                self.assertTrue(-13.0 <= y <= -9.8)


if __name__ == '__main__':
    unittest.main()
