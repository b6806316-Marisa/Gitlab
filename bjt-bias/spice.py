"""SPICE adapter for the CE voltage-divider reference circuit.

Only validated numbers are used to build netlists; raw form text never
reaches a netlist or a subprocess command line.
"""

from dataclasses import dataclass
import datetime
import hashlib
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

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
        "wrdata ac.csv vdb(6) vp(6) vdb(5) vp(5)",
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


def hand_calc_op(inp):
    """Independent analytical reference: fixed VBE = 0.7 V, beta = BF."""
    beta = inp.bf
    vth = inp.vcc_v * inp.r2_ohm / (inp.r1_ohm + inp.r2_ohm)
    rth = inp.r1_ohm * inp.r2_ohm / (inp.r1_ohm + inp.r2_ohm)
    ib = (vth - 0.7) / (rth + (1 + beta) * inp.re_ohm)
    ic = beta * ib
    ie = (1 + beta) * ib
    ve = ie * inp.re_ohm
    vc = inp.vcc_v - ic * inp.rc_ohm
    return {
        "beta": beta,
        "vth": vth,
        "rth": rth,
        "ib": ib,
        "ic": ic,
        "ie": ie,
        "vb": ve + 0.7,
        "ve": ve,
        "vc": vc,
        "vce": vc - ve,
    }


def percent_diff(hand, op):
    """Signed percentage difference of SPICE from the analytical reference."""
    result = {}
    for key in ("vb", "ve", "vc", "vce", "ib", "ic", "ie"):
        reference = hand.get(key, 0.0)
        actual = op.get(key, 0.0)
        result[key] = abs(actual - reference) / reference * 100 if reference else 0.0
    return result


class SpiceError(Exception):
    """Raised when ngspice is missing, fails, times out or writes no result."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class AnalysisRun:
    analysis: str
    netlist: str
    log: str
    rows: list
    exit_code: int
    command: str
    netlist_sha: str
    result_sha: str
    result_name: str


@dataclass(frozen=True)
class SpiceRun:
    op: dict
    op_run: AnalysisRun
    ac: AnalysisRun
    tran: AnalysisRun
    version: str
    timestamp_utc: str
    workdir: str


def find_ngspice():
    """Resolve the ngspice executable: override, bundled binary, then PATH."""
    override = os.environ.get("NGSPICE_BIN", "").strip()
    if override:
        candidate = Path(override)
        if candidate.is_file():
            return candidate
        found = shutil.which(override)
        if found:
            return Path(found)
        return None

    bundled = Path(__file__).resolve().parent / "tools" / "ngspice"
    if bundled.is_dir():
        for name in ("ngspice_con.exe", "ngspice.exe", "ngspice"):
            hits = sorted(bundled.rglob(name))
            if hits:
                return hits[0]

    for name in ("ngspice_con", "ngspice"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _run_process(executable, args, cwd, timeout=15):
    command = [str(executable), *args]
    options = {
        "cwd": str(cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "errors": "replace",
        "timeout": timeout,
    }
    if sys.platform == "win32":
        options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    completed = subprocess.run(command, **options)
    return completed.stdout or "", completed.returncode, command


def parse_wrdata(text):
    """Parse ngspice wrdata output into numeric tuples; reject empty output."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rows.append(tuple(float(part) for part in line.split()))
        except ValueError:
            continue
    if not rows:
        raise SpiceError("ไฟล์ผลจาก ngspice ว่างหรือไม่ถูกต้อง")
    return rows


def parse_op_log(text):
    """Read the node table and the Q1 device section from an ngspice .op log."""
    nodes = {}
    for match in re.finditer(r"^\s*V\((\d+)\)\s+([-+0-9.eE]+)", text, re.MULTILINE):
        nodes[int(match.group(1))] = float(match.group(2))

    devices = {}
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if re.match(r"^\s*device\s+q1\s*$", line):
            for detail in lines[index + 1:]:
                if not detail.strip():
                    break
                parameter = re.match(r"^\s*(\w+)\s+([-+0-9.eE]+)\s*$", detail)
                if parameter:
                    devices[parameter.group(1)] = float(parameter.group(2))
            break

    op = {
        "vb": nodes.get(2, 0.0),
        "vc": nodes.get(3, 0.0),
        "ve": nodes.get(4, 0.0),
        "vout": nodes.get(6, 0.0),
        "ic": devices.get("ic", 0.0),
        "ib": devices.get("ib", 0.0),
        "ie": abs(devices.get("ie", 0.0)),
        "vbe": devices.get("vbe", nodes.get(2, 0.0) - nodes.get(4, 0.0)),
    }
    op["vce"] = op["vc"] - op["ve"]
    return op


def run_simulations(inp, base_dir):
    """Run .op, .ac and .tran in separate directories; keep all raw evidence."""
    executable = find_ngspice()
    if executable is None:
        raise SpiceError("ไม่พบ ngspice — กรุณารัน setup_spice.ps1 หรือตั้งค่า NGSPICE_BIN")

    stamp = datetime.datetime.now(datetime.timezone.utc)
    workdir = Path(base_dir) / f"{stamp.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    workdir.mkdir(parents=True, exist_ok=False)
    netlists = build_netlists(inp)

    runs = {}
    for analysis in ("op", "ac", "tran"):
        netlist = netlists[analysis]
        netlist_path = workdir / f"{analysis}.cir"
        netlist_path.write_text(netlist, encoding="utf-8")
        log_name = f"{analysis}.log"
        output, code, command = _run_process(
            executable, ["-b", "-o", log_name, netlist_path.name], workdir
        )
        log_path = workdir / log_name
        log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        log = (log_text + "\n" + output).strip()
        result_name = f"{analysis}.csv" if analysis != "op" else log_name
        result_path = workdir / result_name
        result_bytes = result_path.read_bytes() if result_path.exists() else b""
        rows = parse_wrdata(result_bytes.decode("utf-8", errors="replace")) if result_bytes else []
        runs[analysis] = AnalysisRun(
            analysis=analysis,
            netlist=netlist,
            log=log,
            rows=rows,
            exit_code=code,
            command=" ".join(command),
            netlist_sha=_sha256(netlist.encode("utf-8")),
            result_sha=_sha256(result_bytes) if result_bytes else "",
            result_name=result_name,
        )
        if code != 0 or (analysis != "op" and not result_bytes):
            raise SpiceError(
                f"ngspice {analysis} ไม่สำเร็จ (exit code {code}) — ดู log ใน {workdir / log_name}"
            )

    version_output, _, _ = _run_process(executable, ["-v"], workdir, timeout=10)
    version_match = re.search(r"ngspice-[\w.]+", version_output)
    version = version_match.group(0) if version_match else version_output.splitlines()[0] if version_output else "unknown"

    return SpiceRun(
        op=parse_op_log(runs["op"].log),
        op_run=runs["op"],
        ac=runs["ac"],
        tran=runs["tran"],
        version=version,
        timestamp_utc=stamp.isoformat(timespec="seconds"),
        workdir=str(workdir),
    )
