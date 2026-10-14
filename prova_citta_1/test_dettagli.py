"""Controlli geometrici dei tre interventi della decima versione.

Eseguire con il Python di Blender / un ambiente con bpy:
    python3 -m unittest discover -s prova_citta_1 -p 'test_*.py' -v
Non carica né sovrascrive citta.blend e non avvia render.
"""
import math
import unittest
from collections import defaultdict
from unittest.mock import patch

import genera_citta as city


def batches():
    return defaultdict(lambda: city.Batch("Test", None, None))


class FontanaTests(unittest.TestCase):
    def setUp(self):
        self.b = batches()
        with patch.object(city, "make_cube"), patch.object(city, "add_text"), \
                patch.object(city, "add_tube", wraps=city.add_tube) as tubes, \
                patch.object(self.b["water"], "ring", wraps=self.b["water"].ring) as rings:
            city.build_town_square(self.b, defaultdict(lambda: None), None)
        self.jets = [c.args[1] for c in tubes.call_args_list
                     if c.args[0] is self.b["water"]]
        self.ripples = rings.call_args_list

    def test_otto_getti_continui_sopra_il_bordo(self):
        self.assertEqual(len(self.jets), 8)
        for points in self.jets:
            self.assertEqual(len(points), 25)
            for x, y, z in points:
                r = math.hypot(x, y + 0.4)
                self.assertGreaterEqual(r, 0.71)  # fuori dal piedistallo
                if 1.15 <= r <= 1.55:
                    self.assertGreater(z, 1.46)  # sopra il bordo superiore
            self.assertGreater(max(p[2] for p in points), 2.0)
            self.assertAlmostEqual(points[-1][2], 0.8175)

    def test_increspature_interne_alla_vasca(self):
        self.assertEqual(len(self.ripples), 16)
        for call in self.ripples:
            (x, y, z), radius, tube = call.args[:3]
            self.assertAlmostEqual(z, 0.8175)
            self.assertLess(math.hypot(x, y + 0.4) + radius + tube, 3.5)


class GiochiTests(unittest.TestCase):
    def setUp(self):
        self.b = batches()
        with patch.object(city, "add_tube", wraps=city.add_tube) as tubes, \
                patch.object(city, "lbox", wraps=city.lbox) as boxes, \
                patch.object(city, "lbox_tilt", wraps=city.lbox_tilt) as tilted:
            city.build_playground(self.b, 0, 0)
        self.tubes = [c.args[1] for c in tubes.call_args_list]
        self.boxes = [c.args for c in boxes.call_args_list]
        self.tilted = [c.args for c in tilted.call_args_list]

    def test_quattro_gambe_inclinate_sul_tappeto(self):
        legs = [p for p in self.tubes if p[0][2] == 0.19 and p[-1][2] == 2.85]
        self.assertEqual(len(legs), 4)
        for low, high in legs:
            self.assertAlmostEqual(abs(low[1] - high[1]), 0.90)
            self.assertAlmostEqual(low[0], high[0])
            self.assertLess(abs(low[0]) + 0.065, 6.0)
            self.assertLess(abs(low[1]) + 0.065, 4.5)

    def test_sospensioni_collegate_a_sedute_e_traversa(self):
        chains = [p for p in self.tubes if p[0][2] == 0.75 and p[-1][2] == 2.85]
        self.assertEqual(len(chains), 4)
        expected_x = sorted(-3.4 + seat + side * 0.23
                            for seat in (-1.1, 1.1) for side in (-1, 1))
        for points, x in zip(sorted(chains), expected_x):
            self.assertAlmostEqual(points[0][0], x)
            self.assertEqual(points[0][:2], points[-1][:2])
            self.assertAlmostEqual(points[0][1], 1.6)

    def test_discesa_e_sponde_con_pendenza_coerente(self):
        self.assertEqual(len(self.tilted), 3)
        slab = self.tilted[0]
        _, _, _, _, _, cy, cz, _, length, thickness, pitch = slab
        self.assertAlmostEqual(math.degrees(pitch), 29.357754, places=5)
        for sign, target_y, target_z in ((-1, -1.3, 0.30), (1, 1.1, 1.65)):
            y = cy + sign * length / 2 * math.cos(pitch) - thickness / 2 * math.sin(pitch)
            z = cz + sign * length / 2 * math.sin(pitch) + thickness / 2 * math.cos(pitch)
            self.assertAlmostEqual(y, target_y)
            self.assertAlmostEqual(z, target_z)
        for side in self.tilted[1:]:
            self.assertEqual(side[-1], pitch)
            self.assertEqual(side[-3], length)

    def test_cinque_pedate_fra_terreno_e_pianerottolo(self):
        steps = [b for b in self.boxes if b[-3:] == (0.80, 0.20, 0.055)]
        self.assertEqual(len(steps), 5)
        last_y, last_z = 2.90, 0.19
        for step in steps:
            y, z = step[5:7]
            self.assertLess(y, last_y)
            self.assertGreater(z, last_z)
            self.assertAlmostEqual((z - 0.19) / (1.65 - 0.19), (2.90 - y) / 1.20)
            last_y, last_z = y, z
        self.assertLess(last_z, 1.65)
        for batch in self.b.values():
            self.assertTrue(all(math.isfinite(c) for p in batch.verts for c in p))
            self.assertEqual(len(batch.faces), len(batch.smooth))


if __name__ == "__main__":
    unittest.main()
