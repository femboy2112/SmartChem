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

AND WHERE THE RULE AS WRITTEN BITES SOMETHING IT SHOULD NOT
-----------------------------------------------------------
Implemented literally, section VI.3 halts on a round that *widens* the spec -- a binding
that resolves one hole and opens two beneath it, which is ordinary refinement and is
exactly what section IX's shepherding loop does when it supplies vocabulary. The rule was
written against rounds that *rephrase*; it cannot tell those from rounds that *deepen*,
because both fail "strictly reduce".

That is reported, not papered over. :data:`WIDENED` is a distinct outcome from
:data:`STALLED` and carries the slots that opened. Reporting them as one token would hide
the informative case behind the failure case, which is the mistake Brick 1 avoided by
splitting ``runtime_refusals`` from ``unexpressed_refusals``. Section VII says each brick
is chosen so its failure is informative; this is that failure, and it is a fact about
section VI.3's measure rather than about the implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .category import Molecule
from .stoichiometry import stoichiometry_menu

__all__ = [
    "COMPILED",
    "COMPILED_SUBJECT_TO",
    "STALLED",
    "WIDENED",
    "LedgerContradiction",
    "Round",
    "Session",
    "Slot",
    "Spec",
    "UnderivedMenu",
    "reaction_slot",
    "shepherd",
]


#: Every free parameter is bound, and every binding was checkable before running anything.
COMPILED = "COMPILED"
#: Every free parameter is bound, but at least one binding is only checkable *after* the
#: calculation it governs. Section VI.1: not the same object as :data:`COMPILED`.
COMPILED_SUBJECT_TO = "COMPILED_SUBJECT_TO"
#: A round failed to reduce the count and did not widen it either -- it rephrased.
STALLED = "STALLED"
#: A round opened more holes than it closed. Ordinary refinement; halts anyway under the
#: rule as section VI.3 states it, and that is the finding rather than a bug.
WIDENED = "WIDENED"


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
    """
    name: str
    written: str
    binding: str | None = None
    checkable_after: bool = False
    menu: tuple[str, ...] = ()
    derivation: str = ""

    def __post_init__(self) -> None:
        if self.menu and not self.derivation:
            raise UnderivedMenu(
                f"slot {self.name!r} carries {len(self.menu)} options with no derivation; "
                f"a menu is an assertion about the world and section III forbids offering "
                f"one that was not derived. State what computed these, or drop them and "
                f"ask an open question instead")

    @property
    def is_bound(self) -> bool:
        """Re-read from ``binding`` on every access; nothing caches this."""
        return self.binding is not None

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

    def holes(self) -> tuple[Slot, ...]:
        """
        The unbound slots, RE-DERIVED from the slot values on every call.

        The measure of section VI.3 is ``len`` of this. It is deliberately a scan and not
        a field: a stored count is a number the loop would have to be told, and being told
        is precisely what this rule cannot afford.
        """
        return tuple(slot for slot in self.slots if slot.binding is None)

    def measure(self) -> int:
        """The number of unbound free parameters. Recomputed, never remembered."""
        return len(self.holes())

    def subject_to(self) -> tuple[Slot, ...]:
        """Bound slots whose binding can only be checked after the run (section VI.1)."""
        return tuple(s for s in self.slots if s.binding is not None and s.checkable_after)

    def bind(self, name: str, value: str) -> "Spec":
        """A new spec with one slot bound. Raises if the slot is not there to bind."""
        if not any(s.name == name for s in self.slots):
            raise KeyError(f"{self.name} has no slot named {name!r}")
        return replace(self, slots=tuple(
            replace(s, binding=value) if s.name == name else s for s in self.slots))

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
            after = "  [a posteriori]" if slot.checkable_after else ""
            lines.append(f" {mark} {slot.name:<28} {slot.written!r} -> "
                         f"{slot.binding!r}{after}")
        return "\n".join(lines)


@dataclass(frozen=True)
class Round:
    """
    One interrogation round, with both measures taken from real spec objects.

    ``before`` and ``after`` are the results of calling :meth:`Spec.measure` on the spec
    going in and the spec coming out. Neither is supplied by the responder.
    """
    index: int
    asked: tuple[str, ...]
    before: int
    after: int
    spec: Spec

    @property
    def reduced(self) -> bool:
        return self.after < self.before

    def __repr__(self) -> str:
        arrow = "->" if self.reduced else "=/=>"
        return (f"round {self.index}: asked {list(self.asked)} "
                f"{self.before} {arrow} {self.after}")


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

    def __bool__(self) -> bool:
        return self.outcome in (COMPILED, COMPILED_SUBJECT_TO)

    def explain(self) -> str:
        lines = [f"{self.outcome}  ({len(self.rounds)} rounds, "
                 f"{self.spec.measure()} free parameters left)"]
        lines.extend(repr(r) for r in self.rounds)
        if self.outcome == STALLED:
            lines.append("halted: a round did not strictly reduce the free parameters and "
                         "did not open new ones -- it rephrased. Cannot reduce: "
                         + ", ".join(self.stuck_on))
        if self.outcome == WIDENED:
            lines.append("halted: a round opened more free parameters than it closed ("
                         + ", ".join(self.opened) + "). That is ordinary refinement, and "
                         "section VI.3's measure cannot tell it from a rephrase; the rule "
                         "is applied as written and the difference is reported here.")
        if self.outcome == COMPILED_SUBJECT_TO:
            lines.append("every free parameter is bound, but the following are checkable "
                         "only AFTER the calculation they govern, so this spec has not "
                         "compiled outright: "
                         + ", ".join(s.name for s in self.spec.subject_to()))
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
    return Slot(
        name=name,
        written=written,
        menu=menu.equations(),
        derivation=(f"stoichiometry_menu over {len(species)} species: "
                    f"rank {menu.rank}, freedom {menu.freedom}, verdict {menu.verdict}"),
    )


def shepherd(spec: Spec, respond, *, discarded: tuple[str, ...] = ()) -> Session:
    """
    Interrogate ``spec`` until it closes or the termination rule stops it.

    ``respond(spec, holes)`` is the scientist: it receives the current spec and its unbound
    slots and returns a NEW spec. It is not asked what it changed and it is not believed if
    it says -- everything the loop knows about a round comes from calling
    :meth:`Spec.measure` on the object it got back.

    The round count is bounded by the initial measure, because strict decrease over a
    non-negative integer cannot run longer than that. That bound is asserted rather than
    assumed: if it is ever exceeded, the strict-decrease check above it is not doing what
    this docstring says, and :class:`LedgerContradiction` is a better outcome than a
    plausible answer from a loop that has already been shown to be lying.
    """
    ceiling = spec.measure()
    rounds: list[Round] = []
    current = spec

    while True:
        before = current.measure()
        if before == 0:
            outcome = COMPILED_SUBJECT_TO if current.subject_to() else COMPILED
            return Session(outcome, current, tuple(rounds), (), (), discarded)

        if len(rounds) >= ceiling:
            raise LedgerContradiction(
                f"{len(rounds)} rounds against an initial measure of {ceiling}; strict "
                f"decrease makes that impossible, so the reduction check is not enforcing "
                f"what it claims")

        holes = current.holes()
        asked = tuple(h.name for h in holes)
        before_names = {h.name for h in holes}

        following = respond(current, holes)
        after = following.measure()
        rounds.append(Round(len(rounds) + 1, asked, before, after, following))

        if after < before:
            current = following
            continue

        # Did not reduce. Which of the two failures was it? The distinction is read off
        # the slot names, not off anything the responder reported about itself.
        opened = tuple(h.name for h in following.holes() if h.name not in before_names)
        still = tuple(name for name in asked
                      if any(h.name == name for h in following.holes()))
        if opened:
            return Session(WIDENED, following, tuple(rounds), still, opened, discarded)
        return Session(STALLED, following, tuple(rounds), still, (), discarded)
