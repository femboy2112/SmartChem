"""
Algebraic shortcuts: what the category lets us NOT compute.

The oracle is the expensive layer, and the interesting question is not "how do we make
CCSD(T) faster" -- we do not, and cannot -- but "which oracle calls can be proven
unnecessary before any of them run". Two are implemented, and they sit at very different
levels of proof:

**Exact, and shipped as policy.** A spectator species cancels identically in ``dE`` by the
monoidal law. It is never priced, and its uncertainty never enters the error bar. There is
no approximation anywhere in the argument, so the system simply does it. Covered by
``test_functor.py::TestSpectatorsAreCancelledStructurally``; here we check the structural
predicate underneath it.

**Approximate, and deliberately NOT shipped as policy.** Bond-order conservation predicts
partial cancellation of method error. Measured, it buys about a factor of two -- real, but
less than the factor of three predicted in advance. So ``is_bond_order_conserving`` decides and
reports the property; nothing downgrades a tier automatically on the strength of it.

That split is the whole discipline: an exact law becomes behaviour, a measured tendency
becomes a labelled observation, and the two never get confused for one another.
"""
from __future__ import annotations

import pytest

from smartchem.category import (
    Config,
    Molecule,
    Reaction,
    bond_order_profile,
    bond_signature,
    identity,
    is_bond_order_conserving,
    is_isodesmic,
    reaction_residue,
)


def _atom(s):
    return Molecule.atom(s)


def _dia(a, b, order=1):
    return Molecule.diatomic(a, b, order=order)


# ======================================================================================
# The exact shortcut: spectators are structurally invisible
# ======================================================================================
class TestReactionResidue:
    def test_a_reaction_without_spectators_is_unchanged(self):
        rxn = Reaction(Config.of(_atom("H"), _atom("H")), Config.of(_dia("H", "H")))
        left, right = reaction_residue(rxn)
        assert left == rxn.dom and right == rxn.cod

    def test_a_spectator_is_removed_from_both_sides(self):
        fe = _atom("Fe")
        rxn = Reaction(Config.of(_atom("H"), _atom("H"), fe),
                       Config.of(_dia("H", "H"), fe))
        left, right = reaction_residue(rxn)
        assert fe not in left.species and fe not in right.species
        assert left.species == (_atom("H"), _atom("H"))

    def test_multiplicity_is_respected_not_just_membership(self):
        """
        Two Fe in, one Fe out: one of them is a spectator and one is consumed. Removing
        both would be wrong, and a set-based implementation would do exactly that.
        """
        fe = _atom("Fe")
        rxn = Reaction(Config.of(fe, fe, _atom("O")), Config.of(fe, _dia("Fe", "O")))
        left, right = reaction_residue(rxn)
        assert left.species.count(fe) == 1, "the surviving Fe should still be priced"
        assert right.species.count(fe) == 0

    def test_identity_reduces_to_nothing(self):
        obj = Config.of(_dia("N", "N", order=3), _atom("Fe"))
        left, right = reaction_residue(identity(obj))
        assert left.species == () and right.species == ()

    def test_residue_stays_balanced(self):
        fe = _atom("Fe")
        rxn = Reaction(Config.of(_atom("H"), _atom("H"), fe),
                       Config.of(_dia("H", "H"), fe))
        left, right = reaction_residue(rxn)
        assert left.formula == right.formula
        assert left.charge == right.charge


# ======================================================================================
# The approximate one: decidable, measured, and not acted on automatically
# ======================================================================================
class TestBondSignature:
    def test_free_atoms_have_no_bonds(self):
        assert bond_signature(Config.atoms("H", "Cl")) == {}

    def test_order_is_part_of_the_type(self):
        single = bond_signature(Config.of(_dia("N", "N", order=1)))
        triple = bond_signature(Config.of(_dia("N", "N", order=3)))
        assert single != triple

    def test_the_type_is_undirected(self):
        assert bond_signature(Config.of(_dia("H", "Cl"))) == \
               bond_signature(Config.of(_dia("Cl", "H")))

    def test_counts_accumulate_across_species(self):
        sig = bond_signature(Config.of(_dia("H", "Cl"), _dia("H", "Cl")))
        assert sig[(("Cl", "H"), 1)] == 2


#: the exact reactions the isodesmic measurement scored, so the predicate and the number
#: cannot drift apart. Kept here rather than in the docstring because a test can check it.
MEASURED_CREATING = [
    ("2H -> H2",     Reaction(Config.of(_atom("H"), _atom("H")), Config.of(_dia("H", "H")))),
    ("H+F -> HF",    Reaction(Config.of(_atom("H"), _atom("F")), Config.of(_dia("H", "F")))),
    ("H+Cl -> HCl",  Reaction(Config.of(_atom("H"), _atom("Cl")), Config.of(_dia("H", "Cl")))),
    ("2Cl -> Cl2",   Reaction(Config.of(_atom("Cl"), _atom("Cl")), Config.of(_dia("Cl", "Cl")))),
    ("2F -> F2",     Reaction(Config.of(_atom("F"), _atom("F")), Config.of(_dia("F", "F")))),
]
MEASURED_CONSERVING = [
    ("HCl+F -> HF+Cl", Reaction(Config.of(_dia("H", "Cl"), _atom("F")),
                                Config.of(_dia("H", "F"), _atom("Cl")))),
    ("H2+Cl -> HCl+H", Reaction(Config.of(_dia("H", "H"), _atom("Cl")),
                                Config.of(_dia("H", "Cl"), _atom("H")))),
    ("H2+F -> HF+H",   Reaction(Config.of(_dia("H", "H"), _atom("F")),
                                Config.of(_dia("H", "F"), _atom("H")))),
    ("F2+H -> HF+F",   Reaction(Config.of(_dia("F", "F"), _atom("H")),
                                Config.of(_dia("H", "F"), _atom("F")))),
]


class TestIsBondOrderConserving:
    def test_atomization_creates_a_bond_from_nothing(self):
        rxn = Reaction(Config.of(_atom("H"), _atom("H")), Config.of(_dia("H", "H")))
        assert not is_bond_order_conserving(rxn)

    def test_exchange_of_like_bonds_conserves(self):
        """HCl + F -> HF + Cl: one single bond in, one single bond out."""
        rxn = Reaction(Config.of(_dia("H", "Cl"), _atom("F")),
                       Config.of(_dia("H", "F"), _atom("Cl")))
        assert is_bond_order_conserving(rxn)

    def test_identity_is_trivially_conserving(self):
        assert is_bond_order_conserving(identity(Config.of(_dia("C", "O", order=3))))

    def test_order_is_not_ignored(self):
        """A single bond becoming a triple is not order-conserving even though the
        partners are identical."""
        rxn = Reaction(Config.of(_dia("N", "N", order=1)),
                       Config.of(_dia("N", "N", order=3)))
        assert not is_bond_order_conserving(rxn)

    @pytest.mark.parametrize("name,rxn", MEASURED_CONSERVING, ids=lambda v: getattr(v, "", v))
    def test_every_reaction_scored_as_conserving_satisfies_the_predicate(self, name, rxn):
        """
        The guard against the mistake this file was written to catch: the measured table
        must be attached to the predicate the measured set actually satisfies.
        """
        assert is_bond_order_conserving(rxn), name

    @pytest.mark.parametrize("name,rxn", MEASURED_CREATING, ids=lambda v: getattr(v, "", v))
    def test_every_reaction_scored_as_creating_fails_the_predicate(self, name, rxn):
        assert not is_bond_order_conserving(rxn), name


class TestIsodesmicIsStrictlyStronger:
    def test_the_measured_conserving_set_is_mostly_not_isodesmic(self):
        """
        The correction that produced this class. HCl + F -> HF + Cl preserves bond ORDERS
        but not bond TYPES, so it is bond-order conserving and NOT isodesmic. Attaching
        the measured ratio to ``is_isodesmic`` would have been claiming a number for a
        property the experiment never varied.
        """
        non_isodesmic = [n for n, r in MEASURED_CONSERVING if not is_isodesmic(r)]
        assert len(non_isodesmic) == 4, non_isodesmic

    def test_isodesmic_implies_bond_order_conserving(self):
        rxn = Reaction(Config.of(_dia("H", "Cl"), _dia("H", "Cl")),
                       Config.of(_dia("H", "Cl"), _dia("H", "Cl")))
        assert is_isodesmic(rxn)
        assert is_bond_order_conserving(rxn)

    def test_the_converse_fails(self):
        rxn = Reaction(Config.of(_dia("H", "Cl"), _atom("F")),
                       Config.of(_dia("H", "F"), _atom("Cl")))
        assert is_bond_order_conserving(rxn)
        assert not is_isodesmic(rxn)

    def test_neither_predicate_asks_an_oracle(self):
        """Both are decided from structure alone -- there is no oracle parameter to pass,
        which is the entire reason they can run ahead of the expensive layer."""
        rxn = Reaction(Config.of(_atom("H"), _atom("H")), Config.of(_dia("H", "H")))
        assert is_bond_order_conserving(rxn) is False
        assert is_isodesmic(rxn) is False


class TestTheMeasuredEffectIsRecorded:
    """
    Pins the numbers so the claim in the docstring cannot quietly drift from the run that
    produced it. These are transcribed from scratchpad/isodesmic.json, measured against
    experimental D0 over 5 bond-creating and 4 bond-conserving diatomic reactions.

    Recorded because the prediction FAILED: a ratio above 3 was pre-registered and the
    measurement returned 2.52 and 2.14. Keeping the falsified prediction next to the
    result is the only reason the number is trustworthy later.
    """

    MEASURED = {
        "HF/cc-pVTZ":      {"creating": 1.8847, "conserving": 0.7475, "ratio": 2.52},
        "CCSD(T)/cc-pVTZ": {"creating": 0.1265, "conserving": 0.0592, "ratio": 2.14},
    }
    PREDICTED_RATIO_FLOOR = 3.0

    @pytest.mark.parametrize("tier", sorted(MEASURED))
    def test_conserving_reactions_really_are_easier(self, tier):
        row = self.MEASURED[tier]
        assert row["conserving"] < row["creating"]

    @pytest.mark.parametrize("tier", sorted(MEASURED))
    def test_the_ratio_is_what_was_measured_not_what_was_predicted(self, tier):
        row = self.MEASURED[tier]
        assert row["creating"] / row["conserving"] == pytest.approx(row["ratio"], abs=0.01)
        assert row["ratio"] < self.PREDICTED_RATIO_FLOOR, (
            "the pre-registered prediction was a ratio above 3; it was not met, and this "
            "test exists to keep that on the record"
        )

    def test_the_effect_survives_an_order_of_magnitude_change_in_tier(self):
        """
        HF and CCSD(T)/TZ differ by ~15x in absolute error, yet the ratio is 2.52 vs 2.14.
        That stability is the evidence the mechanism is bond-local error cancellation
        rather than an accident of one method.
        """
        ratios = [r["ratio"] for r in self.MEASURED.values()]
        assert max(ratios) - min(ratios) < 0.5
