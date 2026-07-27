"""
Section I's loop, end to end: the thing Brick 3's failure paragraph said was blocked.

``THE_COMPILER.md`` section VII ends Brick 3's failure paragraph with a dated prediction --
that section VI.3 "will need a well-founded [measure] ... **before the loop of section I
can run more than one round of genuine refinement**". The multiset order landed 2026-07-26.
This file is that prediction discharged.

The narrated version with the full dialogue printed is
``experiments/section_i_end_to_end.py``. These are the assertions, written against the
public API only, so a regression here fails the suite rather than an experiment nobody ran.

What is asserted that is not asserted elsewhere: not that a deepening round is ACCEPTED
(``test_ledger.py`` covers that on synthetic specs) but that a REAL spec, whose every menu
is derived from this package's own invariants, runs several rounds including a deepening
and then produces an object the category is willing to construct.
"""
import pytest

from smartchem.category import (
    Bond,
    Config,
    ConservationError,
    Molecule,
    Reaction,
    conserves,
)
from smartchem.geometry import is_linear, seed_bond_length, seed_coordinates
from smartchem.ledger import COMPILED, Slot, Spec, reaction_slot, shepherd
from smartchem.stoichiometry import stoichiometry_menu

CH4 = Molecule(("C", "H", "H", "H", "H"),
               frozenset({Bond(0, 1, 1), Bond(0, 2, 1), Bond(0, 3, 1), Bond(0, 4, 1)}))
O2 = Molecule.diatomic("O", "O", order=2)
CO2 = Molecule(("C", "O", "O"), frozenset({Bond(0, 1, 2), Bond(0, 2, 2)}))
H2O = Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}))
SPECIES = (CH4, O2, CO2, H2O)

#: Written by the scientist rather than chosen from the menu -- section I's second clause.
WRITTEN = (1, 2, -1, -2)


def _spec() -> Spec:
    """Section I transcribed: one thing enumerable, one thing constrained to nothing yet."""
    return Spec("burn-methane", (
        reaction_slot("reaction", "CH4 and O2 make CO2 and water, balanced somehow",
                      SPECIES),
        Slot("geometry", "positions constrained -- but I have not said to what", rank=1),
    ))


def _scientist(spec, holes):
    """One question per round; the geometry answer opens two concrete ones beneath it."""
    names = {hole.name for hole in holes}
    if "reaction" in names:
        written = stoichiometry_menu(SPECIES).check(WRITTEN)
        assert written.admissible
        return spec.bind("reaction", "written balance")
    if "geometry" in names:
        kinds = sorted({(min(m.atoms[b.i], m.atoms[b.j]),
                         max(m.atoms[b.i], m.atoms[b.j]), b.order)
                        for m in SPECIES for b in m.bonds})
        lengths = tuple(f"{a}-{b} order {o}: {seed_bond_length(a, b, o):.3f} A"
                        for a, b, o in kinds)
        bent = tuple(repr(m) for m in SPECIES if not is_linear(seed_coordinates(m)))
        return (spec.bind("geometry", "by the bond graph of the species in the reaction")
                    .widen(Slot("geometry.bond_lengths", "the distances that graph implies",
                                menu=lengths,
                                derivation=f"seed_bond_length over {len(kinds)} bond types"),
                           Slot("geometry.frame", "the frame and what counts as a mode",
                                menu=(f"Cartesian/Angstrom, non-linear: {', '.join(bent)}",),
                                derivation="is_linear on seed_coordinates output")))
    target = holes[0]
    return spec.bind(target.name, target.menu[0] if target.menu else "<answered>")


@pytest.fixture(scope="module")
def session():
    return shepherd(_spec(), _scientist)


class TestTheLoopRunsMoreThanOneRoundOfGenuineRefinement:
    """Brick 3's dated prediction, discharged on a real spec rather than a synthetic one."""

    def test_it_closes(self, session):
        assert session.outcome == COMPILED
        assert bool(session) is True
        assert session.spec.measure() == 0

    def test_it_took_several_rounds(self, session):
        """A spec that closes in one round proves nothing: 'reduced' and 'done' coincide."""
        assert len(session.rounds) > 1

    def test_exactly_the_deepening_round_is_the_one_the_old_rule_halted_on(self, session):
        """
        The whole repair in one assertion. There is a round on which the COUNT of free
        parameters rises and the MEASURE strictly falls -- ``reduced`` False, ``descended``
        True, on the same object. Under section VI.3 as originally written, that round
        halted the compiler.
        """
        deepenings = [r for r in session.rounds if r.after > r.before]
        assert len(deepenings) == 1
        only = deepenings[0]
        assert only.reduced is False, "the count went up, so the literal rule refuses it"
        assert only.descended is True, "and the well-founded measure accepts it"
        assert only.before_ordinal == (1,) and only.after_ordinal == (0, 0)

    def test_every_round_descended(self, session):
        assert all(r.descended for r in session.rounds)

    def test_no_menu_was_invented(self, session):
        """
        Section III, checked on the closed spec rather than trusted. ``Slot.__post_init__``
        refuses options without a derivation, so this cannot fail while the constructor
        works -- which is the point of enforcing it there.
        """
        carried = [s for s in session.spec.slots if s.menu]
        assert carried, "this spec really does offer options somewhere"
        assert all(s.derivation for s in carried)


class TestVerifiablyRealisable:
    """
    Section I's word is *verifiably*, and a ``COMPILED`` token is the loop's opinion of its
    own dialogue. The verification is that the category will construct the object.
    """

    def test_the_closed_spec_produces_a_reaction_the_category_accepts(self, session):
        assert session.outcome == COMPILED
        written = stoichiometry_menu(SPECIES).check(WRITTEN)
        assert written.reaction is not None
        assert conserves(written.reaction), "re-verified independently of the constructor"

    def test_and_every_species_gets_coordinates(self):
        placed = sum(seed_coordinates(m).shape[0] for m in SPECIES)
        assert placed == sum(len(m.atoms) for m in SPECIES)

    def test_the_verification_is_a_refusal_and_not_a_flag(self):
        """
        What makes construction evidence: the constructor RAISES rather than returning
        something wrong. A checker that returns False would let a caller ignore it.
        """
        with pytest.raises(ConservationError):
            # CH4 + O2 -> CO2 + 2 H2O: under-oxidised, oxygen off by two. The same vector
            # the written-balance check refuses, arriving at the category instead.
            Reaction(Config.of(CH4, O2), Config.of(CO2, H2O, H2O))
