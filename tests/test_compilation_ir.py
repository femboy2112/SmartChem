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
    recompile_to_ir,
)
from smartchem.decompiler import Formula, example_inventory
from smartchem.search import SearchStatus
from smartchem.smiles import parse_smiles

INV = example_inventory()

# structural recompile fixtures (the same paracetamol loop-closer test_routes.py uses)
PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")          # acetaminophen (the amide)
PARA_O_ESTER = parse_smiles("CC(=O)Oc1ccc(N)cc1")  # its O-acetyl isomer -- SAME formula C8H9NO2, different structure
AMP = parse_smiles("Nc1ccc(O)cc1")                 # 4-aminophenol
WATER = parse_smiles("O")
ACOH = parse_smiles("CC(=O)O")
ANH = parse_smiles("CC(=O)OC(=O)C")                # acetic anhydride
ETAC = parse_smiles("CCOC(=O)C")                   # ethyl acetate (a convergent retro-synthesis)
DAG_REAGENTS = tuple(parse_smiles(s) for s in ("O", "CO", "CC(=O)O", "C=C", "CCO", "C=C=O"))


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


class TestRecompileToIR:
    """IR-CHEM-01 (structural producer): the recompiler emits the SAME shared IR the decompiler does."""

    def test_emits_a_recompile_ir_with_route_candidates(self):
        # depth 3 genuinely exhausts this fixture, so the IR can carry a truthful COMPLETE status.
        ir = recompile_to_ir(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=3)
        assert ir.operation is CompilationOperation.RECOMPILE
        assert ir.target.layer is IdentityLayer.STRUCTURE          # a structure target, never collapsed to formula
        assert ir.candidate_count > 0
        assert all(c.candidate_kind == "ROUTE" and c.readiness_tier == "FORMAL_CANDIDATE" for c in ir.candidates)
        assert ir.search_status is SearchStatus.COMPLETE_WITHIN_BOUNDS
        assert ir.tool_version

    def test_depth_truncation_is_never_laundered_to_complete_in_the_ir(self):
        # REGRESSION (adversarial finding): a depth-limited recompile must surface PARTIAL_DEPTH_LIMIT + a
        # diagnostic in the IR, never a silent COMPLETE -- the receipt now reports depth truncation and the IR
        # propagates it honestly.
        ir = recompile_to_ir(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
        assert ir.search_status is SearchStatus.PARTIAL_DEPTH_LIMIT
        assert not ir.complete_within_bounds
        assert ir.diagnostics and "incomplete" in ir.diagnostics[0]

    def test_dag_mode_emits_dag_candidates(self):
        ir = recompile_to_ir(ETAC, reagents=DAG_REAGENTS, max_depth=2, mode="dags")
        assert ir.operation is CompilationOperation.RECOMPILE
        assert ir.candidate_count > 0
        assert all(c.candidate_kind == "DAG" for c in ir.candidates)

    def test_is_reproducible_same_inputs_same_digest(self):
        a = recompile_to_ir(PARA, reagents=(ANH,), available=(AMP,), max_depth=1)
        b = recompile_to_ir(PARA, reagents=(ANH,), available=(AMP,), max_depth=1)
        assert a.digest == b.digest

    def test_reagent_and_available_order_do_not_change_the_digest(self):
        # section 4.1 presentation invariance: the terminal policy is a frozenset, candidates are digest-sorted.
        a = recompile_to_ir(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
        b = recompile_to_ir(PARA, reagents=(ANH, WATER, ACOH), available=(AMP,), max_depth=1)
        assert a.digest == b.digest

    def test_a_bound_change_changes_the_digest_even_with_an_identical_candidate_set(self):
        # THE subtle 4.1 rule on the structural side: a bound rides in request_digest, so it enters the value
        # digest even when the returned candidate set is byte-for-byte identical (both searches complete here).
        hi = recompile_to_ir(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1, cut_budget=20_000)
        lo = recompile_to_ir(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1, cut_budget=19_000)
        assert [c.candidate_digest for c in hi.candidates] == [c.candidate_digest for c in lo.candidates]
        assert hi.request_digest != lo.request_digest
        assert hi.digest != lo.digest

    def test_moving_a_reagent_to_available_changes_the_request_identity(self):
        # reagents are a HELPER pool the cleavage may consume; plain available stock is not. The request identity
        # must tell them apart even though both terminate the search.
        # (the reagent pool stays non-empty in both -- capped_scissions requires a helper pool; only ANH moves)
        as_reagent = recompile_to_ir(PARA, reagents=(WATER, ANH), available=(AMP,), max_depth=1)
        as_stock = recompile_to_ir(PARA, reagents=(WATER,), available=(AMP, ANH), max_depth=1)
        assert as_reagent.request_digest != as_stock.request_digest

    def test_same_formula_isomers_are_distinct_irs(self):
        # section 5.4 falsifier: PARA and its O-acetyl isomer share formula C8H9NO2 but are distinct structures.
        amide = recompile_to_ir(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
        ester = recompile_to_ir(PARA_O_ESTER, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
        assert amide.target.identity_digest != ester.target.identity_digest
        assert amide.digest != ester.digest

    def test_target_in_terminal_stock_yields_no_candidates_and_a_diagnostic(self):
        ir = recompile_to_ir(PARA, reagents=(WATER,), available=(PARA,), max_depth=1)
        assert ir.candidate_count == 0
        assert ir.search_status is SearchStatus.COMPLETE_WITHIN_BOUNDS
        assert ir.diagnostics and "no synthesis is required" in ir.diagnostics[0]

    def test_incomplete_search_is_carried_faithfully_never_laundered_to_complete(self):
        # falsification matrix "Complete search": a starved cut budget is PARTIAL, never a silent complete/no-route.
        ir = recompile_to_ir(PARA, reagents=(WATER,), available=(), max_depth=1, cut_budget=1)
        assert ir.search_status is SearchStatus.PARTIAL_CUT_BUDGET
        assert not ir.complete_within_bounds
        assert ir.diagnostics and "incomplete" in ir.diagnostics[0]

    def test_of_molecule_records_the_structure_layer_and_a_stable_identity(self):
        cid = ChemicalIdentity.of_molecule(PARA)
        assert cid.layer is IdentityLayer.STRUCTURE
        assert cid.identity_digest == ChemicalIdentity.of_molecule(PARA).identity_digest
        assert cid.identity_digest != ChemicalIdentity.of_molecule(AMP).identity_digest

    def test_rejects_a_non_molecule_target_and_a_bad_mode(self):
        with pytest.raises(TypeError, match="Molecule"):
            recompile_to_ir("CC(=O)Nc1ccc(O)cc1", reagents=(ANH,))
        with pytest.raises(ValueError, match="mode"):
            recompile_to_ir(PARA, reagents=(ANH,), available=(AMP,), mode="sideways")
