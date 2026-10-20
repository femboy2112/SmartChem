"""ISSUE #126 (Phase II): a caller-forged ReactionCenter must not buy a reaction-TYPE vouch, by ANY public route.

Phase I introduced a ``center_trusted`` bool gating the oracle's centre read.  A follow-up hostile audit
(GitHub #126, 2026-10-13) proved that bit forgeable: ``dataclasses.replace`` runs the public constructor, so a
caller could set ``center_trusted=True`` on a forged centre; and the public ``from_transform`` trusted any
duck-typed object's ``reaction_center()``.  A stored field is not an authentication boundary.

Phase II retires the trust bit entirely.  The condensation recognizers (acyl/ether/N-alkylation) -- the #126
forge surface -- RE-DERIVE their locality/elementarity witness from the step's own molecules (an independent
single-cut capped scission, :func:`_condensation_rederives`), so for them recognition is a pure function of the
conserved ``reactants``/``products`` content (CONTENT-DETERMINISTIC), ignoring the forgeable centre entirely.
The universal guarantee across ALL 18 recognizers: no caller-settable field can MINT a vouch -- the pericyclic
families gate on their own Layer-A re-derivation, so a forged centre can only ever DEMOTE, never upgrade a
fiction.  The forge therefore closes under direct construction, ``dataclasses.replace``, AND an arbitrary fake
transform.  (These tests exercise the condensation families, where full content-determinism holds.)

These are fast (``capped_scissions`` + ``from_transform``) regressions, not full-compilation; the replay
round-trip of genuine recognized routes is pinned separately in ``test_poor_man_tamper_hardening.py``.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from smartchem.conditions import ConditionEnvelope
from smartchem.smiles import parse_smiles, resonance_identity
from smartchem.structure import structure_by_name
from smartchem.structure_descent import capped_scissions
from smartchem.reaction_center import ReactionCenter
from smartchem.experiment.step import ExperimentStep
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type

_WATER = structure_by_name("water").molecule

# an elementary ester/acyl condensation centre: {C-O, O-H} formed, {C-O, O-H} broken, ONE connected component --
# exactly what ``is_elementary_condensation`` would have accepted when the centre was trusted.
_FORGED_ELEMENTARY = ReactionCenter.of(
    (("C", "O", 1), ("H", "O", 1)),
    (("C", "O", 1), ("H", "O", 1)),
    1,
)

# the bundled DOUBLE condensation (lactide formation): passes the whole-molecule acyl census but is NOT the
# elementary SINGLE condensation the recognizer is contracted to vouch (it needs TWO cuts).
_LACTIC = "CC(O)C(=O)O"
_LACTIDE = "CC1OC(=O)C(C)OC1=O"

_GENUINE = [
    ("CC(=O)OC", ["CC(=O)O", "CO"], "acyl condensation"),
    ("COC", ["CO", "CO"], "etherification"),
    ("CNc1ccccc1", ["Nc1ccccc1", "CO"], "N-alkylation"),
]


def _hand_step(reactant_smiles, product_smiles, target_smiles, center):
    """A step built through the PUBLIC general constructor with a CALLER-supplied centre (advisory only)."""
    rs = tuple(parse_smiles(s) for s in reactant_smiles)
    ps = tuple(_WATER if s == "water" else parse_smiles(s) for s in product_smiles)
    tg = parse_smiles(target_smiles)
    tt = next((x for x in ps if dict(x.formula) == dict(tg.formula) and x.charge == tg.charge), ps[0])
    return ExperimentStep.assembling(tt, rs, ps, reagents=(), envelope=ConditionEnvelope.unknown(),
                                     reaction_center=center)


def _derived_step(product_smiles, want_products, k=1):
    """A genuine ENGINE-derived step: a capped scission read backwards (centre derived from the transform)."""
    r = parse_smiles(product_smiles)
    want = sorted(resonance_identity(parse_smiles(s)) for s in want_products)
    for cs in capped_scissions(r, tuple(parse_smiles("O") for _ in range(k)), max_reactant_cuts=k)[0]:
        if sorted(resonance_identity(p) for p in cs.products) == want:
            return ExperimentStep.from_transform(cs)
    raise AssertionError(f"no capped scission of {product_smiles} yields {want_products}")


class _FakeTransform:
    """An arbitrary duck-typed object satisfying the transform interface -- NO provider provenance whatsoever.

    This is the Phase-II #126 ``from_transform`` attack: a caller who controls a fake transform can mint a step
    carrying any ``reaction_center()`` they like.  The fix ignores that centre and re-derives from the molecules."""

    def __init__(self, reactant, products, reagents, center):
        self.reactant = reactant
        self.products = products
        self.reagents = reagents
        self._center = center

    def reaction_center(self):
        return self._center


def test_center_trusted_bit_is_retired_not_renamed():
    # the forgeable field no longer exists at all -- not a superficial rename (#126 Phase II directive).
    step = _hand_step([_LACTIC, _LACTIC], [_LACTIDE, "water", "water"], _LACTIDE, _FORGED_ELEMENTARY)
    assert not hasattr(step, "center_trusted")
    with pytest.raises(TypeError):
        replace(step, center_trusted=True)  # cannot set a field that does not exist


def test_lactide_forge_demoted_through_every_public_construction_route():
    # THE #126 acceptance gate: the bundled double condensation must NOT vouch an elementary acyl condensation,
    # by ANY public route a data-only attacker controls.
    from smartchem.experiment.feasibility import _is_intermolecular_acyl_condensation

    # (a) direct public constructor with a forged elementary centre
    direct = _hand_step([_LACTIC, _LACTIC], [_LACTIDE, "water", "water"], _LACTIDE, _FORGED_ELEMENTARY)
    assert _is_intermolecular_acyl_condensation(direct) is True   # the whole-molecule census STILL fires ...
    assert direct.reaction_center is not None                     # ... the centre is retained as metadata ...
    assert recognize_reaction_type(direct) is None                # ... but re-derivation demotes it (was: VOUCH).

    # (b) dataclasses.replace forging the elementary centre onto a demoted step
    replaced = replace(direct, reaction_center=_FORGED_ELEMENTARY)
    assert recognize_reaction_type(replaced) is None

    # (c) a fake transform whose reverse IS the lactide fiction, minting a trusted-looking centre with no provenance
    fake = _FakeTransform(parse_smiles(_LACTIDE), (parse_smiles(_LACTIC), parse_smiles(_LACTIC)),
                          (_WATER, _WATER), _FORGED_ELEMENTARY)
    assert recognize_reaction_type(ExperimentStep.from_transform(fake)) is None


@pytest.mark.parametrize("product,want,label", _GENUINE)
def test_recognition_is_content_deterministic_under_center_mutation(product, want, label):
    # the core new invariant: recognition is a pure function of the conserved molecules.  Mutating the advisory
    # reaction_center (to None, to a forged elementary centre, to a wrong-but-valid centre) never changes the verdict.
    genuine = _derived_step(product, want)
    base = recognize_reaction_type(genuine)
    assert base is not None, f"{label} genuine step must vouch"
    assert recognize_reaction_type(replace(genuine, reaction_center=None)) == base
    assert recognize_reaction_type(replace(genuine, reaction_center=_FORGED_ELEMENTARY)) == base


@pytest.mark.parametrize("product,want,label", _GENUINE)
def test_genuine_engine_derived_steps_still_vouch(product, want, label):
    # no false-reject: the three condensation classes still recognize their genuine ENGINE-derived instances.
    assert recognize_reaction_type(_derived_step(product, want)) is not None, f"{label} lost its vouch"


def test_hand_built_genuine_condensation_now_vouches_via_rederivation():
    # a STRENGTHENING the content-determinism buys: a hand-built genuine esterification with NO centre is now
    # recognized (the oracle re-derives it from the molecules), where the Phase-I trusted-centre gate demoted it.
    hand = _hand_step(["CC(=O)O", "CO"], ["CC(=O)OC", "water"], "CC(=O)OC", None)
    assert hand.reaction_center is None
    assert recognize_reaction_type(hand) is not None


def test_reachable_r55_glue_fiction_stays_demoted_regardless_of_center():
    # the #109 reachable over-generation: isopropanol + ethyl acetate -> isopentyl acetate glues two alkyl fragments
    # with a new C-C bond and calls the departing atoms water.  The census never fires (no acyl/ether/N formed), so
    # it is demoted independently of any attached centre -- the re-derivation is not even reached.
    r55 = _derived_step("CC(C)CCOC(=O)C", ["CC(C)O", "CCOC(=O)C"])
    assert recognize_reaction_type(r55) is None
    assert recognize_reaction_type(replace(r55, reaction_center=_FORGED_ELEMENTARY)) is None
