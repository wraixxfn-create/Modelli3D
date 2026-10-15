"""Test geometrici per coperture dei palazzi, rami degli alberi urbani e panni sui balconi."""

import math
import os
import sys
import unittest
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy
import genera_citta as gc


def make_batches():
    """Raccoglie le primitive in batch fittizi indicizzati per materiale."""
    col = bpy.data.collections.new("TestCopertureAlberiPanni")
    return defaultdict(lambda: gc.Batch("test", None, col))


def boxes_from_batch(batch, count=None):
    """Estrae le scatole da 8 vertici da un batch (eventualmente le prime `count`)."""
    limit = len(batch.verts) if count is None else count * 8
    assert limit % 8 == 0, f"Numero di vertici non multiplo di 8: {limit}"
    return [batch.verts[i:i + 8] for i in range(0, limit, 8)]


def box_center(verts):
    n = len(verts)
    return (
        sum(v[0] for v in verts) / n,
        sum(v[1] for v in verts) / n,
        sum(v[2] for v in verts) / n,
    )


def connected_components(verts, faces):
    """Raggruppa i vertici connessi per faccia o per coincidenza geometrica."""
    key_of = lambda p: (round(p[0], 5), round(p[1], 5), round(p[2], 5))
    by_coord = defaultdict(list)
    for idx, v in enumerate(verts):
        by_coord[key_of(v)].append(idx)

    adj = defaultdict(set)
    for f in faces:
        for u in f:
            for v in f:
                if u != v:
                    adj[u].add(v)
    for indices in by_coord.values():
        first = indices[0]
        for other in indices[1:]:
            adj[first].add(other)
            adj[other].add(first)

    seen = set()
    comps = []
    for idx in range(len(verts)):
        if idx in seen:
            continue
        stack = [idx]
        seen.add(idx)
        comp = []
        while stack:
            cur = stack.pop()
            comp.append(verts[cur])
            for nxt in adj[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        comps.append(comp)
    return comps


class CoperturePalazziTests(unittest.TestCase):
    """Fotovoltaico, lucernari e lettini sui propri sostegni nelle coperture."""

    BUILDING_SPECS = (
        (18.0, 14.0, 5),
        (20.0, 15.0, 5),
        (16.0, 11.0, 4),
    )

    def _build_roof(self, width=18.0, depth=14.0, floors=5, cx=0.0, cy=0.0, yaw=0.0):
        B = make_batches()
        base_z = 0.30
        height = 3.45 + (floors - 1) * 2.85
        gc._apartment_roof_and_terrace(
            B, {}, cx, cy, yaw, width, depth, base_z, height, -depth / 2
        )
        roof_z = base_z + height + 0.10
        return B, roof_z

    def test_fotovoltaico_sui_telai_sul_retro_e_sopra_la_soletta(self):
        pitch = math.radians(16.0)
        for width, depth, floors in self.BUILDING_SPECS:
            B, roof_z = self._build_roof(width, depth, floors)
            slab_top = roof_z + 0.03
            panels = boxes_from_batch(B["roof_dark"])
            glasses = boxes_from_batch(B["glass"])
            self.assertEqual(len(panels), 3)
            self.assertEqual(len(glasses), 3)

            for i, (panel, glass) in enumerate(zip(panels, glasses)):
                expected_x = -width * 0.30 + i * 2.45
                expected_y = depth * 0.30
                pc = box_center(panel)
                gc_c = box_center(glass)
                self.assertAlmostEqual(pc[0], expected_x, places=4)
                self.assertAlmostEqual(pc[1], expected_y, places=4)
                self.assertAlmostEqual(gc_c[0], expected_x, places=4)
                # Il vetro è scostato di 7 cm lungo la normale al pannello.
                self.assertAlmostEqual(
                    gc_c[1] - pc[1], -0.07 * math.sin(pitch), places=4
                )
                self.assertAlmostEqual(
                    gc_c[2] - pc[2], 0.07 * math.cos(pitch), places=4
                )
                # Il bordo basso poggia sul telaio metallico (roof_z + 0,20 m),
                # ben sopra la soletta di calpestio (roof_z + 0,03 m).
                self.assertGreaterEqual(min(v[2] for v in panel), roof_z + 0.19)
                self.assertGreater(min(v[2] for v in glass), slab_top + 0.20)

    def test_lucernari_accanto_al_corpo_scala_e_sopra_la_soletta(self):
        for width, depth, floors in self.BUILDING_SPECS:
            B, roof_z = self._build_roof(width, depth, floors)
            slab_top = roof_z + 0.03
            bx, by = -width * 0.34, -depth * 0.30
            skylights = boxes_from_batch(B["glass_warm"])
            self.assertEqual(len(skylights), 2)

            for i, sky in enumerate(skylights):
                sc = box_center(sky)
                expected_x = bx + 2.05 + i * 1.60
                expected_y = by + 0.15
                self.assertAlmostEqual(sc[0], expected_x, places=4)
                self.assertAlmostEqual(sc[1], expected_y - 0.08 * math.sin(-0.28), places=4)
                self.assertGreater(min(v[2] for v in sky), slab_top + 0.03)
                # Lontani dallo stendino (-width * 0.16, depth * 0.02) e da (0, 0).
                self.assertGreater(math.hypot(sc[0], sc[1]), 1.5)

    def test_lettini_sui_sostegni_a_prua_e_rotazione_invariante(self):
        B0, roof_z = self._build_roof(18.0, 14.0, 5, cx=0.0, cy=0.0, yaw=0.0)
        slab_top = roof_z + 0.03
        # I primi 2 box `white` sono i telai dei lettini (il 3° è il telo sullo stendino);
        # il primo box `red` è il materassino (seguito dal cono dell'ombrellone).
        frames = boxes_from_batch(B0["white"], count=2)
        red_mat = boxes_from_batch(B0["red"], count=1)
        blue_mat = boxes_from_batch(B0["blue"], count=1)
        self.assertEqual(len(frames), 2)
        self.assertEqual(len(red_mat), 1)
        self.assertEqual(len(blue_mat), 1)

        for i, (frame, mat_box) in enumerate(zip(frames, (red_mat[0], blue_mat[0]))):
            lx0 = 18.0 * 0.02 + i * 0.90
            ly0 = -14.0 / 2 + 1.35
            fc = box_center(frame)
            mc = box_center(mat_box)
            self.assertAlmostEqual(fc[0], lx0, places=4)
            self.assertAlmostEqual(fc[1], ly0, places=4)
            self.assertAlmostEqual(mc[0], lx0, places=4)
            self.assertAlmostEqual(mc[1] - fc[1], -0.085 * math.sin(-0.20), places=4)
            self.assertAlmostEqual(mc[2] - fc[2], 0.085 * math.cos(-0.20), places=4)
            self.assertGreater(min(v[2] for v in frame), slab_top + 0.08)

        # Invarianza per rotazione: tutti i batch della copertura devono coincidere
        # con la rototraslazione del caso yaw = 0.
        cx, cy, yaw = -46.0, 12.0, 0.73
        B_rot, _ = self._build_roof(18.0, 14.0, 5, cx=cx, cy=cy, yaw=yaw)
        co, si = math.cos(yaw), math.sin(yaw)
        for key in ("roof_dark", "glass", "glass_warm", "white", "blue"):
            self.assertEqual(len(B0[key].verts), len(B_rot[key].verts))
            for (x0, y0, z0), (xr, yr, zr) in zip(B0[key].verts, B_rot[key].verts):
                wx = cx + x0 * co - y0 * si
                wy = cy + x0 * si + y0 * co
                self.assertAlmostEqual(xr, wx, places=4)
                self.assertAlmostEqual(yr, wy, places=4)
                self.assertAlmostEqual(zr, z0, places=4)


class RamiAlberoUrbanoTests(unittest.TestCase):
    """Quattro rami continui inclinati dal fusto alla chioma nel prototipo di albero urbano."""

    @classmethod
    def setUpClass(cls):
        mats = gc.create_materials()
        cls.col = gc.make_local_tree_template(mats)

    def test_quattro_rami_inclinati_dal_tronco_alla_chioma(self):
        trunk_obj = next(o for o in self.col.objects if "Tronco" in o.name)
        verts = [tuple(v.co) for v in trunk_obj.data.vertices]
        faces = [tuple(p.vertices) for p in trunk_obj.data.polygons]
        comps = connected_components(verts, faces)
        # 1 fusto principale + 4 rami.
        self.assertEqual(len(comps), 5)

        branches = [c for c in comps if min(v[2] for v in c) > 1.0]
        self.assertEqual(len(branches), 4)

        for branch in branches:
            radii = [math.hypot(v[0], v[1]) for v in branch]
            zs = [v[2] for v in branch]
            # La base del ramo nasce dentro il fusto (r <= 0,22 m, z ~ 2,7..3,0 m).
            self.assertLessEqual(min(radii), 0.22)
            self.assertGreaterEqual(min(zs), 2.55)
            # La punta sale in diagonale fino ai lobi laterali della chioma.
            self.assertGreaterEqual(max(radii), 1.38)
            self.assertGreaterEqual(max(zs), 4.00)
            self.assertGreater(max(radii) - min(radii), 1.15)
            self.assertGreater(max(zs) - min(zs), 1.15)

    def test_nessun_ramo_verticale_sospeso_sotto_la_chioma(self):
        trunk_obj = next(o for o in self.col.objects if "Tronco" in o.name)
        for v in trunk_obj.data.vertices:
            r = math.hypot(v.co.x, v.co.y)
            if r > 0.25:
                # Col vecchio `axis="Z"` i cilindri a r ~ 0,80 m scendevano a z = 2,42 m;
                # ora fuori dal fusto la quota cresce insieme alla distanza radiale.
                self.assertGreater(v.co.z, 2.65)
                self.assertGreater(v.co.z, 2.50 + 0.85 * (r - 0.22))


class PanniBalconiTests(unittest.TestCase):
    """Fili e panni stesi dentro i balconi effettivi di primo e secondo piano."""

    def test_fili_e_panni_dentro_i_cinque_balconi_effettivi(self):
        B = make_batches()
        gc.add_balcony_laundry(B, 0.0, 0.0, 0.0, width=18.0, depth=14.0)

        # 5 balconi (2 al primo piano, 3 al secondo) -> 5 fili metallici.
        wires = connected_components(B["metal"].verts, B["metal"].faces)
        self.assertEqual(len(wires), 5)

        garments = []
        for key in gc.LAUNDRY_SHIRTS:
            garments.extend(boxes_from_batch(B[key]))
        self.assertEqual(len(garments), 15)

        usable = 18.0 - 3.2
        x_cols = [-usable / 2 + usable * (c + 0.5) / 5 for c in range(5)]
        valid_balconies = {
            (1, x_cols[1]), (1, x_cols[3]),
            (2, x_cols[0]), (2, x_cols[2]), (2, x_cols[4]),
        }

        for g in garments:
            cx, cy, cz = box_center(g)
            level = 1 if cz < 8.0 else 2
            nearest_col = min(x_cols, key=lambda x0: abs(cx - x0))
            self.assertIn((level, nearest_col), valid_balconies)
            # Il panno resta interamente dentro la larghezza del balcone (±1,03 m)
            # e dentro la profondità della soletta ([-8,02, -7,02]).
            self.assertLessEqual(max(abs(v[0] - nearest_col) for v in g), 0.85)
            self.assertGreaterEqual(min(v[1] for v in g), -8.02)
            self.assertLessEqual(max(v[1] for v in g), -7.02)

    def test_quote_sopra_le_solette_e_rotazione_invariante(self):
        B0 = make_batches()
        gc.add_balcony_laundry(B0, 0.0, 0.0, 0.0)

        slab_z_by_level = {
            1: 3.45 + 0.26 + 1 * 2.85 + 1.10 - 1.72 / 2 - 0.26,  # 6,54 m
            2: 3.45 + 0.26 + 2 * 2.85 + 1.10 - 1.72 / 2 - 0.26,  # 9,39 m
        }
        wires = connected_components(B0["metal"].verts, B0["metal"].faces)
        for w in wires:
            wz = (min(v[2] for v in w) + max(v[2] for v in w)) / 2
            level = 1 if wz < 8.5 else 2
            self.assertAlmostEqual(wz, slab_z_by_level[level] + 0.78, places=3)

        for key in gc.LAUNDRY_SHIRTS:
            for g in boxes_from_batch(B0[key]):
                cz = box_center(g)[2]
                level = 1 if cz < 8.5 else 2
                slab_top = slab_z_by_level[level] + 0.10
                wire_z = slab_z_by_level[level] + 0.78
                # Nessun lembo scende sotto il calpestio del balcone e il bordo
                # superiore tocca il filo alla quota del corrimano.
                self.assertGreater(min(v[2] for v in g), slab_top + 0.10)
                self.assertAlmostEqual(max(v[2] for v in g), wire_z, places=3)

        # Invarianza per rotazione sui due palazzi di Viale Roma (yaw = ±pi/2).
        bx, by, yaw = -46.0, 0.0, math.pi / 2
        B_rot = make_batches()
        gc.add_balcony_laundry(B_rot, bx, by, yaw)
        co, si = math.cos(yaw), math.sin(yaw)
        for key in ("metal",) + gc.LAUNDRY_SHIRTS:
            self.assertEqual(len(B0[key].verts), len(B_rot[key].verts))
            for (x0, y0, z0), (xr, yr, zr) in zip(B0[key].verts, B_rot[key].verts):
                wx = bx + x0 * co - y0 * si
                wy = by + x0 * si + y0 * co
                self.assertAlmostEqual(xr, wx, places=4)
                self.assertAlmostEqual(yr, wy, places=4)
                self.assertAlmostEqual(zr, z0, places=4)


if __name__ == "__main__":
    unittest.main()
