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
  points (H2 and F2) -- see the comment at legacy.py:275.

It is kept because a baseline you can measure is worth more than a baseline you deleted.
"""
from __future__ import annotations

import io
import contextlib
import time

from .base import BaseOracle, Estimate, carries_unmodelled_physics
from ..atoms import PT, Species
from ..category import Molecule
from ..legacy import Env, Situated


class HeuristicOracle(BaseOracle):
    name = "heuristic (legacy)"
    #: Measured over the full reference set, not asserted. See python -m smartchem.bench.
    nominal_accuracy_ev = 3.28

    def __init__(self, env: Env | None = None):
        self.env = env or Env.standard()

    def energy(self, molecule: Molecule) -> Estimate | None:
        """
        Total energy of a species on the free-atom zero: ``E = -sum(bond energies)``.

        This oracle is bond-additive, and that is now a statement about *this
        implementation* rather than about the framework. The interface asks for the energy
        of a species; a bond-additive model answers by summing over edges, and a
        correlated method answers by solving the electronic structure. Both satisfy the
        same contract, and the difference between them becomes visible in the numbers
        rather than baked into the architecture.

        The zero here is free atoms (E(atom) = 0), not PySCF's total electronic energy.
        Different zero, same contract -- it is consistent across every species this
        instance prices, so it cancels in any conserving difference.
        """
        if molecule.charge != 0:
            return None
        if carries_unmodelled_physics(molecule):
            return None      # excitations and radiated quanta: see base.py for why
        if not molecule.bonds:
            # A free atom. Zero by definition of this oracle's reference, exactly -- not
            # an unknown, so it must not decline.
            #
            # "By definition" covers elements this oracle knows. It does NOT cover a
            # symbol that is not an element at all: there the zero is not a convention
            # being applied, it is a confident number about something that does not
            # exist. Symbols here are opaque by design (see category.py), so nothing
            # upstream rules that out and the check has to live here.
            if any(s not in PT for s in molecule.atoms):
                return None
            return Estimate(0.0, 0.0, self.name, 0.0, f"free atom {molecule.atoms[0]}"
                            if len(molecule.atoms) == 1 else "unbonded atoms")

        total = Estimate.zero(self.name)
        for bond in sorted(molecule.bonds):
            pair = (molecule.atoms[bond.i], molecule.atoms[bond.j])
            est = self._pair_energy(pair)
            if est is None:
                return None      # partial pricing is refused; see the module docstring
            total = total + est
        return -total            # bonding releases energy: bound species sit below zero

    def _pair_energy(self, symbols: tuple[str, ...]) -> Estimate | None:
        """Dissociation energy of one atom pair, via the frozen legacy engine."""
        from ..legacy import propose_bond

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
            notes="hand-fitted constants; see legacy.py:275",
        )
