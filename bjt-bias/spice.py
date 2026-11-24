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
