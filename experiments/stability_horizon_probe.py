"""DURATION-STABILITY-01 committed demonstration: duration-aware survival over sourced decomposition kinetics.

A MEASURED claim lives in a committed harness, not a throwaway script.  Every claim here is pinned against a
KNOWN answer (the instrument-calibration discipline -- recover the known case before trusting a novel reading):

  * INSTRUMENT CALIBRATION: for N2O5 (2 N2O5 -> 4 NO2 + O2, the classic first-order gas-phase decomposition,
    Ea = 103.5 kJ/mol, log10 A = 13.69), k = A·exp(-Ea/RT) at 298 K reproduces the measured 3.38e-5 s^-1 to
    ~5%, before any survival reading is believed.
  * The surviving fraction over a hold is first-order decay exp(-k t), reproduced to hand-computed value at
    several (T, t) points, and the duration-aware verdict spreads NON-vacuously: SURVIVES (298 K, 60 s) ->
    MARGINAL (298 K, 1 h) -> DEGRADES (298 K, 6 h), and faster at 338 K.
  * GRADE: inside the sourced 298-338 K fit window the reading is DERIVED; at 373 K it is a flagged PREDICTED
    extrapolation.
  * FAIL-CLOSED + anti-fabrication (section 10.4): a compound with no sourced first-order decomposition rate
    (water) is UNKNOWN, never a fabricated survival; a species that is the PRODUCT of a sourced record (NO2)
    gets no decomposition rate (direction matters); and the formula-collision pair cyclopropane/propene (both
    C3H6) proves the rate is keyed on STRUCTURE not formula -- cyclopropane (the reactant) reads, propene (the
    product isomer) does not borrow it.

Deterministic, so the demonstration is tamper-pinned by a frozen digest: re-run
``python -m experiments.stability_horizon_probe`` after an INTENTIONAL change and set ``FROZEN_HASH`` to the
printed value; an UNINTENTIONAL drift reddens ``report()['hash_matches']``.
"""
from __future__ import annotations

import hashlib
import json
import math

from smartchem.experiment.kinetics import GAS_CONSTANT_J_PER_MOL_K as ENGINE_R
from smartchem.experiment.stability_horizon import (
    GAS_CONSTANT_J_PER_MOL_K,
    SurvivalVerdict,
    decomposition_rate_for,
    stability_horizon,
    surviving_fraction,
)
from smartchem.smiles import parse_smiles

#: The committed tamper pin over the demonstration's numbers/verdicts.  Regenerate ONLY on an intentional
#: change: ``python -m experiments.stability_horizon_probe`` and paste the printed value.
FROZEN_HASH = "a64fb6465919c55cde8ec438137361af562ee6ca9138764aa17a2d83bb2cb9ab"

_N2O5 = "O=[N+]([O-])O[N+](=O)[O-]"
_POINTS = ((298.0, 60.0), (298.0, 3600.0), (298.0, 21600.0), (338.0, 60.0), (338.0, 600.0), (373.0, 60.0))


def _n2o5():
    return parse_smiles(_N2O5)


def _round(x: float, n: int = 6) -> float:
    return round(float(x), n)


def content_hash() -> str:
    mol = _n2o5()
    rows = {
        f"{int(T)}K_{int(t)}s": [stability_horizon(mol, T, t).verdict.value,
                                 _round(stability_horizon(mol, T, t).fraction_remaining, 4),
                                 stability_horizon(mol, T, t).grade]
        for T, t in _POINTS
    }
    payload = {
        "rows": rows,
        "water_verdict": stability_horizon(parse_smiles("O"), 298.0, 60.0).verdict.value,
        "propene_verdict": stability_horizon(parse_smiles("CC=C"), 298.0, 60.0).verdict.value,
        "r_matches_engine": GAS_CONSTANT_J_PER_MOL_K == ENGINE_R,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate() -> None:
    """Raise if the demonstration does not hold against the known answers."""
    mol = _n2o5()
    rec = decomposition_rate_for(mol)
    assert rec is not None and rec.name == "N2O5 decomposition", "N2O5 must resolve a sourced first-order rate"
    assert GAS_CONSTANT_J_PER_MOL_K == ENGINE_R, "R drifted from the L1 rate engine"

    # instrument calibration: k(298 K) reproduces the measured 3.38e-5 s^-1 to ~7%.
    log10_k = rec.log10_a - (rec.ea_kj_per_mol * 1000.0) / (GAS_CONSTANT_J_PER_MOL_K * 298.0 * math.log(10.0))
    k298 = 10.0 ** log10_k
    assert abs(k298 - 3.38e-5) / 3.38e-5 < 0.10, f"k(298) {k298} not within 10% of measured 3.38e-5"

    # surviving fraction matches hand-computed exp(-k t) at every point, and the verdict spreads non-vacuously.
    seen: set[str] = set()
    for T, t in _POINTS:
        h = stability_horizon(mol, T, t)
        lk = rec.log10_a - (rec.ea_kj_per_mol * 1000.0) / (GAS_CONSTANT_J_PER_MOL_K * T * math.log(10.0))
        hand = math.exp(-(10.0 ** lk) * t)
        assert abs(h.fraction_remaining - hand) < 1e-9, f"survival {h.fraction_remaining} != hand {hand} at {T},{t}"
        assert h.fraction_remaining == surviving_fraction(rec, T, t)
        seen.add(h.verdict.value)
    assert {"SURVIVES", "MARGINAL", "DEGRADES"} <= seen, f"verdict must spread non-vacuously, got {seen}"

    # grade: DERIVED inside 298-338 K, PREDICTED at 373 K (extrapolated, flagged).
    assert stability_horizon(mol, 298.0, 60.0).grade == "DERIVED"
    assert stability_horizon(mol, 373.0, 60.0).grade == "PREDICTED"

    # fail-closed + anti-fabrication.
    assert stability_horizon(parse_smiles("O"), 298.0, 60.0).verdict is SurvivalVerdict.UNKNOWN, "water is UNKNOWN"
    assert stability_horizon(parse_smiles("O"), 298.0, 60.0).fraction_remaining is None
    # direction: NO2 is a PRODUCT of the N2O5 record, so it has no decomposition rate.
    assert decomposition_rate_for(parse_smiles("[N+](=O)[O-]")) is None, "a product species must not read a rate"
    # formula collision: cyclopropane and propene are both C3H6; only cyclopropane (the reactant) reads.
    assert decomposition_rate_for(parse_smiles("C1CC1")) is not None, "cyclopropane must read its sourced rate"
    assert decomposition_rate_for(parse_smiles("CC=C")) is None, "propene (same formula C3H6) must NOT borrow it"


def report() -> dict:
    mol = _n2o5()
    return {
        "n2o5_298K_60s": stability_horizon(mol, 298.0, 60.0).verdict.value,
        "n2o5_298K_6h": stability_horizon(mol, 298.0, 21600.0).verdict.value,
        "n2o5_338K_10min": stability_horizon(mol, 338.0, 600.0).verdict.value,
        "water": stability_horizon(parse_smiles("O"), 298.0, 60.0).verdict.value,
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


if __name__ == "__main__":
    validate()
    for key, value in report().items():
        print(f"{key}: {value}")
    print(f"\ncontent_hash (set FROZEN_HASH to this to freeze): {content_hash()}")
