"""Autoload -- proven to layer seed -> cache -> providers, cache offline, and never fabricate.

Offline and deterministic: a FAKE provider stands in for the network, so the resolution order, the cache
round-trip, the seed-wins rule, and the no-fabrication guarantee are all pinned without touching the wire.
"""
import os
import tempfile

from smartchem.conditions import Interval
from smartchem.data.autoload import StabilityCache, autoload_stability, merge_records, smartchem_data_dir
from smartchem.data.providers.base import PropertyProvider, PropertyRecord
from smartchem.smiles import parse_smiles

EA = parse_smiles("CCOC(=O)C")     # off-seed
WATER = parse_smiles("O")          # in the seed


class _Fake(PropertyProvider):
    name = "Fake"
    licence = "CC0 (test)"

    def __init__(self, formula, record):
        self._formula, self._record = formula, record
        self.calls = []

    def fetch(self, *, identifier, formula=None):
        self.calls.append((identifier, formula))
        return self._record if formula == self._formula else None


def _ea_record():
    return PropertyRecord(
        boiling=Interval(350, 350, "K"), dhvap_kj_per_mol=31.9,
        sources={"boiling": "fake bp", "dhvap": "fake hvap"}, licence="CC0 (test)", source_name="Fake",
    )


class TestResolutionOrder:
    def test_provider_hit_extends_the_table_and_caches(self):
        with tempfile.TemporaryDirectory() as d:
            cache = StabilityCache.load(os.path.join(d, "c.json"))
            table = autoload_stability(
                [EA], identifiers={EA: "CCOC(=O)C"}, providers=(_Fake("C4H8O2", _ea_record()),),
                cache=cache, allow_network=True,
            )
            rec = table.for_formula("C4H8O2")
            assert rec is not None and rec.boiling.lo == 350.0 and rec.dhvap_kj_per_mol == 31.9
            assert os.path.exists(os.path.join(d, "c.json"))

    def test_second_run_is_served_from_cache_offline(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "c.json")
            autoload_stability([EA], identifiers={EA: "CCOC(=O)C"},
                               providers=(_Fake("C4H8O2", _ea_record()),),
                               cache=StabilityCache.load(path), allow_network=True)
            table = autoload_stability([EA], providers=(), cache=StabilityCache.load(path),
                                       allow_network=False)
            assert table.for_formula("C4H8O2") is not None  # from cache, no network

    def test_the_seed_wins_and_is_never_refetched(self):
        spy = _Fake("H2O", _ea_record())  # would never match H2O anyway; assert it is not even asked
        with tempfile.TemporaryDirectory() as d:
            autoload_stability([WATER], providers=(spy,),
                               cache=StabilityCache.load(os.path.join(d, "c.json")), allow_network=True)
            assert spy.calls == []  # the seed already covers water; no fetch attempted


class TestNoFabrication:
    def test_a_compound_no_provider_covers_stays_absent(self):
        with tempfile.TemporaryDirectory() as d:
            table = autoload_stability([EA], identifiers={EA: "CCOC(=O)C"},
                                       providers=(_Fake("SOMETHING_ELSE", _ea_record()),),
                                       cache=StabilityCache.load(os.path.join(d, "c.json")),
                                       allow_network=True)
            assert table.for_formula("C4H8O2") is None  # a miss is UNKNOWN, never fabricated

    def test_allow_network_false_makes_no_calls(self):
        spy = _Fake("C4H8O2", _ea_record())
        with tempfile.TemporaryDirectory() as d:
            autoload_stability([EA], identifiers={EA: "CCOC(=O)C"}, providers=(spy,),
                               cache=StabilityCache.load(os.path.join(d, "c.json")), allow_network=False)
            assert spy.calls == []


class TestMergeAndCache:
    def test_merge_takes_first_non_none_field_wise(self):
        a = PropertyRecord(melting=Interval(300, 300, "K"), sources={"melting": "A"}, source_name="A")
        b = PropertyRecord(boiling=Interval(400, 400, "K"), sources={"boiling": "B"}, source_name="B")
        merged = merge_records([a, b])
        assert merged.melting.lo == 300 and merged.boiling.lo == 400
        assert "A" in merged.source_name and "B" in merged.source_name

    def test_cache_survives_a_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "c.json")
            c1 = StabilityCache.load(path)
            from smartchem.data.stability import StabilityRef
            c1.put("k1", StabilityRef("C4H8O2", "ethyl acetate", None, Interval(350, 350, "K"),
                                      None, True, "test", dhvap_kj_per_mol=31.9))
            c1.save()
            c2 = StabilityCache.load(path)
            assert c2.get("k1").dhvap_kj_per_mol == 31.9

    def test_a_corrupt_cache_loads_empty_not_crashing(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "c.json")
            with open(path, "w") as fh:
                fh.write("{ not json")
            assert StabilityCache.load(path).records() == ()

    def test_data_dir_is_resolvable(self):
        assert isinstance(smartchem_data_dir(), str) and smartchem_data_dir()
