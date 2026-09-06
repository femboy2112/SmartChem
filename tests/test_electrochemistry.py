"""ELECTROCHEM-01 (queue item 5, DOW): the EM bridge -- sourced standard potentials -> cell potential,
Gibbs free energy, spontaneity, Nernst, electrolysis voltage.

The battery is calibration-first (the instrument discipline): it recovers KNOWN textbook answers (Cl
displaces Br- but not the reverse; Delta-G deg = -52.3 kJ/mol for the DOW displacement; the 59.16
mV/decade Nernst slope) before trusting any derived reading, then pins the fail-closed and
anti-fabrication boundaries and closes the loop to ROUND-17's REDOX-DISPLACE-01.
"""
from __future__ import annotations

import math

import pytest

from experiments.electrochemistry_probe import FROZEN_HASH, content_hash
from experiments.electrochemistry_probe import validate as validate_probe
from smartchem.category import Molecule
from smartchem.cell import FARADAY_C_PER_MOL as CELL_FARADAY
from smartchem.electrochemistry import (
    ELECTROCHEM_SCHEMA,
    FARADAY_C_PER_MOL,
    CellPotential,
    SpontaneityVerdict,
    StandardReductionPotential,
    couple_potential,
    displacement_cell_potential,
    gibbs_free_energy_j_per_mol,
    minimum_electrolysis_voltage,
    nernst_potential,
    spontaneity,
    standard_cell_potential,
)
from smartchem.redox_displacement import (
    DISPLACEMENT_SCHEMA,
    HalfReactionCouple,
    combine_half_reactions,
    halogen_couple,
)
from smartchem.structure_descent import ScissionError


def _br2():
    return Molecule.diatomic("Br", "Br")


# --- calibration: the instrument recovers the KNOWN halogen electrochemistry ------------------------

def test_the_sourced_halogen_potentials_are_the_textbook_values():
    assert couple_potential(halogen_couple("F")).potential_volts == 2.866
    assert couple_potential(halogen_couple("Cl")).potential_volts == 1.358
    assert couple_potential(halogen_couple("Br")).potential_volts == 1.087
    assert couple_potential(halogen_couple("I")).potential_volts == 0.536


def test_chlorine_displaces_bromide_spontaneously_the_dow_direction():
    cell = displacement_cell_potential(reduction=halogen_couple("Cl"), oxidation=halogen_couple("Br"))
    assert cell is not None
    assert math.isclose(cell.e_cell_volts, 0.271, abs_tol=1e-9)
    assert cell.verdict is SpontaneityVerdict.SPONTANEOUS


def test_bromine_does_not_displace_chloride_the_calibration_reverse():
    # THE known-answer calibration: reverse the pairing and it must flip to NON-spontaneous.
    cell = displacement_cell_potential(reduction=halogen_couple("Br"), oxidation=halogen_couple("Cl"))
    assert math.isclose(cell.e_cell_volts, -0.271, abs_tol=1e-9)
    assert cell.verdict is SpontaneityVerdict.NON_SPONTANEOUS


def test_the_dow_gibbs_free_energy_matches_the_textbook_minus_52_kj():
    cell = displacement_cell_potential(reduction=halogen_couple("Cl"), oxidation=halogen_couple("Br"))
    n = combine_half_reactions(reduction=halogen_couple("Cl"), oxidation=halogen_couple("Br"),
                               target=_br2()).electrons_transferred
    assert n == 2
    dG_kj = cell.gibbs_j_per_mol(n) / 1000
    assert abs(dG_kj - (-52.3)) < 0.2  # -n F E = -2 * 96485.332 * 0.271


def test_the_nernst_slope_is_59_millivolts_per_decade_at_25C():
    # a 1-electron process, Q=10 -> E - E0 = -(RT/F) ln 10 = -0.05916 V (the classic 59 mV/decade).
    assert abs(nernst_potential(0.0, 1, 10.0) - (-0.05916)) < 1e-4
    # n=2 halves the slope.
    assert abs(nernst_potential(0.0, 2, 10.0) - (-0.05916 / 2)) < 1e-4
    # Q=1 -> the standard potential exactly.
    assert nernst_potential(1.234, 2, 1.0) == 1.234


# --- fail-closed + anti-fabrication (section 10.4) --------------------------------------------------

def test_an_unsourced_couple_is_unknown_never_fabricated():
    zn = HalfReactionCouple(DISPLACEMENT_SCHEMA, "Zn",
                            (Molecule.atom("Zn", charge=2),), (Molecule.atom("Zn", charge=0),), 2)
    assert couple_potential(zn) is None
    # and a cell potential with an unsourced half is UNKNOWN, not computed from a fabricated value.
    assert standard_cell_potential(cathode=halogen_couple("Cl"), anode=zn) is None
    assert standard_cell_potential(cathode=zn, anode=halogen_couple("Br")) is None


def test_a_standard_potential_requires_a_citation():
    with pytest.raises(ScissionError):
        StandardReductionPotential.of(halogen_couple("Cl"), 1.358, "   ")


def test_the_potential_table_is_keyed_on_structure_not_a_formula_string():
    # two independently-constructed Cl couples hit the SAME sourced entry (structural digest key).
    a, b = halogen_couple("Cl"), halogen_couple("Cl")
    assert a is not b
    assert couple_potential(a) is couple_potential(b)


# --- the CellPotential coherence certificate (a hand-built edge cannot lie about E_cell) -------------

def test_cell_potential_must_equal_the_difference_of_its_two_electrode_potentials():
    cl = couple_potential(halogen_couple("Cl"))
    br = couple_potential(halogen_couple("Br"))
    # a fabricated e_cell inconsistent with its own two potentials is refused.
    with pytest.raises(ScissionError, match="difference of its own two electrode potentials"):
        CellPotential(ELECTROCHEM_SCHEMA, cl, br, 9.99)
    # the honest one constructs.
    ok = CellPotential(ELECTROCHEM_SCHEMA, cl, br, cl.potential_volts - br.potential_volts)
    assert math.isclose(ok.e_cell_volts, 0.271, abs_tol=1e-9)


def test_a_cell_needs_two_different_couples():
    with pytest.raises(ScissionError, match="two DIFFERENT redox couples"):
        standard_cell_potential(cathode=halogen_couple("Cl"), anode=halogen_couple("Cl"))


# --- gibbs / spontaneity / nernst input discipline --------------------------------------------------

def test_gibbs_sign_and_input_validation():
    assert gibbs_free_energy_j_per_mol(1.0, 1) == -FARADAY_C_PER_MOL  # -nFE, E>0 -> negative
    assert gibbs_free_energy_j_per_mol(-1.0, 1) == FARADAY_C_PER_MOL   # E<0 -> positive
    for bad_n in (0, -1, 1.5, True):
        with pytest.raises(ScissionError):
            gibbs_free_energy_j_per_mol(1.0, bad_n)


def test_cell_gibbs_derives_n_from_the_electron_balance_and_refuses_a_wrong_one():
    # evil-morty fold F3: the object holds both couples, so n = lcm(cathode.e, anode.e) is derived,
    # never a guess.  A wrong n is refused instead of silently corrupting the quantitative ΔG.
    cell = displacement_cell_potential(reduction=halogen_couple("Cl"), oxidation=halogen_couple("Br"))
    assert cell.balanced_electrons == 2
    # no arg -> derives n=2 -> the textbook -52.3 kJ/mol.
    assert abs(cell.gibbs_j_per_mol() / 1000 - (-52.3)) < 0.2
    assert cell.gibbs_j_per_mol() == cell.gibbs_j_per_mol(2)
    # a wrong n (e.g. a caller passing one couple's own count) is refused, not silently off-by-a-factor.
    with pytest.raises(ScissionError, match="balanced reaction's n"):
        cell.gibbs_j_per_mol(1)
    with pytest.raises(ScissionError, match="balanced reaction's n"):
        cell.gibbs_j_per_mol(5)


def test_spontaneity_verdict_signs():
    assert spontaneity(0.5) is SpontaneityVerdict.SPONTANEOUS
    assert spontaneity(-0.5) is SpontaneityVerdict.NON_SPONTANEOUS
    assert spontaneity(0.0) is SpontaneityVerdict.AT_EQUILIBRIUM


def test_nernst_refuses_non_positive_quotient():
    for bad_q in (0.0, -1.0):
        with pytest.raises(ScissionError):
            nernst_potential(1.0, 1, bad_q)


# --- the electrolytic leg (electrons at an anode -- the EM scope) ------------------------------------

def test_minimum_electrolysis_voltage_is_zero_for_spontaneous_and_positive_for_forced():
    dow = displacement_cell_potential(reduction=halogen_couple("Cl"), oxidation=halogen_couple("Br"))
    rev = displacement_cell_potential(reduction=halogen_couple("Br"), oxidation=halogen_couple("Cl"))
    assert minimum_electrolysis_voltage(dow) == 0.0                     # galvanic, no drive needed
    assert math.isclose(minimum_electrolysis_voltage(rev), 0.271, abs_tol=1e-9)  # |E_cell|


# --- no drift + the committed harness ----------------------------------------------------------------

def test_faraday_constant_matches_cell_module():
    assert FARADAY_C_PER_MOL == CELL_FARADAY


def test_the_committed_harness_validates_and_its_hash_is_frozen():
    validate_probe()
    assert content_hash() == FROZEN_HASH
