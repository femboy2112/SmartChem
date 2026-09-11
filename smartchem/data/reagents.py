"""Poor-man's buckets: a curated inventory of WIDELY AVAILABLE commodity chemicals.

The decompiler bottoms a synthesis out at ELEMENTAL buckets ({C, H, N, O, Na, ...}) -- correct, but useless
to someone who cannot get elemental sodium yet can buy a carton of table salt.  This module is the other
terminal set: the compounds a layperson can actually obtain (a grocery store, a hardware store, a pharmacy,
a pool-supply shop), so retrosynthesis can stop at "stuff you can buy" and hand back a SHOPPING LIST instead
of an element-collector's fantasy.

It plugs into the existing machinery with ZERO new mechanism: :func:`~smartchem.experiment.routes.enumerate_routes`
already terminates a branch when a precursor's canonical identity is in its ``available`` set.  Pass
:func:`commodity_inventory` as ``available`` and routes bottom out at commodities; :func:`shopping_list`
then reads back which commodities a route actually needs.

HONESTY -- what is grounded vs what is curated
----------------------------------------------
* The chemical IDENTITY (structure / formula) of every entry is grounded: organics resolve through the
  sourced structure registry (:func:`~smartchem.structure.structure_by_name`); the inorganic salts/acids are
  constructed here from their explicit, well-known Lewis skeletons (sodium chloride IS Na-Cl -- a definition,
  not a measurement) and checked to build and canonicalise.
* The AVAILABILITY tier and the everyday-source note are a CURATED obtainability judgment -- editorial, not a
  sourced physical constant -- and are labelled as such.  They say "you can commonly buy this here"; they do
  not assert a price, a purity, or a legal status (many commodities are sold dilute or impure, and local law
  varies).  This is an aid for a chemist, not a procurement guarantee.

This module adds NO physics and asserts NO reaction.  It is a terminal set for the retrosynthesis, nothing more.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..category import Bond, Molecule
from ..contracts import Digestible, canonical_digest
from ..structure import structure_by_name

__all__ = [
    "Availability",
    "CommodityReagent",
    "COMMODITY_REAGENTS",
    "commodity_inventory",
    "commodity_for",
    "is_commodity",
    "shopping_list",
]


class Availability(str, Enum):
    """Where a layperson can commonly obtain the compound.  A CURATED obtainability judgment, ordered
    easiest-first; NOT a sourced constant, a price, or a legal claim.

    ``INDUSTRIAL`` is the hardest tier and the honest opposite of a "kitchen" commodity: a chemical-supplier /
    industrial-only material a layperson CANNOT buy at a grocery/pharmacy/hardware/pool store (elemental bromine,
    chlorine gas).  It is a load-bearing poor-man signal -- a route that needs an INDUSTRIAL reagent is not
    kitchen-satisfiable and must be surfaced as such, never silently treated as obtainable."""

    GROCERY = "grocery"          # supermarket / kitchen staple
    PHARMACY = "pharmacy"        # drugstore
    HARDWARE = "hardware"        # hardware / DIY / automotive store
    POOL_GARDEN = "pool_garden"  # pool-supply / garden centre
    INDUSTRIAL = "industrial"    # chemical-supplier / industrial only -- NOT a layperson/kitchen commodity (hardest)


@dataclass(frozen=True)
class CommodityReagent(Digestible):
    """One widely-available commodity chemical: a grounded identity + a curated obtainability note."""

    name: str
    molecule: Molecule
    availability: Availability
    common_source: str      # the everyday product it is found in ("white vinegar, ~5% aqueous")
    identity_basis: str     # how the structure is grounded (registry, or an explicit construction)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")
        if type(self.molecule) is not Molecule:
            raise TypeError("molecule must be a Molecule")
        if not isinstance(self.availability, Availability):
            raise TypeError("availability must be an Availability")
        for f in ("common_source", "identity_basis"):
            if not isinstance(getattr(self, f), str) or not getattr(self, f):
                raise ValueError(f"{f} must be a non-empty string")

    @property
    def formula(self) -> dict:
        return self.molecule.formula

    def render(self) -> str:
        return (f"{self.name} ({self.common_source}) [{self.availability.value}]")


def _mol(atoms: tuple[str, ...], bonds: set) -> Molecule:
    return Molecule(atoms=atoms, bonds=frozenset(bonds))


def _named(name: str) -> Molecule:
    """The Molecule for a registry-known organic commodity (grounded, matches decompiler output)."""
    s = structure_by_name(name)
    if s is None:  # pragma: no cover -- guards against a registry rename
        raise KeyError(f"commodity {name!r} is not in the structure registry")
    return s.molecule


# --- the curated commodity inventory ---------------------------------------------------------------
# Organics resolve through the sourced structure registry; the inorganic salts/acids are constructed from
# their explicit Lewis skeletons.  Availability + source are curated obtainability notes (see module docstring).
COMMODITY_REAGENTS: tuple[CommodityReagent, ...] = (
    # --- registry-grounded organics ---
    CommodityReagent("water", _named("water"), Availability.GROCERY,
                     "tap/distilled water", "structure registry"),
    CommodityReagent("acetic acid", _named("acetic acid"), Availability.GROCERY,
                     "white vinegar, ~5-8% aqueous", "structure registry"),
    CommodityReagent("ethanol", _named("ethanol"), Availability.GROCERY,
                     "spirits / fuel-grade / sanitiser", "structure registry"),
    CommodityReagent("propan-2-ol", _named("propan-2-ol"), Availability.PHARMACY,
                     "isopropyl rubbing alcohol, 70-99%", "structure registry"),
    CommodityReagent("acetone", _named("acetone"), Availability.HARDWARE,
                     "nail-polish remover / hardware solvent", "structure registry"),
    CommodityReagent("hydrogen peroxide", _named("hydrogen peroxide"), Availability.PHARMACY,
                     "drugstore 3% / salon-grade higher", "structure registry"),
    CommodityReagent("ammonia", _named("ammonia"), Availability.GROCERY,
                     "household cleaning ammonia, aqueous", "structure registry"),
    CommodityReagent("methanol", _named("methanol"), Availability.HARDWARE,
                     "fuel-line antifreeze / camp-stove fuel", "structure registry"),
    CommodityReagent("formic acid", _named("formic acid"), Availability.HARDWARE,
                     "descaler / some ant-sting products", "structure registry"),
    # --- registry-grounded purchasable SCAFFOLDS (Lane-B reachability, R48) ---
    # Real buyable aromatic/heterocyclic building blocks, so retrosynthesis of a common molecule can terminate at
    # obtainable stock instead of at an un-buyable ring core.  Chosen by the SAME target-independent rule as the rest
    # (commonly purchasable, honestly tagged by WHERE + tier) -- NOT a per-target curation: it includes salicylic acid,
    # which is NOT a precursor of either north star (caffeine/paracetamol), proving the catalog is not a 2-target
    # curation, and the higher tiers (PHARMACY/HARDWARE) are surfaced as such, never treated as a kitchen staple.
    # Identity is registry-grounded; the availability tier/source is a curated obtainability note (see module
    # docstring), asserting no price, purity, or legal status.  (Aspirin is deliberately NOT admitted: it is itself a
    # registered synthesis target with existing producibility/bench-fit coverage, and making it buyable stock would
    # short-circuit that coverage -- the poor man can just buy aspirin, but the test bench still needs to synthesise it.)
    CommodityReagent("theophylline", _named("theophylline"), Availability.PHARMACY,
                     "bronchodilator tablets; also veterinary -- OTC in some regions, prescription in others",
                     "structure registry"),
    CommodityReagent("4-aminophenol", _named("4-aminophenol"), Availability.HARDWARE,
                     "photographic developer (para-aminophenol / 'Rodinal'); photo-supply / specialty retail",
                     "structure registry"),
    CommodityReagent("salicylic acid", _named("salicylic acid"), Availability.PHARMACY,
                     "OTC wart / acne topical", "structure registry"),
    # --- constructed inorganic salts / acids (identity = explicit Lewis skeleton) ---
    CommodityReagent("sodium chloride", _mol(("Na", "Cl"), {Bond(0, 1)}), Availability.GROCERY,
                     "table salt", "constructed: Na-Cl"),
    CommodityReagent("sodium bicarbonate",
                     _mol(("Na", "O", "C", "O", "O", "H"),
                          {Bond(0, 1), Bond(1, 2), Bond(2, 3, 2), Bond(2, 4), Bond(4, 5)}),
                     Availability.GROCERY, "baking soda", "constructed: Na-O-C(=O)-O-H"),
    CommodityReagent("sodium carbonate",
                     _mol(("Na", "O", "C", "O", "O", "Na"),
                          {Bond(0, 1), Bond(1, 2), Bond(2, 3, 2), Bond(2, 4), Bond(4, 5)}),
                     Availability.GROCERY, "washing soda / soda ash", "constructed: Na-O-C(=O)-O-Na"),
    CommodityReagent("sodium hydroxide", _mol(("Na", "O", "H"), {Bond(0, 1), Bond(1, 2)}),
                     Availability.HARDWARE, "lye / caustic drain cleaner", "constructed: Na-O-H"),
    CommodityReagent("sodium hypochlorite", _mol(("Na", "O", "Cl"), {Bond(0, 1), Bond(1, 2)}),
                     Availability.GROCERY, "chlorine bleach, aqueous", "constructed: Na-O-Cl"),
    CommodityReagent("sulfuric acid",
                     _mol(("S", "O", "O", "O", "O", "H", "H"),
                          {Bond(0, 1, 2), Bond(0, 2, 2), Bond(0, 3), Bond(0, 4), Bond(3, 5), Bond(4, 6)}),
                     Availability.HARDWARE, "concentrated drain opener, automotive battery acid",
                     "constructed: (HO)2S(=O)2"),
    # elemental bromine: the DOW-bromine litmus's target commodity.  INDUSTRIAL, not a kitchen product -- a layperson
    # cannot buy Br2 (the whole DOW insight is that you MAKE it from cheap bromide, not buy it).  USGS-priced (see
    # commodity_pricing.py); the diatomic Lewis skeleton Br-Br is the identity the price binds to.
    CommodityReagent("bromine", _mol(("Br", "Br"), {Bond(0, 1)}), Availability.INDUSTRIAL,
                     "elemental bromine -- chemical-supplier / industrial only; NOT a consumer or kitchen product",
                     "constructed: Br-Br"),
)


def _index() -> dict[str, CommodityReagent]:
    """canonical identity -> commodity reagent.  Built once, tolerant of an un-canonicalisable identity."""
    out: dict[str, CommodityReagent] = {}
    for r in COMMODITY_REAGENTS:
        out[_identity(r.molecule)] = r
    return out


def _identity(m: Molecule) -> str:
    try:
        return canonical_digest(m.canonical())
    except NotImplementedError:
        return "asgiven:" + canonical_digest(m)


_COMMODITY_INDEX = _index()


def commodity_inventory() -> tuple[Molecule, ...]:
    """The commodity Molecules, to pass as ``available=`` to
    :func:`~smartchem.experiment.routes.enumerate_routes` so retrosynthesis terminates at obtainable stock."""
    return tuple(r.molecule for r in COMMODITY_REAGENTS)


def commodity_for(molecule: Molecule) -> CommodityReagent | None:
    """The commodity reagent matching ``molecule`` by canonical identity, or ``None`` (not a commodity)."""
    return _COMMODITY_INDEX.get(_identity(molecule))


def is_commodity(molecule: Molecule) -> bool:
    return _identity(molecule) in _COMMODITY_INDEX


def shopping_list(route) -> tuple[CommodityReagent, ...]:
    """The commodity EXTERNAL LEAVES of a route/DAG -- deduplicated and ordered by name.

    A commodity made by an earlier step and consumed later is an intermediate, not something the user must
    buy.  The old all-reactants scan incorrectly listed such intermediates.  A leaf is a reactant whose
    identity is produced by no step in the selected synthesis.  Quantities and commercial formulation remain
    a separate, currently unmodelled material-specification problem.
    """
    found: dict[str, CommodityReagent] = {}
    made = {_identity(step.target) for step in route.steps}
    for step in route.steps:
        for m in step.reactants:
            if _identity(m) in made:
                continue
            r = commodity_for(m)
            if r is not None:
                found[r.name] = r
    return tuple(sorted(found.values(), key=lambda r: r.name))
