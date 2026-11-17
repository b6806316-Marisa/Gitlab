import math
from dataclasses import dataclass

FIELD_ORDER = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")

FIELD_LABELS = {
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rb": "RB",
    "rc": "RC",
    "re": "RE",
    "beta": "beta",
    "vbe": "VBE",
}

MODE_DIVIDER = "divider"
MODE_FIXED = "fixed"
MODE_EMITTER = "emitter"
MODES = (MODE_DIVIDER, MODE_FIXED, MODE_EMITTER)

MODE_LABELS = {
    MODE_DIVIDER: "Voltage Divider Bias",
    MODE_FIXED: "Fixed Bias",
    MODE_EMITTER: "Emitter Bias",
}

# ช่องอินพุตที่แต่ละโหมดใช้จริง (ช่องอื่นไม่ถูกอ่าน/ไม่ถูกตรวจ)
MODE_FIELDS = {
    MODE_DIVIDER: ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"),
    MODE_FIXED: ("vcc", "rb", "rc", "beta", "vbe"),
    MODE_EMITTER: ("vcc", "rb", "rc", "re", "beta", "vbe"),
}

VCE_SAT_V = 0.2
VCE_NEAR_V = 0.5


class BiasError(ValueError):
    """แรงดัน/ความต้านทาน/พารามิเตอร์ที่ผู้ใช้ป้อนไม่ถูกต้อง"""

    def __init__(self, errors):
        self.errors = [str(e) for e in errors]
        super().__init__("; ".join(self.errors))


@dataclass(frozen=True)
class BiasInput:
    vcc_v: float
    r1_ohm: float
    r2_ohm: float
    rc_ohm: float
    re_ohm: float
    beta: float
    vbe_v: float


@dataclass(frozen=True)
class FixedBiasInput:
    vcc_v: float
    rb_ohm: float
    rc_ohm: float
    beta: float
    vbe_v: float


@dataclass(frozen=True)
class EmitterBiasInput:
    vcc_v: float
    rb_ohm: float
    rc_ohm: float
    re_ohm: float
    beta: float
    vbe_v: float


@dataclass(frozen=True)
class BiasResult:
    ib_a: float
    ic_a: float
    ie_a: float
    vce_v: float
    vb_v: float
    ve_v: float
    vc_v: float
    region: str
    warnings: tuple[str, ...] = ()


def _parse_divider(raw):
    """อ่านค่า 7 ช่องของโหมด voltage divider (พฤติกรรมเดิมทั้งหมด)"""
    errors = []
    values = {}

    for field in FIELD_ORDER:
        label = FIELD_LABELS[field]
        text = str(raw.get(field, "")).strip()
        if not text:
            values[field] = None
            errors.append(f"กรุณาระบุค่า {label}")
            continue
        try:
            value = float(text)
        except (TypeError, ValueError):
            values[field] = None
            errors.append(f"{label} ต้องเป็นตัวเลขที่ถูกต้อง")
            continue
        if not math.isfinite(value):
            values[field] = None
            errors.append(f"{label} ต้องเป็นตัวเลขที่ถูกต้อง")
            continue
        values[field] = value

    vcc = values["vcc"]
    if vcc is not None and vcc <= 0:
        errors.append("VCC ต้องมีค่ามากกว่าศูนย์")

    for field in ("r1", "r2", "rc", "re"):
        value = values[field]
        if value is not None and value <= 0:
            errors.append(f"{FIELD_LABELS[field]} ต้องมีค่ามากกว่าศูนย์")

    beta = values["beta"]
    if beta is not None and beta <= 0:
        errors.append("beta ต้องมีค่ามากกว่าศูนย์")

    vbe = values["vbe"]
    if vcc is not None and vbe is not None and not (0 <= vbe < vcc):
        errors.append("VBE ต้องอยู่ระหว่าง 0 ถึง VCC (น้อยกว่า VCC)")

    if errors:
        raise BiasError(errors)

    return BiasInput(
        vcc_v=vcc,
        r1_ohm=values["r1"],
        r2_ohm=values["r2"],
        rc_ohm=values["rc"],
        re_ohm=values["re"],
        beta=beta,
        vbe_v=vbe,
    )


def _read_field(raw, field, errors):
    label = FIELD_LABELS[field]
    text = str(raw.get(field, "")).strip()
    if not text:
        errors.append(f"กรุณาระบุค่า {label}")
        return None
    try:
        value = float(text)
    except (TypeError, ValueError):
        errors.append(f"{label} ต้องเป็นตัวเลขที่ถูกต้อง")
        return None
    if not math.isfinite(value):
        errors.append(f"{label} ต้องเป็นตัวเลขที่ถูกต้อง")
        return None
    return value


def _check_vcc(values, errors):
    vcc = values.get("vcc")
    if vcc is not None and vcc <= 0:
        errors.append("VCC ต้องมีค่ามากกว่าศูนย์")


def _check_positive(values, fields, errors):
    for field in fields:
        value = values.get(field)
        if value is not None and value <= 0:
            errors.append(f"{FIELD_LABELS[field]} ต้องมีค่ามากกว่าศูนย์")


def _check_beta(values, errors):
    beta = values.get("beta")
    if beta is not None and beta <= 0:
        errors.append("beta ต้องมีค่ามากกว่าศูนย์")


def _check_vbe(values, errors):
    vcc = values.get("vcc")
    vbe = values.get("vbe")
    if vcc is not None and vbe is not None and not (0 <= vbe < vcc):
        errors.append("VBE ต้องอยู่ระหว่าง 0 ถึง VCC (น้อยกว่า VCC)")


def _parse_fixed(raw):
    errors = []
    values = {field: _read_field(raw, field, errors) for field in MODE_FIELDS[MODE_FIXED]}
    _check_vcc(values, errors)
    _check_positive(values, ("rb", "rc"), errors)
    _check_beta(values, errors)
    _check_vbe(values, errors)
    if errors:
        raise BiasError(errors)
    return FixedBiasInput(
        vcc_v=values["vcc"],
        rb_ohm=values["rb"],
        rc_ohm=values["rc"],
        beta=values["beta"],
        vbe_v=values["vbe"],
    )


def _parse_emitter(raw):
    errors = []
    values = {field: _read_field(raw, field, errors) for field in MODE_FIELDS[MODE_EMITTER]}
    _check_vcc(values, errors)
    _check_positive(values, ("rb", "rc", "re"), errors)
    _check_beta(values, errors)
    _check_vbe(values, errors)
    if errors:
        raise BiasError(errors)
    return EmitterBiasInput(
        vcc_v=values["vcc"],
        rb_ohm=values["rb"],
        rc_ohm=values["rc"],
        re_ohm=values["re"],
        beta=values["beta"],
        vbe_v=values["vbe"],
    )


def parse_input(raw, mode=MODE_DIVIDER):
    """อ่านค่าตามโหมด แล้วคืน input dataclass ของโหมดนั้น

    โหมด divider คงพฤติกรรมเดิมทุกอย่าง; fixed/emitter ตรวจเฉพาะช่องที่ใช้
    และรวบรวมข้อความผิดพลาดทั้งหมดไว้ใน BiasError.errors ก่อนยกเสมอ
    """
    if mode == MODE_FIXED:
        return _parse_fixed(raw)
    if mode == MODE_EMITTER:
        return _parse_emitter(raw)
    return _parse_divider(raw)


def classify(vce_v):
    if vce_v <= VCE_SAT_V:
        return "saturation"
    return "active"


def solve_thevenin(b):
    vbb = b.vcc_v * b.r2_ohm / (b.r1_ohm + b.r2_ohm)
    rb = b.r1_ohm * b.r2_ohm / (b.r1_ohm + b.r2_ohm)

    if vbb <= b.vbe_v:
        warnings = ("ทรานซิสเตอร์อยู่ในภาวะคัตออฟ (cutoff) กระแสแทบเป็นศูนย์",)
        return BiasResult(
            ib_a=0.0,
            ic_a=0.0,
            ie_a=0.0,
            vce_v=b.vcc_v,
            vb_v=vbb,
            ve_v=0.0,
            vc_v=b.vcc_v,
            region="cutoff",
            warnings=warnings,
        )

    ib = (vbb - b.vbe_v) / (rb + (1.0 + b.beta) * b.re_ohm)
    ic = b.beta * ib
    ie = (1.0 + b.beta) * ib
    ve = ie * b.re_ohm
    vb = b.vbe_v + ve
    vc = b.vcc_v - ic * b.rc_ohm
    vce = vc - ve

    region = classify(vce)
    warnings = []
    if region == "saturation":
        warnings.append("ทรานซิสเตอร์อิ่มตัว (saturation): ค่า VCE ต่ำกว่า 0.2 V แบบจำลองเชิงเส้นอาจไม่ถูกต้อง แต่แสดงค่าที่คำนวณได้ตามจริง")
    elif VCE_SAT_V <= vce < VCE_NEAR_V:
        warnings.append("VCE ใกล้ภาวะอิ่มตัว (near saturation) ควรระวัง headroom")

    return BiasResult(
        ib_a=ib,
        ic_a=ic,
        ie_a=ie,
        vce_v=vce,
        vb_v=vb,
        ve_v=ve,
        vc_v=vc,
        region=region,
        warnings=tuple(warnings),
    )

@dataclass(frozen=True)
class ComparisonRow:
    name: str
    primary: float
    independent: float
    difference: float
    matches: bool


def _solve3(a, bvec):
    # Gaussian elimination with partial pivoting for 3x3
    m = [list(a[i]) + [bvec[i]] for i in range(3)]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-18:
            raise BiasError(["ระบบสมการคำนวณ nodal ไม่สามารถแก้ได้"])
        if pivot != col:
            m[col], m[pivot] = m[pivot], m[col]
        pv = m[col][col]
        for j in range(col, 4):
            m[col][j] /= pv
        for row in range(3):
            if row == col:
                continue
            factor = m[row][col]
            if factor == 0.0:
                continue
            for j in range(col, 4):
                m[row][j] -= factor * m[col][j]
    return [m[0][3], m[1][3], m[2][3]]


def solve_nodal(b):
    vbb = b.vcc_v * b.r2_ohm / (b.r1_ohm + b.r2_ohm)
    if vbb <= b.vbe_v:
        warnings = ("ทรานซิสเตอร์อยู่ในภาวะคัตออฟ (cutoff) กระแสแทบเป็นศูนย์",)
        return BiasResult(
            ib_a=0.0,
            ic_a=0.0,
            ie_a=0.0,
            vce_v=b.vcc_v,
            vb_v=vbb,
            ve_v=0.0,
            vc_v=b.vcc_v,
            region="cutoff",
            warnings=warnings,
        )

    g1 = 1.0 / b.r1_ohm
    g2 = 1.0 / b.r2_ohm
    gc = 1.0 / b.rc_ohm
    k = 1.0 / ((1.0 + b.beta) * b.re_ohm)  # IB = k * VE

    # Unknowns [VB, VE, VC]
    # KCL @ VB: g1*(VCC-VB) - g2*VB - k*VE = 0
    # KCL @ VC: gc*(VCC-VC) - beta*k*VE = 0
    # VBE: VB - VE = VBE
    a = [
        [-g1 - g2, -k, 0.0],
        [0.0, -b.beta * k, -gc],
        [1.0, -1.0, 0.0],
    ]
    bvec = [-g1 * b.vcc_v, -gc * b.vcc_v, b.vbe_v]
    vb, ve, vc = _solve3(a, bvec)

    ie = (1.0 + b.beta) * k * ve
    ib = ie / (1.0 + b.beta)
    ic = b.beta * ib
    vce = vc - ve

    region = classify(vce)
    warnings = []
    if region == "saturation":
        warnings.append("ทรานซิสเตอร์อิ่มตัว (saturation): ค่า VCE ต่ำกว่า 0.2 V แบบจำลองเชิงเส้นอาจไม่ถูกต้อง แต่แสดงค่าที่คำนวณได้ตามจริง")
    elif VCE_SAT_V <= vce < VCE_NEAR_V:
        warnings.append("VCE ใกล้ภาวะอิ่มตัว (near saturation) ควรระวัง headroom")

    return BiasResult(
        ib_a=ib,
        ic_a=ic,
        ie_a=ie,
        vce_v=vce,
        vb_v=vb,
        ve_v=ve,
        vc_v=vc,
        region=region,
        warnings=tuple(warnings),
    )


def _region_warnings(region, vce):
    warnings = []
    if region == "saturation":
        warnings.append("ทรานซิสเตอร์อิ่มตัว (saturation): ค่า VCE ต่ำกว่า 0.2 V แบบจำลองเชิงเส้นอาจไม่ถูกต้อง แต่แสดงค่าที่คำนวณได้ตามจริง")
    elif VCE_SAT_V <= vce < VCE_NEAR_V:
        warnings.append("VCE ใกล้ภาวะอิ่มตัว (near saturation) ควรระวัง headroom")
    return tuple(warnings)


def solve_fixed_bias(b):
    """Fixed bias: RB จาก VCC ไปฐาน, อิมิตเตอร์ต่อกราวด์ตรง (VE = 0)"""
    ib = (b.vcc_v - b.vbe_v) / b.rb_ohm
    ic = b.beta * ib
    ie = (1.0 + b.beta) * ib
    ve = 0.0
    vb = ve + b.vbe_v
    vc = b.vcc_v - ic * b.rc_ohm
    vce = vc - ve
    region = classify(vce)
    return BiasResult(
        ib_a=ib,
        ic_a=ic,
        ie_a=ie,
        vce_v=vce,
        vb_v=vb,
        ve_v=ve,
        vc_v=vc,
        region=region,
        warnings=_region_warnings(region, vce),
    )


def solve_emitter_bias(b):
    """Emitter bias แหล่งจ่ายเดียว: RB จาก VCC ไปฐาน + RE จากอิมิตเตอร์ลงกราวด์"""
    ib = (b.vcc_v - b.vbe_v) / (b.rb_ohm + (1.0 + b.beta) * b.re_ohm)
    ic = b.beta * ib
    ie = (1.0 + b.beta) * ib
    ve = ie * b.re_ohm
    vb = ve + b.vbe_v
    vc = b.vcc_v - ic * b.rc_ohm
    vce = vc - ve
    region = classify(vce)
    return BiasResult(
        ib_a=ib,
        ic_a=ic,
        ie_a=ie,
        vce_v=vce,
        vb_v=vb,
        ve_v=ve,
        vc_v=vc,
        region=region,
        warnings=_region_warnings(region, vce),
    )


def solve_for_mode(mode, b):
    """เลือกสมการตามโหมด — divider ใช้เส้นทางเดิมทั้งหมด"""
    if mode == MODE_FIXED:
        return solve_fixed_bias(b)
    if mode == MODE_EMITTER:
        return solve_emitter_bias(b)
    return solve_thevenin(b)


def result_payload(r):
    """ผลลัพธ์กลาง: คีย์และหน่วยเหมือนกันทุกโหมด (V, µA, mA)"""
    return {
        "VB": {"value": r.vb_v, "unit": "V", "text": f"{r.vb_v:.2f}"},
        "VE": {"value": r.ve_v, "unit": "V", "text": f"{r.ve_v:.2f}"},
        "VC": {"value": r.vc_v, "unit": "V", "text": f"{r.vc_v:.2f}"},
        "VCE": {"value": r.vce_v, "unit": "V", "text": f"{r.vce_v:.2f}"},
        "IB": {"value": r.ib_a * 1e6, "unit": "µA", "text": f"{r.ib_a * 1e6:.3g}"},
        "IC": {"value": r.ic_a * 1e3, "unit": "mA", "text": f"{r.ic_a * 1e3:.3g}"},
        "IE": {"value": r.ie_a * 1e3, "unit": "mA", "text": f"{r.ie_a * 1e3:.3g}"},
    }


def compare(primary, independent, rel_tol=1e-6, abs_tol=1e-12):
    items = [
        ("IC", primary.ic_a, independent.ic_a),
        ("IE", primary.ie_a, independent.ie_a),
        ("VCE", primary.vce_v, independent.vce_v),
    ]
    rows = []
    for name, pval, ival in items:
        diff = abs(pval - ival)
        scale = max(abs(pval), abs(ival), 1e-30)
        ok = diff <= max(rel_tol * scale, abs_tol)
        rows.append(ComparisonRow(name=name, primary=pval, independent=ival, difference=diff, matches=ok))
    return rows
