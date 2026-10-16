"""Le tre migliorie della versione 18, verificate anche senza render.

Eseguire nell'ambiente di Blender (bpy), come gli altri test della città:
    python3 -m unittest discover -s prova_citta_1 -p 'test_*.py'
Il file non apre né sovrascrive citta.blend e non avvia alcun render.
"""
from collections import defaultdict
import math
import unittest
from unittest.mock import Mock, patch

import genera_citta as city


# Inclinazioni delle due superfici nuove, come nel generatore: il leggìo delle
# copertine (62,2°) e il quotidiano piegato dentro il raccoglitore (61,3°).
SHOW_PITCH = 1.086
CP_SHOW, SP_SHOW = math.cos(SHOW_PITCH), math.sin(SHOW_PITCH)
SHEET, SHEET_Y0, SHEET_Y1 = 0.20, -1.385, -1.289
NEWS_PITCH = math.acos((SHEET_Y1 - SHEET_Y0) / SHEET)


def batches():
    return defaultdict(lambda: city.Batch("Test", None, None))


def boxes(batch):
    """Le scatole di una batch, ognuna come gli otto vertici che la chiudono.

    Le facce di Blender non elencano i vertici in ordine progressivo: l'insieme
    ordinato degli indici di sei facce consecutive con otto vertici restituisce
    comunque i vertici della scatola. Poligoni sciolti — strisce della tenda,
    scarpate del tappeto — non hanno sei facce e vengono saltati.
    """
    out, i, n = [], 0, len(batch.faces)
    while i < n:
        window = batch.faces[i:i + 6]
        if (len(window) == 6 and all(len(face) == 4 for face in window)
                and len({v for face in window for v in face}) == 8):
            out.append([batch.verts[v] for v in
                        sorted({v for face in window for v in face})])
            i += 6
        else:
            i += 1
    return out


def box_vertex_indices(batch):
    """Gli indici dei vertici che appartengono alle scatole di una batch."""
    used, i, n = set(), 0, len(batch.faces)
    while i < n:
        window = batch.faces[i:i + 6]
        if (len(window) == 6 and all(len(face) == 4 for face in window)
                and len({v for face in window for v in face}) == 8):
            used |= {v for face in window for v in face}
            i += 6
        else:
            i += 1
    return used


def assert_valid(test, group):
    for batch in group.values():
        test.assertEqual(len(batch.faces), len(batch.smooth))
        test.assertTrue(all(math.isfinite(c) for p in batch.verts for c in p))
        test.assertTrue(all(0 <= i < len(batch.verts)
                            for face in batch.faces for i in face))


class EspositoriEdicolaTests(unittest.TestCase):
    """Le copertine e i quotidiani dell'edicola poggiano su qualcosa."""

    def setUp(self):
        self.b = batches()
        with patch.object(city, "add_text", Mock()):
            city.build_newsstand(self.b, defaultdict(lambda: None), Mock(),
                                 0, 0, 0.0)
        assert_valid(self, self.b)
        board = [b for b in boxes(self.b["wood_light"])
                 if abs(max(p[0] for p in b) - min(p[0] for p in b) - 2.28) < 1e-9]
        self.assertEqual(len(board), 1)
        self.board = board[0]
        self.centre = tuple(sum(p[i] for p in self.board) / 8 for i in range(3))

    def out_of_plane(self, corner):
        """Distanza del vertice dal mezzero del leggìo, verso la piazza."""
        return (-(corner[1] - self.centre[1]) * SP_SHOW
                + (corner[2] - self.centre[2]) * CP_SHOW)

    def along_slope(self, corner):
        """Quota del vertice lungo la salita del leggìo, dal bordo basso."""
        return ((corner[1] - self.centre[1]) * CP_SHOW
                + (corner[2] - self.centre[2]) * SP_SHOW) + 0.22

    def test_leggio_inclinato_appoggiato_alla_base_sul_banco(self):
        # Bordo basso dentro la base (top a 1,25 m sul banco) e bordo alto
        # sopra il banco, con il piano che si alza verso la piazza.
        self.assertAlmostEqual(min(p[2] for p in self.board),
                               1.25 - 0.025 * CP_SHOW, places=6)
        self.assertAlmostEqual(max(p[2] for p in self.board),
                               1.25 + 0.44 * SP_SHOW + 0.025 * CP_SHOW, places=6)
        self.assertAlmostEqual(min(self.out_of_plane(p) for p in self.board),
                               -0.025, places=6)
        self.assertAlmostEqual(min(self.along_slope(p) for p in self.board),
                               0.0, places=6)
        self.assertAlmostEqual(max(self.along_slope(p) for p in self.board),
                               0.44, places=6)
        # La base è una scatola di legno appoggiata sul banco (che sporge fino
        # a y = -1,42) e la battuta frontale poggia sulla base: il piano non è
        # sospeso, è incastrato fra il banco e la battuta.
        plates = [b for b in boxes(self.b["wood"])
                  if abs(min(p[2] for p in b) - 1.20) < 1e-9
                  and abs(max(p[2] for p in b) - 1.25) < 1e-9]
        self.assertEqual(len(plates), 1)
        self.assertLessEqual(max(p[1] for p in plates[0]), -1.42 + 0.14)
        lips = [b for b in boxes(self.b["wood"])
                if abs(min(p[2] for p in b) - 1.25) < 1e-9
                and abs(max(p[2] for p in b) - min(p[2] for p in b) - 0.06) < 1e-9]
        self.assertEqual(len(lips), 1)
        self.assertLessEqual(max(p[1] for p in lips[0]),
                             min(p[1] for p in self.board))

    def test_copertine_appoggiate_sul_leggio(self):
        covers = [b for b in boxes(self.b["white"])
                  if abs(max(p[0] for p in b) - min(p[0] for p in b) - 0.36) < 1e-9]
        self.assertEqual(len(covers), 5)
        # Le copertine erano 3,5 cm di spessore appesi 4 cm sopra il banco: ora
        # hanno il dorso sul piano del leggìo e restano dentro il suo ingombro.
        for cover in covers:
            self.assertAlmostEqual(min(self.out_of_plane(p) for p in cover),
                                   0.025, places=6)
            self.assertAlmostEqual(max(self.out_of_plane(p) for p in cover),
                                   0.055, places=6)
            self.assertGreaterEqual(min(self.along_slope(p) for p in cover), 0.0)
            self.assertLessEqual(max(self.along_slope(p) for p in cover), 0.44)
        slots = sorted(round(sum(p[0] for p in c) / 8, 6) for c in covers)
        self.assertEqual(slots, [-0.90, -0.45, 0.0, 0.45, 0.90])
        # Cinque fascette colorate, una per copertina, posate sulla copertina.
        for key in ("cloth_red", "cloth_yellow", "cloth_green",
                    "cloth_violet", "cloth_blue"):
            band = [b for b in boxes(self.b[key])
                    if abs(max(p[0] for p in b) - min(p[0] for p in b) - 0.28) < 1e-9]
            self.assertEqual(len(band), 1)
            self.assertAlmostEqual(min(self.out_of_plane(p) for p in band[0]),
                                   0.055, places=6)
            self.assertAlmostEqual(max(self.out_of_plane(p) for p in band[0]),
                                   0.067, places=6)

    def test_quotidiani_su_mensole_con_battuta_e_fondale(self):
        shelves = [b for b in boxes(self.b["wood_light"])
                   if abs(max(p[1] for p in b) - min(p[1] for p in b) - 0.13) < 1e-9]
        self.assertEqual(len(shelves), 3)
        sheets = [b for b in boxes(self.b["white"])
                  if abs(max(p[0] for p in b) - min(p[0] for p in b) - 0.60) < 1e-9]
        self.assertEqual(len(sheets), 3)
        order = lambda group: sorted(group, key=lambda b: min(p[2] for p in b))
        shelves, sheets = order(shelves), order(sheets)
        self.assertEqual([round(max(p[2] for p in shelf), 6) for shelf in shelves],
                         [0.42, 0.64, 0.86])
        for shelf, sheet in zip(shelves, sheets):
            shelf_top = max(p[2] for p in shelf)
            # Il bordo basso poggia sulla mensola, il bordo alto contro il
            # fondale del raccoglitore: niente fogli appesi davanti al mobile.
            self.assertAlmostEqual(min(p[2] for p in sheet), shelf_top, delta=0.01)
            self.assertAlmostEqual(max(p[1] for p in sheet), SHEET_Y1, delta=0.02)
            self.assertAlmostEqual(max(p[2] for p in sheet) - shelf_top,
                                   SHEET * math.sin(NEWS_PITCH), delta=0.02)
            # La battuta frontale sporge sul bordo libero e trattiene il foglio.
            lips = [b for b in boxes(self.b["wood"])
                    if abs(max(p[2] for p in b) - min(p[2] for p in b) - 0.05) < 1e-9
                    and abs(max(p[1] for p in b) - min(p[1] for p in b) - 0.025) < 1e-9]
            self.assertEqual(len(lips), 3)
            self.assertTrue(any(min(p[1] for p in lip)
                                <= min(p[1] for p in sheet)
                                <= max(p[1] for p in lip) + 1e-9
                                for lip in lips))
        # Il raccoglitore è aperto sul fronte: sponde, fondale, fondo e cielo.
        walls = [b for b in boxes(self.b["wood"])
                 if abs(max(p[0] for p in b) - min(p[0] for p in b) - 0.06) < 1e-9
                 and abs(max(p[2] for p in b) - min(p[2] for p in b) - 0.94) < 1e-9]
        self.assertEqual(len(walls), 2)


class TappetoParcoGiochiTests(unittest.TestCase):
    """Il tappeto di gomma è raccordato al prato, senza gradino netto."""

    RUN, TOP, OUT_Z = 0.55, 0.19, 0.05

    def setUp(self):
        self.b = batches()
        city.build_playground(self.b, 0, 0)
        assert_valid(self, self.b)
        deck = boxes(self.b["rubber"])
        self.assertEqual(len(deck), 1)
        self.deck = deck[0]
        used = box_vertex_indices(self.b["rubber"])
        self.slopes = [[self.b["rubber"].verts[v] for v in face]
                       for face in self.b["rubber"].faces
                       if not set(face) <= used]
        self.assertEqual(len(self.slopes), 4)

    def test_tappeto_alla_quota_dei_giochi(self):
        self.assertAlmostEqual(max(p[2] for p in self.deck), self.TOP)
        self.assertAlmostEqual(min(p[2] for p in self.deck), 0.09)
        self.assertAlmostEqual(max(p[0] for p in self.deck), 6.0)
        self.assertAlmostEqual(max(p[1] for p in self.deck), 4.5)

    def test_scarpata_perimetrale_raccordata_al_prato(self):
        points = [p for face in self.slopes for p in face]
        inner = [p for p in points if abs(p[2] - self.TOP) < 1e-9]
        outer = [p for p in points if abs(p[2] - self.OUT_Z) < 1e-9]
        # Otto vertici per lato alto e otto per il bordo esterno, ma solo
        # quattro punti distinti per ciascuno: gli spigoli sono mitrati, quindi
        # la scarpata è un anello chiuso attorno al tappeto.
        self.assertEqual(len(inner), 8)
        self.assertEqual(len(outer), 8)
        self.assertEqual(len(set(inner)), 4)
        self.assertEqual(len(set(outer)), 4)
        for x, y, _ in inner:
            on_edge = (abs(abs(x) - 6.0) < 1e-9 and abs(y) <= 4.5 + 1e-9
                       or abs(abs(y) - 4.5) < 1e-9 and abs(x) <= 6.0 + 1e-9)
            self.assertTrue(on_edge, (x, y))
        for x, y, _ in outer:
            self.assertAlmostEqual(abs(x), 6.0 + self.RUN)
            self.assertAlmostEqual(abs(y), 4.5 + self.RUN)
        # Pendenza dolce: 14,3°, sotto il gradino di 11 cm che c'era prima.
        self.assertLess(math.degrees(math.atan2(self.TOP - self.OUT_Z, self.RUN)),
                        20.0)
        # L'ultimo bordo scende sotto la quota dell'erba (0,08 m): la scarpata
        # entra nel prato e non lascia né fessure né scalini.
        self.assertLess(self.OUT_Z, 0.08)


class RuoteFurgoneTests(unittest.TestCase):
    """Le ruote del furgone stanno in sagoma e chiudono il cerchio."""

    def setUp(self):
        self.b = batches()
        with patch.object(city, "add_tube", Mock()) as tubes:
            city.add_van(self.b, 0, 0, 0.0, "white")
        self.calls = [call.args for call in tubes.call_args_list]

    def rings(self):
        return [a for a in self.calls
                if a[0] is self.b["roof_dark"] and len(a[1]) == 25]

    def test_quattro_pneumatici_in_sagoma_sotto_le_fiancate(self):
        rings = self.rings()
        self.assertEqual(len(rings), 4)
        for _, points, radius, *_ in rings:
            self.assertAlmostEqual(radius, 0.055)
            for first, last in zip(points[0], points[-1]):
                self.assertAlmostEqual(first, last)
            self.assertEqual(len({round(p[1], 6) for p in points}), 1)
            # Battistrada a 0,905 m dal mezzero: dentro le fiancate (0,91 m),
            # non più 5 cm fuori, e con il punto più basso 4 cm sopra la strada.
            self.assertAlmostEqual(abs(points[0][1]) + radius, 0.905)
            self.assertLess(abs(points[0][1]) + radius, 0.91)
            self.assertAlmostEqual(min(p[2] for p in points) - radius, 0.0)

    def test_canali_e_mozzi_chiudono_il_cerchio(self):
        # Il canale del cerchio riempie il vuoto del pneumatico (0,275 m di
        # raggio contro i 0,28 interni dell'anello) e resta in sagoma.
        rims = [a for a in self.calls if len(a[1]) == 2 and a[2] == 0.275]
        self.assertEqual(len(rims), 4)
        for _, (near, far), _, *_ in rims:
            self.assertEqual(near[0], far[0])
            self.assertEqual(near[2], far[2])
            self.assertAlmostEqual(abs(far[1]), 0.885)
            self.assertLess(abs(far[1]), 0.91)
        # Mozzo appena fuori dal canale, sempre dentro il battistrada.
        hubs = [a for a in self.calls if len(a[1]) == 2 and a[2] == 0.115]
        self.assertEqual(len(hubs), 4)
        for _, (near, far), _, *_ in hubs:
            self.assertEqual(near[0], far[0])
            self.assertEqual(near[2], far[2])
            self.assertAlmostEqual(abs(far[1]), 0.898)
            self.assertLess(abs(far[1]) + 0.0, 0.905 + 1e-9)


if __name__ == "__main__":
    unittest.main()
