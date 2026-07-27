"""Exact algebra and completeness tests for the finite C3 control map."""
from __future__ import annotations

from dataclasses import replace

import pytest

from smartchem.ising_lattice_gas_domain import (
    C3_EDGES,
    C3_VERTICES,
    IsingLatticeGasSpec,
    MicrostateMap,
    derive_exact_equilibrium_map,
)


SPEC = IsingLatticeGasSpec(coupling_j_ticks=2, field_h_ticks=1)


def test_all_eight_c3_states_obey_the_independent_integer_algebra_and_signs():
    result = derive_exact_equilibrium_map(SPEC)
    expected = {
        "000": ((0, 0, 0), (-1, -1, -1), 0, 0, -3, 3, -3, 0, 3, 0),
        "001": ((0, 0, 1), (-1, -1, 1), 1, 0, -1, -1, 3, 6, -3, -6),
        "010": ((0, 1, 0), (-1, 1, -1), 1, 0, -1, -1, 3, 6, -3, -6),
        "011": ((0, 1, 1), (-1, 1, 1), 2, 1, 1, -1, 1, 4, -1, -4),
        "100": ((1, 0, 0), (1, -1, -1), 1, 0, -1, -1, 3, 6, -3, -6),
        "101": ((1, 0, 1), (1, -1, 1), 2, 1, 1, -1, 1, 4, -1, -4),
        "110": ((1, 1, 0), (1, 1, -1), 2, 1, 1, -1, 1, 4, -1, -4),
        "111": ((1, 1, 1), (1, 1, 1), 3, 3, 3, 3, -9, -6, 9, 6),
    }

    assert C3_VERTICES == (0, 1, 2)
    assert C3_EDGES == ((0, 1), (1, 2), (0, 2))
    assert len(C3_EDGES) == 3
    assert tuple(state.state_id for state in result.states) == tuple(expected)
    for state in result.states:
        (
            occupancies,
            spins,
            occupied_count,
            occupied_edges,
            magnetization,
            spin_edges,
            ising_energy,
            lattice_energy,
            ising_exponent,
            lattice_exponent,
        ) = expected[state.state_id]
        assert state.occupancies == occupancies
        assert state.spins == spins
        assert state.occupied_count == occupied_count
        assert state.occupied_edge_count == occupied_edges
        assert state.magnetization == magnetization
        assert state.spin_edge_sum == spin_edges
        assert state.ising_energy_ticks == ising_energy
        assert state.lattice_energy_ticks == lattice_energy
        assert state.constant_shift_ticks == -3
        assert state.ising_boltzmann_exponent_ticks == ising_exponent
        assert state.lattice_boltzmann_exponent_ticks == lattice_exponent


def test_parameter_map_degeneracies_and_formal_partition_exponents_are_exact():
    result = derive_exact_equilibrium_map(SPEC)

    assert result.parameters.attraction_epsilon_ticks == 8
    assert result.parameters.chemical_potential_mu_ticks == -6
    assert result.parameters.constant_shift_c_ticks == -3
    assert tuple(
        (item.occupied_count, item.degeneracy, item.state_ids,
         item.occupied_edge_count, item.ising_energy_ticks, item.lattice_energy_ticks)
        for item in result.classes
    ) == (
        (0, 1, ("000",), 0, -3, 0),
        (1, 3, ("001", "010", "100"), 0, 3, 6),
        (2, 3, ("011", "101", "110"), 1, 1, 4),
        (3, 1, ("111",), 3, -9, -6),
    )
    assert tuple(item.degeneracy for item in result.partition.lattice_terms) == (1, 3, 3, 1)
    assert tuple(item.exponent_ticks for item in result.partition.lattice_terms) == (0, -6, -4, 6)
    assert tuple(item.exponent_ticks for item in result.partition.ising_terms) == (3, -3, -1, 9)
    assert result.partition.constant_shift_ticks == -3
    assert result.partition.partition_relation == (
        "Z_Ising(beta) = exp(-beta*C) * Xi_lattice_gas(beta)"
    )


def test_completeness_inventory_proves_no_output_reduction():
    result = derive_exact_equilibrium_map(SPEC)

    assert result.completeness.expected_microstates == 8
    assert result.completeness.retained_microstates == 8
    assert result.completeness.unique_occupancy_states == 8
    assert result.completeness.unique_spin_states == 8
    assert result.completeness.retained_state_classes == 4
    assert result.completeness.class_degeneracy_sum == 8
    assert result.completeness.missing_state_ids == ()
    assert result.completeness.duplicate_state_ids == ()
    assert result.completeness.output_reduction_applied is False


def test_invalid_c3_schema_and_subclass_microstate_are_rejected_at_the_type_boundary():
    with pytest.raises(ValueError, match="exactly vertices"):
        IsingLatticeGasSpec(2, 1, vertices=(0, 1, 3))
    with pytest.raises(ValueError, match="three undirected C3 edges"):
        IsingLatticeGasSpec(2, 1, edges=((0, 1), (1, 2), (2, 0)))
    with pytest.raises(TypeError, match="exact integer"):
        IsingLatticeGasSpec(True, 1)  # type: ignore[arg-type]

    result = derive_exact_equilibrium_map(SPEC)

    class ForgedMicrostate(MicrostateMap):
        pass

    forged_state = ForgedMicrostate(**result.states[0].__dict__)
    with pytest.raises(TypeError, match="exact MicrostateMap"):
        replace(result, states=(forged_state, *result.states[1:]))
    with pytest.raises(ValueError, match="s_i = 2\\*n_i - 1"):
        replace(result.states[1], spins=(1, -1, 1))


def test_self_consistent_constant_shift_forgery_is_rejected_against_j_and_h():
    result = derive_exact_equilibrium_map(SPEC)
    forged_zero_state = replace(
        result.states[0],
        ising_energy_ticks=999,
        lattice_energy_ticks=1002,
        ising_boltzmann_exponent_ticks=-999,
        lattice_boltzmann_exponent_ticks=-1002,
    )

    # The forged row still obeys H_I=H_LG+C.  The enclosing map must nevertheless
    # reject it because both Hamiltonians disagree with direct evaluation from J,h,C3.
    with pytest.raises(ValueError, match="direct Hamiltonian evaluation"):
        replace(result, states=(forged_zero_state, *result.states[1:]))
