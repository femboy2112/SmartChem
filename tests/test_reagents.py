"""Poor-man's buckets: a commodity terminal set for retrosynthesis + a chemist's shopping list.

The load-bearing test is ``test_retrosynthesis_terminates_at_commodities`` -- proof that the existing
route enumerator bottoms out at obtainable stock with no new mechanism, and the shopping list reads back
what a chemist would actually buy.
"""
from __future__ import annotations

from smartchem.data.reagents import (
    COMMODITY_REAGENTS,
    Availability,
    CommodityReagent,
    commodity_for,
    commodity_inventory,
    is_commodity,
    shopping_list,
)
from smartchem.experiment.routes import enumerate_routes
from smartchem.structure import structure_by_name


class TestInventoryIntegrity:
    def test_all_commodities_build_with_unique_identities(self):
        assert len(COMMODITY_REAGENTS) >= 12
        idents = {commodity_for(r.molecule).name for r in COMMODITY_REAGENTS}
        # every entry resolves to exactly itself, so identities are unique
        assert len(idents) == len(COMMODITY_REAGENTS)

    def test_every_entry_is_well_formed(self):
        for r in COMMODITY_REAGENTS:
            assert isinstance(r, CommodityReagent)
            assert isinstance(r.availability, Availability)
            assert r.common_source and r.identity_basis

    def test_flagship_table_salt_is_present_and_grocery(self):
        salt = commodity_for(structure_salt())
        assert salt is not None
        assert salt.name == "sodium chloride"
        assert salt.common_source == "table salt"
        assert salt.availability is Availability.GROCERY

    def test_identity_basis_distinguishes_sourced_from_constructed(self):
        bases = {r.identity_basis for r in COMMODITY_REAGENTS}
        assert any("registry" in b for b in bases)      # organics grounded in the sourced registry
        assert any("constructed" in b for b in bases)    # salts from explicit Lewis skeletons


class TestCommodityMembership:
    def test_registry_organic_is_a_commodity(self):
        assert is_commodity(structure_by_name("acetic acid").molecule) is True
        assert commodity_for(structure_by_name("acetic acid").molecule).common_source.startswith("white vinegar")

    def test_non_commodity_is_not(self):
        # acetic anhydride is not a poor-man's commodity (it is a controlled/lab reagent)
        assert is_commodity(structure_by_name("acetic anhydride").molecule) is False
        assert commodity_for(structure_by_name("acetic anhydride").molecule) is None


class TestRetrosynthesisTermination:
    def test_retrosynthesis_terminates_at_commodities(self):
        # Acetic anhydride retrosynthesises to 2 acetic acid (+ water) -- both commodities.
        an = structure_by_name("acetic anhydride").molecule
        water = structure_by_name("water").molecule
        routes = enumerate_routes(an, reagents=(water,), available=commodity_inventory(), max_depth=2)
        assert routes, "expected at least one commodity-terminated route"
        names = {r.name for route in routes for r in shopping_list(route)}
        assert "acetic acid" in names

    def test_shopping_list_is_the_commodity_leaves(self):
        an = structure_by_name("acetic anhydride").molecule
        water = structure_by_name("water").molecule
        routes = enumerate_routes(an, reagents=(water,), available=commodity_inventory(), max_depth=2)
        sl = shopping_list(routes[0])
        # every item on the list is genuinely a commodity, deduplicated, name-ordered
        assert all(is_commodity(r.molecule) for r in sl)
        assert [r.name for r in sl] == sorted({r.name for r in sl})

    def test_internally_produced_commodity_is_not_a_purchase(self):
        from smartchem.experiment.step import ExperimentRoute, ExperimentStep
        from smartchem.smiles import parse_smiles

        ethanol, oxygen, acid, water, anhydride = (
            parse_smiles(s) for s in ("CCO", "O=O", "CC(=O)O", "O", "CC(=O)OC(=O)C")
        )
        make_acid = ExperimentStep.assembling(acid, (ethanol, oxygen), (acid, water))
        use_acid = ExperimentStep.assembling(anhydride, (acid, acid), (anhydride, water))
        names = {r.name for r in shopping_list(ExperimentRoute.of(make_acid, use_acid))}
        assert "acetic acid" not in names
        assert "ethanol" in names


def structure_salt():
    from smartchem.category import Bond, Molecule
    return Molecule(atoms=("Na", "Cl"), bonds=frozenset({Bond(0, 1)}))
