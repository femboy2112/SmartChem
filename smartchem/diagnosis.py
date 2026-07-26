"""
Why a reaction cannot be priced -- as a value, not as a ``None``.

THE ASK, AND WHERE IT COMES FROM
--------------------------------
``THE_COMPILER.md`` section VII names this brick exactly: "turn ``base.py``'s worked
example from a boolean decline into a diagnosis." The worked example is
``Na(excited) -> Na + photon``, and the boolean is ``carries_unmodelled_physics``, which
answers ``True`` and throws away *which* of the two reasons in its own docstring applied.
Downstream, ``thermo.reaction_energy`` answers ``None``, which is honest and mute.

``None`` is the right answer to "what is this worth". It is a useless answer to "what
would have to change". This module answers the second question and does not touch the
first: nothing here alters what any oracle returns, so the ``Estimate | None`` contract,
its 52 test assertions and its 17 internal call sites are exactly as they were. A
diagnosis is a separate channel, which is also why it can take a SET of oracles --
``reaction_energy`` takes one, and a reaction spanning two verticals has nowhere to put
the second.

WHAT IT IS ALLOWED TO SAY, AND WHAT IT IS NOT
---------------------------------------------
Every obstruction below is derived from something already computed by Brick 0
(``stoichiometry.py``) or Brick 1 (``domain.py``). Nothing here invents a reason. That is
the section III derived-menu law applied to refusals rather than to completions: a
plausible wrong explanation of a decline is worse than a bare decline, because the bare
decline at least does not send anyone off to fix the wrong thing.

The obstructions are split by ``removable``, and the split is the point. A caller who
cannot tell "nobody has entered a number in this table yet" from "these two energy scales
have no measurable relationship" cannot tell an afternoon's work from a research problem.

THE ONE CLAIM THAT HAD TO BE WEAKENED BEFORE IT WAS TRUE
--------------------------------------------------------
Brick 1 measured that ``PySCFOracle.domain & PhotonOracle.domain`` is empty and it was
tempting to read that as "so their two arbitrary zeros cannot be aligned, therefore no
cross-vertical reaction energy". That is stronger than the evidence. In
``Na(*) -> Na + photon`` both sodium terms are priced by the SAME oracle, so its zero
cancels between them and the photon's energy is absolute; the zeros are reconcilable *for
this reaction*. What an empty intersection actually establishes is narrower and still
sharp: **the offset between two oracles' zeros cannot be MEASURED, because there is no
species both will price.** That is a statement about verifiability, it is what the code
below reports, and it names its own remedy -- one shared species.

And a non-empty intersection does not settle it either, which is why
:func:`diagnose` measures rather than assumes. ``PhotonOracle(589) &
PhotonOracle(532)`` is non-empty and even ``is_exact``; its sole witness is the bare
quantum; and the two oracles price that witness 0.2255 eV apart. A shared *token* is not
a shared *reference*.
"""
from __future__ import annotations

from dataclasses import dataclass

from .category import Molecule, Reaction
from .oracle.base import domain_of
from .stoichiometry import stoichiometry_menu

__all__ = ["Diagnosis", "Obstruction", "diagnose"]


#: Nothing supplied will attempt this species at all.
UNPRICED = "UNPRICED"
#: The reaction needs more than one oracle, and the offset between two of the zeros
#: involved cannot be measured because no species lies in both domains.
UNMEASURABLE_OFFSET = "UNMEASURABLE_OFFSET"
#: Two oracles share a species and disagree about its energy, so the shared token does not
#: establish a shared reference.
DISAGREED_OFFSET = "DISAGREED_OFFSET"
#: The two domains intersect, but neither oracle actually priced the shared witness --
#: the declared domain over-approximates, which it is allowed to do.
UNCONFIRMED_OFFSET = "UNCONFIRMED_OFFSET"
#: The declared conservation invariants cannot see, or cannot distinguish, a species here.
INVARIANT_BLIND = "INVARIANT_BLIND"


@dataclass(frozen=True)
class Obstruction:
    """
    One reason the reaction cannot be priced, with its provenance and its remedy class.

    ``removable`` is the field worth reading first. True means the obstruction is a limit
    of what has been declared or tabulated -- more coverage, another oracle, another
    invariant -- and False means it is a limit of the relationship between the things
    involved, which no amount of data entry fixes.
    """
    kind: str
    subject: str
    detail: str
    removable: bool

    def __repr__(self) -> str:
        mark = "removable" if self.removable else "STRUCTURAL"
        return f"[{self.kind} / {mark}] {self.subject}: {self.detail}"


@dataclass(frozen=True)
class Diagnosis:
    """
    The obstructions between a reaction and a number, or none if there are none.

    Truthy when the reaction is priceable by the oracles supplied. That polarity is
    deliberate: ``if not diagnose(...)`` reads as "if there is nothing wrong", and the
    object exists to be inspected when there is.
    """
    species: tuple[Molecule, ...]
    assignment: tuple[tuple[Molecule, tuple[str, ...]], ...]
    obstructions: tuple[Obstruction, ...]
    offset_ev: float | None

    def __bool__(self) -> bool:
        return not self.obstructions

    @property
    def structural(self) -> tuple[Obstruction, ...]:
        return tuple(o for o in self.obstructions if not o.removable)

    @property
    def removable(self) -> tuple[Obstruction, ...]:
        return tuple(o for o in self.obstructions if o.removable)

    def oracles_for(self, molecule: Molecule) -> tuple[str, ...]:
        """Every supplied oracle whose declared domain admits this species."""
        for candidate, names in self.assignment:
            if candidate == molecule:
                return names
        return ()

    def explain(self) -> str:
        lines = ["species        : " + ", ".join(repr(m) for m in self.species)]
        for molecule, names in self.assignment:
            lines.append(f"  {molecule!r:<16} <- " +
                         (", ".join(names) if names else "NOTHING SUPPLIED ADMITS IT"))
        if self.offset_ev is not None:
            lines.append(f"measured offset: {self.offset_ev:+.6f} eV between the two zeros")
        if not self.obstructions:
            lines.append("no obstruction: every species is admitted by something, and any "
                         "zeros that had to be combined were measured to agree")
            return "\n".join(lines)
        for obstruction in self.obstructions:
            lines.append(repr(obstruction))
        lines.append(f"{len(self.removable)} removable, {len(self.structural)} structural")
        return "\n".join(lines)


def _unique(molecules) -> tuple[Molecule, ...]:
    seen: list[Molecule] = []
    for molecule in molecules:
        if molecule not in seen:
            seen.append(molecule)
    return tuple(seen)


def diagnose(reaction: Reaction, oracles) -> Diagnosis:
    """
    Why ``reaction`` cannot be priced by ``oracles``, in terms of what has been declared.

    Runs no chemistry unless it has to. The only call to ``energy`` happens when two
    oracles are genuinely both needed AND their domains overlap, which is the one case
    where the answer cannot be read off the declarations.
    """
    oracles = tuple(oracles)
    species = _unique(tuple(reaction.dom.species) + tuple(reaction.cod.species))
    domains = [(getattr(o, "name", type(o).__name__), o, domain_of(o)) for o in oracles]

    assignment = tuple(
        (m, tuple(name for name, _o, d in domains if d.admits(m))) for m in species
    )
    obstructions: list[Obstruction] = []

    # -- 1. species nothing will even attempt ------------------------------------------
    for molecule, names in assignment:
        if names:
            continue
        reasons = []
        for name, _o, domain in domains:
            reasons.extend(f"{name}: {why}" for why in domain.refusals(molecule))
        obstructions.append(Obstruction(
            kind=UNPRICED,
            subject=repr(molecule),
            detail=("no oracle supplied declares coverage; " + "; ".join(reasons)
                    if reasons else "no oracles were supplied"),
            # A coverage gap is a gap in what was DECLARED, and declarations widen.
            removable=True,
        ))

    # -- 2. does one oracle cover the whole reaction? -----------------------------------
    covering = [name for name, _o, d in domains if all(d.admits(m) for m in species)]
    offset_ev: float | None = None

    if not covering and all(names for _m, names in assignment):
        # Every species is priceable by SOMETHING but by no single thing, so two zeros
        # have to be combined and the offset between them becomes load bearing.
        needed = _pick_cover(species, domains)
        for i in range(len(needed)):
            for j in range(i + 1, len(needed)):
                obstruction, offset = _compare_zeros(needed[i], needed[j])
                if offset is not None:
                    offset_ev = offset
                if obstruction is not None:
                    obstructions.append(obstruction)

    # -- 3. what the declared invariants cannot see -- Brick 0 --------------------------
    try:
        menu = stoichiometry_menu(species)
    except (ValueError, TypeError):
        menu = None
    if menu is not None and menu.unconstrained:
        blind = ", ".join(repr(m) for m in menu.unconstrained)
        obstructions.append(Obstruction(
            kind=INVARIANT_BLIND,
            subject=blind,
            detail=("the declared invariants (atom counts, net charge) cannot see or "
                    "cannot distinguish these, so a balance over them constrains nothing "
                    "about whether this reaction happens or what it costs"),
            # Declaring another invariant is exactly what would remove it.
            removable=True,
        ))

    return Diagnosis(species, assignment, tuple(obstructions), offset_ev)


def _pick_cover(species, domains):
    """The oracles actually carrying species here: for each one, the first that admits it."""
    chosen: list[tuple] = []
    for molecule in species:
        for entry in domains:
            if entry[2].admits(molecule):
                if entry not in chosen:
                    chosen.append(entry)
                break
    return chosen


def _compare_zeros(left, right):
    """
    Can these two oracles' energies be added together, and is that CHECKED or assumed?

    Returns ``(obstruction | None, offset_ev | None)``. The offset is only ever a measured
    number; there is no path here that infers one.
    """
    left_name, left_oracle, left_domain = left
    right_name, right_oracle, right_domain = right
    shared = left_domain & right_domain
    witness = shared.witness()
    if witness is None:
        return Obstruction(
            kind=UNMEASURABLE_OFFSET,
            subject=f"{left_name} + {right_name}",
            detail=("no species lies in both declared domains, so the offset between "
                    "these two zeros cannot be measured -- not that it is known to be "
                    "wrong, that it cannot be checked at all. One species both will "
                    "price would remove this"),
            # Only a new oracle, or a widened one, spans both. No data entry does it.
            removable=False,
        ), None

    left_value = left_oracle.energy(witness)
    right_value = right_oracle.energy(witness)
    if left_value is None or right_value is None:
        declined = left_name if left_value is None else right_name
        return Obstruction(
            kind=UNCONFIRMED_OFFSET,
            subject=f"{left_name} + {right_name}",
            detail=(f"{witness!r} lies in both declared domains but {declined} declined "
                    f"it, so the offset is still unmeasured. A declared domain "
                    f"over-approximates by design, so this is the converse failing, not "
                    f"a broken declaration"),
            removable=True,
        ), None

    offset = left_value.value_ev - right_value.value_ev
    if offset != 0.0:
        return Obstruction(
            kind=DISAGREED_OFFSET,
            subject=f"{left_name} + {right_name}",
            detail=(f"both price {witness!r} and they differ by {offset:+.6f} eV, so the "
                    f"shared species is a shared token and not a shared reference; adding "
                    f"their energies would carry that offset into the answer"),
            removable=True,
        ), offset
    return None, offset
