# BJT CE Bias Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the smallest working Flask app that computes the DC operating point of a voltage-divider-biased BJT common-emitter stage, with validation, region warnings, and a Thevenin-vs-nodal independent cross-check.

**Architecture:** Pure engineering module `bjt.py` (input model, validation, Thevenin solver, nodal solver, comparison) is imported by `app.py` (Flask routes only). One template renders form + results; one CSS file; two unittest files run route- and logic-level tests via the Flask test client and plain function calls.

**Tech Stack:** Python 3.12, Flask (only new dependency), stdlib `unittest`, hand-written 3×3 Gaussian elimination (no numpy).

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-ce-bias-design.md`

## Global Constraints

- New code lives only under `bjt-bias/`; `electrical.py`, `test_electrical.py`, root `README.md` must remain byte-identical.
- Only new runtime dependency: `Flask>=3.0`; tests use stdlib `unittest`.
- Inputs: `VCC` (V), `R1, R2, RC, RE` (Ω), `beta`, `VBE` (V). Display: currents in mA (`IB` additionally in µA), voltages in V. Numbers formatted `{x:.4g}`.
- Region constants: `"active"`, `"cutoff"`, `"saturation"`; UI shows `Active` / `Cutoff` / `Saturation`. Warnings and error messages in Thai; code identifiers in English.
- Files are UTF-8. Test messages use marker `class="error"` instead of exact Thai strings.
- Saturation is flagged, never clamped: a negative or sub-0.2 V computed `VCE` is reported as-is.
- Comparison tolerance: relative `1e-6`, absolute `1e-12` for near-zero compared quantities; verdict `matches` bool.
- Form defaults exactly: `VCC=12, R1=47000, R2=10000, RC=2200, RE=470, VBE=0.7, beta=150` (active region: `IC ≈ 2.661 mA`, `VCE ≈ 4.887 V`).
- Branch `lab/bjt-ce-bias`; conventional commits (`feat:`, `test:") matching existing repo style.
- All test/run commands are executed with working directory `bjt-bias/`.

## Review Focus

These input classes are the ones most likely to bite a user; each has a pinning test in the owning task.

1. Empty or whitespace-only field (e.g. `R1 = ""`) → user sees a per-field Thai error and their entered values, never a 500. Pinned by Task 1 `test_empty_string_is_missing`, Task 4 `test_blank_submission_round_trips`.
2. `VBE` at or above `VCC` (e.g. `VBE = 12`, `VCC = 12`) → rejected as invalid input, not solved with a negative headroom. Pinned by Task 1 `test_vbe_must_be_less_than_vcc`.
3. `beta = 1` (worst-case low) and `beta = 1e6` (flood-typed beta) → valid numbers, finite results, no crash; large beta lands in saturation. Pinned by Task 2/3 `test_beta_extremes_are_finite`.
4. Saturated circuit (e.g. `RC = 10000, RE = 100, R1 = R2 = 10000`) → negative `VCE` still displayed, region `Saturation` with a warning; nothing clamped to 0.2 V. Pinned by Task 2 `test_saturation_is_flagged_not_clamped`.
5. Cutoff circuit (`R2 = 1000` with above defaults) → zero currents, `VCE = VCC = 12`, both methods agree, no division-by-negative error. Pinned by Task 2 `test_cutoff_returns_zero_currents`, Task 3 agreement loop.

---

### Task 1: Input model and validation (`bjt.py`)

**Files:**
- Create: `bjt-bias/bjt.py`
- Test: `bjt-bias/tests/test_bjt.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  ```python
  class BiasError(ValueError):
      errors: list[str]        # per-field Thai messages

  @dataclass(frozen=True)
  class BiasInput:
      vcc_v: float; r1_ohm: float; r2_ohm: float
      rc_ohm: float; re_ohm: float; beta: float; vbe_v: float

  FIELD_ORDER: tuple[str, ...] = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")

  def parse_input(raw: dict[str, str]) -> BiasInput  # raises BiasError carrying all messages
  ```

- [ ] **Step 1: Write the failing tests** (`class TestParseInput`):
  - `test_known_happy_case`: `parse_input({"vcc":"12","r1":"47000","r2":"10000","rc":"2200","re":"470","beta":"150","vbe":"0.7"})` → `BiasInput` with exactly `BiasInput(12.0, 47000.0, 10000.0, 2200.0, 470.0, 150.0, 0.7)` (attribute-by-attribute `assertEqual`).
  - `test_missing_field_is_rejected`: drop `"r2"` → `BiasError` with ≥1 message.
  - `test_empty_string_is_missing`: `r1 = ""` and `"   "` variants → `BiasError` (loop with `subTest`).
  - `test_non_numeric_is_rejected`: `rc = "abc"` → `BiasError`.
  - `test_nan_inf_rejected`: `vcc in (nan, inf, -inf)`, also `re` → `BiasError` (loops).
  - `test_nonpositive_values_rejected`: `vcc = 0`, `vcc = -5`, `r1 = 0`, `re = -1`, `beta = 0` (subTests) → `BiasError`.
  - `test_vbe_must_be_less_than_vcc`: `vbe = -0.1` and `vbe == vcc == 12` → `BiasError`.
- [ ] **Step 2: Run to verify they fail**: `python -m unittest discover -s tests -p "test_bjt.py" -v` — expected FAIL (`ModuleNotFoundError: bjt`).
- [ ] **Step 3: Implement** `BiasError`, `BiasInput`, `FIELD_ORDER`, `parse_input` in `bjt.py`. Float conversion with `float(s.strip())` guarded by `try/except (TypeError, ValueError)`; finiteness via `math.isfinite`; positive checks per spec; collect every failing field's message into one `BiasError` (validate all seven, don't fail fast on the first).
- [ ] **Step 4: Run to verify they pass** — same command, expected OK.
- [ ] **Step 5: Commit** `bjt.py tests/test_bjt.py` → `test: validate BJT bias inputs`.

### Task 2: Thevenin solver and region classification (`bjt.py`)

**Files:**
- Modify: `bjt-bias/bjt.py`
- Test: `bjt-bias/tests/test_bjt.py` (new class `TestSolveThevenin`)

**Interfaces:**
- Consumes: `BiasInput`, `FIELD_ORDER` from Task 1.
- Produces:
  ```python
  @dataclass(frozen=True)
  class BiasResult:
      ib_a: float; ic_a: float; ie_a: float
      vce_v: float; vb_v: float; ve_v: float; vc_v: float
      region: str            # "active" | "cutoff" | "saturation"
      warnings: tuple[str, ...]   # Thai, may be empty

  def solve_thevenin(b: BiasInput) -> BiasResult
  def classify(vce_v: float) -> str
  ```
  Constants `VCE_SAT_V = 0.2`, `VCE_NEAR_V = 0.5`.

- [ ] **Step 1: Write the failing tests**:
  - `test_known_active_case`: input from defaults → `assertAlmostEqual` per-field against `ib_a=1.7739724e-05, ic_a=2.6609587e-03, ie_a=2.6786984e-03, vce_v=4.8869027, vb_v=1.9589882, ve_v=1.2589882, vc_v=6.145891` (`delta=1e-8` scaled), `region == "active"`, `warnings == ()`.
  - `test_cutoff_returns_zero_currents`: `r2 = 1000`, others defaults (`VBB = 0.25 V ≤ 0.7`) → `ib_a == ic_a == ie_a == 0`, `ve_v == 0`, `vce_v == 12`, `region == "cutoff"`, at least one warning.
  - `test_saturation_is_flagged_not_clamped`: `(12, 10000, 10000, 10000, 100, 150, 0.7)` → `vce_v < 0` still, `region == "saturation"`, at least one warning, and `vce_v` equals `vcc - ic*rc - ie*re` recomputed in the test (proves no clamping).
  - `test_beta_extremes_are_finite`: `beta = 1` → finite active result; `beta = 1e6` → finite, `region == "saturation"`.
  - `test_classify_boundaries`: `classify(0.19) == "saturation"`, `classify(0.2) == "saturation"`, `classify(0.21) == "active"`, `classify(0.49) == "active"`, `classify(0.5) == "active"`.
- [ ] **Step 2: Run to verify they fail**: `python -m unittest discover -s tests -p "test_bjt.py" -v` — expected FAIL (`AttributeError / ImportError`).
- [ ] **Step 3: Implement** `classify`, `solve_thevenin` in `bjt.py` per the spec's formulas; cutoff branch when `vbb <= vbe` (zero currents, `vb = vbb`, `vc = vcc`, `vce = vcc`, warning); saturation warning when `vce < 0.2`; near-saturation warning when `0.2 <= vce < 0.5`.
- [ ] **Step 4: Run to verify they pass** — expected OK.
- [ ] **Step 5: Commit** → `feat: thevenin solver with region classification`.

### Task 3: Nodal solver and comparison (`bjt.py`)

**Files:**
- Modify: `bjt-bias/bjt.py`
- Test: `bjt-bias/tests/test_bjt.py` (new classes `TestSolveNodal`, `TestCompare`)

**Interfaces:**
- Consumes: `BiasInput` (Task 1), `BiasResult` (Task 2).
- Produces:
  ```python
  def solve_nodal(b: BiasInput) -> BiasResult

  @dataclass(frozen=True)
  class ComparisonRow:
      name: str              # "IC" | "IE" | "VCE"
      primary: float
      independent: float
      difference: float
      matches: bool

  def compare(primary: BiasResult, independent: BiasResult, rel_tol: float = 1e-6, abs_tol: float = 1e-12) -> list[ComparisonRow]
  ```

- [ ] **Step 1: Write the failing tests**:
  - `test_nodal_agrees_with_thevenin`: loop over cases `(12,47000,10000,2200,470,150,0.7)`, `(9,10000,4700,1000,220,100,0.6)`, `(5,22000,4700,1200,330,200,0.65)`, `(12,47000,10000,2200,470,1,0.7)`, `(12,47000,10000,2200,470,1e6,0.7)`, and the cutoff case `(12,47000,1000,2200,470,150,0.7)` — for each, every field of `solve_nodal` and `solve_thevenin` agrees with relative error `≤ 1e-9` (`assertAlmostEqual` on `rel_diff`, or `assertAlmostEqual` places=9 where values are O(1)).
  - `test_beta_extremes_are_finite` (nodal side): same two betas, finite results, no exception.
  - `test_compare_flags_agreement`: `compare(solve_thevenin(c), solve_nodal(c))` → 3 rows `(names == ["IC","IE","VCE"])`, every `matches is True`, `difference` tiny.
  - `test_compare_flags_mismatch`: hand-build two `BiasResult`s (region/warnings filled but `ic_a` `2.0e-3` vs `2.5e-3`) → the `IC` row `matches is False`; other rows built identical still match.
- [ ] **Step 2: Run to verify they fail** — expected FAIL (`ImportError: solve_nodal`).
- [ ] **Step 3: Implement** `solve_nodal` (3 unknowns `VB, VE, VC`; equations per spec; same cutoff branch as Task 2 so off-circuits never solve a negative `IB`) with a module-private `_solve3(a: list[list[float]], b: list[float]) -> list[float]` doing Gaussian elimination with partial pivoting; implement `compare` on `(ic_a, ie_a, vce_v)` with relative/absolute tolerance from the Global Constraints.
- [ ] **Step 4: Run to verify they pass** — expected OK.
- [ ] **Step 5: Commit** → `feat: nodal cross-check with comparison`.

### Task 4: Flask app, template, CSS, venv, requirements

**Files:**
- Create: `bjt-bias/app.py`, `bjt-bias/templates/index.html`, `bjt-bias/static/style.css`, `bjt-bias/requirements.txt`
- Modify: root `.gitignore` (add `.venv/` only if not present)
- Test: `bjt-bias/tests/test_app.py`

**Interfaces:**
- Consumes: `parse_input`, `solve_thevenin`, `solve_nodal`, `compare`, `BiasError` from Tasks 1–3.
- Produces:
  ```python
  def create_app() -> Flask       # GET "/" (form) and POST "/" (results/errors)
  # GET "/" context: {"form": dict[str, str]}        defaults when empty
  # OK  POST   context: adds {"results": {…}, "compare_rows": [ComparisonRow]}
  # ERR POST   context: {"form": dict, "errors": [str]}
  ```
- [ ] **Step 1: Write the failing tests** (`class TestRoutes`):
  - `test_get_shows_form`: `client.get("/")` → 200, and all seven field names present in the HTML.
  - `test_post_valid_shows_results`: POST the defaults → 200, body contains `"2.661"` (IC mA), `"Saturation"` not present, `"Active"`, and `"ตรงกัน"`.
  - `test_post_invalid_zero_resistance`: `r1 = "0"` → 200 (not 500), body contains `class="error"` and no results.
  - `test_post_non_numeric`: `rc = "abc"` → 200, `class="error"`.
  - `test_blank_submission_round_trips`: `r1 = ""` → 200, `class="error"`, and the value `12` still present in an `input` tag (entered-value echo).
- [ ] **Step 2: Create venv and install Flask**: `python -m venv .venv` inside `bjt-bias/` (decided location: `bjt-bias/.venv`, so all later commands are `.venv\Scripts\python` relative to `bjt-bias/`), write `requirements.txt` (`Flask>=3.0`), install with `.venv\Scripts\python -m pip install -r requirements.txt`. Ensure root `.gitignore` lists `.venv/`.
- [ ] **Step 3: Run to verify tests fail**: `.venv\Scripts\python -m unittest discover -s tests -v` — `test_app` FAILS (ModuleNotFoundError `app`), `test_bjt` still PASSES.
- [ ] **Step 4: Implement** `create_app` in `app.py` (parse → `solve_thevenin` → `solve_nodal` → `compare`; error path passes the submitted form dict + `BiasError.errors` back to the same template; no redirect, no session), `templates/index.html` (single page: form block, conditionally region box with `Active`/`Cutoff`/`Saturation`, warnings `<ul>`, results table rows `IB` µA+mA, `IC`/`IE` mA, `VB`/`VE`/`VC`/`VCE` V with `.4g` values, comparison table quantity/primary/nodal/Δ/verdict `ตรงกัน`|`ไม่ตรงกัน`, footer with the Thevenin formulas and fixed-`VBE` caveat), Thai labels + unit hints; `static/style.css` minimal card/table styling, linked via `url_for('static', filename='style.css')`; `app.run(debug=True, port=5000)` under `if __name__ == "__main__"`.
- [ ] **Step 5: Run full suite to pass**: `.venv\Scripts\python -m unittest discover -s tests -v` — expected all OK.
- [ ] **Step 6: Commit** `app.py templates static requirements.txt tests/test_app.py` (+ `.gitignore` if touched) → `feat: flask ui for bjt bias calculation`.

### Task 5: README, demo verification, final commit

**Files:**
- Create: `bjt-bias/README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: run instructions and the documented demo case.

- [ ] **Step 1: Write README** (Thai + code blocks): venv setup, `pip install -r requirements.txt`, `python app.py` → `http://127.0.0.1:5000`, the defaults demo values and the expected active-region outputs, and the formula listing from the spec.
- [ ] **Step 2: Final full test run**: `.venv\Scripts\python -m unittest discover -s tests -v` — expected all OK, no skips.
- [ ] **Step 3: Verify untouched old lab**: `git status --porcelain` shows no changes to `electrical.py`, `test_electrical.py`, `README.md` (root).
- [ ] **Step 4: Local smoke run**: start `python app.py` in the background; `curl` (or test client) `GET /` → 200 `INDEX`, `POST /` defaults → contains `ตรงกัน` and `2.661`, `POST /` `r1=0` → contains `class="error"`. Stop the server.
- [ ] **Step 5: Commit** README → `docs: readme with run and demo instructions`.

## Completion (after all tasks)

Branch `lab/bjt-ce-bias` is verified: full suite green, old lab untouched. Then invoke `finishing-a-development-branch` skill to merge/wrap up: merge to `main`, push `origin`. Commit messages and the pushed state are the remaining reviewer-visible artifacts. Demo request: `http://127.0.0.1:5000`.
