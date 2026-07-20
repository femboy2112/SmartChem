"""
The legacy heuristic, wrapped as an oracle so it can be measured rather than trusted.

This is the model Antigravity shipped: an algebraic expression over Mulliken
electronegativity and chemical hardness with several constants fitted by hand. It is
preserved here unchanged, and deliberately so -- it is the baseline every later oracle
has to beat, and the number it scores is the honest starting point for the README.

Known structural limits, measured not guessed (see tests/test_findings.py):

* Refuses CO, NO and HCl outright.
* Overshoots ionic bonds by roughly 3x (NaCl: 12.1 eV predicted vs 4.23 eV experimental).
* Cannot describe homonuclear bonding through its charge-transfer term, which is
  identically zero when the two atoms are the same element. The homonuclear path is a
  separate hand-fitted branch whose scaling constant was tuned on exactly two data
  points (H2 and F2) -- see the comment at engine.py:94.

It is kept because a baseline you can measure is worth more than a baseline you deleted.
"""
from __future__ import annotations

import io
import contextlib
import time

from .base import BaseOracle, Estimate
from ..atoms import PT, Species
from ..comonad import Env, Situated


class HeuristicOracle(BaseOracle):
    name = "heuristic (legacy)"
    #: Measured over the full reference set, not asserted. See python -m smartchem.bench.
    nominal_accuracy_ev = 3.28

    def __init__(self, env: Env | None = None):
        self.env = env or Env.standard()

    def estimate(self, symbols: tuple[str, ...]) -> Estimate | None:
        from ..engine import propose_bond

        counts: dict = {}
        for s in symbols:
            if s not in PT:
                return None          # element not covered; decline rather than invent
            atom = PT[s]
            counts[atom] = counts.get(atom, 0) + 1
        species = Species.from_dict(counts)

        t0 = time.perf_counter()
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                reaction = propose_bond(Situated(species, self.env))
        except (ZeroDivisionError, IndexError, ValueError):
            # The legacy engine has a real crash surface on degenerate inputs.
            # Declining is correct; pretending is not.
            return None
        dt = time.perf_counter() - t0

        _, effect = reaction.outcomes[0]
        if effect.delta_h_ev == 0.0 and effect.delta_s_ev_k == 0.0:
            return None              # the engine refused to bond these atoms

        meta = reaction.metadata or {}
        return Estimate(
            value_ev=-effect.delta_h_ev,
            uncertainty_ev=self.nominal_accuracy_ev,
            method=f"legacy heuristic ({meta.get('mechanism', 'unknown')}, "
                   f"n={meta.get('transfer_n', '?')})",
            seconds=dt,
            notes="hand-fitted constants; see engine.py:94",
        )
