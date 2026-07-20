"""
SmartChem: a compositional layer above quantum chemistry.

Reactions are typed morphisms in a symmetric monoidal category whose objects carry bond
topology, so conservation is enforced at construction and inherited by every composite.
The environment is a Store comonad, so one local definition yields an entire response
surface. Mechanism search is a Writer-over-List monad, so energy bookkeeping and provenance
cannot drift out of step with the route. Energy comes from a pluggable oracle, so accuracy
is a dial you set rather than a property you inherit.

    from smartchem import Config, Molecule, Reaction, favourability
    from smartchem.oracle.pyscf_oracle import PySCFOracle

    rxn = Reaction(Config.atoms("C", "O"),
                   Config.of(Molecule.diatomic("C", "O", order=3)))
    favourability(rxn, PySCFOracle("CCSD(T)", "aug-cbs(TZ,QZ)"))

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
    is_isodesmic,
    reaction_residue,
    tensor_obj,
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
    "braid", "catalytic_cycle", "conserves", "identity", "is_catalytic",
    "bond_order_profile", "bond_signature", "is_bond_order_conserving", "is_isodesmic",
    "reaction_residue", "tensor_obj",
    # store -- the environment comonad and response surfaces
    "Store", "Conditions", "SOLVENTS",
    "survey", "response_surface", "is_responsive", "grid",
    "argmin_position", "argmax_position",
    # pathway -- the mechanism-search monad
    "Pathway", "Tally", "Step", "Mechanism",
    "search", "catalytic_cycles", "best_route",
    # thermo -- the energy functor
    "configuration_energy", "reaction_energy", "bonding_energy",
    "is_exothermic", "favourability",
    # geometry -- coordinates derived from the bond graph the object already carries
    "GeometryError", "RelaxResult", "VibrationalAnalysis",
    "seed_coordinates", "seed_bond_length", "relax", "harmonic_analysis", "is_linear",
]
