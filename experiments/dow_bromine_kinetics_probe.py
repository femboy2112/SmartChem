"""DOW-BROMINE-KINETICS-01 committed demonstration: the KINETIC half of the DOW-bromine litmus.

A MEASURED claim lives in a committed harness that ASSERTS, not a throwaway that prints.  This pins the
answer to "predict Br2's decomposition (kinetics)" against known answers and against the anti-fabrication
discipline of :mod:`smartchem.experiment.collider_kinetics`:

  * TRANSCRIPTION SELF-CONSISTENCY (NOT independent validation): the modified-Arrhenius fit reproduces
    Warshay's representative Table I point kD(1825 K, Ar) ~= 1.574e6 L mol^-1 s^-1 (observed 1.48e6, +6.3%).
    This REUSES the fitted dataset -- it is a transcription check, unlike N2O5's ~7% instrument check which
    is against an independently measured k.
  * BENCH VERDICT (the litmus answer): at 298 K, [M] = 1 atm ideal-gas, Br2's collisional dissociation
    channel SURVIVES (a flagged PREDICTED extrapolation ~900 K below the sourced window), because the forward
    fraction is a rigorous LOWER bound on the true fraction and the extrapolation is conservative in the
    survival direction.  Cross-referenced to the INDEPENDENT ROUND-26 thermodynamic bearing computed here
    from the sourced CODATA table (Br2 -> 2 Br*, ΔG298 = +161.65 kJ/mol): both agree Br2 is stable.
  * FAIL-CLOSED, the whole point: an in-window LONG hold DEFERS to UNKNOWN (Warshay's fit omits the reverse
    recombination, so a DEGRADES would be a fabricated refutation the reverse overturns); an out-of-window
    sub-survives DEFERS to UNKNOWN (a refutation from an extrapolated rate is fabrication).  Across a wide
    (T, t) sweep the model emits ONLY SURVIVES or UNKNOWN -- never DEGRADES or MARGINAL.
  * The reverse-free RATE carries the fast-at-shock-T fact: t1/2(1825 K, 1 atm) ~ 66 us.
  * [M] is never defaulted; a non-finite/non-positive collider concentration RAISES.

Deterministic, so the demonstration is tamper-pinned by a frozen digest: re-run
``python -m experiments.dow_bromine_kinetics_probe`` after an INTENTIONAL change and set ``FROZEN_HASH`` to
the printed value; an UNINTENTIONAL drift reddens ``report()['hash_matches']``.
"""
from __future__ import annotations

import hashlib
import json
import math

from smartchem.data.thermo import DEFAULT_THERMO
from smartchem.experiment.collider_kinetics import (
    SEED_COLLIDER_REFS,
    SurvivalVerdict,
    collider_dissociation_for,
    collider_survival,
    dissociation_rate,
    pseudo_first_order_k,
)
from smartchem.smiles import parse_smiles

#: The committed tamper pin.  Regenerate ONLY on an intentional change:
#: ``python -m experiments.dow_bromine_kinetics_probe`` and paste the printed value.
FROZEN_HASH = "c1f90cf0311bbd1aa6e9404986c318bfb3dc0234a689fe179146e29a562500a4"

_REF = SEED_COLLIDER_REFS[0]                                 # Br2 dissociation, Ar collider (the only seed)
_R = 8.314462618                                             # J/(mol K), for the ideal-gas collider density


def _collider_mol_per_l(temperature_k: float, atm: float = 1.0) -> float:
    """Ideal-gas number density of the collider at ``atm`` and ``temperature_k``, in mol/L (a DECLARED [M])."""
    return atm * 101325.0 / (_R * temperature_k) / 1000.0


def _round(x: float, n: int = 6) -> float:
    return round(float(x), n)


def _delta_g_dissociation_298() -> float:
    """ΔG298 for Br2 -> 2 Br*, from the SOURCED CODATA thermo table (the INDEPENDENT bearing, computed by a
    different code path from a different source family than the Warshay kinetic fit)."""
    # item 5 (phase-carrying key): Br₂ is now tabulated in BOTH gas and liquid, so a bare ``for_formula("Br2")``
    # is phase-ambiguous and fails closed to None.  This gas-phase dissociation Br₂(g) → 2 Br(g) asks for the GAS
    # records explicitly; the returned values (30.91 / 245.468, 111.87 / 175.018) are unchanged, so ΔG₂₉₈ stays
    # +161.65 and content_hash() is byte-identical to the pre-item-5 FROZEN_HASH.
    br = DEFAULT_THERMO.for_formula("Br", phase="gas")
    br2 = DEFAULT_THERMO.for_formula("Br2", phase="gas")
    dh = 2 * br.dhf_kj_per_mol - br2.dhf_kj_per_mol            # kJ/mol
    ds = 2 * br.s_j_per_mol_k - br2.s_j_per_mol_k              # J/(mol K)
    return dh - 298.15 * ds / 1000.0


def content_hash() -> str:
    br2 = parse_smiles("BrBr")
    bench = collider_survival(_REF, 298.15, 86400.0, _collider_mol_per_l(298.15))
    in_window_long = collider_survival(_REF, 1200.0, 10.0, _collider_mol_per_l(1200.0))
    out_of_window = collider_survival(_REF, 2500.0, 1e-4, _collider_mol_per_l(2500.0))
    payload = {
        "kD_1825_Ar": _round(dissociation_rate(_REF, 1825.0), 1),
        "kD_298_Ar": _round(dissociation_rate(_REF, 298.15), 20),
        "bench_298": [bench.verdict.value, bench.grade, _round(bench.forward_fraction, 9)],
        "in_window_long_1200": [in_window_long.verdict.value, in_window_long.grade],
        "out_of_window_2500": [out_of_window.verdict.value, out_of_window.grade],
        "half_life_1825_1atm_s": _round(math.log(2.0) / pseudo_first_order_k(_REF, 1825.0,
                                                                            _collider_mol_per_l(1825.0)), 9),
        "delta_g_dissoc_298": _round(_delta_g_dissociation_298(), 2),
        "br2_ar_found": collider_dissociation_for(br2, collider="Ar") is not None,
        "br2_ne_unseeded": collider_dissociation_for(br2, collider="Ne") is None,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate() -> None:
    """Raise if the demonstration does not hold against the known answers and the anti-fabrication guards."""
    br2 = parse_smiles("BrBr")

    # 1. TRANSCRIPTION self-consistency: reproduce Warshay's Table I point (reuses the fit, NOT independent).
    kd = dissociation_rate(_REF, 1825.0)
    assert abs(kd - 1.48e6) / 1.48e6 < 0.10, f"kD(1825 K, Ar) {kd:.4e} not within 10% of observed 1.48e6"

    # 2. BENCH verdict (the litmus answer): Br2's collisional channel SURVIVES at 298 K, flagged PREDICTED.
    bench = collider_survival(_REF, 298.15, 86400.0, _collider_mol_per_l(298.15))
    assert bench.verdict is SurvivalVerdict.SURVIVES, f"bench must SURVIVE, got {bench.verdict}"
    assert bench.grade == "PREDICTED", "298 K is ~900 K below the sourced window -> a flagged extrapolation"
    assert bench.forward_fraction >= 0.99, "the forward lower bound must clear the SURVIVES band at the bench"

    # 3. INDEPENDENT thermo bearing agrees Br2 is stable (ΔG298 > 0 for dissociation), computed from the
    #    sourced CODATA table -- a different quantity (equilibrium state function) and source family than the
    #    Warshay kinetic barrier.  Value pinned to the ROUND-26 verdict.
    dg = _delta_g_dissociation_298()
    assert abs(dg - 161.65) < 0.1, f"ΔG298(Br2->2Br) {dg:.2f} drifted from the ROUND-26 sourced +161.65"
    assert dg > 0.0, "the independent thermo bearing must agree Br2 is favoured (stable) at 298 K"

    # 4. FAIL-CLOSED, in-window long hold: the forward channel would destroy Br2, but the reverse is omitted
    #    -> DEFER to UNKNOWN (a DEGRADES would be a fabricated refutation).
    in_long = collider_survival(_REF, 1200.0, 10.0, _collider_mol_per_l(1200.0))
    assert in_long.verdict is SurvivalVerdict.UNKNOWN, "an in-window long hold must DEFER (reverse omitted)"
    assert in_long.grade == "DERIVED", "1200 K is inside the sourced window"
    assert in_long.forward_fraction < 0.5, "the forward channel alone should be well below the SURVIVES band"

    # 5. FAIL-CLOSED, out-of-window refutation: a sub-survives extrapolation must not refute -> UNKNOWN.
    out = collider_survival(_REF, 2500.0, 1e-4, _collider_mol_per_l(2500.0))
    assert out.verdict is SurvivalVerdict.UNKNOWN, "an extrapolated refutation must fail closed to UNKNOWN"
    assert out.grade == "PREDICTED", "2500 K is above the sourced window"

    # 6. NEVER a fabricated DEGRADES/MARGINAL, anywhere on a wide (T, t) sweep.
    seen: set[str] = set()
    for T in (298.15, 500.0, 800.0, 1200.0, 1500.0, 1825.0, 1900.0, 2500.0, 3000.0):
        for t in (1e-4, 1.0, 60.0, 3600.0, 86400.0):
            seen.add(collider_survival(_REF, T, t, _collider_mol_per_l(T)).verdict.value)
    assert seen <= {"SURVIVES", "UNKNOWN"}, f"the model must never certify DEGRADES/MARGINAL, saw {seen}"
    assert seen == {"SURVIVES", "UNKNOWN"}, f"the sweep must exercise BOTH SURVIVES and UNKNOWN, saw {seen}"

    # 7. The reverse-free RATE carries the fast-at-shock-T fact (a sub-ms half-life at 1825 K, 1 atm).
    half_life = math.log(2.0) / pseudo_first_order_k(_REF, 1825.0, _collider_mol_per_l(1825.0))
    assert half_life < 1e-3, f"forward dissociation at 1825 K must be sub-ms, got t1/2 = {half_life:g} s"

    # 8. [M] is never defaulted: a non-finite/non-positive collider concentration RAISES (never fabricates).
    for bad in (0.0, -1.0, float("nan"), float("inf")):
        try:
            collider_survival(_REF, 298.15, 60.0, bad)
            raise AssertionError(f"[M] = {bad} must raise, not fabricate a rate")
        except (ValueError, TypeError):
            pass

    # 9. Structure-keyed, direction-specific lookup: Br2 reads its Ar fit; the Br ATOM (a product) does not;
    #    an unseeded collider (Ne) is a loud None, never a borrowed Ar fit.
    assert collider_dissociation_for(br2, collider="Ar") is not None, "Br2 must read its Ar dissociation fit"
    assert collider_dissociation_for(parse_smiles("[Br]"), collider="Ar") is None, "a product must not read it"
    assert collider_dissociation_for(br2, collider="Ne") is None, "an unseeded collider must be a loud None"


def report() -> dict:
    bench = collider_survival(_REF, 298.15, 86400.0, _collider_mol_per_l(298.15))
    return {
        "kD_1825_Ar_transcription": dissociation_rate(_REF, 1825.0),
        "bench_298_verdict": f"{bench.verdict.value} ({bench.grade})",
        "delta_g_dissoc_298_independent": round(_delta_g_dissociation_298(), 2),
        "half_life_1825_1atm_s": math.log(2.0) / pseudo_first_order_k(_REF, 1825.0, _collider_mol_per_l(1825.0)),
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


if __name__ == "__main__":
    validate()
    for key, value in report().items():
        print(f"{key}: {value}")
    print(f"\ncontent_hash (set FROZEN_HASH to this to freeze): {content_hash()}")
