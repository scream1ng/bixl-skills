"""Regression checks for shop-stock nesting and laser-compatible etch geometry."""
from pathlib import Path
import sys
import tempfile
import unittest

import ezdxf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from shapely.geometry import MultiLineString

from nest_dxf import nest, stroke_text


def plate(name, width, height):
    return {
        "name": name,
        "outer": [[0, 0], [width, 0], [width, height], [0, height]],
        "holes": [],
    }


class NestDxfTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "nested.dxf"
        self.spec = {
            "thickness_mm": 5.0,
            "plates": [
                plate("BASE_A1", 250, 180),
                plate("RIB-B2", 220, 110),
                plate("CAP_3.0", 160, 90),
            ],
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_shop_sheet_preserves_rectangular_remnant(self):
        report = nest(self.spec, self.path)
        self.assertEqual(report["physical_sheet_mm"], [2400.0, 1200.0])
        self.assertEqual(report["usable_size_mm"], [2400.0, 1100.0])
        self.assertEqual(report["clamp_exclusion_area_mm2"], 240000.0)
        self.assertLess(report["used_strip_mm"][0], 2400.0)
        self.assertEqual(
            report["largest_rectangular_remnant_mm"],
            [2400.0 - report["used_strip_mm"][0], 1100.0],
        )
        self.assertEqual(report["status"], "pass")

    def test_etch_is_joined_open_polyline_geometry(self):
        report = nest(self.spec, self.path)
        doc = ezdxf.readfile(self.path)
        modelspace = doc.modelspace()
        self.assertFalse(list(modelspace.query('TEXT[layer=="ETCH"]')))
        self.assertFalse(list(modelspace.query('MTEXT[layer=="ETCH"]')))
        etch = list(modelspace.query('LWPOLYLINE[layer=="ETCH"]'))
        self.assertTrue(etch)
        self.assertTrue(all(not entity.closed for entity in etch))
        self.assertTrue(any(len(list(entity.get_points())) > 2 for entity in etch))
        self.assertLess(report["etch_polylines"], report["etch_source_segments"])
        self.assertEqual(report["etch_text_entities"], 0)
        self.assertTrue(report["etch_labels_inside_profiles"])

    def test_reference_boundaries_never_enter_cut_layer(self):
        nest(self.spec, self.path)
        doc = ezdxf.readfile(self.path)
        modelspace = doc.modelspace()
        for layer in (
            "STOCK_REFERENCE", "USABLE_REFERENCE", "CLAMP_EXCLUSION_REFERENCE", "NEST_REFERENCE"
        ):
            self.assertTrue(list(modelspace.query(f'LWPOLYLINE[layer=="{layer}"]')))
        cuts = list(modelspace.query('LWPOLYLINE[layer=="CUT"]'))
        self.assertTrue(cuts)
        self.assertTrue(all(entity.closed for entity in cuts))

    def test_clamp_strip_is_the_bottom_100_mm(self):
        report = nest(self.spec, self.path)
        self.assertEqual(report["usable_origin_mm"], [0.0, 100.0])
        cuts = ezdxf.readfile(self.path).modelspace().query('LWPOLYLINE[layer=="CUT"]')
        self.assertGreaterEqual(min(y for e in cuts for _, y, *_ in e.get_points()), 100.0)

    def seated_spec(self, base=(300, 200)):
        rib = lambda name, pn, y: {"name": name, "part_number": pn, "origin": [50, y, 0], "u": [1, 0, 0], "v": [0, 0, 1],
                                   "w": [0, -1, 0], "outer": [[0, 0], [200, 0], [200, 60], [0, 60]], "holes": [], "seat": "BASE"}
        seat = {"name": "BASE", "part_number": "WF01", "origin": [0, 0, -2.5], "u": [1, 0, 0], "v": [0, 1, 0], "w": [0, 0, 1],
                "outer": [[0, 0], [base[0], 0], [base[0], base[1]], [0, base[1]]], "holes": []}
        welded = {**rib("K3", "WF04", 100), "outer": [[0, 0], [60, 0], [60, 40], [0, 40]]}; welded.pop("seat")  # welded on, no tabs
        return {"thickness_mm": 5.0, "plates": [seat, rib("R1", "WF02", 50), rib("R2", "WF03", 150), welded]}

    def test_base_carries_each_standing_plates_part_number_clear_of_its_footprint(self):
        from shapely.geometry import box as rect
        spec = self.seated_spec()
        nest(spec, self.path)
        marks = spec["plates"][0]["etch_marks"]
        self.assertEqual(sorted((m["text"], m["for"]) for m in marks), [("WF02", "R1"), ("WF03", "R2"), ("WF04", "K3")])
        feet = rect(50, 47.5, 250, 52.5).union(rect(50, 147.5, 250, 152.5)).union(rect(50, 97.5, 110, 102.5))
        for m in marks:
            paths, _ = stroke_text(m["text"], m["height_mm"], m["at"], m["angle"])
            self.assertGreater(MultiLineString(paths).distance(feet), 1.5)

    def test_explicit_or_disabled_marks_override_the_automatic_ones(self):
        spec = self.seated_spec(); spec["plates"][0]["etch_marks"] = []
        nest(spec, self.path); self.assertEqual(spec["plates"][0]["etch_marks"], [])
        spec = self.seated_spec(); spec["nest"] = {"seat_part_numbers": False}
        nest(spec, self.path); self.assertNotIn("etch_marks", spec["plates"][0])

    def test_no_room_for_a_part_number_is_an_error_not_a_silent_skip(self):
        spec = self.seated_spec(base=(300, 12))  # a 12 mm strip: 2 mm edge + 5 mm foot + 2 mm edge, no room beside it
        spec["plates"] = spec["plates"][:2]; spec["plates"][1]["origin"] = [50, 6, 0]
        with self.assertRaisesRegex(ValueError, "No room on BASE to etch WF02"):
            nest(spec, self.path)

    def test_supported_shop_label_characters(self):
        paths, source_segments = stroke_text("A1_TEST-2.0", 3.5, (0, 0))
        self.assertTrue(paths)
        self.assertGreater(source_segments, len(paths))


if __name__ == "__main__":
    unittest.main()
