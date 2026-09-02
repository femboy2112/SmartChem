"""EVD-KEY-01 -- the unified section-9.1 ReactionEvidenceKey.

Before this, kinetics/Eyring keyed reactions on canonical STRUCTURE (sound) while other providers rolled their own
FORMULA keys (the isomer-borrow hazard), with three separate gcd-normalisers.  These tests pin the ONE unified key:
it is isomer-distinct (structure, not formula), direction-specific, scale-invariant (primitive stoichiometry), and
context-refinable -- and it is LIVE in the sound kinetics/Eyring anchor (not a dead switch), which now resolves
records THROUGH it, byte-congruent to the tuple key it replaced.
"""
from __future__ import annotations

import pytest

from smartchem.evidence_key import REACTION_EVIDENCE_KEY_SCHEMA, ReactionEvidenceKey
from smartchem.smiles import parse_smiles


def _mol(s):
    return parse_smiles(s)


class TestValueSemantics:
    def test_isomer_distinct_not_formula(self):
        # ethanol (CCO) and dimethyl ether (COC) share a formula but are different reactions.
        a = ReactionEvidenceKey.from_molecules([(_mol("CCO"), 1)], [(_mol("O"), 1)])
        b = ReactionEvidenceKey.from_molecules([(_mol("COC"), 1)], [(_mol("O"), 1)])
        assert a != b

    def test_scale_invariant_primitive_stoichiometry(self):
        one = ReactionEvidenceKey.from_molecules([(_mol("CCO"), 1)], [(_mol("O"), 2)])
        triple = ReactionEvidenceKey.from_molecules([(_mol("CCO"), 3)], [(_mol("O"), 6)])
        assert one == triple  # gcd-reduced -> the same key at any scale

    def test_direction_is_encoded_by_side(self):
        forward = ReactionEvidenceKey.from_molecules([(_mol("CCO"), 1)], [(_mol("O"), 1)])
        reverse = ReactionEvidenceKey.from_molecules([(_mol("O"), 1)], [(_mol("CCO"), 1)])
        assert forward != reverse  # a decomposition and its algebraic reverse are different keys

    def test_context_only_refines_never_merges(self):
        base = ReactionEvidenceKey.from_molecules([(_mol("CCO"), 1)], [(_mol("O"), 1)])
        aqueous = base.with_context([("phase", "aqueous")])
        assert base != aqueous                      # a declared context makes the key FINER
        assert base.reactant_identities == aqueous.reactant_identities  # ... on the SAME reaction

    def test_side_order_independent(self):
        a = ReactionEvidenceKey.from_molecules([(_mol("O"), 1), (_mol("CCO"), 1)], [(_mol("CO"), 1)])
        b = ReactionEvidenceKey.from_molecules([(_mol("CCO"), 1), (_mol("O"), 1)], [(_mol("CO"), 1)])
        assert a == b  # canonical (sorted) -> input order does not matter

    def test_sides_view_is_the_reactants_products_tuple(self):
        k = ReactionEvidenceKey.from_molecules([(_mol("CCO"), 1)], [(_mol("O"), 1)])
        r, p = k.sides
        assert list(r) == sorted(r) and list(p) == sorted(p)


class TestValidation:
    def test_empty_side_is_refused(self):
        with pytest.raises(ValueError):
            ReactionEvidenceKey.of([], [("d", 1)])

    def test_nonpositive_coefficient_is_refused(self):
        with pytest.raises(ValueError):
            ReactionEvidenceKey.of([("d", 0)], [("e", 1)])

    def test_duplicate_structure_on_a_side_merges_not_duplicates(self):
        # the same species twice on one side sums its coefficients (never two entries).
        k = ReactionEvidenceKey.of([("d", 1), ("d", 1)], [("e", 1)], primitive=False)
        assert k.reactant_identities == (("d", 2),)

    def test_unsorted_direct_construction_is_refused(self):
        with pytest.raises(ValueError):
            ReactionEvidenceKey(REACTION_EVIDENCE_KEY_SCHEMA, (("z", 1), ("a", 1)), (("e", 1),))

    def test_context_dimension_may_not_repeat(self):
        with pytest.raises(ValueError):
            ReactionEvidenceKey(
                REACTION_EVIDENCE_KEY_SCHEMA, (("d", 1),), (("e", 1),),
                (("phase", "aqueous"), ("phase", "neat")),
            )


class TestLiveInTheSoundAnchor:
    """The type is not a dead switch: the kinetics + Eyring providers resolve records THROUGH it in production."""

    def test_reaction_key_of_is_the_evidence_key_sides_view(self):
        from smartchem.data.kinetics import DEFAULT_KINETICS
        from smartchem.experiment.kinetics import (
            reaction_evidence_key,
            reaction_key_of,
            record_evidence_key,
        )
        from smartchem.experiment.step import ExperimentStep

        # the N2O5 decomposition the kinetics seed documents
        n2o5 = _mol("O=[N+]([O-])O[N+](=O)[O-]")
        no2 = _mol("[N+](=O)[O-]")
        o2 = _mol("O=O")
        step = ExperimentStep.assembling(o2, (n2o5, n2o5), (no2, no2, no2, no2, o2))
        # the tuple view is exactly the unified key's sides
        assert reaction_key_of(step) == reaction_evidence_key(step).sides
        # and a sourced record resolves against the SAME unified key value (structure+direction+primitive-stoich)
        matches = [rec for rec in DEFAULT_KINETICS.records if record_evidence_key(rec) == reaction_evidence_key(step)]
        assert matches, "the N2O5 seed record must resolve through the unified ReactionEvidenceKey"

    def test_kinetics_lookup_unchanged_by_the_refactor(self):
        # behaviour preservation: the seed rate still resolves for the seed reaction (the wiring did not regress it).
        from smartchem.data.kinetics import DEFAULT_KINETICS
        from smartchem.experiment.kinetics import _resolve_record
        from smartchem.experiment.step import ExperimentStep

        n2o5 = _mol("O=[N+]([O-])O[N+](=O)[O-]")
        no2 = _mol("[N+](=O)[O-]")
        o2 = _mol("O=O")
        step = ExperimentStep.assembling(o2, (n2o5, n2o5), (no2, no2, no2, no2, o2))
        assert _resolve_record(DEFAULT_KINETICS, step) is not None
