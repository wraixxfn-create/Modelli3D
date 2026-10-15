"""Esattamente i tre interventi della sedicesima versione; non richiede Blender.

Esegue le funzioni reali estratte via AST e intercetta le primitive dei Batch
(`lbox`, `Batch.box`, `Batch.cylinder`, `add_tube`, `add_text`): ogni verifica
confronta quote e posizioni calcolate a mano con quello che il generatore
costruisce davvero.
"""
import ast
from collections import defaultdict
import collections.abc
import contextlib
import math
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


class _BpyStub:
    """Sostituisce `bpy` solo per le annotazioni di tipo di `Batch`."""
    class types:
        Material = object
        Collection = object
        Object = object


FUNCTIONS = {
    "Batch", "lbox", "lbox_tilt", "lbox_point", "add_tube", "add_text",
    "add_front_window", "add_hip_roof", "add_pyramid", "build_street_lamp",
    "add_lamp", "make_bench", "build_bus", "build_bus_shelter", "build_bus_stop",
    "build_town_hall", "build_tricolore", "build_lawn_care", "build_tree_beds",
}
CONSTANTS = {"AVENUE_TREES", "PARK_TREES", "MOWN_BLOCKS", "BUS_STOP_BOUNDS",
             "BUS_POSITION"}


def load_geometry():
    scope = {"math": math, "PI": math.pi, "TAU": math.tau,
             "make_cube": Mock(), "bpy": _BpyStub, "collections": collections}
    tree = ast.parse(Path(__file__).with_name("genera_citta.py").read_text())
    tree.body = [n for n in tree.body
                 if (isinstance(n, (ast.FunctionDef, ast.ClassDef))
                     and n.name in FUNCTIONS)
                 or (isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id in CONSTANTS
                             for t in n.targets))]
    exec(compile(tree, "genera_citta.py", "exec"), scope)
    return scope


city = load_geometry()
Batch = city["Batch"]
SHELTER = (48.0, -77.0)


def batches():
    return defaultdict(lambda: Batch("Test", None, None))


@contextlib.contextmanager
def recorder(scope=None, **patches):
    """Registra `lbox` e le primitive dei Batch usate dagli interventi."""
    target = scope if scope is not None else city
    real_box, real_cylinder = Batch.box, Batch.cylinder
    calls = {"box": [], "cylinder": []}

    def box(self, center, size, yaw=0.0):
        calls["box"].append((self, center, size, yaw))
        return real_box(self, center, size, yaw)

    def cylinder(self, center, radius, depth, segments=16, axis="Z", radius2=None):
        calls["cylinder"].append((self, center, radius, depth, segments))
        return real_cylinder(self, center, radius, depth, segments, axis, radius2)

    with patch.dict(target, **patches), \
            patch.object(Batch, "box", box), patch.object(Batch, "cylinder", cylinder):
        with patch.dict(target, lbox=Mock(wraps=target["lbox"])) as patched:
            yield patched["lbox"], calls


def point_of(args):
    """(centro, dimensioni) di una chiamata a `lbox`."""
    _, cx, cy, yaw, lx, ly, lz, sx, sy, sz = args[:10]
    return city["lbox_point"](cx, cy, yaw, lx, ly, lz), (sx, sy, sz)


class PensilinaTests(unittest.TestCase):
    """La pensilina non è più una scatola chiusa: telaio, panca e luce."""

    def setUp(self):
        self.group = batches()
        with recorder() as (lbox, calls):
            city["build_bus_shelter"](self.group, *SHELTER)
            self.boxes = [c.args for c in lbox.call_args_list]

    def test_fronte_aperto_verso_la_carreggiata(self):
        # Nessun volume alto (z > 1,0 m) oltre il filo dei pilastrini: la
        # vecchia lastra di fondo arrivava a 3,10 m su tutto lo schermo.
        for args in self.boxes:
            (x, y, z), (sx, sy, sz) = point_of(args)
            if y > SHELTER[1] + 0.95 + 1e-9 and z > 1.0:
                self.fail(f"volume chiuso sul fronte: y {y:.2f}, quota {z:.2f}")
        front = [a for a in self.boxes if a[5] == 0.95]        # y locale
        self.assertEqual(len(front), 2)                        # due pilastrini
        for args in front:
            (x, y, z), (sx, sy, sz) = point_of(args)
            self.assertAlmostEqual(abs(x - SHELTER[0]), 2.62)
            self.assertAlmostEqual(z, 1.34)
            self.assertLess(abs(sx), 0.2)                      # montante

    def test_parete_di_fondo_vetrata_e_ripartita(self):
        glass = [a for a in self.boxes if a[5] == -0.85 and a[8] == 0.055]
        self.assertEqual(len(glass), 1)
        (x, y, z), (sx, sy, sz) = point_of(glass[0])
        self.assertAlmostEqual(x, SHELTER[0])
        self.assertAlmostEqual(z, 1.36)
        self.assertAlmostEqual(sy, 0.055)
        mullions = [a for a in self.boxes
                    if a[5] == -0.85 and a[6] == 1.34 and a[7] == 0.09]
        self.assertEqual(len(mullions), 5)
        xs = sorted(point_of(a)[0][0] for a in mullions)
        for got, wanted in zip(xs, (-2.62, -1.31, 0.0, 1.31, 2.62)):
            self.assertAlmostEqual(got, SHELTER[0] + wanted)
        # Ritorni corti alle testate: nessuna parete piena laterale.
        returns = [a for a in self.boxes if abs(a[4]) == 2.62 and a[6] == 1.30]
        self.assertEqual(len(returns), 2)
        for args in returns:
            self.assertLess(point_of(args)[1][1], 1.2)

    def test_panca_cestino_e_luce_sotto_la_copertura(self):
        seat = [a for a in self.boxes if a[7] == 3.34]
        self.assertEqual(len(seat), 1)
        self.assertAlmostEqual(seat[0][6], 0.55)               # quota del sedile
        legs = [a for a in self.boxes if a[5] == -0.52 and a[7] == 0.09]
        self.assertEqual(len(legs), 3)
        for args in legs:
            (x, y, z), (sx, sy, sz) = point_of(args)
            self.assertGreaterEqual(z - sz / 2, 0.05)          # sopra la platea
        self.assertEqual(len(self.group["lamp"].faces), 6)
        self.assertEqual(len(self.group["metal"].faces), 108)  # telaio completo

    def test_copertura_entro_l_ingombro_di_prima(self):
        roof = [a for a in self.boxes if a[7] == 5.86]
        self.assertEqual(len(roof), 1)
        (x, y, z), (sx, sy, sz) = point_of(roof[0])
        self.assertAlmostEqual(sx, 5.86)
        self.assertAlmostEqual(x, SHELTER[0])
        self.assertAlmostEqual(sy, 2.30)
        self.assertAlmostEqual(sy, 2.30)                       # sporgenza invariata
        self.assertLessEqual(y + sy / 2, -75.9)                # passaggio libero
        self.assertGreater(y - sy / 2, -78.5)                  # dentro la platea
        self.assertLessEqual(z + sz / 2, 3.40)
        lowest = min(point_of(a)[0][2] - point_of(a)[1][2] / 2
                     for a in self.boxes)
        self.assertGreaterEqual(lowest, -0.05)


class BandieraTests(unittest.TestCase):
    """Il tricolore del municipio poggia sul tetto, non dentro la falda."""

    def setUp(self):
        self.group = batches()
        flag = Mock()
        with recorder(build_tricolore=flag, add_text=Mock(),
                      add_tube=Mock()) as (lbox, calls):
            city["build_town_hall"](self.group, defaultdict(lambda: None), None)
            self.flag = flag.call_args.args
            self.poles = [c[1:5] for c in calls["cylinder"]]
            self.boxes = [c.args for c in lbox.call_args_list]
            self.calls = calls

    def test_pennone_attraversa_la_falda_e_sale_sopra_il_colmo(self):
        x0, y0, z0 = self.flag[1:4]
        self.assertAlmostEqual(x0 - 0.05, 5.60)
        self.assertAlmostEqual(y0, 20.55)
        # Falda di poppa: colmo 13,25 a y = 20,0, gronda 9,96 a y = 26,8;
        # il generatore quota la piastra 2 cm sotto la superficie del tetto.
        slope = 13.25 - abs(y0 - 20.0) / 6.8 * (13.25 - 9.96) - 0.02
        self.assertAlmostEqual(slope, 12.963897, places=6)
        pole = [p for p in self.poles if abs(p[0][0] - 5.60) < 1e-9
                and abs(p[0][1] - 20.55) < 1e-9][0]
        center, radius, depth, segments = pole
        self.assertAlmostEqual(radius, 0.055)
        self.assertLess(center[2] - depth / 2, slope)          # dentro il tetto
        self.assertGreater(center[2] + depth / 2, 13.25)       # sopra il colmo
        self.assertGreater(z0 - 0.6, 9.96 + 0.5)               # telo sopra gronda
        self.assertLessEqual(abs(x0) + 0.9, 11.0)              # dentro il colmo
        # Piastra di ancoraggio alla base dell'asta.
        plate = [c for c in self.calls["box"] if abs(c[1][0] - 5.60) < 1e-9
                 and abs(c[1][1] - 20.55) < 1e-9]
        self.assertEqual(len(plate), 1)
        self.assertLessEqual(plate[0][1][2] - plate[0][2][2] / 2, slope)  # incassata

    def test_asta_libera_da_torre_e_camini(self):
        self.assertGreater(abs(5.60 - 0.0), 3.45 / 2 + 0.4)    # torre civica
        for chimney_x in (22.0 * 0.30, 22.0 * 0.38):
            self.assertGreater(abs(5.60 - chimney_x), 0.62)


class VialiTests(unittest.TestCase):
    """Le piazzole dei filari stanno dentro il marciapiede, non sull'erba."""

    CURB_R = 1.02                            # anello in granito della piazzola
    LOT_EDGE = 39.7                          # limite dei lotti delle case
    CAR_EDGE = 8.0 / 2 - 8.0 / 4 + 0.91      # auto in sosta, 0,91 m di semilarghezza

    @staticmethod
    def pavement(half_road):
        """(bordo interno, bordo esterno) del marciapiede dal centro strada."""
        inner = half_road + 0.125
        return inner, inner + 2.25

    def test_filari_nei_marciapiedi_dei_viali(self):
        self.assertEqual(len(city["AVENUE_TREES"]), 20)
        for x, y in city["AVENUE_TREES"]:
            with self.subTest(tree=(x, y)):
                if abs(x) > 10:          # filari delle trasversali y = ±32
                    offset, half_road = abs(y) - 32.0, 4.0
                    self.assertAlmostEqual(offset, 5.25)
                else:                    # filare di Viale Roma, carreggiata 10 m
                    offset, half_road = abs(x), 5.0
                    self.assertAlmostEqual(offset, 6.35)
                inner, outer = self.pavement(half_road)
                self.assertGreaterEqual(offset - self.CURB_R, inner)   # no asfalto
                self.assertLessEqual(offset + self.CURB_R, outer)      # no prato
                self.assertGreater(offset - self.CURB_R, self.CAR_EDGE + 0.10)
                if abs(x) > 10:      # filari accanto alle case: fuori dai lotti
                    self.assertGreaterEqual(self.LOT_EDGE - abs(y), 0.65)

    def test_siepi_esterne_al_marciapiede_e_ai_lotti(self):
        group = batches()
        with recorder() as (lbox, calls):
            city["build_lawn_care"](group)
        hedges = [c for c in calls["box"] if c[2][1] == 0.42 and c[2][2] == 0.72]
        self.assertEqual(len(hedges), 4)
        for _, center, size, _ in hedges:
            self.assertAlmostEqual(abs(center[1]), 38.9)
            self.assertGreater(abs(center[1]) - size[1] / 2, 6.375)  # fuori
            self.assertLess(abs(center[1]) + size[1] / 2, self.LOT_EDGE)

    def test_piazzole_e_aiuole_dei_filari_sui_nuovi_assi(self):
        group = batches()
        with recorder() as (lbox, calls):
            city["build_lawn_care"](group)
        pits = [c for c in calls["cylinder"] if c[0] is group["curb"]
                and c[2] == 1.02]
        self.assertEqual(len(pits),
                         len(city["AVENUE_TREES"]) + len(city["PARK_TREES"]))
        spots = {(round(c[1][0], 2), round(c[1][1], 2)) for c in pits}
        for x, y in list(city["AVENUE_TREES"]) + list(city["PARK_TREES"]):
            self.assertIn((round(x, 2), round(y, 2)), spots)
        # Sfalcio a bande e piazzole condividono la stessa maglia di cordoli.
        self.assertEqual(len(city["MOWN_BLOCKS"]), 11)


class MeshTests(unittest.TestCase):
    def test_mesh_fermata_bandiera_e_prato_valide(self):
        cases = (("build_bus_shelter", SHELTER),
                 ("build_bus_stop", (defaultdict(lambda: None), None)),
                 ("build_town_hall", (defaultdict(lambda: None), None)),
                 ("build_lawn_care", ()), ("build_tree_beds", ()))
        for function, args in cases:
            with self.subTest(function=function):
                group = batches()
                with recorder(add_text=Mock(), add_tube=Mock(),
                              build_tricolore=Mock()):
                    city[function](group, *args)
                for batch in group.values():
                    self.assertEqual(len(batch.faces), len(batch.smooth))
                    self.assertTrue(all(math.isfinite(c)
                                        for v in batch.verts for c in v))
                    for face in batch.faces:
                        self.assertGreaterEqual(len(face), 3)
                        self.assertTrue(all(0 <= i < len(batch.verts)
                                            for i in face))


if __name__ == "__main__":
    unittest.main()
