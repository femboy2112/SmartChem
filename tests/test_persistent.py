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

from dataclasses import replace
import json
import random

import pytest

from smartchem.atoms import PT
from smartchem.category import Bond, Molecule
from smartchem.data.reference import polyatomic
from smartchem.legacy import Env
from smartchem.oracle.base import BaseOracle, Estimate
from smartchem.oracle import heuristic as heuristic_module
from smartchem.oracle.heuristic import HeuristicOracle
from smartchem.oracle.persistent import (
    PersistentCache,
    SCHEMA_VERSION,
    _chain_source_sha256,
    _fingerprint,
    _record_checksum,
    species_signature,
)


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

    def test_an_unlisted_result_driving_attribute_reaches_the_fingerprint(self, tmp_path):
        """The conservative BaseOracle spec includes state a hand-written allowlist misses."""
        path = tmp_path / "cache.json"
        first = CountingOracle("FAKE/same", value=-1.0)
        second = CountingOracle("FAKE/same", value=-2.0)

        PersistentCache(first, path).energy(water())
        result = PersistentCache(second, path).energy(water())

        assert result.value_ev == -2.0
        assert second.calls == 1

    def test_geometry_and_size_policy_reach_the_fingerprint(self, tmp_path):
        first = CountingOracle("FAKE/same", value=-1.0)
        second = CountingOracle("FAKE/same", value=-2.0)
        first.max_atoms, second.max_atoms = 1, 2
        path = tmp_path / "cache.json"
        PersistentCache(first, path).energy(water())
        result = PersistentCache(second, path).energy(water())
        assert result.value_ev == -2.0
        assert second.calls == 1

    def test_environment_reaches_the_fingerprint(self, tmp_path):
        standard = PersistentCache(HeuristicOracle(Env.standard()), tmp_path / "cache.json")
        aqueous = PersistentCache(HeuristicOracle(Env.aqueous()), tmp_path / "cache.json")
        assert standard.fingerprint != aqueous.fingerprint

    def test_heuristic_periodic_inputs_reach_the_fingerprint(self, tmp_path, monkeypatch):
        before = PersistentCache(
            HeuristicOracle(), tmp_path / "cache.json"
        ).fingerprint
        monkeypatch.setattr(
            heuristic_module,
            "PT",
            {**PT, "H": replace(PT["H"], ie_list_ev=(99.0,))},
        )
        after = PersistentCache(
            HeuristicOracle(), tmp_path / "cache.json"
        ).fingerprint
        assert before != after

    def test_legacy_engine_source_reaches_heuristic_model_identity(self, monkeypatch):
        before = HeuristicOracle().calculation_spec()["model_inputs_sha256"]
        real_source_sha256 = heuristic_module._source_sha256

        def changed_legacy_source(subject):
            if subject is heuristic_module.legacy_module:
                return "changed-legacy-source"
            return real_source_sha256(subject)

        monkeypatch.setattr(heuristic_module, "_source_sha256", changed_legacy_source)
        after = HeuristicOracle().calculation_spec()["model_inputs_sha256"]
        assert before != after

    def test_container_types_cannot_collide_in_calculation_specs(self, tmp_path):
        path = tmp_path / "cache.json"
        tuple_oracle = CountingOracle("FAKE/same", value=-1.0)
        list_oracle = CountingOracle("FAKE/same", value=-2.0)
        tuple_oracle.setting = (1, 2)
        list_oracle.setting = [1, 2]

        first = PersistentCache(tuple_oracle, path)
        second = PersistentCache(list_oracle, path)
        assert first.fingerprint != second.fingerprint
        first.energy(water())
        assert second.energy(water()).value_ev == -2.0
        assert list_oracle.calls == 1

    def test_immutable_mapping_inside_a_dataclass_can_be_fingerprinted(self, tmp_path):
        oracle = CountingOracle()
        oracle.reference_profile = polyatomic("H2O")
        cache = PersistentCache(oracle, tmp_path / "cache.json")
        assert cache.fingerprint
        assert cache.energy(water()) is not None

    def test_checksum_rejects_a_record_edited_after_it_was_written(self, tmp_path):
        """
        The checksum is an integrity guard, not authentication. An accidental or torn
        edit must become a cache miss even when the outer key still matches.
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

    def test_signed_record_with_wrong_oracle_identity_is_rejected(self, tmp_path):
        path = tmp_path / "cache.json"
        PersistentCache(CountingOracle(), path).energy(water())
        raw = json.loads(path.read_text())
        key = next(iter(raw["entries"]))
        record = raw["entries"][key]
        record["oracle_name"] = "FAKE/tier-a-evil"
        unsigned = {field: value for field, value in record.items() if field != "checksum"}
        record["checksum"] = _record_checksum(unsigned)
        path.write_text(json.dumps(raw))

        oracle = CountingOracle()
        cache = PersistentCache(oracle, path)
        assert cache.energy(water()).value_ev == -1.0
        assert oracle.calls == 1
        assert cache.rejected == 1


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

    def test_delimiter_characters_in_labels_cannot_collide(self):
        left = Molecule(("A.B", "C"), frozenset({Bond(0, 1)}))
        right = Molecule(("A", "B.C"), frozenset({Bond(0, 1)}))
        assert left != right
        assert species_signature(left) != species_signature(right)

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

    @pytest.mark.parametrize(
        "kwargs",
        [{"autosave": "false"}, {"cache_refusals": "false"}],
    )
    def test_boolean_policies_reject_truthy_strings(self, tmp_path, kwargs):
        with pytest.raises(TypeError, match="boolean"):
            PersistentCache(CountingOracle(), tmp_path / "cache.json", **kwargs)

    def test_a_file_from_another_schema_is_ignored_wholesale(self, tmp_path):
        path = tmp_path / "cache.json"
        future = {
            "version": SCHEMA_VERSION + 99,
            "entries": {"future-expensive-result": {"sentinel": True}},
        }
        original = json.dumps(future, sort_keys=True)
        path.write_text(original)
        oracle = CountingOracle()
        cache = PersistentCache(oracle, path)
        assert cache.load_error is not None
        assert cache.distinct_species == 0
        assert cache.energy(water()).value_ev == -1.0
        assert oracle.calls == 1
        assert path.read_text() == original, "an older writer destroyed a future-schema file"

    def test_autosave_failure_does_not_discard_a_computed_result(self, tmp_path):
        blocker = tmp_path / "not-a-directory"
        blocker.write_text("file")
        oracle = CountingOracle()
        cache = PersistentCache(oracle, blocker / "cache.json")

        result = cache.energy(water())

        assert result.value_ev == -1.0
        assert oracle.calls == 1
        assert cache.save_error is not None

    def test_an_overflowing_numeric_record_is_recomputed(self, tmp_path):
        path = tmp_path / "cache.json"
        PersistentCache(CountingOracle(), path).energy(water())
        raw = json.loads(path.read_text())
        key = next(iter(raw["entries"]))
        record = raw["entries"][key]
        record["value_ev"] = 10**400
        unsigned = {field: value for field, value in record.items() if field != "checksum"}
        record["checksum"] = _record_checksum(unsigned)
        path.write_text(json.dumps(raw))

        oracle = CountingOracle()
        cache = PersistentCache(oracle, path)
        assert cache.energy(water()).value_ev == -1.0
        assert oracle.calls == 1
        assert cache.rejected == 1

    def test_a_boolean_cannot_masquerade_as_a_numeric_record_field(self, tmp_path):
        path = tmp_path / "cache.json"
        PersistentCache(CountingOracle(), path).energy(water())
        raw = json.loads(path.read_text())
        key = next(iter(raw["entries"]))
        record = raw["entries"][key]
        record["value_ev"] = True
        unsigned = {field: value for field, value in record.items() if field != "checksum"}
        record["checksum"] = _record_checksum(unsigned)
        path.write_text(json.dumps(raw))

        oracle = CountingOracle()
        cache = PersistentCache(oracle, path)
        assert cache.energy(water()).value_ev == -1.0
        assert oracle.calls == 1
        assert cache.rejected == 1

    def test_signed_record_rejects_malformed_sensitivity_provenance(self, tmp_path):
        path = tmp_path / "cache.json"
        PersistentCache(CountingOracle(), path).energy(water())
        raw = json.loads(path.read_text())
        key = next(iter(raw["entries"]))
        record = raw["entries"][key]
        record["systematic_terms"] = [[7, 0.1]]
        record["systematic_ev"] = 0.1
        unsigned = {field: value for field, value in record.items() if field != "checksum"}
        record["checksum"] = _record_checksum(unsigned)
        path.write_text(json.dumps(raw))

        oracle = CountingOracle()
        cache = PersistentCache(oracle, path)
        assert cache.energy(water()).value_ev == -1.0
        assert oracle.calls == 1
        assert cache.rejected == 1

    def test_signed_record_rejects_contradictory_method_views(self, tmp_path):
        path = tmp_path / "cache.json"
        PersistentCache(CountingOracle(), path).energy(water())
        raw = json.loads(path.read_text())
        key = next(iter(raw["entries"]))
        record = raw["entries"][key]
        record["methods"] = ["different-method"]
        unsigned = {field: value for field, value in record.items() if field != "checksum"}
        record["checksum"] = _record_checksum(unsigned)
        path.write_text(json.dumps(raw))

        oracle = CountingOracle()
        cache = PersistentCache(oracle, path)
        assert cache.energy(water()).value_ev == -1.0
        assert oracle.calls == 1
        assert cache.rejected == 1

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
        assert PersistentCache(first, path, cache_refusals=True).energy(water()) is None

        second = CountingOracle(decline=True)
        cache = PersistentCache(second, path, cache_refusals=True)
        assert cache.energy(water()) is None
        assert second.calls == 0, "a cached refusal was re-asked"
        assert cache.hits == 1
        assert cache.rejected == 0

    def test_refusals_are_not_persistent_by_default(self, tmp_path):
        path = tmp_path / "cache.json"
        first = CountingOracle(decline=True)
        assert PersistentCache(first, path).energy(water()) is None
        second = CountingOracle(decline=False, value=-2.0)
        result = PersistentCache(second, path).energy(water())
        assert result.value_ev == -2.0
        assert second.calls == 1

    def test_default_reader_does_not_inherit_an_opted_in_cached_refusal(self, tmp_path):
        path = tmp_path / "cache.json"
        PersistentCache(
            CountingOracle(decline=True), path, cache_refusals=True
        ).energy(water())

        live = CountingOracle(decline=True)
        result = PersistentCache(live, path, cache_refusals=False).energy(water())
        assert result is None
        assert live.calls == 1

    def test_a_non_object_record_is_recomputed(self, tmp_path):
        path = tmp_path / "cache.json"
        PersistentCache(CountingOracle(), path).energy(water())
        raw = json.loads(path.read_text())
        key = next(iter(raw["entries"]))
        raw["entries"][key] = []
        path.write_text(json.dumps(raw))
        fresh = CountingOracle()
        cache = PersistentCache(fresh, path)
        assert cache.energy(water()).value_ev == -1.0
        assert fresh.calls == 1
        assert cache.rejected == 1


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
        assert restored.methods == original.methods
        assert restored.systematic_terms == original.systematic_terms
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
        assert sorted(p.name for p in tmp_path.iterdir()) == ["cache.json", "cache.json.lock"]

    def test_stale_writers_merge_instead_of_losing_completed_work(self, tmp_path):
        path = tmp_path / "cache.json"
        first = PersistentCache(CountingOracle(), path)
        second = PersistentCache(CountingOracle(), path)
        first.energy(water())
        second.energy(hydrogen_peroxide())
        raw = json.loads(path.read_text())
        assert len(raw["entries"]) == 2

    def test_stale_writer_cannot_restore_a_record_another_writer_repaired(self, tmp_path):
        path = tmp_path / "cache.json"
        PersistentCache(CountingOracle(), path).energy(water())
        raw = json.loads(path.read_text())
        water_key = next(iter(raw["entries"]))
        raw["entries"][water_key] = []
        path.write_text(json.dumps(raw))

        stale = PersistentCache(CountingOracle(), path, autosave=False)
        repair = PersistentCache(CountingOracle(), path)
        assert repair.energy(water()).value_ev == -1.0

        stale.energy(hydrogen_peroxide())
        assert stale.save()

        merged = json.loads(path.read_text())["entries"]
        assert len(merged) == 2
        assert isinstance(merged[water_key], dict), "stale snapshot overwrote the repair"
        verifier = CountingOracle()
        assert PersistentCache(verifier, path).energy(water()).value_ev == -1.0
        assert verifier.calls == 0

    def test_intact_records_cannot_be_swapped_between_species_keys(self, tmp_path):
        path = tmp_path / "cache.json"
        cache = PersistentCache(CountingOracle(), path)
        cache.energy(water())
        cache.energy(hydrogen_peroxide())

        raw = json.loads(path.read_text())
        first_key, second_key = raw["entries"]
        raw["entries"][first_key], raw["entries"][second_key] = (
            raw["entries"][second_key], raw["entries"][first_key]
        )
        path.write_text(json.dumps(raw))

        oracle = CountingOracle()
        reloaded = PersistentCache(oracle, path)
        assert reloaded.energy(water()).value_ev == -1.0
        assert oracle.calls == 1
        assert reloaded.rejected == 1

    def test_the_certificate_reports_the_saving(self, tmp_path):
        path = tmp_path / "cache.json"
        PersistentCache(CountingOracle(), path).energy(water())
        cache = PersistentCache(CountingOracle(), path)
        cache.energy(water())
        assert "restored" in cache.certificate()
        assert "12.5 s not re-spent" in cache.certificate()


class TestTheWrapperDoesNotHideTheInnerImplementation:
    """
    A wrapped oracle's cache key must depend on the WRAPPED oracle's implementation.

    This was a live silent-wrong-answer path. ``_fingerprint`` hashed only
    ``inspect.getmodule(type(oracle))``, and the ordinary composition this project uses --
    ``PersistentCache(CachingOracle(PySCFOracle(...)))`` -- meant the digest covered
    ``caching.py`` and never ``pyscf_oracle.py``. ``calculation_spec`` delegates correctly,
    but it carries SETTINGS, and ``_model_inputs_sha256`` is a deliberate whitelist: a
    change to ``conv_tol``, ``_DESCENT_STEP_ANGSTROM``, the CBS algebra, or a frozen-core
    flag altered every number and left the key untouched. Measured on a copied tree, adding
    ``mycc.frozen = 1`` moved the bare fingerprint and left the wrapped one bit-identical,
    and the stale value was served with ``rejected=0``.
    """

    class Wrapper:
        """Minimal stand-in for any delegating oracle: the hazard is composition itself."""

        def __init__(self, inner):
            self.inner = inner

        def calculation_spec(self):
            return {"wrapper": "test", "inner": getattr(self.inner, "name", None)}

    def test_the_inner_oracle_source_reaches_the_digest(self):
        # HeuristicOracle and CountingOracle live in different modules, so a digest that
        # ignored `.inner` would return the same value for both wrappers.
        one = _chain_source_sha256(self.Wrapper(HeuristicOracle()))
        two = _chain_source_sha256(self.Wrapper(CountingOracle()))
        assert one != two

    def test_a_wrapper_alone_differs_from_a_wrapper_around_something(self):
        assert _chain_source_sha256(self.Wrapper(None)) != _chain_source_sha256(
            self.Wrapper(HeuristicOracle())
        )

    def test_the_chain_is_walked_to_the_bottom_not_just_one_level(self):
        shallow = self.Wrapper(self.Wrapper(None))
        deep = self.Wrapper(self.Wrapper(HeuristicOracle()))
        assert _chain_source_sha256(shallow) != _chain_source_sha256(deep)

    def test_a_self_referential_chain_terminates_instead_of_recursing_forever(self):
        node = self.Wrapper(None)
        node.inner = node          # the guard is identity, not a depth limit
        assert isinstance(_chain_source_sha256(node), str)

    def test_a_repeated_module_is_not_double_counted(self):
        # Two wrappers of the same class contribute their module once, so the digest is a
        # statement about which implementations are involved, not how deep the stack is.
        once = _chain_source_sha256(self.Wrapper(None))
        twice = _chain_source_sha256(self.Wrapper(self.Wrapper(None)))
        assert once == twice

    def test_the_full_fingerprint_inherits_this(self, tmp_path):
        # The property has to survive at _fingerprint, which is what actually keys records.
        assert _fingerprint(self.Wrapper(HeuristicOracle())) != _fingerprint(
            self.Wrapper(CountingOracle())
        )
