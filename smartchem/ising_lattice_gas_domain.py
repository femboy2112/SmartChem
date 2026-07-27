"""Exact finite Ising-to-lattice-gas change of variables on the three-cycle.

This module proves a deliberately narrow cross-domain analogue.  It enumerates every
microstate on the undirected graph C3 and applies ``s_i = 2*n_i - 1`` to

``H_I = -J sum_edges(s_i*s_j) - h sum_i(s_i)``

and

``H_LG = -epsilon sum_edges(n_i*n_j) - mu sum_i(n_i)``.

All energy parameters and derived exponents are exact integer ticks.  Beta remains a formal
symbol: this module does not hide floating exponentiation, sampling, a thermodynamic limit,
or dynamics behind an "exact" label.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from .contracts import canonical_digest

__all__ = [
    "C3_EDGES",
    "C3_VERTICES",
    "CompletenessInventory",
    "ExactEquilibriumMap",
    "FormalBoltzmannTerm",
    "IsingLatticeGasSpec",
    "MicrostateMap",
    "ParameterMap",
    "PartitionIdentity",
    "StateClass",
    "derive_exact_equilibrium_map",
    "exact_equilibrium_map_error",
]


C3_VERTICES = (0, 1, 2)
C3_EDGES = ((0, 1), (1, 2), (0, 2))


class _Digestible:
    @property
    def digest(self) -> str:
        return canonical_digest(self)


def _exact_int(name: str, value: object) -> None:
    if type(value) is not int:
        raise TypeError(f"{name} must be an exact integer")


def _text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _exact_int_tuple(
    name: str,
    value: object,
    *,
    length: int | None = None,
    allowed: frozenset[int] | None = None,
) -> None:
    if type(value) is not tuple or any(type(item) is not int for item in value):
        raise TypeError(f"{name} must be a tuple of exact integers")
    if length is not None and len(value) != length:
        raise ValueError(f"{name} must have length {length}")
    if allowed is not None and any(item not in allowed for item in value):
        raise ValueError(f"{name} contains a value outside {sorted(allowed)}")


@dataclass(frozen=True)
class IsingLatticeGasSpec(_Digestible):
    """Scientist-confirmed parameters for the one supported finite graph."""

    coupling_j_ticks: int
    field_h_ticks: int
    energy_unit: str = "abstract energy tick"
    beta_symbol: str = "beta"
    vertices: tuple[int, ...] = C3_VERTICES
    edges: tuple[tuple[int, int], ...] = C3_EDGES

    def __post_init__(self) -> None:
        _exact_int("coupling_j_ticks", self.coupling_j_ticks)
        _exact_int("field_h_ticks", self.field_h_ticks)
        _text("energy_unit", self.energy_unit)
        if self.beta_symbol != "beta":
            raise ValueError("beta_symbol must be exactly 'beta' for the formal executor")
        if type(self.vertices) is not tuple or self.vertices != C3_VERTICES:
            raise ValueError("the finite executor supports exactly vertices (0, 1, 2)")
        if type(self.edges) is not tuple or self.edges != C3_EDGES:
            raise ValueError(
                "the finite executor supports exactly the three undirected C3 edges "
                "((0, 1), (1, 2), (0, 2)), each counted once"
            )
        if any(
            type(edge) is not tuple
            or len(edge) != 2
            or any(type(vertex) is not int for vertex in edge)
            for edge in self.edges
        ):
            raise TypeError("edges must contain exact integer vertex pairs")


@dataclass(frozen=True)
class ParameterMap(_Digestible):
    coupling_j_ticks: int
    field_h_ticks: int
    attraction_epsilon_ticks: int
    chemical_potential_mu_ticks: int
    constant_shift_c_ticks: int

    def __post_init__(self) -> None:
        for name in (
            "coupling_j_ticks",
            "field_h_ticks",
            "attraction_epsilon_ticks",
            "chemical_potential_mu_ticks",
            "constant_shift_c_ticks",
        ):
            _exact_int(name, getattr(self, name))
        if self.attraction_epsilon_ticks != 4 * self.coupling_j_ticks:
            raise ValueError("epsilon must equal 4*J")
        if self.chemical_potential_mu_ticks != (
            2 * self.field_h_ticks - 4 * self.coupling_j_ticks
        ):
            raise ValueError("mu must equal 2*h - 4*J")
        if self.constant_shift_c_ticks != (
            3 * (self.field_h_ticks - self.coupling_j_ticks)
        ):
            raise ValueError("C must equal 3*(h - J)")


@dataclass(frozen=True)
class MicrostateMap(_Digestible):
    state_id: str
    occupancies: tuple[int, int, int]
    spins: tuple[int, int, int]
    occupied_count: int
    occupied_edge_count: int
    magnetization: int
    spin_edge_sum: int
    ising_energy_ticks: int
    lattice_energy_ticks: int
    constant_shift_ticks: int
    ising_boltzmann_exponent_ticks: int
    lattice_boltzmann_exponent_ticks: int

    def __post_init__(self) -> None:
        _text("state_id", self.state_id)
        _exact_int_tuple(
            "occupancies", self.occupancies, length=3, allowed=frozenset((0, 1))
        )
        _exact_int_tuple(
            "spins", self.spins, length=3, allowed=frozenset((-1, 1))
        )
        if self.spins != tuple(2 * item - 1 for item in self.occupancies):
            raise ValueError("spins must obey s_i = 2*n_i - 1")
        if self.state_id != "".join(str(item) for item in self.occupancies):
            raise ValueError("state_id must be the occupancy bit string")
        for name in (
            "occupied_count",
            "occupied_edge_count",
            "magnetization",
            "spin_edge_sum",
            "ising_energy_ticks",
            "lattice_energy_ticks",
            "constant_shift_ticks",
            "ising_boltzmann_exponent_ticks",
            "lattice_boltzmann_exponent_ticks",
        ):
            _exact_int(name, getattr(self, name))
        occupied_count = sum(self.occupancies)
        occupied_edges = sum(
            self.occupancies[left] * self.occupancies[right]
            for left, right in C3_EDGES
        )
        magnetization = sum(self.spins)
        spin_edges = sum(
            self.spins[left] * self.spins[right] for left, right in C3_EDGES
        )
        if (
            self.occupied_count != occupied_count
            or self.occupied_edge_count != occupied_edges
            or self.magnetization != magnetization
            or self.spin_edge_sum != spin_edges
        ):
            raise ValueError("microstate derived counts do not match its bits")
        if self.magnetization != 2 * occupied_count - 3:
            raise ValueError("magnetization identity M=2*N-3 failed")
        if self.spin_edge_sum != 4 * occupied_edges - 4 * occupied_count + 3:
            raise ValueError("edge identity sum(s_i*s_j)=4*Q-4*N+3 failed")
        if self.ising_energy_ticks != (
            self.lattice_energy_ticks + self.constant_shift_ticks
        ):
            raise ValueError("statewise energy identity H_I=H_LG+C failed")
        if self.ising_boltzmann_exponent_ticks != -self.ising_energy_ticks:
            raise ValueError("Ising formal Boltzmann exponent must equal -H_I")
        if self.lattice_boltzmann_exponent_ticks != -self.lattice_energy_ticks:
            raise ValueError("lattice formal Boltzmann exponent must equal -H_LG")


@dataclass(frozen=True)
class StateClass(_Digestible):
    occupied_count: int
    degeneracy: int
    state_ids: tuple[str, ...]
    occupied_edge_count: int
    magnetization: int
    spin_edge_sum: int
    ising_energy_ticks: int
    lattice_energy_ticks: int

    def __post_init__(self) -> None:
        for name in (
            "occupied_count",
            "degeneracy",
            "occupied_edge_count",
            "magnetization",
            "spin_edge_sum",
            "ising_energy_ticks",
            "lattice_energy_ticks",
        ):
            _exact_int(name, getattr(self, name))
        if type(self.state_ids) is not tuple or any(
            not isinstance(item, str) or not item for item in self.state_ids
        ):
            raise TypeError("state_ids must contain non-empty strings")
        if self.degeneracy != len(self.state_ids) or self.degeneracy < 1:
            raise ValueError("degeneracy must equal the retained state-id count")
        if len(set(self.state_ids)) != len(self.state_ids):
            raise ValueError("state_ids must be unique within a class")


@dataclass(frozen=True)
class FormalBoltzmannTerm(_Digestible):
    occupied_count: int
    degeneracy: int
    exponent_ticks: int

    def __post_init__(self) -> None:
        _exact_int("occupied_count", self.occupied_count)
        _exact_int("degeneracy", self.degeneracy)
        _exact_int("exponent_ticks", self.exponent_ticks)
        if not 0 <= self.occupied_count <= 3:
            raise ValueError("occupied_count must be in [0, 3]")
        if self.degeneracy < 1:
            raise ValueError("degeneracy must be positive")


@dataclass(frozen=True)
class PartitionIdentity(_Digestible):
    beta_symbol: str
    energy_unit: str
    lattice_terms: tuple[FormalBoltzmannTerm, ...]
    ising_terms: tuple[FormalBoltzmannTerm, ...]
    constant_shift_ticks: int
    statewise_relation: str
    partition_relation: str
    normalized_probability_relation: str

    def __post_init__(self) -> None:
        if self.beta_symbol != "beta":
            raise ValueError("partition identity requires the formal beta symbol")
        _text("energy_unit", self.energy_unit)
        for name in ("lattice_terms", "ising_terms"):
            values = getattr(self, name)
            if type(values) is not tuple or len(values) != 4:
                raise ValueError(f"{name} must retain exactly four occupancy classes")
            if any(type(item) is not FormalBoltzmannTerm for item in values):
                raise TypeError(f"{name} must contain exact FormalBoltzmannTerm values")
            if tuple(item.occupied_count for item in values) != (0, 1, 2, 3):
                raise ValueError(f"{name} must be ordered by occupied count 0,1,2,3")
        _exact_int("constant_shift_ticks", self.constant_shift_ticks)
        for name in (
            "statewise_relation",
            "partition_relation",
            "normalized_probability_relation",
        ):
            _text(name, getattr(self, name))
        if tuple(item.degeneracy for item in self.lattice_terms) != (1, 3, 3, 1):
            raise ValueError("lattice partition degeneracies must be 1,3,3,1")
        if tuple(item.degeneracy for item in self.ising_terms) != (1, 3, 3, 1):
            raise ValueError("Ising partition degeneracies must be 1,3,3,1")
        for lattice, ising in zip(self.lattice_terms, self.ising_terms):
            if (
                lattice.occupied_count != ising.occupied_count
                or lattice.degeneracy != ising.degeneracy
                or ising.exponent_ticks
                != lattice.exponent_ticks - self.constant_shift_ticks
            ):
                raise ValueError(
                    "partition terms must obey -H_I = -H_LG - C class by class"
                )


@dataclass(frozen=True)
class CompletenessInventory(_Digestible):
    expected_microstates: int
    retained_microstates: int
    unique_occupancy_states: int
    unique_spin_states: int
    retained_state_classes: int
    class_degeneracy_sum: int
    missing_state_ids: tuple[str, ...]
    duplicate_state_ids: tuple[str, ...]
    output_reduction_applied: bool

    def __post_init__(self) -> None:
        for name in (
            "expected_microstates",
            "retained_microstates",
            "unique_occupancy_states",
            "unique_spin_states",
            "retained_state_classes",
            "class_degeneracy_sum",
        ):
            _exact_int(name, getattr(self, name))
        for name in ("missing_state_ids", "duplicate_state_ids"):
            values = getattr(self, name)
            if type(values) is not tuple or any(
                not isinstance(item, str) or not item for item in values
            ):
                raise TypeError(f"{name} must be a tuple of non-empty strings")
        if type(self.output_reduction_applied) is not bool:
            raise TypeError("output_reduction_applied must be a boolean")


@dataclass(frozen=True)
class ExactEquilibriumMap(_Digestible):
    spec: IsingLatticeGasSpec
    parameters: ParameterMap
    states: tuple[MicrostateMap, ...]
    classes: tuple[StateClass, ...]
    partition: PartitionIdentity
    completeness: CompletenessInventory

    def __post_init__(self) -> None:
        if type(self.spec) is not IsingLatticeGasSpec:
            raise TypeError("spec must be an exact IsingLatticeGasSpec")
        if type(self.parameters) is not ParameterMap:
            raise TypeError("parameters must be an exact ParameterMap")
        if type(self.states) is not tuple or len(self.states) != 8:
            raise ValueError("states must retain exactly all eight C3 microstates")
        if any(type(item) is not MicrostateMap for item in self.states):
            raise TypeError("states must contain exact MicrostateMap values")
        if type(self.classes) is not tuple or len(self.classes) != 4:
            raise ValueError("classes must retain exactly four occupancy groups")
        if any(type(item) is not StateClass for item in self.classes):
            raise TypeError("classes must contain exact StateClass values")
        if type(self.partition) is not PartitionIdentity:
            raise TypeError("partition must be an exact PartitionIdentity")
        if type(self.completeness) is not CompletenessInventory:
            raise TypeError("completeness must be an exact CompletenessInventory")
        expected_ids = tuple(
            "".join(str(item) for item in occupancy)
            for occupancy in product((0, 1), repeat=3)
        )
        actual_ids = tuple(item.state_id for item in self.states)
        if actual_ids != expected_ids:
            raise ValueError("states must retain all eight occupancy bit strings in order")
        if tuple(item.occupied_count for item in self.classes) != (0, 1, 2, 3):
            raise ValueError("classes must be ordered by occupied count")
        flattened = tuple(
            state_id for state_class in self.classes for state_id in state_class.state_ids
        )
        if set(flattened) != set(expected_ids) or len(flattened) != 8:
            raise ValueError("state classes must partition the eight microstates")
        if self.completeness != CompletenessInventory(
            8, 8, 8, 8, 4, 8, (), (), False
        ):
            raise ValueError("completeness inventory must certify no output reduction")
        semantic_error = exact_equilibrium_map_error(self, self.spec)
        if semantic_error is not None:
            raise ValueError(
                "exact equilibrium map is not bound to its specification: "
                + semantic_error
            )


def exact_equilibrium_map_error(
    candidate: object,
    spec: IsingLatticeGasSpec,
) -> str | None:
    """Verify every retained field directly, without calling the derivation routine.

    This is intentionally a separate implementation path for runtime/postcondition use.
    It computes both Hamiltonians directly from the declared graph and bits, then checks
    parameter, state, class, formal-partition, and completeness records field by field.
    """
    if type(spec) is not IsingLatticeGasSpec:
        return "verifier requires an exact IsingLatticeGasSpec"
    if type(candidate) is not ExactEquilibriumMap:
        return "candidate must be an exact ExactEquilibriumMap"
    if candidate.spec != spec:
        return "candidate specification differs from the approved specification"

    j = spec.coupling_j_ticks
    h = spec.field_h_ticks
    epsilon = 4 * j
    mu = 2 * h - 4 * j
    constant = 3 * h - 3 * j
    parameters = candidate.parameters
    if type(parameters) is not ParameterMap:
        return "parameter map has the wrong concrete type"
    if (
        parameters.coupling_j_ticks,
        parameters.field_h_ticks,
        parameters.attraction_epsilon_ticks,
        parameters.chemical_potential_mu_ticks,
        parameters.constant_shift_c_ticks,
    ) != (j, h, epsilon, mu, constant):
        return "parameter map does not equal the direct J/h substitution"

    occupancies = tuple(product((0, 1), repeat=3))
    if type(candidate.states) is not tuple or len(candidate.states) != len(
        occupancies
    ):
        return "state inventory does not contain exactly eight rows"
    expected_state_fields: list[
        tuple[
            str,
            tuple[int, int, int],
            tuple[int, int, int],
            int,
            int,
            int,
            int,
            int,
            int,
            int,
            int,
            int,
        ]
    ] = []
    for occupancy in occupancies:
        spins = tuple(2 * bit - 1 for bit in occupancy)
        occupied_count = occupancy[0] + occupancy[1] + occupancy[2]
        occupied_edge_count = (
            occupancy[0] * occupancy[1]
            + occupancy[1] * occupancy[2]
            + occupancy[0] * occupancy[2]
        )
        magnetization = spins[0] + spins[1] + spins[2]
        spin_edge_sum = (
            spins[0] * spins[1]
            + spins[1] * spins[2]
            + spins[0] * spins[2]
        )
        ising_energy = -j * spin_edge_sum - h * magnetization
        lattice_energy = (
            -epsilon * occupied_edge_count - mu * occupied_count
        )
        expected_state_fields.append(
            (
                "".join(str(bit) for bit in occupancy),
                occupancy,
                spins,
                occupied_count,
                occupied_edge_count,
                magnetization,
                spin_edge_sum,
                ising_energy,
                lattice_energy,
                constant,
                -ising_energy,
                -lattice_energy,
            )
        )
    for index, (row, expected) in enumerate(
        zip(candidate.states, expected_state_fields)
    ):
        if type(row) is not MicrostateMap:
            return f"state row {index} has the wrong concrete type"
        actual = (
            row.state_id,
            row.occupancies,
            row.spins,
            row.occupied_count,
            row.occupied_edge_count,
            row.magnetization,
            row.spin_edge_sum,
            row.ising_energy_ticks,
            row.lattice_energy_ticks,
            row.constant_shift_ticks,
            row.ising_boltzmann_exponent_ticks,
            row.lattice_boltzmann_exponent_ticks,
        )
        if actual != expected:
            return f"state row {index} differs from direct Hamiltonian evaluation"

    if type(candidate.classes) is not tuple or len(candidate.classes) != 4:
        return "state-class inventory does not contain exactly four rows"
    expected_classes: list[
        tuple[
            int,
            int,
            tuple[str, ...],
            int,
            int,
            int,
            int,
            int,
        ]
    ] = []
    for occupied_count in range(4):
        members = tuple(
            fields
            for fields in expected_state_fields
            if fields[3] == occupied_count
        )
        reference = members[0]
        expected_classes.append(
            (
                occupied_count,
                len(members),
                tuple(fields[0] for fields in members),
                reference[4],
                reference[5],
                reference[6],
                reference[7],
                reference[8],
            )
        )
    for index, (state_class, expected) in enumerate(
        zip(candidate.classes, expected_classes)
    ):
        if type(state_class) is not StateClass:
            return f"state class {index} has the wrong concrete type"
        actual = (
            state_class.occupied_count,
            state_class.degeneracy,
            state_class.state_ids,
            state_class.occupied_edge_count,
            state_class.magnetization,
            state_class.spin_edge_sum,
            state_class.ising_energy_ticks,
            state_class.lattice_energy_ticks,
        )
        if actual != expected:
            return f"state class {index} differs from direct state grouping"

    partition = candidate.partition
    if type(partition) is not PartitionIdentity:
        return "partition identity has the wrong concrete type"
    expected_lattice_terms = tuple(
        (fields[0], fields[1], -fields[7]) for fields in expected_classes
    )
    expected_ising_terms = tuple(
        (fields[0], fields[1], -fields[6]) for fields in expected_classes
    )
    actual_lattice_terms = tuple(
        (term.occupied_count, term.degeneracy, term.exponent_ticks)
        if type(term) is FormalBoltzmannTerm
        else None
        for term in partition.lattice_terms
    )
    actual_ising_terms = tuple(
        (term.occupied_count, term.degeneracy, term.exponent_ticks)
        if type(term) is FormalBoltzmannTerm
        else None
        for term in partition.ising_terms
    )
    if actual_lattice_terms != expected_lattice_terms:
        return "lattice formal partition terms differ from direct state grouping"
    if actual_ising_terms != expected_ising_terms:
        return "Ising formal partition terms differ from direct state grouping"
    if (
        partition.beta_symbol != spec.beta_symbol
        or partition.energy_unit != spec.energy_unit
        or partition.constant_shift_ticks != constant
        or partition.statewise_relation
        != "H_Ising(state) = H_lattice_gas(mapped_state) + C"
        or partition.partition_relation
        != "Z_Ising(beta) = exp(-beta*C) * Xi_lattice_gas(beta)"
        or partition.normalized_probability_relation
        != (
            "normalized equilibrium probability is identical for each paired "
            "microstate because the state-independent factor cancels"
        )
    ):
        return "partition identity metadata differs from the fixed formal contract"
    if candidate.completeness != CompletenessInventory(
        8, 8, 8, 8, 4, 8, (), (), False
    ):
        return "completeness inventory does not certify the full state space"
    return None


def derive_exact_equilibrium_map(
    spec: IsingLatticeGasSpec,
) -> ExactEquilibriumMap:
    """Enumerate and independently retain the exact eight-state change of variables."""
    if type(spec) is not IsingLatticeGasSpec:
        raise TypeError("spec must be an exact IsingLatticeGasSpec")
    j = spec.coupling_j_ticks
    h = spec.field_h_ticks
    epsilon = 4 * j
    mu = 2 * h - 4 * j
    constant = 3 * (h - j)
    parameters = ParameterMap(j, h, epsilon, mu, constant)

    states: list[MicrostateMap] = []
    for occupancy in product((0, 1), repeat=3):
        spins = tuple(2 * item - 1 for item in occupancy)
        occupied_count = sum(occupancy)
        occupied_edges = sum(
            occupancy[left] * occupancy[right] for left, right in C3_EDGES
        )
        magnetization = sum(spins)
        spin_edges = sum(spins[left] * spins[right] for left, right in C3_EDGES)
        ising_energy = -j * spin_edges - h * magnetization
        lattice_energy = -epsilon * occupied_edges - mu * occupied_count
        states.append(
            MicrostateMap(
                "".join(str(item) for item in occupancy),
                occupancy,
                spins,
                occupied_count,
                occupied_edges,
                magnetization,
                spin_edges,
                ising_energy,
                lattice_energy,
                constant,
                -ising_energy,
                -lattice_energy,
            )
        )

    classes: list[StateClass] = []
    for occupied_count in range(4):
        members = tuple(
            item for item in states if item.occupied_count == occupied_count
        )
        reference = members[0]
        if any(
            (
                item.occupied_edge_count,
                item.magnetization,
                item.spin_edge_sum,
                item.ising_energy_ticks,
                item.lattice_energy_ticks,
            )
            != (
                reference.occupied_edge_count,
                reference.magnetization,
                reference.spin_edge_sum,
                reference.ising_energy_ticks,
                reference.lattice_energy_ticks,
            )
            for item in members
        ):
            raise RuntimeError("C3 occupancy class is not energetically uniform")
        classes.append(
            StateClass(
                occupied_count,
                len(members),
                tuple(item.state_id for item in members),
                reference.occupied_edge_count,
                reference.magnetization,
                reference.spin_edge_sum,
                reference.ising_energy_ticks,
                reference.lattice_energy_ticks,
            )
        )

    lattice_terms = tuple(
        FormalBoltzmannTerm(
            item.occupied_count,
            item.degeneracy,
            -item.lattice_energy_ticks,
        )
        for item in classes
    )
    ising_terms = tuple(
        FormalBoltzmannTerm(
            item.occupied_count,
            item.degeneracy,
            -item.ising_energy_ticks,
        )
        for item in classes
    )
    partition = PartitionIdentity(
        spec.beta_symbol,
        spec.energy_unit,
        lattice_terms,
        ising_terms,
        constant,
        "H_Ising(state) = H_lattice_gas(mapped_state) + C",
        "Z_Ising(beta) = exp(-beta*C) * Xi_lattice_gas(beta)",
        (
            "normalized equilibrium probability is identical for each paired "
            "microstate because the state-independent factor cancels"
        ),
    )
    completeness = CompletenessInventory(8, 8, 8, 8, 4, 8, (), (), False)
    return ExactEquilibriumMap(
        spec,
        parameters,
        tuple(states),
        tuple(classes),
        partition,
        completeness,
    )
