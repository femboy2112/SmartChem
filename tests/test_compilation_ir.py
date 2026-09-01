"""IR-CHEM-01 (first brick) -- the shared ChemicalCompilationIR envelope + its formula producer.

Pins the DEFINING property (standard section 4.1): the value's digest changes on any semantic input and never on
a display/ordering difference; plus the value-construction invariants that keep the IR honest.
"""
import random

import pytest

from smartchem.compilation_ir import (
    CANDIDATE_SUMMARY_SCHEMA,
    CHEMICAL_COMPILATION_IR_SCHEMA,
    CandidateSummary,
    ChemicalCompilationIR,
    ChemicalIdentity,
    CompilationOperation,
    IdentityLayer,
    decompile_to_ir,
)
from smartchem.decompiler import Formula, example_inventory
from smartchem.search import SearchStatus

INV = example_inventory()


class TestDecompileToIR:
    def test_emits_a_decompile_ir_with_candidates_and_a_status(self):
        ir = decompile_to_ir("C8H9NO2", INV)
        assert ir.operation is CompilationOperation.DECOMPILE
        assert ir.target.layer is IdentityLayer.FORMULA
        assert ir.candidate_count > 0
        assert ir.search_status is SearchStatus.COMPLETE_WITHIN_BOUNDS
        assert ir.complete_within_bounds
        assert all(
            c.candidate_kind == "FORMULA_EDGE" and c.readiness_tier == "FORMAL_CANDIDATE" for c in ir.candidates
        )
        assert ir.tool_version  # the single-source package version

    def test_is_reproducible_same_inputs_same_digest(self):
        assert decompile_to_ir("C8H9NO2", INV).digest == decompile_to_ir("C8H9NO2", INV).digest

    def test_partial_search_is_carried_faithfully(self):
        ir = decompile_to_ir("C8H9NO2", INV, budget=1)
        assert ir.search_status is SearchStatus.PARTIAL_SEARCH_BUDGET
        assert not ir.complete_within_bounds
        assert ir.diagnostics and "budget" in ir.diagnostics[0]


class TestDigestIsSemanticNotPresentational:
    """Section 4.1: the digest MUST change on a semantic input and MUST NOT change on display/order."""

    def test_inventory_order_does_not_change_the_digest(self):
        shuffled = list(INV)
        random.seed(7)
        random.shuffle(shuffled)
        assert decompile_to_ir("C8H9NO2", INV).digest == decompile_to_ir("C8H9NO2", tuple(shuffled)).digest

    def test_target_change_changes_the_digest(self):
        assert decompile_to_ir("C8H9NO2", INV).digest != decompile_to_ir("C6H6", INV).digest

    def test_inventory_change_changes_the_digest(self):
        assert decompile_to_ir("C8H9NO2", INV).digest != decompile_to_ir("C8H9NO2", INV[:3]).digest

    def test_a_search_bound_change_changes_the_digest_even_with_an_identical_candidate_set(self):
        # THE subtle 4.1 requirement: the bound rides in request_digest (a field), so it enters the value digest
        # even when the returned candidate set is byte-for-byte identical.
        hi = decompile_to_ir("C8H9NO2", INV, budget=100_000)
        lo = decompile_to_ir("C8H9NO2", INV, budget=90_000)
        assert [c.candidate_digest for c in hi.candidates] == [c.candidate_digest for c in lo.candidates]
        assert hi.request_digest != lo.request_digest
        assert hi.digest != lo.digest

    def test_request_digest_is_stable_across_reruns(self):
        assert decompile_to_ir("C8H9NO2", INV).request_digest == decompile_to_ir("C8H9NO2", INV).request_digest


class TestIRConstructionInvariants:
    def test_candidates_are_emitted_in_canonical_digest_order(self):
        ir = decompile_to_ir("C8H9NO2", INV)
        assert [c.candidate_digest for c in ir.candidates] == sorted(c.candidate_digest for c in ir.candidates)

    def test_construction_rejects_unsorted_candidates(self):
        ir = decompile_to_ir("C8H9NO2", INV)
        assert len(ir.candidates) >= 2
        with pytest.raises(ValueError, match="canonical .*order"):
            ChemicalCompilationIR(
                CHEMICAL_COMPILATION_IR_SCHEMA, ir.tool_version, ir.operation, ir.target, ir.request_digest,
                ir.identity_losses, ir.terminal_policy_digest, ir.search_status, ir.search_receipt_digest,
                tuple(reversed(ir.candidates)), ir.diagnostics,
            )

    def test_construction_rejects_duplicate_candidates(self):
        ir = decompile_to_ir("H2O")  # exactly one edge
        with pytest.raises(ValueError, match="distinct by digest"):
            ChemicalCompilationIR(
                CHEMICAL_COMPILATION_IR_SCHEMA, ir.tool_version, ir.operation, ir.target, ir.request_digest,
                ir.identity_losses, ir.terminal_policy_digest, ir.search_status, ir.search_receipt_digest,
                ir.candidates + ir.candidates, ir.diagnostics,
            )

    def test_identity_of_formula_records_the_formula_layer(self):
        cid = ChemicalIdentity.of_formula(Formula.parse("H2O"))
        assert cid.layer is IdentityLayer.FORMULA
        assert cid.canonical_repr == "H2O"
        assert cid.identity_digest

    def test_candidate_summary_rejects_an_unknown_kind(self):
        with pytest.raises(ValueError, match="candidate_kind"):
            CandidateSummary(CANDIDATE_SUMMARY_SCHEMA, "MECHANISM", "d", "eq", "FORMAL_CANDIDATE")
