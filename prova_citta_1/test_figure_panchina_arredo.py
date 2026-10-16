"""Esattamente i tre interventi della venticinquesima versione; non richiede Blender.

Le funzioni geometriche sono estratte dal generatore via AST, come negli altri
test leggeri della città: nessun file .blend viene aperto o modificato. Una
sotto classe di `Batch` annota le primitive ricevute, così ogni verifica
confronta quote e ingombri con quello che lo script costruisce davvero.

1. `add_person`/`add_bicycle` con `surface_z`: le figure in piedi avevano i
   piedi sull'origine zero del generatore, non sulla superficie. Nel
   lastricato della piazza affondavano di 21 cm, sul tappeto di gomma del
   parco giochi di 19 cm e sul rilievo della campagna galleggiavano di 6 cm;
   le biciclette parcheggiate affondavano di 11 cm nel marciapiede o
   galleggiavano di 6 cm sulla campagna. Ora ogni figura e ogni mezzo
   poggia sulla quota della superficie che ha sotto.
2. `build_playground`: la panchina era piantata dentro la sabbiera — la
   gamba destra e lo schienale passavano nel traverso ovest del telaio di
   legno (x 52,59-52,81) — e restavano incrociati. Ora la panchina sta
   nell'angolo sud-ovest del tappeto, libera dalla sabbiera e dalla
   cavalcavallo.
3. `build_trees_and_park`/`build_gardens`: l'arredo dei parchi e i vasi
   fioriti galleggiavano. Le aiuole avevano il cordolo sospeso 6,5 cm sopra
   il prato, i paletti luminosi 10 cm e la fontanella 2 cm; i vasi affondano
   nel marciapiede, galleggiavano 15 cm sul rilievo e uno era piantato in
   mezzo alla carreggiata. Ora tutto poggia sulla superficie che ha sotto.
"""
from __future__ import annotations

from collections import defaultdict
import __future__
import ast
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class _BpyStub:
    """Sostituisce `bpy` solo per le annotazioni di tipo di `Batch`."""

    class types:
        Material = object
        Collection = object
        Object = object


FUNCTIONS = {
    "Batch", "lbox", "lbox_point", "lbox_tilt", "add_person", "add_bicycle",
    "surface_z", "build_street_life", "make_bench", "build_playground",
    "build_sandbox", "build_spring_ride", "build_trees_and_park",
    "build_gardens", "spans_outside",
}
CONSTANTS = {
    "ROAD_X", "ROAD_Y", "VIALE_SPANS", "ROAD_WIDTH", "VIALE_WIDTH",
    "SIDEWALK_REACH", "MOWN_BLOCKS", "PRIVATE_GARDENS", "PARKS",
    "PLAYGROUND_CENTER", "PLAYGROUND_DECK", "ROAD_TOP", "SIDEWALK_TOP",
    "LAWN_Z", "PARK_LAWN_Z", "GARDEN_Z", "PIAZZA_Z", "PIAZZA_RING_Z",
    "MAT_Z", "RELIEF_Z", "POND_CENTER", "BRIDGE_Y_OFFSET",
}

TUBES = []


def record_tube(batch, points, radius, segments=8):
    """Finto `add_tube` che annota i tubi: bastano i punti e il raggio."""
    TUBES.append({"batch": batch, "points": list(points), "radius": radius})


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
    import random
    scope = {"math": math, "random": random, "PI": math.pi, "TAU": math.tau,
             "bpy": _BpyStub, "make_cube": Mock(), "add_text": Mock(),
             "add_tube": record_tube,
             # Non servono al tema: si sostituiscono per non tirare dentro
             # scooter, furgone, cassonetti, edicola e panni stesi.
             "add_scooter": Mock(), "add_van": Mock(),
             "add_waste_container": Mock(), "build_newsstand": Mock(),
             "add_balcony_laundry": Mock()}
    code = compile(tree, "genera_citta.py", "exec",
                   flags=__future__.annotations.compiler_flag, dont_inherit=True)
    exec(code, scope)
    return scope, SimpleNamespace(**scope)


scope, city = load_geometry()


class RecordingBatch(city.Batch):
    """`Batch` che annota anche le primitive ricevute, per poterle verificare."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []

    def box(self, center, size, yaw=0.0):
        self.calls.append({"kind": "box", "center": center, "size": size,
                           "yaw": yaw})
        return super().box(center, size, yaw)

    def cylinder(self, center, radius, depth, segments=16, axis="Z", radius2=None):
        self.calls.append({"kind": "cylinder", "center": center, "radius": radius,
                           "depth": depth, "axis": axis})
        return super().cylinder(center, radius, depth, segments, axis, radius2)

    def sphere(self, center, radius, scale=(1.0, 1.0, 1.0), segments=16, rings=8):
        self.calls.append({"kind": "sphere", "center": center, "radius": radius})
        return super().sphere(center, radius, scale, segments, rings)

    def quad(self, p0, p1, p2, p3):
        self.calls.append({"kind": "quad", "points": (p0, p1, p2, p3)})
        return super().quad(p0, p1, p2, p3)


def batches():
    return defaultdict(lambda: RecordingBatch("Test", None, None))


def pick(calls, shape, **filters):
    """Chiamate di una primitiva, filtrate campo per campo."""
    out = []
    for call in calls:
        if call["kind"] != shape:
            continue
        if not matches(call, filters):
            continue
        out.append(call)
    return out


def matches(call, filters):
    """Confronto campo per campo, tollerante sui valori float."""
    for name, value in filters.items():
        got = call[name]
        if isinstance(value, (tuple, list)):
            if len(got) != len(value):
                return False
            for a, b in zip(got, value):
                if abs(a - b) > 1e-9:
                    return False
        elif abs(got - value) > 1e-9:
            return False
    return True


def box_span(call):
    """Ingombro in pianta e in quota di un box, con lo yaw già applicato."""
    (cx, cy, cz), (sx, sy, sz) = call["center"], call["size"]
    co, si = math.cos(call["yaw"]), math.sin(call["yaw"])
    xs, ys = [], []
    for ix in (-0.5, 0.5):
        for iy in (-0.5, 0.5):
            xs.append(cx + ix * sx * co - iy * sy * si)
            ys.append(cy + ix * sx * si + iy * sy * co)
    return (min(xs), max(xs), min(ys), max(ys), cz - sz / 2, cz + sz / 2)


def spans_overlap(a, b):
    """Due ingombri si sovrappongono se si incrociano su tutti e tre gli assi."""
    return (a[0] < b[1] and a[1] > b[0] and a[2] < b[3] and a[3] > b[2]
            and a[4] < b[5] and a[5] > b[4])


class SuperficiTests(unittest.TestCase):
    """`surface_z` restituisce la quota di quello che c'è davvero sotto."""

    def test_le_quote_delle_superfici(self):
        attese = {
            (0.0, 0.0): 0.2125,        # lastre della piazza
            (0.0, -13.2): 0.16,       # cornice di pietra intorno al lastricato
            (52.0, -50.0): 0.19,      # tappeto di gomma del parco giochi
            (23.0, 0.0): 0.05,        # carreggiata
            (28.5, 0.0): 0.11,        # marciapiede
            (-12.0, -20.0): 0.02,     # prato urbano tagliato a strisce
            (-58.0, 60.0): 0.08,      # prato del Parco delle Rose
            (40.0, 17.0): 0.06,       # prato del giardino privato
            (-40.5, -16.0): -0.06,    # rilievo della campagna
        }
        for (x, y), quota in attese.items():
            with self.subTest(punto=(x, y)):
                self.assertAlmostEqual(city.surface_z(x, y), quota, places=9)

    def test_il_viale_ha_dieci_metri_di_carreggiata(self):
        # Il viale c'è anche a nord del sagrato: a quota -60 m la
        # carreggiata è larga dieci metri e il marciapiede arriva a 7,375.
        self.assertAlmostEqual(city.surface_z(4.9, -60.0), 0.05, places=9)
        self.assertAlmostEqual(city.surface_z(6.4, -60.0), 0.11, places=9)
        self.assertAlmostEqual(city.surface_z(8.0, -95.0), -0.06, places=9)


class FigureTests(unittest.TestCase):
    """Le figure e le biciclette poggiano sulla superficie che hanno sotto."""

    def folla(self):
        """Esegue la vita di strada e restituisce le chiamate registrate."""
        persone = Mock(wraps=city.add_person)
        biciclette = Mock(wraps=city.add_bicycle)
        with patch.dict(scope, add_person=persone, add_bicycle=biciclette):
            city.build_street_life(batches(), defaultdict(lambda: None), None)
        return persone.call_args_list, biciclette.call_args_list

    def test_i_piedi_delle_figure_in_piedi_sono_sulla_superficie(self):
        for x, y in ((0.0, 0.0), (50.6, -53.4), (23.0, 5.0), (-40.5, -16.0),
                     (40.0, 17.0), (-58.0, 60.0), (28.5, 14.0)):
            with self.subTest(punto=(x, y)):
                g = city.surface_z(x, y)
                group = batches()
                city.add_person(group, x, y, 0.0, "cloth_red", "cloth_blue",
                                1.0, ground_z=g)
                piedi = min(v[2] for v in group["cloth_blue"].verts)
                self.assertAlmostEqual(piedi, g, places=6)
                # La testa sale con il piano: 1,52 m sopra i piedi.
                testa = sum(v[2] for v in group["skin"].verts) / len(group["skin"].verts)
                self.assertAlmostEqual(testa, g + 1.52, places=6)

    def test_le_ruote_delle_biciclette_sono_sulla_superficie(self):
        for x, y in ((23.0, -12.0), (16.8, 12.6), (-38.6, -20.0), (-12.0, -20.0)):
            with self.subTest(punto=(x, y)):
                g = city.surface_z(x, y)
                group = batches()
                del TUBES[:]
                city.add_bicycle(group, x, y, 0.0, "cloth_red", ground_z=g)
                basso = min(min(p[2] for p in t["points"]) - t["radius"]
                            for t in TUBES)
                self.assertAlmostEqual(basso, g, places=6)

    def test_la_folla_del_generatore_passa_la_quota_giusta(self):
        persone, biciclette = self.folla()
        # Ventiquattro pedoni, due seduti in piazza, il bimbo, l'adulto al
        # parco giochi e i tre ciclisti: il numero non cambia.
        self.assertEqual(len(persone), 31)
        self.assertEqual(len(biciclette), 9)
        for call in persone:
            x, y = call.args[1], call.args[2]
            if call.kwargs.get("seated"):
                continue
            with self.subTest(pedone=(x, y)):
                self.assertIn("ground_z", call.kwargs)
                self.assertAlmostEqual(call.kwargs["ground_z"],
                                       city.surface_z(x, y), places=9)
        for call in biciclette:
            x, y = call.args[1], call.args[2]
            with self.subTest(bicicletta=(x, y)):
                self.assertIn("ground_z", call.kwargs)
                self.assertAlmostEqual(call.kwargs["ground_z"],
                                       city.surface_z(x, y), places=9)

    def test_il_ciclista_siede_sulla_sella_della_sua_bicicletta(self):
        persone, _ = self.folla()
        seduti = [c for c in persone
                  if c.kwargs.get("seated") and c.kwargs.get("seat_z", 0) > 0.9]
        # I tre ciclisti: la sella è a 0,98 m sopra la superficie.
        self.assertEqual(len(seduti), 3)
        for call in seduti:
            with self.subTest(ciclista=call.args[1:3]):
                g = call.kwargs["seat_z"] - 0.98
                self.assertAlmostEqual(call.kwargs["foot_z"], g + 0.38, places=9)
                self.assertAlmostEqual(g, city.surface_z(call.args[1],
                                                         call.args[2]), places=9)


class PanchinaTests(unittest.TestCase):
    """La panchina del parco giochi non è più incrociata con la sabbiera."""

    def setUp(self):
        # Panchina, sabbiera e cavalcavallo in batch separati: così si
        # confrontano i loro ingombri senza confondere il legno della
        # panchina con quello del telaio della sabbiera.
        self.play = batches()
        self.panchina = batches()
        self.sabbiera = batches()
        self.cavallo = batches()

        def bench(group, x, y, yaw=0.0):
            return city.make_bench(self.panchina, x, y, yaw)

        def sandbox(group, x, y, yaw=0.0):
            return city.build_sandbox(self.sabbiera, x, y, yaw)

        def spring(group, x, y, yaw=0.0):
            return city.build_spring_ride(self.cavallo, x, y, yaw)

        with patch.dict(scope, make_bench=bench, build_sandbox=sandbox,
                        build_spring_ride=spring):
            city.build_playground(self.play, 52.0, -50.0)

    @staticmethod
    def spans(group):
        out = []
        for batch in group.values():
            out.extend(box_span(c) for c in batch.calls if c["kind"] == "box")
        return out

    def test_la_panchina_non_tocca_la_sabbiera(self):
        panchina = self.spans(self.panchina)
        sabbiera = self.spans(self.sabbiera)
        self.assertTrue(panchina, "la panchina non è stata costruita")
        self.assertTrue(sabbiera, "la sabbiera non è stata costruita")
        for a in panchina:
            for b in sabbiera:
                with self.subTest(legno=a, sabbia=b):
                    self.assertFalse(spans_overlap(a, b))

    def test_la_panchina_non_tocca_la_cavalcavallo(self):
        panchina = self.spans(self.panchina)
        cavallo = self.spans(self.cavallo)
        self.assertTrue(cavallo, "la cavalcavallo non è stata costruita")
        for a in panchina:
            for b in cavallo:
                with self.subTest(legno=a, cavallo=b):
                    self.assertFalse(spans_overlap(a, b))

    def test_la_panchina_resta_sul_tappeto_di_gomma(self):
        panchina = self.spans(self.panchina)
        # Il tappeto è 12 x 9 m centrato su (52, -50).
        for a in panchina:
            with self.subTest(legno=a):
                self.assertGreaterEqual(a[0], 46.0)
                self.assertLessEqual(a[1], 58.0)
                self.assertGreaterEqual(a[2], -54.5)
                self.assertLessEqual(a[3], -45.5)

    def test_il_tappeto_e_ancora_piu_in_alto_del_prato(self):
        gomma = self.spans(self.play)
        gomma = [s for s in gomma if s[5] < 0.2]
        self.assertTrue(gomma)
        # La superficie del tappeto è a 0,19 m, il prato del parco a 0,08 m.
        self.assertAlmostEqual(max(s[5] for s in gomma), 0.19, places=9)


class ArredoTests(unittest.TestCase):
    """L'arredo dei parchi e i vasi fioriti poggiano sulla superficie."""

    @classmethod
    def setUpClass(cls):
        cls.group = batches()
        city.build_trees_and_park(cls.group, defaultdict(lambda: None), None, None)

    def test_le_aiuole_sono_piantate_nel_prato(self):
        cordoli = [c for c in self.group["curb"].calls
                   if c["kind"] == "box" and abs(c["size"][2] - 0.25) < 1e-9]
        self.assertEqual(len(cordoli), 8)      # quattro aiuole per parco
        for call in cordoli:
            with self.subTest(aiuola=call["center"]):
                fondo = call["center"][2] - call["size"][2] / 2
                self.assertAlmostEqual(fondo, 0.08, places=9)

    def test_gli_arbusti_appoggiano_sul_cordolo(self):
        arbusti = [c for c in self.group["leaf_light"].calls
                   if c["kind"] == "sphere" and abs(c["radius"] - 0.28) < 1e-9]
        self.assertEqual(len(arbusti), 56)     # sette per aiuola, otto aiuole
        for call in arbusti:
            with self.subTest(arbusto=call["center"]):
                # Raggio 0,28 m e centro a 0,61 m: il fondo è a 0,33 m, il
                # bordo superiore del cordolo.
                self.assertAlmostEqual(call["center"][2] - 0.28, 0.33, places=9)

    def test_i_paletti_luminosi_sono_piantati_nel_prato(self):
        pali = [c for c in self.group["metal"].calls
                if c["kind"] == "cylinder" and abs(c["radius"] - 0.075) < 1e-9]
        self.assertEqual(len(pali), 8)         # quattro per parco
        for call in pali:
            with self.subTest(paletto=call["center"]):
                fondo = call["center"][2] - call["depth"] / 2
                self.assertAlmostEqual(fondo, 0.08, places=9)

    def test_la_fontanella_poggia_sul_prato(self):
        vasca = [c for c in self.group["concrete"].calls
                 if c["kind"] == "cylinder" and abs(c["radius"] - 1.15) < 1e-9]
        self.assertEqual(len(vasca), 1)
        fondo = vasca[0]["center"][2] - vasca[0]["depth"] / 2
        self.assertAlmostEqual(fondo, 0.08, places=9)
        acqua = [c for c in self.group["water"].calls
                 if c["kind"] == "cylinder" and abs(c["radius"] - 0.90) < 1e-9]
        self.assertEqual(len(acqua), 1)
        # L'acqua sta incastrata nel bordo della vasca (0,68 m).
        self.assertLessEqual(acqua[0]["center"][2] - acqua[0]["depth"] / 2, 0.68)
        self.assertGreater(acqua[0]["center"][2] + acqua[0]["depth"] / 2, 0.68)

    def test_i_vasi_fioriti_poggiano_sulla_superficie(self):
        group = batches()
        city.build_gardens(group)
        vasi = [c for c in group["terracotta"].calls if c["kind"] == "cylinder"]
        self.assertEqual(len(vasi), 18)        # sei gruppi da tre vasi
        for call in vasi:
            cx, cy, cz = call["center"]
            with self.subTest(vaso=call["center"]):
                fondo = cz - call["depth"] / 2
                self.assertAlmostEqual(fondo, city.surface_z(cx, cy), places=9)
                # Nessun vaso piantato in mezzo alla carreggiata.
                self.assertNotAlmostEqual(city.surface_z(cx, cy), 0.05, places=6)


if __name__ == "__main__":
    unittest.main()
