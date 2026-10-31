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
    clear the ENOLIZING requirement (over-recognizing a base is the unsafe direction) -- though such a mild base DOES
    clear the separate, pKa-regime-aware ACIDIC_PROTON_BASE requirement of a carboxylic-acid / phenol SN2 (1.5);
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
from smartchem.experiment.reaction_type_oracle import (
    _RECOGNIZERS,
    recognize_reaction_type,
    sn2_oxygen_base_regime,
)
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


def test_class_keyed_ledger_is_claisen_only():
    # A DELIBERATE set. The CLASS-KEYED ledger carries ONLY a requirement universal across EVERY instance of the
    # class -- today exactly the Claisen condensation's enolizing base. Hydrogenation was MOVED to a step-CONDITIONAL
    # requirement (OPERATION XII 1A): its H2-activation need splits by the reduced bond -- a C=N/C#N reduction admits
    # a metal-free FLP catalyst (Stephan 2007), a C=C/C=O one does not -- so a blanket class-keyed TRANSITION_METAL
    # entry would be exactly the false universal the metal-free counterexample refutes. SN2 is likewise conditional.
    assert set(REQUIRED_ACTIVATORS) == {CLAISEN}
    assert REQUIRED_ACTIVATORS[CLAISEN] == frozenset({ActivatorRole.ENOLIZING_BASE})
    assert _HYDROGENATION not in REQUIRED_ACTIVATORS


def test_every_ledger_key_is_a_live_oracle_class_name():
    live = {name for name, _pred in _RECOGNIZERS}
    assert set(REQUIRED_ACTIVATORS) <= live, "a ledger key is not a current oracle display name (rename drift)"


def test_registry_fingerprint_guard_is_armed_and_matches_live_registry():
    # The growth guard: the reviewed snapshot must equal the live 24-class registry, and the guard must pass on it.
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


def test_only_claisen_carries_a_class_keyed_requirement():
    # The base-rate guard, proven over the WHOLE registry without constructing a step per class: every class but
    # Claisen must map to an empty CLASS-KEYED requirement, so no pericyclic / Fischer / activated-acyl /
    # oxoacid-ester / hydrogenation / SN2 step is ever demoted by the blanket dict (the conditional ones key on the
    # step, tested separately).
    carriers = {CLAISEN}
    for name, _pred in _RECOGNIZERS:
        required = REQUIRED_ACTIVATORS.get(name, frozenset())
        if name in carriers:
            assert required
        else:
            assert required == frozenset(), f"{name!r} unexpectedly class-keyed -- false-EXCLUDE risk"


# --------------------------------------------------------------------------- role classifier

_FILLS_ENOLIZING_BASE = [
    "sodium ethoxide", "NaOEt", "sodium methoxide", "NaOMe", "potassium tert-butoxide", "KOtBu",
    "t-BuOK", "tBuOK", "sodium tert-butoxide", "NaH", "sodium hydride", "KH", "LDA", "lithium diisopropylamide",
    "sodium amide", "NaNH2", "LiHMDS", "LiTMP", "KDA",
]

#: must NEVER fill ENOLIZING_BASE (the invariant unchanged by the 1.5 acidic-oxygen refinement). Weak/mild bases
#: (cannot reliably enolize an ester alpha-C), NUCLEOPHILIC organometallics (strong but 1,2-add to the carbonyl
#: rather than enolize it -- the d'Alembert #107 kill), non-bases, and junk. A mild base added for the acidic-oxygen
#: SN2 (NaOH / K2CO3 / Et3N) fills the SEPARATE ACIDIC_PROTON_BASE role -- which is exactly why it must NOT leak into
#: the enolizing role (that would re-open the Claisen false-CLEAR).
_MUST_NOT_FILL_ENOLIZING = [
    "NaOH", "KOH", "sodium hydroxide", "Na2CO3", "K2CO3", "NaHCO3", "sodium bicarbonate",
    "pyridine", "triethylamine", "Et3N", "DBU", "ammonia", "sodium acetate", "water", "acetic acid",
    "sulfuric acid", "base-free", "", "   ",
    "n-BuLi", "s-BuLi", "t-BuLi", "tert-butyllithium", "sec-butyllithium", "MeLi", "methyllithium",
    "PhLi", "phenyllithium", "EtMgBr", "ethylmagnesium bromide",
]

#: fill the ACIDIC_PROTON_BASE role (a mild base competent to deprotonate a carboxylic acid / phenol for an SN2) --
#: AND must NOT fill ENOLIZING_BASE (they cannot enolize an ester). The new 1.5 capability.
_FILLS_ACIDIC_PROTON_BASE = [
    "K2CO3", "potassium carbonate", "Cs2CO3", "cesium carbonate", "Na2CO3", "sodium carbonate",
    "NaOH", "sodium hydroxide", "KOH", "LiOH", "K3PO4", "potassium phosphate",
    "Et3N", "triethylamine", "DIPEA", "diisopropylethylamine", "DBU", "TMG",
]

#: must fill NO activator role at all -- non-bases, junk, nucleophilic organometallics, AND the deliberately-omitted
#: WEAK bases that are too weak to deprotonate a phenol (bicarbonate pKaH ~6.3, pyridine ~5): the conservative
#: boundary of the acidic-oxygen clearing set (a SAFE under-claim). An entry here fills neither role -> clears nothing.
_FILLS_NO_ROLE_AT_ALL = [
    "NaHCO3", "sodium bicarbonate", "pyridine", "ammonia", "sodium acetate", "water", "acetic acid",
    "sulfuric acid", "base-free", "", "   ",
    "n-BuLi", "t-BuLi", "tert-butyllithium", "MeLi", "methyllithium", "PhLi", "EtMgBr", "ethylmagnesium bromide",
]


@pytest.mark.parametrize("name", _FILLS_ENOLIZING_BASE)
def test_recognized_enolizing_bases_fill_the_role(name):
    assert ActivatorRole.ENOLIZING_BASE in classify_activator_roles(name)


@pytest.mark.parametrize("name", _MUST_NOT_FILL_ENOLIZING)
def test_weak_or_nonbase_or_junk_never_fills_the_enolizing_role(name):
    assert ActivatorRole.ENOLIZING_BASE not in classify_activator_roles(name)


@pytest.mark.parametrize("name", _FILLS_ACIDIC_PROTON_BASE)
def test_mild_bases_fill_the_acidic_proton_role_only(name):
    roles = classify_activator_roles(name)
    assert ActivatorRole.ACIDIC_PROTON_BASE in roles, f"{name!r} should fill ACIDIC_PROTON_BASE"
    assert ActivatorRole.ENOLIZING_BASE not in roles, f"{name!r} must NOT leak into ENOLIZING_BASE"


@pytest.mark.parametrize("name", _FILLS_NO_ROLE_AT_ALL)
def test_nonbase_junk_and_too_weak_bases_fill_no_role(name):
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
    assert ActivatorRole.HYDROGEN_ACTIVATION_CATALYST in roles  # a TM metal clears the C=N requirement a fortiori
    assert ActivatorRole.ENOLIZING_BASE not in roles          # a catalyst is not a base -- distinct roles


@pytest.mark.parametrize("name", _MUST_NOT_FILL_METAL_CATALYST)
def test_noncatalyst_or_wrongcase_fills_no_catalyst_role(name):
    roles = classify_activator_roles(name)
    assert ActivatorRole.TRANSITION_METAL_CATALYST not in roles
    assert ActivatorRole.HYDROGEN_ACTIVATION_CATALYST not in roles  # a non-catalyst fills NEITHER H2-activation role


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


# ----------------------------------------- metal-free H2 activation: the C=N / C#N correction (OPERATION XII 1A)
# Refutes the universal "a hydrogenation needs a transition metal". A C=N / C#N reduction is catalysed METAL-FREE by
# a frustrated Lewis pair (Chase, Welch, Jurca & Stephan, Angew. Chem. Int. Ed. 2007, 46, 8050, DOI
# 10.1002/anie.200702908 -- imines + lone-pair-sequestered nitriles, NOT aldehydes). The fix must CLEAR that case
# under a metal-free catalyst WITHOUT ever clearing C=C / C=O (the load-bearing safe-direction boundary).

_FILLS_METAL_FREE_H2 = ["B(C6F5)3", "tris(pentafluorophenyl)borane", "tris(pentafluorophenyl)boron", "BCF"]

#: Lewis acids / reagents that are NOT validated metal-free H2-activation catalysts -> must fill NEITHER activation
#: role (BF3 / AlCl3 are Lewis acids but not FLP hydrogenation catalysts; B(C6F5)2 is a wrong/truncated formula).
_MUST_NOT_FILL_H2_ACTIVATION = ["BF3", "boron trifluoride", "AlCl3", "water", "benzene", "B(C6F5)2", ""]


@pytest.mark.parametrize("name", _FILLS_METAL_FREE_H2)
def test_metal_free_flp_fills_h2_activation_but_is_not_a_transition_metal(name):
    roles = classify_activator_roles(name)
    assert ActivatorRole.HYDROGEN_ACTIVATION_CATALYST in roles
    assert ActivatorRole.TRANSITION_METAL_CATALYST not in roles  # METAL-free: the sets are DISJOINT, the whole point
    assert ActivatorRole.ENOLIZING_BASE not in roles


@pytest.mark.parametrize("name", _MUST_NOT_FILL_H2_ACTIVATION)
def test_non_h2_catalyst_fills_no_activation_role(name):
    roles = classify_activator_roles(name)
    assert ActivatorRole.HYDROGEN_ACTIVATION_CATALYST not in roles
    assert ActivatorRole.TRANSITION_METAL_CATALYST not in roles


def _imine_hydrogenation(catalysts=None):
    # methanimine CH2=NH + H2 -> methylamine CH3NH2: a recognized C=N reduction (the metal-free-FLP domain).
    return _step(("C=N", "[H][H]"), ("CN",), catalysts=catalysts)


def _nitrile_hydrogenation(catalysts=None):
    # acetonitrile CH3C#N + H2 -> ethanimine CH3CH=NH: a recognized C#N partial reduction (metal-free-FLP domain).
    return _step(("CC#N", "[H][H]"), ("CC=N",), catalysts=catalysts)


def _carbonyl_hydrogenation(catalysts=None):
    # acetaldehyde CH3CHO + H2 -> ethanol: a C=O reduction. NO metal-free catalytic route (Stephan 2007: aldehydes
    # do not react under FLP catalysis), so it must keep the TM-only requirement.
    return _step(("CC=O", "[H][H]"), ("CCO",), catalysts=catalysts)


def test_hydrogenation_reduced_bond_elements_reports_the_reduced_unsaturation():
    from smartchem.experiment.reaction_type_oracle import hydrogenation_reduced_bond_elements
    assert hydrogenation_reduced_bond_elements(_imine_hydrogenation()) == frozenset({"C", "N"})
    assert hydrogenation_reduced_bond_elements(_nitrile_hydrogenation()) == frozenset({"C", "N"})
    assert hydrogenation_reduced_bond_elements(_hydrogenation()) == frozenset({"C"})            # alkene C=C
    assert hydrogenation_reduced_bond_elements(_carbonyl_hydrogenation()) == frozenset({"C", "O"})
    assert hydrogenation_reduced_bond_elements(_diels_alder()) is None                          # not a hydrogenation


def test_imine_hydrogenation_demoted_catalyst_free():
    step = _imine_hydrogenation()
    assert recognize_reaction_type(step) == _HYDROGENATION       # type-validity holds ...
    assert step_activator_blockers(step)                         # ... C=N needs an H2-activation catalyst


def test_imine_hydrogenation_cleared_by_a_metal_free_flp():
    # THE Stephan-2007 correction: a metal-free FLP MEETS the H2-activation requirement for a C=N reduction, so the
    # model no longer falsely asserts "only a transition metal can do this".
    assert step_activator_blockers(_imine_hydrogenation(catalysts=("B(C6F5)3",))) == ()


def test_imine_hydrogenation_cleared_by_a_transition_metal_a_fortiori():
    assert step_activator_blockers(_imine_hydrogenation(catalysts=("Pd/C",))) == ()


def test_nitrile_hydrogenation_cleared_by_a_metal_free_flp():
    assert step_activator_blockers(_nitrile_hydrogenation(catalysts=("B(C6F5)3",))) == ()


def test_metal_free_flp_does_not_clear_a_cc_hydrogenation():
    # LOAD-BEARING safe boundary: FLP alkene hydrogenation is not a supported general route, so a C=C reduction
    # stays demoted under B(C6F5)3 -- the metal-free set is ABSENT from the C=C (TRANSITION_METAL_CATALYST) role.
    assert step_activator_blockers(_hydrogenation(catalysts=("B(C6F5)3",)))  # ethylene + H2 -> ethane, still blocked


def test_metal_free_flp_does_not_clear_a_carbonyl_hydrogenation():
    # Stephan 2007: aldehydes do NOT undergo metal-free catalytic hydrogenation -> a C=O reduction keeps TM-only.
    assert step_activator_blockers(_carbonyl_hydrogenation(catalysts=("B(C6F5)3",)))


def test_carbonyl_hydrogenation_cleared_by_a_transition_metal():
    assert step_activator_blockers(_carbonyl_hydrogenation(catalysts=("Pd/C",))) == ()


# ---- the C=N / C#N witness is NARROWER than the element pair {C,N} (evil-morty, OPERATION XII 1A) ----
# A C=N bond is not the exclusive property of an imine: an oxime (N-O), a hydrazone / azine (N-N), an amidine
# (C bearing a 2nd N), and the isocyanate / carbodiimide CUMULENES (C with a 2nd multiple bond) all reduce through a
# C=N yet are NOT metal-free-FLP substrates. They must keep TM-only -- a metal-free FLP must NOT clear them (that was
# the one false-CLEAR evil-morty proved against the first cut, now closed by a structural witness).

_NON_IMINE_CN_HYDROGENATIONS = {
    "oxime        CC=NO -> CCNO":     (("CC=NO", "[H][H]"), ("CCNO",)),
    "hydrazone    C=NN  -> CNN":      (("C=NN", "[H][H]"), ("CNN",)),
    "amidine      CC(=N)N -> CC(N)N": (("CC(=N)N", "[H][H]"), ("CC(N)N",)),
    "isocyanate   O=C=N -> O=CN":     (("O=C=N", "[H][H]"), ("O=CN",)),
    "carbodiimide N=C=N -> N=CN":     (("N=C=N", "[H][H]"), ("N=CN",)),
}


@pytest.mark.parametrize("label", list(_NON_IMINE_CN_HYDROGENATIONS))
def test_decorated_cn_is_not_cleared_by_a_metal_free_flp(label):
    from smartchem.experiment.reaction_type_oracle import (
        hydrogenation_reduced_bond_elements,
        hydrogenation_reduces_imine_or_nitrile,
    )
    rs, ps = _NON_IMINE_CN_HYDROGENATIONS[label]
    step = _step(rs, ps)
    assert recognize_reaction_type(step) == _HYDROGENATION                     # a recognized hydrogenation ...
    assert hydrogenation_reduced_bond_elements(step) == frozenset({"C", "N"})  # ... reducing a C=N bond ...
    assert not hydrogenation_reduces_imine_or_nitrile(step)                    # ... but NOT a genuine imine / nitrile
    assert step_activator_blockers(_step(rs, ps, catalysts=("B(C6F5)3",)))     # metal-free FLP does NOT clear it
    assert step_activator_blockers(_step(rs, ps, catalysts=("Pd/C",))) == ()   # a transition metal clears a fortiori


def test_hydrogenation_reduces_imine_or_nitrile_is_a_narrow_structural_witness():
    from smartchem.experiment.reaction_type_oracle import hydrogenation_reduces_imine_or_nitrile
    assert hydrogenation_reduces_imine_or_nitrile(_imine_hydrogenation())        # C=N imine     -> True
    assert hydrogenation_reduces_imine_or_nitrile(_nitrile_hydrogenation())      # C#N nitrile   -> True
    assert not hydrogenation_reduces_imine_or_nitrile(_hydrogenation())          # alkene C=C    -> False
    assert not hydrogenation_reduces_imine_or_nitrile(_carbonyl_hydrogenation()) # carbonyl C=O  -> False
    assert not hydrogenation_reduces_imine_or_nitrile(_diels_alder())            # not a hydrogenation -> False
    for rs, ps in _NON_IMINE_CN_HYDROGENATIONS.values():
        assert not hydrogenation_reduces_imine_or_nitrile(_step(rs, ps))         # every decorated C=N -> False


@pytest.mark.parametrize("bad", [None, 123, 1.5, b"NaOEt", ["NaOEt"], object()])
def test_non_string_fills_no_role_fail_closed(bad):
    assert classify_activator_roles(bad) == frozenset()


def test_case_ambiguous_token_does_not_clear():
    # Na2CO3 (sodium carbonate) IS a mild base in the acidic-oxygen whitelist (1.5), so the HONEST spelling clears;
    # but the all-lowercase "na2co3" is case-ambiguous (it could read as the cobalt salt Na2Co3), so the case guard
    # refuses it -- the whole point of case-certification applied to a name that IS in the whitelist.
    assert ActivatorRole.ACIDIC_PROTON_BASE in classify_activator_roles("Na2CO3")  # honest spelling certifies
    assert classify_activator_roles("na2co3") == frozenset()  # ambiguous case -> refused (could be Na2Co3)


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


# -- #112 SN2 conditional activator (1.5 consolidation; closes the evil-morty neutral-alcohol capability over-claim).
# The requirement is CONDITIONAL on the step's nucleophile (not class-keyed): a NEUTRAL oxygen nucleophile (an
# alcohol R-O-H) needs a stoichiometric base to form the alkoxide in situ (Williamson), so a baseless such step is
# demoted REAL-BUT-HARD; a salt alkoxide, a neutral amine and a neutral thiol are competent and get no requirement.
SN2 = "SN2 substitution"


def _sn2_neutral_alcohol(catalysts=None):
    # EtBr + EtOH -> Et2O + HBr : a neutral OXYGEN nucleophile (coproduct H-Br), the kill case.
    return _step(("CCBr", "CCO"), ("CCOCC", "Br"), catalysts=catalysts)


def test_sn2_neutral_alcohol_recognition_is_untouched():
    assert SN2 in recognize_reaction_type(_sn2_neutral_alcohol())  # Problem A (type-validity) unchanged by the fix


def test_sn2_neutral_alcohol_without_base_is_demoted():
    reasons = step_activator_blockers(_sn2_neutral_alcohol())
    assert len(reasons) == 1 and "activator not declared" in reasons[0] and "alkoxide" in reasons[0]


@pytest.mark.parametrize("base", ["NaOEt", "sodium ethoxide", "NaH", "LDA", "potassium tert-butoxide"])
def test_sn2_neutral_alcohol_with_a_declared_base_clears(base):
    assert step_activator_blockers(_sn2_neutral_alcohol(catalysts=(base,))) == ()  # recoverable demotion


@pytest.mark.parametrize("weak", ["water", "acetic acid", "pyridine", "triethylamine"])
def test_sn2_neutral_alcohol_with_a_weak_base_stays_demoted(weak):
    assert len(step_activator_blockers(_sn2_neutral_alcohol(catalysts=(weak,)))) == 1  # conservative clearing set


def test_sn2_salt_alkoxide_needs_no_base():
    step = _step(("CCBr", "CCO[Na]"), ("CCOCC", "[Na]Br"))  # the alkoxide IS the competent nucleophile
    assert SN2 in recognize_reaction_type(step) and step_activator_blockers(step) == ()


def test_sn2_neutral_amine_needs_no_base():
    step = _step(("CCBr", "CN"), ("CCNC", "Br"))  # a neutral amine is itself a competent nucleophile
    assert SN2 in recognize_reaction_type(step) and step_activator_blockers(step) == ()


def test_sn2_neutral_thiol_needs_no_base():
    step = _step(("CCBr", "CCS"), ("CCSCC", "Br"))  # neutral thiols react base-free: demoting would false-EXCLUDE
    assert SN2 in recognize_reaction_type(step) and step_activator_blockers(step) == ()


def test_deprotonating_base_role_whitelist():
    assert ActivatorRole.DEPROTONATING_BASE in classify_activator_roles("NaOEt")
    assert ActivatorRole.DEPROTONATING_BASE in classify_activator_roles("NaH")
    assert ActivatorRole.DEPROTONATING_BASE not in classify_activator_roles("water")


def test_sn2_requirement_is_conditional_not_class_keyed():
    # a blanket REQUIRED_ACTIVATORS entry would false-EXCLUDE the salt/amine/thiol sub-populations.
    assert not any("SN2" in k for k in REQUIRED_ACTIVATORS)


# -- #112 SN2 pKa-regime refinement (1.5 consolidation; closes the evil-morty acidic-oxygen SAFE under-claim).
# The neutral-oxygen SN2 base requirement is split by the nucleophile's pKa regime (sn2_oxygen_base_regime): an
# ALCOHOL (sp3 C-O-H, pKa ~16) needs a STRONG base; an ACIDIC oxygen -- a carboxylic acid (pKa ~5) or a phenol
# (pKa ~10), sp2 C-O-H -- needs only a MILD base. The load-bearing asymmetry: a mild base clears the acidic case but
# NEVER the alcohol case (the unsafe direction stays closed).
def _sn2_carboxylic_acid(catalysts=None):
    # AcOH + EtBr -> ethyl acetate + HBr: a neutral OXYGEN nucleophile whose O-H is a carboxylic acid (pKa ~5).
    return _step(("CCBr", "CC(=O)O"), ("CC(=O)OCC", "Br"), catalysts=catalysts)


def _sn2_phenol(catalysts=None):
    # PhOH + MeBr -> anisole + HBr: a neutral OXYGEN nucleophile whose O-H is a phenol (pKa ~10).
    return _step(("CBr", "Oc1ccccc1"), ("COc1ccccc1", "Br"), catalysts=catalysts)


@pytest.mark.parametrize("stepf", [_sn2_carboxylic_acid, _sn2_phenol], ids=["carboxylic-acid", "phenol"])
def test_acidic_oxygen_sn2_recognition_is_untouched(stepf):
    assert SN2 in recognize_reaction_type(stepf())  # Problem A unchanged -- still a vouched SN2


@pytest.mark.parametrize("stepf", [_sn2_carboxylic_acid, _sn2_phenol], ids=["carboxylic-acid", "phenol"])
def test_acidic_oxygen_sn2_without_a_base_is_demoted(stepf):
    reasons = step_activator_blockers(stepf())
    assert len(reasons) == 1 and "activator not declared" in reasons[0] and "acidic oxygen" in reasons[0]


@pytest.mark.parametrize("stepf", [_sn2_carboxylic_acid, _sn2_phenol], ids=["carboxylic-acid", "phenol"])
@pytest.mark.parametrize("mild", ["K2CO3", "potassium carbonate", "Cs2CO3", "NaOH", "sodium hydroxide",
                                  "K3PO4", "Et3N", "triethylamine", "DIPEA", "DBU"])
def test_acidic_oxygen_sn2_clears_with_a_mild_base(stepf, mild):
    assert step_activator_blockers(stepf(catalysts=(mild,))) == ()  # a mild base forms the carboxylate/phenoxide


@pytest.mark.parametrize("stepf", [_sn2_carboxylic_acid, _sn2_phenol], ids=["carboxylic-acid", "phenol"])
@pytest.mark.parametrize("strong", ["NaOEt", "NaH", "LDA"])
def test_acidic_oxygen_sn2_clears_with_a_strong_base_a_fortiori(stepf, strong):
    assert step_activator_blockers(stepf(catalysts=(strong,))) == ()  # a strong base clears it too


@pytest.mark.parametrize("stepf", [_sn2_carboxylic_acid, _sn2_phenol], ids=["carboxylic-acid", "phenol"])
@pytest.mark.parametrize("tooweak", ["NaHCO3", "sodium bicarbonate", "pyridine", "water", "acetic acid"])
def test_acidic_oxygen_sn2_stays_demoted_with_a_too_weak_or_nonbase(stepf, tooweak):
    # conservative clearing set: bicarbonate (too weak for a phenol) and non-bases do NOT clear -- a SAFE under-claim.
    assert len(step_activator_blockers(stepf(catalysts=(tooweak,)))) == 1


# THE load-bearing safety regression: a MILD base must NEVER clear the sp3-ALCOHOL SN2 (it cannot form the alkoxide).
@pytest.mark.parametrize("mild", ["K2CO3", "potassium carbonate", "NaOH", "sodium hydroxide", "Et3N", "DBU", "DIPEA"])
def test_alcohol_sn2_is_NOT_cleared_by_a_mild_base(mild):
    reasons = step_activator_blockers(_sn2_neutral_alcohol(catalysts=(mild,)))
    assert len(reasons) == 1 and "alkoxide" in reasons[0]  # still the STRONG (alkoxide) requirement, unmet


def test_acidic_proton_base_role_whitelist():
    assert ActivatorRole.ACIDIC_PROTON_BASE in classify_activator_roles("K2CO3")
    assert ActivatorRole.ACIDIC_PROTON_BASE in classify_activator_roles("Et3N")
    assert ActivatorRole.ACIDIC_PROTON_BASE in classify_activator_roles("NaOEt")  # a strong base clears it a fortiori
    assert ActivatorRole.ACIDIC_PROTON_BASE not in classify_activator_roles("NaHCO3")  # too weak -> no role
    assert ActivatorRole.ACIDIC_PROTON_BASE not in classify_activator_roles("water")


@pytest.mark.parametrize("stepf,expected", [
    (_sn2_carboxylic_acid, "mild"),
    (_sn2_phenol, "mild"),
    (_sn2_neutral_alcohol, "strong"),
])
def test_oxygen_base_regime_classifier(stepf, expected):
    assert sn2_oxygen_base_regime(stepf()) == expected


def test_benzyl_alcohol_sn2_is_strong_regime_not_fooled_by_the_ring():
    # benzyl alcohol's O-H is on an sp3 CH2 (pKa ~15), NOT the aromatic ring: the regime keys on the HYDROXYL
    # carbon's own hybridisation, so an aromatic ring elsewhere in the molecule does not relax it to 'mild'.
    step = _step(("CBr", "OCc1ccccc1"), ("COCc1ccccc1", "Br"))
    assert sn2_oxygen_base_regime(step) == "strong"
    assert len(step_activator_blockers(step)) == 1 and "alkoxide" in step_activator_blockers(step)[0]


def test_iminol_cn_hydroxyl_is_strong_not_cleared_by_a_mild_base():
    # evil-morty re-review finding: a hydroxyl on a C=N carbon (an amide's iminol tautomer -- N-methylacetimidic
    # acid, the iminol of N-methylacetamide) is NOT carbonate-acidic (amidate pKa ~17-22; O-imidate alkylation needs
    # a strong base / Meerwein salt). The C=N partner is excluded from 'mild', so it keeps the STRONG requirement and
    # a mild base must NOT clear it (closing the false-CLEAR); a strong base still clears it (recoverable).
    step = _step(("CCBr", "CC(O)=NC"), ("CCOC(C)=NC", "Br"))
    assert SN2 in recognize_reaction_type(step)  # it DOES vouch as an SN2 (recognition untouched)
    assert sn2_oxygen_base_regime(step) == "strong"
    assert len(step_activator_blockers(step)) == 1  # baseless -> demoted
    assert len(step_activator_blockers(_step(("CCBr", "CC(O)=NC"), ("CCOC(C)=NC", "Br"), catalysts=("K2CO3",)))) == 1
    assert step_activator_blockers(_step(("CCBr", "CC(O)=NC"), ("CCOC(C)=NC", "Br"), catalysts=("NaH",))) == ()
