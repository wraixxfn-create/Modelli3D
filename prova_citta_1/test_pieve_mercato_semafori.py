"""Test geometrici su pieve romanica, mercato settimanale e semafori (ventesima versione).

Verifica i tre interventi della ventesima versione:
1. ``build_church``: il rosone della facciata è posizionato nel registro
   superiore (``z = 7,80 m``) ben sopra l'architrave del portale (``4,60 m``)
   e orientato nel piano della facciata; le cinque monofore dell'abside sono
   tangenti al cilindro absidale (``r = 4,40 m``); il campanile ha guglia
   piramidale quadrata poggiata sulla cornice sommitale (``20,55 m``) e
   orologio con doppia lancetta; le panche del sagrato hanno gambe in pietra
   ai lati del portale e l'intera pieve è invariante per rotazione.
2. ``build_market_stall`` e ``build_market_cart``: i montanti delle bancarelle
   partono dal lastricato della piazza (``z = 0,21 m``) e si fermano sotto la
   falda inclinata della tenda con traverse e puntoni laterali; il carretto
   del mercato ha due ruote a raggi sui due fianchi opposti (``ly = ±0,60``),
   cassette di ortaggi sul pianale e lavagna dei prezzi staccata dalle ruote.
3. ``build_crosswalk_signal`` e ``build_crosswalk_signals``: i sei pali
   semaforici poggiano sulla parte piana del marciapiede (``x + 5,40``,
   ``y + 5,40``), fuori dalle rampe ribassate e dalle piastre tattili gialle,
   con pulsante fissato direttamente sul fusto e segnale pedonale retto da
   due staffe metalliche.
"""

from collections import defaultdict, deque
import math
import os
import random
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import genera_citta as gc  # noqa: E402


def _make_batches():
    col = bpy.data.collections.new("TestPieveMercatoSemafori")
    bpy.context.scene.collection.children.link(col)
    mats = defaultdict(lambda: None)
    return defaultdict(lambda: gc.Batch("test", None, col)), mats, col


def _to_local(pt, cx, cy, yaw):
    dx, dy = pt[0] - cx, pt[1] - cy
    c, s = math.cos(yaw), math.sin(yaw)
    return (dx * c + dy * s, -dx * s + dy * c, pt[2])


def _mesh_components(batch):
    key_of = lambda p: (round(p[0], 5), round(p[1], 5), round(p[2], 5))
    by_coord = defaultdict(list)
    for idx, v in enumerate(batch.verts):
        by_coord[key_of(v)].append(idx)

    adj = defaultdict(set)
    for f in batch.faces:
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            adj[a].add(b)
            adj[b].add(a)
    for indices in by_coord.values():
        first = indices[0]
        for other in indices[1:]:
            adj[first].add(other)
            adj[other].add(first)

    seen = set()
    comps = []
    for start in range(len(batch.verts)):
        if start in seen:
            continue
        q = deque([start])
        seen.add(start)
        comp = []
        while q:
            v = q.popleft()
            comp.append(batch.verts[v])
            for nb in adj[v]:
                if nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        comps.append(comp)
    return comps


class TestPieveRomanica(unittest.TestCase):
    """Rosone in quota, monofore absidali tangenti, guglia piramidale e panche."""

    @classmethod
    def setUpClass(cls):
        cls.B, cls.mats, cls.col = _make_batches()
        cls.cx, cls.cy, cls.yaw = -48.0, -17.5, gc.PI / 2
        gc.build_church(cls.B, cls.mats, cls.col, cls.cx, cls.cy, cls.yaw)

    def test_rose_window_above_portal_and_below_cornice(self):
        """Il rosone vetrato sta tra 6,50 m e 9,10 m, sopra l'architrave (4,60 m)."""
        local_glass = [
            _to_local(v, self.cx, self.cy, self.yaw)
            for v in self.B["glass"].verts
        ]
        # Filtra i vertici del rosone sulla facciata della navata (|lx| < 3,0, ly < -10,15),
        # escludendo le monofore della cella campanaria (lx ~ 7,9).
        facade_glass = [
            v for v in local_glass if abs(v[0]) < 3.0 and v[1] < -10.15
        ]
        self.assertGreaterEqual(len(facade_glass), 48)

        # Nessun vetro sulla facciata deve scendere nella fascia del portale (< 6,0 m).
        low_facade_glass = [v for v in facade_glass if v[2] < 6.0]
        self.assertEqual(low_facade_glass, [])

        xs = [v[0] for v in facade_glass]
        ys = [v[1] for v in facade_glass]
        zs = [v[2] for v in facade_glass]
        self.assertAlmostEqual(min(xs), -1.02, places=2)
        self.assertAlmostEqual(max(xs), 1.02, places=2)
        self.assertAlmostEqual(min(zs), 7.80 - 1.02, places=2)
        self.assertAlmostEqual(max(zs), 7.80 + 1.02, places=2)
        # Il disco di vetro è sottile lungo la normale di facciata (Y locale),
        # non ruotato di 90° di taglio.
        self.assertLess(max(ys) - min(ys), 0.15)
        # Resta sopra l'architrave (4,60 m) e sotto il cornicione (9,53 m).
        self.assertGreater(min(zs), 4.60 + 1.80)
        self.assertLess(max(zs), 9.53 - 0.40)

    def test_apse_windows_tangent_to_cylinder(self):
        """Le 5 monofore dell'abside seguono la tangente del cilindro (r = 4,40 m)."""
        apse_cy = 11.6  # d / 2 + 1.6 con d = 20.0
        apse_comps = []
        for comp in _mesh_components(self.B["glass"]):
            lcomp = [_to_local(v, self.cx, self.cy, self.yaw) for v in comp]
            cy_m = sum(v[1] for v in lcomp) / len(lcomp)
            if cy_m > 10.5:
                apse_comps.append(lcomp)
        self.assertEqual(len(apse_comps), 5)

        for lcomp in apse_comps:
            radii = [math.hypot(v[0], v[1] - apse_cy) for v in lcomp]
            # Con le monofore tangenti al cilindro (r = 4,40 m), tutti gli
            # spigoli restano nella fascia [4,34, 4,52] anziché sporgere a 4,76 m.
            self.assertGreater(min(radii), 4.32)
            self.assertLess(max(radii), 4.54)

            cx_m = sum(v[0] for v in lcomp) / len(lcomp)
            cy_m = sum(v[1] for v in lcomp) / len(lcomp)
            rx, ry = cx_m, cy_m - apse_cy
            rnorm = math.hypot(rx, ry)
            rx, ry = rx / rnorm, ry / rnorm
            # L'estensione radiale rispetto al centro della finestra non supera
            # metà dello spessore del telaio (~0,06 m + curvatura).
            radial_offsets = [
                (v[0] - cx_m) * rx + (v[1] - cy_m) * ry for v in lcomp
            ]
            self.assertLess(max(radial_offsets) - min(radial_offsets), 0.16)

    def test_campanile_square_pyramid_spire_and_clock_hands(self):
        """La guglia del campanile poggia a 20,55 m con base quadrata e l'orologio ha 2 lancette."""
        tx, ty = 7.9, -13.6
        local_terra = [
            _to_local(v, self.cx, self.cy, self.yaw)
            for v in self.B["terracotta"].verts
        ]
        spire_verts = sorted({
            (round(v[0], 3), round(v[1], 3), round(v[2], 3))
            for v in local_terra if v[2] > 20.0
        })
        self.assertEqual(len(spire_verts), 5)

        base_verts = [v for v in spire_verts if v[2] < 21.0]
        apex_verts = [v for v in spire_verts if v[2] > 23.0]
        self.assertEqual(len(base_verts), 4)
        self.assertEqual(len(apex_verts), 1)
        for v in base_verts:
            self.assertAlmostEqual(v[2], 20.55, places=3)
            self.assertAlmostEqual(abs(v[0] - tx), 1.88, places=3)
            self.assertAlmostEqual(abs(v[1] - ty), 1.88, places=3)
        self.assertAlmostEqual(apex_verts[0][0], tx, places=3)
        self.assertAlmostEqual(apex_verts[0][1], ty, places=3)
        self.assertAlmostEqual(apex_verts[0][2], 23.70, places=3)

        # Orologio a quota ~14,2 m: mozzo cilindrico + 2 lancette dorate.
        clock_gold = []
        for comp in _mesh_components(self.B["metal_gold"]):
            lcomp = [_to_local(v, self.cx, self.cy, self.yaw) for v in comp]
            z_mean = sum(v[2] for v in lcomp) / len(lcomp)
            if 13.5 < z_mean < 15.0:
                clock_gold.append(lcomp)
        self.assertEqual(len(clock_gold), 6)  # due quadranti, ciascuno con mozzo e lancette

    def test_sagrato_benches_and_church_rotation_invariance(self):
        """Le panche del sagrato fiancheggiano il portale con gambe e la pieve ruota senza distorsioni."""
        local_benches = [
            _to_local(v, self.cx, self.cy, self.yaw)
            for v in self.B["wood_light"].verts
        ]
        self.assertEqual(len(local_benches), 16)
        left_bench = [v for v in local_benches if v[0] < 0]
        right_bench = [v for v in local_benches if v[0] > 0]
        self.assertEqual(len(left_bench), 8)
        self.assertEqual(len(right_bench), 8)
        # Il corridoio centrale davanti al portale (lx in [-1.8, +1.8]) è libero.
        for v in local_benches:
            self.assertGreater(abs(v[0]), 1.95)
            self.assertAlmostEqual(abs(v[1] - (-13.5)), 0.25, places=3)

        # Gambe in pietra delle panche sul sagrato (z = 0,20..0,50 m).
        bench_legs = [
            _to_local(v, self.cx, self.cy, self.yaw)
            for v in self.B["concrete"].verts
            if _to_local(v, self.cx, self.cy, self.yaw)[1] < -12.0
        ]
        self.assertEqual(len(bench_legs), 32)
        self.assertAlmostEqual(min(v[2] for v in bench_legs), 0.20, places=3)
        self.assertAlmostEqual(max(v[2] for v in bench_legs), 0.50, places=3)

        # Verifica invarianza rotazionale a un orientamento arbitrario.
        B2, mats2, col2 = _make_batches()
        cx2, cy2, yaw2 = 12.0, -30.0, 1.15
        gc.build_church(B2, mats2, col2, cx2, cy2, yaw2)
        for key in ("glass", "brick", "wood_light"):
            v1 = [_to_local(v, self.cx, self.cy, self.yaw) for v in self.B[key].verts]
            v2 = [_to_local(v, cx2, cy2, yaw2) for v in B2[key].verts]
            self.assertEqual(len(v1), len(v2), msg=f"Batch {key}")
            for p, q in zip(v1, v2):
                for a, b in zip(p, q):
                    self.assertAlmostEqual(a, b, places=4, msg=f"Batch {key}")
        # Per metal_gold tutti gli elementi sopra le basette dei lampioni (z > 1,0 m:
        # targa votiva, mozzo, lancette dell'orologio e croce) coincidono punto a punto.
        mg1 = [
            _to_local(v, self.cx, self.cy, self.yaw)
            for v in self.B["metal_gold"].verts if v[2] > 1.0
        ]
        mg2 = [
            _to_local(v, cx2, cy2, yaw2)
            for v in B2["metal_gold"].verts if v[2] > 1.0
        ]
        self.assertEqual(len(mg1), len(mg2))
        for p, q in zip(mg1, mg2):
            for a, b in zip(p, q):
                self.assertAlmostEqual(a, b, places=4)
        for key in ("trim", "cream", "terracotta", "concrete", "metal_gold"):
            v1 = [_to_local(v, self.cx, self.cy, self.yaw) for v in self.B[key].verts]
            v2 = [_to_local(v, cx2, cy2, yaw2) for v in B2[key].verts]
            self.assertEqual(len(v1), len(v2), msg=f"Batch {key}")
            for axis in range(3):
                self.assertAlmostEqual(
                    min(p[axis] for p in v1), min(q[axis] for q in v2),
                    places=1, msg=f"Batch {key} min axis {axis}"
                )
                self.assertAlmostEqual(
                    max(p[axis] for p in v1), max(q[axis] for q in v2),
                    places=1, msg=f"Batch {key} max axis {axis}"
                )


class TestMercatoBancarelleCarretto(unittest.TestCase):
    """Bancarelle sotto tenda e carretto agricolo a due ruote a raggi."""

    def test_stall_posts_under_sloped_canopy_and_above_paving(self):
        """I montanti partono da z = 0,21 m e restano sotto la falda inclinata."""
        B, _, _ = _make_batches()
        random.seed(42)
        x, y, yaw = -4.3, 5.0, 0.0
        gc.build_market_stall(B, x, y, yaw, "canvas_red")

        for key in ("wood", "wood_light"):
            zs = [v[2] for v in B[key].verts]
            self.assertGreaterEqual(min(zs), 0.21 - 1e-4, msg=f"Batch {key}")

        # Montanti anteriori (ly ~ -1,15): fermi sotto la tenda anteriore (2,141 m).
        local_wood = [_to_local(v, x, y, yaw) for v in B["wood"].verts]
        front_top = max(
            v[2] for v in local_wood if v[1] < -1.0 and abs(v[0]) > 1.4
        )
        back_top = max(
            v[2] for v in local_wood if v[1] > 1.0 and abs(v[0]) > 1.4
        )
        self.assertAlmostEqual(front_top, 2.121, places=2)
        self.assertAlmostEqual(back_top, 2.433, places=2)
        self.assertLess(front_top, 2.141)
        self.assertLess(back_top, 2.453)

    def test_market_cart_spoked_wheels_crates_and_blackboard(self):
        """Il carretto ha due ruote opposte a raggi, cassette di ortaggi e lavagna separata."""
        B, mats, col = _make_batches()
        cx, cy, yaw = -13.6, 9.5, gc.PI / 2
        gc.build_market_cart(B, mats, col, cx, cy, yaw)

        for key in ("wood", "wood_light", "metal", "metal_gold", "roof_dark",
                    "produce_red", "produce_yellow", "produce_green"):
            zs = [v[2] for v in B[key].verts]
            self.assertTrue(zs, msg=f"Batch {key} vuoto")
            self.assertGreaterEqual(min(zs), 0.21 - 1e-3, msg=f"Batch {key}")

        # Due ruote su fianchi opposti (ly ~ -0,60 e ly ~ +0,60).
        local_metal = [_to_local(v, cx, cy, yaw) for v in B["metal"].verts]
        right_wheel = [v for v in local_metal if v[1] < -0.50 and v[2] < 0.98]
        left_wheel = [v for v in local_metal if v[1] > 0.50 and v[2] < 0.98]
        self.assertGreater(len(right_wheel), 80)
        self.assertGreater(len(left_wheel), 80)
        self.assertAlmostEqual(min(v[2] for v in right_wheel), 0.21, places=2)
        self.assertAlmostEqual(min(v[2] for v in left_wheel), 0.21, places=2)
        self.assertAlmostEqual(max(v[2] for v in right_wheel), 0.97, places=2)
        self.assertAlmostEqual(max(v[2] for v in left_wheel), 0.97, places=2)

        # La lavagna (roof_dark) sta a ly ~ -0,90, ben separata dalla ruota destra (ly >= -0,64).
        local_board = [_to_local(v, cx, cy, yaw) for v in B["roof_dark"].verts]
        max_board_ly = max(v[1] for v in local_board)
        min_wheel_ly = min(v[1] for v in right_wheel)
        self.assertLess(max_board_ly, min_wheel_ly - 0.20)

    def test_market_cart_and_stall_rotation_invariance(self):
        """Bancarella e carretto sono invarianti per rotazione nel riferimento locale."""
        B1, mats1, col1 = _make_batches()
        random.seed(99)
        gc.build_market_stall(B1, -4.3, 5.0, 0.0, "canvas_green")
        gc.build_market_cart(B1, mats1, col1, -13.6, 9.5, 0.0)

        B2, mats2, col2 = _make_batches()
        random.seed(99)
        gc.build_market_stall(B2, 6.0, -8.0, 1.35, "canvas_green")
        gc.build_market_cart(B2, mats2, col2, 15.0, -12.0, 1.35)

        for key in ("wood", "wood_light", "metal", "metal_gold", "roof_dark",
                    "canvas_green", "white", "produce_red"):
            self.assertEqual(len(B1[key].verts), len(B2[key].verts), msg=key)


class TestSemaforiIncroci(unittest.TestCase):
    """Pali semaforici fuori dalle rampe tattili, staffe pedonali e pulsante sul fusto."""

    def test_signals_clear_of_curb_ramps_and_tactile_plates(self):
        """I 6 semafori stanno a (x + 5,40, y + 5,40), fuori da rampe (<= 5,175) e piastre tattili."""
        B, mats, col = _make_batches()
        for jx, jy in gc.CROSSWALK_JUNCTIONS:
            gc.build_accessible_corner(B, jx, jy, 1, 1, 8.0, 8.0)
        gc.build_crosswalk_signals(B, mats, col)

        tactile_boxes = []
        for comp in _mesh_components(B["road_yellow"]):
            xs = [v[0] for v in comp]
            ys = [v[1] for v in comp]
            tactile_boxes.append((min(xs), max(xs), min(ys), max(ys)))
        self.assertGreaterEqual(len(tactile_boxes), len(gc.CROSSWALK_JUNCTIONS))

        base_comps = _mesh_components(B["metal_gold"])
        self.assertEqual(len(base_comps), len(gc.CROSSWALK_JUNCTIONS))

        for (jx, jy), comp in zip(gc.CROSSWALK_JUNCTIONS, base_comps):
            xs = [v[0] for v in comp]
            ys = [v[1] for v in comp]
            px = (min(xs) + max(xs)) / 2
            py = (min(ys) + max(ys)) / 2
            self.assertAlmostEqual(px, jx + 5.40, places=2)
            self.assertAlmostEqual(py, jy + 5.40, places=2)
            # La basetta (r = 0,18 m) resta interamente oltre la rampa (jx + 5,175).
            self.assertGreater(min(xs), jx + 5.175 + 0.04)
            self.assertGreater(min(ys), jy + 5.175 + 0.04)
            # Nessuna sovrapposizione XY con alcuna piastra tattile gialla.
            for tx0, tx1, ty0, ty1 in tactile_boxes:
                overlap_x = min(max(xs), tx1) - max(min(xs), tx0)
                overlap_y = min(max(ys), ty1) - max(min(ys), ty0)
                self.assertFalse(overlap_x > 0 and overlap_y > 0)

    def test_signal_pedestrian_brackets_and_attached_call_box(self):
        """Il pulsante aderisce al fusto e due staffe collegano il segnale pedonale al palo."""
        B, _, _ = _make_batches()
        px, py, yaw = -64.6, -64.6, 0.45
        gc.build_crosswalk_signal(B, px, py, yaw)

        metal_comps = [
            [_to_local(v, px, py, yaw) for v in comp]
            for comp in _mesh_components(B["metal"])
        ]
        # Scatola del pulsante a quota ~1,38 m: centrata a lx = 0 e innestata nel palo (r = 0,065).
        call_boxes = [
            c for c in metal_comps
            if 1.15 <= min(v[2] for v in c) and max(v[2] for v in c) <= 1.60
        ]
        self.assertEqual(len(call_boxes), 1)
        cbox = call_boxes[0]
        self.assertAlmostEqual(min(v[0] for v in cbox), -0.10, places=2)
        self.assertAlmostEqual(max(v[0] for v in cbox), 0.10, places=2)
        self.assertGreater(max(v[1] for v in cbox), -0.065)

        # Due staffe orizzontali attorno a z = 2,56 m e z = 3,00 m tra lx = 0 e lx = 0,22.
        brackets = [
            c for c in metal_comps
            if 2.45 <= min(v[2] for v in c) and max(v[2] for v in c) <= 3.10
            and (max(v[2] for v in c) - min(v[2] for v in c)) < 0.12
        ]
        self.assertEqual(len(brackets), 2)
        for br in brackets:
            self.assertLessEqual(min(v[0] for v in br), 0.01)
            self.assertGreaterEqual(max(v[0] for v in br), 0.21)


if __name__ == "__main__":
    unittest.main()
