"""ΔfH°(molecule, 0 K) DERIVED from a COMPUTED atomization energy -- the algebraic inverse of a map the
tree already runs forward.

``reference.atomization_energy_ev`` computes, from stored formation enthalpies,

    D0(molecule) = Σ n_i · ΔfH°(atom_i, 0K) − ΔfH°(molecule, 0K)

This module runs it BACKWARDS, feeding D0 from ``oracle.atomization_energy(molecule)`` (a value the oracle
*computes*, not a stored one) to DERIVE the formation enthalpy:

    ΔfH°(molecule, 0K) = Σ n_i · ΔfH°(atom_i, 0K) − D0(molecule)

That is reproducing known chemistry (the oracle already computes the atomization energy under its
calibrate/state-envelope/refuse discipline; the atomic anchor is sourced), not inventing new physics -- and
it is the second half of the derivation layer's thermodynamics (S° is :mod:`smartchem.thermo_entropy`).

BOUNDS, stated loudly -- outside them the answer is a loud ``None``, NEVER a fabricated number:
* CHNO only.  The sourced atomic anchor ``reference.ATOM_FORMATION_KJ`` exists for H, C, N, O only.
* Neutral only.  ``oracle.atomization_energy`` declines charged species.
* Only where the oracle returns a value.  The bundled public PySCF oracle declines by returning ``None``
  (its polyatomic accuracy gate is unopened, so in production the live reach is the tabulated CHNO
  diatomics), and a ``None`` propagates as ``None`` here; a non-finite (NaN/inf) energy is likewise
  refused.  Fail-closed here means exactly the oracle's documented ``None`` decline -- an oracle that
  *raises* instead is out of that contract and its exception propagates.
* PRECONDITION (unverifiable, so stated not checked): the oracle's atomization energy must be a D_0
  (zero-point-INCLUDED, as the bundled PySCF oracle deliberately reports), NOT a D_e (electronic-only).
  Feed a D_e oracle and the result is wrong by the molecular ZPE (tens of kJ/mol) while still labelled a
  0 K value -- the module cannot detect the convention, so a caller substituting a different oracle owns it.

WHAT THIS IS: a 0 K formation enthalpy.  The oracle's energy folds in the molecular ZPE, so its atomization
energy is an (approximate) D_0 on the same 0 K convention as ``reference.POLYATOMIC_REFS`` -- so the derived
ΔfH° is a 0 K value.  It must NOT be mixed into the 298.15 K ``ThermoTable`` without an explicit 0K->298K
enthalpy correction (a separate, unbuilt rung -- see the roadmap).
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Mapping

from ..category import Molecule
from ..data.reference import ATOM_FORMATION_KJ, KJ_PER_EV

__all__ = ["DerivedFormation", "formation_enthalpy_0k"]


@dataclass(frozen=True)
class DerivedFormation:
    """A DERIVED 0 K standard formation enthalpy, with its grade, band, and method (mirrors
    :class:`~smartchem.thermo_entropy.StandardMolarEntropy`)."""

    value_kj_per_mol: float           # ΔfH°(molecule, 0 K)
    grade: str                        # "DERIVED"
    uncertainty_kj_per_mol: float     # propagated from the oracle's D0 error (a LOWER bound; see notes)
    d0_ev: float                      # the computed atomization energy used
    method: str
    notes: tuple[str, ...] = field(default_factory=tuple)

    def render(self) -> str:
        return (
            f"ΔfH°(0K) = {self.value_kj_per_mol:.1f} +/- >={self.uncertainty_kj_per_mol:.1f} kJ/mol "
            f"[{self.grade}] (band is the oracle D0 error ONLY, a LOWER bound -- the sourced atomic-anchor "
            f"systematic adds; D0 = {self.d0_ev:.3f} eV; {self.method})"
        )


def formation_enthalpy_0k(
    molecule: Molecule, oracle, *, atomic_dfh: Mapping[str, float] = ATOM_FORMATION_KJ
) -> DerivedFormation | None:
    """DERIVE ΔfH°(molecule, 0 K) from the oracle's computed atomization energy, or ``None`` (a loud gap).

    Returns ``None`` -- never a fabricated number -- when the molecule is charged, has an element outside the
    sourced CHNO anchor, or the oracle declines to compute its atomization energy (fail-closed).
    """
    if type(molecule) is not Molecule:
        raise TypeError("molecule must be a Molecule")
    if getattr(molecule, "charge", 0) != 0:
        return None
    atoms = Counter(molecule.atoms)
    if not atoms:
        return None
    missing = sorted({s for s in atoms if s not in atomic_dfh})
    if missing:
        return None  # outside the sourced atomic anchor -> loud gap, never fabricated

    est = oracle.atomization_energy(molecule)
    if est is None:
        return None  # the oracle declined (returned None) -> honest UNKNOWN

    d0_ev = est.value_ev
    if not math.isfinite(d0_ev):
        return None  # a NaN/inf atomization energy is not a number -> loud gap, never a NaN dressed as DERIVED
    atoms_kj = sum(n * atomic_dfh[s] for s, n in atoms.items())
    dfh_kj = atoms_kj - d0_ev * KJ_PER_EV  # the inverse; the sign is load-bearing (dfH = atoms - D0)

    # Band from the oracle's own D0 error.  A LOWER bound: unlike the atomization direction (where the
    # per-element offsets cancel, same atoms on both sides), here the atomic anchor ΔfH does NOT cancel, so
    # its common-mode systematic ADDS -- named, not hidden, and not fabricated into a number we don't have.
    band_kj = max(est.uncertainty_ev, abs(est.systematic_ev)) * KJ_PER_EV
    notes = (
        "0 K value (the oracle's energy folds in ZPE -> approximate D_0); do NOT mix into the 298.15 K "
        "thermo table without an explicit 0K->298K enthalpy correction",
        "band is the oracle's D0 error only; the sourced atomic-anchor ΔfH common-mode systematic does "
        "NOT cancel here and ADDS an un-quantified amount on top (CCCBDB R22 anchor)",
    )
    method = (
        f"ΔfH°(0K) = Σ n·ΔfH°(atom,0K) − D0 (inverse of reference.atomization_energy_ev); "
        f"D0 from {getattr(oracle, 'name', type(oracle).__name__)}.atomization_energy under its "
        f"calibrate/refuse gate; atomic anchor CCCBDB R22 (H/C/N/O)"
    )
    return DerivedFormation(dfh_kj, "DERIVED", band_kj, d0_ev, method, notes)
