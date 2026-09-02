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
    InverseResult,
    InverseStatus,
    decompile_to_ir,
    deserialize_ir,
    ir_from_payload,
    ir_to_payload,
    recompile_from_serialized,
    recompile_to_ir,
    serialize_ir,
)
from smartchem.transform_registry import TRANSFORM_REGISTRIES, transform_registry_digest
from smartchem.decompiler import Formula, example_inventory
from smartchem.search import STANDARD_8_2_STATUSES, SearchStatus
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
H2 = parse_smiles("[H][H]")                         # elemental terminals for the water litmus (IR-INV-01)
O2 = parse_smiles("O=O")


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
                ir.identity_losses, ir.terminal_policy_digest, ir.transform_registry_digest, ir.search_status,
                ir.standard_status, ir.search_receipt_digest, tuple(reversed(ir.candidates)), ir.diagnostics,
            )

    def test_construction_rejects_duplicate_candidates(self):
        ir = decompile_to_ir("H2O")  # exactly one edge
        with pytest.raises(ValueError, match="distinct by digest"):
            ChemicalCompilationIR(
                CHEMICAL_COMPILATION_IR_SCHEMA, ir.tool_version, ir.operation, ir.target, ir.request_digest,
                ir.identity_losses, ir.terminal_policy_digest, ir.transform_registry_digest, ir.search_status,
                ir.standard_status, ir.search_receipt_digest, ir.candidates + ir.candidates, ir.diagnostics,
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


class TestIRSerialization:
    """IR-CHEM-01 serialization: the IR is a transportable artifact whose ROUND TRIP preserves identity."""

    def _decompile_ir(self):
        return decompile_to_ir("C8H9NO2", INV)

    def _recompile_ir(self):
        return recompile_to_ir(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)

    def test_round_trip_preserves_the_digest_for_both_producers(self):
        for ir in (self._decompile_ir(), self._recompile_ir()):
            back = deserialize_ir(serialize_ir(ir))
            assert back.digest == ir.digest          # the load-bearing property: serialize/deserialize is identity
            assert back == ir

    def test_round_trip_preserves_every_semantic_field(self):
        ir = self._recompile_ir()
        back = deserialize_ir(serialize_ir(ir))
        assert back.operation is ir.operation
        assert back.target.layer is ir.target.layer and back.target.identity_digest == ir.target.identity_digest
        assert back.search_status is ir.search_status
        assert [c.candidate_digest for c in back.candidates] == [c.candidate_digest for c in ir.candidates]
        assert back.diagnostics == ir.diagnostics
        assert back.request_digest == ir.request_digest
        assert back.transform_registry_digest == ir.transform_registry_digest

    def test_serialized_string_is_canonical_and_stable(self):
        ir = self._decompile_ir()
        assert serialize_ir(ir) == serialize_ir(deserialize_ir(serialize_ir(ir)))

    def test_deserialize_revalidates_and_refuses_a_tampered_payload(self):
        ir = self._decompile_ir()
        assert len(ir.candidates) >= 2
        payload = ir_to_payload(ir)
        payload["candidates"] = list(reversed(payload["candidates"]))  # break the canonical digest order
        with pytest.raises(ValueError, match="canonical .*order"):
            ir_from_payload(payload)

    def test_deserialize_refuses_an_unknown_enum_value(self):
        payload = ir_to_payload(self._recompile_ir())
        payload["operation"] = "TRANSMOGRIFY"
        with pytest.raises(ValueError):
            ir_from_payload(payload)

    def test_serialize_is_presentation_invariant_across_permuted_inputs(self):
        a = recompile_to_ir(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
        b = recompile_to_ir(PARA, reagents=(ANH, WATER, ACOH), available=(AMP,), max_depth=1)
        assert serialize_ir(a) == serialize_ir(b)

    def test_type_guards(self):
        with pytest.raises(TypeError):
            ir_to_payload("not an ir")
        with pytest.raises(TypeError):
            deserialize_ir(123)


class TestRecompileNoRouteDiagnostic:
    """The producer fix under IR-INV-01: a complete-within-bounds, zero-candidate, not-in-stock recompile is an
    EXHAUSTIVE grammar-level dead end and MUST say so -- a silent empty is the SRCH-DEPTH-01 laundering one layer up.
    """

    def test_complete_empty_not_in_stock_emits_a_precise_dead_end_diagnostic(self):
        # water from H2/O2: outside the capped-scission grammar -> exhaustive empty
        ir = recompile_to_ir(WATER, reagents=(H2, O2), max_depth=2)
        assert ir.search_status is SearchStatus.COMPLETE_WITHIN_BOUNDS
        assert ir.candidate_count == 0
        assert ir.diagnostics, "a complete-empty search MUST NOT be silent -- that is the SRCH-DEPTH-01 disease"
        msg = ir.diagnostics[0].lower()
        assert "exhaustive" in msg
        # the claim is SCOPED to this mode+bounds, never a registry-wide "no route anywhere" (red-team finding 1)
        assert "these bounds" in msg and "'routes'" in msg
        assert "not a proof" in msg
        assert "outside the current registry" not in msg

    def test_the_no_route_diagnostic_does_not_overclaim_registry_wide(self):
        # red-team finding 1: complete_within_bounds proves exhaustion of THIS mode at THESE bounds only. The
        # SAME request under mode='dags' can still be truncated -- so the wording must not assert a registry fact.
        ir = recompile_to_ir(WATER, reagents=(H2, O2), max_depth=2)
        msg = ir.diagnostics[0].lower()
        assert "different mode or higher bounds" in msg  # explicitly names what it does NOT exclude
        for overclaim in ("no route exists anywhere", "outside the current registry", "no bridge exists"):
            assert overclaim not in msg

    def test_a_truncated_empty_search_is_never_called_a_dead_end(self):
        # same target family but starved: PARTIAL, and its diagnostic must speak of incompleteness, not exhaustion
        ir = recompile_to_ir(PARA, reagents=(WATER,), max_depth=1, cut_budget=1)
        assert not ir.complete_within_bounds
        assert ir.candidate_count == 0
        joined = " ".join(ir.diagnostics).lower()
        assert "incomplete" in joined
        assert "exhaustive" not in joined and "dead end" not in joined

    def test_target_in_stock_keeps_its_own_diagnostic_not_the_dead_end_one(self):
        ir = recompile_to_ir(PARA, reagents=(WATER,), available=(PARA,), max_depth=1)
        assert ir.candidate_count == 0
        assert "already present" in ir.diagnostics[0]
        assert "dead end" not in ir.diagnostics[0]

    def test_a_search_with_candidates_carries_no_diagnostic(self):
        ir = recompile_to_ir(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=3)
        assert ir.candidate_count > 0
        assert ir.diagnostics == ()


class TestRecompileFromSerialized:
    """IR-INV-01: the recompiler consumes a SERIALIZED decompile artifact end to end.

    The named acceptance is water: recompile cannot build H2O from H2/O2 (elemental redox is outside the
    capped-scission grammar), so the bridge renders a PRECISE unsupported-transform refusal rather than a
    fabricated water reaction or a silent empty (manifest IR-INV-01: the second, refusal clause).
    """

    def _water_artifact(self) -> str:
        return serialize_ir(decompile_to_ir("H2O"))

    def _para_artifact(self) -> str:
        return serialize_ir(decompile_to_ir("C8H9NO2"))

    # -- the headline: water is a precise, NON-laundered dead end -----------------------------------------
    def test_water_from_elements_is_a_precise_no_route_refusal_not_a_fabricated_transform(self):
        res = recompile_from_serialized(self._water_artifact(), structure=WATER, reagents=(H2, O2), max_depth=2)
        assert type(res) is InverseResult
        assert res.inverse_status is InverseStatus.NO_ROUTE_IN_GRAMMAR
        assert not res.reconstituted
        refusal = res.refusal.lower()
        assert res.refusal and "exhaustive" in refusal
        # the refusal is SCOPED to this mode+bounds, not a fabricated registry-wide claim (red-team finding 1)
        assert "not a proof" in refusal and "different mode or higher bounds" in refusal
        assert "outside the current registry" not in refusal
        # W3: no water reaction was invented -- the recompile IR genuinely has zero candidates
        assert res.recompile_ir is not None and res.recompile_ir.candidate_count == 0

    def test_the_water_dead_end_is_distinguished_from_a_truncated_search(self):
        # exhaustive empty -> NO_ROUTE_IN_GRAMMAR; truncated empty -> INCONCLUSIVE_BOUNDS_HIT. Never conflated.
        dead_end = recompile_from_serialized(self._water_artifact(), structure=WATER, reagents=(H2, O2), max_depth=2)
        starved = recompile_from_serialized(
            self._para_artifact(), structure=PARA, reagents=(WATER,), max_depth=1, cut_budget=1
        )
        assert dead_end.inverse_status is InverseStatus.NO_ROUTE_IN_GRAMMAR
        assert dead_end.recompile_ir.complete_within_bounds is True
        assert starved.inverse_status is InverseStatus.INCONCLUSIVE_BOUNDS_HIT
        assert starved.recompile_ir.complete_within_bounds is False
        assert "cannot be concluded" in starved.refusal

    # -- the artifact genuinely CONSTRAINS the recompile (section 5.4 coherence) --------------------------
    def test_a_structure_whose_formula_is_not_the_decompiled_species_is_refused(self):
        res = recompile_from_serialized(self._water_artifact(), structure=PARA, reagents=(ANH,), available=(AMP,))
        assert res.inverse_status is InverseStatus.FORMULA_MISMATCH
        assert res.recompile_ir is None          # refused BEFORE running any search
        assert "C8H9NO2" in res.refusal and "H2O" in res.refusal

    def test_same_formula_isomer_passes_the_formula_gate(self):
        # PARA and its O-acetyl isomer share C8H9NO2 -- both are legitimate structural hypotheses for that artifact
        for isomer in (PARA, PARA_O_ESTER):
            res = recompile_from_serialized(
                self._para_artifact(), structure=isomer, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1
            )
            assert res.inverse_status is not InverseStatus.FORMULA_MISMATCH
            assert res.recompile_ir is not None
            # and the two isomers key on DISTINCT structure identities (section 5.4), never collapsed to formula
        a = recompile_from_serialized(self._para_artifact(), structure=PARA, reagents=(ANH,), available=(AMP,), max_depth=1)
        b = recompile_from_serialized(self._para_artifact(), structure=PARA_O_ESTER, reagents=(ANH,), available=(AMP,), max_depth=1)
        assert a.recompile_ir.target.identity_digest != b.recompile_ir.target.identity_digest

    def test_a_recompile_artifact_is_refused_as_input(self):
        recompile_text = serialize_ir(recompile_to_ir(PARA, reagents=(ANH,), available=(AMP,), max_depth=1))
        res = recompile_from_serialized(recompile_text, structure=PARA, reagents=(ANH,), available=(AMP,))
        assert res.inverse_status is InverseStatus.NOT_A_DECOMPILE_ARTIFACT
        assert res.recompile_ir is None
        assert "RECOMPILE" in res.refusal

    # -- the two success shapes ---------------------------------------------------------------------------
    def test_a_reachable_target_reconstitutes_with_routes(self):
        res = recompile_from_serialized(
            self._para_artifact(), structure=PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=3
        )
        assert res.inverse_status is InverseStatus.ROUTES_FOUND
        assert res.reconstituted and res.refusal is None
        assert res.recompile_ir.candidate_count > 0

    def test_a_target_already_in_stock_is_trivially_reconstituted(self):
        res = recompile_from_serialized(
            self._para_artifact(), structure=PARA, reagents=(WATER,), available=(PARA,), max_depth=1
        )
        assert res.inverse_status is InverseStatus.TARGET_ALREADY_TERMINAL
        assert res.reconstituted and res.refusal is None

    # -- it truly consumes the TEXT, and re-validates it --------------------------------------------------
    def test_it_consumes_a_serialized_string_not_an_object(self):
        # the artifact crosses the serialization boundary: only the string is handed in
        text = self._water_artifact()
        assert isinstance(text, str)
        res = recompile_from_serialized(text, structure=WATER, reagents=(H2, O2), max_depth=2)
        assert res.decompile_ir.operation is CompilationOperation.DECOMPILE
        # the consumed artifact round-trips to the same identity it was serialized from
        assert res.decompile_ir.digest == decompile_to_ir("H2O").digest

    def test_a_tampered_artifact_is_refused_on_read(self):
        # deserialize re-validates: a broken candidate order in the artifact is rejected before any recompile
        payload = ir_to_payload(decompile_to_ir("C8H9NO2", INV))
        assert len(payload["candidates"]) >= 2
        payload["candidates"] = list(reversed(payload["candidates"]))
        import json

        with pytest.raises(ValueError, match="canonical .*order"):
            recompile_from_serialized(json.dumps(payload), structure=PARA, reagents=(ANH,), available=(AMP,))

    # -- construction invariants of the result record ----------------------------------------------------
    def test_result_rejects_incoherent_construction(self):
        d = decompile_to_ir("H2O")
        r = recompile_to_ir(WATER, reagents=(H2,), max_depth=1)
        with pytest.raises(ValueError, match="success status carries no refusal"):
            InverseResult(d, r, InverseStatus.ROUTES_FOUND, "spurious")     # success must NOT carry a refusal
        with pytest.raises(ValueError, match="non-success status must carry"):
            InverseResult(d, None, InverseStatus.NOT_A_DECOMPILE_ARTIFACT, None)  # non-success NEEDS a refusal
        with pytest.raises(ValueError, match="pre-search refusal must not carry"):
            InverseResult(d, r, InverseStatus.FORMULA_MISMATCH, "x")        # pre-search must not carry a recompile IR
        with pytest.raises(ValueError, match="post-search status must carry"):
            InverseResult(d, None, InverseStatus.ROUTES_FOUND, None)        # post-search must carry a recompile IR

    def test_result_enforces_operation_coherence_of_its_two_irs(self):
        # red-team finding 2: the slots must carry the operations their names advertise -- a DECOMPILE artifact
        # in the recompile slot (or a RECOMPILE in the decompile slot) is incoherent even if all else is valid.
        d = decompile_to_ir("H2O")
        r = recompile_to_ir(WATER, reagents=(H2,), max_depth=1)
        with pytest.raises(ValueError, match="recompile_ir must carry the RECOMPILE operation"):
            InverseResult(d, d, InverseStatus.ROUTES_FOUND, None)           # DECOMPILE ir in the recompile slot
        with pytest.raises(ValueError, match="decompile_ir must carry the DECOMPILE operation"):
            InverseResult(r, r, InverseStatus.ROUTES_FOUND, None)           # RECOMPILE ir in the decompile slot

    def test_type_guard_on_a_non_molecule_structure(self):
        with pytest.raises(TypeError):
            recompile_from_serialized(self._water_artifact(), structure="O", reagents=(H2, O2))


class TestTransformRegistryDigest:
    """The IR names WHICH transform grammar produced its candidates (section 8.4) and its digest is sensitive to
    the grammar version (section 4.1: the digest MUST change on a transform-provider version change)."""

    def test_the_ir_carries_the_declared_registry_digest_for_its_grammar(self):
        dec = decompile_to_ir("C8H9NO2", INV)
        assert dec.transform_registry_digest == transform_registry_digest("formula-decomposition")
        routes = recompile_to_ir(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1, mode="routes")
        assert routes.transform_registry_digest == transform_registry_digest("capped-scission-linear")
        dags = recompile_to_ir(ETAC, reagents=DAG_REAGENTS, max_depth=2, mode="dags")
        assert dags.transform_registry_digest == transform_registry_digest("capped-scission-convergent")

    def test_the_three_grammars_have_distinct_registry_digests(self):
        digests = {
            transform_registry_digest(k)
            for k in ("formula-decomposition", "capped-scission-linear", "capped-scission-convergent")
        }
        assert len(digests) == 3  # a formula edge, a linear route, and a convergent DAG are DIFFERENT grammars

    def test_a_registry_version_bump_changes_request_and_full_digest_even_with_identical_candidates(self, monkeypatch):
        # section 4.1 falsifier: the digest MUST move when the transform-provider version changes, even though
        # nothing else -- target, terminals, bounds, candidate set -- differs.
        before = decompile_to_ir("C8H9NO2", INV)
        bumped = (*TRANSFORM_REGISTRIES["formula-decomposition"][:2], "v2-TEST",
                  *TRANSFORM_REGISTRIES["formula-decomposition"][3:])
        monkeypatch.setitem(TRANSFORM_REGISTRIES, "formula-decomposition", bumped)
        after = decompile_to_ir("C8H9NO2", INV)
        assert [c.candidate_digest for c in after.candidates] == [c.candidate_digest for c in before.candidates]
        assert after.transform_registry_digest != before.transform_registry_digest
        assert after.request_digest != before.request_digest      # folded into the request identity
        assert after.digest != before.digest                       # and hence the full value digest

    def test_registry_digest_is_presentation_invariant(self):
        # it is a property of the GRAMMAR, so permuting the inventory never changes it
        a = recompile_to_ir(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
        b = recompile_to_ir(PARA, reagents=(ANH, WATER, ACOH), available=(AMP,), max_depth=1)
        assert a.transform_registry_digest == b.transform_registry_digest

    def test_round_trip_preserves_the_registry_digest(self):
        ir = recompile_to_ir(ETAC, reagents=DAG_REAGENTS, max_depth=2, mode="dags")
        assert deserialize_ir(serialize_ir(ir)).transform_registry_digest == ir.transform_registry_digest

    def test_construction_rejects_an_empty_registry_digest(self):
        ir = decompile_to_ir("H2O")
        with pytest.raises(ValueError, match="transform_registry_digest must be a non-empty string"):
            ChemicalCompilationIR(
                CHEMICAL_COMPILATION_IR_SCHEMA, ir.tool_version, ir.operation, ir.target, ir.request_digest,
                ir.identity_losses, ir.terminal_policy_digest, "", ir.search_status, ir.standard_status,
                ir.search_receipt_digest, ir.candidates, ir.diagnostics,
            )

    def test_unknown_registry_kind_is_refused(self):
        with pytest.raises(ValueError, match="unknown transform-registry kind"):
            transform_registry_digest("nonexistent-grammar")


class TestSection82IRFace:
    """IR-8.2-01: the IR speaks the standard's section 8.2 terminal-status vocabulary, faithfully to its own
    native search_status, and a refusal string that cites section 8.2 now prints an actual section 8.2 status."""

    def test_schema_bumped_for_the_standard_status_and_loss_fields(self):
        # v1alpha2 added the section 8.2 standard_status field; v1alpha3 (IR-LOSS-01) turned identity_losses into
        # first-class typed records (array[str] -> array[object]) -- another serialized-shape change.
        assert CHEMICAL_COMPILATION_IR_SCHEMA.endswith("v1alpha3")

    def test_decompile_ir_carries_a_faithful_8_2_status(self):
        ir = decompile_to_ir("C8H9NO2", INV)
        assert ir.standard_status in STANDARD_8_2_STATUSES
        assert ir.standard_status == ir.search_status.standard_name  # single-limit native: agrees exactly

    def test_recompile_ir_carries_a_faithful_8_2_status(self):
        ir = recompile_to_ir(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=2)
        assert ir.standard_status in STANDARD_8_2_STATUSES
        if ir.search_status.standard_name is not None:  # non-MULTIPLE agrees; MULTIPLE resolves a primary
            assert ir.standard_status == ir.search_status.standard_name

    def test_render_leads_with_the_8_2_status_and_labels_the_native_one(self):
        ir = decompile_to_ir("H2O")
        r = ir.render()
        assert ir.standard_status in r
        assert f"engine: {ir.search_status.value}" in r

    def test_round_trip_preserves_standard_status_and_digest(self):
        ir = recompile_to_ir(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=2)
        back = deserialize_ir(serialize_ir(ir))
        assert back.standard_status == ir.standard_status
        assert back.digest == ir.digest  # the new semantic field rides in the value digest and round-trips

    def test_the_payload_carries_the_8_2_status(self):
        ir = decompile_to_ir("H2O")
        assert ir_to_payload(ir)["standard_status"] == ir.standard_status

    # -- the faithfulness guard: the IR cannot carry a section 8.2 status contradicting its native status ----
    def _ir_with(self, native, standard):
        base = decompile_to_ir("H2O")
        return ChemicalCompilationIR(
            CHEMICAL_COMPILATION_IR_SCHEMA, base.tool_version, base.operation, base.target, base.request_digest,
            base.identity_losses, base.terminal_policy_digest, base.transform_registry_digest, native, standard,
            base.search_receipt_digest, base.candidates, base.diagnostics,
        )

    def test_a_single_limit_status_must_match_its_standard_name(self):
        with pytest.raises(ValueError, match="must equal search_status.standard_name"):
            self._ir_with(SearchStatus.COMPLETE_WITHIN_BOUNDS, "INCOMPLETE_RESULT_LIMIT")

    def test_a_non_8_2_word_is_refused(self):
        # the engine's own native token is NOT a section 8.2 status
        with pytest.raises(ValueError, match="must be one of the section 8.2 statuses"):
            self._ir_with(SearchStatus.COMPLETE_WITHIN_BOUNDS, "PARTIAL_CUT_BUDGET")

    def test_multiple_limits_accepts_a_resolvable_primary(self):
        ir = self._ir_with(SearchStatus.PARTIAL_MULTIPLE_LIMITS, "INCOMPLETE_CUT_BUDGET")
        assert ir.standard_status == "INCOMPLETE_CUT_BUDGET"

    def test_multiple_limits_refuses_a_non_resolvable_8_2_status(self):
        # INCOMPLETE_CANDIDATE_LIMIT is a real 8.2 name, but no engine limit produces it, so a MULTIPLE status
        # cannot legitimately resolve to it (the residue guard).
        with pytest.raises(ValueError, match="must resolve to a primary"):
            self._ir_with(SearchStatus.PARTIAL_MULTIPLE_LIMITS, "INCOMPLETE_CANDIDATE_LIMIT")

    def test_multiple_limits_refuses_a_completion_status(self):
        # W2: a partial (multiple-limit) search must never be laundered into a completion status
        with pytest.raises(ValueError, match="must resolve to a primary"):
            self._ir_with(SearchStatus.PARTIAL_MULTIPLE_LIMITS, "COMPLETE_WITHIN_DECLARED_SPACE")

    # -- the red-team's finding 4: the section-8.2-citing refusal now prints an actual 8.2 status -----------
    def test_the_inconclusive_refusal_prints_an_8_2_status_not_a_native_token(self):
        starved = recompile_from_serialized(
            serialize_ir(decompile_to_ir("C8H9NO2")), structure=PARA, reagents=(WATER,), max_depth=1, cut_budget=1
        )
        assert starved.inverse_status is InverseStatus.INCONCLUSIVE_BOUNDS_HIT
        assert starved.recompile_ir.standard_status in STANDARD_8_2_STATUSES
        assert starved.recompile_ir.standard_status in starved.refusal   # the 8.2 word is what's printed
        assert "PARTIAL_" not in starved.refusal                          # the native token is gone
        assert "section 8.2" in starved.refusal                          # the stop-reason citation is accurate
        # and this zero-candidate/incomplete cell also names its section 8.3 no-route wording (sibling symmetry)
        assert "section 8.3" in starved.refusal and "INCOMPLETE_NO_ROUTE_OBSERVED" in starved.refusal
