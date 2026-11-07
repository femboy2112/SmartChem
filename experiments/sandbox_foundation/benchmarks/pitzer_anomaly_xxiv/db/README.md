# Vendored `pitzer.dat` (OPERATION XXIV-III-B)

`pitzer.dat` is copied verbatim from the package data of `phreeqpython` 1.6.2 (`phreeqpython/database/pitzer.dat`).
Those are the exact bytes behind XXIII's recorded C2 = -0.07406745913108281.

- sha256: `eb5051704fad461c4e5325721afc7b9025fad7c2906f72ed48ae182aa2c1a5c9`
- size: 31939 bytes, with Latin-1 bytes present
- `-text` in `.gitattributes`, so git never converts the line endings of the pinned bytes

The harness refuses to read the file if its sha256 drifts. It never edits the file: every ablation is written to a
temporary copy. The database originates with the USGS PHREEQC distribution and is shipped by `phreeqpython` under
the Apache License 2.0, whose text is reproduced unmodified in `LICENCE.phreeqpython`. This directory sits under
`experiments/`, which is pruned from the wheel and sdist.
