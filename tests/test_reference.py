"""
Tests on the reference data itself.

Reference data is the one place in this project where a mistake is unrecoverable by
testing anything else. Every accuracy claim is measured against these numbers, so an error
here does not show up as a failure -- it shows up as a *better-looking* result, silently,
forever. The whole suite is calibrated against this file, which means this file is the one
thing the suite cannot calibrate.

So it gets checked three ways that do not share a failure mode:

1. Against an independent literature compilation (two species, two sources).
2. Against internal algebra -- two derivations of the same reaction energy that must agree.
3. Against physical sanity -- signs, magnitudes, and monotonicity that no correct
   thermochemistry can violate.

None of these can prove the table is right. Together they would have caught the ethanol
near-miss documented in `reference.py`, which is the bar that matters.
"""
from __future__ import annotations

import pytest

from smartchem.data import reference as ref


class TestTheDerivationIsCorrect:
    def test_derivation_reproduces_independent_literature_values(self):
        """
        The two-source check. These two atomization energies were taken from a literature
        compilation that is NOT the CCCBDB enthalpies this module derives from, so
        agreement is evidence the derivation and the inputs are both right.

        Tolerance is 0.005 eV: about 20x inside chemical accuracy, and loose enough to
        absorb the ~0.2 kJ/mol spread in the carbon atom's enthalpy of formation between
        compilations (ATcT 711.4 vs CCCBDB 711.2).
        """
        independent = {"CH4": 17.018, "C2H6": 28.885}
        for formula, literature in independent.items():
            derived = ref.atomization_energy_ev(formula)
            assert derived is not None
            assert abs(derived - literature) < 0.005, (
                f"{formula}: derived {derived:.4f} eV vs literature {literature} eV"
            )

    def test_the_ethanol_ether_isomer_gap_matches_experiment(self):
        """
        An independent handle on two of the newer entries.

        C2H5OH and CH3OCH3 have identical formulas, so their atomic terms cancel exactly
        and the gap is a pure difference of measured enthalpies -- no derivation, no atomic
        reference values, nothing this module could get wrong in common. Ethanol is the
        more stable isomer by ~50 kJ/mol experimentally, and that is a number known
        independently of the 0 K table these two were drawn from.
        """
        gap = ref.reaction_energy_ev({"CH3OCH3": 1}, {"C2H5OH": 1})
        assert gap == pytest.approx(-50.5 / ref.KJ_PER_EV, abs=0.01)
        assert gap < 0, "ethanol is the more stable isomer"
        # and the derived atomization energies must reflect the same ordering
        assert ref.atomization_energy_ev("C2H5OH") > ref.atomization_energy_ev("CH3OCH3")

    def test_the_two_routes_to_a_reaction_energy_agree(self):
        """
        A reaction energy can be had by differencing enthalpies of formation, or by
        differencing atomization energies. They agree only because the atomic terms cancel
        -- which they do only if the reaction conserves mass. So this is a live check on
        conservation, not just on arithmetic.
        """
        left = {"C2H6": 1, "CH3OH": 1}
        right = {"C2H5OH": 1, "CH4": 1}

        via_formation = ref.reaction_energy_ev(left, right)

        def atomization_sum(side):
            return sum(c * ref.atomization_energy_ev(f) for f, c in side.items())

        # atomization is energy to pull apart, so a reaction energy is left - right
        via_atomization = atomization_sum(left) - atomization_sum(right)

        assert via_formation == pytest.approx(via_atomization, abs=1e-9)

    def test_a_mass_violating_reaction_makes_the_routes_disagree(self):
        """
        The control for the test above. If the atomic terms did not cancel, the agreement
        would be meaningless -- so break conservation and confirm the two routes part ways.
        Without this, the previous test would pass even if both routes were the same bug.
        """
        left = {"C2H6": 1}
        right = {"CH4": 1}          # a carbon and two hydrogens vanish

        via_formation = ref.reaction_energy_ev(left, right)
        via_atomization = (
            ref.atomization_energy_ev("C2H6") - ref.atomization_energy_ev("CH4")
        )
        assert abs(via_formation - via_atomization) > 1.0, (
            "the atomic terms must NOT cancel when mass is not conserved"
        )


class TestPhysicalSanity:
    @pytest.mark.parametrize("entry", ref.POLYATOMIC_REFS, ids=lambda e: e.formula)
    def test_every_molecule_is_bound(self, entry):
        """Atomization energy is the work to destroy the molecule. It cannot be negative."""
        assert ref.atomization_energy_ev(entry.formula) > 0

    @pytest.mark.parametrize("entry", ref.POLYATOMIC_REFS, ids=lambda e: e.formula)
    def test_atomization_is_within_reach_of_a_bond_count(self, entry):
        """
        Order-of-magnitude gate. A bond runs roughly 1.5-6 eV, and these species have
        between 2 and 8 bonds, so anything outside 3-40 eV is a transcription error rather
        than chemistry. Deliberately loose: this catches a misplaced decimal or a sign,
        which is the realistic failure mode, not a subtly wrong digit.
        """
        assert 3.0 < ref.atomization_energy_ev(entry.formula) < 40.0

    def test_bigger_molecules_hold_more_atoms_together(self):
        """Monotonicity that no correct table can violate, across three independent pairs."""
        assert ref.atomization_energy_ev("C2H6") > ref.atomization_energy_ev("CH4")
        assert ref.atomization_energy_ev("C2H5OH") > ref.atomization_energy_ev("CH3OH")
        assert ref.atomization_energy_ev("H2O2") > ref.atomization_energy_ev("H2O")

    def test_the_isodesmic_reaction_is_not_thermoneutral(self):
        """
        The near-miss, pinned as a regression.

        Bond additivity predicts exactly 0.000 eV for C2H6 + CH3OH -> C2H5OH + CH4: the
        same bonds appear on both sides. Experiment says -0.261 eV. If someone ever
        "corrects" ethanol's enthalpy to the additivity estimate, this fails.

        It also states the finding that matters for `is_isodesmic`: an isodesmic reaction
        is small, not zero. Any claim that method error cancels in these reactions is a
        claim about the *error*, and must not lean on the reaction energy being nil.
        """
        energy = ref.reaction_energy_ev({"C2H6": 1, "CH3OH": 1}, {"C2H5OH": 1, "CH4": 1})
        assert energy == pytest.approx(-0.261, abs=0.005)
        assert abs(energy) > 0.1, "not thermoneutral -- additivity is an approximation"


class TestTheTableDoesNotLieAboutItself:
    def test_missing_species_returns_none_rather_than_guessing(self):
        assert ref.atomization_energy_ev("C6H6") is None
        assert ref.polyatomic("C6H6") is None
        assert ref.reaction_energy_ev({"CH4": 1}, {"C6H6": 1}) is None

    def test_every_element_used_has_an_atomic_reference(self):
        """A composition naming an element with no tabulated atom would KeyError at use."""
        for entry in ref.POLYATOMIC_REFS:
            for symbol in entry.composition:
                assert symbol in ref.ATOM_FORMATION_KJ, (
                    f"{entry.formula} needs dfH for {symbol}"
                )

    def test_splits_are_declared_and_both_populated(self):
        """A held-out split with nothing in it is not a held-out split."""
        assert len(ref.polyatomics("train")) >= 3
        assert len(ref.polyatomics("test")) >= 3
        assert len(ref.polyatomics("train")) + len(ref.polyatomics("test")) == len(
            ref.POLYATOMIC_REFS
        )

    def test_formulas_are_unique(self):
        formulas = [e.formula for e in ref.POLYATOMIC_REFS]
        assert len(formulas) == len(set(formulas))
