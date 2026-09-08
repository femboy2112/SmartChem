"""DOW-BROMINE-KINETICS-01 (queue item 3b): the modified-Arrhenius, collider-dependent Br2 dissociation model.

The KINETIC half of the DOW-bromine litmus, from the recovered Warshay primary (NASA TN D-3502, 1966).  This
battery pins the anti-fabrication discipline that is the whole point of the round:

  * the sourced modified-Arrhenius rate reproduces Warshay's Table I point (a TRANSCRIPTION check) and the
    √T prefactor is load-bearing (a control with n=0 disagrees);
  * the bench verdict is SURVIVES, flagged PREDICTED, and it is a rigorous LOWER bound (the reverse only helps)
    cross-referenced to the INDEPENDENT ROUND-26 thermodynamic bearing;
  * the model NEVER certifies a DEGRADES/MARGINAL -- an in-window long hold DEFERS (the reverse recombination
    Warshay omitted), and an out-of-window sub-survives DEFERS (a refutation from an extrapolation is
    fabrication) -- across a wide (T, t) sweep only SURVIVES/UNKNOWN ever appear;
  * [M] is never defaulted; the lookup is structure-keyed and direction-specific;
  * the interpretive band and gas constant are REUSED from the first-order primitive, never re-declared.
"""
from __future__ import annotations

import math

import pytest

from experiments.dow_bromine_kinetics_probe import FROZEN_HASH, content_hash
from experiments.dow_bromine_kinetics_probe import validate as validate_probe
from smartchem.experiment.collider_kinetics import (
    COLLIDER_KINETICS_SCHEMA,
    SEED_COLLIDER_REFS,
    ColliderDissociationRef,
    ColliderSurvival,
    GAS_CONSTANT_J_PER_MOL_K,
    SurvivalVerdict,
    collider_dissociation_for,
    collider_survival,
    dissociation_rate,
    pseudo_first_order_k,
    survival_verdict,
)
from smartchem.smiles import parse_smiles

_REF = SEED_COLLIDER_REFS[0]
_R = 8.314462618


def _M(temperature_k: float, atm: float = 1.0) -> float:
    return atm * 101325.0 / (_R * temperature_k) / 1000.0


# --- the sourced rate: transcription self-consistency + the load-bearing √T prefactor ------------------

def test_dissociation_rate_reproduces_the_warshay_table_i_point():
    # kD(1825 K, Ar) reproduces Warshay's observed 1.48e6 to ~6% -- a TRANSCRIPTION check (reuses the fit).
    kd = dissociation_rate(_REF, 1825.0)
    assert abs(kd - 1.48e6) / 1.48e6 < 0.10
    # hand value against A*T^n*exp(-Ea/RT).
    hand = (10.0 ** _REF.log10_a) * 1825.0 ** _REF.t_exponent * math.exp(
        -(_REF.ea_kj_per_mol * 1000.0) / (GAS_CONSTANT_J_PER_MOL_K * 1825.0)
    )
    assert abs(kd - hand) / hand < 1e-9


def test_modified_arrhenius_t_exponent_is_load_bearing():
    # the √T prefactor is not decoration: dropping it (n=0) changes the rate materially at shock T.
    assert _REF.t_exponent == 0.5
    with_t = dissociation_rate(_REF, 1825.0)
    plain = (10.0 ** _REF.log10_a) * math.exp(
        -(_REF.ea_kj_per_mol * 1000.0) / (GAS_CONSTANT_J_PER_MOL_K * 1825.0)
    )
    assert abs(with_t / plain - math.sqrt(1825.0)) < 1e-6
    assert with_t / plain > 40.0                              # √1825 ~= 42.7, a real factor, not negligible


def test_pseudo_first_order_multiplies_by_declared_collider_concentration():
    kd = dissociation_rate(_REF, 1200.0)
    assert pseudo_first_order_k(_REF, 1200.0, 2.0) == pytest.approx(kd * 2.0)


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
def test_collider_concentration_never_defaulted_and_validated(bad):
    with pytest.raises((ValueError, TypeError)):
        pseudo_first_order_k(_REF, 298.15, bad)
    with pytest.raises((ValueError, TypeError)):
        collider_survival(_REF, 298.15, 60.0, bad)


# --- the bench verdict: a sound, cross-referenced, LOWER-bound SURVIVES ---------------------------------

def test_bench_survives_as_a_flagged_predicted_extrapolation():
    b = collider_survival(_REF, 298.15, 86400.0, _M(298.15))
    assert b.verdict is SurvivalVerdict.SURVIVES
    assert b.grade == "PREDICTED"                             # 298 K is ~900 K below the sourced window
    assert b.forward_fraction >= 0.99
    # the reason carries its own warrant (birdperson breach 5): the extrapolation, the lower bound, the
    # independent thermo bearing, and the W3 channel scope must all be spoken.
    r = b.reason.lower()
    assert "predicted" in r and "lower bound" in r and "161.65" in b.reason and "channel" in r


def test_bench_survives_scopes_to_the_modelled_channel_not_unconditional_stability():
    b = collider_survival(_REF, 298.15, 86400.0, _M(298.15))
    assert "unconditional" in b.reason.lower()                # never claims "Br2 is stable" against all fates


# --- the fail-closed core: this model NEVER certifies destruction ---------------------------------------

def test_in_window_long_hold_defers_because_the_reverse_is_omitted():
    # 1200 K is inside the sourced window and the forward channel would destroy Br2, but Warshay's fit omits
    # the reverse recombination -> a DEGRADES would be a fabricated refutation -> DEFER to UNKNOWN.
    v = collider_survival(_REF, 1200.0, 10.0, _M(1200.0))
    assert v.verdict is SurvivalVerdict.UNKNOWN
    assert v.grade == "DERIVED"
    assert v.forward_fraction < 0.5                           # the forward channel alone is well below SURVIVES
    assert "reverse" in v.reason.lower()


def test_out_of_window_subsurvives_fails_closed_not_a_refutation():
    v = collider_survival(_REF, 2500.0, 1e-4, _M(2500.0))
    assert v.verdict is SurvivalVerdict.UNKNOWN
    assert v.grade == "PREDICTED"
    assert "extrapolat" in v.reason.lower()


def test_above_window_survives_band_defers_and_emits_no_false_below_window_warrant():
    # Above the fit window (2500 K) a sub-microsecond hold leaves ~everything intact (a SURVIVES BAND), but the
    # conservative-extrapolation argument is proven only IN or BELOW the window -- above it kD GROWS with T, so
    # the forward fraction is no longer a guaranteed lower bound.  The pre-fold code emitted SURVIVES here with
    # a hardcoded *below-window* warrant ("colder is slower / low-T barrier") -- a false story (evil-morty F1).
    v = collider_survival(_REF, 2500.0, 1e-13, _M(2500.0))
    assert v.forward_fraction >= 0.99                        # the forward band IS SURVIVES...
    assert v.verdict is SurvivalVerdict.UNKNOWN              # ...but it is NOT certified above the window
    assert "ABOVE" in v.reason and "not certified" in v.reason.lower()


def test_never_certifies_degrades_or_marginal_across_a_wide_sweep():
    seen = set()
    for T in (298.15, 500.0, 800.0, 1200.0, 1500.0, 1825.0, 1900.0, 2500.0, 3000.0):
        for t in (1e-4, 1.0, 60.0, 3600.0, 86400.0):
            seen.add(collider_survival(_REF, T, t, _M(T)).verdict.value)
    assert seen <= {"SURVIVES", "UNKNOWN"}
    assert seen == {"SURVIVES", "UNKNOWN"}                    # both are exercised -> non-vacuous


def test_survives_only_when_the_forward_lower_bound_clears_the_band():
    # the verdict tracks the SHARED band applied to the forward (lower-bound) fraction, and SURVIVES implies
    # the forward fraction already cleared 99% -- so the reversible truth is at least that intact.
    for T, t in ((298.15, 86400.0), (1825.0, 1e-9), (1200.0, 10.0), (2500.0, 1e-4)):
        v = collider_survival(_REF, T, t, _M(T))
        if v.verdict is SurvivalVerdict.SURVIVES:
            assert survival_verdict(v.forward_fraction) is SurvivalVerdict.SURVIVES
        else:
            assert v.verdict is SurvivalVerdict.UNKNOWN


def test_collider_survival_dataclass_rejects_a_certified_destruction():
    for bad in (SurvivalVerdict.DEGRADES, SurvivalVerdict.MARGINAL):
        with pytest.raises(ValueError):
            ColliderSurvival(COLLIDER_KINETICS_SCHEMA, "x", "Ar", 298.0, 60.0, 0.04, 0.10, bad, "DERIVED")


# --- structure-keyed, direction-specific lookup; the Ar-only seed --------------------------------------

def test_lookup_is_structure_keyed_and_direction_specific():
    br2 = parse_smiles("BrBr")
    assert collider_dissociation_for(br2, collider="Ar") is not None
    assert collider_dissociation_for(parse_smiles("[Br]"), collider="Ar") is None      # product, wrong direction
    assert collider_dissociation_for(br2, collider="Ne") is None                        # unseeded collider


def test_seed_is_ar_only_with_the_collisional_ea_below_the_bond_enthalpy():
    assert len(SEED_COLLIDER_REFS) == 1
    assert _REF.collider == "Ar"
    # the fitted collisional Ea is BELOW the Br-Br bond enthalpy (192.83 kJ/mol) -- the known feature, carried
    # honestly in provenance, never forced to match the thermo quantity.
    assert _REF.ea_kj_per_mol < 192.83
    assert "collisional-Ea-below-D0" in _REF.provenance or "below the Br-Br" in _REF.provenance


# --- reuse-not-redeclare (birdperson breach 4): no drift from the first-order primitive -----------------

def test_band_policy_and_gas_constant_are_reused_not_redeclared():
    from smartchem.experiment import stability_horizon as sh
    assert survival_verdict is sh.survival_verdict            # the SAME band function, not a copy
    assert GAS_CONSTANT_J_PER_MOL_K == sh.GAS_CONSTANT_J_PER_MOL_K


# --- record validation ----------------------------------------------------------------------------------

@pytest.mark.parametrize("kwargs", [
    {"collider": ""},                                         # empty collider label
    {"ea_kj_per_mol": -1.0},                                  # negative Ea
    {"t_exponent": float("nan")},                             # non-finite exponent
    {"t_exponent": -0.5},                                     # negative n breaks the colder-is-slower warrant
    {"temperature_range_k": (1900.0, 1200.0)},                # lo > hi
])
def test_ref_validation_rejects_malformed_records(kwargs):
    base = dict(
        reactant_smiles="BrBr", product_smiles="[Br]", collider="Ar",
        name="x", ea_kj_per_mol=100.0, log10_a=8.0, t_exponent=0.5,
        a_units="L mol^-1 s^-1 K^-1/2", temperature_range_k=(1200.0, 1900.0), provenance="p",
    )
    base.update(kwargs)
    with pytest.raises((ValueError, TypeError)):
        ColliderDissociationRef(**base)


# --- the committed harness (experiments-are-committed) --------------------------------------------------

def test_committed_harness_validates_and_is_frozen():
    validate_probe()
    assert content_hash() == FROZEN_HASH
