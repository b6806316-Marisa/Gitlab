"""SPICE adapter for the CE voltage-divider reference circuit.

Only validated numbers are used to build netlists; raw form text never
reaches a netlist or a subprocess command line.
"""

from dataclasses import dataclass
import math

SPICE_DEFAULTS = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "rl": "10",
    "c1": "10",
    "ce": "0",
    "c2": "10",
    "bf": "200",
    "sin_amp": "10",
    "sin_freq": "1000",
    "ac_fstart": "10",
    "ac_fstop": "1e6",
    "ac_ppd": "50",
    "tran_tstep": "20",
    "tran_tstop": "200",
}


@dataclass(frozen=True)
class SpiceInput:
    vcc_v: float
    r1_ohm: float
    r2_ohm: float
    rc_ohm: float
    re_ohm: float
    rl_ohm: float
    c1_f: float
    ce_f: float
    c2_f: float
    bf: float
    sin_amp_v: float
    sin_freq_hz: float
    ac_fstart_hz: float
    ac_fstop_hz: float
    ac_ppd: int
    tran_tstep_s: float
    tran_tstop_s: float


def default_spice_form():
    """Return a fresh copy of the default form values (UI units)."""
    return dict(SPICE_DEFAULTS)


def _number(form, key, label, scale, errors):
    raw = form.get(key, "")
    if raw is None or str(raw).strip() == "":
        errors.append(f"กรุณาระบุค่า {label}")
        return None
    try:
        value = float(str(raw).strip()) * scale
    except (TypeError, ValueError):
        errors.append(f"{label} ต้องเป็นตัวเลขที่ถูกต้อง")
        return None
    if not math.isfinite(value):
        errors.append(f"{label} ต้องเป็นตัวเลขที่ถูกต้อง")
        return None
    return value


def _positive(value, label, errors, allow_zero=False):
    if value is None:
        return
    if value < 0 or (value == 0 and not allow_zero):
        suffix = "หรือศูนย์" if allow_zero else ""
        errors.append(f"{label} ต้องมีค่ามากกว่าศูนย์{suffix}")


def parse_spice_form(form):
    """Convert validated form values to SI and return (SpiceInput | None, errors)."""
    errors = []
    v = {
        "vcc_v": _number(form, "vcc", "VCC", 1.0, errors),
        "r1_ohm": _number(form, "r1", "R1", 1e3, errors),
        "r2_ohm": _number(form, "r2", "R2", 1e3, errors),
        "rc_ohm": _number(form, "rc", "RC", 1e3, errors),
        "re_ohm": _number(form, "re", "RE", 1e3, errors),
        "rl_ohm": _number(form, "rl", "RL", 1e3, errors),
        "c1_f": _number(form, "c1", "C1", 1e-6, errors),
        "ce_f": _number(form, "ce", "CE", 1e-6, errors),
        "c2_f": _number(form, "c2", "C2", 1e-6, errors),
        "bf": _number(form, "bf", "BF", 1.0, errors),
        "sin_amp_v": _number(form, "sin_amp", "Amplitude", 1e-3, errors),
        "sin_freq_hz": _number(form, "sin_freq", "Frequency", 1.0, errors),
        "ac_fstart_hz": _number(form, "ac_fstart", "AC fstart", 1.0, errors),
        "ac_fstop_hz": _number(form, "ac_fstop", "AC fstop", 1.0, errors),
        "ac_ppd": _number(form, "ac_ppd", "AC points/decade", 1.0, errors),
        "tran_tstep_s": _number(form, "tran_tstep", "tstep", 1e-6, errors),
        "tran_tstop_s": _number(form, "tran_tstop", "tstop", 1e-3, errors),
    }

    for key in ("vcc_v", "r1_ohm", "r2_ohm", "rc_ohm", "re_ohm", "rl_ohm",
                "c1_f", "c2_f", "bf", "sin_amp_v", "sin_freq_hz",
                "ac_fstart_hz", "ac_fstop_hz", "tran_tstep_s", "tran_tstop_s"):
        _positive(v[key], key.split("_")[0].upper(), errors)
    _positive(v["ce_f"], "CE", errors, allow_zero=True)

    ppd = v["ac_ppd"]
    if ppd is not None:
        if ppd != int(ppd) or not 10 <= ppd <= 500:
            errors.append("AC points/decade ต้องอยู่ระหว่าง 10 ถึง 500")
        else:
            v["ac_ppd"] = int(ppd)

    if v["ac_fstart_hz"] is not None and v["ac_fstop_hz"] is not None:
        if v["ac_fstop_hz"] <= v["ac_fstart_hz"]:
            errors.append("AC fstop ต้องมากกว่า AC fstart")
    if v["tran_tstep_s"] is not None and v["tran_tstop_s"] is not None:
        if v["tran_tstep_s"] >= v["tran_tstop_s"] / 10:
            errors.append("tstep ต้องน้อยกว่า tstop/10")

    if errors:
        return None, errors
    return SpiceInput(**v), []


# Standard PSpice 2N2222 card; BF is injected from the form so the
# analytical beta and the SPICE model stay comparable.
MODEL_TEMPLATE = (
    ".model Q2N2222 NPN(IS=14.34F XTI=3 EG=1.11 VAF=74.03 "
    "BF={bf} NE=1.307 ISE=14.34F IKF=0.2847 XTB=1.5 BR=6.092 "
    "NC=2 ISC=0 IKR=0 RC=1 CJC=7.306P MJC=0.3416 VJC=0.75 FC=0.5 "
    "CJE=22.01P MJE=0.377 VJE=0.75 TR=46.91N TF=411.1P "
    "ITF=0.6 VTF=1.7 XTF=3 RB=10)"
)


def _general(value):
    return format(value, ".10g")


def _plain(value):
    """Decimal without exponent, for sweep frequencies."""
    return format(value, ".10f").rstrip("0").rstrip(".") or "0"


def _scientific(value):
    return format(value, ".0e")


def _circuit(inp):
    lines = [
        "* CE voltage-divider reference circuit (Lab 04)",
        f"V1 1 0 DC {_general(inp.vcc_v)}",
        f"R1 1 2 {_general(inp.r1_ohm)}",
        f"R2 2 0 {_general(inp.r2_ohm)}",
        f"RC 1 3 {_general(inp.rc_ohm)}",
        f"RE 4 0 {_general(inp.re_ohm)}",
    ]
    if inp.ce_f > 0:
        lines.append(f"CE 4 0 {_scientific(inp.ce_f)}")
    lines.extend([
        "Q1 3 2 4 Q2N2222",
        f"C1 5 2 {_scientific(inp.c1_f)}",
        f"C2 3 6 {_scientific(inp.c2_f)}",
        f"RL 6 0 {_general(inp.rl_ohm)}",
        f"VS 5 0 DC 0 AC 1 SIN(0 {_general(inp.sin_amp_v)} {_general(inp.sin_freq_hz)})",
        MODEL_TEMPLATE.format(bf=_general(inp.bf)),
    ])
    return lines


def build_netlists(inp):
    """Return one netlist per analysis, all from the same validated topology."""
    circuit = _circuit(inp)
    nets = {}

    # Batch mode prints the operating point (node table + BJT device section)
    # into the log, so no control block is needed for .op.
    nets["op"] = "\n".join(circuit + [".op", ".end", ""])

    # In ngspice batch mode the analysis itself must be invoked from a
    # .control section placed AFTER .end; otherwise no vectors exist for
    # wrdata. set wr_singlescale writes one value per vector.
    nets["ac"] = "\n".join(circuit + [
        ".end",
        ".control",
        "set wr_singlescale",
        f"ac dec {inp.ac_ppd} {_plain(inp.ac_fstart_hz)} {_plain(inp.ac_fstop_hz)}",
        "wrdata ac.csv vdb(6) vp(6) vdb(5)",
        ".endc",
        "",
    ])

    nets["tran"] = "\n".join(circuit + [
        ".end",
        ".control",
        "set wr_singlescale",
        f"tran {_general(inp.tran_tstep_s)} {_general(inp.tran_tstop_s)}",
        "wrdata tran.csv v(5) v(6)",
        ".endc",
        "",
    ])
    return nets
