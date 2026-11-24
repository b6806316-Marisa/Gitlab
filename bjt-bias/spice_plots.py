"""Render ngspice result columns as inline SVG (no JavaScript required)."""

from io import StringIO

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


def build_plots(op, ac_rows, tran_rows):
    """Return {'ac': svg, 'tran': svg} from parsed ngspice output rows.

    ac_rows columns: frequency, vdb(out), vp(out), vdb(in)
    tran_rows columns: time, v(in), v(out)
    """
    plots = {}

    frequency = [row[0] for row in ac_rows]
    gain = [row[1] - (row[3] if len(row) > 3 else 0.0) for row in ac_rows]
    phase = [row[2] for row in ac_rows]

    figure = Figure(figsize=(8.2, 3.9), dpi=110)
    FigureCanvasAgg(figure)
    axis = figure.add_subplot(111)
    axis.set_xscale("log")
    axis.plot(frequency, gain, color="#0b7a72", linewidth=2, label="Gain")
    axis.set_xlabel("Frequency (Hz)")
    axis.set_ylabel("Gain (dB)", color="#0b7a72")
    axis.grid(True, which="both", alpha=0.3)
    axis.set_title("AC frequency response (ngspice .ac)")
    other = axis.twinx()
    other.plot(frequency, phase, color="#a65a2c", linewidth=1.6, linestyle="--", label="Phase")
    other.set_ylabel("Phase (deg)", color="#a65a2c")
    lines = axis.get_lines() + other.get_lines()
    axis.legend(lines, [line.get_label() for line in lines], loc="lower left", fontsize=8)
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
    axis.set_title("Transient response (ngspice .tran)")
    axis.legend(loc="upper right", fontsize=8)
    figure.tight_layout()
    plots["tran"] = _svg(figure)

    return plots
