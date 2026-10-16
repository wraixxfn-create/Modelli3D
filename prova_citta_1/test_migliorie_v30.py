"""Esattamente tre migliorie della trentesima versione; non richiede Blender.

Le funzioni reali sono estratte dal generatore via AST e le primitive vengono
verificate con `Batch`: non si apre né si sovrascrive `citta.blend`.

1. I becchi delle tre anatre seguono ora il loro yaw e partono dentro la testa.
2. Le ruote dei cassonetti sono visibili fuori dalle fiancate, collegate al
   basamento e sempre appoggiate alla quota `ground_z`.
3. I lampioni della piazza non invadono più le carreggiate e i bracci puntano
   verso la piazza, la strada o il sagrato che devono illuminare.
"""
from __future__ import annotations

import ast
import __future__
from collections import defaultdict
import math
import random
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


FUNCTIONS = {
    "Batch", "lbox", "lbox_tilt", "lbox_point", "surface_z",
    "add_oriented_cone", "in_bridge_corridor", "build_pond",
    "add_waste_container", "add_lamp", "build_street_lamp",
    "build_town_square", "build_town_hall", "build_viale_head",
}
CONSTANTS = {
    "ROAD_X", "ROAD_Y", "VIALE_SPANS", "ROAD_WIDTH", "VIALE_WIDTH",
    "SIDEWALK_REACH", "MOWN_BLOCKS", "PRIVATE_GARDENS", "PARKS",
    "PLAYGROUND_CENTER", "PLAYGROUND_DECK", "ROAD_TOP", "SIDEWALK_TOP",
    "LAWN_Z", "PARK_LAWN_Z", "GARDEN_Z", "PIAZZA_Z", "PIAZZA_RING_Z",
    "MAT_Z", "RELIEF_Z", "POND_CENTER", "BRIDGE_HALF_SPAN",
    "BRIDGE_Y_OFFSET", "BRIDGE_HALF_WIDTH", "CAFFE_FLOOR_Z",
    "CAFFE_TABLES", "CAFFE_CHAIRS",
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
        "math": math, "random": random, "PI": math.pi, "TAU": math.tau,
        # Dipendenze estranee ai tre interventi: vengono intercettate nei test.
        "add_tube": Mock(), "build_pond_bridge": Mock(),
        "make_cube": Mock(), "add_text": Mock(), "make_bench": Mock(),
        "make_cafe_table": Mock(), "make_cafe_chair": Mock(),
        "add_person": Mock(), "add_front_window": Mock(),
        "add_hip_roof": Mock(), "build_tricolore": Mock(),
    }
    code = compile(tree, "genera_citta.py", "exec",
                   flags=__future__.annotations.compiler_flag, dont_inherit=True)
    exec(code, scope)
    return scope, SimpleNamespace(**scope)


scope, city = load_geometry()


def batches():
    return defaultdict(lambda: city.Batch("Test", None, None))


def assert_heading(test, yaw, dx, dy):
    """Verifica che l'asse locale +X sia rivolto verso (dx, dy)."""
    length = math.hypot(dx, dy)
    test.assertGreater(length, 0.0)
    test.assertAlmostEqual(math.cos(yaw), dx / length)
    test.assertAlmostEqual(math.sin(yaw), dy / length)


def assert_valid_meshes(test, group):
    for batch in group.values():
        test.assertEqual(len(batch.faces), len(batch.smooth))
        test.assertTrue(all(math.isfinite(value) for vertex in batch.verts
                            for value in vertex))
        test.assertTrue(all(0 <= index < len(batch.verts)
                            for face in batch.faces for index in face))


class DuckBeakTests(unittest.TestCase):
    DUCKS = ((-1.0, 0.5, 0.6), (1.3, -0.8, 2.4), (0.2, 1.8, 4.1))

    def test_cono_orientato_con_base_perpendicolare_all_asse(self):
        batch = city.Batch("Becco", None, None)
        base, tip, radius = (1.0, -2.0, 0.5), (2.0, 1.0, 2.5), 0.045
        city.add_oriented_cone(batch, base, tip, radius, 6)
        self.assertEqual(len(batch.faces), 7)  # sei fianchi e il fondo chiuso
        base_face = batch.faces[-1]
        axis = tuple((tip[i] - base[i]) / math.dist(base, tip) for i in range(3))
        for index in base_face:
            point = batch.verts[index]
            delta = tuple(point[i] - base[i] for i in range(3))
            self.assertAlmostEqual(sum(delta[i] * axis[i] for i in range(3)), 0.0)
            self.assertAlmostEqual(math.dist(point, base), radius)
        self.assertTrue(all(len(face) == 3 for face in batch.faces[:-1]))
        assert_valid_meshes(self, {"beak": batch})

    def test_tutti_i_becchi_seguono_yaw_e_si_innestano_nella_testa(self):
        group = batches()
        calls = []
        real_cone = scope["add_oriented_cone"]

        def record_cone(batch, base, tip, radius, segments=8):
            calls.append((batch, tuple(base), tuple(tip), radius, segments))
            return real_cone(batch, base, tip, radius, segments)

        state = random.getstate()
        try:
            with patch.dict(scope, add_oriented_cone=record_cone,
                            build_pond_bridge=Mock()):
                city.build_pond(group, 0.0, 0.0)
        finally:
            random.setstate(state)

        self.assertEqual(len(calls), len(self.DUCKS))
        for (batch, base, tip, radius, segments), (dx, dy, yaw) in zip(
                calls, self.DUCKS):
            self.assertIs(batch, group["beak"])
            self.assertAlmostEqual(radius, 0.045)
            self.assertEqual(segments, 6)
            head = (dx + 0.24 * math.cos(yaw),
                    dy + 0.24 * math.sin(yaw), 0.64)
            self.assertAlmostEqual(math.dist(base[:2], head[:2]), 0.055)
            self.assertAlmostEqual(base[2], 0.62)
            self.assertAlmostEqual(tip[2], 0.62)
            assert_heading(self, math.atan2(tip[1] - base[1], tip[0] - base[0]),
                           math.cos(yaw), math.sin(yaw))
            self.assertAlmostEqual(math.dist(base, tip), 0.145)
        assert_valid_meshes(self, group)


class WasteContainerWheelTests(unittest.TestCase):
    def test_ruote_visibili_collegate_e_a_contatto_col_marciapiede(self):
        ground_z = city.SIDEWALK_TOP
        x, y, yaw = 3.0, -4.0, 0.73
        tubes = []

        def record_tube(batch, points, radius, segments=8):
            tubes.append({"batch": batch, "points": [tuple(p) for p in points],
                          "radius": radius, "segments": segments})

        group = batches()
        with patch.dict(scope, add_tube=record_tube):
            city.add_waste_container(group, x, y, yaw, "canvas_green",
                                     ground_z=ground_z)

        tires = [call for call in tubes if call["batch"] is group["rubber"]
                 and math.isclose(call["radius"], 0.075)]
        brackets = [call for call in tubes if call["batch"] is group["metal"]
                    and len(call["points"]) == 2
                    and math.isclose(call["radius"], 0.022)]
        self.assertEqual(len(tires), 4)
        self.assertEqual(len(brackets), 4)
        co, si = math.cos(yaw), math.sin(yaw)
        local_centers = set()
        for tire in tires:
            p0, p1 = tire["points"]
            center = tuple((p0[i] + p1[i]) / 2 for i in range(3))
            self.assertAlmostEqual(center[2] - tire["radius"], ground_z)
            local_x = (center[0] - x) * co + (center[1] - y) * si
            local_y = -(center[0] - x) * si + (center[1] - y) * co
            local_centers.add((round(local_x, 3), round(local_y, 3)))
            # Il fianco esterno sborda dal corpo (semiprofondità 31 cm),
            # ma la ruota conserva una piccola zona d'innesto sotto il bordo.
            self.assertGreater(abs(local_y), 0.31)
            self.assertLess(abs(local_y) - tire["radius"], 0.31)
            self.assertAlmostEqual(abs(local_y) + tire["radius"] - 0.31, 0.105)
        self.assertEqual(local_centers,
                         {(-0.335, -0.34), (-0.335, 0.34),
                          (0.335, -0.34), (0.335, 0.34)})
        tire_centers = [tuple(sum(p[i] for p in call["points"]) /
                              len(call["points"]) for i in range(3))
                        for call in tires]
        for bracket in brackets:
            start = bracket["points"][0]
            self.assertTrue(any(math.dist(start, center) < 1e-9
                                for center in tire_centers))
        assert_valid_meshes(self, group)


class StreetLampTests(unittest.TestCase):
    def record_square_lamps(self):
        calls = []

        def record(_batches, x, y, height=5.0, ornate=False, yaw=0.0):
            calls.append((x, y, height, ornate, yaw))

        group = batches()
        with patch.dict(scope, add_lamp=record, add_tube=Mock(),
                        make_cube=Mock(), add_text=Mock(), make_bench=Mock(),
                        make_cafe_table=Mock(), make_cafe_chair=Mock(),
                        add_person=Mock()):
            city.build_town_square(group, defaultdict(lambda: None), None)
        return calls

    def test_lampioni_della_piazza_su_pavimento_o_marciapiede(self):
        calls = self.record_square_lamps()
        self.assertEqual(len(calls), 12)
        positions = {(x, y) for x, y, *_ in calls}
        self.assertEqual(len(positions), 12)
        floor_heights = [city.surface_z(x, y) for x, y, *_ in calls]
        self.assertEqual(sum(math.isclose(z, city.PIAZZA_Z) for z in floor_heights), 4)
        self.assertEqual(sum(math.isclose(z, city.SIDEWALK_TOP) for z in floor_heights), 8)
        for x, y, _height, _ornate, yaw in calls:
            if abs(x) == 14.0:
                target = (-x, -y)  # verso il centro della piazza
            elif abs(y) == 19.0:
                target = ((-23.0 if x < 0 else 23.0) - x, 0.0)
            else:
                target = (0.0, (-32.0 if y < 0 else 32.0) - y)
            assert_heading(self, yaw, *target)

    def test_lampioni_del_municipio_e_delle_testate_puntano_verso_la_strada(self):
        hall_calls = []

        def record_hall(_batches, x, y, height=5.0, ornate=False, yaw=0.0):
            hall_calls.append((x, y, yaw))

        group = batches()
        with patch.dict(scope, add_lamp=record_hall, make_cube=Mock(),
                        add_text=Mock(), add_front_window=Mock(),
                        add_hip_roof=Mock(), build_tricolore=Mock()):
            city.build_town_hall(group, defaultdict(lambda: None), None)
        self.assertEqual(len(hall_calls), 2)
        self.assertTrue(all(math.isclose(yaw, -math.pi / 2)
                            for _, _, yaw in hall_calls))

        head_calls = []

        def record_head(_batches, x, y, height=5.0, ornate=False, yaw=0.0):
            head_calls.append((x, y, yaw))

        for sign in (-1, 1):
            with patch.dict(scope, add_lamp=record_head, make_bench=Mock()):
                city.build_viale_head(batches(), sign)
        self.assertEqual(len(head_calls), 4)
        for x, y, yaw in head_calls:
            assert_heading(self, yaw, -x, 0.0)

    def test_wrapper_inoltra_yaw_al_costruttore(self):
        light = Mock()
        with patch.dict(scope, build_street_lamp=light):
            city.add_lamp(None, 4.0, -2.0, height=5.4, ornate=True, yaw=1.2)
        light.assert_called_once_with(None, 4.0, -2.0, 5.4,
                                      yaw=1.2, ornate=True, ground_z=city.surface_z(4.0, -2.0))


if __name__ == "__main__":
    unittest.main()
