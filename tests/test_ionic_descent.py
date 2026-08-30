"""G4 -- ionic descent: heterolysis + redox wired into one view, the chemical<->EM bridge.

Redox is where the chemical vertical meets the electromagnetic one: an electron transfer is an exact
conserving morphism when the electron is spelled the repository's way -- a charge carrier with no
atoms, massless in the mass ledger, charge -1. These tests pin the conservation (charge, and mass
trivially), the refusals (a redox step may not make or break a bond), and the honest labelling (every
ionic product is an ION or an electron, never a neutral compound).
"""

import pytest

from smartchem.category import Bond, Molecule
from smartchem.decompiler_boundary import SpeciesClass, species_class
from smartchem.structure_descent import (
    ELECTRON,
    REDOX_SCHEMA,
    RedoxHalfReaction,
    ScissionError,
    ionic_edges,
    redox_couples,
)


class TestRedoxConservesChargeAndMass:
    def test_the_electron_is_massless_and_carries_unit_negative_charge(self):
        assert ELECTRON.atoms == () and dict(ELECTRON.formula) == {} and ELECTRON.charge == -1

    def test_iron_two_to_three_is_a_conserving_half_reaction(self):
        fe2 = Molecule.atom("Fe", charge=2)
        rx = redox_couples(fe2, max_electrons=1)[0]
        assert rx.equation() == "Fe^2+ -> Fe^3+ + e-"
        # charge conserved (the certificate turns on this); mass conserved trivially (electron atomless)
        assert rx.oxidized.charge - rx.electrons == rx.reduced.charge
        assert rx.reduced.atoms == rx.oxidized.atoms

    def test_products_are_the_oxidised_species_plus_n_electrons(self):
        na = Molecule.atom("Na")
        rx = redox_couples(na, max_electrons=1)[0]        # Na -> Na+ + e-
        assert rx.products == (Molecule.atom("Na", charge=1), ELECTRON)

    def test_two_electron_oxidation_releases_two_electrons(self):
        zn = Molecule.atom("Zn")
        rx = redox_couples(zn, max_electrons=2)[1]        # Zn -> Zn2+ + 2 e-
        assert rx.electrons == 2
        assert rx.products.count(ELECTRON) == 2 and rx.oxidized.charge == 2


class TestRedoxCertificateBites:
    def test_a_bond_change_is_rejected(self):
        # a redox step moves electrons, it must not make or break bonds
        red = Molecule(("C", "C"), frozenset({Bond(0, 1, 1)}))
        ox = Molecule(("C", "C"), frozenset({Bond(0, 1, 2)}), charge=1)   # bond order changed
        with pytest.raises(ScissionError, match="make or break"):
            RedoxHalfReaction(REDOX_SCHEMA, red, ox, 1)

    def test_charge_non_conservation_is_rejected(self):
        red = Molecule.atom("Fe", charge=2)
        ox = Molecule.atom("Fe", charge=2)               # no charge change, but 1 e- claimed
        with pytest.raises(ScissionError, match="charge not conserved"):
            RedoxHalfReaction(REDOX_SCHEMA, red, ox, 1)

    def test_zero_electrons_is_rejected(self):
        fe = Molecule.atom("Fe")
        with pytest.raises(ValueError, match="max_electrons"):
            redox_couples(fe, max_electrons=0)


class TestUnifiedIonicView:
    def test_hcl_gives_both_heterolysis_and_redox(self):
        hcl = Molecule(("H", "Cl"), frozenset({Bond(0, 1)}))
        ie = ionic_edges(hcl)
        assert len(ie.heterolytic) == 2                  # both electron assignments
        assert len(ie.redox) == 2                        # 1- and 2-electron oxidations
        assert len(ie.ions) == 4                          # anion + cation per heterolysis

    def test_every_ionic_product_is_labelled_ion_never_a_compound(self):
        hcl = Molecule(("H", "Cl"), frozenset({Bond(0, 1)}))
        ie = ionic_edges(hcl)
        for ion in ie.ions:
            assert species_class(ion) is SpeciesClass.ION   # honest: an ion, not an isolable compound

    def test_a_charged_species_skips_heterolysis_but_still_has_redox(self):
        # the v1 heterolytic engine splits neutrals; an already-charged ion has no heterolysis here
        cation = Molecule(("H", "Cl"), frozenset({Bond(0, 1)}), charge=1)
        ie = ionic_edges(cation)
        assert ie.heterolytic == ()                      # documented boundary: recursive ionic descent
        assert len(ie.redox) >= 1                         # but redox still applies to any species
