"""Regressioni sugli edifici in strada e sui tre dettagli dell'undicesima versione.

Usa i modelli sorgente reali, senza salvare .blend o avviare render:
    python3 -m unittest discover -s prova_citta_1 -p 'test_*.py' -v
"""
import math
import random
import unittest
from collections import Counter, defaultdict
from dataclasses import replace
from unittest.mock import patch

from mathutils import Matrix, Vector

import genera_citta as city


def batches():
    return defaultdict(lambda: city.Batch("Test", None, None))


def assert_valid_meshes(test, group):
    for batch in group.values():
        test.assertEqual(len(batch.faces), len(batch.smooth))
        test.assertTrue(all(math.isfinite(c) for p in batch.verts for c in p))
        test.assertTrue(all(0 <= i < len(batch.verts) for f in batch.faces for i in f))


class UrbanisticaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.templates, _ = city.import_city_assets()
        cls.layout = city.plan_house_layout(cls.templates)

    def test_conserva_tutte_le_33_case_e_i_modelli(self):
        self.assertEqual(len(self.layout), 33)
        self.assertEqual(len({h.lot.name for h in self.layout}), 33)
        self.assertEqual(Counter(h.lot.model for h in self.layout),
                         {"casale": 13, "chalet": 13, "villa": 7})
        for h in self.layout:
            self.assertGreater(h.scale, .48)
            self.assertLessEqual(h.scale, h.lot.scale)

    def test_ingombri_reali_ruotati_dentro_i_lotti(self):
        # Controllo indipendente: tutti i bounding box dei singoli oggetti,
        # trasformati con matrici Blender, non solo il rettangolo del planner.
        for h in self.layout:
            with self.subTest(casa=h.lot.name):
                template = self.templates[h.lot.model]
                transform = (Matrix.Translation((h.x, h.y, 0)) @
                             Matrix.Rotation(h.yaw, 4, "Z") @ Matrix.Scale(h.scale, 4))
                points = [transform @ (obj.matrix_world @ Vector(v) - template.instance_offset)
                          for obj in template.all_objects if obj.type == "MESH"
                          for v in obj.bound_box]
                actual = city.bounds_xy(points)
                for got, wanted in zip(actual, h.bounds):
                    self.assertAlmostEqual(got, wanted, places=4)
                a, b, c, d = h.lot.bounds
                self.assertGreaterEqual(actual[0], a + .3999)
                self.assertLessEqual(actual[1], b - .3999)
                self.assertGreaterEqual(actual[2], c + .3999)
                self.assertLessEqual(actual[3], d - .3999)

    def test_case_fuori_dalla_viabilita_generata(self):
        # Le fasce vengono ricavate dalle chiamate effettive ai costruttori
        # delle strade, così il test non dipende solo dai dati del planner.
        b = batches()
        state = random.getstate()
        try:
            with patch.object(city, "make_batch_set", return_value=b), \
                    patch.object(city.Batch, "flush"), patch.object(city, "make_cube"), \
                    patch.object(city, "add_road_h", wraps=city.add_road_h) as horizontal, \
                    patch.object(city, "add_road_v", wraps=city.add_road_v) as vertical:
                city.build_roads(defaultdict(lambda: None), None, None)
        finally:
            random.setstate(state)
        roads = []
        for call in horizontal.call_args_list:
            _, y, a, b, width = call.args
            roads.append((a, b, y - width / 2 - 2.375, y + width / 2 + 2.375))
        for call in vertical.call_args_list:
            _, x, a, b, width = call.args
            roads.append((x - width / 2 - 2.375, x + width / 2 + 2.375, a, b))
        self.assertEqual(len(roads), 12)
        for h in self.layout:
            self.assertFalse(any(city.rectangles_overlap(h.bounds, r) for r in roads),
                             h.lot.name)
            for x, y in city.ROUNDABOUTS:
                a, b, c, d = h.bounds
                distance = math.hypot(x - min(max(x, a), b), y - min(max(y, c), d))
                self.assertGreaterEqual(distance, 9.9)

    def test_nessuna_casa_sovrapposta_a_un_altra(self):
        for i, h in enumerate(self.layout):
            for other in self.layout[:i]:
                self.assertFalse(city.rectangles_overlap(h.bounds, other.bounds),
                                 (h.lot.name, other.lot.name))

    def test_intercetta_le_vecchie_case_in_strada(self):
        for model, x, y, direction, scale in (
                ("chalet", -19, 80, "S", .74), ("villa", 19, 80, "S", .66),
                ("chalet", -18.5, 44, "S", .70), ("villa", -96, -40, "E", .72)):
            bounds = city.transformed_bounds_xy(city.collection_bounds_xy(self.templates[model]),
                                                 x, y, city.DIRECTIONS[direction] -
                                                 city.HOUSE_FRONT[model], scale)
            self.assertTrue(city.footprint_on_street(bounds, sidewalk=False))

    def test_validatore_blocca_regressioni_prima_del_salvataggio(self):
        h = self.layout[0]
        with self.assertRaisesRegex(ValueError, "viabilità"):
            city.validate_house_layout([replace(h, bounds=(-72, -68, 0, 4))])
        with self.assertRaisesRegex(ValueError, "sovrapposte"):
            city.validate_house_layout([h, h])
        with self.assertRaisesRegex(ValueError, "dentro un edificio"):
            city.validate_house_layout([h], [("Palazzo", h.bounds)])

    def test_giardini_e_siepi_non_tornano_sulle_strade_o_sulle_case(self):
        self.assertEqual(len(city.PRIVATE_GARDENS), 16)
        for x, y, w, d in city.PRIVATE_GARDENS:
            bounds = (x - w / 2 - .16, x + w / 2 + .16,
                      y - d / 2 - .16, y + d / 2 + .16)
            self.assertFalse(city.footprint_on_street(bounds), bounds)
            self.assertFalse(any(city.rectangles_overlap(bounds, h.bounds)
                                 for h in self.layout), bounds)


class PonticelloTests(unittest.TestCase):
    def setUp(self):
        self.b = batches()
        with patch.object(city, "add_tube", wraps=city.add_tube) as tubes:
            city.build_pond_bridge(self.b, 0, 0)
        self.tubes = [(c.args[1], c.args[2]) for c in tubes.call_args_list]

    def test_24_tavole_inclinate_con_bordi_contigui(self):
        deck = self.b["wood_light"]
        self.assertEqual(len(deck.faces), 24 * 6)
        last_edge = None
        for i in range(24):
            top = [deck.verts[v] for v in deck.faces[i * 6 + 1]]
            left, right = min(p[0] for p in top), max(p[0] for p in top)
            edge = {p for p in top if p[0] == left}
            if last_edge is not None:
                self.assertEqual(edge, last_edge)
            last_edge = {p for p in top if p[0] == right}
            for p in top:
                t = (p[0] + 4.8) / 9.6
                self.assertAlmostEqual(p[2], city.bridge_point(0, 0, t)[2])
            self.assertNotEqual(top[0][2], top[1][2])
        assert_valid_meshes(self, self.b)

    def test_due_estremita_sulla_terraferma_e_piano_sopra_la_sponda(self):
        for t in (0, 1):
            x, y, z = city.bridge_point(0, 0, t)
            self.assertAlmostEqual(z, .18)
            for side in (-1, 1):
                self.assertGreater(math.hypot(x, y + side * .78), 4.4)
        for i in range(101):
            x, y, z = city.bridge_point(0, 0, i / 100)
            if 3.8 <= math.hypot(x, y) <= 4.5:
                self.assertGreater(z - .09, .21)

    def test_corrimani_continui_e_montanti_collegati(self):
        rails = [points for points, radius in self.tubes
                 if len(points) == 25 and radius in (.035, .05)]
        posts = [points for points, _ in self.tubes if len(points) == 2]
        self.assertEqual(len(rails), 4)
        self.assertEqual(len(posts), 14)
        for points in rails:
            offset = points[0][2] - .18
            self.assertIn(round(offset, 2), (.48, .90))
            for i, p in enumerate(points):
                self.assertAlmostEqual(p[2], city.bridge_point(0, 0, i / 24)[2] + offset)
        for low, high in posts:
            t = (low[0] + 4.8) / 9.6
            self.assertAlmostEqual(low[2], city.bridge_point(0, 0, t)[2] - .09)
            self.assertAlmostEqual(high[2], city.bridge_point(0, 0, t)[2] + .90)

    def test_accesso_senza_canneti_massi_o_cordolo_trasversale(self):
        b = batches()
        state = random.getstate()
        try:
            with patch.object(b["leaf_light"], "cone", wraps=b["leaf_light"].cone) as reeds, \
                    patch.object(b["concrete"], "sphere", wraps=b["concrete"].sphere) as rocks:
                city.build_pond(b, *city.POND_CENTER)
            for call in reeds.call_args_list + rocks.call_args_list:
                x, y, _ = call.args[0]
                self.assertFalse(city.in_bridge_corridor(x, y, *city.POND_CENTER))
            with patch.object(city, "make_cube"), \
                    patch.object(b["curb"], "box", wraps=b["curb"].box) as curbs:
                city.build_trees_and_park(b, defaultdict(lambda: None), None, None)
            for call in curbs.call_args_list:
                (x, y, _), (_, length, _) = call.args[:2]
                if abs(x + 64.7) < 1e-5:
                    self.assertFalse(y - length / 2 < 47.1 < y + length / 2)
        finally:
            random.setstate(state)


class FermataTests(unittest.TestCase):
    def test_bus_interamente_nella_corsia_sud(self):
        b = batches()
        city.build_bus(b, *city.BUS_POSITION, ground_z=city.ROAD_TOP)
        a, c, d, e = city.bounds_xy(p for batch in b.values() for p in batch.verts)
        self.assertGreater(a, 29.9)  # dopo attraversamento e rotatoria x = 23
        self.assertLess(c, 63.1)     # prima dell'attraversamento x = 70
        self.assertGreater(d, -74)
        self.assertLess(e, -70)
        # Il battistrada tocca la carreggiata (ventinovesima versione).
        self.assertAlmostEqual(min(p[2] for batch in b.values() for p in batch.verts),
                               city.ROAD_TOP)
        assert_valid_meshes(self, b)

    def test_ruote_ruotano_con_il_bus(self):
        b = batches()
        yaw = .73
        with patch.object(city, "add_tube", wraps=city.add_tube) as tubes:
            city.build_bus(b, 0, 0, yaw)
        self.assertEqual(len(tubes.call_args_list), 8)
        for call in tubes.call_args_list:
            p, q = map(Vector, call.args[1])
            axis = (q - p).normalized()
            self.assertAlmostEqual(axis.x, -math.sin(yaw), places=5)
            self.assertAlmostEqual(axis.y, math.cos(yaw), places=5)
            self.assertAlmostEqual(axis.z, 0)

    def test_vetratura_esterna_e_due_porte_a_destra(self):
        b = batches()
        with patch.object(city, "lbox", wraps=city.lbox) as boxes:
            city.build_bus(b, 0, 0)
        windows = [c.args for c in boxes.call_args_list
                   if c.args[0] is b["glass"] and c.args[-3:] == (1.23, .055, 1.6)]
        self.assertEqual(len(windows), 14)
        self.assertTrue(all(abs(c[5]) == 1.23 for c in windows))
        doors = [c.args for c in boxes.call_args_list
                 if c.args[0] is b["metal"] and c.args[-3:] == (1.25, .055, 2.38)]
        self.assertEqual(len(doors), 2)
        self.assertTrue(all(c[5] < -1.225 for c in doors))

    def test_pensilina_aperta_verso_la_strada(self):
        # Dalla sedicesima versione la pensilina ha la parete di fondo vetrata
        # ripartita da cinque montanti e due ritorni corti alle testate: qui
        # si verifica l'invariante — nessuna lastra verso la carreggiata e
        # una vetrata di fondo continua su tutta la larghezza.
        b = batches()
        with patch.object(city, "lbox", wraps=city.lbox) as boxes:
            city.build_bus_shelter(b, 0, 0)
        glass = [c.args for c in boxes.call_args_list if c.args[0] is b["glass"]]
        self.assertEqual(len(glass), 3)
        self.assertTrue(all(c[5] + c[8] / 2 < .5 for c in glass))
        back = [c for c in glass if c[5] == -.85]
        self.assertEqual(len(back), 1)
        self.assertGreaterEqual(back[0][7], 5.0)   # copre tutta la larghezza

    def test_arredi_sulla_piazzola_e_passaggio_laterale_libero(self):
        b = batches()
        with patch.object(city, "add_text"), patch.object(city, "build_bus"):
            city.build_bus_stop(b, defaultdict(lambda: None), None)
        a, c, d, e = city.BUS_STOP_BOUNDS
        for key, batch in b.items():
            # La pavimentazione tattile (tile_b) e la segnaletica gialla non
            # sono arredi: dal passaggio della ventiquattresima versione sono
            # incassate nel marciapiede e non occupano il passaggio.
            if key in ("road_yellow", "sidewalk", "tile_b"):
                continue
            for x, y, _ in batch.verts:
                self.assertGreaterEqual(x, a)
                self.assertLessEqual(x, c)
                self.assertGreaterEqual(y, d)
                self.assertLessEqual(y, -75.9)  # almeno 1.775 m di passaggio libero
        self.assertEqual(city.bounds_xy(b["sidewalk"].verts), city.BUS_STOP_BOUNDS)
        self.assertLessEqual(max(p[2] for p in b["sidewalk"].verts), .111)
        # Il percorso tattile resta a filo del marciapiede: due millimetri la
        # guida e la fascia, sei millimetri i bolli.
        self.assertLessEqual(max(p[2] for p in b["tile_b"].verts), .112 + 1e-6)
        self.assertLessEqual(max(p[2] for p in b["road_yellow"].verts), .116 + 1e-6)
        assert_valid_meshes(self, b)


class TricoloreTests(unittest.TestCase):
    def setUp(self):
        self.b = batches()
        city.build_tricolore(self.b, 0, 0, 0)

    def test_tre_bande_verticali_della_stessa_larghezza(self):
        for i, key in enumerate(("flag_green", "flag_white", "flag_red")):
            batch = self.b[key]
            self.assertEqual(len(batch.faces), 48)
            self.assertTrue(all(batch.smooth))
            self.assertAlmostEqual(min(p[0] for p in batch.verts), i * .6)
            self.assertAlmostEqual(max(p[0] for p in batch.verts), (i + 1) * .6)
        assert_valid_meshes(self, self.b)

    def test_cuciture_contigue_senza_fessure(self):
        for left, right in (("flag_green", "flag_white"), ("flag_white", "flag_red")):
            seam = max(p[0] for p in self.b[left].verts)
            a = {p for p in self.b[left].verts if p[0] == seam}
            b = {p for p in self.b[right].verts if p[0] == seam}
            self.assertEqual(len(a), 9)
            self.assertEqual(a, b)

    def test_inferitura_ferma_e_telo_ondulato(self):
        points = [p for key in ("flag_green", "flag_white", "flag_red")
                  for p in self.b[key].verts]
        hoist = {p for p in points if p[0] == 0}
        self.assertEqual(len(hoist), 9)
        self.assertTrue(all(p[1] == 0 for p in hoist))
        self.assertAlmostEqual(max(p[2] for p in hoist) - min(p[2] for p in hoist), 1.2)
        self.assertGreater(max(abs(p[1]) for p in points), .1)
        for key in ("flag_green", "flag_white", "flag_red"):
            batch = self.b[key]
            for face in batch.faces:
                a, b, c = (Vector(batch.verts[i]) for i in face[:3])
                self.assertGreater((b - a).cross(c - a).length, 1e-6)


if __name__ == "__main__":
    unittest.main()
