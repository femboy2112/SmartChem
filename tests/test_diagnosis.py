"""
Brick 2, machine-checked: a decline that says what would have to change.

``THE_COMPILER.md`` section VII names ``Na(excited) -> Na + photon`` as the design's
acceptance test and asks for a diagnosis rather than a boolean. These tests pin what the
diagnosis is allowed to claim, and -- more importantly -- what it must not.

The governing hazard is the one the whole repository exists to prevent, one level up: a
plausible wrong EXPLANATION of a decline is worse than a bare decline, because a bare
decline does not send anyone off to fix the wrong thing. So every obstruction has to be
traceable to something Brick 0 or Brick 1 actually computed, and the ``removable`` flag
has to be right, because that flag is the difference between an afternoon's work and a
research problem.
"""
import pytest

from smartchem.category import Config, Molecule, Reaction
from smartchem.diagnosis import (
    DISAGREED_OFFSET,
    INVARIANT_BLIND,
    UNMEASURABLE_OFFSET,
    UNPRICED,
    Diagnosis,
    diagnose,
)
from smartchem.oracle.heuristic import HeuristicOracle
from smartchem.oracle.photon import PhotonOracle

NA_EXCITED = Molecule(atoms=("Na",), state="excited")
NA = Molecule(atoms=("Na",))
H2 = Molecule.diatomic("H", "H")
QUANTUM_589 = Molecule.quantum("589nm")


def _kinds(diagnosis):
    return {o.kind for o in diagnosis.obstructions}


class TestTheAcceptanceCase:
    """``Na(excited) -> Na + photon``, the morphism section VII was written around."""

    @pytest.fixture
    def diagnosis(self):
        reaction = Reaction(Config((NA_EXCITED,)), Config((NA, QUANTUM_589)),
                            name="Na-deexcitation")
        return diagnose(reaction, [HeuristicOracle(), PhotonOracle(589.0)])

    def test_it_is_not_priceable_and_says_so_as_a_value(self, diagnosis):
        assert not diagnosis
        assert diagnosis.obstructions

    def test_the_excited_atom_is_named_as_the_species_nothing_prices(self, diagnosis):
        unpriced = [o for o in diagnosis.obstructions if o.kind == UNPRICED]
        assert [o.subject for o in unpriced] == [repr(NA_EXCITED)]
        assert diagnosis.oracles_for(NA_EXCITED) == ()

    def test_it_reports_every_reason_each_oracle_had_not_just_the_first(self, diagnosis):
        """
        Brick 1's ``refusals`` enumerates all failing axes on purpose. A diagnosis that
        collapsed them would hand back one axis to fix and hide the other two behind it.
        """
        detail = next(o.detail for o in diagnosis.obstructions if o.kind == UNPRICED)
        assert "heuristic (legacy)" in detail and "photon/589nm" in detail
        assert detail.count(";") >= 3

    def test_the_species_that_ARE_priceable_are_attributed(self, diagnosis):
        assert diagnosis.oracles_for(NA) == ("heuristic (legacy)",)
        assert diagnosis.oracles_for(QUANTUM_589) == ("photon/589nm",)

    def test_brick_0s_blindness_is_carried_through(self, diagnosis):
        """Na(*) and Na share a composition column; the quantum's column is all zero."""
        assert INVARIANT_BLIND in _kinds(diagnosis)

    def test_the_offset_question_is_NOT_raised_while_a_species_is_unpriced(self, diagnosis):
        """
        Order of obstructions is a claim in itself. Whether two zeros can be combined is
        moot while something in the reaction has no oracle at all, and reporting it anyway
        would be a fabricated second problem.
        """
        assert UNMEASURABLE_OFFSET not in _kinds(diagnosis)
        assert diagnosis.offset_ev is None


class TestTheCrossVerticalObstruction:
    """
    Every species priced, but by two different verticals -- so the offset between the two
    zeros becomes load bearing, and section VII's acceptance test actually fires.
    """

    @pytest.fixture
    def diagnosis(self):
        emission = Reaction(Config((H2,)), Config((H2, QUANTUM_589)), name="emission")
        return diagnose(emission, [HeuristicOracle(), PhotonOracle(589.0)])

    def test_each_species_has_an_oracle_yet_the_reaction_still_cannot_be_priced(self, diagnosis):
        assert diagnosis.oracles_for(H2) == ("heuristic (legacy)",)
        assert diagnosis.oracles_for(QUANTUM_589) == ("photon/589nm",)
        assert not diagnosis

    def test_the_obstruction_is_structural_and_it_is_the_only_structural_one(self, diagnosis):
        assert [o.kind for o in diagnosis.structural] == [UNMEASURABLE_OFFSET]

    def test_it_claims_unmeasurable_and_never_claims_wrong(self, diagnosis):
        """
        The weaker claim is the true one. An empty intersection does not establish that
        summing the two would be wrong -- in this very reaction the matter oracle's zero
        cancels between the two H2 terms. It establishes that the offset cannot be CHECKED.
        """
        detail = next(o.detail for o in diagnosis.structural)
        assert "cannot be measured" in detail
        assert "cannot be checked at all" in detail
        assert "known to be wrong" in detail   # as the thing it explicitly is not saying

    def test_it_names_what_would_remove_it(self, diagnosis):
        assert "One species both will price" in next(o.detail for o in diagnosis.structural)


class TestTheOffsetIsMeasuredAndNeverAssumed:
    """
    A shared species is a shared TOKEN, not automatically a shared REFERENCE.

    Two photon oracles at different wavelengths have a non-empty -- and ``is_exact`` --
    domain intersection whose sole member is the bare quantum, and they price that member
    differently. Reading "intersection non-empty" as "zeros align" would be exactly the
    plausible-and-wrong inference this package exists to refuse.
    """

    @pytest.fixture
    def diagnosis(self):
        reaction = Reaction(Config((QUANTUM_589,)), Config((Molecule.quantum("532nm"),)))
        return diagnose(reaction, [PhotonOracle(589.0), PhotonOracle(532.0)])

    def test_a_nonempty_intersection_does_not_end_the_question(self, diagnosis):
        assert DISAGREED_OFFSET in _kinds(diagnosis)
        assert not diagnosis

    def test_the_offset_is_an_actual_measurement(self, diagnosis):
        """Not a flag, a number -- and one obtained by calling both oracles."""
        assert diagnosis.offset_ev is not None
        a = PhotonOracle(589.0).energy(Molecule.quantum())
        b = PhotonOracle(532.0).energy(Molecule.quantum())
        assert diagnosis.offset_ev == pytest.approx(a.value_ev - b.value_ev, abs=1e-12)
        assert abs(diagnosis.offset_ev) > 0.2

    def test_the_number_appears_in_the_prose(self, diagnosis):
        assert f"{diagnosis.offset_ev:+.6f} eV" in next(
            o.detail for o in diagnosis.obstructions if o.kind == DISAGREED_OFFSET)


class TestThePositiveControl:
    """
    Without this the suite proves nothing. Every test above asserts an obstruction exists,
    and a ``diagnose`` that returned an obstruction for absolutely everything would pass
    all of them. Something has to come back clean.
    """

    def test_a_reaction_one_oracle_covers_entirely_has_no_obstruction(self):
        from smartchem.category import Bond
        water = Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}))
        reaction = Reaction(Config((H2, H2, Molecule.diatomic("O", "O"))),
                            Config((water, water)))
        diagnosis = diagnose(reaction, [HeuristicOracle()])
        assert diagnosis, diagnosis.explain()
        assert diagnosis.obstructions == ()
        assert "no obstruction" in diagnosis.explain()

    def test_a_single_oracle_covering_everything_skips_the_offset_question(self):
        """No second zero, no offset to check, and therefore no oracle calls made."""
        reaction = Reaction(Config((QUANTUM_589,)), Config((QUANTUM_589,)))
        diagnosis = diagnose(reaction, [PhotonOracle(589.0)])
        assert diagnosis.offset_ev is None


class TestTheContractWithTheValueLayer:
    def test_diagnose_changes_nothing_about_what_energy_returns(self):
        """
        Brick 2 is additive by design. Turning the ``Estimate | None`` contract into a
        richer type would have broken 52 test assertions and 17 internal call sites and
        every third-party ``EnergyOracle``, for a gain that is available without it.
        """
        from smartchem.thermo import reaction_energy
        reaction = Reaction(Config((NA_EXCITED,)), Config((NA, QUANTUM_589)))
        assert reaction_energy(reaction, HeuristicOracle()) is None

    def test_an_empty_oracle_set_is_a_diagnosis_not_a_crash(self):
        reaction = Reaction(Config((NA,)), Config((NA,)))
        diagnosis = diagnose(reaction, [])
        assert not diagnosis
        assert UNPRICED in _kinds(diagnosis)

    def test_removable_and_structural_partition_the_obstructions(self):
        reaction = Reaction(Config((H2,)), Config((H2, QUANTUM_589)))
        d = diagnose(reaction, [HeuristicOracle(), PhotonOracle(589.0)])
        assert len(d.removable) + len(d.structural) == len(d.obstructions)
        assert set(d.removable).isdisjoint(d.structural)

    def test_explain_mentions_every_obstruction_it_holds(self):
        """A summary that silently drops one is the renderer defect in another costume."""
        reaction = Reaction(Config((NA_EXCITED,)), Config((NA, QUANTUM_589)))
        d = diagnose(reaction, [HeuristicOracle(), PhotonOracle(589.0)])
        text = d.explain()
        for obstruction in d.obstructions:
            assert obstruction.kind in text
            assert obstruction.subject in text
        assert isinstance(d, Diagnosis)
