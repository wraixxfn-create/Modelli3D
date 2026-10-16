"""Tre migliorie geometriche della trentaduesima versione, senza Blender.

Le funzioni effettive sono estratte dal generatore via AST e misurate con
primitive Batch: il file .blend e l'anteprima non vengono modificati.
"""
from __future__ import annotations

import ast
import __future__
import collections.abc
from collections import defaultdict
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


FUNCTIONS = {
    "Batch", "lbox", "lbox_point", "surface_z", "build_street_lamp",
    "add_lamp", "build_church",
}
CONSTANTS = {
    "PI", "TAU", "ROAD_X", "ROAD_Y", "VIALE_SPANS", "ROAD_WIDTH",
    "VIALE_WIDTH", "SIDEWALK_REACH", "MOWN_BLOCKS", "PRIVATE_GARDENS",
    "PARKS", "PLAYGROUND_CENTER", "PLAYGROUND_DECK", "MAT_Z", "PIAZZA_Z",
    "PIAZZA_RING_Z", "LAWN_Z", "PARK_LAWN_Z", "GARDEN_Z", "ROAD_TOP",
    "SIDEWALK_TOP", "RELIEF_Z",
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
        "math": math, "collections": collections,
        "make_cube": Mock(), "add_text": Mock(), "add_tube": Mock(),
        "build_tricolore": Mock(),
    }
    code = compile(tree, "genera_citta.py", "exec",
                   flags=__future__.annotations.compiler_flag, dont_inherit=True)
    exec(code, scope)
    return scope, SimpleNamespace(**scope)


scope, city = load_geometry()


def batches():
    return defaultdict(lambda: city.Batch("Test", None, None))


def local_xy(x, y, cx=-48.0, cy=-17.5, yaw=math.pi / 2):
    dx, dy = x - cx, y - cy
    return (dx * math.cos(yaw) + dy * math.sin(yaw),
            -dx * math.sin(yaw) + dy * math.cos(yaw))


def build_church_with(scope_updates=None):
    group = batches()
    updates = scope_updates or {}
    with patch.dict(scope, updates):
        city.build_church(group, defaultdict(lambda: None), None)
    return group


class LampBaseTests(unittest.TestCase):
    def test_pedestal_and_pole_start_at_surface_z(self):
        floor = 0.21
        group = batches()
        with patch.dict(scope, surface_z=lambda _x, _y: floor):
            city.add_lamp(group, -4.0, 8.0, height=4.4, ornate=True, yaw=.6)
        gold = group["metal_gold"]
        # Il solo componente dorato della base è il primo cilindro: dal
        # pavimento al suo piano superiore, senza aria sotto e senza interro.
        self.assertAlmostEqual(min(v[2] for v in gold.verts), floor)
        self.assertAlmostEqual(max(v[2] for v in gold.verts), floor + .18)
        pole_z = [v[2] for v in group["metal"].verts]
        self.assertAlmostEqual(min(pole_z), floor)
        self.assertGreater(max(pole_z), floor + 4.4)

    def test_wrapper_passa_quota_e_yaw_al_costruttore(self):
        builder = Mock()
        with patch.dict(scope, surface_z=lambda x, y: x - y,
                        build_street_lamp=builder):
            city.add_lamp(None, 4.0, -2.0, height=5.4, ornate=True, yaw=1.2)
        builder.assert_called_once_with(None, 4.0, -2.0, 5.4, yaw=1.2,
                                        ornate=True, ground_z=6.0)


class PieveSagratoLampTests(unittest.TestCase):
    def test_lampioni_sagrato_liberi_dai_cipressi_e_appoggiati(self):
        lamps = []

        def record(_batches, x, y, **kwargs):
            lamps.append((x, y, kwargs))

        build_church_with({"build_street_lamp": record})
        self.assertEqual(len(lamps), 2)
        local_positions = []
        for x, y, kwargs in lamps:
            lx, ly = local_xy(x, y)
            local_positions.append((lx, ly))
            self.assertAlmostEqual(abs(lx), 4.5)
            self.assertAlmostEqual(ly, -18.4)
            self.assertAlmostEqual(kwargs["ground_z"], .21)
            self.assertAlmostEqual(kwargs["height"], 4.4)
            # Il cipresso più vicino ha chioma di raggio 1,15 m; resta un
            # margine netto anche considerando il raggio del palo.
            nearest_trunk = min(math.hypot(lx - tx, ly + 19.0)
                                for tx in (-6.6, 6.6))
            self.assertGreater(nearest_trunk, 1.5)
        self.assertAlmostEqual(local_positions[0][0], -local_positions[1][0])


class ChurchClockTests(unittest.TestCase):
    def test_quadranti_opposti_sullo_stesso_campanile(self):
        clock_frames = []
        real_lbox = city.lbox

        def record_lbox(batch, cx, cy, yaw, x, y, z, sx, sy, sz):
            if batch.name == "Test" and (sx, sy, sz) == (1.38, .08, 1.38):
                clock_frames.append((x, y, z, yaw))
            return real_lbox(batch, cx, cy, yaw, x, y, z, sx, sy, sz)

        group = batches()
        with patch.dict(scope, lbox=record_lbox):
            city.build_church(group, defaultdict(lambda: None), None)
        self.assertEqual(len(clock_frames), 2)
        tx, ty = 7.9, -13.6
        self.assertEqual({round(y - ty, 2) for _x, y, _z, _yaw in clock_frames},
                         {-1.74, 1.74})
        self.assertTrue(all(abs(x - tx) < 1e-9 and abs(z - 14.2) < 1e-9
                            for x, _y, z, _yaw in clock_frames))
        self.assertTrue(all(abs(yaw - math.pi / 2) < 1e-9
                            for _x, _y, _z, yaw in clock_frames))


if __name__ == "__main__":
    unittest.main()
