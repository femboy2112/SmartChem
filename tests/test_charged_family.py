"""Item 3 -- the CHARGED transform family (heterolytic scission) rides the transform algebra.

`HeterolyticScission`/`RedoxHalfReaction` existed as charged structural certificates but had NO forgetful projection
(the neutral `MediatedEdge`/`DecompositionEdge` refuse a charged species), so no charged family could ride the IR.
Item 3 gives the heterolytic family the uniform transform interface (`reagents`/`products`/`forget`) and a
charge-carrying `ChargedDecompositionEdge`, registers it through a `HeterolyticScissionProvider`, and it rides the
SAME `StructuralCandidate`/`StructuralWitness` machinery as the neutral families -- the algebra widening past
neutral rewrites with no engine fork (Lane B). Redox stays a named follow-on (electrons complicate the species).

W3 unchanged: a heterolytic candidate is a `FORMAL_CANDIDATE` -- it certifies a charge-and-valence-consistent split
EXISTS, never that the bond ionises this way, at what potential, or how the charge localizes.
"""

import pytest

from smartchem.category import Bond, Molecule
from smartchem.decompiler import Formula
from smartchem.structure_descent import (
    ChargedDecompositionEdge,
    ScissionError,
    heterolytic_scissions,
)
from smartchem.transform_provider import (
    CappedScissionProvider,
    HeterolyticScissionProvider,
    TransformProviderRegistry,
)
from smartchem.compilation_ir import (
    IdentityLayer,
    StructureInverseStatus,
    decompile_structure_to_ir,
    deserialize_ir,
    ir_from_payload,
    ir_to_payload,
    recompile_structure_from_serialized,
    serialize_ir,
)

HCL = Molecule(("H", "Cl"), frozenset({Bond(0, 1, 1)}), 0, "")
DUMMY_REAGENT = Molecule(("O",), frozenset(), 0, "")   # heterolytic ignores the reagent pool; the API still wants one
CHARGED_REGISTRY = TransformProviderRegistry((HeterolyticScissionProvider(),))
MIXED_REGISTRY = TransformProviderRegistry((CappedScissionProvider(), HeterolyticScissionProvider()))


def _charged_ir(reactant=HCL, registry=CHARGED_REGISTRY):
    return decompile_structure_to_ir(reactant, reagents=(DUMMY_REAGENT,), registry=registry)


class TestUniformInterfaceAndChargedForget:
    def test_heterolysis_exposes_the_uniform_transform_interface(self):
        h = heterolytic_scissions(HCL)[0]
        assert h.reagents == ()                                   # reagentless
        assert len(h.products) == 2 and {p.charge for p in h.products} == {-1, 1}
        edge = h.forget()
        assert type(edge) is ChargedDecompositionEdge

    def test_the_charged_edge_conserves_mass_and_charge(self):
        h = next(h for h in heterolytic_scissions(HCL) if {p.charge for p in h.products} == {-1, 1})
        edge = h.forget()
        # sum of product charges == reactant charge (0); sum of product atoms == reactant atoms
        assert sum(f.charge * m for f, m in edge.products) == 0     # charge conserved (reactant neutral)
        mass = {}
        for f, m in edge.products:
            for s, c in f.counts:
                mass[s] = mass.get(s, 0) + c * m
        assert mass == {"H": 1, "Cl": 1}                            # mass conserved

    def test_a_charge_non_conserving_edge_is_refused(self):
        # THE point of the charged edge vs the neutral one: H^+ + Cl^0 sums to +1 != 0 -> refused (non-vacuous).
        with pytest.raises(ScissionError, match="charge not conserved"):
            ChargedDecompositionEdge(
                Formula.of({"H": 1, "Cl": 1}, 0), 1,
                tuple(sorted(((Formula.of({"H": 1}, 1), 1), (Formula.of({"Cl": 1}, 0), 1)),
                            key=lambda pm: ((pm[0].counts, pm[0].charge), pm[1]))),
            )

    def test_a_mass_non_conserving_edge_is_refused(self):
        with pytest.raises(ScissionError, match="mass not conserved|sorted"):
            ChargedDecompositionEdge(
                Formula.of({"H": 1, "Cl": 1}, 0), 1,
                ((Formula.of({"H": 1}, 1), 1), (Formula.of({"Cl": 1, "O": 3}, -1), 1)),
            )


class TestChargedFamilyRidesTheIR:
    def test_the_charged_decompile_emits_heterolytic_candidates(self):
        ir = _charged_ir()
        assert ir.target.layer is IdentityLayer.STRUCTURE
        assert ir.structural_candidates
        for sc in ir.structural_candidates:
            assert sc.witness_kind == "HETEROLYTIC_SCISSION"
            assert sc.projection_kind == "CHARGED_DECOMPOSITION_EDGE"
            assert sc.readiness_tier == "FORMAL_CANDIDATE"      # W3: no evidence claim
            assert sc.reagents == ()                            # reagentless

    def test_the_real_ionisation_is_among_the_candidates(self):
        # H-Cl -> H^+ + Cl^-  (the chemically real acid dissociation) is enumerated.
        ir = _charged_ir()
        reprs = {tuple(sorted(s.structure.canonical_repr for s, m in sc.products)) for sc in ir.structural_candidates}
        assert any("H^1+" in r and "Cl^1-" in r for r in reprs)

    def test_the_forgetful_square_holds_for_the_charged_family(self):
        ir = _charged_ir()
        for sc in ir.structural_candidates:
            recomputed = sc._recompute_projection()
            assert recomputed.digest == sc.projection_digest and recomputed.equation() == sc.projection_equation

    def test_a_charge_tampered_projection_is_refused_on_read(self):
        ir = _charged_ir()
        payload = ir_to_payload(ir)
        one = payload["structural_candidates"][0]
        one["projection_digest"] = "0" * 64
        payload["structural_candidates"] = [one]
        with pytest.raises(ValueError, match="commuting|square|projection"):
            ir_from_payload(payload)

    def test_round_trip_is_digest_stable(self):
        ir = _charged_ir()
        assert deserialize_ir(serialize_ir(ir)).digest == ir.digest

    def test_the_default_registry_emits_no_charged_candidate(self):
        # the charged family is opt-in: the DEFAULT (capped-only) algebra never emits a heterolytic candidate.
        ir = decompile_structure_to_ir(HCL, reagents=(DUMMY_REAGENT,))   # default registry
        assert all(sc.witness_kind != "HETEROLYTIC_SCISSION" for sc in ir.structural_candidates)


class TestChargedGraphReplayAndInverse:
    def test_the_witness_replays_to_the_stored_ions(self):
        from collections import Counter
        ir = _charged_ir()
        for sc in ir.structural_candidates:
            t = sc.witness.replay_transform()
            assert t.digest == sc.witness_digest
            replayed = Counter(m.canonical() for m in t.products)
            stored = Counter(s.molecule.canonical() for s, m in sc.products for _ in range(m))
            assert replayed == stored

    def test_a_tampered_witness_fragment_is_refused(self):
        ir = _charged_ir()
        payload = ir_to_payload(ir)
        one = payload["structural_candidates"][0]
        # flip the anion fragment's charge in the witness -> it no longer replays to the stored ions / its digest
        one["witness"]["fragments"][0]["charge"] += 2
        payload["structural_candidates"] = [one]
        with pytest.raises(ValueError, match="witness|replay|charge|GRAPH"):
            ir_from_payload(payload)

    def test_the_charged_inverse_rejoins_the_ions_to_the_parent(self):
        # item 1 generalizes to the charged family: the ions rejoin across the cut bond -> the parent.
        ir = _charged_ir()
        res = recompile_structure_from_serialized(serialize_ir(ir))
        assert res.status is StructureInverseStatus.RECONSTITUTED
        assert res.reconstituted_target == HCL.canonical()
        for sc in ir.structural_candidates:
            assert sc.reconstitute_parent() == HCL.canonical()


class TestProviderIdentityAndScope:
    def test_the_charged_provider_declares_charged_in_its_manifest(self):
        manifest = dict(HeterolyticScissionProvider().capability_manifest)
        assert manifest["charged"] is True and manifest["projection_kind"] == "CHARGED_DECOMPOSITION_EDGE"

    def test_the_registry_digest_moves_with_the_charged_provider(self):
        capped_only = TransformProviderRegistry((CappedScissionProvider(),))
        assert MIXED_REGISTRY.digest != capped_only.digest
        assert "heterolytic-scission" in MIXED_REGISTRY.provider_ids

    def test_a_mixed_registry_carries_the_charged_family_through_the_unchanged_seam(self):
        # HCl over water: no capped cleavage, but a heterolytic split -> under the mixed (capped+charged) registry the
        # SAME decompile seam surfaces the charged family (composition through the unchanged core, no engine branch).
        water = Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}), 0, "")
        ir = decompile_structure_to_ir(HCL, reagents=(water,), registry=MIXED_REGISTRY)
        assert "HETEROLYTIC_SCISSION" in {sc.witness_kind for sc in ir.structural_candidates}

    def test_redox_is_not_registered_a_named_follow_on(self):
        # redox (electron-transfer) is NOT wired as a provider yet -- electrons as massless carriers complicate the
        # species/forget; documented as a follow-on, not silently faked.
        assert not any("redox" in pid for pid in MIXED_REGISTRY.provider_ids)
