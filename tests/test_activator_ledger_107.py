"""Regression lock for ACTIVATOR-LEDGER-01 (#107): the typed activator ledger demotes a recognized class whose
stoichiometric activator its declared conditions do not supply -- today exactly the Claisen condensation's
enolizing base -- WITHOUT touching type-validity and WITHOUT ever claiming impossibility.

The soundness law under test (mirrors the module docstring):
  * pure DEMOTER -> no-false-VOUCH by construction (it only ever ADDS a hard_blocker; there is no clear/vouch path);
  * class-keyed + base-rate-safe -> ONLY the Claisen condensation carries a requirement today; the other 19 classes
    (pericyclics, Fischer esterification -- the base-rate trap -- activated acyl transfer #110, sulfonate #111) carry
    NONE, so paracetamol-via-Ac2O and the esterification flagships are NOT false-EXCLUDEd;
  * silence resolved toward the capability model -> catalysts==() does NOT clear a class-level requirement;
  * conservative role whitelist -> a base too weak to enolize an ester alpha-C (hydroxide/carbonate/amine) does NOT
    clear the requirement (over-recognizing a base is the unsafe direction);
  * content-determinism preserved -> the check reads the ENVELOPE, never the conserved molecules or reaction_center.
"""
from __future__ import annotations

import dataclasses

import pytest

from smartchem.conditions import ConditionEnvelope, EvidenceStatus
from smartchem.diels_alder import _DA_CENTER
from smartchem.experiment import activator_ledger as al
from smartchem.experiment.activator_ledger import (
    ActivatorRole,
    REQUIRED_ACTIVATORS,
    classify_activator_roles,
    route_activator_blockers,
    step_activator_blockers,
)
from smartchem.experiment.reaction_type_oracle import _RECOGNIZERS, recognize_reaction_type
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

CLAISEN = "Claisen condensation (ester/ketone + ester/carbonate -> 1,3-dicarbonyl + alcohol)"


def _step(rs, ps, catalysts=None):
    s = ExperimentStep.assembling(parse_smiles(ps[0]), tuple(parse_smiles(x) for x in rs),
                                  tuple(parse_smiles(x) for x in ps))
    if catalysts is not None:
        env = ConditionEnvelope(catalysts=tuple(catalysts), status=EvidenceStatus.EXPERIMENTAL, provenance="test")
        s = dataclasses.replace(s, envelope=env)
    return s


def _claisen(catalysts=None):
    return _step(("CC(=O)OCC", "CC(=O)OCC"), ("CC(=O)CC(=O)OCC", "CCO"), catalysts=catalysts)


def _fischer():
    return _step(("CC(=O)O", "CCO"), ("CC(=O)OCC", "O"))


def _diels_alder():
    return _step(("C=CC=C", "C=C"), ("C1CCC=CC1",))


# --------------------------------------------------------------------------- ledger invariants

_HYDROGENATION = "hydrogenation (partial bond-order edit, precursor + H2 -> saturated; one unsaturation reduced)"


def test_ledger_is_exactly_the_two_reviewed_entries_today():
    # A DELIBERATE set. Adding a class requirement is a reviewed base-rate decision, not an accident; this test
    # must be changed on purpose when a further entry is justified. Mega-Round XI re-review added hydrogenation
    # (TRANSITION_METAL_CATALYST); oxoacid ester was reviewed and correctly carries NO entry (self-acidic).
    assert set(REQUIRED_ACTIVATORS) == {CLAISEN, _HYDROGENATION}
    assert REQUIRED_ACTIVATORS[CLAISEN] == frozenset({ActivatorRole.ENOLIZING_BASE})
    assert REQUIRED_ACTIVATORS[_HYDROGENATION] == frozenset({ActivatorRole.TRANSITION_METAL_CATALYST})


def test_every_ledger_key_is_a_live_oracle_class_name():
    live = {name for name, _pred in _RECOGNIZERS}
    assert set(REQUIRED_ACTIVATORS) <= live, "a ledger key is not a current oracle display name (rename drift)"


def test_registry_fingerprint_guard_is_armed_and_matches_live_registry():
    # The growth guard: the reviewed snapshot must equal the live 22-class registry, and the guard must pass on it.
    import hashlib
    live = sorted(name for name, _pred in _RECOGNIZERS)
    assert len(live) == al._REVIEWED_CLASS_COUNT
    assert hashlib.sha256("\n".join(live).encode()).hexdigest()[:16] == al._REVIEWED_REGISTRY_DIGEST
    al._assert_registry_unchanged_since_ledger_review()  # must not raise on the reviewed registry


def test_registry_fingerprint_guard_fires_on_drift(monkeypatch):
    # If a recognizer is added/removed/renamed (digest drifts), import-time guard MUST raise -> forces a ledger
    # re-decision instead of a silent false-VOUCH on growth.
    monkeypatch.setattr(al, "_REVIEWED_REGISTRY_DIGEST", "deadbeefdeadbeef")
    with pytest.raises(AssertionError):
        al._assert_registry_unchanged_since_ledger_review()


def test_only_the_two_reviewed_classes_carry_a_requirement():
    # The base-rate guard, proven over the WHOLE registry without constructing a step per class: every class but
    # the two reviewed ones (Claisen, hydrogenation) must map to an empty requirement, so no pericyclic / Fischer /
    # activated-acyl / oxoacid-ester step is ever demoted.
    carriers = {CLAISEN, _HYDROGENATION}
    for name, _pred in _RECOGNIZERS:
        required = REQUIRED_ACTIVATORS.get(name, frozenset())
        if name in carriers:
            assert required
        else:
            assert required == frozenset(), f"{name!r} unexpectedly requires an activator -- false-EXCLUDE risk"


# --------------------------------------------------------------------------- role classifier

_FILLS_ENOLIZING_BASE = [
    "sodium ethoxide", "NaOEt", "sodium methoxide", "NaOMe", "potassium tert-butoxide", "KOtBu",
    "t-BuOK", "tBuOK", "sodium tert-butoxide", "NaH", "sodium hydride", "KH", "LDA", "lithium diisopropylamide",
    "sodium amide", "NaNH2", "LiHMDS", "LiTMP", "KDA",
]

#: must NOT fill ENOLIZING_BASE. Weak bases (cannot reliably enolize an ester alpha-C), NUCLEOPHILIC organometallics
#: (strong but 1,2-add to the carbonyl rather than enolize it -- the d'Alembert #107 kill), non-bases, and junk.
_MUST_NOT_FILL = [
    "NaOH", "KOH", "sodium hydroxide", "Na2CO3", "K2CO3", "NaHCO3", "sodium bicarbonate",
    "pyridine", "triethylamine", "Et3N", "DBU", "ammonia", "sodium acetate", "water", "acetic acid",
    "sulfuric acid", "base-free", "", "   ",
    # strong-but-nucleophilic organometallics: never used to enolize an ester/ketone -> must NOT clear
    "n-BuLi", "s-BuLi", "t-BuLi", "tert-butyllithium", "sec-butyllithium", "MeLi", "methyllithium",
    "PhLi", "phenyllithium", "EtMgBr", "ethylmagnesium bromide",
]


@pytest.mark.parametrize("name", _FILLS_ENOLIZING_BASE)
def test_recognized_enolizing_bases_fill_the_role(name):
    assert ActivatorRole.ENOLIZING_BASE in classify_activator_roles(name)


@pytest.mark.parametrize("name", _MUST_NOT_FILL)
def test_weak_or_nonbase_or_junk_fills_no_role(name):
    assert classify_activator_roles(name) == frozenset()


# --------------------------------------------------------------------------- hydrogenation catalyst role (XI)

_FILLS_METAL_CATALYST = [
    "Pd/C", "palladium on carbon", "palladium/carbon", "Pd", "palladium", "Pd(OH)2", "Pearlman's catalyst",
    "PtO2", "platinum oxide", "Adams' catalyst", "Pt", "platinum", "Raney nickel", "Raney Ni", "nickel",
    "Rh", "rhodium", "Wilkinson's catalyst", "Ru", "ruthenium",
]

#: must NOT fill TRANSITION_METAL_CATALYST -- non-catalysts, a base (fills the OTHER role, not this one), wrong case.
_MUST_NOT_FILL_METAL_CATALYST = ["water", "acetic acid", "NaOEt", "sulfuric acid", "pD", "PT", "", "palladium-free"]


@pytest.mark.parametrize("name", _FILLS_METAL_CATALYST)
def test_recognized_hydrogenation_catalysts_fill_the_catalyst_role_only(name):
    roles = classify_activator_roles(name)
    assert ActivatorRole.TRANSITION_METAL_CATALYST in roles
    assert ActivatorRole.ENOLIZING_BASE not in roles          # a catalyst is not a base -- distinct roles


@pytest.mark.parametrize("name", _MUST_NOT_FILL_METAL_CATALYST)
def test_noncatalyst_or_wrongcase_fills_no_catalyst_role(name):
    assert ActivatorRole.TRANSITION_METAL_CATALYST not in classify_activator_roles(name)


def _hydrogenation(catalysts=None):
    # ethylene + H2 -> ethane: the recognized H2-consuming hydrogenation class.
    return _step(("C=C", "[H][H]"), ("CC",), catalysts=catalysts)


def test_hydrogenation_recognized_and_demoted_without_a_catalyst():
    step = _hydrogenation()
    assert recognize_reaction_type(step) == _HYDROGENATION       # type-validity holds ...
    assert step_activator_blockers(step)                         # ... but no catalyst declared -> REAL_BUT_HARD


def test_hydrogenation_catalyst_declared_clears_the_activator_requirement():
    # a declared metal catalyst MEETS the ledger requirement (the activator channel clears); its INDUSTRIAL
    # obtainability is catalyst_availability's separate gate, so the two compose to REAL_BUT_HARD, never false-CLEAN.
    from smartchem.experiment.catalyst_availability import route_catalyst_blockers
    from smartchem.experiment.step import ROUTE_SCHEMA, ExperimentRoute
    step = _hydrogenation(catalysts=("Pd/C",))
    assert step_activator_blockers(step) == ()                   # requirement met
    assert route_catalyst_blockers(ExperimentRoute(ROUTE_SCHEMA, (step,)))  # ... but Pd/C is INDUSTRIAL (separate gate)


def test_hydrogenation_noncatalyst_condition_stays_demoted():
    assert step_activator_blockers(_hydrogenation(catalysts=("water",)))  # water is not a hydrogenation catalyst


@pytest.mark.parametrize("bad", [None, 123, 1.5, b"NaOEt", ["NaOEt"], object()])
def test_non_string_fills_no_role_fail_closed(bad):
    assert classify_activator_roles(bad) == frozenset()


def test_case_ambiguous_token_does_not_clear():
    # Na2CO3 (carbonate) is not a base in the whitelist at all; but the case guard must also refuse a token whose
    # alternate case reading is a DIFFERENT species. "na2co3" never clears regardless (double safety).
    assert classify_activator_roles("na2co3") == frozenset()
    assert classify_activator_roles("Na2CO3") == frozenset()


# --------------------------------------------------------------------------- step-level demotion

def test_claisen_without_any_declared_base_is_demoted():
    blockers = step_activator_blockers(_claisen())
    assert len(blockers) == 1
    reason = blockers[0]
    assert "activator not declared" in reason
    assert "enolizing base" in reason
    # honest, recoverable, NOT a fiction/impossibility claim
    assert "type-validity holds" in reason
    assert "NOT a claim of" in reason and "impossibility" in reason


@pytest.mark.parametrize("base", ["sodium ethoxide", "NaOEt", "NaH", "LDA", "potassium tert-butoxide"])
def test_claisen_with_a_recognized_enolizing_base_is_cleared(base):
    assert step_activator_blockers(_claisen(catalysts=(base,))) == ()


@pytest.mark.parametrize("weak", ["NaOH", "NaHCO3", "pyridine", "triethylamine", "sulfuric acid"])
def test_claisen_with_only_a_weak_or_wrong_reagent_stays_demoted(weak):
    assert len(step_activator_blockers(_claisen(catalysts=(weak,)))) == 1


def test_claisen_cleared_when_strong_base_present_among_several_reagents():
    assert step_activator_blockers(_claisen(catalysts=("ethanol", "sodium ethoxide"))) == ()


def test_fischer_esterification_is_not_demoted_the_base_rate_trap():
    assert recognize_reaction_type(_fischer()) == "acyl condensation (esterification/amidation)"
    assert step_activator_blockers(_fischer()) == ()


def test_diels_alder_is_not_demoted():
    assert step_activator_blockers(_diels_alder()) == ()


def test_unrecognized_step_is_not_our_concern():
    # A conserved, formula-balanced non-reaction (ethanol -> ethene + water): recognized by nothing -> the oracle's
    # route_reaction_type_blockers demotes it, the activator ledger stays silent (it speaks only about classes it has
    # a requirement for).
    junk = _step(("CCO",), ("C=C", "O"))
    assert recognize_reaction_type(junk) is None
    assert step_activator_blockers(junk) == ()


# --------------------------------------------------------------------------- content-determinism

def test_forged_reaction_centre_buys_nothing():
    # The check reads the envelope, never the (forgeable, compare=False) reaction_center. A baseless Claisen stays
    # demoted whether or not a centre is attached.
    plain = _claisen()
    forged = dataclasses.replace(plain, reaction_center=_DA_CENTER)
    assert step_activator_blockers(plain) == step_activator_blockers(forged)
    assert len(step_activator_blockers(forged)) == 1


# --------------------------------------------------------------------------- route level

def test_route_blockers_are_deduplicated_and_sorted():
    # Two identical baseless Claisen steps -> ONE deduplicated reason.
    class R:
        steps = (_claisen(), _claisen())
    out = route_activator_blockers(R)
    assert len(out) == 1
    assert list(out) == sorted(out)


def test_zero_step_route_is_vacuously_unblocked():
    class R:
        steps = ()
    assert route_activator_blockers(R) == ()


def test_route_is_total_and_fail_closed_on_a_raising_step():
    class Boom:
        @property
        def envelope(self):
            raise RuntimeError("boom")
    class R:
        steps = (Boom(),)
    # a step whose recognition/access raises must not crash the route and must not spuriously clear anything
    assert route_activator_blockers(R) == ()


def test_mixed_route_only_the_baseless_claisen_contributes():
    class R:
        steps = (_claisen(), _fischer(), _diels_alder(), _claisen(catalysts=("NaOEt",)))
    assert len(route_activator_blockers(R)) == 1
