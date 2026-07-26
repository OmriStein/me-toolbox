# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

`me_toolbox` is a Python library implementing mechanical engineering design calculations
(fatigue, gears, springs, fasteners) drawn from two different sources depending on domain:
`fasteners`, `fatigue`, and `springs` follow *Shigley's Mechanical Engineering Design*; `gears`
follows the AGMA standard (AGMA 2001-D04). Variable names intentionally mirror the source's
notation (`Sut`, `Sy`, `Se`, `Kf`, `Kv`, `Yj`, etc.) rather than being expanded into descriptive
names — check the docstring or the referenced standard before renaming anything.

## Setup and commands

Install dependencies before doing anything else — none of the packages import cleanly otherwise:

```bash
pip install -r requirements.txt
pip install icecream  # used by me_toolbox/fatigue/fatigue_analysis.py but missing from requirements.txt/setup.py
```

There is no lint config, CI workflow, or build tooling beyond `setuptools` (see `setup.py`,
`pyproject.toml`). Packaging the CSV data tables relies on `MANIFEST.in`.

### Tests

Tests use `unittest` and live next to the code they test (not in a separate `tests/` directory),
named `test_*.py`. Coverage is sparse — only `Bolt`, `ThreadedFastener`, and
`HelicalCompressionSpring` currently have tests.

```bash
# run everything
python -m unittest discover

# run one module's tests
python -m unittest me_toolbox.fasteners.test_bolt

# run a single test case/method
python -m unittest me_toolbox.fasteners.test_bolt.TestBolt.test_stress_area
```

## Architecture

The library is split into four independent engineering domain packages, plus a shared `tools`
package:

- `me_toolbox/fasteners` — `Bolt`, `ThreadedFastener`, `BoltPattern`
- `me_toolbox/fatigue` — `EnduranceLimit`, `FatigueAnalysis`, `FailureCriteria`
- `me_toolbox/gears` — `Gear` (base), `SpurGear`, `HelicalGear`, `Transmission`
- `me_toolbox/springs` — `Spring` (ABC base), `HelicalCompressionSpring`, `ExtensionSpring`,
  `HelicalTorsionSpring`
- `me_toolbox/tools` — shared helpers used across all domains: `table_interpolation` (2D
  interpolation over a numpy table, raises `NotInRangeError`), `parse_input`/`print_atributes`
  (kwargs-driven attribute assignment for constructors), and unit-conversion functions in
  `helpers.py`

Each domain package's `__init__.py` flat-re-exports its public classes, so consumers do
`from me_toolbox.springs import HelicalCompressionSpring` rather than importing submodules
directly — follow this pattern when adding a new class to a package.

Domains generally follow a class-hierarchy-with-properties style: a base class (`Gear`, `Spring`)
holds shared geometry/material properties and standard-derived factors as `@property` methods;
subclasses (`SpurGear`/`HelicalGear`, `HelicalCompressionSpring`/`ExtensionSpring`/
`HelicalTorsionSpring`) add type-specific geometry and override `static_analysis`/
`fatigue_analysis`. `FatigueAnalysis` and `FailureCriteria` are then applied on top using the
stresses/strengths computed by the geometry classes.

`fasteners` and `springs` both reuse the shared `fatigue` package (`Bolt`/`BoltPattern` and all
three spring classes call into `FatigueAnalysis`/`EnduranceLimit`/`FailureCriteria`) — this is
Shigley's fatigue theory applied consistently across those two domains. `gears` deliberately does
not go through `fatigue`: `Gear` computes its own AGMA cycle-life factors (`YN`, `ZN`) directly as
properties, since AGMA's life-factor approach is a separate model from Shigley's and reuse was
never evaluated. Don't "fix" this by wiring `Gear` into `FatigueAnalysis` without checking the
AGMA formulas actually match.

### Examples

Usage isn't documented in docstrings beyond parameter descriptions — `examples/<domain>_examples/`
is where worked usage lives, one subfolder per domain (`fasteners_examples`, `fatigue_examples`,
`gears_examples`, `springs_examples`). `fasteners` and `springs` examples are Jupyter notebooks
(`.ipynb`) walking through a full calculation with textbook figures/tables reproduced as images
in an `img/` subfolder; `fatigue` and `gears` examples are plain `.py` scripts. When adding a new
class or changing a constructor's signature, check whether an example uses it and update the
example alongside the code — these notebooks are the de facto usage reference, not just demos.

### Standard data tables

`gears/tables/*.csv` and `springs/tables/*.csv` hold digitized values from AGMA/Shigley reference
tables (geometry factors, tensile strength coefficients), loaded via `table_interpolation` or
`numpy.genfromtxt`/`csv.DictReader`. The paths to these files are built with hardcoded backslashes
(e.g. `os.path.dirname(__file__) + "\\tables\\..."` in `gear.py`, `helical_gear.py`,
`spring.py`), which only works on Windows — fix to `os.path.join` if you touch this code and need
it to run cross-platform.
