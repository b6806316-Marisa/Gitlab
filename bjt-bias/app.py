from flask import Flask, render_template, request

from bjt import BiasError, compare, parse_input, solve_nodal, solve_thevenin

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
                return render_template(
                    "index.html",
                    form=form,
                    fields=FIELD_META,
                    results=results,
                    errors=None,
                )
            except BiasError as exc:
                return render_template(
                    "index.html",
                    form=form,
                    fields=FIELD_META,
                    results=None,
                    errors=exc.errors,
                )

        return render_template(
            "index.html",
            form=dict(DEFAULT_FORM),
            fields=FIELD_META,
            results=None,
            errors=None,
        )

    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5000)
