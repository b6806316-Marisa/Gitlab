from flask import Flask, render_template, request
from markupsafe import Markup

from bjt import BiasError, compare, parse_input, solve_nodal, solve_thevenin
from diagrams import load_line_svg, schematic_svg

DEFAULT_FORM = {
    "vcc": "12",
    "r1": "47000",
    "r2": "10000",
    "rc": "2200",
    "re": "470",
    "beta": "150",
    "vbe": "0.7",
}

FIELD_META = [
    ("vcc", "VCC (V)", "แรงดันจ่ายรวม"),
    ("r1", "R1 (Ω)", "ตัวต้านทานแบ่งแรงดันบน"),
    ("r2", "R2 (Ω)", "ตัวต้านทานแบ่งแรงดันล่าง"),
    ("rc", "RC (Ω)", "ตัวต้านทานคอลเลกเตอร์"),
    ("re", "RE (Ω)", "ตัวต้านทานอีมิตเตอร์"),
    ("beta", "β (hFE)", "อัตราขยายกระแส"),
    ("vbe", "VBE (V)", "แรงดันเบส-อีมิตเตอร์"),
]


def fmt(x):
    # compact engineering-style number for display
    return f"{x:.4g}"


def create_app():
    app = Flask(__name__)

    def schematic_for(form, nodes=None):
        try:
            values = {k: float(str(form.get(k, "")).strip() or 0) for k in DEFAULT_FORM}
        except (TypeError, ValueError):
            values = {k: 0.0 for k in DEFAULT_FORM}
        return Markup(schematic_svg(nodes=nodes, **values))

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            form = {k: request.form.get(k, "") for k in DEFAULT_FORM}
            try:
                bias = parse_input(form)
                primary = solve_thevenin(bias)
                nodal = solve_nodal(bias)
                rows = compare(primary, nodal)
                results = {
                    "primary": primary,
                    "nodal": nodal,
                    "rows": rows,
                    "fmt": fmt,
                    "ib_uA": primary.ib_a * 1e6,
                    "ib_mA": primary.ib_a * 1e3,
                    "ic_mA": primary.ic_a * 1e3,
                    "ie_mA": primary.ie_a * 1e3,
                    "all_match": all(r.matches for r in rows),
                    "region_label": {
                        "active": "Active",
                        "cutoff": "Cutoff",
                        "saturation": "Saturation",
                    }.get(primary.region, primary.region),
                }
                nodes = {
                    "vb_v": primary.vb_v,
                    "ve_v": primary.ve_v,
                    "vc_v": primary.vc_v,
                }
                return render_template(
                    "index.html",
                    form=form,
                    fields=FIELD_META,
                    results=results,
                    errors=None,
                    schematic=schematic_for(form, nodes),
                    loadline=Markup(
                        load_line_svg(bias.vcc_v, bias.rc_ohm, bias.re_ohm, primary.ic_a, primary.vce_v)
                    ),
                )
            except BiasError as exc:
                return render_template(
                    "index.html",
                    form=form,
                    fields=FIELD_META,
                    results=None,
                    errors=exc.errors,
                    schematic=schematic_for(form),
                    loadline=None,
                )

        return render_template(
            "index.html",
            form=dict(DEFAULT_FORM),
            fields=FIELD_META,
            results=None,
            errors=None,
            schematic=schematic_for(DEFAULT_FORM),
            loadline=None,
        )

    return app


if __name__ == "__main__":
    # โหมดพัฒนาสำหรับเดโมในเครื่องเท่านั้น (debug=True ไม่เหมาะกับงานจริง)
    create_app().run(debug=True, port=5000)
