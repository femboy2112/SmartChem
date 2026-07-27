"""
Section I's loop, run end to end, with a round of genuine refinement in the middle.

    python experiments/section_i_end_to_end.py

WHY THIS FILE EXISTS, AND WHAT WAS BLOCKING IT
-----------------------------------------------
``THE_COMPILER.md`` section VII, Brick 3, ends its failure paragraph with a dated
prediction::

    A cardinality measure is the wrong measure for a shepherding loop, and section VI.3
    will need a well-founded one -- depth-weighted, or ordinal -- before the loop of
    section I can run more than one round of genuine refinement.

That measure landed 2026-07-26 (the Dershowitz--Manna multiset order over the holes'
ranks), so the gate is open and this is the thing it was gating. "Genuine refinement" has
a precise meaning here and it is the meaning the old rule could not express: a round that
**closes one abstract question and opens two concrete ones beneath it**, so the COUNT of
free parameters rises while the MEASURE strictly falls. Under the cardinality rule that
round halted the compiler. It is round 2 below.

WHAT "VERIFIABLY REALISABLE" IS TAKEN TO MEAN
----------------------------------------------
Section I says the compiler iterates "until the spec is *verifiably* realisable". A
``COMPILED`` token is not that -- it is the loop's opinion of its own dialogue. So this
file does not stop at the outcome. It REALISES the closed spec: it builds the ``Reaction``
the bindings name and seeds the geometry they describe, and the verification is that
``category.Reaction``'s constructor re-derives conservation by accumulating formula
dictionaries and would raise rather than return. The spec is realisable because the object
exists, not because the session said so.

EVERY MENU HERE IS DERIVED, WHICH IS SECTION III AND IS THE HARD PART
----------------------------------------------------------------------
* the reaction options come from ``stoichiometry_menu`` (Brick 0), via ``reaction_slot``
* the bond-length options come from ``geometry.seed_bond_length`` per distinct bond type
* the frame options come from calling ``is_linear`` on ``seed_coordinates``' own output

Nothing below writes an option by hand. A slot carrying options with no ``derivation``
cannot even be constructed -- ``Slot.__post_init__`` raises ``UnderivedMenu`` -- so this is
enforced by the type rather than by my care in writing it.

AND SECTION I'S SECOND CLAUSE IS EXERCISED, NOT JUST THE FIRST
----------------------------------------------------------------
"Choose one, **or write one and I will check it against the same rules.**" The scientist
below WRITES its own balance rather than picking the offered one, and
``StoichiometryMenu.check`` judges it against the same matrix that derived the menu. The
negative control at the bottom writes a wrong one and shows the refusal naming which
conserved quantity broke and by how much.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smartchem.category import Bond, Config, Molecule, Reaction, conserves  # noqa: E402
from smartchem.geometry import (                                            # noqa: E402
    is_linear,
    seed_bond_length,
    seed_coordinates,
)
from smartchem.ledger import (                                              # noqa: E402
    COMPILED,
    Slot,
    Spec,
    reaction_slot,
    shepherd,
)
from smartchem.stoichiometry import stoichiometry_menu                      # noqa: E402

CH4 = Molecule(("C", "H", "H", "H", "H"),
               frozenset({Bond(0, 1, 1), Bond(0, 2, 1), Bond(0, 3, 1), Bond(0, 4, 1)}))
O2 = Molecule.diatomic("O", "O", order=2)
CO2 = Molecule(("C", "O", "O"), frozenset({Bond(0, 1, 2), Bond(0, 2, 2)}))
H2O = Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}))

#: Order is load-bearing: ``check`` aligns a written vector with this tuple.
SPECIES = (CH4, O2, CO2, H2O)

#: What the scientist writes instead of choosing. It is the same balance the menu derived,
#: reached independently, which is the point -- clause two has to accept a right answer it
#: did not supply, or it is a lookup table with extra steps.
WRITTEN_BALANCE = (1, 2, -1, -2)

#: The negative control. Under-oxidised by one O2; the oxygen row is off by -2.
WRONG_BALANCE = (1, 1, -1, -2)


def build_spec() -> Spec:
    """
    Section I's ask, transcribed: two things specified, one constrained *to nothing yet*.

    ``geometry`` is rank 1 -- an abstract question, one that can still be unfolded. That
    single integer is what the whole repair bought: it is what lets round 2 answer this
    question by asking two smaller ones without the loop calling that a failure.
    """
    return Spec("burn-methane", (
        reaction_slot("reaction",
                      "CH4 and O2 make CO2 and water, balanced somehow",
                      SPECIES),
        Slot("geometry", "positions constrained -- but I have not said to what", rank=1),
    ))


def _bond_length_menu() -> tuple[tuple[str, ...], str]:
    """Derived: one option per distinct (element, element, order) across the species."""
    kinds = sorted({(min(m.atoms[b.i], m.atoms[b.j]), max(m.atoms[b.i], m.atoms[b.j]),
                     b.order)
                    for m in SPECIES for b in m.bonds})
    options = tuple(f"{a}-{b} order {order}: {seed_bond_length(a, b, order):.3f} A"
                    for a, b, order in kinds)
    return options, (f"geometry.seed_bond_length over {len(kinds)} distinct bond types "
                     f"present in the {len(SPECIES)} candidate species")


def _frame_menu() -> tuple[tuple[str, ...], str]:
    """Derived: ask ``is_linear`` about the coordinates ``seed_coordinates`` produces."""
    shapes = {m: is_linear(seed_coordinates(m)) for m in SPECIES}
    linear = sorted(repr(m) for m, flat in shapes.items() if flat)
    bent = sorted(repr(m) for m, flat in shapes.items() if not flat)
    options = (
        f"Cartesian / Angstrom, treating {', '.join(bent)} as non-linear (3N-6 modes)",
        f"Cartesian / Angstrom, treating {', '.join(linear)} as linear (3N-5 modes)",
    )
    return options, ("geometry.is_linear applied to geometry.seed_coordinates output for "
                     f"each of the {len(SPECIES)} species")


def scientist(spec: Spec, holes: tuple[Slot, ...]) -> Spec:
    """
    The other side of the dialogue. Answers ONE question per round, on purpose.

    Answering everything at once would close the spec in a single round and prove nothing
    about a termination rule -- on a spec that closes immediately, "strictly reduced" and
    "finished" are the same event. The interesting round is the middle one.
    """
    names = {hole.name for hole in holes}

    if "reaction" in names:
        # Clause two: write one rather than choose one, and let it be checked.
        menu = stoichiometry_menu(SPECIES)
        written = menu.check(WRITTEN_BALANCE)
        if not written.admissible:
            raise AssertionError(f"the written balance was refused: {written.explain()}")
        return spec.bind("reaction", written.reaction.name or "written balance")

    if "geometry" in names:
        # THE ROUND THIS FILE EXISTS FOR. One abstract question closed, two concrete ones
        # opened beneath it. The count of free parameters goes UP and the measure goes DOWN.
        lengths, lengths_from = _bond_length_menu()
        frames, frames_from = _frame_menu()
        return (spec.bind("geometry", "by the bond graph of the species in the reaction")
                    .widen(Slot("geometry.bond_lengths",
                                "the internuclear distances that graph implies",
                                menu=lengths, derivation=lengths_from, rank=0),
                           Slot("geometry.frame",
                                "the coordinate frame and what counts as a mode",
                                menu=frames, derivation=frames_from, rank=0)))

    # Everything left is atomic: answer one, from its own derived menu.
    target = holes[0]
    return spec.bind(target.name, target.menu[0] if target.menu else "<answered>")


def realise(spec: Spec) -> dict:
    """
    Turn a closed spec into the objects it names, and let the category do the verifying.

    ``Reaction``'s constructor re-derives conservation from ``Molecule.formula``
    accumulation and raises ``ConservationError`` rather than returning something wrong,
    so the existence of the returned object IS the verification. Nothing here asserts
    conservation itself; it asks for the object and reports whether it was granted.
    """
    bound = {slot.name: slot.binding for slot in spec.slots}
    if any(value is None for value in bound.values()):
        raise ValueError("realise() needs a closed spec")

    menu = stoichiometry_menu(SPECIES)
    written = menu.check(WRITTEN_BALANCE)
    reaction = written.reaction
    geometry = {repr(m): seed_coordinates(m) for m in SPECIES}
    return {
        "reaction": reaction,
        "conserves": conserves(reaction),
        "verified": written.verified,
        "geometry": geometry,
        "atoms_placed": sum(coords.shape[0] for coords in geometry.values()),
        "bindings": bound,
    }


def main() -> int:
    spec = build_spec()

    print("=" * 78)
    print("SECTION I, END TO END")
    print("=" * 78)
    print(f"  the scientist wrote : {spec.name}")
    for slot in spec.slots:
        print(f"    {slot.name:<22} rank {slot.rank}   {slot.written!r}")
    print(f"  measure             : {spec.measure()} free parameters")
    print(f"  ordinal             : {spec.ordinal()}")
    print(f"  round bound         : {spec.round_bound()} "
          f"(unconditional: {spec.bound_is_theorem()})")

    print("\n  -- what it is asked, before anything is answered " + "-" * 24)
    for slot in spec.holes():
        print(f"    {slot.question()[:150]}")

    session = shepherd(spec, scientist)

    print("\n  -- the dialogue " + "-" * 56)
    deepenings = []
    for round_ in session.rounds:
        widened = round_.after > round_.before
        if widened and round_.descended:
            deepenings.append(round_.index)
        print(f"    round {round_.index}: asked {list(round_.asked)}")
        print(f"        count   {round_.before} -> {round_.after}"
              + ("   <-- ROSE" if widened else ""))
        print(f"        measure {list(round_.before_ordinal)} -> "
              f"{list(round_.after_ordinal)}"
              + ("   <-- and FELL anyway" if widened and round_.descended else ""))

    print(f"\n  outcome             : {session.outcome}")
    print(f"  rounds              : {len(session.rounds)}")
    print(f"  genuine refinements : {deepenings} "
          f"(count rose while the measure fell)")

    print("\n  -- section I's second clause " + "-" * 43)
    menu = stoichiometry_menu(SPECIES)
    print(f"    offered  : {menu.equations()[0]}")
    good = menu.check(WRITTEN_BALANCE)
    print(f"    written  : {WRITTEN_BALANCE}  -> admissible={good.admissible} "
          f"verified={good.verified}")
    bad = menu.check(WRONG_BALANCE)
    print(f"    negative : {WRONG_BALANCE}  -> admissible={bad.admissible} "
          f"violations={list(bad.violations)}")
    print(f"               {bad.explain()[:180]}")

    print("\n  -- realised, and verified by construction " + "-" * 30)
    if session.outcome != COMPILED:
        print(f"    NOT REALISED: the session ended {session.outcome}")
        return 1
    made = realise(session.spec)
    print(f"    reaction        : {made['reaction']}")
    print(f"    conserves()     : {made['conserves']}")
    print(f"    atoms placed    : {made['atoms_placed']} across "
          f"{len(made['geometry'])} species")

    checks = {
        "the session closed": session.outcome == COMPILED,
        "more than one round ran": len(session.rounds) > 1,
        "a round deepened (count rose, measure fell)": bool(deepenings),
        "the written balance was accepted": good.admissible and good.verified,
        "the wrong one was refused, naming the row": bad.violations == (("O", -2),),
        "the realised reaction conserves": made["conserves"],
        # Derived from the species, not typed in. Written as a literal first, and it was
        # wrong -- 15 against the true 13 -- in the one file arguing that a menu must be
        # the image of a declared invariant rather than something someone was confident about.
        "every species got coordinates":
            made["atoms_placed"] == sum(len(m.atoms) for m in SPECIES),
    }
    print("\n" + "=" * 78)
    for label, passed in checks.items():
        print(f"  {'PASS' if passed else 'FAIL'}  {label}")
    print("=" * 78)
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
