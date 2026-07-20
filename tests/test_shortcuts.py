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
    Bond,
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

    def test_scaling_a_reaction_does_not_change_either_verdict(self):
        """
        Both predicates compare multisets, so doubling every coefficient must be a no-op.
        Worth pinning because the reaction enumerator relies on it: it discards 2X -> 2Y as
        a duplicate of X -> Y, which is only sound if the classification agrees.
        """
        single = Reaction(Config.of(_dia("H", "Cl"), _atom("F")),
                          Config.of(_dia("H", "F"), _atom("Cl")))
        doubled = Reaction(
            Config.of(_dia("H", "Cl"), _dia("H", "Cl"), _atom("F"), _atom("F")),
            Config.of(_dia("H", "F"), _dia("H", "F"), _atom("Cl"), _atom("Cl")),
        )
        assert is_isodesmic(single) == is_isodesmic(doubled)
        assert is_bond_order_conserving(single) == is_bond_order_conserving(doubled)


class TestIsodesmicCoverageWasTheBlocker:
    """
    Why `is_isodesmic` went unmeasured for so long, recorded as a fact about the SPECIES
    SET rather than about the energies.

    Enumerating every mass-balanced reaction over the nine originally-referenced species
    and letting the predicate sort them returned exactly ONE strictly isodesmic reaction.
    The blocker was never the cost of the energies -- it was that n=1 cannot measure a
    predicate, and no amount of care with the oracle changes that.

    This is the shape of mistake worth pinning: the obvious next step (run better energies)
    would have produced a confident-looking number from a sample of one.
    """

    #: bond-order-conserving, and the ONLY isodesmic reaction available over the original
    #: nine species. Every other conserving reaction there changes at least one bond TYPE.
    ETHANOL_SWAP = ("C2H6 + CH3OH -> C2H5OH + CH4",)

    def test_a_reaction_can_conserve_order_while_changing_every_type(self):
        """
        The reason the isodesmic set is so much thinner than the order-conserving one.
        C2H6 + H2 -> 2 CH4 keeps the bond-order multiset (8 single in, 8 single out) while
        replacing a C-C and an H-H with two C-H. Order is cheap to conserve; type is not.
        """
        c2h6 = Molecule(("C", "C", "H", "H", "H", "H", "H", "H"),
                        frozenset({Bond(0, 1), Bond(0, 2), Bond(0, 3), Bond(0, 4),
                                   Bond(1, 5), Bond(1, 6), Bond(1, 7)}))
        ch4 = Molecule(("C", "H", "H", "H", "H"),
                       frozenset({Bond(0, 1), Bond(0, 2), Bond(0, 3), Bond(0, 4)}))
        rxn = Reaction(Config.of(c2h6, _dia("H", "H")), Config.of(ch4, ch4))
        assert is_bond_order_conserving(rxn)
        assert not is_isodesmic(rxn)

    def test_the_species_that_unlock_the_class_are_cheap_to_canonicalise(self):
        """
        The fix was coverage, and it had to be coverage the canonicaliser could afford.
        Each of these unlocks at least one strictly isodesmic reaction and costs less than
        the budget by orders of magnitude; propane would unlock more and does not.
        """
        from smartchem.category import _MAX_CANONICAL_CANDIDATES, _canonical_cost

        affordable = {
            "CH2O": ("C", "O", "H", "H"),
            "HCOOH": ("C", "O", "O", "H", "H"),
            "CH3OCH3": ("C", "C", "O", "H", "H", "H", "H", "H", "H"),
        }
        for name, atoms in affordable.items():
            assert _canonical_cost(atoms) < _MAX_CANONICAL_CANDIDATES / 10, name

        propane = ("C", "C", "C") + ("H",) * 8
        assert _canonical_cost(propane) > _MAX_CANONICAL_CANDIDATES, (
            "propane is expected to remain out of reach until the canonical key is "
            "refined by degree as well as symbol"
        )


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


# ======================================================================================
# Separating geometry determination from energy evaluation
# ======================================================================================
class TestGeometryTierPlumbing:
    """
    The scan and the single point ask different questions, so they may be answered at
    different tiers. These check the wiring without running PySCF; the accuracy claim is
    pinned separately below.
    """

    def _oracle(self, **kw):
        from smartchem.oracle.pyscf_oracle import PySCFOracle
        return PySCFOracle("CCSD(T)", "cc-pVTZ", tight_d=False, **kw)

    def test_no_geometry_tier_means_no_sub_oracle(self):
        assert self._oracle()._geom_oracle is None

    def test_a_geometry_tier_builds_a_sub_oracle_at_that_tier(self):
        o = self._oracle(optimize_geometry=True, geometry_tier=("MP2", "cc-pVDZ"))
        assert o._geom_oracle is not None
        assert o._geom_oracle.method == "MP2"
        assert o._geom_oracle.basis == "cc-pVDZ"

    def test_the_sub_oracle_does_not_recurse(self):
        """optimize_geometry=False on the child is the whole termination argument."""
        o = self._oracle(optimize_geometry=True, geometry_tier=("HF", "cc-pVDZ"))
        assert o._geom_oracle.optimize_geometry is False
        assert o._geom_oracle._geom_oracle is None

    def test_provenance_records_both_tiers(self):
        """
        A result whose geometry came from a different method is not the same result, and
        the name has to say so -- the same reason tight_d is in the name.
        """
        o = self._oracle(optimize_geometry=True, geometry_tier=("MP2", "cc-pVDZ"))
        assert "//" in o.name and "MP2" in o.name and "cc-pVDZ" in o.name

    def test_the_energy_tier_is_unaffected(self):
        o = self._oracle(optimize_geometry=True, geometry_tier=("HF", "cc-pVDZ"))
        assert o.method == "CCSD(T)" and o.basis == "cc-pVTZ"


class TestGeometryTierWasMeasured:
    """
    Transcribed from scratchpad/geometry_tier.json. Energy tier held fixed at
    CCSD(T)/cc-pVTZ; only the tier the SCAN runs at varies. One variable at a time.

    Pre-registered: P1 HF r_e within 0.03 A of the full scan; P2 MP2 within 0.015 A and
    BETTER than HF; P3 |d MAE| < 0.30 kcal/mol; P4 speedup >= 3x.
    """

    FULL_MAE = 4.99
    ARMS = {
        "MP2/cc-pVDZ": {"d_re_max": 0.0289, "mae": 5.26, "speedup": 3.64},
        "HF/cc-pVDZ":  {"d_re_max": 0.0236, "mae": 5.27, "speedup": 3.08},
    }

    @pytest.mark.parametrize("arm", sorted(ARMS))
    def test_p3_accuracy_cost_stayed_under_the_pre_registered_bar(self, arm):
        assert abs(self.ARMS[arm]["mae"] - self.FULL_MAE) < 0.30

    @pytest.mark.parametrize("arm", sorted(ARMS))
    def test_p3_passed_but_with_almost_no_margin(self, arm):
        """
        Honesty about how close this was. Both arms landed at 0.27-0.28 against a 0.30
        bar, on n=7. That is a pass, not a comfortable one, and it is why the option is
        opt-in rather than the default.
        """
        assert abs(self.ARMS[arm]["mae"] - self.FULL_MAE) > 0.20

    @pytest.mark.parametrize("arm", sorted(ARMS))
    def test_p4_speedup_cleared_three_times(self, arm):
        assert self.ARMS[arm]["speedup"] >= 3.0

    def test_p2_was_falsified(self):
        """
        MP2 was predicted to give geometries closer to the full tier than HF, and within
        0.015 A. It did neither: 0.0289 A, and WORSE than HF's 0.0236. Kept on the record
        because the prediction was written down before the run.
        """
        assert self.ARMS["MP2/cc-pVDZ"]["d_re_max"] > 0.015
        assert self.ARMS["MP2/cc-pVDZ"]["d_re_max"] > self.ARMS["HF/cc-pVDZ"]["d_re_max"]

    def test_the_speedup_ordering_between_arms_is_not_a_result(self):
        """
        HF/cc-pVDZ measured SLOWER overall than MP2/cc-pVDZ, which cannot reflect work
        done -- MP2 is HF plus a correction. Per-species wall-clock swung ~3.4x on
        identical final calculations, so the timing carries that much noise. The claim is
        "about 3x", and the 3.64-vs-3.08 ordering is not resolvable.
        """
        arms = [a["speedup"] for a in self.ARMS.values()]
        assert max(arms) - min(arms) < 1.0
