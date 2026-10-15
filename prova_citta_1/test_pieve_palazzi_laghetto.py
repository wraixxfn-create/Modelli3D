"""Tre migliorie della ventunesima versione: pieve, palazzi e laghetto.

Le funzioni geometriche sono estratte dal generatore via AST, come negli altri
test leggeri della città: nessun file .blend viene aperto o modificato.

1. ``build_church``: le quattro lesene per lato della navata cadevano in asse
   con le finestre laterali — otto compenetrazioni da 0,30 a 1,00 m lungo
   l'imbotte e per 12 cm di spessore, su tutta l'altezza della vetrata. Ora
   stanno nelle campate libere fra le finestre (``ly = ±4,65`` e ``±8,85``),
   con almeno 39 cm di margine dalle mostre e dai davanzali.
2. ``_apartment_side_windows`` e ``_apartment_elevator_shaft``: la fascia
   vetrata del vano scala era arretrata di ``-0,02 × profondità`` e le due
   colonne centrali di finestre finivano sotto il vetro (fino a 64 cm di
   compenetrazione). Ora il vano è in asse e le quattro colonne per lato
   stanno fuori dal suo ingombro: 12 cm fra traverso di piano e cornici,
   25 cm fra traverso e vetrata.
3. ``build_pond``: il cordolo era un cilindro troncoconico pieno con la
   calotta a 0,21 m, sopra il pelo dell'acqua (0,20 m) e con raggio 4,10 m
   maggiore di quello del bacino (3,85 m): l'acqua non si vedeva. Ora è un
   anello a sezione tonda, con foro da 4,10 m e cresta a 0,25 m.
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

FACES_PER_BOX = 6

FUNCTIONS = {
    "Batch", "lbox", "lbox_point", "build_church", "build_pond",
    "build_pond_bridge", "bridge_point", "in_bridge_corridor",
    "_apartment_side_windows", "_apartment_elevator_shaft",
}
CONSTANTS = {"POND_CENTER", "BRIDGE_HALF_SPAN", "BRIDGE_Y_OFFSET", "BRIDGE_HALF_WIDTH"}


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
    scope = {"math": math, "PI": math.pi, "TAU": math.tau,
             "make_cube": Mock(), "add_tube": Mock(), "add_text": Mock(),
             "add_gable_roof": Mock(), "build_street_lamp": Mock()}
    try:
        import bpy
    except ImportError:
        pass
    else:
        scope["bpy"] = bpy
    import collections.abc
    scope.setdefault("collections", collections)
    code = compile(tree, "genera_citta.py", "exec",
                   flags=__future__.annotations.compiler_flag, dont_inherit=True)
    exec(code, scope)
    # `random` serve solo a `build_pond`, che lo usa per canne e massi.
    import random
    scope.setdefault("random", random)
    return scope, SimpleNamespace(**scope)


scope, city = load_geometry()


class RecordingBatch(city.Batch):
    """Batch che annota anche le primitive ricevute, per poterle verificare."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []

    def box(self, center, size, yaw=0.0):
        self.calls.append(("box", center, size))
        return super().box(center, size, yaw)

    def cylinder(self, center, radius, depth, segments=16, axis="Z", radius2=None):
        self.calls.append(("cylinder", center, radius, depth, axis, radius2))
        return super().cylinder(center, radius, depth, segments, axis, radius2)

    def cone(self, center, radius_bottom, radius_top, depth, segments=16, axis="Z"):
        self.calls.append(("cylinder", center, radius_bottom, depth, axis, radius_top))
        return super().cone(center, radius_bottom, radius_top, depth, segments, axis)

    def ring(self, center, radius, tube, segments=40, tube_segments=8):
        self.calls.append(("ring", center, radius, tube))
        return super().ring(center, radius, tube, segments, tube_segments)

    def sphere(self, center, radius, scale=(1.0, 1.0, 1.0), segments=16, rings=8):
        self.calls.append(("sphere", center, radius))
        return super().sphere(center, radius, scale, segments, rings)


def batches():
    return defaultdict(lambda: RecordingBatch("Test", None, None))


def record_lbox(calls):
    """Sostituisce `lbox` nello scope del generatore con una versione che annota."""
    real = scope["lbox"]

    def recording(batch, cx, cy, yaw, x, y, z, sx, sy, sz):
        calls.append({"batch": batch, "x": x, "y": y, "z": z, "sx": sx, "sy": sy, "sz": sz})
        return real(batch, cx, cy, yaw, x, y, z, sx, sy, sz)

    scope["lbox"] = recording
    return real


def boxes(calls, key, **sizes):
    """Scatole di una batch, filtrate per le dimensioni locali indicate."""
    out = []
    for call in calls:
        if call["batch"] is not key:
            continue
        if any(abs(call[name] - value) > 1e-9 for name, value in sizes.items()):
            continue
        out.append(call)
    return out


def overlap(a, b):
    return min(a[1], b[1]) - max(a[0], b[0])


class PieveLeseneTests(unittest.TestCase):
    """Le lesene della navata stanno fra le finestre, non in asse con esse."""

    WINDOW_SY = 1.5
    SILL_SY = 1.8
    LESENA_SY = 1.1
    HEIGHT = 9.6

    @classmethod
    def setUpClass(cls):
        cls.calls = []
        cls.real_lbox = record_lbox(cls.calls)
        cls.B = batches()
        mats = defaultdict(lambda: None)
        city.build_church(cls.B, mats, None)
        scope["lbox"] = cls.real_lbox

    def test_four_windows_per_side_are_kept(self):
        windows = boxes(self.calls, self.B["glass"], sx=0.12, sy=self.WINDOW_SY, sz=2.6)
        self.assertEqual(len(windows), 8)
        for side in (-1, 1):
            self.assertEqual(sorted(c["y"] for c in windows
                                    if abs(c["x"]) > 1.0
                                    and (c["x"] > 0) == (side > 0)), [-7.0, -2.3, 2.3, 7.0])

    def test_four_lesene_per_side_are_kept(self):
        lesene = boxes(self.calls, self.B["trim"], sx=0.22, sy=self.LESENA_SY,
                       sz=self.HEIGHT)
        self.assertEqual(len(lesene), 8)
        self.assertAlmostEqual(lesene[0]["x"], -6.6, places=6)
        self.assertAlmostEqual(lesene[-1]["x"], 6.6, places=6)

    def test_lesene_do_not_touch_the_windows(self):
        lesene = boxes(self.calls, self.B["trim"], sx=0.22, sy=self.LESENA_SY,
                       sz=self.HEIGHT)
        windows = boxes(self.calls, self.B["glass"], sx=0.12, sy=self.WINDOW_SY, sz=2.6)
        sills = boxes(self.calls, self.B["trim"], sx=0.18, sy=self.SILL_SY, sz=0.22)
        for lesena in lesene:
            for other in windows + sills:
                if (lesena["x"] > 0) != (other["x"] > 0):
                    continue
                half = other["sy"] / 2
                span = (other["y"] - half, other["y"] + half)
                own = (lesena["y"] - self.LESENA_SY / 2,
                       lesena["y"] + self.LESENA_SY / 2)
                self.assertLess(overlap(own, span), 0.0,
                                "lesena in asse con una finestra")

    def test_every_lesena_has_a_free_pier_on_both_sides(self):
        lesene = boxes(self.calls, self.B["trim"], sx=0.22, sy=self.LESENA_SY,
                       sz=self.HEIGHT)
        sills = boxes(self.calls, self.B["trim"], sx=0.18, sy=self.SILL_SY, sz=0.22)
        for lesena in lesene:
            own = (lesena["y"] - self.LESENA_SY / 2, lesena["y"] + self.LESENA_SY / 2)
            left = [s for s in sills if (s["x"] > 0) == (lesena["x"] > 0)
                    and s["y"] < lesena["y"] - 1.0]
            right = [s for s in sills if (s["x"] > 0) == (lesena["x"] > 0)
                     and s["y"] > lesena["y"] + 1.0]
            if left:
                margin = own[0] - (max(c["y"] for c in left) + self.SILL_SY / 2)
                self.assertGreaterEqual(margin, 0.39)
            if right:
                margin = (min(c["y"] for c in right) - self.SILL_SY / 2) - own[1]
                self.assertGreaterEqual(margin, 0.39)

    def test_pilasters_stay_clear_of_the_wall_corners(self):
        lesene = boxes(self.calls, self.B["trim"], sx=0.22, sy=self.LESENA_SY,
                       sz=self.HEIGHT)
        for lesena in lesene:
            self.assertLessEqual(abs(lesena["y"]) + self.LESENA_SY / 2, 9.5)


class CorpoScalaTests(unittest.TestCase):
    """Le colonne di finestre stanno fuori dalla fascia vetrata del vano."""

    CASES = ((18.0, 14.0, 5), (20.0, 15.0, 5), (16.0, 11.0, 3))
    WINDOW_WIDTH = 1.20
    TRAVERSE_WIDTH = 2.90

    def build(self, width, depth, floors):
        calls = []
        real = record_lbox(calls)
        B = batches()
        city._apartment_side_windows(B, 0.0, 0.0, 0.0, width, depth, floors)
        city._apartment_elevator_shaft(B, 0.0, 0.0, 0.0, width, depth, 0.30,
                                       3.45 + (floors - 1) * 2.85, 2.85, floors)
        scope["lbox"] = real
        return B, calls

    def test_the_shaft_is_centred_on_the_side(self):
        for width, depth, floors in self.CASES:
            B, calls = self.build(width, depth, floors)
            glass = boxes(calls, B["glass_warm"], sx=0.10, sy=2.6)
            self.assertEqual(len(glass), 2)
            for pane in glass:
                self.assertAlmostEqual(pane["y"], 0.0, places=9)
            traverse = boxes(calls, B["trim"], sx=0.16, sy=self.TRAVERSE_WIDTH)
            self.assertEqual(len(traverse), 2 * floors)
            for beam in traverse:
                self.assertAlmostEqual(beam["y"], 0.0, places=9)

    def test_four_window_columns_per_side_per_floor(self):
        for width, depth, floors in self.CASES:
            B, calls = self.build(width, depth, floors)
            windows = boxes(calls, B["glass"], sx=0.12, sy=self.WINDOW_WIDTH, sz=1.62)
            self.assertEqual(len(windows), (floors - 1) * 2 * 4)

    def test_no_window_ends_up_under_the_glazed_shaft(self):
        for width, depth, floors in self.CASES:
            B, calls = self.build(width, depth, floors)
            windows = boxes(calls, B["glass"], sx=0.12, sy=self.WINDOW_WIDTH, sz=1.62)
            # Ogni finestra occupa tutta la cornice: 0,73 m per lato dal vetro.
            half_frame = 0.73
            half_traverse = self.TRAVERSE_WIDTH / 2
            colonne = sorted({round(abs(c["y"]), 9) for c in windows})
            self.assertEqual(len(colonne), 2)
            for y in colonne:
                self.assertGreaterEqual(round(y - half_frame - half_traverse, 9), 0.12,
                                        "cornice dentro il traverso del vano")
                self.assertGreaterEqual(round(y - self.WINDOW_WIDTH / 2 - half_traverse, 9),
                                        0.25, "vetrata sotto il vetro del vano")

    def test_outer_columns_keep_the_old_spacing_and_columns_do_not_merge(self):
        for width, depth, floors in self.CASES:
            B, calls = self.build(width, depth, floors)
            windows = boxes(calls, B["glass"], sx=0.12, sy=self.WINDOW_WIDTH, sz=1.62)
            for side in (-1, 1):
                colonne = sorted({round(abs(c["y"]), 9) for c in windows
                                  if c["y"] * side > 0})
                self.assertEqual(len(colonne), 2, "due colonne per metà fianco")
                self.assertAlmostEqual(colonne[0], 2.30, places=9)
                self.assertAlmostEqual(colonne[1], depth * 0.33, places=9)
                self.assertGreater(colonne[1] - colonne[0], self.WINDOW_WIDTH)


class LaghettoTests(unittest.TestCase):
    """Il bacino del laghetto non è coperto dalla calotta del cordolo."""

    @classmethod
    def setUpClass(cls):
        cls.B = batches()
        cx, cy = city.POND_CENTER
        cls.cx, cls.cy = cx, cy
        city.build_pond(cls.B, cx, cy)
        cls.curb = cls.B["curb"].calls

    def covers_centre(self, call, z):
        """True se la primitiva copre il centro del bacino alla quota z."""
        cx, cy = self.cx, self.cy
        if call[0] == "cylinder":
            _, center, radius, depth, axis, radius2 = call
            if axis != "Z":
                return False
            r = radius if radius2 is None else max(radius, radius2)
            if math.hypot(cx - center[0], cy - center[1]) > r:
                return False
            return center[2] - depth / 2 <= z <= center[2] + depth / 2
        if call[0] == "ring":
            _, center, radius, tube = call
            d = math.hypot(cx - center[0], cy - center[1])
            return abs(d - radius) <= tube and abs(z - center[2]) <= tube
        return False

    def test_the_water_surface_is_no_longer_covered(self):
        # Il pelo dell'acqua sta a 0,20 m: niente del cordolo può coprirlo.
        for z in (0.21, 0.22, 0.25, 0.30):
            for call in self.curb:
                self.assertFalse(self.covers_centre(call, z),
                                 f"il cordolo copre il bacino a {z} m")

    def test_the_curb_is_a_round_rim_not_a_solid_disc(self):
        kinds = [c[0] for c in self.curb]
        self.assertEqual(kinds.count("ring"), 1)
        self.assertEqual(kinds.count("cylinder"), 0)
        _, center, radius, tube = [c for c in self.curb if c[0] == "ring"][0]
        self.assertAlmostEqual(radius, 4.25, places=6)
        self.assertAlmostEqual(tube, 0.15, places=6)
        self.assertAlmostEqual(radius + tube, 4.40, places=6)   # ingombro esterno
        self.assertAlmostEqual(radius - tube, 4.10, places=6)   # foro
        self.assertAlmostEqual(center[2] + tube, 0.25, places=6)  # cresta

    def test_water_and_bottom_are_unchanged_and_fit_the_hole(self):
        panes = [c for c in self.B["water"].calls if c[0] == "cylinder"]
        self.assertEqual(len(panes), 1)
        _, center, radius, depth, axis, _ = panes[0]
        self.assertAlmostEqual(radius, 3.85, places=6)
        self.assertAlmostEqual(center[2] + depth / 2, 0.20, places=6)
        self.assertLess(radius, 4.10)  # l'acqua sta dentro il foro del cordolo
        fondo = [c for c in self.B["asphalt"].calls if c[0] == "cylinder"]
        self.assertEqual(len(fondo), 1)
        self.assertAlmostEqual(fondo[0][2], 4.0, places=6)
        self.assertGreater(fondo[0][2], radius)  # il fondo arriva sotto il cordolo


if __name__ == "__main__":
    unittest.main()
