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
        # and a sourced record RESOLVES against the step via the applies_to LOOKUP (EVD-KEY-CTX-01): the seed
        # record now carries phase="gas" while this step is phase-unspecified, so raw == is (correctly) False,
        # but applies_to subsumes the unspecified context and the gas record still answers the step.
        assert record_evidence_key(
            next(r for r in DEFAULT_KINETICS.records if r.name == "N2O5 decomposition")
        ) != reaction_evidence_key(step)  # identity is finer: the phase makes the record key a distinct value
        matches = [
            rec for rec in DEFAULT_KINETICS.records
            if record_evidence_key(rec).applies_to(reaction_evidence_key(step))
        ]
        assert matches, "the N2O5 seed record must resolve (applies_to) through the unified ReactionEvidenceKey"

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


class TestPhaseNormalization:
    """EVD-KEY-CTX-01: the conservative free-text-medium -> canonical-phase normalizer."""

    def test_recognises_the_controlled_gas_and_aqueous_vocabulary(self):
        from smartchem.evidence_key import normalize_phase
        for s in ("gas", "GAS", " gas phase ", "gas-phase", "Gaseous", "vapour", "vapor"):
            assert normalize_phase(s) == "gas", s
        for s in ("aqueous", "Aqueous Solution", "water", " AQ "):
            assert normalize_phase(s) == "aqueous", s

    def test_declines_everything_outside_the_vocabulary(self):
        from smartchem.evidence_key import normalize_phase
        # the SOUNDNESS tripwire: a fuzzy/substring matcher would mis-map these; the exact matcher declines them.
        for s in ("non-aqueous", "aqueous, mild acid", "gaslight", "dmso", "toluene", "", "  "):
            assert normalize_phase(s) == "", s

    def test_a_non_string_medium_declines(self):
        from smartchem.evidence_key import normalize_phase
        assert normalize_phase(None) == "" and normalize_phase(42) == ""

    def test_phase_context_is_the_key_ready_tuple_or_empty(self):
        from smartchem.evidence_key import phase_context
        assert phase_context("gas phase") == (("phase", "gas"),)
        assert phase_context("aqueous") == (("phase", "aqueous"),)
        assert phase_context("dmso") == ()   # unrecognised -> context-free
        assert phase_context("") == ()


class TestAppliesToLookup:
    """EVD-KEY-CTX-01: applies_to is the LOOKUP relation -- exact on structure/direction, SUBSUMING on context."""

    def _rxn(self, ctx=()):
        return ReactionEvidenceKey.from_molecules([(_mol("CCO"), 1)], [(_mol("O"), 1)]).with_context(ctx)

    def test_a_different_structure_never_applies(self):
        a = ReactionEvidenceKey.from_molecules([(_mol("CCO"), 1)], [(_mol("O"), 1)])
        b = ReactionEvidenceKey.from_molecules([(_mol("COC"), 1)], [(_mol("O"), 1)])  # isomer
        assert not a.applies_to(b) and not b.applies_to(a)

    def test_the_reverse_direction_never_applies(self):
        fwd = ReactionEvidenceKey.from_molecules([(_mol("CCO"), 1)], [(_mol("O"), 1)])
        rev = ReactionEvidenceKey.from_molecules([(_mol("O"), 1)], [(_mol("CCO"), 1)])
        assert not fwd.applies_to(rev)

    def test_an_unspecified_step_resolves_a_phase_tagged_record(self):
        gas_record = self._rxn([("phase", "gas")])
        unspecified_step = self._rxn()
        assert gas_record.applies_to(unspecified_step)   # no regression: the record still answers
        assert gas_record != unspecified_step            # ... though identity is strictly finer

    def test_an_untagged_record_answers_any_phase_step(self):
        untagged_record = self._rxn()
        aqueous_step = self._rxn([("phase", "aqueous")])
        assert untagged_record.applies_to(aqueous_step)  # backward compatible: absence never refuses

    def test_a_conflicting_declared_phase_withholds_the_record(self):
        gas_record = self._rxn([("phase", "gas")])
        aqueous_step = self._rxn([("phase", "aqueous")])
        assert not gas_record.applies_to(aqueous_step)   # THE phase-borrow, closed
        assert not aqueous_step.applies_to(gas_record)   # symmetric in context

    def test_a_matching_declared_phase_applies(self):
        assert self._rxn([("phase", "gas")]).applies_to(self._rxn([("phase", "gas")]))

    def test_equality_implies_applies_but_not_conversely(self):
        gas = self._rxn([("phase", "gas")])
        unspec = self._rxn()
        assert gas.applies_to(gas)                 # == implies applies_to
        assert gas.applies_to(unspec) and gas != unspec  # applies_to is strictly weaker than ==

    def test_applies_to_type_guards_its_argument(self):
        with pytest.raises(TypeError):
            self._rxn().applies_to(("not", "a", "key"))
