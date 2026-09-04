"""IR-STRUCT-01 / IR-FORGET-01: a first-class structural decomposition candidate rides ChemicalCompilationIR.

The genericity audit (AUDIT_GENERIC_..._2026-09-03, sections 7.2-7.3, B0, Probe P1) found that structural
decompilation reduced its target to a FORMULA as the sole shared artifact, so the recompiler's inverse had to be
handed a caller-supplied structure -- "a formula-compatibility-constrained structural search, not a
structure-reconstructing inverse of the decompile artifact".  IR-STRUCT-01 promotes the structural scission into
the IR itself: a :class:`StructuralCandidate` retains the parent/product STRUCTURE identities, the scission edit
witness, the primitive stoichiometry, the producing provider's id/version, and the EXACT forgetful formula
projection.

The load-bearing guarantees this pins, each non-vacuously:
  * PRODUCER -- a structural decompile emits a STRUCTURE-layer DECOMPILE IR whose candidates are structural, and
    the real chemistry (paracetamol's amide hydrolysis) is among them;
  * FORGETFUL SQUARE (IR-FORGET-01) -- every stored projection IS the forget of its structure, and a payload
    whose projection (or species) contradicts that is REFUSED on read, never coerced;
  * TRANSPORT -- structural identities and edit witnesses survive serialization byte-for-byte, digest-stable;
  * SEMANTIC DIGEST -- the provider version and the search bounds are in the identity; presentation is not;
  * HAND-BUILT GUARDS -- canonical/distinct order, STRUCTURE-layer coherence, the witness/projection pairing,
    the W3 FORMAL_CANDIDATE tier, and positive multiplicity are all enforced at construction;
  * RECEIPT HONESTY -- the structural descent's section-8.1 receipt nulls what it does not measure (never zero),
    and an exhausted-but-empty run is said precisely, never laundered into a false completeness or a false miss.
"""
import copy

import pytest

from smartchem.compilation_ir import (
    ChemicalIdentity,
    CompilationOperation,
    IdentityLayer,
    StructuralCandidate,
    StructuralSpecies,
    decompile_structure_to_ir,
    decompile_to_ir,
    deserialize_ir,
    ir_from_payload,
    ir_to_payload,
    recompile_to_ir,
    serialize_ir,
    _structural_candidate_from_payload,
    _structural_candidate_to_payload,
    _structural_species_to_payload,
)
from smartchem.search import SearchStatus
from smartchem.smiles import parse_smiles
from smartchem.structure_descent import capped_scissions

PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")   # paracetamol, C8H9NO2
WATER = parse_smiles("O")
AMINOPHENOL = parse_smiles("Nc1ccc(O)cc1")   # 4-aminophenol, C6H7NO
ACETIC = parse_smiles("CC(=O)O")             # acetic acid, C2H4O2
METHANE = parse_smiles("C")                  # no valence-preserving capped scission over water


def _para_ir():
    return decompile_structure_to_ir(PARA, reagents=(WATER,))


def _first_edge():
    edges, _ = capped_scissions(PARA, (WATER,))
    return edges[0]


class TestStructuralDecompileProducer:
    def test_emits_a_structure_layer_decompile_carrying_structural_candidates(self):
        ir = _para_ir()
        assert ir.operation is CompilationOperation.DECOMPILE
        assert ir.target.layer is IdentityLayer.STRUCTURE      # the structure is retained, not reduced to formula
        assert len(ir.structural_candidates) > 0
        assert ir.candidate_count == 0                          # the structural candidates carry the payload

    def test_every_structural_candidate_is_a_formal_decompose(self):
        ir = _para_ir()
        for c in ir.structural_candidates:
            assert c.direction.value == "DECOMPOSE"
            assert c.witness_kind == "CAPPED_SCISSION"
            assert c.projection_kind == "MEDIATED_EDGE"
            assert c.readiness_tier == "FORMAL_CANDIDATE"      # W3: structure enumerates, never claims it runs
            assert c.provider_id == "capped-scission-mediated" and c.provider_version == "v1"
            assert c.parent.structure.identity_digest == ir.target.identity_digest

    def test_the_real_amide_hydrolysis_is_among_the_candidates(self):
        # NON-VACUITY: the machinery finds paracetamol's genuine retro-step (-> 4-aminophenol + acetic acid), not
        # merely valence-valid noise.  Two DISTINCT edit witnesses share this product set -- the structural IR
        # carries more than the formula edge: two structures, one forgetful projection.
        ir = _para_ir()
        amp = ChemicalIdentity.of_molecule(AMINOPHENOL).identity_digest
        acoh = ChemicalIdentity.of_molecule(ACETIC).identity_digest
        hits = [
            c for c in ir.structural_candidates
            if {s.structure.identity_digest for s, _ in c.products} == {amp, acoh}
        ]
        assert len(hits) >= 1
        # every witness of the shared product set forgets to the SAME mediated edge (acetic acid + aminophenol)...
        assert len({c.projection_digest for c in hits}) == 1
        # ...but they are DISTINCT candidates, separated by their edit witness (structure > its formula image).
        assert len({c.witness_digest for c in hits}) == len(hits)


class TestForgetfulSquare:
    def test_every_stored_projection_is_the_true_forget_of_its_edge(self):
        # independent check: recompute the forgetful image straight off the LIVE capped scissions and match it to
        # the projections the producer stored -- the section-7.3 square holding on the real path.
        edges, _ = capped_scissions(PARA, (WATER,))
        forget_digests = {e.forget().digest for e in edges}
        stored = {c.projection_digest for c in _para_ir().structural_candidates}
        assert stored == forget_digests

    def test_a_tampered_projection_digest_is_refused_on_read(self):
        # IR-FORGET-01 teeth: a payload whose projection digest no longer equals the forget of its structure is
        # REFUSED on deserialize, not silently coerced.
        payload = ir_to_payload(_para_ir())
        payload["structural_candidates"][0]["projection_digest"] = "0" * 64
        with pytest.raises(ValueError, match="commuting square|not the forget"):
            ir_from_payload(payload)

    def test_a_tampered_projection_equation_is_refused_on_read(self):
        payload = ir_to_payload(_para_ir())
        payload["structural_candidates"][0]["projection_equation"] = "C8H9NO2 + H2O -> lies + more_lies"
        with pytest.raises(ValueError, match="commuting square|not the forget"):
            ir_from_payload(payload)

    def test_a_tampered_product_formula_breaks_the_square_and_is_refused(self):
        # change a product species' stored FORMULA so it no longer forgets to the stored projection: the square is
        # a two-sided check (structure side vs projection side), so mutating either side and not the other refuses.
        payload = ir_to_payload(_para_ir())
        prod = payload["structural_candidates"][0]["products"][0]["species"]["formula"]
        prod["counts"].append(["Xe", 1])          # a foreign atom nothing conserves
        prod["counts"].sort()
        with pytest.raises(ValueError):
            ir_from_payload(payload)


class TestStructureSurvivesSerialization:
    def test_round_trip_is_digest_stable_and_canonical(self):
        ir = _para_ir()
        text = serialize_ir(ir)
        back = deserialize_ir(text)
        assert back.digest == ir.digest              # identity survives the transport
        assert serialize_ir(back) == text            # and the serialized form is canonical (a fixed point)

    def test_structure_identities_survive_byte_for_byte(self):
        # Probe P1: the STRUCTURE identities (which isomer) survive serialization, so a consumer reads the
        # structure the transform acted on -- not a formula it would have to re-hypothesise.
        ir = _para_ir()
        back = deserialize_ir(serialize_ir(ir))
        for before, after in zip(ir.structural_candidates, back.structural_candidates):
            assert after.parent.structure.canonical_repr == before.parent.structure.canonical_repr
            assert after.parent.structure.identity_digest == before.parent.structure.identity_digest
            assert [s.structure.identity_digest for s, _ in after.products] == \
                   [s.structure.identity_digest for s, _ in before.products]

    def test_edit_witness_survives_serialization(self):
        ir = _para_ir()
        back = deserialize_ir(serialize_ir(ir))
        for before, after in zip(ir.structural_candidates, back.structural_candidates):
            assert after.witness_kind == before.witness_kind
            assert after.witness_digest == before.witness_digest
            assert after.edit_equation == before.edit_equation


class TestSemanticDigestSensitivity:
    def test_provider_version_is_in_the_candidate_identity(self):
        edge = _first_edge()
        v1 = StructuralCandidate.from_capped_scission(edge, provider_version="v1")
        v2 = StructuralCandidate.from_capped_scission(edge, provider_version="v2")
        assert v1.digest != v2.digest                # bumping the provider grammar version changes the identity

    def test_a_bound_change_changes_the_ir_digest_even_with_an_identical_candidate_set(self):
        # section 4.1: a semantic REQUEST change (a bound) must move the value digest even when the returned
        # candidate set is byte-for-byte identical.
        a = decompile_structure_to_ir(PARA, reagents=(WATER,), budget=50_000)
        b = decompile_structure_to_ir(PARA, reagents=(WATER,), budget=90_000)
        assert {c.digest for c in a.structural_candidates} == {c.digest for c in b.structural_candidates}
        assert a.digest != b.digest                  # ...yet the IR digest differs (the bound is in the identity)

    def test_permuting_reagents_is_presentation_invariant(self):
        ACOH = parse_smiles("CC(=O)O")
        a = decompile_structure_to_ir(PARA, reagents=(WATER, ACOH))
        b = decompile_structure_to_ir(PARA, reagents=(ACOH, WATER))
        assert a.digest == b.digest                  # the reagent set is a frozenset; order is not identity


class TestHandBuiltIRGuards:
    def test_structural_candidates_require_a_structure_layer_target(self):
        payload = ir_to_payload(_para_ir())
        payload["target"]["layer"] = IdentityLayer.FORMULA.value    # structure claims over a formula-only target
        with pytest.raises(ValueError, match="STRUCTURE-layer target"):
            ir_from_payload(payload)

    def test_unsorted_structural_candidates_are_refused(self):
        ir = _para_ir()
        assert len(ir.structural_candidates) > 1
        payload = ir_to_payload(ir)
        payload["structural_candidates"].reverse()                  # break the canonical digest-sorted order
        with pytest.raises(ValueError, match="canonical .*order"):
            ir_from_payload(payload)

    def test_duplicate_structural_candidate_is_refused(self):
        payload = ir_to_payload(_para_ir())
        payload["structural_candidates"].insert(0, copy.deepcopy(payload["structural_candidates"][0]))
        with pytest.raises(ValueError, match="distinct by digest|canonical .*order"):
            ir_from_payload(payload)


class TestStructuralCandidateRecordGuards:
    def _candidate_payload(self):
        return _structural_candidate_to_payload(StructuralCandidate.from_capped_scission(_first_edge()))

    def test_readiness_must_be_formal_candidate(self):
        p = self._candidate_payload()
        p["readiness_tier"] = "PROBABLE"
        with pytest.raises(ValueError, match="FORMAL_CANDIDATE"):
            _structural_candidate_from_payload(p)

    def test_witness_projection_pairing_is_enforced(self):
        p = self._candidate_payload()
        p["projection_kind"] = "DECOMPOSITION_EDGE"     # wrong image for a CAPPED_SCISSION witness
        with pytest.raises(ValueError, match="projection_kind"):
            _structural_candidate_from_payload(p)

    def test_a_duplicate_product_species_is_refused(self):
        p = self._candidate_payload()
        p["products"].append(copy.deepcopy(p["products"][0]))
        with pytest.raises(ValueError, match="appears twice|canonical"):
            _structural_candidate_from_payload(p)

    def test_a_zero_multiplicity_is_refused(self):
        p = self._candidate_payload()
        p["products"][0]["multiplicity"] = 0
        with pytest.raises(ValueError, match="multiplicity"):
            _structural_candidate_from_payload(p)

    def test_an_empty_provider_id_is_refused(self):
        p = self._candidate_payload()
        p["provider_id"] = ""
        with pytest.raises(ValueError, match="provider_id"):
            _structural_candidate_from_payload(p)


class TestSection81ReceiptHonesty:
    def test_the_structural_receipt_nulls_what_it_does_not_measure(self):
        ir = _para_ir()
        rv = ir.search_receipt
        assert rv.search_kind == "STRUCTURE_DECOMPOSITION"
        # section 8.1 "null, not zero": the descent measures none of these, so they are UNKNOWN, never a false 0.
        assert rv.nodes_visited is None
        assert rv.transforms_considered is None
        assert rv.candidates_emitted is None
        assert rv.candidate_limit is None
        assert rv.result_limit is None
        # what it DOES know: the distinct emitted count, and a completeness that is not a truncating limit.
        assert rv.results_returned == len(ir.structural_candidates)
        assert rv.cut_enumeration_complete and rv.candidate_enumeration_complete
        assert not rv.result_limit_saturated

    def test_an_incomplete_budget_is_not_a_false_complete(self):
        ir = decompile_structure_to_ir(PARA, reagents=(WATER,), budget=1)
        assert ir.search_status is SearchStatus.PARTIAL_SEARCH_BUDGET
        assert ir.standard_status == "INCOMPLETE_CUT_BUDGET"
        assert not ir.complete_within_bounds
        assert ir.diagnostics and "incomplete" in ir.diagnostics[0]
        assert not ir.search_receipt.cut_enumeration_complete

    def test_an_exhausted_empty_run_is_said_precisely_not_laundered(self):
        # methane has no valence-preserving capped scission over water: the run EXHAUSTS its grammar (complete) and
        # finds nothing.  That must be said as exhaustion-within-bounds, NOT a false completeness or a false miss.
        ir = decompile_structure_to_ir(METHANE, reagents=(WATER,))
        assert ir.complete_within_bounds                      # the grammar was exhausted (no budget fired)
        assert len(ir.structural_candidates) == 0
        assert ir.diagnostics and "exhaustive" in ir.diagnostics[0]
        assert "no structural transform" in ir.diagnostics[0] and "within the algebra" in ir.diagnostics[0]


class TestRedTeamFold:
    """Red-team fold (blind-bearing workflow, 4 CONFIRMED findings): the structure identity was an unverifiable
    one-way label, so a transported payload could forge WHICH isomer a species is, advertise a decomposition of the
    wrong subject, or launder the provider out of an empty-candidate IR. The fold binds each species to a
    re-verifiable canonical graph, pins the parent to the IR target, guards the operation, and folds the provider
    into the request identity. Each finding is now REFUSED (proven here) while the honest path is unchanged.
    """

    ORTHO = parse_smiles("CC(=O)Nc1ccccc1O")   # o-acetamidophenol: C8H9NO2, a DISTINCT isomer of paracetamol

    def test_a_species_carries_its_canonical_graph_and_it_round_trips(self):
        # the structure genuinely RIDES the artifact now (not an opaque digest): atoms/bonds survive serialization.
        ir = _para_ir()
        back = deserialize_ir(serialize_ir(ir))
        for before, after in zip(ir.structural_candidates, back.structural_candidates):
            assert after.parent.atoms == before.parent.atoms and after.parent.bonds == before.parent.bonds
            assert after.parent.molecule.canonical() == before.parent.molecule.canonical()

    def test_a_forged_structure_identity_isomer_swap_is_refused(self):
        # HIGH #1/#2: swap the parent's structure IDENTITY to a different real isomer while leaving the graph -- the
        # graph-bound species certificate refuses it (the square alone was blind to this: same formula).
        payload = ir_to_payload(_para_ir())
        one = payload["structural_candidates"][0]
        forged = ChemicalIdentity.of_molecule(self.ORTHO)   # ortho's digest, C8H9NO2 (same formula as para)
        one["parent"]["structure"] = {
            "schema_version": forged.schema_version, "layer": forged.layer.value,
            "canonical_repr": forged.canonical_repr, "identity_digest": forged.identity_digest,
        }
        payload["structural_candidates"] = [one]
        with pytest.raises(ValueError, match="does not match the stored molecular graph"):
            ir_from_payload(payload)

    def test_a_forged_formula_inconsistent_with_the_graph_is_refused(self):
        payload = ir_to_payload(_para_ir())
        one = payload["structural_candidates"][0]
        one["parent"]["formula"]["counts"] = [
            [s, (c + 3 if s == "H" else c)] for s, c in one["parent"]["formula"]["counts"]
        ]
        payload["structural_candidates"] = [one]
        with pytest.raises(ValueError, match="does not match the stored molecular graph|forget"):
            ir_from_payload(payload)

    def test_a_wrong_subject_parent_same_formula_isomer_is_refused_by_the_parent_pin(self):
        # HIGH #4: a fully-coherent parent that is a DIFFERENT same-formula isomer than the IR target. The forgetful
        # square passes (formula-level: C8H9NO2 either way); ONLY the parent==target pin catches it.
        payload = ir_to_payload(_para_ir())
        one = payload["structural_candidates"][0]
        one["parent"] = _structural_species_to_payload(StructuralSpecies.of_molecule(self.ORTHO))
        payload["structural_candidates"] = [one]
        with pytest.raises(ValueError, match="parent must be the IR target"):
            ir_from_payload(payload)

    def test_structural_candidates_on_a_recompile_operation_are_refused(self):
        # coherence: a DECOMPOSE candidate rides only a DECOMPILE IR, not a RECOMPILE (assembly) artifact.
        payload = ir_to_payload(_para_ir())
        payload["operation"] = CompilationOperation.RECOMPILE.value
        with pytest.raises(ValueError, match="ride only a DECOMPILE IR"):
            ir_from_payload(payload)

    def test_the_provider_is_in_the_ir_identity_even_with_an_empty_candidate_set(self):
        # MEDIUM #3 (now via the registry, TRANSFORM-PROVIDER-01): methane has no cleavage (empty candidate set);
        # the transform algebra must still move ir.digest, else the provider is laundered out of the identity
        # entirely (section 4.1 names "transform/evidence provider version").
        from smartchem.transform_provider import CappedScissionProvider, TransformProviderRegistry
        r_v1 = TransformProviderRegistry((CappedScissionProvider(provider_version="v1"),))
        r_v2 = TransformProviderRegistry((CappedScissionProvider(provider_version="v2"),))
        a = decompile_structure_to_ir(METHANE, reagents=(WATER,), registry=r_v1)
        b = decompile_structure_to_ir(METHANE, reagents=(WATER,), registry=r_v2)
        assert len(a.structural_candidates) == 0 and len(b.structural_candidates) == 0
        assert a.digest != b.digest

    def test_the_honest_full_ir_still_round_trips_unchanged(self):
        ir = _para_ir()
        assert deserialize_ir(serialize_ir(ir)).digest == ir.digest


class TestExistingProducersUnaffected:
    def test_formula_decompile_still_works_and_carries_no_structural_candidates(self):
        ir = decompile_to_ir("C8H9NO2")
        assert ir.structural_candidates == ()
        assert ir.target.layer is IdentityLayer.FORMULA
        assert deserialize_ir(serialize_ir(ir)).digest == ir.digest    # v1alpha5 round-trip intact

    def test_recompile_still_works_and_carries_no_structural_candidates(self):
        ir = recompile_to_ir(PARA, reagents=(WATER,), available=(AMINOPHENOL,), max_depth=1)
        assert ir.structural_candidates == ()
        assert deserialize_ir(serialize_ir(ir)).digest == ir.digest
