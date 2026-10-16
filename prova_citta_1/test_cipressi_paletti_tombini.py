"""Esattamente i tre interventi della ventiseiesima versione; non richiede Blender.

Le funzioni geometriche sono estratte dal generatore via AST, come negli altri
test leggeri della città: nessun file .blend viene aperto o modificato. Una
classe `Batch` annota le primitive ricevute (scatole, cilindri, coni, sfere,
tubi), così ogni verifica controlla quote e ingombri rispetto alle superfici reali.

1. `build_countryside`: i cipressi isolati e di filare sulla campagna avevano
   quota fissa (z = 3,0·s) che ignorava il profilo collinare: sul pendio
   (-95, 118) il fusto affondava fino a 1,08 m dentro il terreno, mentre
   sulla piana (118, 20) galleggiava di 27 cm nel vuoto. Ora la quota del
   fusto e del cono di chioma è campionata punto per punto su `relief_height(x, y)`.
2. `build_town_square`: i paletti metallici a protezione del perimetro della
   piazza poggiavano a quota z = 0,16 m, fluttuando dieci centimetri sopra il
   basamento in pietra (z = 0,06 m); a nord (y = 13,7) un paletto a x = 0 era
   piantato in mezzo al gradino superiore della scalinata del municipio; i
   paletti est e ovest non avevano la sfera dorata e non c'era alcuna catena.
   Ora poggiano sul basamento, il varco centrale del municipio è libero e una
   catena bassa a festone collega i paletti contigui.
3. `build_street_life`: un tombino circolare era piantato dentro lo spartitraffico
   fiorito di Viale Roma (x = 0, y = -40 m) sepolto nella siepe, uno stava in
   mezzo a un prato e tre galleggiavano di 10 cm nel rilievo della campagna;
   le quattro caditoie stavano sul marciapiede a quota ribassata di 2,5 cm
   sotto il calpestio. Ora tutti i tombini sono nelle corsie carrabili delle
   strade (z = 0,05 m) e le caditoie alloggiano nella canaletta a filo cordolo.
"""
from __future__ import annotations

from collections import defaultdict
import ast
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class _BpyStub:
    """Sostituisce `bpy` per le annotazioni e le chiamate di base."""

    class types:
        Material = object
        Collection = object
        Object = object

    class data:
        class meshes:
            @staticmethod
            def new(name):
                return Mock()

        class objects:
            @staticmethod
            def new(name, mesh):
                return Mock()


FUNCTIONS = {
    "Batch", "lbox", "lbox_point", "lbox_tilt", "surface_z",
    "hill_height", "smooth01", "relief_height", "spans_outside",
    "build_town_square", "build_street_life", "build_countryside",
}
CONSTANTS = {
    "ROAD_X", "ROAD_Y", "VIALE_SPANS", "ROAD_WIDTH", "VIALE_WIDTH",
    "SIDEWALK_REACH", "MOWN_BLOCKS", "PRIVATE_GARDENS", "PARKS",
    "PLAYGROUND_CENTER", "PLAYGROUND_DECK", "ROAD_TOP", "SIDEWALK_TOP",
    "LAWN_Z", "PARK_LAWN_Z", "GARDEN_Z", "PIAZZA_Z", "PIAZZA_RING_Z",
    "MAT_Z", "RELIEF_Z", "POND_CENTER", "BRIDGE_Y_OFFSET", "HILLS",
    "CAFFE_FLOOR_Z", "CAFFE_TABLES", "CAFFE_CHAIRS",
}

TUBES = []


def record_tube(batch, points, radius, segments=8):
    """Finto `add_tube` che annota i tubi: bastano i punti e il raggio."""
    TUBES.append({"batch": batch, "points": list(points), "radius": radius,
                  "segments": segments})


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
             "add_lamp": Mock(), "make_bench": Mock(),
             "make_cafe_table": Mock(), "make_cafe_chair": Mock(),
             "add_person": Mock(), "add_bicycle": Mock(),
             "add_scooter": Mock(), "add_van": Mock(),
             "add_waste_container": Mock(), "build_newsstand": Mock(),
             "add_balcony_laundry": Mock(), "build_far_horizon": Mock(),
             "build_hill_village": Mock()}
    code = compile(tree, "genera_citta.py", "exec")
    exec(code, scope)
    return scope, SimpleNamespace(**scope)


scope, city = load_geometry()


class MockBatch:
    """Intercetta le primitive geometriche salvando vertici e chiamate."""

    def __init__(self, name: str, material=None, collection=None):
        self.name = name
        self.material = material
        self.collection = collection
        self.verts: list[tuple[float, float, float]] = []
        self.faces: list[tuple[int, ...]] = []
        self.smooth: list[bool] = []
        self.calls: list[dict] = []

    def cylinder(self, center, radius, height, segments=16, axis="Z"):
        self.calls.append({"type": "cylinder", "center": center,
                           "radius": radius, "height": height,
                           "segments": segments, "axis": axis})
        cz = center[2]
        r, h = radius, height
        self.verts.extend([(center[0], center[1], cz - h / 2),
                           (center[0], center[1], cz + h / 2)])
        self.faces.append((len(self.verts) - 2, len(self.verts) - 1))
        self.smooth.append(True)

    def cone(self, center, r1, r2, height, segments=16, axis="Z"):
        self.calls.append({"type": "cone", "center": center,
                           "r1": r1, "r2": r2, "height": height,
                           "segments": segments, "axis": axis})
        cz = center[2]
        self.verts.extend([(center[0], center[1], cz - height / 2),
                           (center[0], center[1], cz + height / 2)])
        self.faces.append((len(self.verts) - 2, len(self.verts) - 1))
        self.smooth.append(True)

    def sphere(self, center, radius, scale=(1, 1, 1), segments=12, rings=8):
        self.calls.append({"type": "sphere", "center": center,
                           "radius": radius, "scale": scale,
                           "segments": segments, "rings": rings})
        self.verts.append(center)
        self.faces.append((len(self.verts) - 1,))
        self.smooth.append(True)

    def ring(self, center, radius, tube, segments=24, tube_segments=6):
        self.calls.append({"type": "ring", "center": center,
                           "radius": radius, "tube": tube})
        self.verts.append(center)
        self.faces.append((len(self.verts) - 1,))
        self.smooth.append(True)

    def box(self, center, size, yaw=0.0):
        self.calls.append({"type": "box", "center": center, "size": size,
                           "yaw": yaw})
        x, y, z = center
        sx, sy, sz = size
        for dx in (-sx / 2, sx / 2):
            for dy in (-sy / 2, sy / 2):
                for dz in (-sz / 2, sz / 2):
                    self.verts.append((x + dx, y + dy, z + dz))
        base = len(self.verts) - 8
        for face in ((0, 2, 6, 4), (1, 5, 7, 3), (0, 4, 5, 1),
                     (2, 3, 7, 6), (0, 1, 3, 2), (4, 6, 7, 5)):
            self.faces.append(tuple(base + i for i in face))
            self.smooth.append(False)

    def poly(self, points, smooth=False):
        self.verts.extend(points)
        self.faces.append(tuple(range(len(self.verts) - len(points), len(self.verts))))
        self.smooth.append(smooth)

    def quad(self, p0, p1, p2, p3, smooth=False):
        self.poly((p0, p1, p2, p3), smooth=smooth)

    def tri(self, p0, p1, p2, smooth=False):
        self.poly((p0, p1, p2), smooth=smooth)


def batches():
    return defaultdict(lambda: MockBatch("Test"))


class CipressiCampagnaTests(unittest.TestCase):
    """Miglioria 1: cipressi isolati e di versante quotati su `relief_height`."""

    CYPRESSES = [
        ((-112, 92), 1.0),
        ((-95, 118), 0.9),
        ((112, 100), 1.1),
        ((100, -112), 1.0),
        ((-115, -100), 0.95),
        ((118, 20), 1.05),
        ((-20, 116), 1.0),
        ((24, -116), 0.9),
    ]

    def setUp(self):
        self.B = batches()
        city.build_countryside(self.B, defaultdict(lambda: None), Mock())
        self.cyls = [c for c in self.B["cypress"].calls if c["type"] == "cylinder"]
        self.cones = [c for c in self.B["cypress"].calls if c["type"] == "cone"]

    def test_numero_di_cipressi_generati(self):
        # 8 cipressi isolati/di filare + 5 cipressi di colle = 13 cilindri e 13 coni
        self.assertEqual(len(self.cyls), 13)
        self.assertEqual(len(self.cones), 13)

    def test_fusto_cipressi_appoggiato_sul_rilievo(self):
        """Il fondo di ciascun fusto parte esattamente dalla quota del terreno."""
        for (x, y), s in self.CYPRESSES:
            matching = [c for c in self.cyls
                        if math.isclose(c["center"][0], x, abs_tol=0.1)
                        and math.isclose(c["center"][1], y, abs_tol=0.1)]
            self.assertEqual(len(matching), 1, f"Cipresso in ({x}, {y}) non trovato")
            call = matching[0]
            center_z = call["center"][2]
            height = call["height"]
            base_z = center_z - height / 2
            ground_z = city.relief_height(x, y)
            self.assertAlmostEqual(base_z, ground_z, places=5,
                                   msg=f"Base cipresso in ({x}, {y}) non coincide con quota terreno")

    def test_chioma_sopra_il_fusto(self):
        """Il cono di chioma si innesta sul fusto e non sotto terra."""
        for (x, y), s in self.CYPRESSES:
            matching = [c for c in self.cones
                        if math.isclose(c["center"][0], x, abs_tol=0.1)
                        and math.isclose(c["center"][1], y, abs_tol=0.1)]
            self.assertEqual(len(matching), 1)
            cone_call = matching[0]
            ground_z = city.relief_height(x, y)
            cone_bottom = cone_call["center"][2] - cone_call["height"] / 2
            self.assertGreater(cone_bottom, ground_z)

    def test_regressione_pendio_e_piana(self):
        """Controlla i due casi estremi: dosso a quota +1.26 e piana a -0.06."""
        # Pendio collinare (-95, 118): prima z=3.0*0.9 - 2.8*0.9 = 0.18 m, affondava di 1.08 m
        z_slope = city.relief_height(-95, 118)
        self.assertGreater(z_slope, 1.20)
        c_slope = [c for c in self.cyls if math.isclose(c["center"][0], -95, abs_tol=0.1)][0]
        base_slope = c_slope["center"][2] - c_slope["height"] / 2
        self.assertAlmostEqual(base_slope, z_slope, places=5)
        self.assertNotAlmostEqual(base_slope, 0.18, places=2)

        # Bordo della piana (118, 20): prima z=0.21 m, galleggiava di 27 cm nel vuoto
        z_plain = city.relief_height(118, 20)
        self.assertAlmostEqual(z_plain, -0.06, places=5)
        c_plain = [c for c in self.cyls if math.isclose(c["center"][0], 118, abs_tol=0.1)][0]
        base_plain = c_plain["center"][2] - c_plain["height"] / 2
        self.assertAlmostEqual(base_plain, z_plain, places=5)
        self.assertNotAlmostEqual(base_plain, 0.21, places=2)


class PalettiPiazzaTests(unittest.TestCase):
    """Miglioria 2: paletti perimetrali della piazza su quota basamento, varco e catena."""

    STONE_BASE_TOP = 0.06  # quota superiore del Basamento della piazza

    def setUp(self):
        self.B = batches()
        del TUBES[:]
        city.build_town_square(self.B, defaultdict(lambda: None), None)
        self.bollard_cyls = [c for c in self.B["metal"].calls
                             if c["type"] == "cylinder" and c["radius"] == 0.045]
        self.gold_spheres = [c for c in self.B["metal_gold"].calls
                             if c["type"] == "sphere" and c["radius"] == 0.09]

    def test_paletti_poggiano_sul_basamento(self):
        """Tutti i paletti hanno il piede a quota 0,06 m (filo del basamento)."""
        self.assertGreater(len(self.bollard_cyls), 20)
        for c in self.bollard_cyls:
            base_z = c["center"][2] - c["height"] / 2
            self.assertAlmostEqual(base_z, self.STONE_BASE_TOP, places=5,
                                   msg=f"Paletto in {c['center']} non poggia sul basamento a 0.06")
            # Prima partivano da z = 0,16 m, fluttuando di 10 cm nel vuoto
            self.assertNotAlmostEqual(base_z, 0.16, places=2)

    def test_varco_municipio_libero_da_paletti(self):
        """A nord (y = 13,7) nessun paletto intralcia la scalinata (abs(x) < 4,0 m)."""
        north_bollards = [c for c in self.bollard_cyls if math.isclose(c["center"][1], 13.7, abs_tol=0.1)]
        # I paletti a nord restano solo sulle ali laterali (x <= -4 o x >= 4)
        for c in north_bollards:
            self.assertGreaterEqual(abs(c["center"][0]), 4.0,
                                    msg=f"Paletto a x={c['center'][0]} blocca il varco centrale del municipio")
        # Prima c'era un paletto a x = 0 piantato nel gradino della scalinata
        center_bollards = [c for c in north_bollards if math.isclose(c["center"][0], 0.0, abs_tol=0.5)]
        self.assertEqual(len(center_bollards), 0)

    def test_sfere_dorate_su_tutti_i_paletti(self):
        """Ogni paletto, compresi quelli sui lati est e ovest, ha la sua sfera dorata."""
        self.assertEqual(len(self.bollard_cyls), len(self.gold_spheres))
        # Verifica che per ogni cilindro esista una sfera centrata sopra la sommità
        for cyl in self.bollard_cyls:
            cx, cy, cz = cyl["center"]
            top_z = cz + cyl["height"] / 2
            matching_spheres = [
                s for s in self.gold_spheres
                if math.isclose(s["center"][0], cx, abs_tol=0.05)
                and math.isclose(s["center"][1], cy, abs_tol=0.05)
            ]
            self.assertEqual(len(matching_spheres), 1)
            sphere_z = matching_spheres[0]["center"][2]
            self.assertGreater(sphere_z, top_z)

    def test_catena_perimetrale_bassa(self):
        """Una catena bassa a festone collega i paletti contigui."""
        chains = [t for t in TUBES if t["radius"] == 0.012 and len(t["points"]) == 3]
        self.assertGreater(len(chains), 15)
        for ch in chains:
            p0, mid, p1 = ch["points"]
            # Il punto centrale ha quota inferiore rispetto agli estremi (catenaria)
            self.assertLess(mid[2], p0[2])
            self.assertLess(mid[2], p1[2])
            self.assertGreater(mid[2], self.STONE_BASE_TOP)


class TombiniCaditoieTests(unittest.TestCase):
    """Miglioria 3: tombini e caditoie alloggiati sulla carreggiata e nelle canalette."""

    def setUp(self):
        self.B = batches()
        city.build_street_life(self.B, defaultdict(lambda: None), None)
        # Tombini: cilindri in metallo di raggio 0.42 m
        self.manholes = [c for c in self.B["metal"].calls
                         if c["type"] == "cylinder" and math.isclose(c["radius"], 0.42, abs_tol=0.01)]
        # Caditoie: scatole in metallo di dimensioni circa 0.35 x 0.90 m
        self.drains = [c for c in self.B["metal"].calls
                       if c["type"] == "box" and math.isclose(c["size"][0], 0.35, abs_tol=0.05)]

    def test_numero_tombini_e_caditoie(self):
        self.assertEqual(len(self.manholes), 5)
        self.assertEqual(len(self.drains), 4)

    def test_tombini_tutti_su_carreggiata(self):
        """Tutti i tombini poggiano su carreggiata (surface_z == ROAD_TOP)."""
        for mh in self.manholes:
            x, y = mh["center"][:2]
            sz = city.surface_z(x, y)
            self.assertAlmostEqual(sz, city.ROAD_TOP, places=5,
                                   msg=f"Tombino in ({x}, {y}) ha quota superficie {sz} != {city.ROAD_TOP}")

    def test_nessun_tombino_nello_spartitraffico_o_prato(self):
        """Nessun tombino sta a x=0 su Viale Roma (spartitraffico fiorito) o in un prato."""
        for mh in self.manholes:
            x, y = mh["center"][:2]
            # Su Viale Roma (dove lo spartitraffico è largo 1.2 m), abs(x) deve essere > 1.0 m
            if abs(y) < 100 and city.surface_z(x, y) == city.ROAD_TOP and abs(x) < 5.0:
                self.assertGreaterEqual(abs(x), 2.0,
                                        msg=f"Tombino in ({x}, {y}) è dentro o troppo vicino allo spartitraffico")
            # Prima un tombino era esattamente a (0, -40)
            self.assertFalse(math.isclose(x, 0.0, abs_tol=0.5) and math.isclose(y, -40.0, abs_tol=0.5))
            # Prima c'era un tombino a (-11, -24) nel prato urbano
            self.assertFalse(math.isclose(x, -11.0, abs_tol=0.5) and math.isclose(y, -24.0, abs_tol=0.5))

    def test_caditoie_nella_canaletta_della_carreggiata(self):
        """Le caditoie stanno a x = ±26.75 m (dentro la carreggiata a filo cordolo)."""
        for dr in self.drains:
            x, y = dr["center"][:2]
            sz = city.surface_z(x, y)
            self.assertAlmostEqual(sz, city.ROAD_TOP, places=5,
                                   msg=f"Caditoia in ({x}, {y}) non è sulla carreggiata")
            # La carreggiata di via ±23 va da 19 a 27 m; il cordolo è a 27.0 m
            self.assertAlmostEqual(abs(x), 26.75, places=2)
            # Prima erano a x = ±27.4 m sul marciapiede (surface_z = 0.11 m)
            self.assertNotAlmostEqual(abs(x), 27.4, places=1)

    def test_caditoie_sotto_quota_marciapiede(self):
        """Le caditoie hanno la superficie a quota asfalto, sotto il marciapiede (0.11 m)."""
        for dr in self.drains:
            top_z = dr["center"][2] + dr["size"][2] / 2
            self.assertLess(top_z, city.SIDEWALK_TOP)
            self.assertGreater(top_z, city.ROAD_TOP)

    def test_tombini_incassati_nell_asfalto(self):
        """I tombini sono incassati nell'asfalto con il bordo superiore a filo carreggiata."""
        for mh in self.manholes:
            cz = mh["center"][2]
            h = mh["height"]
            bottom = cz - h / 2
            top = cz + h / 2
            # Base immersa nell'asfalto (< 0.05 m) e bordo superiore a filo (tra 0.05 e 0.07 m)
            self.assertLess(bottom, city.ROAD_TOP)
            self.assertGreater(top, city.ROAD_TOP)
            self.assertLess(top, city.ROAD_TOP + 0.02)


class ValiditaMeshTests(unittest.TestCase):
    """Verifica che tutte le facce e i vertici generati siano geometricamente corretti."""

    def test_vertici_finiti_e_facce_valide(self):
        for build, args in (
            (city.build_countryside, (batches(), defaultdict(lambda: None), Mock())),
            (city.build_town_square, (batches(), defaultdict(lambda: None), None)),
            (city.build_street_life, (batches(), defaultdict(lambda: None), None)),
        ):
            b_dict = args[0]
            build(*args)
            for batch in b_dict.values():
                for v in batch.verts:
                    self.assertTrue(all(math.isfinite(coord) for coord in v))
                for face in batch.faces:
                    self.assertTrue(all(0 <= idx < len(batch.verts) for idx in face))


if __name__ == "__main__":
    unittest.main()
