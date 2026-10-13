"""ISSUE #126: a caller-forged ReactionCenter must not be trusted as reaction-TYPE recognition evidence.

The hole (proven at runtime before the fix): the acyl / ether / N-alkylation recognizers read
``step.reaction_center`` as their locality/elementarity WITNESS, and
:meth:`ReactionCenter.is_elementary_condensation` inspects only the centre's OWN declared bonds -- never the
step's molecules.  So a caller who hand-builds an :class:`ExperimentStep` through the public ``assembling``
constructor could attach an *elementary* condensation centre to a balanced NON-elementary fiction (a bundled
double condensation whose true centre is non-elementary) and buy a false VOUCH.

The fix: a centre justifies a vouch ONLY when the ENGINE derived or authenticated it
(``ExperimentStep.center_trusted``, set by :meth:`from_transform` and the replay deserialization seam).  A
caller-supplied centre on a hand-built step is retained as neutral diagnostic metadata but is NOT evidence --
the recognizers fail closed on it exactly as they do on an absent centre (TAMPER-HARDENING-01).

These are fast (``capped_scissions`` + ``from_transform``), not full-compilation, regressions; the replay
round-trip of genuine recognized routes is pinned separately in ``test_poor_man_tamper_hardening.py``.
"""
from __future__ import annotations

import pytest

from smartchem.conditions import ConditionEnvelope
from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name
from smartchem.structure_descent import capped_scissions
from smartchem.reaction_center import ReactionCenter
from smartchem.experiment.step import STEP_SCHEMA, ExperimentStep, StepError
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type

_WATER = structure_by_name("water").molecule

# an elementary ester/acyl condensation centre: {C-O, O-H} formed, {C-O, O-H} broken, ONE connected component.
_FORGED_ELEMENTARY = ReactionCenter.of(
    (("C", "O", 1), ("H", "O", 1)),
    (("C", "O", 1), ("H", "O", 1)),
    1,
)


def _hand_step(reactant_smiles, product_smiles, target_smiles, center):
    """A step built through the PUBLIC general constructor with a CALLER-supplied centre (untrusted)."""
    rs = tuple(parse_smiles(s) for s in reactant_smiles)
    ps = tuple(_WATER if s == "water" else parse_smiles(s) for s in product_smiles)
    tg = parse_smiles(target_smiles)
    tt = next((x for x in ps if dict(x.formula) == dict(tg.formula) and x.charge == tg.charge), ps[0])
    return ExperimentStep.assembling(tt, rs, ps, reagents=(), envelope=ConditionEnvelope.unknown(),
                                     reaction_center=center)


def _derived_step(product_smiles, want_products, k=1):
    """A genuine ENGINE-derived step: a capped scission read backwards (centre derived from the transform)."""
    r = parse_smiles(product_smiles)
    want = sorted(parse_smiles(s).canonical().__repr__() for s in want_products)
    for cs in capped_scissions(r, tuple(parse_smiles("O") for _ in range(k)), max_reactant_cuts=k)[0]:
        if sorted(p.canonical().__repr__() for p in cs.products) == want:
            return ExperimentStep.from_transform(cs)
    raise AssertionError(f"no capped scission of {product_smiles} yields {want_products}")


# the bundled DOUBLE condensation (lactide formation): passes the whole-molecule acyl census but is NOT the
# elementary SINGLE condensation the recognizer is contracted to vouch.
_LACTIC = "CC(O)C(=O)O"
_LACTIDE = "CC1OC(=O)C(C)OC1=O"


def test_forged_elementary_center_does_not_vouch_a_bundled_fiction():
    # THE HOLE: 2 lactic acid -> lactide + 2 water, a non-elementary double condensation, with a forged elementary
    # acyl centre.  Pre-fix this VOUCHED "acyl condensation"; it must now demote.
    from smartchem.experiment.feasibility import _is_intermolecular_acyl_condensation
    step = _hand_step([_LACTIC, _LACTIC], [_LACTIDE, "water", "water"], _LACTIDE, _FORGED_ELEMENTARY)
    assert _is_intermolecular_acyl_condensation(step) is True   # the whole-molecule census still fires ...
    assert step.reaction_center is not None                     # ... the centre is retained as metadata ...
    assert step.center_trusted is False                         # ... but it is NOT trusted evidence ...
    assert recognize_reaction_type(step) is None                # ... so no VOUCH (was: acyl condensation).


def test_a_copied_genuine_center_on_a_hand_built_step_still_does_not_vouch():
    # even the EXACT centre of a genuine recognized step, copied onto a hand-built twin, confers no vouch: trust is
    # engine provenance, not the descriptor's content.  (Closes the "copy a real centre" variant of the forge.)
    for product, want in (("CC(=O)OC", ["CC(=O)O", "CO"]), ("COC", ["CO", "CO"])):
        genuine = _derived_step(product, want)
        assert genuine.center_trusted is True
        assert recognize_reaction_type(genuine) is not None            # genuine engine step vouches
        twin = ExperimentStep.assembling(genuine.target, genuine.reactants, genuine.products,
                                         reagents=genuine.reagents, envelope=genuine.envelope,
                                         reaction_center=genuine.reaction_center)   # same centre, hand-built
        assert twin.reaction_center == genuine.reaction_center         # identical descriptor ...
        assert twin.center_trusted is False                            # ... untrusted ...
        assert recognize_reaction_type(twin) is None                   # ... so no vouch.


@pytest.mark.parametrize("product,want,label", [
    ("CC(=O)OC", ["CC(=O)O", "CO"], "acyl condensation"),
    ("COC", ["CO", "CO"], "etherification"),
    ("CNc1ccccc1", ["Nc1ccccc1", "CO"], "N-alkylation"),
])
def test_genuine_engine_derived_steps_still_vouch(product, want, label):
    # no false-reject: the three centre-trusting classes still recognize their genuine ENGINE-derived instances.
    step = _derived_step(product, want)
    assert step.center_trusted is True
    vouch = recognize_reaction_type(step)
    assert vouch is not None, f"{label} genuine step lost its vouch"


def test_wrong_molecule_pairing_with_a_borrowed_center_does_not_upgrade():
    # #126 acceptance: a valid-looking acyl centre attached (untrusted) to a non-acyl pairing must not upgrade type.
    step = _hand_step(["CO", "CO"], ["COC", "water"], "COC", _FORGED_ELEMENTARY)
    assert step.center_trusted is False
    assert recognize_reaction_type(step) is None


def test_center_trusted_invariants():
    # the public general constructor leaves a supplied centre untrusted ...
    assert _hand_step([_LACTIC, _LACTIC], [_LACTIDE, "water", "water"], _LACTIDE,
                      _FORGED_ELEMENTARY).center_trusted is False
    # ... from_transform marks an engine-derived centre trusted ...
    assert _derived_step("CC(=O)OC", ["CC(=O)O", "CO"]).center_trusted is True
    # ... and a trusted flag with no centre is an incoherent state the certificate refuses.
    acid, methanol, ester = (parse_smiles(s) for s in ("CC(=O)O", "CO", "CC(=O)OC"))
    with pytest.raises(StepError):
        ExperimentStep(STEP_SCHEMA, target=ester, reactants=(acid, methanol), products=(ester, _WATER),
                       reagents=(), envelope=ConditionEnvelope.unknown(),
                       reaction_center=None, center_trusted=True)
