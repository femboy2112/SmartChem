"""
The species cache (#18): what it saves, that it changes nothing, and where it decays.

The saving is the easy part to test and the least important. The two claims that matter
are that a memoised run is bit-identical to an unmemoised one, and that the saving rests
on the canonical key rather than on an invariant some other module happens to maintain.
"""
from __future__ import annotations

import pytest

from smartchem.category import Bond, Config, Molecule, Reaction
from smartchem.oracle.caching import CachingOracle
from smartchem.oracle.heuristic import HeuristicOracle
from smartchem.thermo import reaction_energy


def mol(atoms, bonds):
    return Molecule(tuple(atoms), frozenset(Bond(*b) for b in bonds))


H2 = mol("HH", [(0, 1)])
O2 = mol("OO", [(0, 1, 2)])
N2 = mol("NN", [(0, 1, 3)])
H2O = mol("OHH", [(0, 1), (0, 2)])
NH3 = mol("NHHH", [(0, 1), (0, 2), (0, 3)])
OH = mol("OH", [(0, 1)])
NH = mol("NH", [(0, 1)])
H, O, N = Molecule.atom("H"), Molecule.atom("O"), Molecule.atom("N")

STEPS = [
    (Config.of(H2), Config.of(H, H)),
    (Config.of(N2), Config.of(N, N)),
    (Config.of(N, H), Config.of(NH)),
    (Config.of(NH, H, H), Config.of(NH3)),
    (Config.of(O2), Config.of(O, O)),
    (Config.of(O, H), Config.of(OH)),
    (Config.of(OH, H), Config.of(H2O)),
    (Config.of(H2, O), Config.of(H2O)),
    (Config.of(N2, H2), Config.of(N, N, H, H)),
]
SPECTATORS = [(), (N2,), (N2, H2), (N2, H2, H2O), (N2, H2, H2O, NH3)]


def a_search():
    """Every step under each spectator set -- the shape a real search generates."""
    return [
        Reaction(Config(dom.species + extra), Config(cod.species + extra))
        for dom, cod in STEPS
        for extra in SPECTATORS
    ]


class CountingOracle(HeuristicOracle):
    """Records every species it is asked to price."""

    def __init__(self):
        super().__init__()
        self.asked = []

    def energy(self, molecule):
        self.asked.append(molecule)
        return super().energy(molecule)


class TestTheCacheChangesNothing:
    """Transparency first. A speedup that moves an answer is not a speedup."""

    def test_every_reaction_energy_is_bit_identical(self):
        plain, cached = HeuristicOracle(), CachingOracle(HeuristicOracle())
        for rxn in a_search():
            a, b = reaction_energy(rxn, plain), reaction_energy(rxn, cached)
            assert (a is None) == (b is None), rxn
            if a is not None:
                assert a.value_ev == b.value_ev
                assert a.uncertainty_ev == b.uncertainty_ev
                assert a.systematic_ev == b.systematic_ev

    def test_refusals_are_cached_too(self):
        """
        An oracle that declines a species declines it every time, so re-asking is pure
        cost. Caching `None` is the point, and it is the case a naive `if not in cache`
        over a truthiness check would get wrong.
        """
        inner = CountingOracle()
        cached = CachingOracle(inner)
        unpriceable = Molecule.atom("Xx")           # no such element; the oracle declines
        assert cached.energy(unpriceable) is None
        assert cached.energy(unpriceable) is None
        assert len(inner.asked) == 1, "a refusal was re-asked"
        assert cached.hits == 1


class TestTheSavingIsReal:
    def test_the_search_prices_each_distinct_species_exactly_once(self):
        """
        The floor, not a tuning target: there are N distinct species, each is priced once,
        and nothing can do better without pricing something zero times.
        """
        inner = CountingOracle()
        cached = CachingOracle(inner)
        for rxn in a_search():
            reaction_energy(rxn, cached)

        distinct = {m for rxn in a_search() for m in rxn.dom.species + rxn.cod.species}
        assert len(inner.asked) == len(set(inner.asked))          # nothing priced twice
        assert len(inner.asked) <= len(distinct)

    def test_it_beats_spectator_cancellation_alone_by_an_order_of_magnitude(self):
        """
        Measured 2026-07-20: 335 naive -> 155 with spectator cancellation -> 10 with the
        cache. Pinned as a ratio rather than as absolute counts, so the test survives a
        change to the species set but still fails if the cache stops working.
        """
        search = a_search()

        uncached = CountingOracle()
        for rxn in search:
            reaction_energy(rxn, uncached)

        inner = CountingOracle()
        cached = CachingOracle(inner)
        for rxn in search:
            reaction_energy(rxn, cached)

        assert len(uncached.asked) / len(inner.asked) > 10.0, (
            f"cache saved only {len(uncached.asked) / len(inner.asked):.2f}x "
            f"({len(uncached.asked)} -> {len(inner.asked)})"
        )


class TestTheSavingRestsOnTheCanonicalKey:
    """
    The failure mode worth a test: a cache keyed on raw molecules is still CORRECT and
    silently stops saving. There is no symptom except a slow run, so the property is
    pinned rather than left to be noticed.
    """

    def test_differently_labelled_copies_share_one_entry(self):
        inner = CountingOracle()
        cached = CachingOracle(inner)
        water = mol("OHH", [(0, 1), (0, 2)])
        same_water_relabelled = mol("HOH", [(1, 0), (1, 2)])

        assert water != same_water_relabelled, (
            "these must be structurally unequal, or the test proves nothing"
        )
        cached.energy(water)
        cached.energy(same_water_relabelled)
        assert len(inner.asked) == 1, "the relabelled copy was priced again"
        assert cached.hits == 1

    def test_a_species_too_large_to_canonicalise_still_gets_a_correct_answer(self, monkeypatch):
        """
        Above the canonicalisation budget the key cannot be canonical. Correctness must
        not depend on the saving, so it falls back to the molecule as given -- and says
        so, rather than degrading quietly.
        """
        import smartchem.category as category

        inner = CountingOracle()
        cached = CachingOracle(inner)
        # The witness used to be the complete graph K_9, whose true-twin vertices blew past the
        # leaf ceiling. 0.9.5 S16 automorphism pruning canonicalises K_9 in a handful of nodes,
        # so this leg failed ("DID NOT RAISE NotImplementedError") on fbf1287. The law is about
        # what happens PAST the bound, not about which graph sits there: lower the S16 node
        # ceiling to 2 and K_9 is over it again, refused with CanonicalBoundExceeded (a
        # NotImplementedError). The cache is emptied around it -- an earlier test may hold K_9.
        monkeypatch.setattr(category, "_MAX_INDIVIDUALISATION_NODES", 2)
        Molecule.canonical.cache_clear()
        huge = Molecule(
            tuple("C" * 9),
            frozenset(Bond(i, j) for i in range(9) for j in range(i + 1, 9)),
        )                                                   # refuses to canonicalise
        try:
            with pytest.raises(category.CanonicalBoundExceeded):
                huge.canonical()

            assert cached.energy(huge) is cached.energy(huge)  # cached, and consistent
            assert cached.uncanonicalised >= 1                 # and it is counted, not hidden
        finally:
            Molecule.canonical.cache_clear()

    def test_the_certificate_reports_what_was_actually_saved(self):
        cached = CachingOracle(HeuristicOracle())
        for rxn in a_search():
            reaction_energy(rxn, cached)
        line = cached.certificate()
        assert "distinct species" in line and "x saved" in line
        assert str(cached.distinct_species) in line
