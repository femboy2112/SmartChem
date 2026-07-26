"""
Brick 3, machine-checked: a termination rule that cannot be satisfied by claiming it was.

``THE_COMPILER.md`` section VI.3 asks for a loop that "must strictly reduce the number of
unbound free parameters, or the compiler halts and says which parameter it cannot reduce."
The whole difficulty is in the word *must*, because the cheapest implementation of that
sentence is a counter the loop decrements itself, and a counter the loop decrements itself
is satisfied by every responder including one that does nothing at all.

So the class that matters here is :class:`TestTheMeasureIsTakenNotReported`. The rest pin
what the loop is allowed to offer (section III), what it must ask anyway (section IX), what
it refuses to certify (section VI.2), and what it must report on the way out (section X).
"""
import pytest

from smartchem.category import Bond, Molecule
from smartchem.ledger import (
    COMPILED,
    COMPILED_SUBJECT_TO,
    STALLED,
    WIDENED,
    Round,
    Session,
    Slot,
    Spec,
    UnderivedMenu,
    reaction_slot,
    shepherd,
)
from smartchem.stoichiometry import stoichiometry_menu

#: Section I's example, transcribed. Two objects, masses and spins and positions, and the
#: positions "constrained -- but you have not said to what". Four unbound slots, which is
#: the "more than one hole" section VII gated this brick on.
SECTION_I = Spec("section-I", (
    Slot("testParticle.mass", "<value or range>"),
    Slot("testParticle.spin", "observe", binding="observe"),
    Slot("testParticle.position", "constrain"),
    Slot("testParticle2.mass", "<other value>"),
    Slot("testParticle2.spin", "observe", binding="observe"),
    Slot("testParticle2.position", "constrain"),
))

H2 = Molecule.diatomic("H", "H")
O2 = Molecule.diatomic("O", "O")
WATER = Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}))


def _bind_all(spec, holes):
    for hole in holes:
        spec = spec.bind(hole.name, "0.0")
    return spec


class TestTheMeasureIsTakenNotReported:
    """
    The anti-tautology class, and the reason this module is shaped the way it is.

    Three defects in this repository within two days were the same disease: a check whose
    input was derived from the thing it checked. A termination rule is the ideal fourth
    host, because "strictly reduced" is trivially true of any number the loop computes by
    subtracting what it was told it accomplished.
    """

    def test_the_measure_is_the_hand_counted_number_of_holes(self):
        """Four, counted off the fixture above by eye, not by calling the thing under test."""
        assert SECTION_I.measure() == 4
        assert len(SECTION_I.slots) == 6

    def test_a_responder_that_claims_progress_and_makes_none_halts(self):
        """
        The load-bearing test. This responder reports binding every hole it was shown and
        returns the spec untouched. A loop that trusted the report would run to COMPILED
        having changed nothing.
        """
        claimed = []

        def liar(spec, holes):
            claimed.extend(h.name for h in holes)
            return spec

        session = shepherd(SECTION_I, liar)
        assert session.outcome == STALLED
        assert not session
        assert len(claimed) == 4, "the responder did make the claim"
        assert session.spec.measure() == 4, "and nothing was actually bound"

    def test_an_equal_but_freshly_built_spec_is_still_no_progress(self):
        """Guards the other cheap shortcut: comparing identity instead of measuring."""
        session = shepherd(SECTION_I, lambda s, h: Spec(s.name, tuple(s.slots)))
        assert session.outcome == STALLED

    def test_both_measures_on_a_round_come_from_spec_objects(self):
        session = shepherd(SECTION_I, _bind_all)
        round_one = session.rounds[0]
        assert round_one.before == 4
        assert round_one.after == round_one.spec.measure() == 0

    def test_binding_returns_a_new_spec_and_leaves_the_original_alone(self):
        bound = SECTION_I.bind("testParticle.mass", "1.0")
        assert bound.measure() == 3
        assert SECTION_I.measure() == 4

    def test_binding_a_slot_that_is_not_there_raises_rather_than_no_ops(self):
        with pytest.raises(KeyError):
            SECTION_I.bind("testParticle.charge", "0")


class TestTheRuleHasTeeth:
    """Section VI.3, applied literally."""

    def test_a_round_that_reduces_is_allowed_to_continue(self):
        def one_at_a_time(spec, holes):
            return spec.bind(holes[0].name, "x")

        session = shepherd(SECTION_I, one_at_a_time)
        assert session.outcome == COMPILED
        assert len(session.rounds) == 4
        assert [r.after for r in session.rounds] == [3, 2, 1, 0]

    def test_it_names_the_parameter_it_could_not_reduce(self):
        stuck = "testParticle2.position"

        def all_but_one(spec, holes):
            for hole in holes:
                if hole.name != stuck:
                    spec = spec.bind(hole.name, "0.0")
            return spec

        session = shepherd(SECTION_I, all_but_one)
        assert session.outcome == STALLED
        assert session.stuck_on == (stuck,)
        assert stuck in session.explain()
        assert len(session.rounds) == 2, "one productive round, then the rephrase"

    def test_the_round_count_cannot_exceed_the_initial_measure(self):
        """
        Strict decrease over a non-negative integer bounds the loop, which is why there is
        no max-rounds knob to tune. ``LedgerContradiction`` guards the bound and is
        deliberately unreachable while the check above it stays strict -- it exists to
        catch a future relaxation of ``<`` to ``<=``, not a case reachable today.
        """
        for responder in (_bind_all, lambda s, h: s.bind(h[0].name, "x")):
            session = shepherd(SECTION_I, responder)
            assert len(session.rounds) <= SECTION_I.measure()


class TestWideningIsAnOutcomeOfItsOwn:
    """
    The place section VI.3's measure is wrong, reported rather than smoothed over.

    A round that binds one hole and opens two beneath it is ordinary refinement -- it is
    what section IX's shepherd does when it supplies vocabulary -- and it fails "strictly
    reduce" exactly as loudly as a round that rephrases.
    """

    @pytest.fixture
    def session(self):
        def deepen(spec, holes):
            return (spec.bind("testParticle.position", "relative to testParticle2")
                        .widen(Slot("testParticle.position.value", "<distance>"),
                               Slot("testParticle.position.units", "<units>")))
        return shepherd(SECTION_I, deepen)

    def test_it_halts(self, session):
        assert not session

    def test_it_is_not_reported_as_a_rephrase(self, session):
        assert session.outcome == WIDENED
        assert session.outcome != STALLED

    def test_it_names_the_parameters_that_opened(self, session):
        assert set(session.opened) == {"testParticle.position.value",
                                       "testParticle.position.units"}

    def test_the_explanation_says_the_measure_cannot_tell_the_two_apart(self, session):
        assert "ordinary refinement" in session.explain()

    def test_widening_a_slot_that_already_exists_raises(self):
        with pytest.raises(KeyError):
            SECTION_I.widen(Slot("testParticle.mass", "<again>"))


class TestAMenuCannotBeInvented:
    """Section III at the constructor, because review is the expensive way to enforce it."""

    def test_options_without_a_derivation_are_refused(self):
        with pytest.raises(UnderivedMenu):
            Slot("p.position", "constrain", menu=("adjacent", "fixed", "free"))

    def test_options_with_a_derivation_are_allowed(self):
        slot = Slot("p.position", "constrain", menu=("adjacent",), derivation="a source")
        assert slot.menu == ("adjacent",)

    def test_an_empty_menu_needs_no_derivation(self):
        assert Slot("p.position", "constrain").menu == ()

    def test_a_slot_with_no_derivable_options_is_still_asked_about(self):
        """
        Section IX: generous in interrogation. Refusing to ask because nothing could be
        enumerated is the courtier failure arriving from the other side -- silence reads as
        "nothing can be done here" when the truth is "this package cannot enumerate it".
        """
        question = Slot("p.position", "constrain").question()
        assert "constrain" in question
        assert "available language" in question

    def test_the_written_words_are_never_normalised_away(self):
        slot = Slot("p.position", "  CONSTRAIN, somehow  ")
        assert slot.written == "  CONSTRAIN, somehow  "
        assert "  CONSTRAIN, somehow  " in slot.question()


class TestTheChemicalMenuIsBrick0sVerbatim:
    """
    Section I's "there are exactly X admissible relations. Here they are." made literal.

    Without this class the module is a shape with no content: anything can enumerate
    options if it is allowed to invent them.
    """

    @pytest.fixture
    def slot(self):
        return reaction_slot("water.formation", "relate these somehow", (H2, O2, WATER))

    def test_the_options_are_the_menus_own_equations(self, slot):
        assert slot.menu == stoichiometry_menu((H2, O2, WATER)).equations()
        assert slot.menu, "the fixture must have something to offer"

    def test_the_derivation_names_the_source_and_the_verdict(self, slot):
        menu = stoichiometry_menu((H2, O2, WATER))
        assert "stoichiometry_menu" in slot.derivation
        assert menu.verdict in slot.derivation
        assert f"freedom {menu.freedom}" in slot.derivation

    def test_the_question_quotes_the_count_it_actually_has(self, slot):
        assert f"exactly {len(slot.menu)} admissible bindings" in slot.question()

    def test_a_derived_zero_is_not_reported_as_missing_vocabulary(self):
        """
        Brick 0's REFUSE verdict: enumerated, and the answer is none. That is the opposite
        claim from "nothing here can enumerate this", and the first version of
        ``question()`` collapsed them -- it would have told a scientist to find better
        words for a question that had already been answered by theorem.
        """
        slot = reaction_slot("impossible", "relate these", (H2, WATER))
        assert slot.menu == ()
        assert slot.derivation, "Brick 0 did run; that is the whole distinction"
        question = slot.question()
        assert "ZERO admissible bindings" in question
        assert "enumerated, not" in question
        assert "available language" not in question


class TestAPosterioriIsNotSilentlyUpgraded:
    """Section VI.1. Compiling subject to a condition is a different object."""

    def _spec(self, checkable_after):
        return Spec("t1-gated", (
            Slot("diagnostic", "T1 < 0.02", binding="T1 < 0.02",
                 checkable_after=checkable_after),
            Slot("basis", "<name>"),
            Slot("method", "<name>"),
        ))

    def test_it_gets_its_own_outcome_token(self):
        session = shepherd(self._spec(True), _bind_all)
        assert session.outcome == COMPILED_SUBJECT_TO
        assert session.outcome != COMPILED

    def test_the_same_spec_without_the_condition_compiles_outright(self):
        session = shepherd(self._spec(False), _bind_all)
        assert session.outcome == COMPILED

    def test_it_still_counts_as_closed(self):
        assert bool(shepherd(self._spec(True), _bind_all)) is True

    def test_the_condition_is_named_in_the_explanation(self):
        text = shepherd(self._spec(True), _bind_all).explain()
        assert "diagnostic" in text
        assert "AFTER" in text


class TestTheCasualtyList:
    """Section X: on every successful refinement, report what was discarded."""

    def test_the_discards_are_reported(self):
        session = shepherd(SECTION_I, _bind_all,
                           discarded=("memorylessness", "rate invariance"))
        assert session
        assert "memorylessness" in session.explain()
        assert "rate invariance" in session.explain()

    def test_an_empty_casualty_list_is_stated_rather_than_omitted(self):
        """Omitting it would read as 'nothing was lost', which is a different claim."""
        assert "nothing was recorded as discarded" in shepherd(SECTION_I,
                                                               _bind_all).explain()

    def test_a_halt_does_not_pretend_to_have_a_casualty_list(self):
        session = shepherd(SECTION_I, lambda s, h: s)
        assert "discarded on the way" not in session.explain()


class TestItNeverCertifiesMeaningful:
    """Section VI.2. Coherent is available; meaningful is the scientist's, permanently."""

    def test_a_successful_session_says_coherent_and_not_more(self):
        text = shepherd(SECTION_I, _bind_all).explain().lower()
        assert "coherent" in text
        for overclaim in ("meaningful", "is true", "is correct", "will work",
                          "guaranteed", "valid physics"):
            assert overclaim not in text

    def test_the_certification_is_scoped_to_the_declared_rules(self):
        assert "under the declared rules" in shepherd(SECTION_I, _bind_all).explain()


class TestThePositiveControl:
    """
    Without this, the suite proves nothing: almost every test above asserts a halt, and a
    ``shepherd`` that halted on absolutely everything would pass all of them.
    """

    def test_a_spec_with_nothing_missing_compiles_without_a_single_round(self):
        def never(spec, holes):
            raise AssertionError("a spec with no holes must not be interrogated")

        session = shepherd(Spec("done", (Slot("a", "1", binding="1"),)), never)
        assert session
        assert session.outcome == COMPILED
        assert session.rounds == ()
        assert session.stuck_on == () and session.opened == ()

    def test_the_types_are_what_they_say(self):
        session = shepherd(SECTION_I, _bind_all)
        assert isinstance(session, Session)
        assert all(isinstance(r, Round) for r in session.rounds)
        assert isinstance(session.spec, Spec)
