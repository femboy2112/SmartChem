"""
SmartChem: a conserving sequential-history layer above quantum chemistry.

Reactions are typed morphisms whose objects carry bond topology, so conservation is
enforced at construction and inherited by sequential composites. Configurations have a
commutative multiset product; morphisms do not yet have a true parallel tensor because a
linear history cannot satisfy interchange. ``Reaction.tensor`` is a compatibility name for
an explicit left-first schedule while the future open-system layer gains ports/process graphs.
The Store comonad represents a condition-indexed query plus a focus; finite response-surface
utilities explicitly evaluate that query at requested positions. Mechanism search has a
Writer-over-List shape and appends caller-supplied energy/provenance tallies alongside route
transitions. Energy comes from a pluggable oracle whose coverage and measured accuracy are
method- and domain-dependent.

    from smartchem import Config, Molecule, Reaction, favourability
    from smartchem.oracle.pyscf_oracle import PySCFOracle

    rxn = Reaction(Config.atoms("C", "O"),
                   Config.of(Molecule.diatomic("C", "O", order=3)))
    favourability(rxn, PySCFOracle("CCSD(T)", "cbs(TZ,QZ)", tight_d=False))

``smartchem.legacy`` holds the frozen original engine. It is kept executable so the
accuracy comparison stays checkable, and it is not exported here: new work builds on
``category``, ``store``, ``pathway`` and ``thermo``.
"""
from .category import (
    Bond,
    Config,
    ConservationError,
    CompositionError,
    Molecule,
    Reaction,
    UNIT,
    bond_order_profile,
    bond_signature,
    braid,
    catalytic_cycle,
    conserves,
    identity,
    is_bond_order_conserving,
    is_catalytic,
    is_regenerated,
    is_isodesmic,
    reaction_residue,
    tensor_obj,
)
from .domain import (
    EVERYTHING,
    NOTHING,
    Domain,
    DomainContradiction,
)
from .stoichiometry import (
    Completion,
    MenuContradiction,
    StoichiometryMenu,
    composition_matrix,
    integer_kernel_basis,
    stoichiometry_menu,
)
from .store import (
    Conditions,
    SOLVENTS,
    Store,
    argmax_position,
    argmin_position,
    grid,
    is_responsive,
    response_surface,
    survey,
)
from .pathway import (
    Mechanism,
    Pathway,
    Step,
    Tally,
    best_route,
    catalytic_cycles,
    search,
)
from .thermo import (
    bonding_energy,
    configuration_energy,
    favourability,
    is_exothermic,
    reaction_energy,
)
from .geometry import (
    GeometryError,
    RelaxResult,
    VibrationalAnalysis,
    harmonic_analysis,
    is_linear,
    relax,
    seed_bond_length,
    seed_coordinates,
)

__all__ = [
    # category -- objects, morphisms, and the conservation theorem
    "Bond", "Config", "Molecule", "Reaction", "UNIT",
    "ConservationError", "CompositionError",
    "braid", "catalytic_cycle", "conserves", "identity", "is_catalytic", "is_regenerated",
    "bond_order_profile", "bond_signature", "is_bond_order_conserving", "is_isodesmic",
    "reaction_residue", "tensor_obj",
    # stoichiometry -- the inverse of `conserves`: derive the balances, never guess them
    "Completion", "StoichiometryMenu", "MenuContradiction",
    "composition_matrix", "integer_kernel_basis", "stoichiometry_menu",

    # domain -- what an oracle declares it can price, before being called
    "Domain", "DomainContradiction", "EVERYTHING", "NOTHING",
    # store -- the environment comonad and finite response-surface sampling
    "Store", "Conditions", "SOLVENTS",
    "survey", "response_surface", "is_responsive", "grid",
    "argmin_position", "argmax_position",
    # pathway -- Writer/List-style branching search (float accumulation is approximate)
    "Pathway", "Tally", "Step", "Mechanism",
    "search", "catalytic_cycles", "best_route",
    # thermo -- separable endpoint-energy adapter
    "configuration_energy", "reaction_energy", "bonding_energy",
    "is_exothermic", "favourability",
    # geometry -- candidate coordinates seeded from the bond graph
    "GeometryError", "RelaxResult", "VibrationalAnalysis",
    "seed_coordinates", "seed_bond_length", "relax", "harmonic_analysis", "is_linear",
]
