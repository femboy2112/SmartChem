# Vendored PHREEQC databases (solid-equilibrium harness, OPERATION XXIII S4)

The constants `run_solid_equilibrium_xxiii.py` uses are read from these files, and it refuses to read them unless each
one's sha256 matches the pin in `DB_SHA256`. The files are copied **verbatim** from the package data of
`phreeqpython` 1.6.2 (`phreeqpython/database/`). Those are the exact bytes that produced the committed
`result_solid_equilibrium_xxiii.json`.

| file | sha256 | bytes | line endings | used for |
|---|---|---|---|---|
| `phreeqc.dat` | `6bb5ebc1d0ecca0e921c13a2241d05d3a3333b142d1d740b2ed03a786442bdf5` | 46008 | LF (6 Latin-1 bytes) | carbonate, water and Ca ion-pair logK; PHREEQC calcite reference |
| `wateq4f_PWN.dat` | `1c4de8335cd87b4227ffe562a838c485669801273a8e43d4724b834d51aa61f4` | 107557 | CRLF | nahcolite logK (hostile holdout) |

`minteq.v4.dat` (calcite logKsp) is the separately vendored copy in `../../carbonate_na_pair_s6/db/`, pinned the same way.

**Why vendored.** Until this fix the harness read both files out of whatever `phreeqpython` was installed under
`sys.prefix`. Hosted CI has no `phreeqpython`, so 27 tests failed with `FileNotFoundError` (PR #161) while a dev venv
passed. Worse, the "frozen" constants were never pinned to a version. Vendoring plus pinning makes the tests hermetic.
The tests do not need `phreeqpython`. Only re-running the PHREEQC reference (`phreeqc_reference()`) needs it, and that
reads this same pinned `phreeqc.dat`.

**Licence.** `phreeqpython` is distributed under the Apache License 2.0. Its licence text is reproduced unmodified in
`LICENCE.phreeqpython`, and the database files themselves are unmodified. The databases originate with the USGS
PHREEQC distribution. `wateq4f_PWN.dat` is the WATEQ4F database as shipped by `phreeqpython`; its header carries the
upstream `$Id: wateq4f.dat …` line. `.gitattributes` marks `*.dat` as `-text`, so git never EOL-converts the pinned
bytes. This directory sits under `experiments/`, which is pruned from the wheel and sdist, so it ships only in the
source repository.
