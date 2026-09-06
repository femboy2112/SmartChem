"""ELECTROCHEM-01 committed demonstration: sourced standard potentials reproduce the DOW electrochemistry.

A MEASURED claim lives in a committed harness, not a throwaway script.  The claims here, all against
KNOWN textbook answers (the instrument-calibration discipline -- recover the known cases before trusting
a novel reading):

  * The DOW displacement ``Cl2 + 2 Br- -> Br2 + 2 Cl-`` (ROUND-17 REDOX-DISPLACE-01, enumerable) is
    SPONTANEOUS at standard state: E deg_cell = E deg(Cl2/Cl-) - E deg(Br2/Br-) = 1.358 - 1.087 =
    +0.271 V, Delta-G deg = -n F E deg = -2 * 96485.332 * 0.271 = -52.3 kJ/mol.
  * The REVERSE (Br2 + 2 Cl- -> Cl2 + 2 Br-) is NON-spontaneous (-0.271 V) -- reproducing WHY chlorine
    displaces bromide but bromine does not displace chloride (the known-answer calibration).
  * Chlorine displaces iodide too (Cl vs I-: +0.822 V).
  * The Nernst slope is the textbook 59.16 mV per decade of Q at 25 C.
  * An unsourced couple returns UNKNOWN (None), never a fabricated potential (section 10.4).

The demonstration is deterministic, so its output is tamper-pinned by a frozen digest: re-run
``python -m experiments.electrochemistry_probe`` after an INTENTIONAL change and set ``FROZEN_HASH`` to
the printed value; an UNINTENTIONAL drift reddens ``report()['hash_matches']``.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.category import Molecule
from smartchem.electrochemistry import (
    FARADAY_C_PER_MOL,
    couple_potential,
    displacement_cell_potential,
    minimum_electrolysis_voltage,
    nernst_potential,
)
from smartchem.redox_displacement import (
    DISPLACEMENT_SCHEMA,
    HalfReactionCouple,
    combine_half_reactions,
    halogen_couple,
)

#: The committed tamper pin over the demonstration's canonical numbers/digests.  Regenerate ONLY on an
#: intentional change: ``python -m experiments.electrochemistry_probe`` and paste the printed value.
FROZEN_HASH = "b5db546c824003068f4aabe0e036cf958e6535dda6bbc086ca30f7ed66e59bae"


def dow_cell():
    """The DOW displacement's standard cell potential (Cl oxidant/cathode, Br reductant/anode)."""
    return displacement_cell_potential(reduction=halogen_couple("Cl"), oxidation=halogen_couple("Br"))


def reverse_cell():
    """The reverse pairing (Br2 tries to displace Cl-): must be NON-spontaneous."""
    return displacement_cell_potential(reduction=halogen_couple("Br"), oxidation=halogen_couple("Cl"))


def dow_electrons() -> int:
    """The electron count of the DOW displacement (LCM, from ROUND-17's combiner) -- n for Delta-G."""
    br2 = Molecule.diatomic("Br", "Br")
    return combine_half_reactions(reduction=halogen_couple("Cl"), oxidation=halogen_couple("Br"),
                                  target=br2).electrons_transferred


def unsourced_couple() -> HalfReactionCouple:
    """A well-formed couple absent from the sourced table (Zn2+/Zn) -> couple_potential must be None."""
    return HalfReactionCouple(DISPLACEMENT_SCHEMA, "Zn",
                              (Molecule.atom("Zn", charge=2),), (Molecule.atom("Zn", charge=0),), 2)


def _round(x: float, n: int = 6) -> float:
    return round(float(x), n)


def content_hash() -> str:
    dow, rev = dow_cell(), reverse_cell()
    n = dow_electrons()
    payload = {
        "dow_e_cell": _round(dow.e_cell_volts),
        "dow_verdict": dow.verdict.value,
        "dow_gibbs_kj": _round(dow.gibbs_j_per_mol(n) / 1000, 3),
        "dow_n": n,
        "reverse_e_cell": _round(rev.e_cell_volts),
        "reverse_verdict": rev.verdict.value,
        "cl_vs_i": _round(displacement_cell_potential(reduction=halogen_couple("Cl"),
                                                      oxidation=halogen_couple("I")).e_cell_volts),
        "nernst_1e_Q10": _round(nernst_potential(0.0, 1, 10.0)),
        "min_electrolysis_reverse": _round(minimum_electrolysis_voltage(rev)),
        "unsourced_is_none": couple_potential(unsourced_couple()) is None,
        "faraday": FARADAY_C_PER_MOL,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate() -> None:
    """Raise if the demonstration does not hold against the known textbook answers."""
    from smartchem.electrochemistry import SpontaneityVerdict
    from smartchem.cell import FARADAY_C_PER_MOL as CELL_F

    dow, rev = dow_cell(), reverse_cell()
    assert dow is not None and rev is not None, "the halogen couples must be sourced"
    assert abs(dow.e_cell_volts - 0.271) < 1e-9, f"DOW E_cell {dow.e_cell_volts} != +0.271 V"
    assert dow.verdict is SpontaneityVerdict.SPONTANEOUS, "the DOW displacement must be spontaneous"
    n = dow_electrons()
    assert n == 2, f"DOW n {n} != 2"
    dG_kj = dow.gibbs_j_per_mol(n) / 1000
    assert abs(dG_kj - (-52.3)) < 0.2, f"DOW Delta-G {dG_kj} != -52.3 kJ/mol"
    # the calibration: the reverse must be NON-spontaneous (bromine does not displace chloride).
    assert abs(rev.e_cell_volts - (-0.271)) < 1e-9, f"reverse E_cell {rev.e_cell_volts} != -0.271 V"
    assert rev.verdict is SpontaneityVerdict.NON_SPONTANEOUS, "the reverse must be non-spontaneous"
    # Nernst slope: 59.16 mV/decade at 25 C for a 1e process.
    assert abs(nernst_potential(0.0, 1, 10.0) - (-0.05916)) < 1e-4, "Nernst slope != 59.16 mV/decade"
    # electrolysis: the forced reverse needs |E|; a spontaneous cell needs 0.
    assert abs(minimum_electrolysis_voltage(rev) - 0.271) < 1e-9
    assert minimum_electrolysis_voltage(dow) == 0.0
    # fail-closed + no drift.
    assert couple_potential(unsourced_couple()) is None, "an unsourced couple must be UNKNOWN"
    assert FARADAY_C_PER_MOL == CELL_F, "Faraday constant drifted from smartchem.cell"


def report() -> dict:
    dow, rev = dow_cell(), reverse_cell()
    n = dow_electrons()
    return {
        "dow_e_cell_volts": _round(dow.e_cell_volts, 4),
        "dow_verdict": dow.verdict.value,
        "dow_gibbs_kj_per_mol": _round(dow.gibbs_j_per_mol(n) / 1000, 1),
        "reverse_e_cell_volts": _round(rev.e_cell_volts, 4),
        "reverse_verdict": rev.verdict.value,
        "nernst_1e_Q10_volts": _round(nernst_potential(0.0, 1, 10.0), 5),
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


if __name__ == "__main__":
    validate()
    r = report()
    for key, value in r.items():
        print(f"{key}: {value}")
    print(f"\ncontent_hash (set FROZEN_HASH to this to freeze): {content_hash()}")
