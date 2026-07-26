# TODO

Things to improve or fix, found while reviewing the codebase.

## Bugs

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
- [ ] `requirements.txt` pins ancient exact versions (`numpy==1.20.1`, `sympy==1.7.1`, both
  ~2021), while `setup.py`'s `install_requires` has no version constraints at all — reconcile
  the two and update the pins.
- [ ] Table-file paths built with hardcoded backslashes (`gear.py`, `helical_gear.py`,
  `spring.py` — `os.path.dirname(__file__) + "\\tables\\..."`) — Windows-only, breaks on
  Linux/Mac. Switch to `os.path.join`.

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

## Smaller code-quality items

- [ ] `tools/helpers.py:23` has a bare `except Exception: continue` inside `print_atributes`
  that silently swallows any attribute-access error — narrow it to `AttributeError`.
- [ ] Delete leftover commented-out code (`bolt_pattern.py`, `helical_torsion_spring.py`,
  `extension_spring.py`, `bolt.py`) now that git history preserves it.
- [ ] Mixed error-reporting style throughout (`print()` warnings vs. raised exceptions vs.
  returned `None`/`"Error"` sentinels) — makes failure modes inconsistent across the same class
  hierarchy.
