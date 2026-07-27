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
from collections import Counter
from itertools import combinations, combinations_with_replacement

import pytest

from smartchem.category import Bond, Molecule
from smartchem.ledger import (
    COMPILED,
    COMPILED_SUBJECT_TO,
    EXHAUSTED,
    STALLED,
    WIDENED,
    IllFoundedRank,
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
        With every rank 0 the bound is still the plain count, and still a theorem: no
        descent can add a hole, so the loop cannot outrun it. ``LedgerContradiction``
        guards that and stays deliberately unreachable while the check above it is strict
        -- it exists to catch a future relaxation of ``<`` to ``<=``, not a case reachable
        today. The conditional version of the same bound is :data:`EXHAUSTED`; see
        ``TestTheBoundIsAConditionalOnceRanksExist``.
        """
        assert SECTION_I.bound_is_theorem()
        assert SECTION_I.round_bound() == SECTION_I.measure() == 4
        for responder in (_bind_all, lambda s, h: s.bind(h[0].name, "x")):
            session = shepherd(SECTION_I, responder)
            assert len(session.rounds) <= SECTION_I.measure()


class TestWideningWithoutRanksStillHalts:
    """
    The regression guard on the repair: an UNRANKED spec behaves exactly as it used to.

    Section I's fixture declares no ranks, so every slot is rank 0 and nothing sits below
    rank 0. A round that binds one hole and opens two therefore has nothing simpler to
    descend to, and it halts -- which is what the cardinality rule did, for a reason that
    is now stated rather than accidental. If this class ever starts passing by compiling,
    the ordinal is accepting a widening it has no grounds to accept.
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

    def test_the_explanation_says_what_a_legal_deepening_would_have_needed(self, session):
        text = session.explain()
        assert "not strictly simpler" in text
        assert "must declare a rank below" in text
        assert "nothing sits below rank 0" in text

    def test_widening_a_slot_that_already_exists_raises(self):
        with pytest.raises(KeyError):
            SECTION_I.widen(Slot("testParticle.mass", "<again>"))


#: One abstract question that may be unfolded once. Hand-written, and the ranks are the
#: point: ``geometry`` is rank 1 because "constrain the geometry" is a question that
#: decomposes, and the two slots it decomposes into are rank 0 because they are answers.
RANKED = Spec("ranked", (
    Slot("geometry", "constrain it somehow", rank=1),
))


def _unfold_geometry(spec, holes):
    """Unfold the abstract slot once, then answer the concrete ones it opened."""
    if any(hole.name == "geometry" for hole in holes):
        return (spec.bind("geometry", "internal coordinates")
                    .widen(Slot("geometry.bond_length", "<distance>"),
                           Slot("geometry.units", "<units>")))
    for hole in holes:
        spec = spec.bind(hole.name, "0.0")
    return spec


def _fan_five(spec, holes):
    """
    Unfold the most abstract hole into FIVE sub-questions, against a budget bought for two.

    Every round descends -- five holes of rank ``r-1`` really are simpler than one of rank
    ``r`` -- so nothing here is illegitimate. It just costs more rounds than the declared
    fan-out paid for.
    """
    deepest = max(holes, key=lambda hole: hole.rank)
    spec = spec.bind(deepest.name, "unfolded")
    if deepest.rank == 0:
        return spec
    index = len(spec.slots)
    return spec.widen(*[Slot(f"{deepest.name}.{index}.{i}", "<sub>",
                             rank=deepest.rank - 1) for i in range(5)])


class TestTheWellFoundedMeasureAdmitsDeepening:
    """
    The repair itself: the round that used to halt the loop now continues it.

    Section VII recorded the cardinality rule's failure as the informative part of Brick 3
    -- "a cardinality measure is the wrong measure for a shepherding loop, and section VI.3
    will need a well-founded one". This class is that measure, doing the one thing the old
    one could not.
    """

    def test_the_ordinal_is_the_hand_written_multiset_of_ranks(self):
        """Counted off the fixtures by eye, not by calling the thing under test."""
        assert RANKED.ordinal() == (1,)
        assert SECTION_I.ordinal() == (0, 0, 0, 0)
        assert Spec("empty", ()).ordinal() == ()

    def test_a_deepening_round_is_allowed_to_continue(self):
        session = shepherd(RANKED, _unfold_geometry)
        assert session
        assert session.outcome == COMPILED

    def test_the_count_rises_on_the_very_round_the_measure_falls(self):
        """
        The whole disagreement between the two rules, on one round object. Under section
        VI.3 as written this round is a failure; under the multiset order it is progress.
        """
        session = shepherd(RANKED, _unfold_geometry)
        first = session.rounds[0]
        assert (first.before, first.after) == (1, 2), "one hole became two"
        assert first.reduced is False, "section VI.3's literal rule says this failed"
        assert first.descended is True, "the well-founded measure says it progressed"
        assert (first.before_ordinal, first.after_ordinal) == ((1,), (0, 0))
        assert "deepened: more holes, simpler ones" in repr(first)

    def test_a_rephrase_inside_a_ranked_spec_is_still_a_stall(self):
        """The permission is for deepening only; it is not a general amnesty."""
        session = shepherd(RANKED, lambda s, h: s)
        assert session.outcome == STALLED

    def test_opening_a_hole_at_the_same_rank_is_not_a_descent(self):
        def sideways(spec, holes):
            return (spec.bind("geometry", "something")
                        .widen(Slot("geometry.restated", "<same question>", rank=1)))

        session = shepherd(RANKED, sideways)
        assert session.outcome == WIDENED
        assert session.opened == ("geometry.restated",)

    def test_the_sort_is_the_termination_argument(self):
        """
        THE MUTANT THIS CLASS EXISTS FOR: drop ``reverse=True`` from ``Spec.ordinal`` and
        every other test in this file still passes.

        Lexicographic order on arbitrary tuples of naturals is not well-founded, and the
        infinite descent is realisable rather than theoretical: this responder closes its
        rank-1 hole and opens a rank-0 and a rank-1 hole, forever. Sorted descending the
        round reads ``(1,) -> (1, 0)``, an increase, and halts here. Unsorted it reads
        ``(1,) -> (0, 1)``, which every comparison in this module would call a descent,
        and the loop never stops -- the budget would eventually cut it off and report
        EXHAUSTED, so the assertion below is on WIDENED specifically.
        """
        def never_simpler(spec, holes):
            n = len(spec.slots)
            return (spec.bind("geometry", "one level down")
                        .widen(Slot(f"answered.{n}", "<a real answer>", rank=0),
                               Slot(f"geometry.{n}", "and constrain THAT", rank=1)))

        session = shepherd(RANKED, never_simpler)
        assert session.outcome == WIDENED, "an unsorted ordinal accepts this forever"
        assert len(session.rounds) == 1


class TestTheOrderIsTheOneItClaimsToBe:
    """
    The mathematical claim under the termination proof, decided by exhaustive search rather
    than asserted in a docstring.

    ``Spec.ordinal`` compares descending-sorted tuples with Python's ``<``, and the whole
    argument for termination is that this *is* the Dershowitz--Manna multiset order, which
    is well-founded. That is a claim about two definitions agreeing, so it is checkable the
    only honest way: implement the textbook definition separately and enumerate.
    """

    @staticmethod
    def _dershowitz_manna_greater(bigger, smaller):
        """
        ``M >mul N`` iff ``N == (M - X) + Y`` for some nonempty ``X`` in ``M`` with every
        ``y`` in ``Y`` strictly less than some ``x`` in ``X``.

        Written straight from the definition, over ``Counter``, with no reference to sorting
        or to tuple comparison -- if it shared any machinery with the thing it checks it
        would be worth nothing.
        """
        big, small = Counter(bigger), Counter(smaller)
        for size in range(1, sum(big.values()) + 1):
            for combo in combinations(sorted(big.elements()), size):
                removed = Counter(combo)
                kept = big - removed
                if kept - small:                      # kept must survive into N
                    continue
                added = small - kept
                if all(y < max(removed.elements()) for y in added.elements()):
                    return True
        return False

    @pytest.mark.parametrize("size", [0, 1, 2, 3])
    def test_it_agrees_with_the_textbook_definition_on_every_small_multiset(self, size):
        """
        Every multiset of ranks drawn from {0,1,2} up to size 3, against every other. The
        ranks are small on purpose: the order only ever compares whole multisets, so a
        disagreement would show up at this size or not be about the definition at all.
        """
        universe = [tuple(sorted(c, reverse=True))
                    for n in range(4)
                    for c in combinations_with_replacement((0, 1, 2), n)]
        subjects = [m for m in universe if len(m) == size]
        assert subjects, "the parametrisation must actually test something"

        for bigger in subjects:
            for smaller in universe:
                # ASCENDING slot order, deliberately. Built descending, this loop cannot
                # tell a correct sort from no sort at all -- it would be handing the
                # subject its own answer, which is the failure mode this file exists to
                # avoid. Measured: with the slots pre-sorted, `sort-dropped-entirely`
                # survives every assertion in this class.
                spec_big = Spec("b", tuple(Slot(f"b{i}", "<x>", rank=r)
                                           for i, r in enumerate(reversed(bigger))))
                spec_small = Spec("s", tuple(Slot(f"s{i}", "<x>", rank=r)
                                             for i, r in enumerate(reversed(smaller))))
                by_code = spec_small.ordinal() < spec_big.ordinal()
                by_definition = self._dershowitz_manna_greater(bigger, smaller)
                assert by_code == by_definition, (
                    f"{bigger} vs {smaller}: ordinal says {by_code}, "
                    f"Dershowitz-Manna says {by_definition}")

    def test_the_definition_used_above_is_not_vacuous(self):
        """
        A check that never fires proves nothing, and this file has been bitten by exactly
        that before. Both verdicts must be reachable from the reference implementation.
        """
        assert self._dershowitz_manna_greater((1,), (0, 0)), "one hole into two simpler"
        assert not self._dershowitz_manna_greater((1,), (1, 0)), "into one simpler and one not"
        assert not self._dershowitz_manna_greater((1,), (1,)), "a rephrase"
        assert not self._dershowitz_manna_greater((0, 0), (1,)), "two into one harder"


class TestRanksIndexAWellFoundedOrder:
    """The hypothesis the termination proof rests on, enforced where it can be checked."""

    def test_a_negative_rank_is_refused_at_construction(self):
        with pytest.raises(IllFoundedRank):
            Slot("bottomless", "<anything>", rank=-1)

    def test_the_refusal_says_which_theorem_it_is_protecting(self):
        with pytest.raises(IllFoundedRank, match="infinite descent"):
            Slot("bottomless", "<anything>", rank=-1)

    def test_rank_zero_is_allowed_and_is_the_default(self):
        assert Slot("plain", "<x>").rank == 0
        assert Slot("plain", "<x>", rank=0).rank == 0

    @pytest.mark.parametrize("bad", [float("inf"), float("nan"), 2.0, "3", None])
    def test_a_rank_that_is_not_an_integer_is_refused(self, bad):
        """
        ``rank: int`` is an annotation, and annotations do not run. The sign test alone is
        defeated by exactly the two values that break the order, because ``inf < 0`` and
        ``nan < 0`` are both False.
        """
        with pytest.raises(IllFoundedRank):
            Slot("mistyped", "<anything>", rank=bad)

    def test_what_the_missing_type_check_actually_cost(self):
        """
        The guard demonstrated to be load-bearing rather than asserted to be.

        The bypass is deliberate -- ``object.__setattr__`` is the only way to build what
        the constructor now refuses -- and it shows the two distinct failures a float
        bought. ``inf``: the round budget becomes infinite, so ``len(rounds) >= budget``
        is False for every finite round count and the loop's ONLY backstop against a
        runaway responder is silently off. ``nan``: every comparison against it is False,
        so the ranks stop forming an order at all.
        """
        runaway = Slot("smuggled", "<x>", rank=0)
        object.__setattr__(runaway, "rank", float("inf"))
        assert not (runaway.rank < 0), "the sign test alone waves it straight through"
        spec = Spec("runaway", (runaway,))
        assert spec.round_bound(2) == float("inf")
        assert not (10 ** 9 >= spec.round_bound(2)), "no finite round count can trip it"

    def test_and_what_a_nan_rank_costs_is_worse_than_a_wrong_answer(self):
        """
        MEASURED, because the obvious guess about nan is wrong in an instructive way.

        The guess is "every comparison against nan is False, so a real descent is rejected".
        That holds only for DISTINCT nan objects, and then it is a trichotomy failure --
        neither ``<`` nor ``>`` nor ``==`` -- which is precisely what "not an order" means.
        When the two specs share one nan object, CPython's tuple ``==`` takes an identity
        shortcut, the nan is skipped, and the comparison proceeds as though it were absent.
        So the same logical spec answers differently depending on whether a Slot was reused
        or rebuilt. Not a wrong order: no order, plus a result that depends on object
        identity. Hence the constructor refuses the type rather than testing the value.
        """
        def ordinal_with(nan, tail):
            poisoned = Slot("poisoned", "<x>", rank=0)
            object.__setattr__(poisoned, "rank", nan)
            return Spec("p", (poisoned, Slot("real", "<x>", rank=tail))).ordinal()

        first, second = float("nan"), float("nan")
        low, high = ordinal_with(first, 1), ordinal_with(second, 3)
        assert not low < high and not high < low and not low == high, "trichotomy fails"

        shared = float("nan")
        assert ordinal_with(shared, 1) < ordinal_with(shared, 3), (
            "and one shared object silently restores a comparison the other case refused")

    def test_the_largest_rank_never_rises_across_an_accepted_round(self):
        """
        A consequence of the ordering, asserted on real sessions rather than argued: a
        larger leading element makes the tuple lexicographically larger, so a round that
        raises the maximum rank cannot descend. It is what keeps an all-rank-0 spec
        all-rank-0, which is what makes its round bound unconditional.
        """
        session = shepherd(RANKED, _unfold_geometry)
        peaks = [max(r.before_ordinal, default=0) for r in session.rounds]
        peaks += [max(session.rounds[-1].after_ordinal, default=0)]
        assert peaks == sorted(peaks, reverse=True)


class TestTheDiagnosisIsReadOffTheMeasureItGatedOn:
    """
    The reason a round halted must come from the quantity that halted it.

    Found by an adversarial pass over the committed module. A responder that binds two
    rank-0 holes and hands the third back with its rank raised 0 -> 5 was correctly
    REFUSED -- the ordinal rose, so the loop halted and never advanced into it -- and then
    described as ``STALLED``: "left the measure exactly where it was ... it rephrased",
    printed directly beneath its own line reading ``ranks [0, 0, 0] =/=> [5]``. The
    decision was sound; the diagnosis was computed from slot-name set differences, and a
    name is silent about a rank. Same disease as everywhere else in this repository -- a
    check derived from something other than its own subject -- landing in the diagnostics
    rather than the gate, which is why every termination test passed straight over it.
    """

    START = Spec("s", (Slot("a", "<x>"), Slot("b", "<x>"), Slot("c", "<x>")))

    @staticmethod
    def _raise_c_in_place(spec, holes):
        """Answer two questions honestly, hand the third back declared more abstract."""
        spec = spec.bind("a", "0").bind("b", "0")
        return Spec(spec.name, tuple(
            Slot("c", "<x>", rank=5) if s.name == "c" else s for s in spec.slots))

    def test_the_round_is_still_refused(self):
        """The gate was never the broken part; pin that before touching the report."""
        session = shepherd(self.START, self._raise_c_in_place)
        assert not session
        assert len(session.rounds) == 1, "it halted immediately, it did not advance"
        assert session.rounds[-1].before_ordinal == (0, 0, 0)
        assert session.rounds[-1].after_ordinal == (5,)
        assert session.rounds[-1].descended is False

    def test_and_it_is_not_reported_as_a_rephrase(self):
        session = shepherd(self.START, self._raise_c_in_place)
        assert session.outcome == WIDENED, "the measure rose; only the names stayed put"
        text = session.explain()
        assert "rephrased" not in text, "the count fell 3 -> 1 and the measure went UP"
        assert "raised the measure without opening any new slot" in text
        assert "[0, 0, 0] became [5]" in text, "the report quotes the deciding numbers"

    def test_the_count_and_the_measure_disagree_here_which_is_the_whole_point(self):
        """``reduced`` is True and ``descended`` is False on the very same round."""
        session = shepherd(self.START, self._raise_c_in_place)
        only = session.rounds[-1]
        assert only.before == 3 and only.after == 1
        assert only.reduced is True, "section VI.3's literal rule accepts this round"
        assert only.descended is False, "and the well-founded measure refuses it"

    def test_a_rank_raised_with_nothing_else_touched_is_also_a_widening(self):
        """
        A second route to the same claim, by a different responder shape, because the
        mutation probe measured the first one as the ONLY test standing between this
        module and the defect. One assertion guarding a finding is how the last one got
        through: nothing is bound here, so the count does not move either.
        """
        def only_raise_a(spec, holes):
            return Spec(spec.name, tuple(
                Slot("a", "<x>", rank=2) if s.name == "a" else s for s in spec.slots))

        session = shepherd(self.START, only_raise_a)
        assert session.outcome == WIDENED
        assert session.opened == (), "no new name appeared, and the measure moved anyway"
        assert session.rounds[-1].before == session.rounds[-1].after == 3
        assert session.rounds[-1].after_ordinal == (2, 0, 0)

    def test_a_genuine_rephrase_is_still_stalled(self):
        """The other side of the discriminant: nothing moves, nothing new appears."""
        def reword(spec, holes):
            return Spec(spec.name, tuple(
                Slot(s.name, s.written + " (restated)", rank=s.rank) for s in spec.slots))

        session = shepherd(self.START, reword)
        assert session.outcome == STALLED
        assert session.rounds[-1].before_ordinal == session.rounds[-1].after_ordinal
        assert "rephrased" in session.explain()


class TestTheLoopMeasuresOnlyWhatItWrote:
    """
    A responder returns a ``Spec`` or the loop stops, because every verdict it issues is
    ``Spec``'s own measure quoted back at the caller.

    Found adversarially. ``shepherd`` called ``.ordinal()``/``.measure()`` on whatever came
    back, so an object merely supplying those names could drive the loop anywhere -- and
    the worst destination is not a wrong answer, it is a ``LedgerContradiction`` reading
    "the descent check is not enforcing what it claims" raised about machinery that was
    never exercised. A module that a caller's return type can make accuse its own theorem
    is not enforcing that theorem.
    """

    class _Liar:
        """Quacks like a Spec and claims to descend forever."""

        class _BelowEverything(tuple):
            def __lt__(self, other):
                return True

            def __gt__(self, other):
                return False

        def __init__(self, spec):
            self._spec = spec

        def measure(self):
            return 1

        def ordinal(self):
            return self._BelowEverything()

        def holes(self):
            return self._spec.holes()

        def subject_to(self):
            return ()

    FLAT = Spec("flat", (Slot("x", "<x>"),))

    def test_an_impostor_is_refused_by_type(self):
        with pytest.raises(TypeError, match="not a Spec"):
            shepherd(self.FLAT, lambda spec, holes: self._Liar(spec))

    def test_the_refusal_names_why_duck_typing_is_not_enough_here(self):
        with pytest.raises(TypeError, match="a rule it never exercised"):
            shepherd(self.FLAT, lambda spec, holes: self._Liar(spec))

    def test_the_impostor_really_would_have_been_believed(self):
        """
        Not a hypothetical: the object's comparison is checked to be the lie it claims.
        Without the type guard this returns True against every ordinal forever, so the
        descent test passes on every round and only the round budget ends the session.
        """
        liar = self._Liar(self.FLAT)
        assert liar.ordinal() < (0,)
        assert liar.ordinal() < liar.ordinal(), "it even claims to descend below itself"
        assert liar.measure() != 0, "and it never reports itself closed"


class TestOneInvariantNeedsBothDoors:
    """
    ``widen`` has refused a duplicate slot name since it was written. The constructor did
    not, and an invariant enforced at one entrance is not an invariant.
    """

    def test_widen_refuses_a_clash(self):
        with pytest.raises(KeyError):
            Spec("s", (Slot("x", "<a>"),)).widen(Slot("x", "<b>"))

    def test_and_now_so_does_direct_construction(self):
        with pytest.raises(KeyError, match="more than once"):
            Spec("s", (Slot("x", "<a>"), Slot("x", "<b>")))

    def test_what_the_open_door_let_through(self):
        """
        The damage, demonstrated through the same deliberate bypass used above.

        A duplicate name is counted twice by every measure, and ``bind`` -- whose filter is
        ``s.name == name`` rather than "the first match" -- binds BOTH in one call. The
        effect on the ordinal is monotone, so it could never break termination, which is
        precisely why no test about termination could see it.
        """
        pair = (Slot("x", "<a>", rank=2), Slot("x", "<b>", rank=2))
        smuggled = Spec.__new__(Spec)
        object.__setattr__(smuggled, "name", "dup")
        object.__setattr__(smuggled, "slots", pair)

        assert smuggled.measure() == 2, "one question, counted as two"
        assert smuggled.ordinal() == (2, 2)
        with pytest.raises(KeyError):
            smuggled.bind("x", "value")   # the guard catches it on the way out, too


class TestTheBoundIsAConditionalOnceRanksExist:
    """
    What the repair cost, kept as a distinction rather than absorbed into a number.

    Cardinality was doing two jobs -- the termination argument and an a-priori round count
    -- and only the first survives unconditionally. Reporting an exhausted resource budget
    as a ``LedgerContradiction`` would be claiming a theorem this module does not have.
    """

    #: One rank-2 hole. Hand-computed: ``round_bound(2) == 3**2 == 9``.
    DEEP = Spec("deep", (Slot("top", "<abstract>", rank=2),))

    def test_the_bound_is_hand_computable_and_is_not_the_hole_count(self):
        assert self.DEEP.measure() == 1
        assert self.DEEP.round_bound(fan_out=2) == 9
        assert self.DEEP.round_bound(fan_out=1) == 4

    def test_a_ranked_spec_says_its_bound_is_conditional(self):
        assert self.DEEP.bound_is_theorem() is False
        assert SECTION_I.bound_is_theorem() is True

    def test_outrunning_a_conditional_bound_is_exhaustion_not_contradiction(self):
        """
        Five sub-questions per hole against a budget computed for two. Every round here
        descends honestly; the loop simply runs out of the allowance that assumption
        bought. That is not a rule being broken and it is not reported as one.
        """
        session = shepherd(self.DEEP, _fan_five)
        assert session.outcome == EXHAUSTED
        assert not session
        assert len(session.rounds) == 9, "it ran the whole budget before stopping"
        assert all(r.descended for r in session.rounds), "and every round was legitimate"

    def test_the_explanation_calls_it_a_resource_limit_and_names_the_assumption(self):
        session = shepherd(self.DEEP, _fan_five)
        text = session.explain()
        assert "resource limit reached, not a rule broken" in text
        assert "declared assumption" in text


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
