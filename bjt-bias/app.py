from flask import Flask, render_template, request
from markupsafe import Markup

from bjt import BiasError, compare, parse_input, solve_nodal, solve_thevenin
from diagrams import load_line_svg, schematic_svg
from units import RESISTANCE_UNITS, VOLTAGE_UNITS, UnitError, to_si

FIELD_META = [
    {
        "name": "vcc",
        "sym": "V",
        "sub": "CC",
        "desc": "Supply Voltage",
        "kind": "voltage",
        "units": VOLTAGE_UNITS,
        "default": "12.0",
        "default_unit": "v",
    },
    {
        "name": "r1",
        "sym": "R",
        "sub": "1",
        "desc": "Upper Divider",
        "kind": "resistance",
        "units": RESISTANCE_UNITS,
        "default": "100",
        "default_unit": "kohm",
    },
    {
        "name": "r2",
        "sym": "R",
        "sub": "2",
        "desc": "Lower Divider",
        "kind": "resistance",
        "units": RESISTANCE_UNITS,
        "default": "22",
        "default_unit": "kohm",
    },
    {
        "name": "rc",
        "sym": "R",
        "sub": "C",
        "desc": "Collector Resistor",
        "kind": "resistance",
        "units": RESISTANCE_UNITS,
        "default": "2.2",
        "default_unit": "kohm",
    },
    {
        "name": "re",
        "sym": "R",
        "sub": "E",
        "desc": "Emitter Resistor",
        "kind": "resistance",
        "units": RESISTANCE_UNITS,
        "default": "1.0",
        "default_unit": "kohm",
    },
    {
        "name": "beta",
        "sym": "β",
        "sub": "",
        "desc": "Current Gain",
        "kind": "none",
        "units": (("", "—"),),
        "default": "100",
        "default_unit": "",
    },
    {
        "name": "vbe",
        "sym": "V",
        "sub": "BE",
        "desc": "Base-Emitter Voltage",
        "kind": "voltage",
        "units": VOLTAGE_UNITS,
        "default": "0.70",
        "default_unit": "v",
    },
]

FIELD_NAMES = tuple(f["name"] for f in FIELD_META)


def default_form():
    return {f["name"]: f["default"] for f in FIELD_META}


def default_units():
    return {f["name"]: f["default_unit"] for f in FIELD_META}


def parse_form(form):
    """แปลงค่าตามหน่วยที่เลือกในฟอร์ม ให้เป็นหน่วยฐาน (V, Ω) เป็นข้อความ

    คืน (ค่าในหน่วยฐาน, รายการข้อความผิดพลาดของหน่วย)
    """
    si = {}
    errors = []
    for field in FIELD_META:
        name = field["name"]
        raw = form.get(name, "")
        if field["kind"] == "none":
            si[name] = str(raw).strip()
            continue
        unit = form.get(f"{name}_unit", field["default_unit"])
        try:
            si[name] = to_si(raw, unit, field["kind"])
        except UnitError as exc:
            si[name] = str(raw).strip()
            errors.append(f"{field['sym']}{field['sub']} ({field['desc']}): {exc}")
    return si, errors


def build_status(primary, bias, rows):
    """สถานะการทำงานของทรานซิสเตอร์สำหรับการ์ดสีเขียว/เหลือง/แดง"""
    vce = primary.vce_v
    vbb = bias.vcc_v * bias.r2_ohm / (bias.r1_ohm + bias.r2_ohm)
    if primary.region == "cutoff":
        return {
            "kind": "warn",
            "icon": "⚠",
            "title": "Cutoff — transistor is off",
            "detail": f"VBB = {vbb:.2f} V ≤ VBE = {bias.vbe_v:.2f} V (no base bias)",
        }
    if primary.region == "saturation":
        return {
            "kind": "bad",
            "icon": "✕",
            "title": "Saturation — linear model invalid",
            "detail": f"VCE = {vce:.2f} V < 0.2 V (value shown unclamped)",
        }
    if vce < 0.5:
        return {
            "kind": "warn",
            "icon": "⚠",
            "title": "Active region (close to saturation)",
            "detail": f"VCE = {vce:.2f} V is close to the 0.2 V saturation limit",
        }
    return {
        "kind": "ok",
        "icon": "✓",
        "title": "Active region approximation OK",
        "detail": f"VCE = {vce:.2f} V > 0.2 V (transistor in active region)",
    }


def create_app():
    app = Flask(__name__)

    def schematic_for(values, nodes=None):
        safe = {}
        for name in FIELD_NAMES:
            try:
                safe[name] = float(str(values.get(name, "")).strip() or 0.0)
            except (TypeError, ValueError):
                safe[name] = 0.0
        return Markup(schematic_svg(nodes=nodes, **safe))

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            form = {name: request.form.get(name, "") for name in FIELD_NAMES}
            units = {name: request.form.get(f"{name}_unit", "") for name in FIELD_NAMES}
            si, unit_errors = parse_form(request.form)
            if unit_errors:
                return render_template(
                    "index.html",
                    form=form,
                    units=units,
                    fields=FIELD_META,
                    results=None,
                    errors=unit_errors,
                    schematic=schematic_for(si),
                    loadline=None,
                )
            try:
                bias = parse_input(si)
                primary = solve_thevenin(bias)
                nodal = solve_nodal(bias)
                rows = compare(primary, nodal)
                results = {
                    "vb": f"{primary.vb_v:.2f}",
                    "ve": f"{primary.ve_v:.2f}",
                    "vc": f"{primary.vc_v:.2f}",
                    "vce": f"{primary.vce_v:.2f}",
                    "ib": f"{primary.ib_a * 1e6:.3g}",
                    "ic": f"{primary.ic_a * 1e3:.3g}",
                    "ie": f"{primary.ie_a * 1e3:.3g}",
                    "rows": rows,
                    "all_match": all(r.matches for r in rows),
                    "max_diff": f"{max(r.difference for r in rows):.2e}",
                    "status": build_status(primary, bias, rows),
                }
                nodes = {
                    "vb_v": primary.vb_v,
                    "ve_v": primary.ve_v,
                    "vc_v": primary.vc_v,
                }
                return render_template(
                    "index.html",
                    form=form,
                    units=units,
                    fields=FIELD_META,
                    results=results,
                    errors=None,
                    schematic=schematic_for(si, nodes),
                    loadline=Markup(
                        load_line_svg(bias.vcc_v, bias.rc_ohm, bias.re_ohm, primary.ic_a, primary.vce_v)
                    ),
                )
            except BiasError as exc:
                return render_template(
                    "index.html",
                    form=form,
                    units=units,
                    fields=FIELD_META,
                    results=None,
                    errors=exc.errors,
                    schematic=schematic_for(si),
                    loadline=None,
                )

        return render_template(
            "index.html",
            form=default_form(),
            units=default_units(),
            fields=FIELD_META,
            results=None,
            errors=None,
            schematic=schematic_for(default_form()),
            loadline=None,
        )

    return app


if __name__ == "__main__":
    # โหมดพัฒนาสำหรับเดโมในเครื่องเท่านั้น (debug=True ไม่เหมาะกับงานจริง)
    create_app().run(debug=True, port=5000)
