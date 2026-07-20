"""
The persistent cache, tested where it can actually hurt: the key.

A cache that returns the right answer for the right species is the easy half, and a suite
that only checks that half would pass on a cache which serves an HF/cc-pVDZ number to a
CCSD(T)/cbs question. That is the failure worth writing tests against, because it produces
a plausible number rather than a crash -- and this project's whole position is that a
plausible wrong number is worse than no number.

So the classes below are ordered by how badly the failure would hurt:

    TestTheKeySeparatesTiers            a wrong answer, silently. The one that matters.
    TestTheKeySeparatesSpecies          a wrong answer, silently.
    TestFailureIsAlwaysAMiss            a slow run. Acceptable, and must stay that way.
    TestItActuallyCaches                the easy half, checked last because it is easiest.

The oracle under test is a counting fake, not PySCF. What is being tested is the cache's
key discipline, and putting a forty-minute quantum chemistry calculation inside a unit test
would test the cache no better while making it impossible to run.
"""
from __future__ import annotations

import json
import random

import pytest

from smartchem.category import Bond, Molecule
from smartchem.oracle.base import BaseOracle, Estimate
from smartchem.oracle.persistent import (PersistentCache, SCHEMA_VERSION,
                                         species_signature)


class CountingOracle(BaseOracle):
    """
    An oracle that reports which tier it is and how many times it was asked.

    ``value`` is what makes the tier tests bite: two of these with different values stand
    in for two tiers that disagree, which is exactly the situation a bad key would hide.
    """

    def __init__(self, name: str = "FAKE/tier-a", value: float = -1.0,
                 method: str = "FAKE", basis: str = "tier-a", decline: bool = False):
        self.name = name
        self.method = method
        self.basis = basis
        self.tight_d = False
        self.geometry_tier = None
        self.nominal_accuracy_ev = 0.3
        self.value = value
        self.decline = decline
        self.calls = 0

    def energy(self, molecule: Molecule) -> Estimate | None:
        self.calls += 1
        if self.decline:
            return None
        return Estimate(value_ev=self.value, uncertainty_ev=0.3, method=self.name,
                        seconds=12.5, notes="fake", systematic_ev=0.0)


def water() -> Molecule:
    return Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}))


def hydrogen_peroxide() -> Molecule:
    return Molecule(("O", "O", "H", "H"),
                    frozenset({Bond(0, 1, 1), Bond(0, 2, 1), Bond(1, 3, 1)}))


# ======================================================================================
class TestTheKeySeparatesTiers:
    """
    The catastrophic case. A cache that gets this wrong returns a number computed at one
    level of theory, labelled as another, with no symptom whatsoever.
    """

    def test_a_different_tier_does_not_read_the_first_tiers_entry(self, tmp_path):
        path = tmp_path / "cache.json"
        cheap = CountingOracle("FAKE/tier-a", value=-1.0, basis="tier-a")
        dear = CountingOracle("FAKE/tier-b", value=-2.0, basis="tier-b")

        first = PersistentCache(cheap, path).energy(water())
        second = PersistentCache(dear, path).energy(water())

        assert first.value_ev == -1.0
        assert second.value_ev == -2.0, "the expensive tier was served the cheap number"
        assert dear.calls == 1, "the expensive tier never ran"

    def test_the_same_tier_in_a_new_process_does_read_it(self, tmp_path):
        """The mirror image, so the separation above is not just a cache that never hits."""
        path = tmp_path / "cache.json"
        first_run = CountingOracle("FAKE/tier-a", value=-1.0)
        second_run = CountingOracle("FAKE/tier-a", value=-1.0)

        PersistentCache(first_run, path).energy(water())
        cache = PersistentCache(second_run, path)
        restored = cache.energy(water())

        assert second_run.calls == 0, "the second process recomputed a known species"
        assert restored.value_ev == -1.0
        assert cache.hits == 1

    def test_a_tier_differing_only_in_an_attribute_still_separates(self, tmp_path):
        """
        The subtle version: two oracles whose ``name`` is the same but whose settings are
        not. The name is the primary key material, so an oracle carrying a distinguishing
        setting its name forgets to mention is precisely where a collision would hide.
        """
        path = tmp_path / "cache.json"
        plain = CountingOracle("FAKE/same", value=-1.0)
        tight = CountingOracle("FAKE/same", value=-2.0)
        tight.tight_d = True

        PersistentCache(plain, path).energy(water())
        result = PersistentCache(tight, path).energy(water())

        assert result.value_ev == -2.0
        assert tight.calls == 1

    def test_the_cross_check_rejects_a_record_whose_method_disagrees(self, tmp_path):
        """
        Belt and braces, tested directly: even if a key DID collide, the stored method
        string is compared against the asking oracle and a mismatch is discarded.

        Simulated by writing a record under the right key with the wrong method -- which is
        what a future key bug would look like from the cache's point of view.
        """
        path = tmp_path / "cache.json"
        oracle = CountingOracle("FAKE/tier-a", value=-1.0)
        cache = PersistentCache(oracle, path)
        cache.energy(water())

        raw = json.loads(path.read_text())
        key = next(iter(raw["entries"]))
        raw["entries"][key]["method"] = "SOMETHING/else"
        raw["entries"][key]["value_ev"] = -999.0
        path.write_text(json.dumps(raw))

        fresh = CountingOracle("FAKE/tier-a", value=-1.0)
        reloaded = PersistentCache(fresh, path)
        result = reloaded.energy(water())

        assert result.value_ev == -1.0, "a mismatched record was served"
        assert reloaded.rejected == 1
        assert fresh.calls == 1


# ======================================================================================
class TestTheKeySeparatesSpecies:
    """Every field of Molecule can change the energy, so every field must reach the key."""

    def test_different_species_do_not_share_an_entry(self, tmp_path):
        path = tmp_path / "cache.json"
        oracle = CountingOracle()
        cache = PersistentCache(oracle, path)
        cache.energy(water())
        cache.energy(hydrogen_peroxide())
        assert oracle.calls == 2

    def test_charge_reaches_the_key(self):
        neutral = Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}))
        cation = Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}),
                          charge=1)
        assert species_signature(neutral) != species_signature(cation)

    def test_state_reaches_the_key(self):
        """
        The one a reasonable person forgets, because ``state`` was added later for
        carriers and excited species. Omitting it merges a ground and an excited species
        into a single entry -- a collision that yields a plausible number, not a crash.
        """
        ground = Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}))
        excited = Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}),
                           state="excited")
        assert species_signature(ground) != species_signature(excited)

    def test_bond_order_reaches_the_key(self):
        single = Molecule(("C", "C"), frozenset({Bond(0, 1, 1)}))
        double = Molecule(("C", "C"), frozenset({Bond(0, 1, 2)}))
        assert species_signature(single) != species_signature(double)

    def test_the_signature_does_not_depend_on_frozenset_iteration_order(self):
        """
        A frozenset has no order, so a signature built by iterating one is not reproducible
        -- and a key that changes between runs is a cache that never hits while looking
        like it works. The bonds are sorted for exactly this reason.

        THIS TEST WAS VACUOUS ONCE AND THE REASON IS WORTH KEEPING
        ----------------------------------------------------------
        It first used water, whose two bonds cannot collide in the hash table, so two
        frozensets built in opposite orders iterated identically and the assertion held
        with the sorting REMOVED. Deleting ``sorted`` left the suite green.

        That is the same defect ``#22`` shipped: a property exercised only at the size
        where it structurally cannot fail. Measured, frozenset iteration order starts
        diverging by insertion order at roughly eight elements. So this uses PROPANE --
        ten bonds, and the species this project spent 2515.9 s on -- and permutes the
        insertion order rather than assuming one reversal is enough.
        """
        bonds = [Bond(0, 1, 1), Bond(1, 2, 1),                       # C-C-C
                 Bond(0, 3, 1), Bond(0, 4, 1), Bond(0, 5, 1),        # methyl
                 Bond(1, 6, 1), Bond(1, 7, 1),                       # methylene
                 Bond(2, 8, 1), Bond(2, 9, 1), Bond(2, 10, 1)]       # methyl
        atoms = ("C", "C", "C", "H", "H", "H", "H", "H", "H", "H", "H")

        reference = species_signature(Molecule(atoms, frozenset(bonds)))
        rng = random.Random(0)
        for _ in range(50):
            shuffled = bonds[:]
            rng.shuffle(shuffled)
            assert species_signature(Molecule(atoms, frozenset(shuffled))) == reference

    def test_the_permutation_test_above_can_actually_fail(self):
        """
        The guard on the guard. If frozensets of this size never reordered, the test above
        would be decoration -- so this asserts that the hazard it defends against is real,
        by finding an unsorted iteration that genuinely differs.

        If this ever fails because CPython's set implementation changed, the test above has
        silently become vacuous again and needs a new size, not deletion.
        """
        bonds = [Bond(0, 1, 1), Bond(1, 2, 1), Bond(0, 3, 1), Bond(0, 4, 1),
                 Bond(0, 5, 1), Bond(1, 6, 1), Bond(1, 7, 1), Bond(2, 8, 1),
                 Bond(2, 9, 1), Bond(2, 10, 1)]
        reference = list(frozenset(bonds))
        rng = random.Random(0)
        reordered = False
        for _ in range(200):
            shuffled = bonds[:]
            rng.shuffle(shuffled)
            if list(frozenset(shuffled)) != reference:
                reordered = True
                break
        assert reordered, ("frozenset iteration is order-stable at this size, so the "
                           "sorting test above no longer proves anything")

    def test_two_spellings_of_one_species_share_an_entry(self, tmp_path):
        """
        The saving depends on canonicalisation, same as the in-memory cache: the same water
        spelled two ways must be priced once. Correctness would survive missing this; the
        speedup would not.
        """
        path = tmp_path / "cache.json"
        oracle = CountingOracle()
        cache = PersistentCache(oracle, path)
        cache.energy(Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)})))
        cache.energy(Molecule(("H", "O", "H"), frozenset({Bond(1, 0, 1), Bond(1, 2, 1)})))
        assert oracle.calls == 1, "the same species was priced twice"


# ======================================================================================
class TestFailureIsAlwaysAMiss:
    """
    Every way this can break must cost time and nothing else. These tests are the contract
    that the cache can make the project slower but never wrong.
    """

    def test_a_corrupt_file_is_ignored_rather_than_raising(self, tmp_path):
        path = tmp_path / "cache.json"
        path.write_text("{ this is not json")
        oracle = CountingOracle()
        cache = PersistentCache(oracle, path)
        assert cache.energy(water()).value_ev == -1.0
        assert cache.load_error is not None

    def test_a_file_from_another_schema_is_ignored_wholesale(self, tmp_path):
        path = tmp_path / "cache.json"
        path.write_text(json.dumps({"version": SCHEMA_VERSION + 99, "entries": {}}))
        cache = PersistentCache(CountingOracle(), path)
        assert cache.load_error is not None
        assert cache.distinct_species == 0

    def test_a_record_missing_a_field_is_recomputed(self, tmp_path):
        path = tmp_path / "cache.json"
        oracle = CountingOracle()
        PersistentCache(oracle, path).energy(water())
        raw = json.loads(path.read_text())
        key = next(iter(raw["entries"]))
        del raw["entries"][key]["value_ev"]
        path.write_text(json.dumps(raw))

        fresh = CountingOracle()
        cache = PersistentCache(fresh, path)
        assert cache.energy(water()).value_ev == -1.0
        assert fresh.calls == 1
        assert cache.rejected == 1

    def test_a_missing_file_is_simply_empty(self, tmp_path):
        cache = PersistentCache(CountingOracle(), tmp_path / "nope" / "cache.json")
        assert cache.load_error is None
        assert cache.distinct_species == 0
        assert cache.energy(water()) is not None

    def test_a_refusal_is_cached_but_never_confused_with_a_broken_record(self, tmp_path):
        """
        ``None`` is a legitimate cached value. The restore path signals "unusable" with
        ``False`` precisely so a corrupt record cannot masquerade as a refusal and turn a
        transient file problem into a permanent decline.
        """
        path = tmp_path / "cache.json"
        first = CountingOracle(decline=True)
        assert PersistentCache(first, path).energy(water()) is None

        second = CountingOracle(decline=True)
        cache = PersistentCache(second, path)
        assert cache.energy(water()) is None
        assert second.calls == 0, "a cached refusal was re-asked"
        assert cache.hits == 1
        assert cache.rejected == 0


# ======================================================================================
class TestItActuallyCaches:
    """The easy half. Last, because it is the half a broken cache also passes."""

    def test_a_repeated_species_is_priced_once(self, tmp_path):
        oracle = CountingOracle()
        cache = PersistentCache(oracle, tmp_path / "cache.json")
        for _ in range(5):
            cache.energy(water())
        assert oracle.calls == 1
        assert cache.hits == 4

    def test_the_estimate_survives_the_round_trip_exactly(self, tmp_path):
        path = tmp_path / "cache.json"
        original = PersistentCache(CountingOracle(), path).energy(water())
        restored = PersistentCache(CountingOracle(), path).energy(water())
        assert restored.value_ev == original.value_ev
        assert restored.uncertainty_ev == original.uncertainty_ev
        assert restored.systematic_ev == original.systematic_ev
        assert restored.method == original.method

    def test_a_restored_estimate_keeps_what_it_cost_to_know(self, tmp_path):
        """
        ``seconds`` is the cost of KNOWING, not the cost of this invocation, so it survives
        restoration unchanged. Zeroing it would make a warm run look like the science was
        free. What this run saved is reported separately.
        """
        path = tmp_path / "cache.json"
        PersistentCache(CountingOracle(), path).energy(water())
        cache = PersistentCache(CountingOracle(), path)
        restored = cache.energy(water())
        assert restored.seconds == 12.5
        assert cache.saved_seconds == 12.5

    def test_a_restored_estimate_says_where_it_came_from(self, tmp_path):
        path = tmp_path / "cache.json"
        PersistentCache(CountingOracle(), path).energy(water())
        restored = PersistentCache(CountingOracle(), path).energy(water())
        assert "persistent cache" in restored.notes

    def test_the_write_is_atomic_enough_to_leave_no_stray_files(self, tmp_path):
        cache = PersistentCache(CountingOracle(), tmp_path / "cache.json")
        cache.energy(water())
        cache.energy(hydrogen_peroxide())
        assert sorted(p.name for p in tmp_path.iterdir()) == ["cache.json"]

    def test_the_certificate_reports_the_saving(self, tmp_path):
        path = tmp_path / "cache.json"
        PersistentCache(CountingOracle(), path).energy(water())
        cache = PersistentCache(CountingOracle(), path)
        cache.energy(water())
        assert "restored" in cache.certificate()
        assert "12.5 s not re-spent" in cache.certificate()
