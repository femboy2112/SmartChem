"""ITEM5-PHASE-RANK-01: the drafter's public LINEAR ranking API (`rank_routes`) is now phase-aware.

The R37 item-5 brick threaded ``phases`` through ``verify_feasibility`` but deliberately STOPPED below the public
ranking API -- "no dual-phase ranked route exists -- the zero-call-sites trap; unparks when one does" (ROADMAP.md,
the item-5 remaining brick).  This round builds the forcing consumer and threads ``phases`` up
``rank_routes`` -> ``fit_routes`` -> ``fit_route`` -> ``verify_feasibility`` to serve it.

Re-checkable demonstrations, all on the REAL ``rank_routes``/``fit_route``:

1. THREADING REACHES THE RANKER -- the SAME single route (Br2 -> 2 Br., Br2 the dual-phase species) scored with
   ``phases=None`` fail-closes its feasibility to UNKNOWN (net ΔG ``None``: a phase-blind lookup of the multiphase
   Br2 is refused, the R36 fail-closed gate), and with ``phases={Br2:"gas", Br:"gas"}`` resolves to UNFAVORABLE with
   net ΔG = +161.65 (the sourced CODATA Br-Br dissociation the R26 DOW-thermo add calibrated).

2. THE FORCING CONSUMER -- the SIGN-tier ranking-ORDER flip (default thermo, no injection).  A Br2 route
   (phase-sensitive: UNKNOWN -> UNFAVORABLE) vs an unsourced, phase-INERT sibling (I2 -> 2 I., stays UNKNOWN).
   ``phases=None`` -> they tie on every ranking tier -> discovery order [Br2, I2]; ``phases={Br2:"gas",...}`` -> the
   Br2 route sinks to the UNFAVORABLE feasibility tier and the order FLIPS to [I2, Br2].  This flip rides on the
   sourced +161.65 kJ dissociation -- a real, robust effect, ORDERS OF MAGNITUDE above any thermochemical noise.
   It is the dual-phase ranked route the R37 brick was waiting for.

3. BYTE-IDENTICAL DEFAULT -- ``rank_routes(routes)`` (no ``phases`` arg) == ``rank_routes(routes, phases=None)``, and
   a phase declaration for a species a route does NOT carry leaves that route's fit untouched (the dict is filtered
   to each route's own species).

4. THE FAIL-CLOSED GUARANTEE HOLDS AT THE SPECIFIC-PHASE LAYER (evil-morty R43 fold) -- for a MULTIPHASE species, a
   declared phase that the table does not hold (an untabulated "solid"/"aqueous", or a mis-cased "Gas") fail-closes
   to UNKNOWN, exactly as ``phase=None`` does.  It does NOT fall through to a phase-blind Benson estimate (which would
   answer a DIFFERENT phase than asked -- a silently-wrong-phase ΔG).  This is what makes "rank on the declared
   phase" SOUND rather than "rank on whatever the fallback guessed"; see feasibility.py's guard and
   ``docs/research/ITEM5_PHASE_AWARE_RANKING_SCOPE_v0.1.md`` §Hardening.

5. THE MAGNITUDE TIER IS PHASE-FED (plumbing, at the FIT level) -- Br2 + H2 -> 2 HBr is FAVORABLE in BOTH phases but
   with a phase-dependent net ΔG (gas -109.83, liquid -106.72).  So the M2b additive net-ΔG magnitude tier
   (``_score_tuple`` applies it only in the FAVORABLE class) reads a phase-dependent value -- the plumbing reaches
   it.  HONEST BOUNDARY: this 3.11 kJ/mol split is Br2's ΔG_vap at 298 K, BELOW the thermochemical noise floor of
   the estimates this stack derives, so it is NOT claimed that a REAL-chemistry ranking reorders on it (a flip needs
   a rival route within ~3 kJ of the lever, which is within noise).  The magnitude tier's phase-feed is demonstrated;
   the robust forcing consumer is the SIGN tier (#2), not this.

6. THE PHASE LEVER IS NON-MONOTONE IN T -- it REVERSES SIGN (dalembert R43 fold).  ΔG_gas - ΔG_liq =
   -30.91 + 0.093258*T (kJ/mol), zero at T = 331.45 K.  Below it gas is the more favorable phase; ABOVE it liquid is.
   Demonstrated at 298.15 K (gas favored) vs 350 K (liquid favored).  A caller reaches T through the step
   ``ConditionEnvelope``; the ranker exposes no ``temperature_k`` of its own (a named follow-up).  So any DIRECTIONAL
   statement ("declaring gas floats a Br2-reactant route") is a 298 K statement, false above the crossover.

7. THE rank_dags DEFER IS REAL -- ``rank_routes`` grew a ``phases`` parameter but ``rank_dags`` did NOT (the ROUND-15
   ``of_dag`` re-projection fold: rank_routes returns the fits of_fit projects, rank_dags returns DAGs of_dag
   RE-PROJECTS under defaults -- exposing phases on rank_dags alone diverges rank from dossier).  A signature fact.

RDKit-free; no oracle needed (the thermochemistry is the repo's own sourced CODATA seed + a labelled test-injected
HBr(g) record for the FAVORABLE fit-level magnitude demonstration).
"""
from __future__ import annotations

import hashlib
import inspect
import json

from smartchem.data.thermo import DEFAULT_THERMO, ThermoRef
from smartchem.experiment.drafter import ConstraintBox, fit_route, rank_dags, rank_routes
from smartchem.experiment.feasibility import _formula_str, verify_feasibility
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles as M

FROZEN_HASH = "93d9f0cf61cbc9caeafd4b3ee2ef446ed3517cf84852c4953b6e740c906b506d"

# --- species -------------------------------------------------------------------------------------------------
_BR2 = M("BrBr")   # dual-phase in DEFAULT_THERMO: gas ΔfH°=+30.91, liquid ΔfH°=0 -> is_multiphase -> phase-blind fail
_BR = M("[Br]")    # bromine atom, gas (sourced)
_I2 = M("II")      # iodine: UNSOURCED / not phase-tabulated -> feasibility UNKNOWN, phase-INERT
_I = M("[I]")
_H2 = M("[H][H]")
_HBR = M("Br")     # HBr (BrH); injected for the FAVORABLE fit-level magnitude demonstration
_ETOH = M("CCO")   # a multiphase Benson-coverable species (injected gas+liquid) -- the F1 guard-leak test bed
_C2H4 = M("C=C")   # ethylene (Benson-derivable) -- product in the ethanol decomposition guard reaction
_H2O = M("O")      # water (sourced) -- product in the ethanol decomposition guard reaction

# HBr(g) at standard values (CODATA-ish) for the FAVORABLE magnitude demonstration (fit-level only; no order flip).
_TBL_HBR = DEFAULT_THERMO.with_records(
    ThermoRef(_formula_str(_HBR), "hydrogen bromide", -36.29, 198.70, "gas", "test-injected CODATA-standard HBr(g)"),
)
# ethanol tabulated in TWO phases -> a multiphase, Benson-COVERABLE species: the case where the specific-phase leak
# would fabricate a verdict if the guard only covered phase=None (evil-morty R43).
_TBL_ETOH = DEFAULT_THERMO.with_records(
    ThermoRef(_formula_str(_ETOH), "ethanol", -234.8, 281.6, "gas", "test-injected ethanol(g)"),
    ThermoRef(_formula_str(_ETOH), "ethanol", -277.6, 160.7, "liquid", "test-injected ethanol(l)"),
)


def _step(reactants, products, target):
    return ExperimentStep.assembling(target, tuple(reactants), tuple(products))


def _route_labels(fits, marks):
    """Best-first labels of a rank_routes result (which returns FITS, not routes)."""
    out = []
    for f in fits:
        for label, route in marks:
            if f.route is route:
                out.append(label)
                break
    return out


# 1 -- the phase declaration reaches the ranker (the same route, two declarations, a different fit).
def threading_reaches_ranker() -> dict:
    ra = ExperimentRoute.of(_step([_BR2], [_BR, _BR], _BR))   # Br2 -> 2 Br.
    none = fit_route(ra, ConstraintBox())
    gas = fit_route(ra, ConstraintBox(), phases={_BR2: "gas", _BR: "gas"})
    return {
        "none_verdict": none.feasibility.verdict,
        "none_net": none.feasibility.net_delta_g_kj,
        "gas_verdict": gas.feasibility.verdict,
        "gas_net": round(gas.feasibility.net_delta_g_kj, 4),
        "changed": none.feasibility.verdict != gas.feasibility.verdict,
    }


# 2 -- the forcing consumer: the sign-tier ORDER flip on the default thermo table.
def sign_tier_order_flip() -> dict:
    ra = ExperimentRoute.of(_step([_BR2], [_BR, _BR], _BR))   # phase-sensitive
    rb = ExperimentRoute.of(_step([_I2], [_I, _I], _I))       # phase-inert (unsourced -> UNKNOWN)
    marks = [("Br2", ra), ("I2", rb)]
    order_none = _route_labels(rank_routes([ra, rb]), marks)
    order_gas = _route_labels(rank_routes([ra, rb], phases={_BR2: "gas", _BR: "gas"}), marks)
    return {"order_none": order_none, "order_gas": order_gas, "flipped": order_none != order_gas}


# 3 -- the default is byte-identical: no-arg == phases=None, and a foreign phase decl leaves an untouched route.
def default_is_byte_identical() -> dict:
    ra = ExperimentRoute.of(_step([_BR2], [_BR, _BR], _BR))
    rb = ExperimentRoute.of(_step([_I2], [_I, _I], _I))
    marks = [("Br2", ra), ("I2", rb)]
    noarg = _route_labels(rank_routes([ra, rb]), marks)
    explicit_none = _route_labels(rank_routes([ra, rb], phases=None), marks)
    rb_none = fit_route(rb, ConstraintBox())
    rb_with_foreign_phase = fit_route(rb, ConstraintBox(), phases={_BR2: "gas"})
    return {
        "noarg": noarg,
        "explicit_none": explicit_none,
        "noarg_equals_none": noarg == explicit_none,
        "foreign_phase_inert": rb_none.feasibility.verdict == rb_with_foreign_phase.feasibility.verdict,
    }


# 4 -- the fail-closed guarantee holds at the SPECIFIC-phase layer, for a multiphase Benson-coverable species.
def guard_closes_on_untabulated_phase() -> dict:
    # ethanol is tabulated gas+liquid (multiphase) AND Benson-coverable, so a declared phase the table lacks would
    # fabricate a phase-blind estimate if the guard only covered phase=None (the evil-morty R43 leak).  Decompose it
    # so ethanol's own phase actually drives the net (an identity step would cancel the species).
    route = ExperimentRoute.of(_step([_ETOH], [_C2H4, _H2O], _C2H4))   # ethanol -> ethylene + water
    out = {}
    for ph_key, ph in [("none", None), ("gas", "gas"), ("liquid", "liquid"),
                       ("solid", "solid"), ("miscased_Gas", "Gas"), ("aqueous", "aqueous")]:
        phases = None if ph is None else {_ETOH: ph}
        f = fit_route(route, ConstraintBox(), thermo=_TBL_ETOH, phases=phases)
        out[ph_key] = {"verdict": f.feasibility.verdict,
                       "net": None if f.feasibility.net_delta_g_kj is None else round(f.feasibility.net_delta_g_kj, 4)}
    return out


# 5 -- the M2b net-ΔG MAGNITUDE tier is phase-fed (FAVORABLE class), at the FIT level (plumbing; no order claim).
def magnitude_tier_phase_fed() -> dict:
    rc = ExperimentRoute.of(_step([_BR2, _H2], [_HBR, _HBR], _HBR))   # Br2 + H2 -> 2 HBr (phase-sensitive, FAVORABLE)
    gas = fit_route(rc, ConstraintBox(), thermo=_TBL_HBR, phases={_BR2: "gas"})
    liq = fit_route(rc, ConstraintBox(), thermo=_TBL_HBR, phases={_BR2: "liquid"})
    none = fit_route(rc, ConstraintBox(), thermo=_TBL_HBR)
    return {
        "none_verdict": none.feasibility.verdict,       # UNKNOWN (multiphase fail-closed)
        "gas_verdict": gas.feasibility.verdict,          # FAVORABLE
        "liquid_verdict": liq.feasibility.verdict,       # FAVORABLE
        "gas_net": round(gas.feasibility.net_delta_g_kj, 4),
        "liquid_net": round(liq.feasibility.net_delta_g_kj, 4),
        "both_favorable": gas.feasibility.verdict == "FAVORABLE" == liq.feasibility.verdict,
        "net_is_phase_dependent": gas.feasibility.net_delta_g_kj != liq.feasibility.net_delta_g_kj,
        "lever_kj": round(gas.feasibility.net_delta_g_kj - liq.feasibility.net_delta_g_kj, 4),
    }


# 6 -- the phase lever is non-monotone in T: it reverses sign at 331.45 K.
def phase_lever_reverses_with_temperature() -> dict:
    rc = ExperimentRoute.of(_step([_BR2, _H2], [_HBR, _HBR], _HBR))
    def lever(temp):
        g = verify_feasibility(rc, thermo=_TBL_HBR, phases={_BR2: "gas"}, temperature_k=temp).net_delta_g_kj
        liq = verify_feasibility(rc, thermo=_TBL_HBR, phases={_BR2: "liquid"}, temperature_k=temp).net_delta_g_kj
        return g - liq
    l298 = lever(298.15)
    l350 = lever(350.0)
    crossover = 30.91 / 0.093258   # ΔfH° gap 30.91 / ΔS° gap 0.093258 kJ/mol/K
    return {
        "lever_298_kj": round(l298, 4),      # < 0: gas the more favorable phase
        "lever_350_kj": round(l350, 4),      # > 0: liquid the more favorable phase
        "sign_reverses": (l298 < 0) and (l350 > 0),
        "crossover_k": round(crossover, 2),
    }


# 7 -- the rank_dags defer is a real signature fact (the ROUND-15 of_dag re-projection fold).
def rank_dags_defers_phases() -> dict:
    rr = set(inspect.signature(rank_routes).parameters)
    rd = set(inspect.signature(rank_dags).parameters)
    return {
        "rank_routes_has_phases": "phases" in rr,
        "rank_dags_has_phases": "phases" in rd,
        "defer_is_real": ("phases" in rr) and ("phases" not in rd),
    }


def _payload() -> dict:
    return {
        "threading": threading_reaches_ranker(),
        "sign_flip": sign_tier_order_flip(),
        "default_identical": default_is_byte_identical(),
        "guard_closed": guard_closes_on_untabulated_phase(),
        "magnitude_fed": magnitude_tier_phase_fed(),
        "lever_reverses": phase_lever_reverses_with_temperature(),
        "rank_dags_defer": rank_dags_defers_phases(),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, default=str).encode()).hexdigest()


def validate() -> bool:
    """RDKit-free self-check: the phase declaration reaches the ranker and flips the ORDER (sign tier, robust);
    the default is byte-identical; the fail-closed guarantee holds at the specific-phase layer; the magnitude tier
    is phase-fed (plumbing); the lever reverses sign at 331.45 K; and the rank_dags defer holds."""
    t = threading_reaches_ranker()
    assert t["none_verdict"] == "UNKNOWN" and t["none_net"] is None, t
    assert t["gas_verdict"] == "UNFAVORABLE" and t["gas_net"] == 161.6531, t
    assert t["changed"] is True, t

    s = sign_tier_order_flip()
    assert s["order_none"] == ["Br2", "I2"], s
    assert s["order_gas"] == ["I2", "Br2"], s
    assert s["flipped"] is True, s

    d = default_is_byte_identical()
    assert d["noarg_equals_none"] is True, d
    assert d["foreign_phase_inert"] is True, d

    g = guard_closes_on_untabulated_phase()
    assert g["none"]["verdict"] == "UNKNOWN" and g["none"]["net"] is None, g          # phase-blind on a multiphase species
    assert g["gas"]["verdict"] != "UNKNOWN" and g["liquid"]["verdict"] != "UNKNOWN", g  # tabulated phases resolve
    assert g["gas"]["net"] != g["liquid"]["net"], g                                    # ... to DIFFERENT nets (phase matters)
    assert g["solid"]["verdict"] == "UNKNOWN" and g["solid"]["net"] is None, g         # untabulated -> fail-closed (F1)
    assert g["aqueous"]["verdict"] == "UNKNOWN", g                                     # untabulated -> fail-closed (F1)
    assert g["miscased_Gas"]["verdict"] == "UNKNOWN", g                                # a mis-cased real phase -> fail-closed (F1)

    m = magnitude_tier_phase_fed()
    assert m["none_verdict"] == "UNKNOWN", m
    assert m["both_favorable"] is True, m
    assert m["gas_net"] == -109.8263 and m["liquid_net"] == -106.7212, m
    assert m["net_is_phase_dependent"] is True, m
    assert m["lever_kj"] == -3.1051, m                                     # Br2 ΔG_vap at 298 K -- sub-noise, disclosed

    lv = phase_lever_reverses_with_temperature()
    assert lv["lever_298_kj"] < 0, lv                                      # gas favored at 298 K
    assert lv["lever_350_kj"] > 0, lv                                      # liquid favored at 350 K
    assert lv["sign_reverses"] is True, lv
    assert lv["crossover_k"] == 331.45, lv

    r = rank_dags_defers_phases()
    assert r["rank_routes_has_phases"] is True, r
    assert r["rank_dags_has_phases"] is False, r
    assert r["defer_is_real"] is True, r
    return True


if __name__ == "__main__":  # pragma: no cover
    ok = validate()
    print(f"validate() -> {ok}")
    print(f"content_hash() -> {content_hash()}")
