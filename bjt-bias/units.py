"""แปลงค่าตัวเลขตามหน่วยที่ผู้ใช้เลือก ให้เป็นหน่วยฐาน (V และ Ω)

ไม่มี JavaScript ทั้งหน้า การแปลงหน่วยจึนทำฝั่ง server:
ฟอร์มส่งค่า + หน่วยที่เลือกมา แล้วฟังก์ชันนี้คืนค่าในหน่วยฐานเป็นข้อความ
ถ้าค่าแปลงไม่ได้ (ว่างหรือไม่ใช่ตัวเลข) จะคืนค่าเดิม เพื่อให้ bjt.parse_input
รับผิดชอบข้อความแจ้งข้อผิดพลาดตามเดิม
"""

VOLTAGE_UNITS = (("v", "V"), ("mv", "mV"))
RESISTANCE_UNITS = (("ohm", "Ω"), ("kohm", "kΩ"), ("mohm", "MΩ"))

_FACTORS = {
    "voltage": {"v": 1.0, "mv": 1e-3},
    "resistance": {"ohm": 1.0, "kohm": 1e3, "mohm": 1e6},
}

_LABELS = {
    "voltage": {"v": "V", "mv": "mV"},
    "resistance": {"ohm": "Ω", "kohm": "kΩ", "mohm": "MΩ"},
}


class UnitError(ValueError):
    """หน่วยที่ไม่รู้จัก — ต้องแจ้งผู้ใช้ ไม่ใช่ตีความเงียบ ๆ เป็นหน่วยฐาน"""


def unit_label(kind, unit_key):
    """ชื่อหน่วยที่แสดงผล เช่น unit_label("resistance", "kohm") -> "kΩ" """
    return _LABELS.get(kind, {}).get(unit_key, unit_key)


def to_si(value_text, unit_key, kind):
    """คืนค่าที่กรอก (เป็นข้อความ) ในหน่วยฐานของ kind

    ค่าว่างหรือไม่ใช่ตัวเลขจะคืนค่าเดิม เพื่อให้ bjt.parse_input
    รับผิดชอบข้อความแจ้งข้อผิดพลาดตามเดิม
    หน่วยที่ไม่รู้จักจะโยน UnitError เพื่อไม่ให้อ่านค่าผิดหน่วยเงียบ ๆ
    """
    text = str(value_text if value_text is not None else "").strip()
    if not text:
        return text
    factors = _FACTORS.get(kind)
    if factors is None or unit_key not in factors:
        raise UnitError(f"ไม่รู้จักหน่วย '{unit_key}' สำหรับค่าประเภท {kind}")
    try:
        value = float(text)
    except (TypeError, ValueError):
        return text
    return repr(value * factors[unit_key])
