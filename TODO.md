# TODO

Things to improve or fix, found while reviewing the codebase.

## Bugs

- [x] Table-file paths built with hardcoded backslashes (`gear.py`, `helical_gear.py`,
  `spring.py` — `os.path.dirname(__file__) + "\\tables\\..."`) — confirmed by actually running
  `examples/gears_examples/Gears_examples.py` on Linux: crashed with `FileNotFoundError` on
  `me_toolbox/gears\tables\...`. Switched all four call sites to `os.path.join`.
- [x] **`BoltPattern`'s fatigue calculation was completely broken.**
  `me_toolbox/fasteners/bolt_pattern.py:301` (`variable_equivalent_stresses`, called from
  `fatigue_safety_factor`) constructed `FatigueAnalysis` with a signature that no longer matched
  `FatigueAnalysis.__init__` at all: passed `endurance_limit=endurance_limit[i]` (an
  `EnduranceLimit` *object*) where the constructor expects `modified_endurance_limit` as a
  **float**; never passed `stress_type` or `ultimate_tensile_strength`, both required with no
  default; passed `Sy=` where the parameter is actually named `yield_strength`. Confirmed by
  executing `examples/fasteners_examples/BoltPattern_example.ipynb`, which crashed at this call
  for every user of `BoltPattern.fatigue_safety_factor`/`variable_equivalent_stresses`. Fixed:
  now passes `modified_endurance_limit=endurance_limit[i].modified`, `stress_type='multiple'`
  (both normal and torsion stress are involved), `ultimate_tensile_strength=fastener.bolt.tensile_strength`,
  `yield_strength=fastener.bolt.yield_strength`. Verified end-to-end via the notebook and a new
  regression test in `test_bolt_pattern.py`.
- [ ] `ExtensionSpring.weight` (inherited unchanged from `HelicalCompressionSpring`) reads
  `self.total_coils`, but `ExtensionSpring.total_coils` deliberately overrides that to raise
  `NotImplementedError` ("has no use in ExtensionSpring") — so `.weight` is unusable on any
  `ExtensionSpring` instance. Looks unintentional; probably should use `self.body_coils` for
  extension springs, or `weight` needs its own `ExtensionSpring` override. Found while writing
  `test_extension_spring.py` (pinned down as `test_weight_raises_due_to_total_coils`).
- [ ] `ExtensionSpring.__repr__` (extension_spring.py:20) — the `hook_shear_yield_percent=...`
  field actually interpolates `self.hook_normal_yield_percent` instead of
  `self.hook_shear_yield_percent`. Copy-paste bug, cosmetic (only affects `repr()` output) but
  easy one-line fix.
- [ ] `me_toolbox/gears/gear.py` `Kb` property (see `FIXME` at
  `me_toolbox/fatigue/endurance_limit.py:76`) — falls through and returns `None` silently when
  `de` is outside `2.79-254`, instead of raising or covering the full range.
- [ ] `me_toolbox/gears/gear.py` `YN` property (~line 258) — returns the string `"Error"` on a
  bad hardness key instead of raising, so callers doing math on `YN` get a `TypeError` far from
  the real cause instead of a clear error at the source.
- [ ] `me_toolbox/fatigue/fatigue_analysis.py` `miner_rule` (~line 461) — when
  `reversible_stress` falls outside both the LCF and HCF ranges, the code prints a warning but
  appends nothing, so `group[-1]` stays the raw `reversible_stress` instead of a cycle count.
  The final `group[0]/group[-1]` division then silently produces a dimensionally-wrong result
  instead of failing loudly.
- [ ] README usage example: `pattern = fasteners.BoltPattern(fasteners, ...)` passes the
  `fasteners` module itself as the first argument — looks like a copy-paste typo, should be a
  list of fastener/location data.

## Dependency & packaging hygiene

- [ ] `icecream` is imported by `fatigue_analysis.py` but declared in neither
  `requirements.txt` nor `setup.py` — fresh installs break on import.
- [x] `requirements.txt`'s pinned `numpy==1.20.1` **failed to build at all on Python 3.11**
  (confirmed: no wheel available, source build errored out) — not just staleness risk, it
  actively blocked installing the project from `requirements.txt` on any recent Python.
  Dropped all exact version pins from `requirements.txt` (now just `numpy`/`sympy`/`mpmath`/
  `icecream`, unpinned), matching `setup.py`'s already-unpinned `install_requires` (which now
  also lists `icecream`). Whole suite validated running against `numpy 2.4.6`/`sympy 1.14.0`.
- [ ] `examples/fasteners_examples/*.ipynb` import `inflect` (used only for cosmetic "1st/2nd/3rd"
  ordinal formatting in printed output) without declaring it anywhere — blocks running the
  example notebooks from a fresh environment.

## Confirmed by actually running the examples and test suite

Ran every example script/notebook and the full `unittest` suite against the code as of this
pass. Two of the bugs above (hardcoded paths, `BoltPattern` fatigue) were caught this way. Also
found and fixed some now-stale examples, and found the existing test suite is significantly out
of sync with the current API:

- [x] `examples/fatigue_examples/FatigueAnalysis_example.py` imported `uniform_stress`/
  `torsion_stress` from `me_toolbox.fatigue` — broken since `stress.py` moved to `me_toolbox.tools`
  (commit `ffbd80e`). Fixed the import. (Confirms the symbolic `Symbol`/`Eq`/`solveset` pattern in
  this file still works end-to-end today, for what it's worth.)
- [x] `examples/fasteners_examples/BoltPattern_example.ipynb` and `BoltPattern_example2.ipynb`
  had an f-string nesting `"` inside a `"`-delimited f-string
  (`f"...{["%.2f" % x for x in ...]}..."`) — a syntax error on Python < 3.12 (PEP 701's relaxed
  f-string grammar is 3.12+ only), so these notebooks couldn't even parse despite `setup.py`
  claiming `python_requires=">=3.9"`. Requoted to single quotes.
- [x] `examples/fasteners_examples/BoltPattern_example.ipynb` called
  `fastener.separation_safety_factor(...)`/`load_safety_factor(...)`/`proof_safety_factor(...)`
  on individual `ThreadedFastener` objects — those methods only exist on `BoltPattern` now (see
  `BoltPattern_example2.ipynb`, which already calls them correctly at the pattern level).
  Replaced with `pattern.<method>(verbose=True)`, matching example2's working style.
- [x] **The existing test suite was stale against the current API — 14 of 45 tests failed/errored.**
  Confirmed the owner: trust the current code, fix the tests. Fixed:
  - `test_bolt.py` (4 failures): was testing the *old* approximate geometry formulas
    (`diameter - (5/8)*height` etc.) and an *old* constructor semantics where the 4th
    positional arg was a raw `threaded_length` and `thread_length` was a separately computed
    standard value. Updated to the current code's Shigley Table 8-1 precise minor/pitch
    diameter constants (`d - 1.226869*pitch`, `d - 0.649519*pitch`) and `thread_length` being a
    direct constructor input (verified the new expected values by actually running the code).
  - `test_threaded_fastener.py` (5 errors, all `test_substrate_stiffness_*`): renamed to
    `member_stiffness` (both the assertions and the test method names).
  - `test_helical_compression_spring.py` `test_static_safety_factor_*` (2 errors): renamed to
    `test_static_analysis_*`, calling `static_analysis()` (values unchanged — confirmed by
    running the renamed method, same numbers as before).
  - `test_helical_compression_spring.py` `test_buckling`/`test_natural_frequency_*` (3
    failures): root cause identified precisely — `buckling()`/`natural_frequency()` use
    `sympy.sqrt` internally and return `sympy.Float`, and `unittest.assertAlmostEqual`'s
    `round(diff, places) == 0` check does not collapse a tiny (~1e-17) sympy `Float` residual to
    exactly 0 the way it does for a plain Python float (confirmed directly:
    `round(sympy.Float(-2.8e-17), 7) == 0` is `False`). Fixed by wrapping the actual value in
    `float(...)` before asserting. This is a concrete, reproduced instance of the general
    symbolic/numeric boundary hazard already logged under "Symbolic support" below.
  - All 45 tests pass now.

## Test coverage gaps

- [x] `fatigue` (`EnduranceLimit`, `FatigueAnalysis`, `FailureCriteria`) had no tests — added
  (67 tests).
- [x] `ExtensionSpring`, `HelicalTorsionSpring` had no tests — added (61 tests).
- [ ] Still untested: `BoltPattern`, and all of `gears` (`Gear`, `SpurGear`, `HelicalGear`,
  `Transmission`) — in progress.
- [ ] No CI workflow to run the existing tests on push/PR.

## Existing TODOs left in the code

- [ ] `spur_gear.py`: low-cycle `YN` solution missing for hardness not in the graph; no way to
  calculate `Qv` per AGMA 2001-D04.
- [ ] `transmission.py`: no strength-improvement advice, no minimum-volume optimization, no
  multi-stage gear-train support.
- [ ] `threaded_fastener.py`: pre-torque calculation not implemented.
- [ ] `tools/stress.py`: stress calculations marked as needing improvement.

## Symbolic support (sympy)

- [ ] Typecheck inputs so it's clear which functions/properties tolerate a `sympy.Symbol` in
  place of a number and which don't. Right now symbolic support is an accident of not
  type-checking anywhere — a `Symbol` rides through plain arithmetic fine, but silently breaks
  (`TypeError: cannot determine truth value of Relational`, or a `numpy` type error) the moment
  it hits `np.interp`, `table_interpolation`, or any `if x > threshold:` branch. Deciding and
  enforcing which paths are numeric-only vs. symbolic-safe would turn that into a clear error at
  the call site instead of a confusing one deep in `numpy`/`sympy`.
- [ ] Build an actual supported way to get a symbolic report out of a calculation (equation with
  values substituted in, for hand-calc documentation), instead of it only working ad hoc when a
  `Symbol` happens to be passed in and nothing symbolic-unsafe is hit along the way. See the
  `HelicalCompressionSpring`/`HelicalTorsionSpring` pattern that used to live in
  `examples/springs_examples/old/` (deleted in `c27aa2c`) and still lives in
  `examples/fatigue_examples/FatigueAnalysis_example.py` — solve for a design variable via
  `sympy.Eq`/`solveset` and `.subs()` it back in. Worth deciding whether this is a first-class
  API (e.g. an opt-in symbolic mode on the closed-form Shigley formulas: `fatigue`,
  `stress.py`, spring/bolt geometry) rather than something that only works by accident.

## Getter/setter validation

- [ ] The only four `@x.setter`s in the codebase (`Spring.wire_diameter`, `Spring.diameter`,
  `Spring.spring_rate` in `me_toolbox/springs/spring.py`, and `EnduranceLimit.A95` in
  `me_toolbox/fatigue/endurance_limit.py`) are pure passthroughs — `self._x = x`, no validation.
  Add real checks in each setter (e.g. reject negative/zero geometry values, whatever range each
  quantity is physically valid in) instead of removing the setters — keep the encapsulation,
  give it a job.

## Smaller code-quality items

- [ ] `tools/helpers.py:23` has a bare `except Exception: continue` inside `print_atributes`
  that silently swallows any attribute-access error — narrow it to `AttributeError`.
- [ ] Delete leftover commented-out code (`bolt_pattern.py`, `helical_torsion_spring.py`,
  `extension_spring.py`, `bolt.py`) now that git history preserves it.
- [ ] Mixed error-reporting style throughout (`print()` warnings vs. raised exceptions vs.
  returned `None`/`"Error"` sentinels) — makes failure modes inconsistent across the same class
  hierarchy.
