"""สร้างผังวงจรและกราฟ load line เป็น inline SVG (ไม่พึ่ง dependency ภายนอก)

โมดูลนี้เป็นฟังก์ชันบริสุทธิ์: รับค่าตัวเลข คืนข้อความ SVG
ไม่มีการอ่านไฟล์ ไม่มี side effect และไม่เกี่ยวข้องกับ Flask
"""
import html

SCHEMATIC_VIEWBOX = "0 0 560 380"
LOADLINE_VIEWBOX = "0 0 560 360"


def _fmt_resistance(ohms):
    if ohms >= 1000:
        return f"{ohms / 1000:g} kΩ"
    return f"{ohms:g} Ω"


def _fmt_voltage(volts):
    return f"{volts:g} V"


def _fmt_current(amps):
    return f"{amps * 1000:.3g} mA"


def _text(x, y, content, anchor="start", cls="lbl"):
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}">'
        f"{html.escape(content)}</text>"
    )


def _line(x1, y1, x2, y2, cls="wire"):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cls}" />'


def _rect(x, y, w, h, cls="res"):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="{cls}" />'


def _circle(cx, cy, r, cls="node"):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" class="{cls}" />'


def schematic_svg(vcc, r1, r2, rc, re, beta, vbe, nodes=None):
    """ผังวงจร BJT common-emitter แบบ voltage divider bias"""
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{SCHEMATIC_VIEWBOX}" '
        f'role="img" aria-label="ผังวงจร BJT common-emitter แบบ voltage divider bias">'
    ]

    # แหล่งจ่ายและกราวด์
    parts.append(_line(70, 50, 490, 50))
    parts.append(_line(70, 330, 490, 330))
    parts.append(_text(20, 36, f"VCC = {_fmt_voltage(vcc)}", cls="lbl"))
    for i, width in enumerate((24, 16, 8)):
        parts.append(_line(110 - width // 2, 330 + 8 + i * 6, 110 + width // 2, 330 + 8 + i * 6))

    # สาขา R1 -> เบส
    parts.append(_line(110, 50, 110, 70))
    parts.append(_rect(98, 70, 24, 70))
    parts.append(_line(110, 140, 110, 200))
    parts.append(_text(135, 96, "R1", cls="lbl"))
    parts.append(_text(135, 114, _fmt_resistance(r1), cls="val"))

    # สาขา R2 -> กราวด์
    parts.append(_rect(98, 215, 24, 70))
    parts.append(_line(110, 285, 110, 330))
    parts.append(_text(135, 241, "R2", cls="lbl"))
    parts.append(_text(135, 259, _fmt_resistance(r2), cls="val"))

    # สาขา RC -> คอลเลกเตอร์
    parts.append(_line(430, 50, 430, 70))
    parts.append(_rect(418, 70, 24, 70))
    parts.append(_line(225, 140, 430, 140))
    parts.append(_text(455, 96, "RC", cls="lbl"))
    parts.append(_text(455, 114, _fmt_resistance(rc), cls="val"))

    # ทรานซิสเตอร์
    parts.append(_circle(225, 200, 30, cls="bjtt"))
    parts.append(_line(110, 200, 195, 200))
    parts.append(_line(225, 170, 225, 140))
    parts.append(_line(225, 230, 225, 262))
    parts.append('<polygon points="219,248 231,248 225,259" class="bjtt" />')
    parts.append(_text(264, 208, f"β = {beta:g}", cls="val"))

    # สาขา RE -> กราวด์
    parts.append(_rect(213, 275, 24, 40))
    parts.append(_line(225, 315, 225, 330))
    parts.append(_text(250, 292, "RE", cls="lbl"))
    parts.append(_text(250, 310, _fmt_resistance(re), cls="val"))

    # เบสและ VBE
    parts.append(_circle(110, 200, 4))
    parts.append(_text(112, 168, f"VBE = {_fmt_voltage(vbe)}", cls="val"))

    if nodes:
        parts.append(_text(106, 186, f"VB = {nodes['vb_v']:.3g} V", anchor="end", cls="nodeval"))
        parts.append(_text(222, 258, f"VE = {nodes['ve_v']:.3g} V", anchor="end", cls="nodeval"))
        parts.append(_text(428, 158, f"VC = {nodes['vc_v']:.3g} V", anchor="end", cls="nodeval"))

    parts.append("</svg>")
    return "".join(parts)


def load_line_svg(vcc, rc, re, q_ic, q_vce):
    """กราฟ load line ของวงจร (VCE = VCC - IC*(RC+RE)) พร้อมจุด Q"""
    isat = vcc / (rc + re)
    left, right, top, bottom = 70, 520, 40, 290

    def px(vce):
        return left + (vce / vcc) * (right - left)

    def py(ic_ma):
        return bottom - (ic_ma / (isat * 1000)) * (bottom - top)

    q_ic_ma = q_ic * 1000
    outside = q_ic_ma <= 0 or q_vce < 0 or q_vce > vcc or q_ic_ma > isat * 1000
    q_x = min(max(q_vce, 0.0), vcc)
    q_y_ma = min(max(q_ic_ma, 0.0), isat * 1000)
    q_x_px = px(q_x)
    q_y_px = py(q_y_ma)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{LOADLINE_VIEWBOX}" '
        f'role="img" aria-label="กราฟ load line พร้อมจุดทำงาน Q">'
    ]

    # กริดและแกน
    parts.append(_line(left, top, left, bottom, cls="axis"))
    parts.append(_line(left, bottom, right, bottom, cls="axis"))
    parts.append(_line(left, bottom, right, bottom, cls="grid"))
    parts.append(_line(px(vcc / 2), bottom, px(vcc / 2), top, cls="grid"))
    parts.append(_line(left, py(isat * 500), right, py(isat * 500), cls="grid"))

    # เส้น load line
    parts.append(_line(left, top, right, bottom, cls="loadline"))

    # ป้ายแกน
    parts.append(_text((left + right) // 2, 330, "VCE (V)", anchor="middle", cls="axislabel"))
    parts.append(_text(20, 165, "IC (mA)", anchor="start", cls="axislabel"))
    parts.append(_text(left, 310, "0", anchor="middle", cls="tick"))
    parts.append(_text(right, 310, f"{vcc:g}", anchor="middle", cls="tick"))
    parts.append(_text(left - 8, top + 4, _fmt_current(isat), anchor="end", cls="tick"))

    # จุด Q
    parts.append(_line(q_x_px, bottom, q_x_px, q_y_px, cls="qguide"))
    parts.append(_line(left, q_y_px, q_x_px, q_y_px, cls="qguide"))
    parts.append(_circle(q_x_px, q_y_px, 5, cls="qdot"))
    label = f"Q ({q_ic_ma:.3g} mA, {q_vce:.3g} V)"
    if q_x_px + 12 + 7 * len(label) <= 560:
        parts.append(_text(q_x_px + 12, q_y_px - 10, label, cls="qlab"))
    else:
        parts.append(_text(q_x_px - 12, q_y_px - 10, label, anchor="end", cls="qlab"))

    if outside:
        parts.append(
            _text(
                left,
                352,
                "Q-point อยู่นอกเส้น load line (ทรานซิสเตอร์ไม่ทำงานในเขตแอคทีฟ)",
                cls="warnnote",
            )
        )

    parts.append("</svg>")
    return "".join(parts)
