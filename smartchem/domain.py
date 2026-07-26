"""
What an oracle DECLARES it can price -- answerable without calling it.

Every refusal in this package is currently an inline ``return None`` buried inside the
method that would have computed the answer. That is sound and it is the whole point of the
project, but it makes coverage undiscoverable: the only way to learn that an oracle will
never price your species is to ask it and get nothing back, once per species, forever. A
misconfigured oracle is indistinguishable from a hard problem.

A :class:`Domain` is that boundary lifted out and made a value. It answers "would you even
try?" from the request alone, and it composes -- which is the property ``THE_COMPILER.md``
section VII actually requires of this brick, because two oracles in two verticals can only
be combined over the species both of them cover.

THE CONTRACT, AND IT POINTS ONE WAY ONLY
----------------------------------------
This is the load-bearing sentence in the module and it is deliberately weak::

    not domain.admits(m)   IMPLIES   oracle.energy(m) is None

Declared-outside means certainly refused. The converse is **not** claimed and must never be
read into it: a species the domain admits may still come back ``None``. A domain therefore
OVER-approximates coverage, and that direction is the safe one -- a loose domain wastes a
call, while a tight one would promise an answer that never arrives.

Two separate things break the converse, and collapsing them into one "sometimes it fails
anyway" would hide the fixable case behind the unfixable one:

``runtime_refusals``
    Not knowable without attempting the computation. An SCF that does not converge is the
    canonical member. No declared domain can ever pre-announce these, in this design or any
    other, and the honest move is to name them rather than imply they do not exist.

``unexpressed_refusals``
    Fully determined by the request, but outside what this constraint language can say. The
    PySCF oracle's tabulated-geometry lookup is keyed by molecular FORMULA, and this domain
    speaks in element sets and atom counts, so it cannot express "H2 yes, HeH no". These are
    a limitation of the vocabulary and could be removed by extending it.

``is_exact`` is true only when both are empty, and only then does ``admits`` mean "will
answer". Nothing in this repository currently has an exact domain, and the property exists
so that fact is reported rather than assumed.

THE CONSTRAINT LANGUAGE, AND WHY IT IS THIS SMALL
-------------------------------------------------
Four independent axes -- atom count, element set, charge, internal state -- chosen because
each one is forced by a decline site that already exists in a shipped oracle, not because
they seemed like a complete ontology. Independence is what buys decidable emptiness: a
domain is empty exactly when one axis is empty on its own, so the first cross-vertical
refusal is a computation rather than an opinion.

That decision is checked rather than trusted. :meth:`Domain.witness` constructs a real
``Molecule`` inside the domain by an independent route -- picking a value on each axis and
building the object -- and :class:`DomainContradiction` fires if the algebra and the
construction ever disagree about emptiness. Same discipline as ``stoichiometry.py``: a
second derivation over different machinery, and a raise rather than a quiet preference.

WHAT THE FIRST TWO DOMAINS TURNED OUT TO SAY
--------------------------------------------
Both results were measured by writing this down, and neither was visible before:

* ``PySCFOracle`` prices **no polyatomic species in any configuration.** Raising
  ``max_atoms`` past 2 does not open the polyatomic path, it opens a path whose own
  finiteness gate then closes it, because ``_RELAXED_GEOMETRY_MAE`` is the empty dict.
  The declared domain says ``atoms <= 2`` for every setting, which is a fact previously
  obtainable only by calling the oracle and getting ``None``.
* ``PySCFOracle.domain & PhotonOracle.domain`` is **empty**. One needs at least one atom;
  the other admits only species with none. So there is no species both can price -- and
  therefore no shared reference for aligning their two arbitrary zeros. That is a real
  obstruction to a cross-vertical reaction energy, stated by construction instead of
  discovered per-attempt, and it is the diagnosis Brick 2 needs.

WHAT THIS DOES NOT ESTABLISH
----------------------------
That a domain is TIGHT. Soundness is one-directional by design, so a domain admitting a
species proves nothing about whether an answer exists. Tightness would need the converse,
and the converse is false for good reasons named above.

It also does not establish that the four axes suffice for a future oracle. They suffice for
the three that exist. An oracle refusing on, say, molecular symmetry would have to widen
the language or declare the refusal ``unexpressed`` -- and declaring it is the supported
outcome, not a failure.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from .category import Bond, Molecule

__all__ = [
    "Domain",
    "DomainContradiction",
    "EVERYTHING",
    "NOTHING",
]


class DomainContradiction(AssertionError):
    """
    The emptiness algebra and an explicit witness construction disagreed.

    Raised, never swallowed. :attr:`Domain.is_empty` reasons over the constraint axes;
    :meth:`Domain.witness` builds an actual ``Molecule`` and asks :meth:`Domain.admits`.
    Those are separate code paths over separate representations, and if they disagree one
    of them is wrong. A caller is entitled to find out which rather than receive a
    confidently wrong answer about whether a cross-vertical composition is possible.
    """


@dataclass(frozen=True)
class Domain:
    """
    A declared, introspectable set of species an oracle is willing to attempt.

    ``None`` on an axis means UNRESTRICTED, which is not the same as the empty set: an
    ``elements`` of ``None`` admits every element, while ``frozenset()`` admits none. That
    distinction is why the axes are optional rather than defaulting to empty containers.
    """

    #: Human-readable provenance -- normally the oracle's ``name``. Intersections join them.
    label: str
    #: Fewest atoms the oracle will attempt. ``1`` excludes a photon; ``0`` permits one.
    min_atoms: int = 0
    #: Most atoms it will attempt, or ``None`` for unbounded.
    max_atoms: int | None = None
    #: Permitted element symbols, or ``None`` for any.
    elements: frozenset[str] | None = None
    #: Permitted net charges, or ``None`` for any.
    charges: frozenset[int] | None = None
    #: Permitted internal-state labels, or ``None`` for any. ``frozenset({""})`` is
    #: "ground state only", which is what every matter oracle here declares.
    states: frozenset[str] | None = None
    #: Refusals that cannot be known without attempting the computation.
    runtime_refusals: tuple[str, ...] = ()
    #: Refusals determined by the request but inexpressible in these four axes.
    unexpressed_refusals: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label:
            raise ValueError("a domain must carry a non-empty label")
        if type(self.min_atoms) is not int or self.min_atoms < 0:
            raise ValueError("min_atoms must be a non-negative integer")
        if self.max_atoms is not None and (
            type(self.max_atoms) is not int or self.max_atoms < 0
        ):
            raise ValueError("max_atoms must be a non-negative integer or None")
        for name in ("elements", "charges", "states"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, frozenset):
                object.__setattr__(self, name, frozenset(value))
        for name in ("runtime_refusals", "unexpressed_refusals"):
            value = getattr(self, name)
            if isinstance(value, str) or not isinstance(value, (tuple, list)):
                raise TypeError(f"{name} must be a tuple of reason strings")
            object.__setattr__(self, name, tuple(value))

    # -- the question the whole brick exists to answer --------------------------------
    def refusals(self, molecule: Molecule) -> tuple[str, ...]:
        """
        Every declared constraint this species fails, not merely the first.

        Enumerating all of them is the point. An inline ``return None`` chain reports the
        earliest failure and hides the rest, so a caller who fixes it learns about the next
        one only on the next call. A species outside the domain on three axes should be
        told three things.
        """
        reasons: list[str] = []
        count = len(molecule.atoms)
        if count < self.min_atoms:
            reasons.append(
                f"{count} atoms, and {self.label} requires at least {self.min_atoms}"
            )
        if self.max_atoms is not None and count > self.max_atoms:
            reasons.append(
                f"{count} atoms, and {self.label} attempts at most {self.max_atoms}"
            )
        if self.elements is not None:
            outside = sorted(set(molecule.atoms) - self.elements)
            if outside:
                reasons.append(
                    f"{self.label} declares no coverage for {', '.join(outside)}"
                )
        if self.charges is not None and molecule.charge not in self.charges:
            reasons.append(
                f"net charge {molecule.charge:+d}, and {self.label} covers "
                f"{sorted(self.charges)}"
            )
        if self.states is not None and molecule.state not in self.states:
            shown = sorted(self.states) or ["(nothing)"]
            reasons.append(
                f"internal state {molecule.state!r}, and {self.label} covers "
                f"{[s or '(ground)' for s in shown]}"
            )
        return tuple(reasons)

    def admits(self, molecule: Molecule) -> bool:
        """
        True when every declared constraint passes.

        Read this as "not ruled out", never as "will answer" -- see the module docstring's
        contract. ``admits`` is a necessary condition for an answer and nothing more.
        """
        return not self.refusals(molecule)

    # -- composition ------------------------------------------------------------------
    def __and__(self, other: "Domain") -> "Domain":
        """
        The species BOTH oracles are willing to attempt.

        This is the operation section VII names, and it is what makes a cross-vertical
        combination checkable: two oracles can share a reaction only over the intersection
        of their domains, and their zeros can be aligned only over a species inside it.

        **THAT LAST CLAUSE IS NECESSARY AND NOT SUFFICIENT, and it used to be written as
        though it were both.** A shared species is a shared TOKEN, not a shared REFERENCE.
        Measured: ``PhotonOracle(589) & PhotonOracle(532)`` is non-empty and even
        ``is_exact``, its sole witness is the bare quantum, and the two oracles price that
        witness **0.225535 eV apart**. So a non-empty intersection licenses the offset to be
        MEASURED and never licenses it to be assumed. ``diagnosis._compare_zeros`` does the
        measuring and reports ``DISAGREED_OFFSET`` when it comes back non-zero; a caller who
        read this docstring as a sufficient condition and skipped that step would be off by
        exactly that much, silently.

        Caveats union rather than intersect. If either side may refuse at runtime, so may
        the pair -- a combination is no more predictable than its least predictable half.

        **The meet is a value, so it is commutative and idempotent AS ONE.** Both used to
        fail: caveats came out in argument order, so ``a & b != b & a`` with identical
        admitted species and identical caveat SETS, and ``d & d`` grew a doubled label. A
        frozen dataclass carries ``__eq__`` and ``__hash__``, so a value that compares
        unequal to its own mirror is a value lying about itself, and it would have lied the
        moment anyone put a domain in a set. Neither had a caller yet; both are fixed here
        rather than left as a trap with a note on it.
        """
        if not isinstance(other, Domain):
            return NotImplemented
        return Domain(
            # Canonical, so the label cannot be the one field that breaks the identities
            # below. A set collapses the self-meet, sorting drops the argument order.
            # Associativity of the LABEL is not claimed and does not hold -- "(a & b) & c"
            # and "a & (b & c)" sort differently -- while every constraint field does
            # associate, because max, min, set-meet and set-union all do. Stated rather
            # than quietly assumed, since the boundary is exactly the sort of thing that
            # gets read as covered.
            label=" & ".join(sorted({self.label, other.label})),
            min_atoms=max(self.min_atoms, other.min_atoms),
            max_atoms=_min_bound(self.max_atoms, other.max_atoms),
            elements=_meet(self.elements, other.elements),
            charges=_meet(self.charges, other.charges),
            states=_meet(self.states, other.states),
            runtime_refusals=_union(self.runtime_refusals, other.runtime_refusals),
            unexpressed_refusals=_union(
                self.unexpressed_refusals, other.unexpressed_refusals
            ),
        )

    def relabelled(self, label: str) -> "Domain":
        """The same constraints under a different name."""
        return replace(self, label=label)

    # -- self-knowledge ---------------------------------------------------------------
    @property
    def is_empty(self) -> bool:
        """
        True when no species at all satisfies these constraints.

        Decidable because the axes are independent: a product of sets is empty exactly when
        one factor is. The one coupling worth spelling out is that an empty ``elements``
        set is only fatal when at least one atom is required -- a species with no atoms
        needs no element, which is precisely how this package spells a photon.

        Checked against :meth:`witness` rather than trusted; see :class:`DomainContradiction`.

        AND IT NOW ACTUALLY IS. This property used to return ``_empty_by_algebra()``
        directly while the sentence above claimed otherwise, and nothing else in the package
        called :meth:`witness`, so the cross-check the docstring advertised ran for no
        caller. It answers with the *agreed* verdict of two derivations or it raises.
        """
        return self.witness() is None

    def _empty_by_algebra(self) -> bool:
        if self.max_atoms is not None and self.min_atoms > self.max_atoms:
            return True
        if self.charges is not None and not self.charges:
            return True
        if self.states is not None and not self.states:
            return True
        if self.elements is not None and not self.elements and self.min_atoms >= 1:
            return True
        return False

    def witness(self) -> Molecule | None:
        """
        A real ``Molecule`` inside this domain, or ``None`` if there is none.

        The independent derivation. Where :attr:`is_empty` reasons about the constraint
        sets, this one picks a concrete value on every axis, builds the object through the
        ordinary ``Molecule`` constructor -- connectivity validation and all -- and confirms
        by calling :meth:`admits`. Disagreement raises rather than resolves.

        Deliberately not cached: it is a proof obligation, not a hot path.

        THE CONSTRUCTION IS NOT GATED ON THE ALGEBRA, AND THAT IS THE WHOLE POINT. It used
        to read ``built = None if empty else self._construct_witness()``, which makes the
        "independent" derivation a function of the thing it audits: the two can then only
        disagree when the algebra says NON-empty and construction fails, and that is the
        harmless direction -- it costs a caller one wasted call. The direction that matters
        is the other one, algebra says EMPTY while a species exists, because that is what
        turns "these two oracles cannot both price anything, so no reaction spans them"
        into a confident false obstruction. Gated, that direction was unreachable by
        construction: a mutant asserting emptiness for a domain admitting water passed the
        entire suite, and this method agreed with it.

        Build first, compare second. Same lesson as the sublattice defect in
        ``stoichiometry.py`` -- a check derived from its own subject checks nothing.
        """
        empty = self._empty_by_algebra()
        built = self._construct_witness()
        if built is not None and not self.admits(built):
            raise DomainContradiction(
                f"{self.label}: constructed {built!r} as a witness, but admits() rejects "
                f"it for {self.refusals(built)}"
            )
        if empty != (built is None):
            raise DomainContradiction(
                f"{self.label}: is_empty is {empty} but witness construction "
                f"{'succeeded' if built is not None else 'failed'}"
            )
        return built

    def _construct_witness(self) -> Molecule | None:
        """
        Build the cheapest species satisfying every axis, or ``None`` if there is none.

        Every axis that cannot be satisfied returns ``None`` rather than being CLAMPED into
        range. The atom count used to be ``min(min_atoms, max_atoms)``, which quietly
        produced a candidate below the floor it was supposed to respect -- so an
        impossible domain handed back a real ``Molecule`` that :meth:`admits` then rejected,
        and the caller saw a contradiction where the honest answer was "no witness". Now
        that :meth:`witness` runs this unconditionally, that distinction is load bearing:
        every ``None`` here must mean "no such species", never "I gave up part way".
        """
        count = self.min_atoms
        if self.max_atoms is not None and count > self.max_atoms:
            return None
        try:
            symbol = "H" if self.elements is None else (sorted(self.elements) or [None])[0]
            if count >= 1 and symbol is None:
                return None
            if self.charges is not None and not self.charges:
                return None
            charge = (0 if self.charges is None or 0 in self.charges
                      else sorted(self.charges)[0])
            if self.states is not None and not self.states:
                return None
            state = ("" if self.states is None or "" in self.states
                     else sorted(self.states)[0])
        except TypeError:
            # A declared set whose members are not orderable (mixed types, None) cannot be
            # searched for a witness. That is "no witness I can build", not a crash.
            return None
        atoms = tuple([symbol] * count) if count else ()
        # A Molecule with more than one atom must be connected; a chain is the cheapest
        # graph that satisfies that for any count.
        bonds = frozenset(Bond(i, i + 1) for i in range(count - 1))
        try:
            return Molecule(atoms, bonds, charge, state)
        except (TypeError, ValueError):
            return None

    @property
    def is_exact(self) -> bool:
        """
        True when ``admits`` is equivalent to "will return a value".

        False for everything in this repository today, and the attribute exists so that is
        stated rather than assumed. Both caveat lists must be empty for the biconditional
        to hold; either one alone breaks it.
        """
        return not self.runtime_refusals and not self.unexpressed_refusals

    def explain(self) -> str:
        """A human-readable statement of the boundary, caveats included."""
        lines = [f"domain: {self.label}"]
        if self.is_empty:
            lines.append("  EMPTY -- this configuration can price no species at all")
        upper = "unbounded" if self.max_atoms is None else str(self.max_atoms)
        lines.append(f"  atoms       : {self.min_atoms} to {upper}")
        lines.append(
            "  elements    : any"
            if self.elements is None
            else f"  elements    : {len(self.elements)} declared"
            f" ({', '.join(sorted(self.elements)[:12])}"
            f"{', ...' if len(self.elements) > 12 else ''})"
        )
        lines.append(
            "  charge      : any"
            if self.charges is None
            else f"  charge      : {sorted(self.charges)}"
        )
        lines.append(
            "  state       : any"
            if self.states is None
            else "  state       : "
            + ", ".join(s or "(ground)" for s in sorted(self.states))
        )
        if self.is_exact:
            lines.append("  EXACT -- admitted species are answered")
        else:
            lines.append(
                "  NOT EXACT -- admission is necessary, not sufficient. It may still "
                "decline:"
            )
            for reason in self.runtime_refusals:
                lines.append(f"    [runtime]     {reason}")
            for reason in self.unexpressed_refusals:
                lines.append(f"    [unexpressed] {reason}")
        return "\n".join(lines)


def _min_bound(left: int | None, right: int | None) -> int | None:
    """Least upper bound, treating ``None`` as unbounded."""
    if left is None:
        return right
    if right is None:
        return left
    return min(left, right)


def _meet(left: frozenset | None, right: frozenset | None) -> frozenset | None:
    """Set intersection, treating ``None`` as the universe."""
    if left is None:
        return right
    if right is None:
        return left
    return left & right


def _union(left: tuple[str, ...], right: tuple[str, ...]) -> tuple[str, ...]:
    """
    Canonical union of caveat strings.

    Sorted rather than argument-ordered, and that is the whole point: caveats are a SET,
    and preserving ``left + right`` order made ``Domain.__and__`` non-commutative as a
    value -- same admitted species, same caveats, different tuple, different hash. Reading
    order was never worth a value that disagrees with its own mirror.
    """
    return tuple(sorted(set(left) | set(right)))


#: Claims nothing. The correct default for an oracle that has not declared a domain:
#: soundness ("outside implies refused") holds vacuously when nothing is outside.
EVERYTHING = Domain(label="unrestricted")

#: Admits no species. What a misconfigured oracle declares.
NOTHING = Domain(label="empty", min_atoms=1, max_atoms=0)
