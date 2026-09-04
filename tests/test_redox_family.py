"""Item 1 -- the REDOX (electron-transfer) transform family rides the transform algebra.

`RedoxHalfReaction` existed as a charge-conserving structural certificate (``reduced -> oxidized + n e-``) but had
NO forgetful projection and no uniform transform interface, so no redox family could ride the IR.  Item 1 gives it
the uniform interface (`reactant`/`reagents`/`products`/`forget`) and a new charge-carrying `ElectronTransferEdge`
forget target, registers it through a `RedoxHalfReactionProvider`, and it rides the SAME
`StructuralCandidate`/`StructuralWitness` machinery as the other families -- the algebra reaching the chemical<->EM
bridge with no engine fork (Lane B, the [[electromagnetic-scope]] payoff).

A redox step is CHARGE-ONLY (same atoms, same bonds -- it makes and breaks nothing), so it is the first family whose
"decomposition" does not reduce the species' size; it is DECOMPILE-only and OPT-IN (absent from the default
registry).  An electron is a massless charge carrier with NO atoms, so it can never be a `StructuralSpecies` nor a
`Formula`; it rides the witness's integer `electrons` count and the `ElectronTransferEdge`, never as a product
species.

W3 unchanged: a redox candidate is a `FORMAL_CANDIDATE` -- it certifies a charge-and-mass-consistent electron
transfer EXISTS, never that the oxidation occurs, at what potential, or that the oxidation state is accessible.
"""

import pytest

from smartchem.category import Bond, Molecule
from smartchem.decompiler import Formula
from smartchem.structure_descent import (
    ELECTRON,
    REDOX_SCHEMA,
    ElectronTransferEdge,
    RedoxHalfReaction,
    ScissionError,
    redox_couples,
)
from smartchem.transform_provider import (
    CappedScissionProvider,
    RedoxHalfReactionProvider,
    TransformProviderRegistry,
)
from smartchem.compilation_ir import (
    IdentityLayer,
    StructuralSpecies,
    StructureInverseStatus,
    decompile_structure_to_ir,
    deserialize_ir,
    ir_from_payload,
    ir_to_payload,
    recompile_structure_from_serialized,
    serialize_ir,
)

NA = Molecule(("Na",), frozenset(), 0, "")               # Na -> Na^+ + e- (the real first ionisation)
NO = Molecule(("N", "O"), frozenset({Bond(0, 1, 2)}), 0, "")   # NO -> NO^+ + e- (nitrosonium, a real molecular redox)
DUMMY_REAGENT = Molecule(("O",), frozenset(), 0, "")     # redox ignores the reagent pool; the API still wants one
REDOX_REGISTRY = TransformProviderRegistry((RedoxHalfReactionProvider(),))
MIXED_REGISTRY = TransformProviderRegistry((CappedScissionProvider(), RedoxHalfReactionProvider()))


def _redox_ir(reactant=NA, registry=REDOX_REGISTRY):
    return decompile_structure_to_ir(reactant, reagents=(DUMMY_REAGENT,), registry=registry)


class TestUniformInterfaceAndElectronForget:
    def test_redox_exposes_the_uniform_transform_interface(self):
        r = redox_couples(NA, max_electrons=1)[0]
        assert r.reactant is r.reduced and r.reagents == ()          # reactant==reduced, reagentless
        assert r.products[0] == r.oxidized and all(p is ELECTRON for p in r.products[1:])
        edge = r.forget()
        assert type(edge) is ElectronTransferEdge

    def test_the_electron_edge_conserves_mass_and_charge(self):
        r = redox_couples(NA, max_electrons=1)[0]           # Na -> Na^+ + e-
        edge = r.forget()
        # mass: an electron is massless, so the oxidised species carries EXACTLY the reactant atoms
        assert dict(edge.reactant.counts) == dict(edge.oxidized.counts) == {"Na": 1}
        # charge: oxidised(+1) - 1 e- == reactant(0)
        assert edge.oxidized.charge - edge.electrons == edge.reactant.charge == 0

    def test_a_charge_non_conserving_electron_edge_is_refused(self):
        # THE point of the electron edge: Na^+ from Na removing ZERO electrons is charge-non-conserving -> refused.
        with pytest.raises(ScissionError, match="charge not conserved|at least one electron"):
            ElectronTransferEdge(Formula.of({"Na": 1}, 0), 1, Formula.of({"Na": 1}, 1), 0)

    def test_a_mass_non_conserving_electron_edge_is_refused(self):
        # a redox step moves electrons, NOT atoms: an oxidised species with different atoms is refused.
        with pytest.raises(ScissionError, match="mass not conserved"):
            ElectronTransferEdge(Formula.of({"Na": 1}, 0), 1, Formula.of({"Na": 1, "O": 1}, 1), 1)


class TestRedoxFamilyRidesTheIR:
    def test_the_redox_decompile_emits_electron_transfer_candidates(self):
        ir = _redox_ir()
        assert ir.target.layer is IdentityLayer.STRUCTURE
        assert ir.structural_candidates
        for sc in ir.structural_candidates:
            assert sc.witness_kind == "REDOX_HALF_REACTION"
            assert sc.projection_kind == "ELECTRON_TRANSFER_EDGE"
            assert sc.readiness_tier == "FORMAL_CANDIDATE"       # W3: no evidence claim
            assert sc.reagents == ()                             # reagentless
            assert len(sc.products) == 1                         # exactly one product species (the oxidised form)

    def test_the_real_first_ionisation_is_among_the_candidates(self):
        # Na -> Na^+ + e- (the real first ionisation) is enumerated, with the electron count on the witness.
        ir = _redox_ir()
        one_e = [sc for sc in ir.structural_candidates if sc.witness.electrons == 1]
        assert one_e and one_e[0].products[0][0].structure.canonical_repr == "Na^1+"

    def test_the_forgetful_square_holds_for_the_redox_family(self):
        ir = _redox_ir()
        for sc in ir.structural_candidates:
            recomputed = sc._recompute_projection()
            assert recomputed.digest == sc.projection_digest and recomputed.equation() == sc.projection_equation

    def test_a_tampered_projection_is_refused_on_read(self):
        ir = _redox_ir()
        payload = ir_to_payload(ir)
        one = payload["structural_candidates"][0]
        one["projection_digest"] = "0" * 64
        payload["structural_candidates"] = [one]
        with pytest.raises(ValueError, match="commuting|square|projection"):
            ir_from_payload(payload)

    def test_round_trip_is_digest_stable(self):
        for reactant in (NA, NO):
            ir = _redox_ir(reactant=reactant)
            assert deserialize_ir(serialize_ir(ir)).digest == ir.digest

    def test_the_default_registry_emits_no_redox_candidate(self):
        # redox is OPT-IN: the DEFAULT (capped-only) algebra never emits a redox candidate.
        ir = decompile_structure_to_ir(NO, reagents=(DUMMY_REAGENT,))   # default registry
        assert all(sc.witness_kind != "REDOX_HALF_REACTION" for sc in ir.structural_candidates)


class TestRedoxGraphReplayAndInverse:
    def test_the_witness_replays_to_the_oxidised_species_plus_electrons(self):
        from collections import Counter
        ir = _redox_ir()
        for sc in ir.structural_candidates:
            t = sc.witness.replay_transform()
            assert t.digest == sc.witness_digest
            replayed = Counter(m.canonical() for m in t.products)
            stored = Counter(s.molecule.canonical() for s, m in sc.products for _ in range(m))
            stored[ELECTRON.canonical()] += sc.witness.electrons     # the massless carriers ride the witness count
            assert replayed == stored

    def test_a_tampered_witness_electron_count_is_refused(self):
        ir = _redox_ir()
        payload = ir_to_payload(ir)
        one = payload["structural_candidates"][0]
        one["witness"]["electrons"] += 1     # now the witness replays a DIFFERENT oxidised charge / a new digest
        payload["structural_candidates"] = [one]
        with pytest.raises(ValueError, match="witness|replay|digest|charge|GRAPH"):
            ir_from_payload(payload)

    def test_the_redox_inverse_recovers_the_reduced_parent(self):
        # item 1: the charge-only inverse re-adds the transferred electrons -> the reduced parent.
        for reactant in (NA, NO):
            ir = _redox_ir(reactant=reactant)
            res = recompile_structure_from_serialized(serialize_ir(ir))
            assert res.status is StructureInverseStatus.RECONSTITUTED
            assert res.reconstituted_target == reactant.canonical()
            for sc in ir.structural_candidates:
                assert sc.reconstitute_parent() == reactant.canonical()

    def test_the_inverse_is_non_vacuous_a_swapped_product_is_refused(self):
        # soundness is NOT a reactant echo: swapping the oxidised product to a DIFFERENT species is refused at
        # reconstitute step 1 (the product-consuming check), reproduced on a live candidate.
        ir = _redox_ir()
        sc = ir.structural_candidates[0]
        assert sc.reconstitute_parent() == NA.canonical()
        mg2 = Molecule(("Mg",), frozenset(), 2, "")
        object.__setattr__(sc, "products", ((StructuralSpecies.of_molecule(mg2), 1),))
        with pytest.raises(ValueError, match="stored products are not the witness|cannot be reconstituted"):
            sc.reconstitute_parent()


class TestElectronsAreNotSpecies:
    def test_an_electron_cannot_be_a_structural_species(self):
        # a massless charge carrier has NO atoms, so StructuralSpecies (which requires >=1 atom) refuses it -- which
        # is exactly why electrons ride the witness count + the edge, never a product species.
        assert ELECTRON.atoms == ()
        with pytest.raises((ValueError, TypeError)):
            StructuralSpecies.of_molecule(ELECTRON)

    def test_the_oxidised_product_shares_the_parent_graph_differing_only_in_charge(self):
        # a redox step makes/breaks no bonds: the single product species has the SAME atoms and bonds as the parent,
        # differing ONLY in charge -- the charge-only signature of the family.
        ir = _redox_ir(reactant=NO)
        for sc in ir.structural_candidates:
            (oxidised, _mult), = sc.products
            assert oxidised.atoms == sc.parent.atoms and oxidised.bonds == sc.parent.bonds
            assert oxidised.charge == sc.parent.charge + sc.witness.electrons


class TestProviderIdentityAndScope:
    def test_the_redox_provider_manifest_declares_the_electron_transfer_projection(self):
        manifest = dict(RedoxHalfReactionProvider().capability_manifest)
        assert manifest["charged"] is True
        assert manifest["projection_kind"] == "ELECTRON_TRANSFER_EDGE"
        assert manifest["max_electrons"] == 2

    def test_the_registry_digest_moves_with_the_redox_provider(self):
        capped_only = TransformProviderRegistry((CappedScissionProvider(),))
        assert MIXED_REGISTRY.digest != capped_only.digest
        assert "redox-half-reaction" in MIXED_REGISTRY.provider_ids

    def test_max_electrons_rides_the_manifest_so_a_bump_moves_the_digest(self):
        # the enumeration bound is a declared capability, so widening it changes the registry identity (section 8.4).
        r2 = TransformProviderRegistry((RedoxHalfReactionProvider(max_electrons=2),))
        r3 = TransformProviderRegistry((RedoxHalfReactionProvider(max_electrons=3),))
        assert r2.digest != r3.digest

    def test_a_mixed_registry_carries_the_redox_family_through_the_unchanged_seam(self):
        # NO over water: no capped cleavage, but a redox couple -> the mixed (capped+redox) registry surfaces the
        # redox family through the SAME decompile seam (composition through the unchanged core, no engine branch).
        water = Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}), 0, "")
        ir = decompile_structure_to_ir(NO, reagents=(water,), registry=MIXED_REGISTRY)
        assert "REDOX_HALF_REACTION" in {sc.witness_kind for sc in ir.structural_candidates}


class TestRedTeamFold:
    """Fold of the item-1 red-team (1 CONFIRMED MEDIUM). The electron count was validated only with a LOWER bound
    (>= 1) and the charge certificate is TAUTOLOGICAL in n, so a crafted serialized artifact could carry an absurd
    count (e.g. 10**18) that passed every digest/conservation check and then materialized a (ELECTRON,)*n tuple --
    a MemoryError / slow-burn DoS through the public deserialize_ir boundary. Fixed: a LIVE physical UPPER bound
    (8 * atom count, the max +8 oxidation state) at the RedoxHalfReaction certificate, so an absurd count is refused
    on read (and on replay) BEFORE .products is ever touched."""

    def test_the_electron_count_has_a_live_physical_upper_bound(self):
        # a 1-atom species (Na) cannot shed more than 8*1 electrons; AT the bound is accepted, one OVER is refused.
        RedoxHalfReaction(REDOX_SCHEMA, NA, Molecule(("Na",), frozenset(), 8, ""), 8)         # 8 == 8*1: accepted
        with pytest.raises(ScissionError, match="at most|oxidation state"):
            RedoxHalfReaction(REDOX_SCHEMA, NA, Molecule(("Na",), frozenset(), 9, ""), 9)     # 9 > 8: refused
        # NO (2 atoms) -> ceiling 16
        RedoxHalfReaction(REDOX_SCHEMA, NO, Molecule(("N", "O"), frozenset({Bond(0, 1, 2)}), 16, ""), 16)
        with pytest.raises(ScissionError, match="at most|oxidation state"):
            RedoxHalfReaction(REDOX_SCHEMA, NO, Molecule(("N", "O"), frozenset({Bond(0, 1, 2)}), 17, ""), 17)

    def test_an_absurd_electron_count_is_refused_on_deserialize_without_a_dos(self):
        # THE attack: a serialized artifact carrying electrons=10**18 must be REFUSED on read, NOT materialize a
        # (ELECTRON,)*10**18 tuple. The bound fires at the witness replay -> RedoxHalfReaction certificate, before
        # .products (a lazy property) is ever touched, so the refusal is instant on a few-KB payload.
        import json
        import time
        ir = _redox_ir()
        payload = ir_to_payload(ir)
        payload["structural_candidates"][0]["witness"]["electrons"] = 10**18
        text = json.dumps(payload, sort_keys=True)
        t0 = time.time()
        with pytest.raises((ScissionError, ValueError)):
            deserialize_ir(text)
        assert time.time() - t0 < 5.0, "the refusal must be instant -- no (ELECTRON,)*n materialization (the DoS)"

    def test_redox_couples_never_enumerates_past_the_physical_ceiling(self):
        # a generous max_electrons on a 1-atom species is capped at 8*1=8, so the enumerator never constructs a
        # half-reaction the certificate would refuse (enumerator and certificate agree on the bound).
        couples = redox_couples(NA, max_electrons=1000)
        assert len(couples) == 8 and all(c.electrons <= 8 for c in couples)
