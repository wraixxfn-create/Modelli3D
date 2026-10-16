"""Esattamente i tre interventi della ventiquattresima versione; non richiede Blender.

Le funzioni geometriche sono estratte dal generatore via AST, come negli altri
test leggeri della città: nessun file .blend viene aperto o modificato. Una
sotto classe di `Batch` annota le primitive ricevute e `make_cube` è
intercettato, così ogni verifica confronta quote e ingombri con quello che lo
script costruisce davvero.

1. `build_bus_stop`: la pavimentazione tattile della fermata non era incassata
   nel marciapiede — la guida in pavé sporgeva 3,25 cm, la fascia gialla 5,75 cm
   e i bolli dieci centimetri dal piano (0,11 m) — e il percorso attraversava
   il passaggio libero come un arredo. Ora è a filo: 2 mm la guida e la fascia,
   6 mm i bolli, e resta una pavimentazione, non un mobile che occupa il
   passaggio di 1,775 m.
2. `build_roundabout`: il cordolo dell'isola centrale era un cilindro pieno
   (la calotta a 0,21 m restava sotto il prato a 0,25 m: l'erba debordava dal
   bordo di 4 cm) e la fontanella era un tamburo su cui stava stesa una lamina
   d'acqua, senza bacino. Ora il cordolo è un anello con parete alto a 0,31 m
   che contiene il prato, e la fontana ha fondo, bordo e acqua dentro la
   vasca, 16 cm sotto il filo.
3. `build_church`: l'edicola votiva era piantata nel fianco nord della navata,
   dentro il basamento in pietra — il fondo del corpo a 0,55 m, dodici
   centimetri sotto la quota del basamento (0,67 m) — e guardava verso la
   campagna, fuori dal sagrato. Ora è appoggiata al basolato del sagrato
   (0,21 m), nell'angolo della facciata, con la porticina a portata di mano.
"""
from __future__ import annotations

from collections import defaultdict
import __future__
import ast
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class _BpyStub:
    """Sostituisce `bpy` solo per le annotazioni di tipo di `Batch`."""

    class types:
        Material = object
        Collection = object
        Object = object


FUNCTIONS = {
    "Batch", "lbox", "lbox_point", "add_annulus", "in_sector",
    "add_ring_slab", "add_ring_curb", "build_roundabout", "build_bus_stop",
    "build_bus", "build_bus_shelter", "make_bench", "build_church",
    "build_street_lamp",
}
CONSTANTS = {"BUS_STOP_BOUNDS", "BUS_POSITION", "ROAD_TOP"}


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
             "add_tube": Mock()}
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

    def cone(self, center, radius_bottom, radius_top, depth, segments=16, axis="Z"):
        self.calls.append({"kind": "cylinder", "center": center,
                           "radius": radius_bottom, "depth": depth, "axis": axis})
        return super().cone(center, radius_bottom, radius_top, depth, segments, axis)

    def ring(self, center, radius, tube, segments=40, tube_segments=8):
        self.calls.append({"kind": "ring", "center": center, "radius": radius,
                           "tube": tube})
        return super().ring(center, radius, tube, segments, tube_segments)

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


def face_covers(batch, point):
    """Vero se una faccia della batch copre il punto in pianta."""
    for face in batch.faces:
        pts = [batch.verts[i] for i in face]
        signs = []
        for i in range(len(pts)):
            ax, ay = pts[i][0], pts[i][1]
            bx, by = pts[(i + 1) % len(pts)][0], pts[(i + 1) % len(pts)][1]
            signs.append((bx - ax) * (point[1] - ay) - (by - ay) * (point[0] - ax))
        if all(s > 1e-12 for s in signs) or all(s < -1e-12 for s in signs):
            return True
    return False


def highest_face_over(batch, point):
    """Quota massima delle facce che coprono il punto in pianta."""
    best = None
    for face in batch.faces:
        pts = [batch.verts[i] for i in face]
        signs = []
        for i in range(len(pts)):
            ax, ay = pts[i][0], pts[i][1]
            bx, by = pts[(i + 1) % len(pts)][0], pts[(i + 1) % len(pts)][1]
            signs.append((bx - ax) * (point[1] - ay) - (by - ay) * (point[0] - ax))
        if all(s > 1e-12 for s in signs) or all(s < -1e-12 for s in signs):
            top = max(p[2] for p in pts)
            best = top if best is None else max(best, top)
    return best


class FermataTests(unittest.TestCase):
    """Il percorso tattile della fermata è incassato nel marciapiede."""

    PAVING_TOP = 0.11        # quota del piano del marciapiede
    TACTILE_TOP = 0.112      # guida e fascia: 2 mm di rialzo
    STUDS_TOP = 0.116        # bolli: 6 mm di rialzo

    @classmethod
    def setUpClass(cls):
        cls.B = batches()
        city.build_bus_stop(cls.B, defaultdict(lambda: None), None)

    def test_la_guida_tattile_e_a_filo_del_marciapiede(self):
        guide = pick(self.B["tile_b"].calls, "box", **{"center": (48, -75.15, 0.0945)})
        self.assertEqual(len(guide), 1)
        center, size = guide[0]["center"], guide[0]["size"]
        self.assertAlmostEqual(center[2] + size[2] / 2, self.TACTILE_TOP)
        # La guida è incassata: il fondo è sotto il piano del marciapiede.
        self.assertLess(center[2] - size[2] / 2, self.PAVING_TOP)
        self.assertAlmostEqual(size[0], 0.42)
        self.assertAlmostEqual(size[1], 1.35)

    def test_la_fascia_gialla_e_a_filo(self):
        band = pick(self.B["road_yellow"].calls, "box", **{"center": (48, -74.35, 0.0995)})
        self.assertEqual(len(band), 1)
        self.assertAlmostEqual(band[0]["center"][2] + band[0]["size"][2] / 2,
                               self.TACTILE_TOP)
        self.assertLess(band[0]["center"][2] - band[0]["size"][2] / 2, self.PAVING_TOP)
        self.assertAlmostEqual(band[0]["size"][0], 5.8)
        self.assertAlmostEqual(band[0]["size"][1], 0.42)

    def test_i_bolli_sono_bassi_e_solo_sei_millimetri_sopra_il_piano(self):
        studs = [c for c in self.B["road_yellow"].calls
                 if c["kind"] == "cylinder" and abs(c["center"][1] + 74.35) < 1e-9]
        self.assertEqual(len(studs), 13)
        for stud in studs:
            top = stud["center"][2] + stud["depth"] / 2
            self.assertAlmostEqual(top, self.STUDS_TOP)
            self.assertLessEqual(top - self.PAVING_TOP, 0.006 + 1e-9)
            self.assertAlmostEqual(stud["radius"], 0.035)
            self.assertAlmostEqual(stud["depth"], 0.012)
        # I bolli sono in fila regolare lungo il ciglio.
        xs = sorted(round(c["center"][0], 3) for c in studs)
        self.assertAlmostEqual(xs[0], 45.25)
        self.assertAlmostEqual(xs[-1], 45.25 + 12 * 0.458)

    def test_il_percorso_collega_la_pensilina_al_ciglio_senza_occupare_il_passaggio(self):
        guide = pick(self.B["tile_b"].calls, "box")
        self.assertEqual(len(guide), 1)
        y0 = guide[0]["center"][1] - guide[0]["size"][1] / 2
        y1 = guide[0]["center"][1] + guide[0]["size"][1] / 2
        # Parte dalla testata della pensilina e arriva alla fascia sul ciglio.
        self.assertLessEqual(y0, -75.8)
        self.assertGreaterEqual(y1, -74.6)
        a, c, d, e = city.BUS_STOP_BOUNDS
        self.assertGreaterEqual(guide[0]["center"][0] - guide[0]["size"][0] / 2, a)
        self.assertLessEqual(guide[0]["center"][0] + guide[0]["size"][0] / 2, c)
        self.assertGreaterEqual(y0, d)
        self.assertLessEqual(y1, e)
        # Nessun elemento del percorso è un ostacolo: tutto entro 6 mm.
        self.assertLessEqual(max(p[2] for p in self.B["tile_b"].verts),
                              self.TACTILE_TOP + 1e-6)
        self.assertLessEqual(max(p[2] for p in self.B["road_yellow"].verts),
                              self.STUDS_TOP + 1e-6)


class RotatoriaTests(unittest.TestCase):
    """L'isola centrale ha un cordolo vero e una fontana a vasca."""

    CX, CY = 23.0, 32.0
    ISLAND_R = 4.6
    KERB_TOP = 0.31
    LAWN_TOP = 0.25

    @classmethod
    def setUpClass(cls):
        cls.B = batches()
        city.build_roundabout(cls.B, cls.CX, cls.CY)

    def test_il_cordolo_e_un_amento_con_parete_e_non_un_tamburo(self):
        curb = self.B["curb"]
        # Nessuna faccia del cordolo copre il centro dell'isola: il vecchio
        # cilindro pieno chiudeva la calotta sopra il prato.
        self.assertFalse(face_covers(curb, (self.CX, self.CY)))
        # Il filo del cordolo è a 0,31 m e forma un anello fra 4,60 e 4,82 m.
        crest = [v for v in curb.verts if abs(v[2] - self.KERB_TOP) < 1e-9]
        self.assertTrue(crest)
        radii = sorted({round(math.hypot(v[0] - self.CX, v[1] - self.CY), 2)
                        for v in crest})
        self.assertEqual(radii, [self.ISLAND_R, round(self.ISLAND_R + 0.22, 2)])

    def test_il_prato_sta_dentro_al_cordolo(self):
        lawn = pick(self.B["grass"].calls, "cylinder")
        self.assertEqual(len(lawn), 1)
        self.assertAlmostEqual(lawn[0]["center"][2] + lawn[0]["depth"] / 2,
                               self.LAWN_TOP)
        self.assertLess(lawn[0]["center"][2] + lawn[0]["depth"] / 2, self.KERB_TOP)
        # Il manto entra nel cordolo di due centimetri: non si vede il vuoto.
        self.assertAlmostEqual(lawn[0]["radius"], self.ISLAND_R + 0.02)
        self.assertLess(lawn[0]["radius"], self.ISLAND_R + 0.22)

    def test_la_fontana_ha_una_vera_vasca_con_l_acqua_dentro(self):
        water = pick(self.B["water"].calls, "cylinder")
        self.assertEqual(len(water), 1)
        top = water[0]["center"][2] + water[0]["depth"] / 2
        bottom = water[0]["center"][2] - water[0]["depth"] / 2
        # Il filo della vasca sta almeno 10 cm sopra il pelo dell'acqua.
        rim = max(v[2] for v in self.B["concrete"].verts)
        self.assertGreaterEqual(rim - top, 0.10)
        # Il fondo della vasca è coperto dall'acqua e non è un coperchio
        # sopra: il pelo dell'acqua sta sopra il fondo e il fondo affonda
        # dentro il volume dell'acqua.
        floor = highest_face_over(self.B["concrete"], (self.CX, self.CY))
        self.assertLessEqual(floor, top + 1e-9)
        self.assertLess(bottom, floor)
        # Il getto centrale spicca dal fondo e la sfera dorata resta in alto.
        jet = pick(self.B["trim"].calls, "cylinder")
        self.assertEqual(len(jet), 1)
        self.assertLessEqual(jet[0]["center"][2] - jet[0]["depth"] / 2, top + 1e-9)
        self.assertGreater(jet[0]["center"][2] + jet[0]["depth"] / 2, rim)
        spheres = pick(self.B["metal_gold"].calls, "sphere")
        self.assertEqual(len(spheres), 1)
        self.assertGreater(spheres[0]["center"][2], rim)

    def test_i_fiori_dell_isola_restano_appoggiati_al_prato(self):
        flowers = [c for c in self.B["flower"].calls
                   if c["kind"] == "sphere"
                   and math.hypot(c["center"][0] - self.CX,
                                  c["center"][1] - self.CY) < self.ISLAND_R]
        bushes = [c for c in self.B["leaf_light"].calls if c["kind"] == "sphere"]
        self.assertEqual(len(flowers), 14)
        for flower in flowers:
            bottom = flower["center"][2] - flower["radius"] * 0.55
            # Ogni fiore pianta nel suo arbusto, e l'arbusto entra nel prato.
            near = [b for b in bushes
                    if math.dist(b["center"][:2], flower["center"][:2]) < 0.01]
            self.assertEqual(len(near), 1)
            bush_bottom = near[0]["center"][2] - near[0]["radius"] * 0.7
            bush_top = near[0]["center"][2] + near[0]["radius"] * 0.7
            self.assertLess(bush_bottom, self.LAWN_TOP)
            self.assertGreater(bush_bottom, self.LAWN_TOP - 0.10)
            self.assertLess(bottom, bush_top)

    def test_mesh_della_rotatoria_valide(self):
        for batch in self.B.values():
            self.assertEqual(len(batch.faces), len(batch.smooth))
            self.assertTrue(all(math.isfinite(c) for v in batch.verts for c in v))
            for face in batch.faces:
                self.assertGreaterEqual(len(face), 3)
                self.assertTrue(all(0 <= i < len(batch.verts) for i in face))


class PieveTests(unittest.TestCase):
    """L'edicola votiva è appoggiata al basolato del sagrato."""

    CX, CY, YAW = -48.0, -17.5, math.pi / 2

    @classmethod
    def setUpClass(cls):
        cls.B = batches()
        scope["make_cube"].reset_mock()
        city.build_church(cls.B, defaultdict(lambda: None), None)
        cls.cubes = scope["make_cube"].call_args_list

    def basolato(self):
        """Quota e ingombro in pianta del basolato del sagrato."""
        calls = [c for c in self.cubes if c.args and c.args[0] == "Sagrato della pieve"]
        self.assertEqual(len(calls), 1)
        _name, location, size = calls[0].args[:3]
        yaw = calls[0].kwargs.get("yaw", 0.0)
        co, si = math.cos(yaw), math.sin(yaw)
        # Le dimensioni sono nel riferimento del cubo, ruotato con la pieve.
        hx, hy = size[0] / 2, size[1] / 2
        corners = [(location[0] + dx * co - dy * si, location[1] + dx * si + dy * co)
                   for dx, dy in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))]
        return location[2] + size[2] / 2, corners

    def shrine(self):
        """Scatola dell'edicola e della sua porticina, in coordinate locali."""
        boxes = [c for c in self.B["trim"].calls
                 if c["kind"] == "box" and c["size"] == (0.5, 0.9, 1.9)]
        doors = [c for c in self.B["metal_gold"].calls
                 if c["kind"] == "box" and c["size"] == (0.10, 0.5, 0.7)]
        self.assertEqual(len(boxes), 1)
        self.assertEqual(len(doors), 1)
        return boxes[0], doors[0]

    def test_l_edicola_e_appoggiata_al_basolato(self):
        top, corners = self.basolato()
        shrine, door = self.shrine()
        center, size = shrine["center"], shrine["size"]
        base = center[2] - size[2] / 2
        # Il fondo coincide con la quota del basolato: più niente sospensione.
        self.assertAlmostEqual(base, top)
        # E la botola dorata è alla stessa altezza relativa del corpo.
        self.assertAlmostEqual(door["center"][2] - top,
                               center[2] - top - size[2] / 2 + 1.05)

    def test_l_edicola_sta_sul_sagrato_e_non_nel_vuoto(self):
        top, corners = self.basolato()
        shrine, _door = self.shrine()
        # Il corpo è posizionato in un punto noto: lo si riporta al mondo con
        # la stessa trasformazione del generatore.
        world = city.lbox_point(self.CX, self.CY, self.YAW, 7.30, -11.50, 0.0)
        x0 = min(c[0] for c in corners)
        x1 = max(c[0] for c in corners)
        y0 = min(c[1] for c in corners)
        y1 = max(c[1] for c in corners)
        self.assertGreater(world[0], x0)
        self.assertLess(world[0], x1)
        self.assertGreater(world[1], y0)
        self.assertLess(world[1], y1)
        # La facciata della pieve resta a ovest dell'edicola.
        facade = city.lbox_point(self.CX, self.CY, self.YAW, 0.0, -10.0, 0.0)
        self.assertGreater(world[0] - facade[0], 1.0)

    def test_l_edicola_non_e_piu_incalcata_nel_basamento_della_pieve(self):
        top, _corners = self.basolato()
        shrine, _door = self.shrine()
        base = shrine["center"][2] - shrine["size"][2] / 2
        # Il fondo è alla quota del basolato: niente affondamento.
        self.assertAlmostEqual(base, top)
        # Il basamento in pietra della pieve non copre più la sua pianta: il
        # vecchio corpo affondava 12 cm nel calcestruzzo (0,55 m su 0,67 m).
        socle = [c for c in self.B["concrete"].calls
                 if c["kind"] == "box" and c["size"] == (13.5, 20.5, 1.2)]
        self.assertEqual(len(socle), 1)
        east = socle[0]["center"][0] + socle[0]["size"][1] / 2
        self.assertGreater(shrine["center"][0], east)
        # E la nicchia è alla quota del sagrato, non a 58 cm dal basamento.
        self.assertAlmostEqual(base - (-0.06), 0.27)

    def test_mesh_della_pieve_valide(self):
        for batch in self.B.values():
            self.assertEqual(len(batch.faces), len(batch.smooth))
            self.assertTrue(all(math.isfinite(c) for v in batch.verts for c in v))
            for face in batch.faces:
                self.assertGreaterEqual(len(face), 3)
                self.assertTrue(all(0 <= i < len(batch.verts) for i in face))


if __name__ == "__main__":
    unittest.main()
