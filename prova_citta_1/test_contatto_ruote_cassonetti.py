"""Esattamente i tre interventi della ventinovesima versione; non richiede Blender.

Le funzioni geometriche sono estratte dal generatore via AST, come negli altri
test leggeri della città: nessun file .blend viene aperto o modificato. I tubi
sono intercettati prima della tessellazione (bastano punti e raggio per le
quote), e le scatole passano dalla classe `Batch` reale.

1. `build_car`, `build_bus`, `add_van`: le ruote erano centrate a quota fissa
   (0,46 m, 0,53 m e 0,43 m), quindi il battistrada scendeva a 3 cm sopra
   zero: affondava nella carreggiata (quota 0,05 m) e nell'asfalto dei
   piazzali (0,055 m), e il furgone restava 4,5 cm sospeso. Ora ogni mezzo
   riceve `ground_z` e il punto più basso dei pneumatici coincide con quella
   quota. Le auto in sosta usano l'asfalto dei piazzali.
2. `add_waste_container`: il cassonetto galleggiava sul piano zero con le
   ruote a 4,5 cm da terra e veniva piazzato sull'incrocio con via -23. Ora
   le ruote poggiano su `ground_z` e i cassonetti stanno sui marciapiedi,
   fuori dalla carreggiata delle vie di quartiere.
"""
from __future__ import annotations

from collections import defaultdict
import __future__
import ast
import math
import random
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


FUNCTIONS = {
    "Batch", "lbox", "lbox_point", "lbox_tilt", "surface_z",
    "build_car", "build_bus", "add_van", "add_waste_container",
    "build_street_life", "build_parking_lots",
}
CONSTANTS = {
    "ROAD_X", "ROAD_Y", "VIALE_SPANS", "ROAD_WIDTH", "VIALE_WIDTH",
    "SIDEWALK_REACH", "MOWN_BLOCKS", "PRIVATE_GARDENS", "PARKS",
    "PLAYGROUND_CENTER", "PLAYGROUND_DECK", "ROAD_TOP", "SIDEWALK_TOP",
    "LAWN_Z", "PARK_LAWN_Z", "GARDEN_Z", "PIAZZA_Z", "PIAZZA_RING_Z",
    "MAT_Z", "RELIEF_Z", "PARKING_ASPHALT_Z", "BUS_POSITION",
}


class MockBatch:
    """Batch che accetta le chiamate del generatore senza `bpy`."""

    def __init__(self, name="Test", material=None, collection=None):
        self.name = name
        self.verts = []
        self.calls = []

    def box(self, center, size, yaw=0.0):
        self.calls.append(("box", center, size))
        self.verts.append(tuple(center))

    def cylinder(self, center, radius, height, segments=16, axis="Z"):
        self.calls.append(("cylinder", center, radius, height))

    def sphere(self, center, radius, scale=(1, 1, 1), segments=12, rings=8):
        self.calls.append(("sphere", center, radius))

    def flush(self):
        pass


TUBES = []


def record_tube(batch, points, radius, segments=8):
    """Finto `add_tube`: annota punti e raggio di ogni tubo."""
    TUBES.append({"batch": batch, "points": [tuple(p) for p in points],
                  "radius": radius})


def load_geometry():
    source = Path(__file__).with_name("genera_citta.py").read_text()
    tree = ast.parse(source)
    kept = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in FUNCTIONS:
            kept.append(node)
        elif isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in CONSTANTS for t in node.targets):
            kept.append(node)
    tree.body = kept
    scope = {"math": math, "random": random, "PI": math.pi, "TAU": 2.0 * math.pi,
             "add_tube": record_tube, "make_cube": Mock(), "add_text": Mock(),
             "add_lamp": Mock(), "make_bench": Mock(), "make_cafe_table": Mock(),
             "make_cafe_chair": Mock(), "add_person": Mock(),
             "add_bicycle": Mock(), "add_scooter": Mock(), "add_van": Mock(),
             "add_waste_container": Mock(), "build_newsstand": Mock(),
             "add_balcony_laundry": Mock(), "build_car": Mock()}
    code = compile(tree, "genera_citta.py", "exec",
                   flags=__future__.annotations.compiler_flag, dont_inherit=True)
    exec(code, scope)
    return scope, SimpleNamespace(**scope)


scope, city = load_geometry()


def batches():
    return defaultdict(lambda: city.Batch("Test", None, None))


def wheel_tubes(radius):
    """Tubi di raggio dato con i loro estremi, per la ruota considerata."""
    return [t for t in TUBES if math.isclose(t["radius"], radius)]


class AutoTests(unittest.TestCase):
    def setUp(self):
        TUBES.clear()

    def test_ruote_auto_sulla_carreggiata(self):
        city.build_car(batches(), 0, 0, 0.0, ground_z=city.ROAD_TOP)
        wheels = wheel_tubes(0.43)
        self.assertEqual(len(wheels), 4)
        for t in wheels:
            # Il battistrada, cioè asse meno raggio, tocca la carreggiata.
            for p in t["points"]:
                self.assertAlmostEqual(p[2] - 0.43, city.ROAD_TOP)

    def test_auto_in_sosta_appoggiata_all_asfalto(self):
        city.build_car(batches(), 0, 0, 0.0, ground_z=city.PARKING_ASPHALT_Z)
        for t in wheel_tubes(0.43):
            for p in t["points"]:
                self.assertAlmostEqual(p[2] - 0.43, city.PARKING_ASPHALT_Z)

    def test_auto_senza_quota_usa_il_piano_zero(self):
        city.build_car(batches(), 0, 0, 0.0)
        for t in wheel_tubes(0.43):
            for p in t["points"]:
                self.assertAlmostEqual(p[2], 0.43)

    def test_quota_ruote_indipendente_dallo_yaw(self):
        heights = []
        for yaw in (0.0, 0.73):
            TUBES.clear()
            city.build_car(batches(), 3.0, -2.0, yaw, ground_z=city.ROAD_TOP)
            heights.append(sorted(p[2] for t in wheel_tubes(0.43) for p in t["points"]))
        self.assertEqual(heights[0], heights[1])


class BusTests(unittest.TestCase):
    def setUp(self):
        TUBES.clear()

    def test_ruote_del_bus_toccano_la_carreggiata(self):
        b = batches()
        city.build_bus(b, *city.BUS_POSITION, ground_z=city.ROAD_TOP)
        wheels = wheel_tubes(0.50)
        self.assertEqual(len(wheels), 4)
        for t in wheels:
            for p in t["points"]:
                self.assertAlmostEqual(p[2] - 0.50, city.ROAD_TOP)
        # Nessun'altra parte del bus scende sotto la carreggiata.
        self.assertGreaterEqual(min(p[2] for batch in b.values() for p in batch.verts),
                                city.ROAD_TOP - 1e-9)

    def test_bus_senza_quota_come_prima(self):
        city.build_bus(batches(), 0, 0, 0)
        for t in wheel_tubes(0.50):
            for p in t["points"]:
                self.assertAlmostEqual(p[2], 0.50)


class FurgoneTests(unittest.TestCase):
    def setUp(self):
        TUBES.clear()

    def rings(self):
        return [t for t in TUBES if len(t["points"]) == 25 and
                math.isclose(t["radius"], 0.055)]

    def test_pneumatici_del_furgone_toccano_la_carreggiata(self):
        city.add_van(batches(), 0, 0, 0.0, "white", ground_z=city.ROAD_TOP)
        rings = self.rings()
        self.assertEqual(len(rings), 4)
        for t in rings:
            lowest = min(p[2] for p in t["points"]) - t["radius"]
            self.assertAlmostEqual(lowest, city.ROAD_TOP)

    def test_furgone_ruote_in_sagoma_con_la_quota(self):
        # Il canale resta a 0,905 m dal mezzeria anche con la nuova quota.
        city.add_van(batches(), 0, 0, 0.0, "white", ground_z=city.ROAD_TOP)
        for t in self.rings():
            self.assertAlmostEqual(abs(t["points"][0][1]) + t["radius"], 0.905)


class CassonettiTests(unittest.TestCase):
    def setUp(self):
        TUBES.clear()

    def test_ruote_del_cassonetto_sul_marciapiede(self):
        b = batches()
        city.add_waste_container(b, 0, 0, 0.0, "canvas_green", ground_z=city.SIDEWALK_TOP)
        wheels = wheel_tubes(0.075)
        self.assertEqual(len(wheels), 4)
        for t in wheels:
            for p in t["points"]:
                self.assertAlmostEqual(p[2] - 0.075, city.SIDEWALK_TOP)
        # Nessuna parte metallica affonda nel marciapiede.
        self.assertGreaterEqual(min(v[2] for v in b["metal"].verts),
                                city.SIDEWALK_TOP - 1e-9)

    def test_cassonetto_senza_quota_tocca_il_piano_zero(self):
        city.add_waste_container(batches(), 0, 0, 0.0, "canvas_green")
        for t in wheel_tubes(0.075):
            for p in t["points"]:
                self.assertAlmostEqual(p[2] - 0.075, 0.0)

    def test_cassonetti_su_marciapiede_fuori_dalla_carreggiata(self):
        with patch.dict(scope, {"add_waste_container": Mock()}) as _:
            wc = scope["add_waste_container"]
            city.build_street_life(batches(), defaultdict(lambda: None), None)
            bins = [c for c in wc.call_args_list]
        self.assertEqual(len(bins), 4)
        for call in bins:
            x, y = call.args[1], call.args[2]
            # Quota del marciapiede e, nello stesso tempo, ground_z passato.
            self.assertAlmostEqual(call.kwargs["ground_z"], city.SIDEWALK_TOP)
            self.assertAlmostEqual(city.surface_z(x, y), city.SIDEWALK_TOP)
            # Nessuna carreggiata delle vie di quartiere né del viale.
            half = city.ROAD_WIDTH / 2
            for rx in city.ROAD_X:
                self.assertGreater(abs(x - rx), half)
            for ry in city.ROAD_Y:
                self.assertGreater(abs(y - ry), half)


class ParcheggioTests(unittest.TestCase):
    def test_auto_del_piazzale_sull_asfalto_della_lastra(self):
        car = Mock()
        make_set = lambda mats_, col, keys: defaultdict(lambda: MockBatch())
        with patch.dict(scope, {"make_batch_set": make_set, "build_car": car}):
            city.build_parking_lots(defaultdict(lambda: None), None, batches())
        calls = car.call_args_list
        self.assertEqual(len(calls), 6)  # tre auto per piazzale
        for call in calls:
            self.assertAlmostEqual(call.kwargs["ground_z"], city.PARKING_ASPHALT_Z)
        # La lastra d'asfalto è centrata a 0,02 m e alta 0,07 m: il suo
        # piano superiore coincide con la quota usata per le auto.
        self.assertAlmostEqual(0.02 + 0.07 / 2, city.PARKING_ASPHALT_Z)


if __name__ == "__main__":
    unittest.main()
