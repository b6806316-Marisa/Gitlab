import math
from dataclasses import dataclass

FIELD_ORDER = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")

FIELD_LABELS = {
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rc": "RC",
    "re": "RE",
    "beta": "beta",
    "vbe": "VBE",
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


def parse_input(raw):
    """อ่านค่า 7 ช่องจากฟอร์ม (dict ของข้อความ) แล้วคืน BiasInput

    รวบรวมข้อความผิดพลาดของทุกช่องไว้ใน BiasError.errors ก่อนยกเสมอ
    """
    errors = []
    values = {}

    for field in FIELD_ORDER:
        label = FIELD_LABELS[field]
        text = str(raw.get(field, "")).strip()
        try:
            values[field] = float(text or "nan")
        except (TypeError, ValueError):
            values[field] = None
            errors.append(f"{label} ต้องเป็นตัวเลขที่ถูกต้อง")

    vcc = values["vcc"]
    if vcc is not None and not (math.isfinite(vcc) and vcc > 0):
        errors.append("VCC ต้องมีค่ามากกว่าศูนย์")

    for field in ("r1", "r2", "rc", "re"):
        value = values[field]
        if value is not None and not (math.isfinite(value) and value > 0):
            errors.append(f"{FIELD_LABELS[field]} ต้องมีค่ามากกว่าศูนย์")

    beta = values["beta"]
    if beta is not None and not (math.isfinite(beta) and beta > 0):
        errors.append("beta ต้องมีค่ามากกว่าศูนย์")

    vbe = values["vbe"]
    if vcc is not None and vbe is not None:
        if not math.isfinite(vbe):
            errors.append("VBE ต้องเป็นตัวเลขที่ถูกต้อง")
        elif not (0 <= vbe < vcc):
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
