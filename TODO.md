# TODO

Things to improve or fix, found while reviewing the codebase.

## Bugs

- [x] Table-file paths built with hardcoded backslashes (`gear.py`, `helical_gear.py`,
  `spring.py` — `os.path.dirname(__file__) + "\\tables\\..."`) — confirmed by actually running
  `examples/gears_examples/Gears_examples.py` on Linux: crashed with `FileNotFoundError` on
  `me_toolbox/gears\tables\...`. Switched all four call sites to `os.path.join`.
- [ ] **Critical — `BoltPattern`'s fatigue calculation is completely broken.**
  `me_toolbox/fasteners/bolt_pattern.py:301` (`variable_equivalent_stresses`, called from
  `fatigue_safety_factor`) constructs `FatigueAnalysis` with a signature that no longer matches
  `FatigueAnalysis.__init__` at all:
  - passes `endurance_limit=endurance_limit[i]` (an `EnduranceLimit` *object*) where the
    constructor now expects `modified_endurance_limit` as a **float** (the `Se` value — see
    how `Bolt.endurance_limit()`/the fatigue examples use `.modified`)
  - never passes `stress_type` or `ultimate_tensile_strength`, both required with no default
  - passes `Sy=` where the parameter is actually named `yield_strength`
  Confirmed by executing `examples/fasteners_examples/BoltPattern_example.ipynb`, which hits
  `TypeError: FatigueAnalysis.__init__() missing 2 required positional arguments` at this call.
  This means any user calling `BoltPattern.fatigue_safety_factor`/`variable_equivalent_stresses`
  today gets a crash, not a wrong number — but it means that feature has been non-functional
  since `FatigueAnalysis`'s constructor was last changed. Needs a real fix (get `ultimate_tensile_strength`
  from `fastener.bolt.tensile_strength`, decide the right `stress_type` — likely `'multiple'`
  since both normal and torsion stresses are involved), not a guess.
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
- [ ] `requirements.txt`'s pinned `numpy==1.20.1` **fails to build at all on Python 3.11**
  (confirmed: no wheel available, source build errors out) — this isn't just staleness risk,
  it currently blocks installing the project from `requirements.txt` on any recent Python.
  `sympy==1.7.1` is from the same ~2021 vintage. `setup.py`'s `install_requires` has no version
  constraints at all, so the two files disagree on strictness as well as currency — reconcile
  and update the pins (validated running against `numpy 2.4.6`/`sympy 1.14.0` instead, see test
  findings below for what that version jump exposed).
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
- [ ] **The existing test suite is stale against the current API — 14 of 45 tests fail/error.**
  Ran `python -m unittest discover`. Breakdown:
  - `test_bolt.py` (4 failures): tests the *old* approximate geometry formulas
    (`diameter - (5/8)*height` etc.) and an *old* constructor semantics where the 4th
    positional arg was a raw `threaded_length` and `thread_length` was a separately computed
    standard value. The current code instead uses Shigley Table 8-1's precise minor/pitch
    diameter constants (`d - 1.226869*pitch`, `d - 0.649519*pitch`) and takes `thread_length`
    directly as a constructor input. **This looks like the code was correctly upgraded to more
    precise formulas and the test file was simply never updated** — but since I can't verify
    Shigley's exact published constants independently, this needs your confirmation before
    rewriting the test's expected values.
  - `test_threaded_fastener.py` (5 errors, all `test_substrate_stiffness_*`): calls
    `self.fastener.substrate_stiffness`, which doesn't exist — the current attribute is
    `member_stiffness`. Stale rename, needs the test updated.
  - `test_helical_compression_spring.py` `test_static_safety_factor_*` (2 errors): calls
    `spring.static_safety_factor()`, renamed to `static_analysis` in commit `064ecbb`. Stale
    rename, needs the test updated.
  - `test_helical_compression_spring.py` `test_buckling`/`test_natural_frequency_*` (3
    failures): differences are all at the 1e-14 to 1e-17 level — floating-point noise, not a
    real discrepancy. Likely exposed by running against much newer `numpy`/`sympy` than the
    (uninstallable) pinned versions; worth re-checking once the dependency pins above are fixed,
    but not a priority.
  - Net effect: **test coverage gaps (below) undersell the problem** — it's not just "untested
    classes," the tests that do exist don't reliably tell you if you broke something, since a
    meaningful fraction already fail for reasons unrelated to correctness.

## Test coverage gaps

- [ ] Only `Bolt`, `ThreadedFastener`, `HelicalCompressionSpring` have tests. Untested:
  `BoltPattern`, all of `fatigue` (`EnduranceLimit`, `FatigueAnalysis`, `FailureCriteria`), all
  of `gears` (`Gear`, `SpurGear`, `HelicalGear`, `Transmission`), and two of three spring types
  (`ExtensionSpring`, `HelicalTorsionSpring`).
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
