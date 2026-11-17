from flask import Flask, render_template, request
from markupsafe import Markup

from bjt import (
    MODE_DIVIDER,
    MODE_LABELS,
    MODE_FIELDS,
    MODES,
    BiasError,
    compare,
    parse_input,
    result_payload,
    solve_for_mode,
    solve_nodal,
)
from diagrams import load_line_svg, schematic_svg
from units import RESISTANCE_UNITS, VOLTAGE_UNITS, UnitError, to_si

FIELD_META = {
    "vcc": {
        "name": "vcc",
        "sym": "V",
        "sub": "CC",
        "desc": "Supply Voltage",
        "kind": "voltage",
        "units": VOLTAGE_UNITS,
        "default": "12.0",
        "default_unit": "v",
    },
    "r1": {
        "name": "r1",
        "sym": "R",
        "sub": "1",
        "desc": "Upper Divider",
        "kind": "resistance",
        "units": RESISTANCE_UNITS,
        "default": "100",
        "default_unit": "kohm",
    },
    "r2": {
        "name": "r2",
        "sym": "R",
        "sub": "2",
        "desc": "Lower Divider",
        "kind": "resistance",
        "units": RESISTANCE_UNITS,
        "default": "22",
        "default_unit": "kohm",
    },
    "rb": {
        "name": "rb",
        "sym": "R",
        "sub": "B",
        "desc": "Base Resistor",
        "kind": "resistance",
        "units": RESISTANCE_UNITS,
        "default": "470",
        "default_unit": "kohm",
    },
    "rc": {
        "name": "rc",
        "sym": "R",
        "sub": "C",
        "desc": "Collector Resistor",
        "kind": "resistance",
        "units": RESISTANCE_UNITS,
        "default": "2.2",
        "default_unit": "kohm",
    },
    "re": {
        "name": "re",
        "sym": "R",
        "sub": "E",
        "desc": "Emitter Resistor",
        "kind": "resistance",
        "units": RESISTANCE_UNITS,
        "default": "1.0",
        "default_unit": "kohm",
    },
    "beta": {
        "name": "beta",
        "sym": "β",
        "sub": "",
        "desc": "Current Gain",
        "kind": "none",
        "units": (("", "—"),),
        "default": "100",
        "default_unit": "",
    },
    "vbe": {
        "name": "vbe",
        "sym": "V",
        "sub": "BE",
        "desc": "Base-Emitter Voltage",
        "kind": "voltage",
        "units": VOLTAGE_UNITS,
        "default": "0.70",
        "default_unit": "v",
    },
}

FIELD_NAMES = tuple(FIELD_META)


def fields_for(mode):
    return [FIELD_META[name] for name in MODE_FIELDS[mode]]


def default_form(mode=MODE_DIVIDER):
    return {name: FIELD_META[name]["default"] for name in MODE_FIELDS[mode]}


def default_units(mode=MODE_DIVIDER):
    return {name: FIELD_META[name]["default_unit"] for name in MODE_FIELDS[mode]}


def parse_form(form, mode=MODE_DIVIDER):
    """แปลงค่าตามหน่วยที่เลือกในฟอร์ม ให้เป็นหน่วยฐาน (V, Ω) เป็นข้อความ

    อ่านเฉพาะช่องที่โหมดนั้นใช้ — ช่องของโหมดอื่นที่ค้างมาไม่ถูกตรวจ
    คืน (ค่าในหน่วยฐาน, รายการข้อความผิดพลาดของหน่วย)
    """
    si = {}
    errors = []
    for name in MODE_FIELDS[mode]:
        field = FIELD_META[name]
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


def build_status(primary, bias, rows=None, mode=MODE_DIVIDER):
    """สถานะการทำงานของทรานซิสเตอร์สำหรับการ์ดสีเขียว/เหลือง/แดง"""
    vce = primary.vce_v
    if primary.region == "cutoff":
        if mode == MODE_DIVIDER:
            vbb = bias.vcc_v * bias.r2_ohm / (bias.r1_ohm + bias.r2_ohm)
            detail = f"VBB = {vbb:.2f} V ≤ VBE = {bias.vbe_v:.2f} V (no base bias)"
        else:
            detail = f"VCC = {bias.vcc_v:.2f} V ≤ VBE = {bias.vbe_v:.2f} V (no base bias)"
        return {
            "kind": "warn",
            "icon": "⚠",
            "title": "Cutoff — transistor is off",
            "detail": detail,
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

    def schematic_for(mode, values, nodes=None):
        safe = {}
        for name in FIELD_NAMES:
            try:
                safe[name] = float(str(values.get(name, "")).strip() or 0.0)
            except (TypeError, ValueError):
                safe[name] = 0.0
        return Markup(schematic_svg(mode=mode, nodes=nodes, **safe))

    def render_page(mode, form, units, results=None, errors=None, schematic=None, loadline=None):
        return render_template(
            "index.html",
            mode=mode,
            mode_label=MODE_LABELS[mode],
            modes=[(key, MODE_LABELS[key]) for key in MODES],
            fields=fields_for(mode),
            form=form,
            units=units,
            results=results,
            errors=errors,
            schematic=schematic,
            loadline=loadline,
        )

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            mode = request.form.get("mode", MODE_DIVIDER)
        else:
            mode = request.args.get("mode", MODE_DIVIDER)
        if mode not in MODES:
            mode = MODE_DIVIDER

        if request.method == "POST":
            form = {name: request.form.get(name, "") for name in MODE_FIELDS[mode]}
            units = {name: request.form.get(f"{name}_unit", "") for name in MODE_FIELDS[mode]}
            si, unit_errors = parse_form(request.form, mode)
            if unit_errors:
                return render_page(
                    mode,
                    form,
                    units,
                    results=None,
                    errors=unit_errors,
                    schematic=schematic_for(mode, si),
                )
            try:
                bias = parse_input(si, mode)
                primary = solve_for_mode(mode, bias)
                if mode == MODE_DIVIDER:
                    nodal = solve_nodal(bias)
                    rows = compare(primary, nodal)
                    all_match = all(r.matches for r in rows)
                    max_diff = f"{max(r.difference for r in rows):.2e}"
                else:
                    rows = []
                    all_match = None
                    max_diff = None
                results = {
                    "payload": result_payload(primary),
                    "rows": rows,
                    "all_match": all_match,
                    "max_diff": max_diff,
                    "status": build_status(primary, bias, rows, mode),
                    "region": primary.region,
                }
                nodes = {
                    "vb_v": primary.vb_v,
                    "ve_v": primary.ve_v,
                    "vc_v": primary.vc_v,
                }
                re_ohm = getattr(bias, "re_ohm", 0.0) or 0.0
                return render_page(
                    mode,
                    form,
                    units,
                    results=results,
                    errors=None,
                    schematic=schematic_for(mode, si, nodes),
                    loadline=Markup(
                        load_line_svg(bias.vcc_v, bias.rc_ohm, re_ohm, primary.ic_a, primary.vce_v)
                    ),
                )
            except BiasError as exc:
                return render_page(
                    mode,
                    form,
                    units,
                    results=None,
                    errors=exc.errors,
                    schematic=schematic_for(mode, si),
                )

        form = default_form(mode)
        return render_page(
            mode,
            form,
            default_units(mode),
            results=None,
            errors=None,
            schematic=schematic_for(mode, form),
        )

    return app


if __name__ == "__main__":
    # โหมดพัฒนาสำหรับเดโมในเครื่องเท่านั้น (debug=True ไม่เหมาะกับงานจริง)
    create_app().run(debug=True, port=5000)
