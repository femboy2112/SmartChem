"""DISCONN-SEL-01: the ranker prefers a chemically-sensible disconnection -- DERIVED from bond energies, not hard-coded.

The R45 caffeine finding: the capped-scission engine OVER-GENERATES, and the ranker put a valence-valid-but-dubious
C-C homologation (``ethanol + theophylline -> caffeine + methanol``) ABOVE the sound N-methylation (``theophylline +
methanol -> caffeine + water``), because both are thermo-UNKNOWN and the ranker fell through to arbitrary discovery
order.  This adds the missing signal WITHOUT hard-coding any reaction: it hard-codes REALITY (mean bond enthalpies --
measured physical constants, like atomic masses) and DERIVES the reaction enthalpy by Hess's law over the net bond
change (:mod:`smartchem.experiment.bond_enthalpy`), then ranks on its SIGN as a dead-last, strictly-subordinate,
neutral-on-ignorance tiebreaker.

Re-checkable demonstrations, all on the REAL estimator + ``compile_synthesis`` route engine (RDKit-free):

1. CALIBRATION (the instrument rule) -- the estimator recovers the correct SIGN of seven reactions with known ΔH
   (RMS residual ≈ 9 kJ, the source of the dead-band) BEFORE its readings on novel disconnections are trusted.
2. CAFFEINE FLIP -- the sound N-methylation now ranks ABOVE the dubious C-C homologation; the derived tier's physics
   is that water's O-H (463 kJ) is a strong sink the homologation lacks: ΔH(sound) = −19, ΔH(dubious) = +19 kJ.
3. NEUTRAL ON IGNORANCE -- a reaction whose net bond change touches an UNTABULATED bond type (a C-P bond) yields
   ``None`` (never a fabricated number) -> the BORDERLINE middle rank, never a reward or penalty for ignorance.
4. STRICTLY SUBORDINATE -- the derived tier is DEAD-LAST: a route better on ANY sourced tier (here selectivity) but
   worse on the derived tier still ranks ABOVE one worse on the sourced tier but better on the derived tier.  Sourced
   evidence always dominates the estimate; where a sourced ΔG reaches a route, this tier is inert.
5. NOT A REACTION TABLE -- the derived ΔH is computed from the molecular graphs + the bond-enthalpy constants (keyed
   by bond TYPE, never by reaction) for reactions in NO table (caffeine's methylation is untabulated, R45).  That
   GENERALIZATION is the anti-lookup proof; the reverse-reaction sign-flip is only a corroborating property (every
   signed quantity, a lookup included, is antisymmetric -- dalembert R47).
6. DOMAIN GUARD -- bond additivity inverts the sign on ring-strain release / aromatization (it is blind to non-local
   stabilization); the guard FAILS CLOSED (declines to BORDERLINE) when the endocyclic-bond-type multiset changes,
   keeping the ring-PRESERVING caffeine methylation while declining cyclopropane->propene and CHD->benzene
   (evil-morty / dalembert R47).
"""
from __future__ import annotations

import hashlib
import json

from smartchem.experiment.bond_enthalpy import (
    CALIBRATION,
    DERIVED_BORDERLINE_KJ,
    MEAN_BOND_ENTHALPY_KJ,
    disconnection_favorability_rank,
    reaction_delta_h_kj,
)
from smartchem.experiment.compile import compile_synthesis
from smartchem.experiment.drafter import ConstraintBox, RouteFitStatus, _score_tuple
from smartchem.smiles import parse_smiles as M

_CAFFEINE = "CN1C=NC2=C1C(=O)N(C)C(=O)N2C"
_THEOPHYLLINE = "N1C=NC2=C1C(=O)N(C)C(=O)N2C"
_SOUND = "C7H8N4O2 + CH4O -> C8H10N4O2 + H2O"        # theophylline + methanol -> caffeine + water
_DUBIOUS = "C2H6O + C7H8N4O2 -> C8H10N4O2 + CH4O"    # ethanol + theophylline -> caffeine + methanol (C-C homologation)


def _eq(step) -> str:
    lhs = sorted("".join(f"{e}{n if n > 1 else ''}" for e, n in sorted(m.formula.items())) for m in step.reactants)
    rhs = sorted("".join(f"{e}{n if n > 1 else ''}" for e, n in sorted(m.formula.items())) for m in step.products)
    return " + ".join(lhs) + " -> " + " + ".join(rhs)


def _route_eq(route) -> str:
    return " ; ".join(_eq(s) for s in route.steps)


def calibration() -> dict:
    # the instrument rule: recover the SIGN of every known-sign reaction (ALL 7, INCLUDING combustion -- its ~200 kJ
    # magnitude error is why the tier grades sign, never magnitude).  The dead-band is set ABOVE the largest in-domain
    # residual (14 kJ, CH4+Cl2), honestly reported here -- NOT the combustion-excluded RMS (the earlier overclaim).
    signs_ok, residuals = [], []
    for name, rs, ps, lit in CALIBRATION:
        dh = reaction_delta_h_kj(tuple(M(s) for s in rs), tuple(M(s) for s in ps))
        signs_ok.append(dh is not None and (dh < 0) == (lit < 0))
        residuals.append(abs(dh - lit) if dh is not None else None)
    max_resid = max(r for r in residuals if r is not None)                    # combustion, ~200 kJ (magnitude only)
    max_resid_ex_combustion = max(r for (_, _, ps, _), r in zip(CALIBRATION, residuals)
                                  if r is not None and "O=C=O" not in ps)     # exclude combustion (CO2 product)
    return {"all_signs_recovered": all(signs_ok), "n": len(signs_ok),
            "max_residual_kj": round(max_resid, 1), "max_in_domain_residual_kj": round(max_resid_ex_combustion, 1),
            "dead_band_kj": DERIVED_BORDERLINE_KJ, "table_size": len(MEAN_BOND_ENTHALPY_KJ)}


def domain_guard() -> dict:
    # evil-morty / dalembert R47: bond additivity inverts the sign on ring-strain release and aromatization; the guard
    # FAILS CLOSED (None) there, while keeping the ring-PRESERVING caffeine methylation.
    return {
        "cyclopropane_to_propene_declined": reaction_delta_h_kj((M("C1CC1"),), (M("CC=C"),)) is None,
        "chd_to_benzene_declined": reaction_delta_h_kj((M("C1=CCCC=C1"),), (M("c1ccccc1"), M("[H][H]"))) is None,
        "benzene_to_chd_declined": reaction_delta_h_kj((M("c1ccccc1"), M("[H][H]")), (M("C1=CCCC=C1"),)) is None,
        # the caffeine methylation preserves the purine ring -> NOT declined (its ΔH stands)
        "caffeine_methylation_in_domain": reaction_delta_h_kj((M(_THEOPHYLLINE), M("CO")),
                                                              (M(_CAFFEINE), M("O"))) is not None,
    }


def _caffeine_ranked() -> tuple:
    compiled = compile_synthesis(
        M(_CAFFEINE), reagents=(M("CO"), M("O")), available=(M(_THEOPHYLLINE), M("CCO")),
        max_depth=2, max_routes=12, cut_budget=40000, commodities=(), box=ConstraintBox(),
    )
    return compiled.ranked


def caffeine_flip() -> dict:
    ranked = _caffeine_ranked()
    eqs = [_route_eq(r.route) for r in ranked]
    sound_i = next((i for i, e in enumerate(eqs) if e == _SOUND), None)
    dubious_i = next((i for i, e in enumerate(eqs) if e == _DUBIOUS), None)
    return {
        "sound_rank": sound_i,
        "dubious_rank": dubious_i,
        "sound_outranks_dubious": sound_i is not None and dubious_i is not None and sound_i < dubious_i,
        # the derived tier is a CALLER-computed coordinate (rank_routes applies it); read it directly, not off
        # _route_score (a pure extractor that defaults it to the neutral 1).
        "sound_derived_rank": disconnection_favorability_rank(ranked[sound_i].route) if sound_i is not None else None,
        "dubious_derived_rank": (disconnection_favorability_rank(ranked[dubious_i].route)
                                 if dubious_i is not None else None),
    }


def derived_delta_h() -> dict:
    caf, theo, meoh, water, etoh = M(_CAFFEINE), M(_THEOPHYLLINE), M("CO"), M("O"), M("CCO")
    return {
        "sound_dh_kj": reaction_delta_h_kj((theo, meoh), (caf, water)),
        "dubious_dh_kj": reaction_delta_h_kj((etoh, theo), (caf, meoh)),
        # antisymmetry -- a corroborating property, NOT the anti-lookup proof (every signed quantity, a lookup
        # included, flips on reverse; dalembert R47).  The real proof it is derived not looked-up is GENERALIZATION:
        # the ΔH is COMPUTED for caffeine's methylation, which is in no reaction/conditions table (R45 untabulated).
        "reverse_sound_dh_kj": reaction_delta_h_kj((caf, water), (theo, meoh)),
    }


def neutral_on_ignorance() -> dict:
    # a net bond change touching an untabulated bond (C-P) -> None, never a fabricated number.
    dh = reaction_delta_h_kj((M("P"), M("C=C")), (M("CCP"),))    # PH3 + C2H4 -> ethylphosphine (forms a C-P bond)
    return {"c_p_untabulated": ("C", "P", 1) not in MEAN_BOND_ENTHALPY_KJ, "delta_h": dh, "is_none": dh is None}


def strictly_subordinate() -> dict:
    # DEAD-LAST proof: a route sourced-FAVORED but derived-UNFAVORABLE must beat one sourced-DISFAVORED but
    # derived-FAVORABLE.  The sourced selectivity tier (position 3) dominates the derived tier (position 11).
    favored_sourced = _score_tuple(RouteFitStatus.FITS, "COMPOSABLE", "FAVORED", "UNKNOWN", "UNKNOWN", "UNKNOWN",
                                   0, 0, derived_rank=2)     # sourced-favored, derived-unfavorable
    favored_derived = _score_tuple(RouteFitStatus.FITS, "COMPOSABLE", "DISFAVORED", "UNKNOWN", "UNKNOWN", "UNKNOWN",
                                   0, 0, derived_rank=0)     # sourced-disfavored, derived-favorable
    return {"sourced_dominates_derived": favored_sourced < favored_derived}


def _payload() -> dict:
    return {
        "1_calibration": calibration(),
        "2_caffeine_flip": caffeine_flip(),
        "3_derived_delta_h": derived_delta_h(),
        "4_neutral_on_ignorance": neutral_on_ignorance(),
        "5_strictly_subordinate": strictly_subordinate(),
        "6_domain_guard": domain_guard(),
    }


FROZEN_HASH = "1fb861eda073275203ad43fb0537c09ea1f9b2fca060f2baf4cddb09f449cd88"


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, default=str).encode()).hexdigest()


def validate() -> bool:
    """RDKit-free self-check: the instrument recovers every known sign (incl combustion) and the dead-band sits above
    the largest in-domain residual; the sound methylation now outranks the dubious homologation; the derived ΔH is
    antisymmetric under reversal; an untabulated bond yields None (neutral on ignorance); the derived tier is strictly
    subordinate to a sourced tier; and the domain guard declines ring-strain/aromatization while keeping the caffeine
    methylation."""
    p = _payload()
    c = p["1_calibration"]
    assert c["all_signs_recovered"] is True, c
    assert c["max_in_domain_residual_kj"] < c["dead_band_kj"] < 19, c   # honest floor: above in-domain error, below the caffeine signal
    f = p["2_caffeine_flip"]
    assert f["sound_outranks_dubious"] is True, f
    assert f["sound_derived_rank"] == 0 and f["dubious_derived_rank"] == 2, f
    d = p["3_derived_delta_h"]
    assert d["sound_dh_kj"] < 0 < d["dubious_dh_kj"], d
    assert d["reverse_sound_dh_kj"] == -d["sound_dh_kj"], d      # antisymmetry (a property; the anti-lookup proof is generalization)
    assert p["4_neutral_on_ignorance"]["is_none"] is True, p["4_neutral_on_ignorance"]
    assert p["5_strictly_subordinate"]["sourced_dominates_derived"] is True, p["5_strictly_subordinate"]
    g = p["6_domain_guard"]
    assert g["cyclopropane_to_propene_declined"] and g["chd_to_benzene_declined"] and g["benzene_to_chd_declined"], g
    assert g["caffeine_methylation_in_domain"] is True, g
    return True


if __name__ == "__main__":
    print("content_hash:", content_hash())
    print("validate:", validate())
    print(json.dumps(_payload(), indent=2, default=str))
