# BJT Common-Emitter DC Bias Web App — Design

Lab: ENG29 2121. Date: 2026-11-10. Status: awaiting approval.

## Intent

A small, real Flask web application that computes the DC operating point of a
voltage-divider-biased BJT common-emitter stage. It exists so a student can type
seven component values, see the bias point with units, be warned when the
transistor is not in the active region, and see that a second, independently
derived calculation agrees.

Why: it is the graded lab deliverable, demonstrated on localhost and committed
to GitHub the same day. "Smallest working" is the governing constraint.

## Goals

- Compute and display `IB, IC, IE, VCE, VB, VE, VC` for a voltage-divider bias.
- Reject bad input with a clear message; never return a 500 for user input.
- Classify the region (active / cutoff / saturation) and warn when not active.
- Show the primary result and an independent nodal-analysis result side by side
  with the difference and a match/mismatch verdict.
- Separate engineering logic, Flask routes, templates, CSS, and tests.
- Run on localhost and be committed and pushed today.

## Non-goals

- AC analysis, gain, input/output impedance, frequency response.
- Transient or time-domain simulation.
- Schematic editor, netlist import, component library, database, auth, JS.
- FET or other topologies (fixed bias, emitter feedback, collector feedback).
- Plotting or export.

## Anti-goals

- A result that is physically wrong or silently accepts nonsense.
- Clamping or "fixing" the linear-model answer without saying so.
- Refactoring or deleting the existing DC resistor calculator in this repo.
- Framework or dependency sprawl beyond Flask.

## Constraints

- Python 3.12, Flask only new runtime dependency.
- Tests use the standard library `unittest` (already used in this repo).
- Inputs: `VCC` (V), `R1, R2, RC, RE` (Ω), `beta` (dimensionless), `VBE` (V).
- Display currents in mA (IB also in µA), voltages in V.
- UI labels in Thai with standard engineering symbols; code identifiers in English.
- Windows development machine; files must be UTF-8.
- The new app lives in `bjt-bias/`; existing root files stay untouched.

## Approaches considered

1. **Thevenin base-loop primary + nodal-analysis check, both in app (chosen).**
   The textbook method is the primary answer; a second solver forms the KCL
   equations and solves a 3×3 linear system. Self-contained, demo-friendly,
   and the agreement is real evidence rather than a typed-in number.
   Trade-off: two implementations to keep correct.
2. **Single method only.** Simplest, but fails the "compare with an independent
   calculation" requirement.
3. **User types a hand-calculated reference value.** Closest to a lab worksheet,
   but the demo depends on the student's arithmetic, and it adds a field that
   can be wrong for reasons unrelated to the app.

Chosen: approach 1.

## Design

### Layout

```
bjt-bias/
  bjt.py                 # pure engineering logic, no Flask
  app.py                 # Flask routes only
  templates/index.html   # form + results, one page
  static/style.css       # presentation only
  tests/test_bjt.py      # logic tests
  tests/test_app.py      # route tests via Flask test client
  requirements.txt       # Flask
  README.md              # install, run, demo values
```

### Engineering model (`bjt.py`)

Inputs validated once, then solved by both methods.

Primary (Thevenin):

```
VBB = VCC * R2 / (R1 + R2)
RB  = R1 * R2 / (R1 + R2)
IB  = (VBB - VBE) / (RB + (1 + beta) * RE)
IC  = beta * IB
IE  = (1 + beta) * IB
VE  = IE * RE
VB  = VBE + VE
VC  = VCC - IC * RC
VCE = VC - VE
```

Independent (nodal). Unknowns `VB, VE, VC`; with `IB = VE / ((1+beta)*RE)`:

```
(VCC - VB)/R1 - VB/R2 - IB          = 0
(VCC - VC)/RC - beta * IB           = 0
VB - VE                             = VBE
```

Solved by a hand-written 3×3 Gaussian elimination with partial pivoting. This
shares the model (fixed `VBE`, `IC = beta*IB`) but not the derivation.

Cutoff guard: when `VBB <= VBE` the transistor is off. Both methods return
`IB = IC = IE = 0`, `VE = 0`, `VB = VBB`, `VC = VCC`, `VCE = VCC`, region
`cutoff`. No division by a negative base current.

Saturation: the app reports the linear-model result and flags the region when
`VCE < 0.2 V` (including negative or zero `VCE`, deep saturation). It does **not**
clamp `VCE` to 0.2 V. The warning says the linear model no longer holds and the
unclamped value is shown as-is. (Builder must keep this behavior.)

Near-saturation: `0.2 V <= VCE < 0.5 V` gets a warning but stays `active`.

### Validation rules

Every field required, numeric, finite. Reject when:

- `VCC <= 0`
- any of `R1, R2, RC, RE <= 0`
- `beta <= 0`
- `VBE < 0` or `VBE >= VCC`
- value is `nan`, `inf`, empty, or non-numeric

Errors are collected and shown together in Thai; the form keeps what the user
typed. No exceptions escape to a 500.

### Comparison

Both results are computed for every valid input. Compare `IC`, `IE`, `VCE`
with relative tolerance `1e-6` (absolute `1e-12` for near-zero). Display both
columns, the absolute difference, and a Thai verdict: `ตรงกัน` or `ไม่ตรงกัน`.
A mismatch is shown, not hidden.

### Web layer (`app.py`)

- `GET /` → empty form with sensible defaults
  (`VCC=12, R1=47000, R2=10000, RC=2200, RE=470, beta=150, VBE=0.7`).
- `POST /` → parse and validate; on error re-render the same page with the
  submitted values and the error list; on success render the same page with
  the results. One template, no redirects, no session, no secret key.
- `python app.py` serves `http://127.0.0.1:5000`.

Defaults were chosen to land in the active region: `VBB ≈ 2.11 V`,
`IC ≈ 2.66 mA`, `VCE ≈ 4.89 V`.

### Page content

1. Form: seven labeled numeric fields, unit hints, Calculate button.
2. Region badge: active / cutoff / saturation.
3. Warnings list (empty when active and not near saturation).
4. Results table: `IB` (µA and mA), `IC`, `IE` (mA), `VB`, `VE`, `VC`, `VCE` (V),
   each with its unit.
5. Comparison table: quantity, primary, nodal, difference, verdict.
6. Footer: formula reference and the fixed `VBE` / linear-model caveat.

### Tests

Logic (`tests/test_bjt.py`):

- Known active case matches hand-computed values within `1e-9` relative.
- Cutoff case returns zero currents and `VCE = VCC`.
- Saturation case is classified `saturation` and is not clamped.
- Boundary: `VCE` just below `0.2 V` → saturation; just above → active.
- Each validation rule raises the app's validation error.
- Thevenin and nodal agree within `1e-9` for several active cases.

Routes (`tests/test_app.py`, Flask test client):

- `GET /` → 200 and all seven field names present.
- `POST /` valid → 200, contains `IC`, the computed mA value, and `ตรงกัน`.
- `POST /` with `R1=0` → 200, contains an error message, no traceback.
- `POST /` with `abc` → 200, contains an error message.
- Invalid submission echoes the entered values back.

### Git and demo

- Work on branch `lab/bjt-ce-bias`, one commit per task.
- Finish: run the test suite, start the app, verify `GET /` and a valid `POST /`
  in a browser, then merge to `main` and push to `origin`.
- README documents venv setup, `pip install -r requirements.txt`,
  `python app.py`, and the demo values above.

## Definition of done

- `python -m unittest discover -s tests -v` passes from `bjt-bias/`.
- `python app.py` serves the page; a valid submission shows all seven
  quantities with units, an active badge, and a `ตรงกัน` comparison.
- An invalid submission shows a Thai error and keeps the typed values.
- The existing `electrical.py`, `test_electrical.py`, and root `README.md`
  are unchanged.
- Work is committed and pushed to GitHub.

## Left to the builder

Exact Thai wording, CSS styling, table ordering within the constraints above,
and the internal helper names. Numeric defaults may be adjusted only if the
documented demo case remains active.
