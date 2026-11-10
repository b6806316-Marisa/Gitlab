import re
import unittest

from diagrams import load_line_svg, schematic_svg


DEFAULTS = dict(vcc=12.0, r1=47000.0, r2=10000.0, rc=2200.0, re=470.0, beta=150.0, vbe=0.7)

CHAR_WIDTH = 7.0
LINE_TOLERANCE = 12.0


def _find_overlaps(svg):
    """หา text ที่อยู่บรรทัดเดียวกันแล้วช่วง x ทับกัน"""
    texts = []
    for match in re.finditer(r'<text x="(-?[\d.]+)" y="(-?[\d.]+)" text-anchor="(\w+)"[^>]*>([^<]*)</text>', svg):
        x = float(match.group(1))
        y = float(match.group(2))
        anchor = match.group(3)
        content = match.group(4)
        width = CHAR_WIDTH * len(content)
        if anchor == "end":
            span = (x - width, x)
        elif anchor == "middle":
            span = (x - width / 2, x + width / 2)
        else:
            span = (x, x + width)
        texts.append((content, y, span))

    overlaps = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            content_a, y_a, span_a = texts[i]
            content_b, y_b, span_b = texts[j]
            if abs(y_a - y_b) >= LINE_TOLERANCE:
                continue
            if span_a[0] < span_b[1] and span_b[0] < span_a[1]:
                overlaps.append(f"{content_a!r} ทับ {content_b!r}")
    return overlaps


class TestSchematicSvg(unittest.TestCase):
    def test_matches_lab_reference_labels(self):
        svg = schematic_svg(vcc=12.0, r1=100000.0, r2=22000.0, rc=2200.0, re=1000.0, beta=100.0, vbe=0.7)
        for token in ("Q1", "NPN", "R1", "R2", "RC", "RE", "VCC = 12 V",
                      "100 kΩ", "22 kΩ", "2.2 kΩ", "1 kΩ", "(β = 100)"):
            self.assertIn(token, svg)

    def test_is_svg_document(self):
        svg = schematic_svg(**DEFAULTS)
        self.assertTrue(svg.lstrip().startswith("<svg"))
        self.assertIn("</svg>", svg)
        self.assertIn("viewBox", svg)

    def test_contains_component_labels(self):
        svg = schematic_svg(**DEFAULTS)
        for label in ("VCC", "R1", "R2", "RC", "RE", "VBE", "β"):
            self.assertIn(label, svg)

    def test_shows_input_values(self):
        svg = schematic_svg(**DEFAULTS)
        for value in ("12 V", "47 kΩ", "10 kΩ", "2.2 kΩ", "470 Ω", "0.7 V", "150"):
            self.assertIn(value, svg)

    def test_shows_node_voltages_when_given(self):
        svg = schematic_svg(**DEFAULTS, nodes={"vb_v": 1.959, "ve_v": 1.259, "vc_v": 6.146})
        self.assertIn("VB = 1.96 V", svg)
        self.assertIn("VE = 1.26 V", svg)
        self.assertIn("VC = 6.15 V", svg)

    def test_no_node_voltages_without_results(self):
        svg = schematic_svg(**DEFAULTS)
        self.assertNotIn("VB =", svg)
        self.assertNotIn("VE =", svg)
        self.assertNotIn("VC =", svg)

    def test_labels_do_not_overlap(self):
        svg = schematic_svg(**DEFAULTS, nodes={"vb_v": 1.959, "ve_v": 1.259, "vc_v": 6.146})
        overlaps = _find_overlaps(svg)
        self.assertEqual(overlaps, [], "ป้ายในผังวงจรทับกัน: " + "; ".join(overlaps))

    def test_load_line_labels_do_not_overlap(self):
        svg = load_line_svg(vcc=12.0, rc=2200.0, re=470.0, q_ic=2.6609586538184696e-3, q_vce=4.886902723856055)
        overlaps = _find_overlaps(svg)
        self.assertEqual(overlaps, [], "ป้ายในกราฟทับกัน: " + "; ".join(overlaps))

    def test_contains_no_script_or_untrusted_markup(self):
        svg = schematic_svg(**DEFAULTS, nodes={"vb_v": 1.959, "ve_v": 1.259, "vc_v": 6.146})
        self.assertNotIn("<script", svg.lower())
        self.assertNotIn("onload", svg.lower())

    def test_geometry_stays_inside_viewbox(self):
        svg = schematic_svg(**DEFAULTS, nodes={"vb_v": 1.959, "ve_v": 1.259, "vc_v": 6.146})
        box = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
        xs = [float(x) for x in re.findall(r'\b(?:x|cx|x1|x2)="(-?[\d.]+)"', svg)]
        ys = [float(y) for y in re.findall(r'\b(?:y|cy|y1|y2)="(-?[\d.]+)"', svg)]
        self.assertTrue(xs)
        self.assertTrue(ys)
        for x in xs:
            self.assertGreaterEqual(x, box[0])
            self.assertLessEqual(x, box[0] + box[2])
        for y in ys:
            self.assertGreaterEqual(y, box[1])
            self.assertLessEqual(y, box[1] + box[3])


class TestLoadLineSvg(unittest.TestCase):
    def test_is_svg_document_with_axis_labels(self):
        svg = load_line_svg(vcc=12.0, rc=2200.0, re=470.0, q_ic=2.6609586538184696e-3, q_vce=4.886902723856055)
        self.assertTrue(svg.lstrip().startswith("<svg"))
        self.assertIn("VCE (V)", svg)
        self.assertIn("IC (mA)", svg)

    def test_shows_intercepts(self):
        svg = load_line_svg(vcc=12.0, rc=2200.0, re=470.0, q_ic=2.6609586538184696e-3, q_vce=4.886902723856055)
        # saturation intercept: 12 V / (2200 + 470) ohm = 4.494 mA
        self.assertIn("4.49 mA", svg)
        self.assertIn("12", svg)

    def test_marks_q_point(self):
        svg = load_line_svg(vcc=12.0, rc=2200.0, re=470.0, q_ic=2.6609586538184696e-3, q_vce=4.886902723856055)
        self.assertIn("Q (2.66 mA, 4.89 V)", svg)
        self.assertNotIn("นอกเส้น load line", svg)

    def test_clamps_q_point_outside_load_line(self):
        svg = load_line_svg(vcc=12.0, rc=2200.0, re=470.0, q_ic=0.0395, q_vce=-380.0)
        self.assertIn("นอกเส้น load line", svg)
        box = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
        xs = [float(x) for x in re.findall(r'\b(?:x|cx|x1|x2)="(-?[\d.]+)"', svg)]
        ys = [float(y) for y in re.findall(r'\b(?:y|cy|y1|y2)="(-?[\d.]+)"', svg)]
        for x in xs:
            self.assertGreaterEqual(x, box[0])
            self.assertLessEqual(x, box[0] + box[2])
        for y in ys:
            self.assertGreaterEqual(y, box[1])
            self.assertLessEqual(y, box[1] + box[3])

    def test_cutoff_q_point_is_marked_outside(self):
        svg = load_line_svg(vcc=12.0, rc=2200.0, re=470.0, q_ic=0.0, q_vce=12.0)
        self.assertIn("นอกเส้น load line", svg)


if __name__ == "__main__":
    unittest.main()
