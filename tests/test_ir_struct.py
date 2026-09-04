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
    StructuralWitness,
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
        # HIGH #4: a FULLY-COHERENT candidate for a DIFFERENT same-formula isomer (o-acetamidophenol) -- its parent,
        # witness, and products all agree internally (so both the formula square AND the item-4 graph-scission replay
        # pass), but its parent is not the IR target (paracetamol). ONLY the IR-level parent==target pin catches it.
        # (Grafting merely the ORTHO parent onto a PARA candidate is caught EARLIER, by the witness-reactant check;
        # a genuinely coherent wrong-subject candidate is what isolates the parent pin.)
        ortho_ir = decompile_structure_to_ir(self.ORTHO, reagents=(WATER,))
        assert ortho_ir.structural_candidates, "o-acetamidophenol must have a structural decomposition"
        ortho_candidate = _structural_candidate_to_payload(ortho_ir.structural_candidates[0])
        payload = ir_to_payload(_para_ir())                       # target = paracetamol
        payload["structural_candidates"] = [ortho_candidate]      # a coherent ortho candidate on a para IR
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


ORTHO_AMINOPHENOL = parse_smiles("Nc1ccccc1O")   # 2-aminophenol: C6H7NO, a same-formula isomer of 4-aminophenol
ETHANE = parse_smiles("CC")


def _extended_registry():
    from smartchem.transform_provider import CappedScissionProvider, TransformProviderRegistry
    from smartchem.bond_order_edit import BondOrderEditProvider
    return TransformProviderRegistry((CappedScissionProvider(), BondOrderEditProvider()))


def _species_digest_of_payload(entry):
    from smartchem.compilation_ir import _structural_species_from_payload
    return _structural_species_from_payload(entry["species"]).digest


class TestGraphScissionReplay:
    """Item 4 -- the graph-scission replay: the witness is a RE-VERIFIABLE graph edit, not a one-way label.

    IR-STRUCT-01 stored the scission only as a digest + equation, so a deserialized candidate could pair a
    witness_digest for edit A with product species that are edit B's same-formula isomers -- the formula-level
    forgetful square is blind to a product's structure, so it passed (the differently-witnessed-formal-candidate
    gap the IR-STRUCT-01 red-team named and LEFT as a follow-on). This closes it: the candidate now carries a
    :class:`StructuralWitness` whose stored graph edit is reconstructed and replayed on read, and its GRAPH-level
    products are demanded to equal the stored product species. Each guarantee below is non-vacuous.
    """

    def test_every_honest_candidate_carries_a_witness_that_replays_to_its_products(self):
        # POSITIVE, non-vacuous: the witness genuinely reproduces the stored products at the graph level (not just
        # asserting no-raise -- assert the replayed product multiset EQUALS the stored one).
        from collections import Counter
        ir = _para_ir()
        assert ir.structural_candidates
        for sc in ir.structural_candidates:
            assert isinstance(sc.witness, StructuralWitness)
            t = sc.witness.replay_transform()
            assert t.digest == sc.witness_digest
            replayed = Counter(m.canonical() for m in t.products)
            stored = Counter(s.molecule.canonical() for s, mult in sc.products for _ in range(mult))
            assert replayed == stored

    def test_the_witness_survives_serialization_and_still_replays(self):
        ir = _para_ir()
        back = deserialize_ir(serialize_ir(ir))
        assert back.digest == ir.digest
        for sc in back.structural_candidates:
            assert sc.witness.replay_transform().digest == sc.witness_digest

    def _amide_hydrolysis_candidate_payload(self):
        # the real amide hydrolysis: paracetamol + water -> 4-aminophenol + acetic acid
        ir = _para_ir()
        p4 = StructuralSpecies.of_molecule(AMINOPHENOL).structure
        target = next((sc for sc in ir.structural_candidates
                       if any(s.structure == p4 for s, m in sc.products)), None)
        assert target is not None, "the amide-hydrolysis candidate producing 4-aminophenol was not enumerated"
        return _structural_candidate_to_payload(target)

    def test_a_product_isomer_swap_that_passes_the_formula_square_is_refused_by_the_replay(self):
        # THE headline: swap 4-aminophenol -> 2-aminophenol (SAME formula C6H7NO, DIFFERENT structure, itself a
        # VALID species). The formula square passes (identical formulas) and the species certificate passes (2-AP is
        # real) -- ONLY the graph replay catches that the witness edit produces 4-AP, not the swapped 2-AP.
        four = StructuralSpecies.of_molecule(AMINOPHENOL)
        two = StructuralSpecies.of_molecule(ORTHO_AMINOPHENOL)
        assert four.formula == two.formula and four.structure != two.structure   # the swap is formula-blind
        pay = self._amide_hydrolysis_candidate_payload()
        for entry in pay["products"]:
            if entry["species"]["structure"] == _structural_species_to_payload(four)["structure"]:
                entry["species"] = _structural_species_to_payload(two)
        pay["products"].sort(key=_species_digest_of_payload)   # keep canonical order so ONLY the replay fires
        with pytest.raises(ValueError, match="GRAPH level|does not replay"):
            _structural_candidate_from_payload(pay)

    def test_a_witness_whose_graph_edit_is_tampered_is_refused(self):
        # tamper the witness's cut so the reconstructed edit no longer matches the advertised witness_digest.
        pay = self._amide_hydrolysis_candidate_payload()
        assert pay["witness"]["cut"], "a capped-scission witness carries cut bonds"
        # bump the bond order of the first cut bond -> a different (or invalid) edit: it is caught either at the
        # family certificate (reconstructing the transform) or at the witness_digest/replay check -- both are the
        # tamper being refused on read, never a silently-trusted witness.
        pay["witness"]["cut"][0][2] += 1
        with pytest.raises(ValueError, match="witness|replay|valence|reconstruct|cut bond|bond of the joined"):
            _structural_candidate_from_payload(pay)

    def test_a_witness_lifted_from_a_different_candidate_is_refused(self):
        # graft candidate B's witness onto candidate A: B's edit replays to B's products, not A's -> refused.
        ir = _para_ir()
        assert len(ir.structural_candidates) >= 2
        a = _structural_candidate_to_payload(ir.structural_candidates[0])
        b = _structural_candidate_to_payload(ir.structural_candidates[1])
        assert a["witness_digest"] != b["witness_digest"]
        a_grafted = dict(a)
        a_grafted["witness"] = b["witness"]
        a_grafted["witness_digest"] = b["witness_digest"]
        a_grafted["edit_equation"] = b["edit_equation"]
        with pytest.raises(ValueError, match="different structure|does not replay|GRAPH level"):
            _structural_candidate_from_payload(a_grafted)

    def test_the_witness_is_a_required_serialized_field(self):
        # the witness rides IN the candidate payload (hence in the candidate/IR digest, which is why the schema
        # bumped v1alpha5 -> v1alpha6); a payload missing it is refused on read, not silently defaulted.
        pay = self._amide_hydrolysis_candidate_payload()
        assert "witness" in pay and pay["witness"]["witness_kind"] == "CAPPED_SCISSION"
        del pay["witness"]
        with pytest.raises((KeyError, ValueError, TypeError)):
            _structural_candidate_from_payload(pay)

    def test_a_bond_order_edit_witness_replays_through_the_reagentless_family(self):
        # CHEM-ALG-01's reagentless family also carries a re-verifiable witness (bond_edit, no cut/caps/reagents).
        ir = decompile_structure_to_ir(ETHANE, reagents=(WATER,), registry=_extended_registry())
        boe = [sc for sc in ir.structural_candidates if sc.witness_kind == "BOND_ORDER_EDIT"]
        assert boe, "ethane must yield a bond-order (dehydrogenation) candidate under the extended algebra"
        for sc in boe:
            w = sc.witness
            assert w.reagents == () and w.cut == () and w.caps == () and len(w.bond_edit) == 4
            assert w.replay_transform().digest == sc.witness_digest
        assert deserialize_ir(serialize_ir(ir)).digest == ir.digest


ASPIRIN = parse_smiles("CC(=O)Oc1ccccc1C(=O)O")   # acetylsalicylic acid, C9H8O4


class TestStructureRebuildingInverse:
    """Item 1 -- the structure-rebuilding inverse: reconstitute the target STRUCTURE from a decompile artifact with
    NO caller-supplied structure (the audit's B0 headline). recompile_from_serialized needs a caller structure
    because a FORMULA does not fix one; a STRUCTURE artifact carries molecular graphs + re-verifiable witnesses, so
    the target is READ FROM the artifact and each capped-scission candidate's inverse reconstitutes it -- the
    decompile->recompile loop closing at the graph level. W3 unchanged: invertibility, never a validated synthesis.
    """

    def test_every_capped_candidate_reconstitutes_its_parent(self):
        ir = _para_ir()
        assert ir.structural_candidates
        for sc in ir.structural_candidates:
            rebuilt = sc.reconstitute_parent()
            assert rebuilt == sc.parent.molecule == PARA.canonical()

    def test_the_headline_reconstitutes_the_target_with_no_caller_structure(self):
        from smartchem.compilation_ir import recompile_structure_from_serialized, StructureInverseStatus
        ir = _para_ir()
        # NOTE: no structure= argument anywhere -- the target is rebuilt from the artifact alone.
        res = recompile_structure_from_serialized(serialize_ir(ir))
        assert res.status is StructureInverseStatus.RECONSTITUTED
        assert res.reconstituted
        assert res.reconstituted_target == PARA.canonical()
        assert res.inverted_count == len(ir.structural_candidates) and res.deferred_count == 0

    def test_the_inverse_returns_the_real_structure_not_a_constant(self):
        # reconstitute is structure-SPECIFIC: an aspirin decomposition reconstitutes ASPIRIN, a paracetamol one
        # PARACETAMOL -- distinct structures (not a fixed constant).  NB the genuine NON-vacuity (that it CONSUMES the
        # products, not just echoes the reactant) is proven by TestRedTeamFoldRound2::
        # test_reconstitute_parent_consumes_the_products_not_just_the_reactant_edit; this only pins structure-specificity.
        para_ir = _para_ir()
        asp_ir = decompile_structure_to_ir(ASPIRIN, reagents=(WATER,))
        assert asp_ir.structural_candidates, "aspirin must have a capped-scission decomposition"
        p = para_ir.structural_candidates[0].reconstitute_parent()
        a = asp_ir.structural_candidates[0].reconstitute_parent()
        assert p == PARA.canonical() and a == ASPIRIN.canonical() and p != a

    def test_a_formula_artifact_is_routed_out_not_misinverted(self):
        from smartchem.compilation_ir import recompile_structure_from_serialized, StructureInverseStatus
        res = recompile_structure_from_serialized(serialize_ir(decompile_to_ir("C8H9NO2")))
        assert res.status is StructureInverseStatus.NOT_A_STRUCTURE_DECOMPILE
        assert res.reconstituted_target is None

    def test_a_bond_order_only_artifact_defers_and_does_not_fake(self):
        # the reagentless bond-order family's inverse is a NAMED FOLLOW-ON (H2 carries no skeleton); it is reported
        # as deferred, never faked with a vacuous echo of the stored reactant.
        from smartchem.compilation_ir import recompile_structure_from_serialized, StructureInverseStatus
        from smartchem.transform_provider import TransformProviderRegistry
        from smartchem.bond_order_edit import BondOrderEditProvider
        ir = decompile_structure_to_ir(ETHANE, reagents=(WATER,),
                                       registry=TransformProviderRegistry((BondOrderEditProvider(),)))
        assert ir.structural_candidates
        res = recompile_structure_from_serialized(serialize_ir(ir))
        assert res.status is StructureInverseStatus.NO_INVERTIBLE_FAMILY
        assert res.deferred_count == len(ir.structural_candidates) and res.reconstituted_target is None

    def test_the_bond_order_inverse_raises_rather_than_echo(self):
        ir = decompile_structure_to_ir(ETHANE, reagents=(WATER,), registry=_extended_registry())
        boe = next(sc for sc in ir.structural_candidates if sc.witness_kind == "BOND_ORDER_EDIT")
        with pytest.raises(NotImplementedError, match="follow-on|skeleton"):
            boe.witness.rebuild_parent()

    def test_a_tampered_structure_artifact_is_refused_before_the_inverse_runs(self):
        # the recompile input is the item-4-guarded artifact: an isomer-swapped product is refused on deserialize,
        # so the inverse never runs on a corrupt decomposition.
        from smartchem.compilation_ir import recompile_structure_from_serialized
        four = StructuralSpecies.of_molecule(AMINOPHENOL)
        two = StructuralSpecies.of_molecule(ORTHO_AMINOPHENOL)
        payload = ir_to_payload(_para_ir())
        for cand in payload["structural_candidates"]:
            for entry in cand["products"]:
                if entry["species"]["structure"] == _structural_species_to_payload(four)["structure"]:
                    entry["species"] = _structural_species_to_payload(two)
            cand["products"].sort(key=_species_digest_of_payload)
        import json
        with pytest.raises(ValueError, match="GRAPH level|does not replay|sorted|distinct"):
            recompile_structure_from_serialized(json.dumps(payload, sort_keys=True))


class TestRedTeamFoldRound2:
    """Fold of the items-4/1/3/2 red-team (6 CONFIRMED). Each defect reproduced pre-fold and is refused/fixed here."""

    def test_reconstitute_parent_consumes_the_products_not_just_the_reactant_edit(self):
        # CONFIRMED MEDIUM (inverse-vacuity): rebuild_parent alone echoes the reactant, so its ==parent check could
        # never fail. reconstitute_parent now RE-VERIFIES the stored products against the witness replay (step 1), so
        # a swapped product set is refused -- proven by swapping products on a live candidate (bypassing __post_init__
        # via object.__setattr__ to hit reconstitute_parent's OWN guard, not the constructor's).
        ir = _para_ir()
        sc = ir.structural_candidates[0]
        assert sc.reconstitute_parent() == PARA.canonical()          # honest candidate reconstitutes
        object.__setattr__(sc, "products", ((StructuralSpecies.of_molecule(ASPIRIN), 1),))
        with pytest.raises(ValueError, match="stored products are not the witness|cannot be reconstituted"):
            sc.reconstitute_parent()

    def test_a_tampered_edit_equation_is_refused_on_read(self):
        # CONFIRMED LOW/MEDIUM (edit_equation is the HUMAN twin of witness_digest): a candidate whose machine identity
        # is honest but whose readable equation states false chemistry is refused, not trusted.
        payload = ir_to_payload(_para_ir())
        one = payload["structural_candidates"][0]
        one["edit_equation"] = "N2 + 3 H2 -> 2 NH3 (a reaction this edit does NOT perform)"
        payload["structural_candidates"] = [one]
        with pytest.raises(ValueError, match="edit_equation is not the witness edit's own equation"):
            ir_from_payload(payload)

    def test_the_recompile_note_names_the_rebuilt_molecule_not_the_target_repr(self):
        # CONFIRMED LOW: target.canonical_repr is a free field a tampered artifact can set to any string; the
        # RECONSTITUTED note must name the ACTUAL rebuilt molecule, not that unverified field.
        import json
        from smartchem.compilation_ir import recompile_structure_from_serialized
        payload = ir_to_payload(_para_ir())
        payload["target"]["canonical_repr"] = "TOTALLY_NOT_PARACETAMOL"
        res = recompile_structure_from_serialized(json.dumps(payload, sort_keys=True))
        assert "TOTALLY_NOT_PARACETAMOL" not in res.note
        assert "C8H9NO2" in res.note and res.reconstituted_target == PARA.canonical()


class TestExistingProducersUnaffected:
    def test_formula_decompile_still_works_and_carries_no_structural_candidates(self):
        ir = decompile_to_ir("C8H9NO2")
        assert ir.structural_candidates == ()
        assert ir.target.layer is IdentityLayer.FORMULA
        assert deserialize_ir(serialize_ir(ir)).digest == ir.digest    # v1alpha7 round-trip intact

    def test_recompile_still_works_and_carries_no_structural_candidates(self):
        ir = recompile_to_ir(PARA, reagents=(WATER,), available=(AMINOPHENOL,), max_depth=1)
        assert ir.structural_candidates == ()
        assert deserialize_ir(serialize_ir(ir)).digest == ir.digest
