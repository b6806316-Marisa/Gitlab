"""Render ngspice result columns as inline SVG (no JavaScript required)."""

from io import StringIO
import math

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


def _svg(figure):
    buffer = StringIO()
    figure.savefig(buffer, format="svg")
    text = buffer.getvalue()
    start = text.find("<svg")
    return text[start:] if start >= 0 else text


def ac_metrics(row):
    """Return (gain_db, phase_deg) of Vout/Vin from one AC result row.

    ac row columns: frequency, vdb(out), vp(out), vdb(in), vp(in)
    ngspice 47 writes vp() in radians, so convert the difference to degrees.
    """
    gain_db = row[1] - (row[3] if len(row) > 3 else 0.0)
    phase_rad = row[2] - (row[4] if len(row) > 4 else 0.0)
    return gain_db, math.degrees(phase_rad)


def build_plots(op, ac_rows, tran_rows, sin_freq_hz=None):
    """Return {'ac': svg, 'tran': svg} from parsed ngspice output rows.

    ac_rows columns: frequency, vdb(out), vp(out), vdb(in), vp(in)
    tran_rows columns: time, v(in), v(out)
    """
    plots = {}

    frequency = [row[0] for row in ac_rows]
    metrics = [ac_metrics(row) for row in ac_rows]
    gain = [item[0] for item in metrics]
    phase = [item[1] for item in metrics]

    figure = Figure(figsize=(8.2, 4.2), dpi=110)
    FigureCanvasAgg(figure)
    axis = figure.add_subplot(111)
    axis.set_xscale("log")
    axis.plot(frequency, gain, color="#0b7a72", linewidth=2, linestyle="-", label="Gain (dB)")
    axis.set_xlabel("Frequency (Hz)")
    axis.set_ylabel("Gain (dB)", color="#0b7a72")
    axis.tick_params(axis="y", labelcolor="#0b7a72")
    axis.grid(True, which="both", alpha=0.3)
    axis.set_title("AC Response (ngspice .ac)")

    phase_axis = axis.twinx()
    phase_axis.plot(
        frequency, phase, color="#a65a2c", linewidth=1.8, linestyle="--", label="Phase (deg)"
    )
    phase_axis.set_ylabel("Phase (deg)", color="#a65a2c")
    phase_axis.tick_params(axis="y", labelcolor="#a65a2c")

    lines = axis.get_lines() + phase_axis.get_lines()
    axis.legend(lines, [line.get_label() for line in lines], loc="best", fontsize=8)
    figure.tight_layout()
    plots["ac"] = _svg(figure)

    time = [row[0] * 1e3 for row in tran_rows]
    vin = [row[1] * 1e3 for row in tran_rows]
    vout_dc = op.get("vout", 0.0)
    vout = [(row[2] - vout_dc) * 1e3 for row in tran_rows]

    figure = Figure(figsize=(8.2, 3.9), dpi=110)
    FigureCanvasAgg(figure)
    axis = figure.add_subplot(111)
    axis.plot(time, vin, color="#0b7a72", linewidth=1.6, label="Vin")
    axis.plot(time, vout, color="#c77a35", linewidth=1.6, label="Vout - DC")
    axis.set_xlabel("Time (ms)")
    axis.set_ylabel("Voltage (mV)")
    axis.grid(True, alpha=0.3)
    if sin_freq_hz:
        freq_label = f"{sin_freq_hz / 1000:g} kHz" if sin_freq_hz >= 1000 else f"{sin_freq_hz:g} Hz"
        title = f"Transient response (f = {freq_label}, ngspice .tran)"
    else:
        title = "Transient response (ngspice .tran)"
    axis.set_title(title)
    axis.legend(loc="upper right", fontsize=8)
    figure.tight_layout()
    plots["tran"] = _svg(figure)

    return plots
