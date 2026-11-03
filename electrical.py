import math


def calculate_dc(voltage_v, resistance_ohm):
	if not math.isfinite(voltage_v):
		raise ValueError("แรงดันต้องเป็นตัวเลขที่ถูกต้อง")
	if not math.isfinite(resistance_ohm) or resistance_ohm <= 0:
		raise ValueError("ความต้านทานต้องมากกว่าศูนย์")

	current_a = voltage_v / resistance_ohm
	power_w = voltage_v * current_a
	return current_a, power_w


def read_number(prompt):
	while True:
		try:
			return float(input(prompt))
		except ValueError:
			print("กรุณาป้อนค่าเป็นตัวเลข")


def main():
	while True:
		voltage_v = read_number("ป้อนแรงดัน V (โวลต์): ")
		resistance_ohm = read_number("ป้อนความต้านทาน R (โอห์ม): ")

		try:
			current_a, power_w = calculate_dc(voltage_v, resistance_ohm)
			break
		except ValueError as error:
			print(error)

	print(f"กระแส I = {current_a:.6g} A")
	print(f"กำลังไฟฟ้า P = {power_w:.6g} W")


if __name__ == "__main__":
	main()