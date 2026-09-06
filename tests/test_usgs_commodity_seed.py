"""COST-VEC-01 / TERM-MAT-01: the committed USGS commodity-price seed -- a dated, cited, frozen reference dataset of
real average unit values, and the non-vacuous price discipline that lifts the old BLOCKED-on-price wall honestly.
"""

import pytest

from experiments.usgs_commodity_seed import (
    ACCESS_DATE,
    ESTIMATE_YEAR,
    FINAL_YEAR,
    FROZEN_HASH,
    SOURCE,
    UNPRICED_NO_PRIMARY_SOURCE,
    USGS_COMMODITY_PRICES,
    CommodityPrice,
    content_hash,
    report,
    validate,
)


class TestSourcedAndFrozen:
    def test_the_frozen_set_validates(self):
        validate()  # raises if any record is hollow / non-finite / unsourced / duplicate-keyed

    def test_the_content_hash_is_frozen_and_matches(self):
        # tamper-evident: the committed FROZEN_HASH must equal the live content hash of the values.
        assert content_hash() == FROZEN_HASH
        assert len(FROZEN_HASH) == 64  # sha256 hex

    def test_it_names_a_dated_source(self):
        assert "USGS" in SOURCE and "2026" in SOURCE
        assert ACCESS_DATE == "2026-09-04"
        assert FINAL_YEAR == 2024 and ESTIMATE_YEAR == 2025

    def test_every_price_names_its_usgs_source_url(self):
        for r in USGS_COMMODITY_PRICES:
            assert r.chapter_url.startswith("https://pubs.usgs.gov/periodicals/mcs2026/")


class TestTranscribedValues:
    """Anti-drift pins on the load-bearing numbers -- each read directly off the MCS 2026 chapter price row and its
    column-year header (2021 2022 2023 2024 2025e), verified in-sandbox (curl + pdftotext -layout)."""

    def _by(self, commodity, material):
        return next(r for r in USGS_COMMODITY_PRICES if r.commodity == commodity and r.material == material)

    def test_salt_soda_lime_sulfur_final_2024_values(self):
        assert self._by("salt", "rock salt").price_usd_per_t == 52.95
        assert self._by("salt", "vacuum and open pan salt").price_usd_per_t == 259.69
        assert self._by("soda ash", "soda ash (natural)").price_usd_per_t == 169.35
        assert self._by("lime", "quicklime").price_usd_per_t == 261.4
        assert self._by("sulfur", "elemental sulfur").price_usd_per_t == 46.42

    def test_the_2025_estimate_is_carried_and_flagged(self):
        # the following-year USGS estimate ('2025e') is carried too -- the sulfur jump 46.42 -> 180 is a real datum,
        # not a transcription slip (the chapter narrative confirms "increasing to $180 per ton from $46 per ton").
        assert self._by("sulfur", "elemental sulfur").estimate_2025_usd_per_t == 180.0
        assert self._by("soda ash", "soda ash (natural)").estimate_2025_usd_per_t == 150.0


class TestKeysAndForms:
    def test_keys_are_distinct(self):
        keys = [r.key() for r in USGS_COMMODITY_PRICES]
        assert len(keys) == len(set(keys))

    def test_four_salt_forms_are_present(self):
        salt = [r for r in USGS_COMMODITY_PRICES if r.commodity == "salt"]
        assert {r.material for r in salt} == {"rock salt", "solar salt", "vacuum and open pan salt", "salt in brine"}


class TestNonVacuousPriceDiscipline:
    def test_a_hollow_zero_price_is_refused(self):
        # THE non-vacuity: a sourced row claiming a $0/t price is a hollow claim -- REFUSED, and the guard fires on
        # the hollow RECORD, not merely on an empty set.
        hollow = CommodityPrice("salt", "fake", "NaCl", 0.0, 10.0, "basis", "https://pubs.usgs.gov/x.pdf")
        with pytest.raises(ValueError, match="hollow|> 0|real sourced"):
            validate((hollow,))

    def test_a_negative_price_is_refused(self):
        bad = CommodityPrice("salt", "fake", "NaCl", -5.0, 10.0, "basis", "https://pubs.usgs.gov/x.pdf")
        with pytest.raises(ValueError, match="hollow|> 0|real sourced"):
            validate((bad,))

    def test_an_unsourced_price_is_refused(self):
        # a price with no USGS source URL fails section 10.4's "dated AND sourced".
        unsourced = CommodityPrice("salt", "fake", "NaCl", 50.0, 51.0, "basis", "")
        with pytest.raises(ValueError, match="source URL|sourced"):
            validate((unsourced,))

    def test_an_empty_seed_is_refused_not_vacuously_green(self):
        with pytest.raises(ValueError, match="must not be empty"):
            validate(())

    def test_a_no_primary_source_commodity_cannot_be_fabricated_into_the_seed(self):
        # acetic acid / vinegar / bicarbonate have no primary USGS per-ton price; slipping one in (e.g. from a
        # commercial aggregator) is REFUSED by the validator, not merely discouraged by a comment.
        fabricated = CommodityPrice("vinegar", "acetic acid", "C2H4O2", 527.0, 500.0, "aggregator",
                                    "https://pubs.usgs.gov/x.pdf")
        with pytest.raises(ValueError, match="no primary-source|fabricated"):
            validate((fabricated,))


class TestHonestlyAbsent:
    def test_acetic_acid_and_bicarbonate_are_absent_not_invented(self):
        materials = {r.material.casefold() for r in USGS_COMMODITY_PRICES}
        for absent in ("acetic acid", "vinegar", "sodium bicarbonate", "baking soda"):
            assert absent.casefold() not in materials
            assert absent in UNPRICED_NO_PRIMARY_SOURCE

    def test_soda_ash_is_present_as_the_priced_parent_of_bicarbonate(self):
        # bicarbonate itself has no USGS price; its priced parent commodity (soda ash) IS present, usable only as a
        # labelled proxy -- so the honesty note in the docstring is backed by a real row, not an empty gesture.
        assert any(r.material == "soda ash (natural)" and r.formula == "Na2CO3" for r in USGS_COMMODITY_PRICES)


def test_report_is_self_consistent():
    r = report()
    assert r["hash_matches"] is True
    assert r["priced_forms"] == 9   # +1: DOW-BROMINE-01 added the USGS bromine import unit value
    assert set(r["commodities"]) == {"salt", "soda ash", "lime", "sulfur", "bromine"}
