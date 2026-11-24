"""Flask page for the ngspice CE amplifier simulator (Lab 04)."""

from pathlib import Path

from flask import Blueprint, render_template, request
from markupsafe import Markup

from spice import (
    SpiceError,
    default_spice_form,
    find_ngspice,
    hand_calc_op,
    parse_spice_form,
    percent_diff,
    run_simulations,
)
from spice_plots import ac_metrics, build_plots


spice_bp = Blueprint("spice", __name__)

VAR_DIR = Path(__file__).resolve().parent / "var" / "spice"

# (key, label, unit, hint) — raw form text is never used in a netlist.
FIELD_GROUPS = [
    ("DC / bias", [
        ("vcc", "VCC", "V", "Supply voltage"),
        ("r1", "R1", "kΩ", "Upper divider"),
        ("r2", "R2", "kΩ", "Lower divider"),
        ("rc", "RC", "kΩ", "Collector resistor"),
        ("re", "RE", "kΩ", "Emitter resistor"),
        ("rl", "RL", "kΩ", "Load at collector"),
        ("bf", "BF (β)", "", "Transistor forward gain"),
    ]),
    ("Coupling / bypass", [
        ("c1", "C1", "µF", "Input coupling"),
        ("ce", "CE", "µF", "Emitter bypass (0 = ไม่ใส่)"),
        ("c2", "C2", "µF", "Output coupling"),
    ]),
    ("Sinusoidal source", [
        ("sin_amp", "Amplitude", "mV", "Input amplitude"),
        ("sin_freq", "Frequency", "Hz", "Input / midband target"),
    ]),
    ("Analysis windows", [
        ("ac_fstart", "AC fstart", "Hz", "Sweep start"),
        ("ac_fstop", "AC fstop", "Hz", "Sweep stop"),
        ("ac_ppd", "AC points/decade", "", "10–500"),
        ("tran_tstep", "tstep", "µs", "Transient step"),
        ("tran_tstop", "tstop", "ms", "Transient duration"),
    ]),
]

COMPARE_FIELDS = [
    ("vb", "VB", "V"),
    ("ve", "VE", "V"),
    ("vc", "VC", "V"),
    ("vce", "VCE", "V"),
    ("ib", "IB", "µA"),
    ("ic", "IC", "mA"),
    ("ie", "IE", "mA"),
]

_CURRENT_KEYS = {"ib", "ic", "ie"}


def _scale(key):
    if key in _CURRENT_KEYS:
        return 1e6 if key == "ib" else 1e3
    return 1.0


def _fmt(value, key):
    if value is None:
        return "—"
    return f"{value * _scale(key):.4f}"


def _ac_summary(run, target_hz):
    rows = [row for row in run.ac.rows if len(row) >= 5]
    if not rows:
        return None
    nearest = min(rows, key=lambda row: abs(row[0] - target_hz))
    gain_db, phase_deg = ac_metrics(nearest)
    return {
        "frequency_hz": nearest[0],
        "gain_db": gain_db,
        "phase_deg": phase_deg,
        "vin_db": nearest[3],
        "samples": len(rows),
        "fmin_hz": rows[0][0],
        "fmax_hz": rows[-1][0],
    }


def _tran_summary(run):
    rows = [row for row in run.tran.rows if len(row) >= 3]
    if not rows:
        return None
    vin = [row[1] for row in rows]
    vout = [row[2] for row in rows]
    return {
        "vin_pp_mv": (max(vin) - min(vin)) * 1e3,
        "vout_pp_mv": (max(vout) - min(vout)) * 1e3,
        "vout_dc_v": run.op["vout"],
        "samples": len(rows),
        "tstop_ms": rows[-1][0] * 1e3,
    }


def _provenance(run):
    entries = []
    for analysis in ("op", "ac", "tran"):
        item = getattr(run, "op_run" if analysis == "op" else analysis)
        entries.append({
            "name": analysis.upper(),
            "netlist": item.netlist,
            "netlist_sha": item.netlist_sha,
            "command": item.command,
            "log": item.log,
            "result_name": item.result_name,
            "result_sha": item.result_sha,
            "exit_code": item.exit_code,
        })
    return entries


@spice_bp.route("/spice", methods=["GET", "POST"])
def spice_page():
    form = default_spice_form()
    context = {
        "form": form,
        "groups": FIELD_GROUPS,
        "errors": [],
        "run": None,
        "plots": None,
        "ac_summary": None,
        "tran_summary": None,
        "compare_rows": [],
        "provenance": [],
        "engine": None,
    }

    if request.method != "POST":
        return render_template("spice.html", **context)

    form = {key: request.form.get(key, form[key]) for key in form}
    context["form"] = form
    inp, errors = parse_spice_form(form)
    if errors:
        context["errors"] = errors
        return render_template("spice.html", **context)

    executable = find_ngspice()
    if executable is None:
        context["errors"] = [
            "ไม่พบ ngspice — กรุณารัน .\\setup_spice.ps1 หรือตั้งค่า NGSPICE_BIN "
            "ให้ชี้ไปที่ ngspice_con.exe แล้วลองใหม่"
        ]
        return render_template("spice.html", **context)

    try:
        run = run_simulations(inp, VAR_DIR)
    except (SpiceError, OSError, ValueError) as exc:
        context["errors"] = [getattr(exc, "message", str(exc))]
        return render_template("spice.html", **context)

    hand = hand_calc_op(inp)
    diffs = percent_diff(hand, run.op)
    raw_plots = build_plots(run.op, run.ac.rows, run.tran.rows, sin_freq_hz=inp.sin_freq_hz)
    context.update({
        "run": run,
        "plots": {
            "ac": Markup(raw_plots["ac"]),
            "tran": Markup(raw_plots["tran"]),
        },
        "ac_summary": _ac_summary(run, inp.sin_freq_hz),
        "tran_summary": _tran_summary(run),
        "compare_rows": [
            {"key": key, "label": label, "unit": unit,
             "hand": _fmt(hand.get(key), key),
             "spice": _fmt(run.op.get(key), key),
             "diff": f"{diffs[key]:.2f}"}
            for key, label, unit in COMPARE_FIELDS
        ],
        "provenance": _provenance(run),
        "engine": {
            "version": run.version,
            "executable": str(executable),
            "timestamp": run.timestamp_utc,
            "workdir": run.workdir,
        },
    })
    return render_template("spice.html", **context)
