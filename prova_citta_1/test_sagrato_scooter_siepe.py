"""Tre interventi della versione 28: test geometrici senza dipendenze Blender.

Si eseguono le stesse funzioni del generatore, estratte via AST senza caricare
`bpy`: il sagrato della pieve entra in `surface_z`, gli scooter ricevono la
quota del piano che hanno sotto e la siepe meridionale del centro civico è
piantata nel terreno anziché sospesa nel vuoto.
"""
import __future__
import ast
from collections import defaultdict
import math
from pathlib import Path
import random
import unittest
from unittest.mock import Mock, patch


def load_geometry():
    tree = ast.parse(Path(__file__).with_name("genera_citta.py").read_text())
    functions = {"Batch", "surface_z", "lbox", "lbox_point", "lbox_tilt",
                 "spans_outside", "add_person", "add_bicycle", "add_scooter",
                 "add_van", "add_waste_container", "build_newsstand",
                 "add_balcony_laundry", "build_street_life", "build_gardens",
                 "build_trees_and_park"}
    # Le costanti del generatore non accedono a Blender; si tengono soltanto
    # quelle necessarie alla classificazione delle superfici e alle funzioni
    # richiamate dai tre interventi.
    constants = {"ROAD_X", "ROAD_Y", "VIALE_SPANS", "ROAD_WIDTH", "VIALE_WIDTH",
                 "SIDEWALK_REACH", "MOWN_BLOCKS", "PRIVATE_GARDENS", "PARKS",
                 "PLAYGROUND_CENTER", "PLAYGROUND_DECK", "ROAD_TOP",
                 "SIDEWALK_TOP", "LAWN_Z", "PARK_LAWN_Z", "GARDEN_Z", "PIAZZA_Z",
                 "PIAZZA_RING_Z", "MAT_Z", "RELIEF_Z", "POND_CENTER",
                 "BRIDGE_Y_OFFSET", "LAUNDRY_SHIRTS", "CAFFE_FLOOR_Z"}
    tree.body = [node for node in tree.body
                 if (isinstance(node, (ast.FunctionDef, ast.ClassDef))
                     and node.name in functions)
                 or (isinstance(node, ast.Assign) and any(
                     isinstance(t, ast.Name) and t.id in constants
                     for t in node.targets))]
    scope = {"math": math, "random": random, "PI": math.pi, "TAU": math.tau}
    # `make_cube`, `add_text` e i tubi non servono alla geometria verificata:
    # qui si controllano le quote dei box e le polilinee dei pneumatici.
    for name in ("add_tube", "add_text", "make_cube"):
        scope[name] = Mock()
    exec(compile(tree, "genera_citta.py", "exec",
                 flags=__future__.annotations.compiler_flag, dont_inherit=True),
         scope)
    return scope


city = load_geometry()
# Ciglio del basolato del sagrato: x minimo, x massimo, y minimo, y massimo.
SAGRATO = (-39.4, -27.8, -26.25, -8.75)
PANTS_KEYS = ("cloth_blue", "hair_dark", "cloth_green", "cloth_red")


def batches():
    return defaultdict(lambda: city["Batch"]("Test", None, None))


def in_sagrato(x, y):
    x0, x1, y0, y1 = SAGRATO
    return x0 <= x <= x1 and y0 <= y <= y1


def surface(x, y):
    """Quota della superficie, campionata come fa il generatore."""
    return city["surface_z"](x, y)


def street_life():
    group = batches()
    tubes = Mock()
    with patch.dict(city, add_tube=tubes):
        city["build_street_life"](group, {"white": None}, None)
    return group, tubes.call_args_list


def rings(calls, points_count, radius):
    """Polilinee chiuse di un dato passo: pneumatici di scooter, ruote di bici."""
    return [call.args[1] for call in calls
            if len(call.args[1]) == points_count
            and abs(call.args[2] - radius) < 1e-9]


def ring_center(points):
    return (sum(p[0] for p in points) / len(points),
            sum(p[1] for p in points) / len(points))


def standing_legs(group):
    """Gambe delle figure in piedi: box alti dei batch dei pantaloni."""
    legs = []
    for key in PANTS_KEYS:
        verts = group[key].verts
        for i in range(0, len(verts) - 7, 8):
            box = verts[i:i + 8]
            width = max(p[0] for p in box) - min(p[0] for p in box)
            height = max(p[2] for p in box) - min(p[2] for p in box)
            if height > 0.6 and height > 3 * width:
                legs.append((key,
                             sum(p[0] for p in box) / 8,
                             sum(p[1] for p in box) / 8,
                             min(p[2] for p in box)))
    return legs


class SagratoTests(unittest.TestCase):
    def test_basolato_quotato_in_surface_z(self):
        # Lastricato della pieve: lastra a 0,21 m su tutta la griglia.
        for x, y in ((-33.0, -17.5), (-31.5, -14.0), (-36.0, -24.6),
                     (-39.3, -26.2), (-28.0, -9.0)):
            self.assertAlmostEqual(surface(x, y), 0.21, places=9,
                                   msg="punto %.1f, %.1f" % (x, y))

    def test_ciglio_del_sagrato_e_marciapiede_di_via_23(self):
        # A ovest e a sud il ciglio cade sul rilievo della campagna; a est il
        # basolato copre il marciapiede di via -23, che resta a 0,11 m fuori.
        for x, y in ((-40.5, -16.0), (-39.5, -16.0), (-38.0, -8.0)):
            self.assertAlmostEqual(surface(x, y), -0.06, places=9,
                                   msg="punto %.1f, %.1f" % (x, y))
        # Subito fuori dal ciglio valgono le superfici urbane: il marciapiede
        # di via -23 a est e la fascia di via -32 a sud.
        for x, y in ((-27.1, -22.0), (-27.8, -8.0), (-35.0, -26.5)):
            self.assertAlmostEqual(surface(x, y), 0.11, places=9,
                                   msg="punto %.1f, %.1f" % (x, y))

    def test_superfici_urbane_invariate(self):
        # Il nuovo ciglio non sposta nessuna delle quote già in uso.
        reference = ((0.0, 0.0, 0.2125), (0.0, 13.0, 0.16), (23.0, 0.0, 0.05),
                     (17.75, 0.0, 0.11), (52.0, -50.0, 0.19), (-52.0, 52.0, 0.08),
                     (35.0, 50.0, 0.02), (-35.0, 90.3, 0.06), (200.0, 200.0, -0.06))
        for x, y, quota in reference:
            self.assertAlmostEqual(surface(x, y), quota, places=9,
                                   msg="punto %.1f, %.1f" % (x, y))

    def test_figure_in_piedi_sul_basolato(self):
        group, _ = street_life()
        # Le due figure che stavano davanti alla facciata della pieve avevano
        # le suole 27 cm sotto il lastricato.
        on_sagrato = [leg for leg in standing_legs(group) if in_sagrato(*leg[1:3])]
        self.assertEqual(len(on_sagrato), 4)          # due figure, due gambe
        for key, x, y, bottom in on_sagrato:
            self.assertAlmostEqual(bottom, 0.21, places=9,
                                   msg="gamba %s in %.2f, %.2f" % (key, x, y))

    def test_bicicletta_parcheggiata_sul_basolato(self):
        _, calls = street_life()
        wheels = [pts for pts in rings(calls, 25, 0.03)
                  if in_sagrato(*ring_center(pts))]
        self.assertEqual(len(wheels), 2)              # due ruote della bici
        for pts in wheels:
            # Battistrada a filo del basolato: anello (0,33 m) + sezione 3 cm.
            bottom = min(p[2] for p in pts) - 0.03
            self.assertAlmostEqual(bottom, 0.21, places=9)

    def test_vasi_fioriti_quotati_uno_per_uno(self):
        group = batches()
        with patch.object(group["terracotta"], "cylinder",
                          wraps=group["terracotta"].cylinder) as vases:
            city["build_gardens"](group)
        self.assertEqual(vases.call_count, 18)        # sei file da tre vasi
        rows = {}
        for call in vases.call_args_list:
            (x, y, z), radius, depth = call.args[0], call.args[1], call.args[2]
            rows.setdefault(round(y, 3), []).append(
                (round(x, 3), z - depth / 2, surface(x, y)))
        for y, pots in rows.items():
            for x, bottom, quota in pots:
                # Ogni vaso poggia sulla superficie che ha sotto, anche dove
                # la fila attraversa il ciglio del sagrato.
                self.assertAlmostEqual(bottom, quota, places=9,
                                       msg="vaso %.2f, %.2f" % (x, y))
        # La fila davanti alla pieve resta a cavallo del ciglio: due vasi sul
        # rilievo (0,06 m sotto il piano) e uno sul basolato.
        self.assertAlmostEqual([p[1] for p in sorted(rows[-22.0])][1], 0.21,
                               places=9)
        self.assertAlmostEqual([p[1] for p in sorted(rows[-22.0])][2], 0.11,
                               places=9)


class ScooterTests(unittest.TestCase):
    def test_pneumatici_sulla_superficie(self):
        _, calls = street_life()
        tyres = rings(calls, 21, 0.05)
        self.assertEqual(len(tyres), 6)               # tre scooter, due ruote
        for pts in tyres:
            x, y = ring_center(pts)
            bottom = min(p[2] for p in pts) - 0.05
            # La quota va cercata con lo stesso arrotondamento con cui il
            # generatore campiona il punto: i centri dei cerchi nascono da
            # prodotti per coseni, con residui di 10^-17 sulle coordinate.
            quota = surface(round(x, 6), round(y, 6))
            self.assertAlmostEqual(bottom, quota, places=9,
                                   msg="pneumatico in %.2f, %.2f" % (x, y))
        # Due scooter sui marciapiedi (0,11 m) e uno sul sagrato (0,21 m).
        self.assertEqual(sorted({round(min(p[2] for p in t) - 0.05, 3)
                                 for t in tyres}), [0.11, 0.21])

    def test_scooter_senza_quota_resta_invariato(self):
        # Chiamata senza `ground_z` la geometria resta quella di sempre: il
        # battistrada a quota zero, come nelle prove della versione 13.
        group = batches()
        tyres = Mock()
        with patch.dict(city, add_tube=tyres):
            city["add_scooter"](group, 0, 0, 0.0, "cloth_green")
        rings_ = rings(tyres.call_args_list, 21, 0.05)
        self.assertEqual(len(rings_), 2)
        for pts in rings_:
            self.assertAlmostEqual(min(p[2] for p in pts), 0.05, places=9)


class SiepeTests(unittest.TestCase):
    def hedges(self):
        group = batches()
        with patch.object(group["leaf"], "box",
                          wraps=group["leaf"].box) as leaf_boxes:
            city["build_trees_and_park"](group, {"grass": None}, None, None)
        return [(call.args[0], call.args[1]) for call in leaf_boxes.call_args_list]

    def test_siepe_meridionale_piantata_nel_terreno(self):
        hedges = self.hedges()
        self.assertEqual(len(hedges), 3)              # due laterali e una sud
        south = [h for h in hedges if h[0][1] < 0]
        self.assertEqual(len(south), 1)
        (cx, cy, cz), (sx, sy, sz) = south[0]
        self.assertAlmostEqual(cx, 0.0, places=9)
        self.assertAlmostEqual(cy, -15.6, places=9)
        self.assertAlmostEqual(sx, 25.0, places=9)
        # Il piede scende sotto la quota del prato (0,06 m sotto il piano) e
        # la siepe si alza di un metro dal terreno, come le due laterali.
        self.assertLessEqual(cz - sz / 2, -0.10)
        self.assertAlmostEqual(cz + sz / 2, 0.99, places=9)
        for (hx, hy, hz), (_, _, hsz) in hedges:
            self.assertLessEqual(hz - hsz / 2, surface(hx, hy) + 1e-9,
                                 msg="siepe sospesa in %.1f, %.1f" % (hx, hy))

    def test_lato_nord_libero_per_il_municipio(self):
        # Il volume del municipio comincia a y = 14 m: nessuna siepe in asse
        # deve entrare nella sua muratura.
        for (cx, cy, cz), _ in self.hedges():
            if abs(cx) < 11.0:
                self.assertLessEqual(cy + 0.25, 14.0,
                                     msg="siepe dentro il municipio")


if __name__ == "__main__":
    unittest.main()
