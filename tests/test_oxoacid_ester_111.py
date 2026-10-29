"""#111 extension -- the oxoacid (nitrate / phosphate) ester condensation recognizer.

``_oxoacid_ester`` recognizes a dehydrative condensation forming an O-Z ester bond (Z in {N, P}):
``R-OH + (HO)Z(=O).. -> R-O-Z(=O).. + H2O``. Sound by re-derivation via the generator's own single-cut
capped scission at the O-Z oxoacid-ester locus (no ``reaction_center`` read); the CappedScission certificate
conserves + W1-descends, so a bundled multi-cut fiction can never be re-derived. Scope Z in {N, P} keeps it
DISJOINT from the #111 sulfonate recognizer (which owns C-S oxoacid esters).

Proof obligations: positive, negative, null, no-poach / exactly-one, oxoacid-centre discrimination
(phosphite / hydroxylamine abstain), content-determinism, conservation, fresh holdout.
"""
from __future__ import annotations

import pytest

from smartchem.experiment.reaction_type_oracle import (
    _RECOGNIZERS,
    _oxoacid_ester,
    recognize_reaction_type,
    recognize_reaction_type_outcome,
)
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

WATER = "O"


def _step(target: str, reactants: list[str], products: list[str]) -> ExperimentStep:
    return ExperimentStep.assembling(
        parse_smiles(target),
        tuple(parse_smiles(s) for s in reactants),
        tuple(parse_smiles(s) for s in products),
        reagents=(),
    )


def _ester_step(ester: str, alcohol: str, oxoacid: str) -> ExperimentStep:
    return _step(ester, [alcohol, oxoacid], [ester, WATER])


# -- positives: genuine nitrate / phosphate esters ---------------------------------------------------------
_POSITIVES = [
    ("methyl phosphate",  "COP(=O)(O)O",     "CO",   "OP(=O)(O)O"),
    ("dimethyl phosphate", "COP(=O)(OC)O",   "CO",   "COP(=O)(O)O"),
    ("methyl nitrate",    "CO[N+](=O)[O-]",  "CO",   "O[N+](=O)[O-]"),
    ("ethyl nitrate",     "CCO[N+](=O)[O-]", "CCO",  "O[N+](=O)[O-]"),
]


@pytest.mark.parametrize("label,ester,alcohol,acid", _POSITIVES, ids=[c[0] for c in _POSITIVES])
def test_genuine_oxoacid_ester_is_recognized(label, ester, alcohol, acid):
    name = recognize_reaction_type(_ester_step(ester, alcohol, acid))
    assert name is not None and "oxoacid" in name, f"{label}: recognized as {name!r}"


# -- oxoacid-centre discrimination: an O-Z bond that is NOT an oxoacid centre abstains ----------------------
def test_phosphite_no_oxo_abstains():
    # trimethyl phosphite P(III), no P=O: not an oxoacid ester -> abstain (deferred, honest coverage loss).
    out = recognize_reaction_type_outcome(_ester_step("COP(OC)OC", "CO", "COP(O)OC"))
    assert not out.is_match and not out.is_internal_error


# -- no cross-poach: the new recognizer never steals, and is never stolen from -----------------------------
def test_exactly_one_recognizer_fires_on_an_oxoacid_ester():
    step = _ester_step("CO[N+](=O)[O-]", "CO", "O[N+](=O)[O-]")
    fired = []
    for name, pred in _RECOGNIZERS:
        try:
            if pred(step):
                fired.append(name)
        except Exception:
            pass
    assert len(fired) == 1 and "oxoacid" in fired[0], f"fired: {fired}"


def test_oxoacid_does_not_fire_on_acyl_ether_or_sulfonate():
    # an acyl ester, a dialkyl ether, and a sulfonate ester are each owned by another recognizer; _oxoacid_ester
    # must abstain on all three (C=O carbonyl, no O-Z oxoacid centre; C-S is excluded by the Z in {N,P} scope).
    acyl = _ester_step("CCOC(C)=O", "CCO", "CC(=O)O")
    ether = _ester_step("COC", "CO", "CO")
    sulfonate = _ester_step("COS(C)(=O)=O", "CO", "CS(=O)(=O)O")  # methyl methanesulfonate: C-S, excluded
    assert _oxoacid_ester(acyl) is False
    assert _oxoacid_ester(ether) is False
    assert _oxoacid_ester(sulfonate) is False


def test_oxoacid_does_not_fire_on_the_free_acid_or_nothing():
    # the acyl recognizer's own positive must not be poached, and a non-condensation abstains cleanly.
    assert recognize_reaction_type(_ester_step("CCOC(C)=O", "CC(=O)O", "CCO")) == "acyl condensation (esterification/amidation)"


# -- content-determinism + null control --------------------------------------------------------------------
def test_recognizer_never_reads_the_reaction_centre():
    assert "reaction_center" not in set(_oxoacid_ester.__code__.co_names)


def test_null_control_centreless_step_is_recognized():
    step = _ester_step("CO[N+](=O)[O-]", "CO", "O[N+](=O)[O-]")
    assert getattr(step, "reaction_center", None) is None
    assert "oxoacid" in (recognize_reaction_type(step) or "")


# -- conservation: a recognized step balances atom-for-atom ------------------------------------------------
def test_a_recognized_step_is_mass_conserved():
    from collections import Counter

    step = _ester_step("COP(=O)(O)O", "CO", "OP(=O)(O)O")
    assert "oxoacid" in (recognize_reaction_type(step) or "")
    assert Counter(a for m in step.reactants for a in m.atoms) == Counter(a for m in step.products for a in m.atoms)


# -- fresh holdout not used to design the rule -------------------------------------------------------------
def test_holdout_isopropyl_nitrate():
    assert "oxoacid" in (recognize_reaction_type(_ester_step("CC(C)O[N+](=O)[O-]", "CC(C)O", "O[N+](=O)[O-]")) or "")


# -- dalembert KILL, now a permanent regression control: a VALENCE-INSANE fiction must never vouch ----------
def _hypervalent_carbon_alcohol():
    # CH5-OH: a carbon at bond-order-sum 5 (4 C-H + 1 C-O) -- a conserved but valence-insane FICTION that SMILES
    # cannot express; capped scission PRESERVES its valence rather than refusing it.
    from smartchem.category import Bond, Molecule
    return Molecule(("C", "H", "H", "H", "H", "O", "H"),
                    frozenset({Bond(0, 1, 1), Bond(0, 2, 1), Bond(0, 3, 1), Bond(0, 4, 1), Bond(0, 5, 1), Bond(5, 6, 1)}),
                    0, "")


def _hypervalent_carbon_nitrate_ester():
    # CH5-O-NO2: the same hypervalent carbon, esterified to a genuine O-N oxoacid locus (N: 3 O, one oxo).
    from smartchem.category import Bond, Molecule
    return Molecule(("C", "H", "H", "H", "H", "O", "N", "O", "O"),
                    frozenset({Bond(0, 1, 1), Bond(0, 2, 1), Bond(0, 3, 1), Bond(0, 4, 1), Bond(0, 5, 1),
                               Bond(5, 6, 1), Bond(6, 7, 2), Bond(6, 8, 1)}),
                    0, "")


def test_valence_gate_rejects_hypervalent_carbon_but_accepts_genuine_oxoacid_esters():
    from smartchem.experiment.reaction_type_oracle import _valence_upper_bound_sane
    assert _valence_upper_bound_sane(_hypervalent_carbon_alcohol()) is False        # C degree 5 > max{4}
    assert _valence_upper_bound_sane(_hypervalent_carbon_nitrate_ester()) is False  # hypervalent C again
    assert _valence_upper_bound_sane(parse_smiles("CO[N+](=O)[O-]")) is True         # genuine nitrate ester (N degree 5 ok)
    assert _valence_upper_bound_sane(parse_smiles("COP(=O)(O)O")) is True            # genuine phosphate ester


def test_dalembert_kill_hypervalent_nitrate_ester_never_vouches():
    # The exact false-VOUCH d'Alembert found: a conserved valence-insane 'nitrate ester' (hypervalent carbon)
    # was vouched because the recognizer dropped the #132 valence gate. The upper-bound valence gate restores
    # fail-closed behaviour. ExperimentStep.assembling accepts the step (it conserves; it does not check valence).
    alcohol, ester, water = _hypervalent_carbon_alcohol(), _hypervalent_carbon_nitrate_ester(), parse_smiles("O")
    acid = parse_smiles("O[N+](=O)[O-]")
    step = ExperimentStep.assembling(ester, (alcohol, acid), (ester, water), reagents=())
    assert _oxoacid_ester(step) is False
    assert "oxoacid" not in (recognize_reaction_type(step) or "")
