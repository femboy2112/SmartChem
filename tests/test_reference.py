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

from smartchem.atoms import PT
from smartchem.data.basis_tight_d import TIGHT_D
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

    def test_the_c3_entries_agree_with_the_source_they_did_not_come_from(self):
        """
        The two-source check for the ATcT entries, run the other way round.

        These three are stored from ATcT v1.202. CCCBDB derives its 0 K values by an
        entirely different route -- 298 K measurements pushed down with TRC heat-content
        functions -- so its numbers are an independent read on the same quantity. Both
        being right is the evidence; the tolerance is what the two sources actually
        disagree by, which was measured, not assumed.

        Worth pinning because a scrape of the CCCBDB table once returned propane = -98.5
        carrying butane's formula string. Nothing about that number looked wrong. A second
        source is the only thing that catches a row-bleed, because the value it hands you
        is a perfectly good value -- for the wrong molecule.
        """
        cccbdb_kj = {"C3H8": -82.4, "C3H7OH": -231.3, "CH3OC2H5": -193.6}
        for formula, other_source in cccbdb_kj.items():
            stored = ref.polyatomic(formula)
            assert stored is not None, formula
            assert abs(stored.dfh_0k_kj - other_source) < 1.0, (
                f"{formula}: ATcT {stored.dfh_0k_kj} vs CCCBDB {other_source} kJ/mol"
            )
        # and the row-bleed itself would have been caught: butane is 16 kJ/mol away
        assert abs(ref.polyatomic("C3H8").dfh_0k_kj - (-98.5)) > 10.0

    def test_the_homologous_series_is_smooth(self):
        """
        A shape check no transcription error survives: adding a CH2 to a saturated chain
        adds a near-constant amount of atomization energy, because it adds the same two
        C-H bonds and converts one C-H into a C-C.

        This is independent of the enthalpies' *source* -- it constrains the sequence, so
        a single wrong entry breaks the pattern even if it looks individually plausible.
        Increments measured across two families; the tolerance is what the real
        (non-constant) trend spans, not a fitted number.
        """
        alkanes = ["CH4", "C2H6", "C3H8"]
        alcohols = ["CH3OH", "C2H5OH", "C3H7OH"]
        for series in (alkanes, alcohols):
            d = [ref.atomization_energy_ev(f) for f in series]
            steps = [d[i + 1] - d[i] for i in range(len(d) - 1)]
            assert all(11.0 < s < 12.5 for s in steps), f"{series}: {steps}"

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

    def test_a_mass_violating_pseudo_reaction_is_refused(self):
        """
        Formation-enthalpy differences across unequal inventories depend on omitted atomic
        reservoirs. Publishing one as an experimental reaction energy would be a plausible
        but reference-dependent wrong answer.
        """
        left = {"C2H6": 1}
        right = {"CH4": 1}          # a carbon and two hydrogens vanish
        with pytest.raises(ValueError, match="conserve elemental composition"):
            ref.reaction_energy_ev(left, right)

    @pytest.mark.parametrize(
        ("side", "error"),
        [
            ({}, ValueError),
            ({"CH4": 0}, ValueError),
            ({"CH4": -1}, ValueError),
            ({"CH4": True}, TypeError),
            ({"CH4": 1.5}, TypeError),
            ({"": 1}, ValueError),
        ],
    )
    def test_reaction_stoichiometry_is_validated(self, side, error):
        with pytest.raises(error):
            ref.reaction_energy_ev(side, {"CH4": 1})

    def test_reaction_sides_are_typed_mappings(self):
        with pytest.raises(TypeError, match="mapping"):
            ref.reaction_energy_ev([("CH4", 1)], {"CH4": 1})


class TestPhysicalSanity:
    @pytest.mark.parametrize("entry", ref.POLYATOMIC_REFS, ids=lambda e: e.formula)
    def test_every_molecule_is_bound(self, entry):
        """Atomization energy is the work to destroy the molecule. It cannot be negative."""
        assert ref.atomization_energy_ev(entry.formula) > 0

    @pytest.mark.parametrize("entry", ref.POLYATOMIC_REFS, ids=lambda e: e.formula)
    def test_atomization_is_within_reach_of_a_bond_count(self, entry):
        """
        Order-of-magnitude gate, per ATOM so it does not go stale as species grow.

        It was written as an absolute 3-40 eV window when nothing here had more than 8
        bonds, and propane (10 bonds, 40.9 eV) walked straight through the ceiling. A
        bound that has to be widened every time the table grows is not a bound, so this
        one is intensive instead.

        Each atom's share of the atomization energy is at most half of four strong bonds
        (4 x 6 / 2 = 12 eV) and at least half of one weak one. Deliberately loose: it
        catches a misplaced decimal, a sign flip, or a kJ/eV confusion -- the realistic
        transcription failures -- and is not trying to catch a subtly wrong digit, which
        is what the two-source check is for.
        """
        n_atoms = sum(entry.composition.values())
        per_atom = ref.atomization_energy_ev(entry.formula) / n_atoms
        assert 0.75 < per_atom < 12.0, f"{entry.formula}: {per_atom:.2f} eV/atom"

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
    @pytest.mark.parametrize(
        "table,key,value",
        [
            (ref.GEOMETRY, "H2", (9.0, 9.0, 0)),
            (ref.ATOM_SPIN, "H", 0),
            (ref.ATOM_FORMATION_KJ, "H", 0.0),
            (PT, "H", None),
            (TIGHT_D, "cc-pV(T+d)Z", "changed"),
        ],
    )
    def test_model_input_tables_are_immutable(self, table, key, value):
        """A running oracle's calculation inputs cannot drift behind its cache identity."""
        with pytest.raises(TypeError):
            table[key] = value

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
        """Historical regression partitions remain explicit, even though neither is pristine."""
        assert len(ref.polyatomics("train")) >= 3
        assert len(ref.polyatomics("test")) >= 3
        assert len(ref.polyatomics("train")) + len(ref.polyatomics("test")) == len(
            ref.POLYATOMIC_REFS
        )

    def test_formulas_are_unique(self):
        formulas = [e.formula for e in ref.POLYATOMIC_REFS]
        assert len(formulas) == len(set(formulas))

    def test_polyatomic_composition_is_an_immutable_snapshot(self):
        source = {"H": 2, "O": 1}
        entry = ref.PolyatomicRef("H2O", source, -238.9, 0.004, "train", "test")

        source["H"] = 99
        assert entry.composition == {"H": 2, "O": 1}
        with pytest.raises(TypeError):
            entry.composition["H"] = 3

    @pytest.mark.parametrize(
        ("composition", "error"),
        [
            ([], TypeError),
            ({}, ValueError),
            ({"": 1}, ValueError),
            ({1: 1}, ValueError),
            ({"H": True}, TypeError),
            ({"H": 1.5}, TypeError),
            ({"H": 0}, ValueError),
            ({"H": -1}, ValueError),
        ],
    )
    def test_polyatomic_composition_rejects_invalid_counts(self, composition, error):
        with pytest.raises(error):
            ref.PolyatomicRef("bad", composition, 0.0, 0.0, "train", "test")

    def test_diatomic_rows_encode_their_conventional_graph_order(self):
        expected = {
            "H2": 1, "N2": 3, "O2": 2, "F2": 1, "Cl2": 1, "I2": 1,
            "P2": 3, "S2": 2, "C2": 2, "Si2": 2, "Na2": 1, "K2": 1,
            "HF": 1, "HCl": 1, "HI": 1, "OH": 1, "CH": 1, "NH": 1,
            "SiO": 2, "CS": 3, "CO": 3, "NO": 2, "CN": 3,
            "NaCl": 1, "KCl": 1, "NaF": 1, "MgO": 1, "ICl": 1,
        }
        assert {entry.formula: entry.bond_order for entry in ref.BOND_REFS} == expected

    def test_new_bond_references_default_to_a_single_bond_for_source_compatibility(self):
        entry = ref.BondRef("AB", ("A", "B"), 1.0, 0.1, "train", "test", "test")
        assert entry.bond_order == 1

    def test_chemical_accuracy_is_exactly_one_kcal_per_mol(self):
        assert ref.CHEMICAL_ACCURACY_EV * ref.KCAL_PER_EV == pytest.approx(1.0)
