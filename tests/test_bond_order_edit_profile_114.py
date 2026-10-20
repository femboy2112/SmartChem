"""CHEM-ALG-01 #114: the bond-order-edit (de/hydrogenation) family wired behind the OPT-IN ``bond-order-edit-v1``
algebra profile.

The ``BondOrderEditProvider`` and its construction certificate already exist and are tested in
``test_bond_order_edit.py``.  This brick pins the #114 deliverable on top of that: a NAMED, selectable, reviewed
profile that makes the synthesis-direction hydrogenation route reachable, plus the two INDEPENDENT invariants the
mega-round mandate (§5) asks for -- bond-order and stoichiometry -- each re-derived from PUBLIC molecule fields by a
different route than the provider's own ``_precursor``/``forget`` machinery, so they are a genuine second witness and
not a re-run of the implementation.  The load-bearing soundness pin is TestNoFalseVouch: wiring a generator behind a
profile must NOT mint a reaction vouch for a family that has no oracle recognizer -- the route is reachable (W1/W3)
and the readiness layer correctly withholds the vouch (the honesty boundary stated in bond_order_edit.py:222-223).
"""
from __future__ import annotations

from collections import Counter

import pytest

from smartchem.algebra_profiles import (
    DEFAULT_ALGEBRA_PROFILE,
    DEFAULT_ROUTE_ALGEBRA_PROFILE,
    LEGACY_MISSING_ALGEBRA_PROFILE,
    PROFILE_USES,
    algebra_profile_ids,
    resolve_algebra_profile,
)
from smartchem.bond_order_edit import bond_order_edits
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type_outcome
from smartchem.experiment.routes import search_dags, search_routes
from smartchem.experiment.step import ExperimentStep
from smartchem.identity_parse import InputKind
from smartchem.service import build_recompile_request
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import DEFAULT_TRANSFORM_REGISTRY, ProviderUse

PROFILE = "bond-order-edit-v1"

ETHANE = parse_smiles("CC")
ETHENE = parse_smiles("C=C")
H2 = parse_smiles("[H][H]")
WATER = parse_smiles("O")

# molecules with at least one raisable heavy-heavy bond (de/hydrogenation positives)
_POSITIVES = [
    parse_smiles("CC"),          # ethane
    parse_smiles("CCC"),         # propane
    parse_smiles("CCCC"),        # butane
    parse_smiles("CC(C)C"),      # isobutane
    parse_smiles("C1CCCCC1"),    # cyclohexane
]


# -- the independent witnesses (read ONLY public Molecule fields; no call into _precursor/forget) ----------------
def _precursor_of(edit):
    """The non-H2 product of a bond-order edit, selected by PUBLIC fields only (the precursor is the product that
    still carries a heavy atom).  Independent of the provider's internal ``_precursor``."""
    carriers = [p for p in edit.products if set(p.atoms) != {"H"}]
    assert len(carriers) == 1, "a de/hydrogenation yields exactly one heavy precursor + H2"
    return carriers[0]


def _heavy_bond_orders(mol) -> Counter:
    """Multiset of bond ORDERS among bonds whose BOTH endpoints are non-hydrogen -- representation-robust (reads
    orders, never an aromaticity flag)."""
    return Counter(b.order for b in mol.bonds if mol.atoms[b.i] != "H" and mol.atoms[b.j] != "H")


def _elements(mol) -> Counter:
    """Element histogram straight off ``mol.atoms`` -- independent of the ``Molecule.formula`` property."""
    return Counter(mol.atoms)


class TestProfileWiring:
    def test_profile_resolves_to_capped_plus_bond_order(self):
        reg = resolve_algebra_profile(PROFILE)
        assert reg.provider_ids == ("capped-scission-mediated", "bond-order-edit")

    def test_profile_id_is_in_the_closed_set(self):
        assert PROFILE in algebra_profile_ids()

    def test_profile_is_coherent_for_every_topology(self):
        # both members support all three uses, so the intersection the request layer checks is all three.
        assert PROFILE_USES[PROFILE] == frozenset(
            {ProviderUse.STRUCTURE_DECOMPILE, ProviderUse.LINEAR_ROUTE, ProviderUse.CONVERGENT_DAG}
        )

    def test_the_profile_is_selectable_through_the_public_request_front_door(self):
        # a production request naming the profile is ACCEPTED (not an INVALID_INPUT refusal) and round-trips its id.
        req = build_recompile_request("CC", input_kind=InputKind.SMILES, helper_reagents=(), algebra_profile=PROFILE)
        assert req.algebra_profile == PROFILE


class TestNoDefaultFlip:
    """The opt-in invariant (mirrors tests/test_v0_7_production_algebra.py): adding the profile moved NO default."""

    def test_the_three_default_constants_are_untouched(self):
        assert DEFAULT_ALGEBRA_PROFILE == "legacy-capped-v1"
        assert LEGACY_MISSING_ALGEBRA_PROFILE == "legacy-capped-v1"
        assert DEFAULT_ROUTE_ALGEBRA_PROFILE == "certified-route-v07"  # NOT flipped to bond-order-edit-v1

    def test_the_default_transform_registry_is_still_capped_only(self):
        assert DEFAULT_TRANSFORM_REGISTRY.provider_ids == ("capped-scission-mediated",)

    def test_constructing_the_new_profile_did_not_perturb_legacy(self):
        legacy = resolve_algebra_profile("legacy-capped-v1")
        assert legacy.provider_ids == DEFAULT_TRANSFORM_REGISTRY.provider_ids
        assert legacy.digest == DEFAULT_TRANSFORM_REGISTRY.digest


class TestReachabilityVsDefault:
    """The gain: the hydrogenation route exists ONLY under the opt-in profile -- the search never changed."""

    def _has_hydrogenation(self, res) -> bool:
        return any(
            "C2H4" in " ".join(r.equation_lines()) and "C2H6" in " ".join(r.equation_lines())
            for r in res.routes
        )

    def test_the_route_is_found_under_the_opt_in_profile(self):
        reg = resolve_algebra_profile(PROFILE)
        res = search_routes(ETHANE, reagents=(WATER,), available=(ETHENE, H2), max_depth=1, registry=reg)
        assert self._has_hydrogenation(res)

    def test_neither_default_profile_reaches_it(self):
        for pid in ("legacy-capped-v1", "certified-route-v07"):
            reg = resolve_algebra_profile(pid)
            res = search_routes(ETHANE, reagents=(WATER,), available=(ETHENE, H2), max_depth=1, registry=reg)
            assert not self._has_hydrogenation(res), f"{pid} should not carry the bond-order family"

    def test_it_composes_through_the_convergent_dag_search_too(self):
        reg = resolve_algebra_profile(PROFILE)
        ext = search_dags(ETHANE, reagents=(WATER,), available=(ETHENE, H2), max_depth=1, registry=reg)
        assert len(ext.dags) >= 1


# targets whose hydrogenation PRODUCT shapes deliberately mimic other families' products -- the attribution-theft
# surface the #114 adversary pass hammered (DA-adduct ring, arene-adjacent, ether, ester, fused/branched).
_NOVOUCH_TARGETS = [
    "C1=CCCCC1",       # cyclohexene (from a DA-adduct-shaped diene) -- the worst case
    "C1CCCCC1",        # cyclohexane
    "CCc1ccccc1",      # ethylbenzene (arene-adjacent)
    "CC1CCCCC1",       # methylcyclohexane
    "CCCC",            # n-butane
    "CCC(C)C",         # 2-methylbutane
    "CCCc1ccccc1",     # propylbenzene
    "C1CCC2CCCCC2C1",  # decalin (fused)
    "CCOCC",           # diethyl ether (ether-shaped)
    "CCC(=O)OCC",      # ethyl propanoate (ester-shaped)
]


class TestNoFalseVouch:
    """SOUNDNESS PIN: a generator wired behind a profile must not mint a reaction vouch for a recognizer-less family.
    The oracle ABSTAINS on the hydrogenation step -- cleanly, not through a swallowed instrument error."""

    def test_the_oracle_abstains_on_the_reachable_route_step(self):
        reg = resolve_algebra_profile(PROFILE)
        res = search_routes(ETHANE, reagents=(WATER,), available=(ETHENE, H2), max_depth=1, registry=reg)
        assert res.routes, "expected the hydrogenation route to be reachable"
        for r in res.routes:
            for step in r.steps:
                out = recognize_reaction_type_outcome(step)
                assert not out.is_match           # never MATCH -> never REACTION_VOUCHED by this family
                assert not out.is_internal_error  # abstains CLEANLY (not an error disguised as a non-recognition)
                assert out.reaction_class is None

    @pytest.mark.parametrize("target_smiles", _NOVOUCH_TARGETS)
    def test_oracle_abstains_on_every_hydrogenation_step_the_family_can_emit(self, target_smiles):
        # Encodes the invariant the #114 adversary flagged as "emergent, not asserted anywhere": a future 2->1
        # recognizer that vouched an H2 addition (without reconstructing both declared reactants) would trip this.
        # Build the synthesis step the route layer presents to the oracle (precursor + H2 -> target) for EVERY edit.
        target = parse_smiles(target_smiles)
        edits, _ = bond_order_edits(target)
        assert edits, f"{target_smiles} must carry at least one raisable bond"
        for edit in edits:
            precursor = _precursor_of(edit)
            step = ExperimentStep.assembling(target, (precursor, H2), (target,), reagents=())
            out = recognize_reaction_type_outcome(step)
            assert not out.is_match, f"{target_smiles}: unexpected vouch -> {out.reaction_class}"
            assert not out.is_internal_error, f"{target_smiles}: internal recognizer error -> {out.faults}"


class TestIndependentBondOrder:
    """INDEPENDENT bond-order witness: every edit raises EXACTLY one heavy-heavy bond by EXACTLY one order and sheds
    EXACTLY two hydrogens -- re-derived from the public heavy-atom bond-order multiset, not the provider internals."""

    @pytest.mark.parametrize("reactant", _POSITIVES, ids=lambda m: "".join(m.atoms))
    def test_each_edit_raises_one_heavy_bond_by_one_and_sheds_two_h(self, reactant):
        edits, complete = bond_order_edits(reactant)
        assert complete and edits, "every positive has at least one raisable bond"
        for edit in edits:
            precursor = _precursor_of(edit)
            rb, pb = _heavy_bond_orders(reactant), _heavy_bond_orders(precursor)
            # the heavy-heavy bond COUNT is preserved (an order is raised, not a bond added or removed)
            assert sum(pb.values()) == sum(rb.values())
            gained, lost = pb - rb, rb - pb      # Counter diffs keep only the positive part of each direction
            assert sum(gained.values()) == 1 and sum(lost.values()) == 1, "exactly one heavy bond changed order"
            (gained_order, _), = gained.items()
            (lost_order, _), = lost.items()
            assert gained_order == lost_order + 1, "the one changed bond went up by exactly one order"
            # exactly two hydrogens shed
            assert _elements(reactant)["H"] - _elements(precursor)["H"] == 2


class TestIndependentStoichiometry:
    """INDEPENDENT stoichiometric witness: reactant atoms == precursor atoms + H2, by element-histogram arithmetic
    off ``mol.atoms`` -- never the ``Molecule.formula`` property nor ``forget``'s element-bucket merge."""

    @pytest.mark.parametrize("reactant", _POSITIVES, ids=lambda m: "".join(m.atoms))
    def test_atoms_balance_as_precursor_plus_h2(self, reactant):
        edits, _ = bond_order_edits(reactant)
        assert edits
        for edit in edits:
            precursor = _precursor_of(edit)
            rf, pf = _elements(reactant), _elements(precursor)
            assert rf - pf == Counter({"H": 2}), "reactant carries exactly two more H than the precursor"
            assert pf - rf == Counter(), "the precursor introduces no element the reactant lacks"
            assert reactant.charge == 0 and precursor.charge == 0, "the family is neutral-only"
            # the shed pair is exactly dihydrogen
            shed = next(p for p in edit.products if set(p.atoms) == {"H"})
            assert _elements(shed) == Counter({"H": 2}) and shed.charge == 0


class TestMeasuredReachabilityGain:
    """The committed bench is the measured artifact; this pins its verdict so the gain cannot silently regress."""

    def test_the_bench_validates(self):
        from experiments.bond_order_edit_profile_114 import validate

        ok, summary = validate()
        assert ok, summary
        assert summary["reachable_under_profile"] == summary["cases"]  # reachable in every case under the profile
        assert summary["reachable_under_defaults"] == 0                # unreachable under either default
        assert summary["false_vouch"] == 0                            # and no minted vouch for the recognizer-less family
