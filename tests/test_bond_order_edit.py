"""CHEM-ALG-01: the bond-order-edit family -- a SECOND, qualitatively distinct transform algebra.

The genericity thesis says SmartChem is a bounded SEARCH compiler parameterized by a transform algebra; this brick
proves a second family (partial bond-order edit / dehydrogenation) registers through :class:`TransformProvider` and
composes through the UNCHANGED core search, with no bespoke engine branch.  Each guarantee is pinned non-vacuously:
  * FAMILY   -- the enumeration is real chemistry: ethane -> ethene + H2, cyclohexane -> cyclohexene + H2, and a
                molecule with no raisable bond (methane) yields nothing;
  * IR       -- a bond-order candidate rides the structural decompile IR alongside capped scissions, as a
                FORMAL_CANDIDATE with a DECOMPOSITION_EDGE projection and NO reagents, and round-trips;
  * SQUARE   -- its forgetful square (a reagentless DecompositionEdge) is enforced; a tampered projection is refused;
  * COMPOSE  -- with the extended algebra the hydrogenation route ``H2 + C2H4 -> C2H6`` is found through the SAME
                search code; with the default (capped-only) algebra it is NOT -- the search never changed, the
                algebra did;
  * COHERENCE-- a bond-order candidate must carry empty reagents; a capped candidate must not.
"""
import copy

import pytest

from smartchem.bond_order_edit import (
    BOND_ORDER_EDIT_SCHEMA,
    BondOrderEdit,
    BondOrderEditProvider,
    bond_order_edits,
)
from smartchem.compilation_ir import (
    decompile_structure_to_ir,
    deserialize_ir,
    ir_from_payload,
    ir_to_payload,
    serialize_ir,
)
from smartchem.experiment.routes import search_routes
from smartchem.smiles import parse_smiles
from smartchem.structure_descent import ScissionError
from smartchem.transform_provider import CappedScissionProvider, TransformProviderRegistry

ETHANE = parse_smiles("CC")
ETHENE = parse_smiles("C=C")
ACETYLENE = parse_smiles("C#C")
CYCLOHEXANE = parse_smiles("C1CCCCC1")
METHANE = parse_smiles("C")
WATER = parse_smiles("O")
H2 = parse_smiles("[H][H]")

EXT = TransformProviderRegistry((CappedScissionProvider(), BondOrderEditProvider()))


class TestFamilyEnumeration:
    def test_ethane_dehydrogenates_to_ethene_plus_h2(self):
        edits, complete = bond_order_edits(ETHANE)
        assert complete and len(edits) == 1
        assert edits[0].forget().equation() == "C2H6 -> C2H4 + 2 H"   # reactant -> ethene + H2 (element bucket)
        assert edits[0].reagents == ()                                # consumes no reagent

    def test_methane_has_no_bond_order_edit(self):
        edits, complete = bond_order_edits(METHANE)
        assert complete and edits == ()

    def test_cyclohexane_dehydrogenates(self):
        edits, complete = bond_order_edits(CYCLOHEXANE)
        assert complete and len(edits) >= 1
        assert edits[0].forget().equation() == "C6H12 -> C6H10 + 2 H"

    def test_a_triple_bond_cannot_be_raised(self):
        edits, complete = bond_order_edits(ACETYLENE)   # C#C is already maximal order
        assert complete and edits == ()


class TestCertificate:
    def _one(self):
        edits, _ = bond_order_edits(ETHANE)
        return edits[0]

    def test_equal_bond_endpoints_are_refused(self):
        e = self._one()
        with pytest.raises(ScissionError, match="distinct in-range atom indices"):
            BondOrderEdit(BOND_ORDER_EDIT_SCHEMA, ETHANE, e.bond_i, e.bond_i, e.h_i, e.h_j)

    def test_a_non_bonded_pair_is_refused(self):
        # two hydrogens (2 and 5 in canonical ethane) are distinct, in range, but not bonded to each other.
        with pytest.raises(ScissionError, match="not a bond of the reactant"):
            BondOrderEdit(BOND_ORDER_EDIT_SCHEMA, ETHANE, 2, 5, 0, 1)

    def test_a_non_hydrogen_shed_is_refused(self):
        e = self._one()
        # bond_j itself is a carbon, not an H bonded to bond_i
        with pytest.raises(ScissionError, match="must be an order-1 hydrogen"):
            BondOrderEdit(BOND_ORDER_EDIT_SCHEMA, ETHANE, e.bond_i, e.bond_j, e.bond_j, e.h_j)


class TestRidesTheIR:
    def _ext_ir(self):
        return decompile_structure_to_ir(ETHANE, reagents=(WATER,), registry=EXT)

    def _boe(self, ir):
        return [c for c in ir.structural_candidates if c.witness_kind == "BOND_ORDER_EDIT"]

    def test_a_bond_order_candidate_rides_the_decompile_ir(self):
        ir = self._ext_ir()
        boe = self._boe(ir)
        assert len(boe) == 1
        c = boe[0]
        assert c.readiness_tier == "FORMAL_CANDIDATE"          # W3: never a claim it runs
        assert c.projection_kind == "DECOMPOSITION_EDGE"
        assert c.reagents == ()                                # reagentless family
        assert c.provider_id == "bond-order-edit"
        # it rides ALONGSIDE capped scissions -- one IR, two families
        assert any(x.witness_kind == "CAPPED_SCISSION" for x in ir.structural_candidates)

    def test_round_trip_is_digest_stable(self):
        ir = self._ext_ir()
        assert deserialize_ir(serialize_ir(ir)).digest == ir.digest
        assert ir.transform_registry_digest == EXT.digest      # the IR names the extended algebra

    def test_the_forgetful_square_holds_and_a_tampered_projection_is_refused(self):
        ir = self._ext_ir()
        payload = ir_to_payload(ir)
        touched = False
        for c in payload["structural_candidates"]:
            if c["witness_kind"] == "BOND_ORDER_EDIT":
                c["projection_digest"] = "0" * 64
                touched = True
        assert touched
        with pytest.raises(ValueError, match="commuting square|not the forget"):
            ir_from_payload(payload)


class TestComposesThroughUnchangedSearch:
    def test_the_hydrogenation_route_composes_with_the_extended_algebra(self):
        res = search_routes(ETHANE, reagents=(WATER,), available=(ETHENE, H2), max_depth=1, registry=EXT)
        eqs = [" ; ".join(r.equation_lines()) for r in res.routes]
        assert any("C2H4" in e and "C2H6" in e for e in eqs)   # H2 + C2H4 -> C2H6, a hydrogenation

    def test_the_default_capped_only_algebra_does_not_find_it(self):
        # the SAME search code, the SAME query -- only the algebra differs.  The default has no bond-order family,
        # so the hydrogenation route does not exist for it.  This is the whole point: no engine branch, just the
        # registry parameter.
        res = search_routes(ETHANE, reagents=(WATER,), available=(ETHENE, H2), max_depth=1)
        assert len(res.routes) == 0

    def test_it_composes_through_the_unchanged_DAG_search_too(self):
        from smartchem.experiment.routes import search_dags
        ext = search_dags(ETHANE, reagents=(WATER,), available=(ETHENE, H2), max_depth=1, registry=EXT)
        default = search_dags(ETHANE, reagents=(WATER,), available=(ETHENE, H2), max_depth=1)
        assert len(ext.dags) >= 1 and len(default.dags) == 0


class TestReagentlessCoherence:
    def test_a_bond_order_candidate_carrying_a_reagent_is_refused(self):
        # inject a reagent into a bond-order candidate's payload -> refused (the family consumes none).
        ir = decompile_structure_to_ir(ETHANE, reagents=(WATER,), registry=EXT)
        payload = ir_to_payload(ir)
        capped = next(c for c in payload["structural_candidates"] if c["witness_kind"] == "CAPPED_SCISSION")
        boe = next(c for c in payload["structural_candidates"] if c["witness_kind"] == "BOND_ORDER_EDIT")
        boe["reagents"] = copy.deepcopy(capped["reagents"])    # a bond-order edit with a reagent
        payload["structural_candidates"] = [boe]
        with pytest.raises(ValueError, match="consumes no reagent"):
            ir_from_payload(payload)

    def test_a_capped_candidate_with_no_reagents_is_refused(self):
        ir = decompile_structure_to_ir(parse_smiles("CC(=O)Nc1ccc(O)cc1"), reagents=(WATER,))
        payload = ir_to_payload(ir)
        one = payload["structural_candidates"][0]
        one["reagents"] = []                                    # a mediated cleavage with no reagent
        payload["structural_candidates"] = [one]
        with pytest.raises(ValueError, match="non-empty"):
            ir_from_payload(payload)
