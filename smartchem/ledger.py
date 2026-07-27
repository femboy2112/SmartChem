"""
The free-parameter ledger, and a termination rule with teeth.

THE ASK, AND THE GATE IT WAS WAITING ON
---------------------------------------
``THE_COMPILER.md`` section VII lists this brick last and gates it: "only after a real
spec has more than one hole." That gate is now met twice over. Section I's own worked
example is a two-hole spec as written -- both particles say ``position: constrain`` and
neither says *to what* -- and Brick 2's :func:`~smartchem.diagnosis.diagnose` returns more
than one obstruction on a real reaction. The gate was never arbitrary: on a one-hole spec
"strictly reduced" and "finished" are the same event, so the rule below has no teeth and
testing it proves nothing.

Section VI.3 states the rule this module exists to enforce:

    every round must strictly reduce the number of unbound free parameters, or the
    compiler halts and says which parameter it cannot reduce.

THE ONE DESIGN DECISION EVERYTHING ELSE HANGS OFF
--------------------------------------------------
**The measure is re-derived from the spec every round. Nothing decrements a counter, and
the responder's own account of what it accomplished is never read.**

This is not fastidiousness, it is the repository's most expensive lesson applied before
the fact. Three defects here in two days shared one shape: a check whose input was derived
from the thing it checked -- emptiness read off a rendering, a witness gated on the verdict
it audited, a substring assertion vacuous against the exact case it existed for. A
termination rule is the perfect host for a fourth. Write ``remaining -= len(bound)`` and
"strictly reduced" becomes a tautology that no responder can fail, so the loop would
certify progress it never made and halt on nothing. :meth:`Spec.measure` therefore counts
``binding is None`` over the slots of the object actually returned, every single time.

WHAT IT MAY OFFER, AND WHAT IT MAY ONLY ASK
--------------------------------------------
Section IX: generous in interrogation, strict in assertion. A question is falsifiable by
the person answering it, so the compiler may invent questions freely. A *menu* of
admissible bindings is an assertion about the world and must be derived or absent. Here
that is enforced by the type rather than by discipline: a :class:`Slot` carrying options
and no ``derivation`` raises :class:`UnderivedMenu` at construction. :func:`reaction_slot`
is the worked case -- its options are Brick 0's ``equations()``, verbatim, which is
section I's "there are exactly X admissible relations" made literal.

WHAT IT REFUSES TO CERTIFY
--------------------------
Section VI.2: *coherent* is available and *meaningful* is not, permanently. Nothing this
module emits says a compiled spec is true, right, or worth running. Section VI.1: a spec
that closes only subject to an a-posteriori condition is a different object from one that
closes outright, so it gets a different outcome token, and :data:`COMPILED_SUBJECT_TO` is
never collapsed into :data:`COMPILED`.

WHERE CARDINALITY BIT SOMETHING IT SHOULD NOT, AND WHAT REPLACED IT
--------------------------------------------------------------------
The first build of this module implemented section VI.3 with the literal count, and its
failure was the interesting part: the rule halts on a round that *widens* the spec -- a
binding that resolves one hole and opens two beneath it, which is ordinary refinement and
exactly what section IX's shepherding loop does when it supplies vocabulary. The rule was
written against rounds that *rephrase*; a cardinality measure cannot tell those from
rounds that *deepen*, because both fail "strictly reduce".

**The measure is now the multiset of the holes' ranks, ordered by the Dershowitz--Manna
multiset extension of the natural numbers.** A :class:`Slot` carries a ``rank``: how
abstract the question is, and therefore how far it may still be decomposed. The measure of
a spec is :meth:`Spec.ordinal`, and a round is allowed to continue exactly when that
measure strictly descends. Binding a hole removes an element and descends. Replacing one
hole of rank *r* by any finite number of holes of rank *< r* also descends -- **the count
goes up and the measure goes down, which is the whole repair.** Rephrasing leaves the
multiset alone and descends nowhere.

Two things make this the right object rather than a heuristic that happens to work:

* **It is well-founded, so termination is a theorem and not a hope.** The multiset
  extension of a well-founded order is well-founded, and the ranks are naturals. Equivalent
  reading: the measure is the ordinal ``sum of omega**rank`` below ``omega**omega``, and
  :meth:`Spec.ordinal` returns its Cantor normal form.
* **The implementation is Python's own tuple comparison, and the sort is load-bearing.**
  Lexicographic order on arbitrary tuples of naturals is NOT well-founded --
  ``(1,) > (0,1) > (0,0,1) > ...`` descends forever. On tuples sorted DESCENDING it is
  exactly the multiset order and it is well-founded. Dropping ``reverse=True`` leaves every
  test about binding and rephrasing passing while admitting a responder that runs the loop
  forever, so two tests exist for that one token: one naming the responder
  (``test_the_sort_is_the_termination_argument``) and one deciding the claimed identity by
  exhaustive search against the textbook definition
  (``TestTheOrderIsTheOneItClaimsToBe``). Both are needed, and measuring that was itself
  informative -- see ``experiments/ledger_mutation_probe.py``.

Consequently :data:`WIDENED` now means something sharper than "the count went up": *this
round opened holes that are not strictly simpler than what it closed*. A spec whose slots
declare no ranks is entirely rank 0, no widening can descend, and the behaviour is
bit-for-bit the old cardinality rule -- so nothing that worked before changed meaning.

WHAT THE REPAIR COST, STATED RATHER THAN ABSORBED
---------------------------------------------------
Cardinality was doing two jobs at once and they are separable: it was the termination
argument AND an a-priori bound on the number of rounds. The well-founded measure keeps the
first and gives up the second, because a rule that permits unbounded fan-out on a deepening
permits unboundedly many rounds -- that is a theorem about descending sequences below
``omega**omega``, not a gap in this implementation.

So the round bound is now conditional on a *declared* fan-out (:meth:`Spec.round_bound`),
and the two cases are kept apart because they are different claims. With every rank 0 the
bound is unconditional and exceeding it is still a :class:`LedgerContradiction`, exactly as
before. With ranks declared the bound holds only if the responder respects the declared
fan-out, and exceeding it is :data:`EXHAUSTED` -- a resource limit reached, not a lie
detected. Calling the second one a contradiction would be claiming a theorem this module
does not have.

AND THE BOUNDARY, BECAUSE IT IS EASY TO OVERREAD
--------------------------------------------------
The rank order certifies **termination**. It does not certify that a newly opened slot is
genuinely a sub-question of the one it replaced -- no parentage is recorded and none is
checked, so a responder may close a rank-3 hole and open two rank-2 holes about something
else entirely and the loop will accept it. Semantic descent is not a property anything here
can decide. What is decided is that the dialogue ends.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace

from .category import Molecule
from .contracts import (
    DerivationRef,
    InferenceKind,
    ValidityObligation,
    canonical_digest,
)
from .stoichiometry import stoichiometry_menu

__all__ = [
    "COMPILED",
    "COMPILED_SUBJECT_TO",
    "EXHAUSTED",
    "STALLED",
    "WIDENED",
    "DEFAULT_FAN_OUT",
    "IllFoundedRank",
    "LedgerContradiction",
    "Round",
    "Session",
    "BindingSchema",
    "TypedBinding",
    "DerivedOption",
    "Slot",
    "Spec",
    "UnderivedMenu",
    "reaction_slot",
    "shepherd",
]

#: The fan-out the round bound is computed against: how many sub-questions one hole may
#: open. Two is the smallest number for which "deepening" is a real branching rather than a
#: rename, and it is a **declared assumption about the responder, not a measurement of
#: it** -- nothing here can observe a responder's fan-out before running it. It is a
#: parameter because it is not derivable; see :meth:`Spec.round_bound`.
DEFAULT_FAN_OUT = 2

#: Every free parameter is bound, and every binding was checkable before running anything.
COMPILED = "COMPILED"
#: Every free parameter is bound, but at least one binding is only checkable *after* the
#: calculation it governs. Section VI.1: not the same object as :data:`COMPILED`.
COMPILED_SUBJECT_TO = "COMPILED_SUBJECT_TO"
#: A round left the measure exactly where it was and opened no new slot -- it rephrased.
#: Both halves are checked against the thing they name: the measure half comes from the
#: ordinal the gate itself used, never from the slot names, so a round that keeps every
#: name while raising a rank is emphatically NOT this.
STALLED = "STALLED"
#: A round did not descend and the measure did not stay put either -- it opened holes that
#: are not strictly simpler than what it closed, or raised the rank of a hole it left open.
#: Under the old cardinality rule this token meant "the count went up", which also caught
#: legitimate deepening; it no longer does.
WIDENED = "WIDENED"
#: Every round descended legitimately and the declared round budget ran out first. Not a
#: stall (progress was real) and not a contradiction (no theorem was violated) -- the
#: bound was conditional on :data:`DEFAULT_FAN_OUT` and the responder outran it.
EXHAUSTED = "EXHAUSTED"


class IllFoundedRank(ValueError):
    """
    Raised when a slot is given a negative rank.

    The termination argument is that the ranks are drawn from a **well-founded** order, and
    the integers are not one: ``0 > -1 > -2 > ...`` descends forever, so a single negative
    rank would let a responder deepen without end while every round honestly reported a
    strictly descending measure. This is the well-foundedness hypothesis enforced at the
    constructor rather than assumed in a docstring -- the same move as
    :class:`UnderivedMenu`, protecting a theorem instead of a policy.
    """


class UnderivedMenu(ValueError):
    """
    Raised when a slot is handed options without saying what derived them.

    Section III as a constructor check. The compiler may invent a *question* and may not
    invent an *answer*, and the difference is cheap to enforce here and expensive to
    enforce by review.
    """


class LedgerContradiction(AssertionError):
    """
    Raised when the loop outlives its own termination argument.

    Strict decrease bounds the round count by the initial measure. If that bound is ever
    exceeded the invariant is broken somewhere above, and continuing would mean trusting a
    loop that has already demonstrated it is not the loop described here. Sibling of
    ``MenuContradiction`` and ``DomainContradiction``.
    """


@dataclass(frozen=True)
class BindingSchema:
    """The runtime type and local predicate required by a typed slot.

    ``validator_id`` is retained with the schema so a plan can later name the check it used.
    The callable is deliberately local to the ledger transition: executable plans retain only
    the stable obligation identity, never a process-local callable.
    """
    accepted_types: tuple[type, ...]
    validator_id: str = ""
    validator: Callable[[object], bool] | None = field(
        default=None, compare=False, repr=False
    )

    def __post_init__(self) -> None:
        if (not isinstance(self.accepted_types, tuple) or not self.accepted_types
                or any(not isinstance(kind, type) for kind in self.accepted_types)):
            raise TypeError("accepted_types must be a non-empty tuple of types")
        if not isinstance(self.validator_id, str):
            raise TypeError("validator_id must be a string")
        if self.validator is not None and not callable(self.validator):
            raise TypeError("validator must be callable or None")
        if self.validator is not None and not self.validator_id:
            raise ValueError("a validator must carry a non-empty validator_id")
        if self.validator is None and self.validator_id:
            raise ValueError("validator_id names no validator")

    def validate(self, value: object) -> None:
        """Raise rather than silently accepting a value outside this physical schema."""
        if not isinstance(value, self.accepted_types):
            names = ", ".join(kind.__name__ for kind in self.accepted_types)
            raise TypeError(
                f"expected a value of type {names}, got {type(value).__name__}"
            )
        if self.validator is not None:
            passed = self.validator(value)
            if type(passed) is not bool:
                raise TypeError(
                    f"validator {self.validator_id!r} returned "
                    f"{type(passed).__name__}, not bool"
                )
            if not passed:
                raise ValueError(
                    f"value does not satisfy validator {self.validator_id!r}"
                )


@dataclass(frozen=True)
class TypedBinding:
    """A checked semantic value plus the source text and inference that licensed it."""
    value: object
    source_text: str
    inference: InferenceKind
    derivation: DerivationRef | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_text, str) or not self.source_text:
            raise ValueError("source_text must be a non-empty string")
        if not isinstance(self.inference, InferenceKind):
            raise TypeError("inference must be an InferenceKind")
        if self.derivation is not None and not isinstance(self.derivation, DerivationRef):
            raise TypeError("derivation must be a DerivationRef or None")
        if (self.inference in (InferenceKind.DERIVED_COMPLETE,
                               InferenceKind.WRITTEN_CHECKED)
                and self.derivation is None):
            raise ValueError(
                f"{self.inference.value} bindings require a machine derivation reference"
            )


@dataclass(frozen=True)
class DerivedOption:
    """One displayable derived option and the machine reference that produced it."""
    display: str
    value: object
    derivation: DerivationRef

    def __post_init__(self) -> None:
        if not isinstance(self.display, str) or not self.display:
            raise ValueError("display must be a non-empty string")
        if not isinstance(self.derivation, DerivationRef):
            raise TypeError("derivation must be a DerivationRef")


@dataclass(frozen=True)
class Slot:
    """
    One named parameter of a spec, bound or not, with what the scientist actually wrote.

    ``written`` is preserved verbatim and never normalised, because section IX's whole
    posture is handing back something sharper that the scientist still recognises as their
    own idea -- which is impossible if the first thing the compiler does is discard their
    words.

    ``menu`` is the admissible bindings and ``derivation`` says what computed them. An
    empty menu is honest and common: it means nothing in this package could derive the
    options, so the slot is interrogated with an open question instead of a list.

    ``rank`` is how abstract the question is, and therefore how far it may still be
    decomposed: a slot of rank *r* may be closed and replaced by sub-slots of rank *< r*,
    and that counts as progress. **Rank 0 is the default and means atomic** -- a question
    that must be answered rather than unfolded. A spec that declares no ranks is entirely
    rank 0, no decomposition can descend, and :func:`shepherd` behaves exactly as the
    original cardinality rule did. Rank is the scientist's or the responder's declaration
    about the shape of their own question; the loop never invents one, and the ordering is
    what stops a declaration from being self-serving (see :meth:`Spec.ordinal`).
    """
    name: str
    written: str
    binding: str | None = None
    #: Deprecated compatibility marker for old text-only callers.  New slots declare
    #: explicit ``ValidityObligation`` records in ``obligations`` instead.
    checkable_after: bool = False
    menu: tuple[str, ...] = ()
    derivation: str = ""
    rank: int = 0
    #: ``None`` preserves the original text-only slot behaviour.  A schema makes a slot
    #: physical: only :meth:`bind_typed` may close it.
    schema: BindingSchema | None = None
    typed_binding: TypedBinding | None = None
    derived_options: tuple[DerivedOption, ...] = ()
    obligations: tuple[ValidityObligation, ...] = ()

    def __post_init__(self) -> None:
        # Checked BEFORE the sign test, because the sign test is what a float defeats:
        # ``nan < 0`` is False and ``inf < 0`` is False, so a bare ``rank < 0`` waves
        # through the two values that break the order outright. The annotation ``int`` is
        # a hint and hints are not enforcement -- the well-foundedness hypothesis has to be
        # checked by something that runs.
        if not isinstance(self.rank, int):
            raise IllFoundedRank(
                f"slot {self.name!r} has rank {self.rank!r} of type "
                f"{type(self.rank).__name__}; ranks index a well-founded order and only "
                f"the naturals are offered as one here. Floats defeat the sign test twice "
                f"over: inf makes the round budget infinite, so the loop's only backstop "
                f"against a runaway responder can never fire, and nan is not comparable "
                f"even to itself, so the ranks stop being an order -- with the further "
                f"charm that whether a descent is seen at all then depends on whether two "
                f"slots happen to share one nan object")
        if self.rank < 0:
            raise IllFoundedRank(
                f"slot {self.name!r} has rank {self.rank}; ranks index a well-founded "
                f"order and the negative integers are not one. A negative rank admits an "
                f"infinite descent, so a responder could deepen forever while every round "
                f"truthfully reported a strictly descending measure")
        if self.menu and not self.derivation:
            raise UnderivedMenu(
                f"slot {self.name!r} carries {len(self.menu)} options with no derivation; "
                f"a menu is an assertion about the world and section III forbids offering "
                f"one that was not derived. State what computed these, or drop them and "
                f"ask an open question instead")
        if self.schema is not None and not isinstance(self.schema, BindingSchema):
            raise TypeError("schema must be a BindingSchema or None")
        if self.typed_binding is not None:
            if not isinstance(self.typed_binding, TypedBinding):
                raise TypeError("typed_binding must be a TypedBinding or None")
            if self.schema is None:
                raise ValueError("a typed binding requires a BindingSchema")
            self.schema.validate(self.typed_binding.value)
            if self.binding is not None and self.binding != self.typed_binding.source_text:
                raise ValueError("binding text must match typed_binding.source_text")
            if self.binding is None:
                object.__setattr__(self, "binding", self.typed_binding.source_text)
        elif self.schema is not None and self.binding is not None:
            raise TypeError(
                "a schema slot cannot close through legacy text; use bind_typed()"
            )
        if not isinstance(self.derived_options, tuple) or any(
            not isinstance(option, DerivedOption) for option in self.derived_options
        ):
            raise TypeError("derived_options must be a tuple of DerivedOption values")
        if self.derived_options:
            displayed = tuple(option.display for option in self.derived_options)
            if self.menu and self.menu != displayed:
                raise ValueError("menu must exactly match derived_options displays")
            if not self.menu:
                object.__setattr__(self, "menu", displayed)
        if not isinstance(self.obligations, tuple) or any(
            not isinstance(obligation, ValidityObligation) for obligation in self.obligations
        ):
            raise TypeError("obligations must be a tuple of ValidityObligation values")

    @property
    def is_bound(self) -> bool:
        """Re-read from both binding representations; nothing caches this."""
        return self.binding is not None or self.typed_binding is not None

    def bind_typed(
        self,
        value: object,
        *,
        source_text: str,
        inference: InferenceKind,
        derivation: DerivationRef | None = None,
    ) -> "Slot":
        """Close a physical slot through its schema, never through a placeholder string."""
        if self.schema is None:
            raise TypeError(f"slot {self.name!r} has no BindingSchema")
        typed = TypedBinding(value, source_text, inference, derivation)
        self.schema.validate(typed.value)
        return replace(self, binding=typed.source_text, typed_binding=typed)

    def question(self) -> str:
        """
        What to ask about this slot. Always answerable, menu or no menu.

        A slot with no derivable options still gets a question, because refusing to ask is
        how section IX's courtier failure arrives from the other direction -- silence reads
        as "nothing can be done here" when the truth is "this package cannot enumerate it".
        """
        if self.binding is not None:
            return f"{self.name}: bound to {self.binding!r}"
        if self.menu:
            return (f"{self.name}: you wrote {self.written!r}. Under the declared rules "
                    f"there are exactly {len(self.menu)} admissible bindings. "
                    f"Choose one, or write one and it will be checked against the same "
                    f"rules: " + "; ".join(self.menu))
        if self.derivation:
            # An empty menu WITH a derivation is a derived answer of zero, which is the
            # opposite claim from having no way to look. Collapsing the two would tell a
            # scientist their vocabulary was missing when what they were actually handed
            # was a refusal by theorem -- and would send them off to find better words for
            # a question that has been answered. Brick 0's REFUSE verdict lands here.
            return (f"{self.name}: you wrote {self.written!r}. Under the declared rules "
                    f"there are exactly ZERO admissible bindings -- enumerated, not "
                    f"unavailable. Derived from: {self.derivation}")
        return (f"{self.name}: you wrote {self.written!r}, which does not yet name a "
                f"binding. Nothing held here can enumerate the admissible options -- that "
                f"is a statement about the available language, not about the idea.")


@dataclass(frozen=True)
class Spec:
    """
    An underdetermined specification: named slots, some bound, some not.

    Frozen, and every operation returns a new value. The loop compares two *objects*
    rather than reading a running total, and it can only do that if a round cannot mutate
    the spec it was handed.
    """
    name: str
    slots: tuple[Slot, ...]

    def __post_init__(self) -> None:
        """
        Reject duplicate slot names, which :meth:`widen` already refuses at its own door.

        An invariant enforced at one entrance and not the other is not an invariant. Built
        directly, ``Spec("s", (Slot("x", ...), Slot("x", ...)))`` double-counts in
        :meth:`holes`, :meth:`measure` and :meth:`ordinal`, and :meth:`bind` -- whose filter
        is ``s.name == name`` rather than "the first match" -- binds BOTH in one call. The
        double-count is monotone and so cannot break termination, which is exactly why it
        would have survived every test about termination.
        """
        names = [s.name for s in self.slots]
        # Set membership first, and the O(n^2) roster only on the way to raising. Every
        # bind() and widen() rebuilds the Spec, so this runs once per round; counting each
        # name against the whole list would make a loop over a spec with n slots quadratic
        # in n for no answer it does not already have. Identity-preserving, not a tradeoff.
        if len(names) == len(set(names)):
            return
        clash = sorted({name for name in names if names.count(name) > 1})
        if clash:
            raise KeyError(f"{self.name} declares slot name(s) {clash} more than once; "
                           f"a name is how bind() and the round report identify a slot, so "
                           f"two slots sharing one are bound together and counted twice")

    def holes(self) -> tuple[Slot, ...]:
        """
        The unbound slots, RE-DERIVED from the slot values on every call.

        The measure of section VI.3 is ``len`` of this. It is deliberately a scan and not
        a field: a stored count is a number the loop would have to be told, and being told
        is precisely what this rule cannot afford.
        """
        return tuple(slot for slot in self.slots if not slot.is_bound)

    def measure(self) -> int:
        """
        The number of unbound free parameters. Recomputed, never remembered.

        This is section VI.3's literal count. It is still reported on every round, because
        it is what a reader wants to know, but it is no longer what the loop decides on --
        :meth:`ordinal` is. Keeping both visible is the point: the rounds where the two
        disagree are exactly the deepening rounds, and printing them side by side is how
        the repair stays legible rather than becoming folklore.
        """
        return len(self.holes())

    def ordinal(self) -> tuple[int, ...]:
        """
        The well-founded measure: the holes' ranks as a DESCENDING-sorted tuple.

        Compared with ordinary tuple ordering, this is the Dershowitz--Manna multiset
        extension of ``<`` on the naturals, and equivalently the ordinal
        ``sum of omega**rank`` written in Cantor normal form. Both readings say the same
        thing about what a round is allowed to do:

        * bind a hole                       -- an element leaves          -> descends
        * close rank *r*, open ranks *< r*  -- one element becomes many smaller ones,
          any finite number of them         -> descends, though the COUNT rises
        * rephrase                          -- the multiset is unchanged  -> does not
        * open a hole of rank >= everything it closed                     -> does not

        **The descending sort is the termination argument, not presentation.** Lex order on
        arbitrary tuples of naturals is not well-founded -- ``(1,) > (0,1) > (0,0,1) > ...``
        goes on forever -- and that infinite descent is realisable here: it is a responder
        that closes its rank-1 hole and opens a rank-0 and a rank-1 hole every round. Sorted
        descending, that round reads ``(1,) -> (1,0)``, which is an increase and halts.
        Unsorted it reads ``(1,) -> (0,1)``, which looks like a descent and never stops.

        It follows that the largest rank present can never increase across a round the loop
        accepts, since a bigger leading element makes the tuple lexicographically larger.
        A spec that starts entirely rank 0 therefore stays entirely rank 0, which is what
        makes its round bound unconditional in :meth:`round_bound`.
        """
        return tuple(sorted((slot.rank for slot in self.holes()), reverse=True))

    def round_bound(self, fan_out: int = DEFAULT_FAN_OUT) -> int:
        """
        How many rounds the loop can run, if every deepening fans out at most ``fan_out``.

        ``sum((fan_out+1)**rank)`` over the holes. It strictly decreases by at least one on
        every legal round: binding a rank-*r* hole drops it by ``(fan_out+1)**r``, and
        replacing that hole with ``m <= fan_out`` holes of rank ``<= r-1`` drops it by at
        least ``(fan_out+1)**r - fan_out*(fan_out+1)**(r-1) = (fan_out+1)**(r-1) >= 1``.

        **Whether this is a theorem depends on the spec**, and :meth:`bound_is_theorem`
        answers that rather than leaving a caller to assume. With every rank 0 it reduces
        to :meth:`measure` and holds unconditionally, because no descent can add a hole at
        all. With ranks declared it holds only while the responder honours ``fan_out``,
        which nothing here can check in advance -- so overrunning it reports
        :data:`EXHAUSTED` and not a contradiction.

        **It is exponential in the rank, so it is a termination argument and not a
        practical guard, and those are different jobs.** A responder that repeatedly splits
        the highest hole into ``fan_out`` holes one rank down is entirely legal and never
        threatens this budget -- it walks a binary tree of ``2**(rank+1) - 1`` nodes against
        a bound of ``3**rank`` -- and simply takes as long as that is. MEASURED at
        ``fan_out=2`` from a single ``Slot(rank=K)``, by
        ``experiments/ledger_rank_blowup.py``::

            K= 5   rounds     63   bound    243
            K=10   rounds   2047   bound  59049     1.35 s
            K=12   rounds   8191   bound 531441    43.84 s

        Wall time grows ~7x per unit of K while the round count only doubles, because
        :meth:`bind` and :meth:`widen` each rebuild the whole slot tuple, so the cost is
        quadratic in the slots alive. (Timings taken while another job held the box; they
        are an order of magnitude, not a benchmark. The round counts are exact and load-
        independent.) Nothing is broken -- descending sequences below ``omega**omega`` can
        be as long as they like, which is the price of admitting deepening at all -- but a
        caller who reads ``round_bound`` as "this will stop soon" has read it wrong. It
        says the loop stops. It says nothing whatever about when.
        """
        return sum((fan_out + 1) ** slot.rank for slot in self.holes())

    def bound_is_theorem(self) -> bool:
        """True when :meth:`round_bound` needs no assumption about the responder."""
        return all(slot.rank == 0 for slot in self.holes())

    def subject_to(self) -> tuple[Slot, ...]:
        """Bound slots carrying legacy or typed post-run validity obligations."""
        return tuple(
            slot for slot in self.slots
            if slot.is_bound and (
                slot.checkable_after
                or any(obligation.required and obligation.stage.value == "POST"
                       for obligation in slot.obligations)
            )
        )

    def bind(self, name: str, value: str) -> "Spec":
        """Legacy text binding for untyped slots; schema slots must use :meth:`bind_typed`."""
        found = next((slot for slot in self.slots if slot.name == name), None)
        if found is None:
            raise KeyError(f"{self.name} has no slot named {name!r}")
        if found.schema is not None:
            raise TypeError(
                f"slot {name!r} is physical and cannot close through legacy text; "
                "use bind_typed()"
            )
        return replace(self, slots=tuple(
            replace(s, binding=value) if s.name == name else s for s in self.slots))

    def bind_typed(
        self,
        name: str,
        value: object,
        *,
        source_text: str,
        inference: InferenceKind,
        derivation: DerivationRef | None = None,
    ) -> "Spec":
        """Bind one schema slot through a checked semantic value and inference record."""
        found = next((slot for slot in self.slots if slot.name == name), None)
        if found is None:
            raise KeyError(f"{self.name} has no slot named {name!r}")
        bound = found.bind_typed(
            value,
            source_text=source_text,
            inference=inference,
            derivation=derivation,
        )
        return replace(self, slots=tuple(
            bound if slot.name == name else slot for slot in self.slots
        ))

    def widen(self, *slots: Slot) -> "Spec":
        """A new spec with further slots appended -- the sub-holes a binding opened."""
        existing = {s.name for s in self.slots}
        clash = [s.name for s in slots if s.name in existing]
        if clash:
            raise KeyError(f"{self.name} already has slot(s) {clash}")
        return replace(self, slots=self.slots + slots)

    def explain(self) -> str:
        lines = [f"spec {self.name}: {len(self.slots)} slots, "
                 f"{self.measure()} unbound"]
        for slot in self.slots:
            mark = "  " if slot.is_bound else "??"
            after = "  [a posteriori]" if slot in self.subject_to() else ""
            lines.append(f" {mark} {slot.name:<28} {slot.written!r} -> "
                         f"{slot.binding!r}{after}")
        return "\n".join(lines)


@dataclass(frozen=True)
class Round:
    """
    One interrogation round, with both measures taken from real spec objects.

    ``before``/``after`` are :meth:`Spec.measure` and ``before_ordinal``/``after_ordinal``
    are :meth:`Spec.ordinal`, all four taken from real spec objects going in and coming
    out. None of them is supplied by the responder.

    Both measures are carried because the interesting rounds are the ones where they
    disagree: a deepening has ``reduced`` false and ``descended`` true, and that pair is
    the whole content of the repair to section VI.3.
    """
    index: int
    asked: tuple[str, ...]
    before: int
    after: int
    before_ordinal: tuple[int, ...]
    after_ordinal: tuple[int, ...]
    spec: Spec

    @property
    def reduced(self) -> bool:
        """Section VI.3's literal rule: did the COUNT of free parameters fall?"""
        return self.after < self.before

    @property
    def descended(self) -> bool:
        """The rule the loop actually applies: did the well-founded measure fall?"""
        return self.after_ordinal < self.before_ordinal

    def __repr__(self) -> str:
        arrow = "->" if self.descended else "=/=>"
        note = ""
        if self.descended and not self.reduced:
            note = "  [deepened: more holes, simpler ones]"
        return (f"round {self.index}: asked {list(self.asked)} "
                f"{self.before} {arrow} {self.after} holes, "
                f"ranks {list(self.before_ordinal)} {arrow} "
                f"{list(self.after_ordinal)}{note}")


@dataclass(frozen=True)
class Session:
    """
    The whole interrogation: how it ended, where it got to, and what it cost.

    Truthy when the spec closed, by either compiling outcome. The two are kept apart in
    ``outcome`` because section VI.1 says they are different objects; ``bool`` answers
    "did this close", ``outcome`` answers "closed how", and no caller should have to infer
    the second from the first.
    """
    outcome: str
    spec: Spec
    rounds: tuple[Round, ...]
    stuck_on: tuple[str, ...]
    opened: tuple[str, ...]
    discarded: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.outcome not in (
            COMPILED,
            COMPILED_SUBJECT_TO,
            EXHAUSTED,
            STALLED,
            WIDENED,
        ):
            raise ValueError(f"unknown shepherd outcome {self.outcome!r}")
        if not isinstance(self.spec, Spec):
            raise TypeError("spec must be a Spec")
        for name in ("rounds", "stuck_on", "opened", "discarded"):
            if not isinstance(getattr(self, name), tuple):
                raise TypeError(f"{name} must be a tuple")
        if self.outcome == COMPILED:
            if self.spec.measure() != 0 or self.spec.subject_to():
                raise ValueError(
                    "COMPILED requires a closed spec with no post-run obligations"
                )
        elif self.outcome == COMPILED_SUBJECT_TO:
            if self.spec.measure() != 0 or not self.spec.subject_to():
                raise ValueError(
                    "COMPILED_SUBJECT_TO requires a closed spec with post-run obligations"
                )
        elif self.spec.measure() == 0:
            raise ValueError(f"{self.outcome} cannot describe a closed spec")

    def __bool__(self) -> bool:
        return self.outcome in (COMPILED, COMPILED_SUBJECT_TO)

    def explain(self) -> str:
        lines = [f"{self.outcome}  ({len(self.rounds)} rounds, "
                 f"{self.spec.measure()} free parameters left)"]
        lines.extend(repr(r) for r in self.rounds)
        if self.outcome == STALLED:
            lines.append("halted: a round left the measure exactly where it was and opened "
                         "nothing -- it rephrased. Cannot reduce: "
                         + ", ".join(self.stuck_on))
        if self.outcome == WIDENED and self.opened:
            lines.append("halted: a round opened free parameters ("
                         + ", ".join(self.opened) + ") that are not strictly simpler than "
                         "what it closed, so the measure did not descend. Deepening is "
                         "allowed and is not this: a slot opened beneath a rank-r hole "
                         "must declare a rank below r. Everything here is rank 0 unless "
                         "someone said otherwise, and nothing sits below rank 0.")
        if self.outcome == WIDENED and not self.opened:
            # No new NAME appeared and the measure still rose, so the widening happened
            # inside a slot the loop had already seen. Reported separately because the
            # name-set is silent about it, and a report that says "it rephrased" while its
            # own ranks line shows an increase is worse than no report.
            last = self.rounds[-1]
            lines.append("halted: a round raised the measure without opening any new slot "
                         f"-- ranks {list(last.before_ordinal)} became "
                         f"{list(last.after_ordinal)}. An existing hole came back declared "
                         "MORE abstract than it went out, which refuses to descend exactly "
                         "as opening one would, while wearing a name the loop had already "
                         "seen. Cannot reduce: " + ", ".join(self.stuck_on))
        if self.outcome == EXHAUSTED:
            lines.append("halted: every round descended, and the round budget ran out "
                         "first. The budget assumes each hole opens at most "
                         f"{DEFAULT_FAN_OUT} sub-questions, which is a declared assumption "
                         "about the responder and not a measurement of one -- so this is a "
                         "resource limit reached, not a rule broken. Still open: "
                         + ", ".join(self.stuck_on))
        if self.outcome == COMPILED_SUBJECT_TO:
            post_checks = []
            for slot in self.spec.subject_to():
                if slot.checkable_after:
                    post_checks.append(slot.name)
                post_checks.extend(
                    f"{slot.name}: {obligation.name}"
                    for obligation in slot.obligations
                    if obligation.required and obligation.stage.value == "POST"
                )
            lines.append("every free parameter is bound, but the following are checkable "
                         "only AFTER the calculation they govern, so this spec has not "
                         "compiled outright: "
                         + ", ".join(post_checks))
        if self:
            # Section X, and it is not optional. A shepherd that reports only successes
            # flatters; the casualty list is what makes a successful refinement legible
            # as a refinement rather than as a vindication of what came in.
            lines.append("discarded on the way: " + (", ".join(self.discarded)
                                                     if self.discarded else
                                                     "nothing was recorded as discarded"))
            lines.append("coherent under the declared rules. Whether it is worth running "
                         "is not a property this can certify.")
        return "\n".join(lines)


def reaction_slot(name: str, written: str, species: tuple[Molecule, ...]) -> Slot:
    """
    A slot asking which balanced reaction relates ``species``, carrying Brick 0's menu.

    This is section I's paragraph made literal -- "under this system's declared rules there
    are exactly X admissible relations ... here they are" -- with X and the list both
    coming from :func:`~smartchem.stoichiometry.stoichiometry_menu` rather than from
    anything invented here. The derivation string names the source and the verdict so a
    reader can tell an enumerated menu from a forced one.
    """
    menu = stoichiometry_menu(species)
    source_digest = canonical_digest((menu.species, menu.row_labels, menu.matrix))
    derived_options = tuple(
        DerivedOption(
            display=completion.equation(menu.species),
            value=completion.reaction,
            derivation=DerivationRef(
                kind=InferenceKind.DERIVED_COMPLETE,
                source="smartchem.stoichiometry.stoichiometry_menu",
                source_digest=source_digest,
                scope=(f"completion {index} of rank {menu.rank} / "
                       f"freedom {menu.freedom}"),
            ),
        )
        for index, completion in enumerate(menu.completions)
    )
    return Slot(
        name=name,
        written=written,
        menu=menu.equations(),
        derivation=(f"stoichiometry_menu over {len(species)} species: "
                    f"rank {menu.rank}, freedom {menu.freedom}, verdict {menu.verdict}"),
        derived_options=derived_options,
    )


def shepherd(spec: Spec, respond, *, discarded: tuple[str, ...] = (),
             fan_out: int = DEFAULT_FAN_OUT) -> Session:
    """
    Interrogate ``spec`` until it closes or the termination rule stops it.

    ``respond(spec, holes)`` is the scientist: it receives the current spec and its unbound
    slots and returns a NEW spec. It is not asked what it changed and it is not believed if
    it says -- everything the loop knows about a round comes from calling
    :meth:`Spec.ordinal` and :meth:`Spec.measure` on the object it got back.

    A round continues exactly when the ordinal strictly descends. That is what admits
    deepening (one hole out, several simpler ones in) while still refusing a rephrase, and
    it terminates because the multiset order over the naturals is well-founded.

    ``fan_out`` sizes the round budget only; it does not gate a round. A responder that
    opens more sub-questions than this is not doing anything illegal -- the ordinal still
    decides -- it has merely outrun the budget derived from the assumption, which is why
    that case is :data:`EXHAUSTED`. When the spec declares no ranks the budget needs no
    assumption at all (:meth:`Spec.bound_is_theorem`) and overrunning it is impossible, so
    it stays a :class:`LedgerContradiction`: a claim this module really can make.
    """
    budget = spec.round_bound(fan_out)
    budget_is_theorem = spec.bound_is_theorem()
    rounds: list[Round] = []
    current = spec

    while True:
        before = current.measure()
        before_ordinal = current.ordinal()
        if before == 0:
            outcome = COMPILED_SUBJECT_TO if current.subject_to() else COMPILED
            return Session(outcome, current, tuple(rounds), (), (), discarded)

        if len(rounds) >= budget:
            still = tuple(h.name for h in current.holes())
            if budget_is_theorem:
                raise LedgerContradiction(
                    f"{len(rounds)} rounds against an unconditional bound of {budget}; "
                    f"every rank here is 0, so no round can add a hole and strict descent "
                    f"cannot run longer than that. The descent check is not enforcing "
                    f"what it claims")
            # Ranks are declared, so the bound was only ever conditional on the fan-out.
            # Calling this a contradiction would be asserting a theorem this module does
            # not have -- the responder outran an assumption, it did not break a rule.
            return Session(EXHAUSTED, current, tuple(rounds), still, (), discarded)

        holes = current.holes()
        asked = tuple(h.name for h in holes)
        before_names = {h.name for h in holes}

        following = respond(current, holes)
        if not isinstance(following, Spec):
            # Everything below is a claim about the multiset order, and it is only a claim
            # about the multiset order if the object being measured is the one whose
            # ordinal() this module wrote. Duck-typing here does not merely risk a wrong
            # answer, it risks a LedgerContradiction -- a message asserting that "the
            # descent check is not enforcing what it claims" -- raised because a supplied
            # object lied about its own measure. The loop must not be able to blame its own
            # theorem for a caller's return type.
            raise TypeError(
                f"respond returned {type(following).__name__}, not a Spec. Every outcome "
                f"this loop reports is derived from Spec.ordinal() and Spec.measure(); an "
                f"object that merely supplies those names can drive the loop to any "
                f"conclusion, including a contradiction against a rule it never exercised")
        # Taken ONCE and reused, so the number recorded on the round is provably the number
        # the decision below was made on. Two calls could not disagree today -- Spec is
        # frozen -- but a report that is re-derived separately from the decision it reports
        # is the shape of defect this module was built to avoid.
        after_ordinal = following.ordinal()
        rounds.append(Round(len(rounds) + 1, asked, before, following.measure(),
                            before_ordinal, after_ordinal, following))

        if after_ordinal < before_ordinal:
            current = following
            continue

        # Did not descend. Which of the two failures was it?
        #
        # The names are REPORTED here; they are not what decides. Reading the verdict off a
        # name-set difference is how a round that raised an existing hole's rank -- from
        # (0,0,0) to (5), a strict increase -- got reported as "left the measure exactly
        # where it was ... it rephrased", with the contradicting ranks printed two lines
        # above in the same report. Same name, so no name opened; the measure moved anyway.
        # The discriminant has to be the quantity the gate above actually used, or the
        # diagnosis is derived from something other than its own subject.
        opened = tuple(h.name for h in following.holes() if h.name not in before_names)
        still = tuple(name for name in asked
                      if any(h.name == name for h in following.holes()))
        if opened or after_ordinal > before_ordinal:
            return Session(WIDENED, following, tuple(rounds), still, opened, discarded)
        return Session(STALLED, following, tuple(rounds), still, (), discarded)
