"""Open-data providers -- proven to parse REAL captured responses, aggregate honestly, and never fabricate.

The committed suite is offline and deterministic: it parses recorded API fixtures (captured live once,
in ``tests/fixtures/providers/``), never the live network.  What the tests pin is exactly the discipline
that makes autoload safe -- an explicit unit is required, outliers are rejected, a miss is ``None``.
"""
from pathlib import Path

from smartchem.data.providers.bradley import BradleyMeltingPointProvider
from smartchem.data.providers.pubchem import record_from_annotations, smiles_from_property_json
from smartchem.data.providers.tempparse import aggregate_kelvin, parse_temperature_values
from smartchem.data.providers.wikidata import record_from_sparql

_FIX = Path(__file__).parent / "fixtures" / "providers"


class TestTemperatureParser:
    def test_unit_bearing_values_parse_to_kelvin(self):
        assert parse_temperature_values("168 °C") == [(441.15, 441.15)]
        (lo, hi), = parse_temperature_values("336 to 342 °F")
        assert 442 < lo < 443 and 445 < hi < 446

    def test_a_bare_unitless_number_is_dropped_not_guessed(self):
        assert parse_temperature_values("168-172") == []

    def test_aggregate_rejects_a_gross_outlier(self):
        agg = aggregate_kelvin([(441, 443), (442, 442), (9999, 9999)])
        assert agg is not None and agg.hi < 500  # the 9999 outlier is discarded

    def test_empty_aggregates_to_none(self):
        assert aggregate_kelvin([]) is None


class TestPubChemParsing:
    def test_real_acetaminophen_melting_point_annotation(self):
        mp_json = (_FIX / "pubchem_mp_acetaminophen.json").read_text()
        rec = record_from_annotations(mp_json, None, 1983)
        assert rec.melting is not None
        assert 440 < rec.melting.lo < 446  # ~168-172 C, aggregated from several sourced values
        assert "PubChem CID 1983" in rec.sources["melting"]
        assert "public domain" in rec.licence

    def test_real_acetic_acid_boiling_point_annotation(self):
        bp_json = (_FIX / "pubchem_bp_aceticacid.json").read_text()
        rec = record_from_annotations(None, bp_json, 176)
        assert rec.boiling is not None and 390 < rec.boiling.lo < 392  # ~118 C

    def test_an_empty_annotation_is_a_clean_miss(self):
        assert record_from_annotations(None, None, 1).is_empty


class TestPubChemNameResolution:
    """The name->SMILES resolution that lets an arbitrary NAME be warmed (structure is the cache key)."""

    def test_real_aspirin_name_to_smiles_response(self):
        # PubChem's current property key is `SMILES` (formerly CanonicalSMILES) -- the parser reads it
        text = (_FIX / "pubchem_name2smiles_aspirin.json").read_text()
        assert smiles_from_property_json(text) == "CC(=O)OC1=CC=CC=C1C(=O)O"

    def test_a_historical_key_is_still_read(self):
        # resilience to the endpoint's own churn: the old CanonicalSMILES key still parses
        assert smiles_from_property_json(
            '{"PropertyTable":{"Properties":[{"CID":1,"CanonicalSMILES":"CCO"}]}}'
        ) == "CCO"

    def test_an_empty_or_malformed_response_is_a_clean_none(self):
        assert smiles_from_property_json('{"PropertyTable":{"Properties":[]}}') is None
        assert smiles_from_property_json("not json") is None


class TestWikidataParsing:
    def test_real_acetic_acid_structured_values(self):
        wd_json = (_FIX / "wikidata_aceticacid.json").read_text()
        rec = record_from_sparql(wd_json, "Q47512")
        assert rec.melting is not None and 288 < rec.melting.lo < 291   # ~16.6 C
        assert rec.boiling is not None and 390 < rec.boiling.lo < 392   # ~118 C
        assert "CC0" in rec.licence

    def test_malformed_sparql_is_a_clean_empty_record(self):
        assert record_from_sparql("not json").is_empty


class TestBradleyProvider:
    def _provider(self):
        return BradleyMeltingPointProvider(csv_path=str(_FIX / "bradley_sample.csv"))

    def test_reads_a_melting_point_by_name(self):
        rec = self._provider().fetch(identifier="ethyl acetate")
        assert rec is not None and abs(rec.melting.lo - (273.15 - 83.6)) < 0.01
        assert "CC0" in rec.licence

    def test_duplicate_rows_are_aggregated_to_the_median(self):
        # benzoic acid appears twice (121, 123 C) -> median 122 C
        rec = self._provider().fetch(identifier="benzoic acid")
        assert abs(rec.melting.lo - (273.15 + 122.0)) < 0.01

    def test_a_donotuse_row_is_skipped(self):
        assert self._provider().fetch(identifier="bad entry") is None

    def test_a_miss_returns_none(self):
        assert self._provider().fetch(identifier="unobtainium") is None

    def test_unavailable_without_a_csv(self):
        assert not BradleyMeltingPointProvider(csv_path="/nonexistent/nope.csv").available
