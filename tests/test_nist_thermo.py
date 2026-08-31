"""NIST WebBook thermochemistry -- proven to read a real page's ΔfH°/S°, refuse a half-sourced one, and
never mistake the glossary's prose for a measurement.

*Ooh yeah, existence is offline pain!* Like :mod:`tests.test_providers`, this parses recorded, VERBATIM
NIST WebBook fixtures (``tests/fixtures/providers/``) -- never the live network. What it pins is exactly
the discipline that makes the thermo autoload safe: an explicit ΔfH°+S° PAIR is required (no entropy, no
record), the AVG row wins when one exists, a flagged extrapolation outlier is skipped, and a compound this
provider cannot resolve stays absent -- never guessed at.
"""
import os
import tempfile
from pathlib import Path

from smartchem.data.autoload import ThermoCache, autoload_thermo
from smartchem.data.providers.nist_thermo import NIST_IDS, parse_condensed_thermo
from smartchem.data.thermo import DEFAULT_THERMO
from smartchem.smiles import parse_smiles

_FIX = Path(__file__).parent / "fixtures" / "providers"

ETHANOL_HTML = (_FIX / "nist_thermo_ethanol.html").read_text()
ACETIC_ACID_HTML = (_FIX / "nist_thermo_aceticacid.html").read_text()

#: A minimal condensed-phase table with a ΔfH°liquid row but no S° row at all -- the "no entropy, no
#: record" case, built by hand rather than trimmed from a fixture so the missing row is unambiguous.
_NO_ENTROPY_SNIPPET = """
<h2 id="Thermo-Condensed">Condensed phase thermochemistry data</h2>
<table class="data" aria-label="One dimensional data"><tr>
<th scope="col">Quantity</th><th scope="col">Value</th><th scope="col">Units</th>
<th scope="col">Method</th><th scope="col">Reference</th><th scope="col">Comment</th>
</tr>
<tr class="exp"><td style="text-align: left;">&#916;<sub>f</sub>H&deg;<sub>liquid</sub></td>
<td class="right-nowrap">-100.0</td><td style="text-align: right;">kJ/mol</td>
<td style="text-align: center;">N/A</td>
<td style="text-align: left;"><a href="#ref-1">Someone, 1999</a></td>
<td style="text-align: left;"><em>ALS</em></td></tr>
</table>
"""


class TestParseCondensedThermo:
    def test_real_ethanol_page_reads_the_avg_dhf_and_the_only_s(self):
        result = parse_condensed_thermo(ETHANOL_HTML)
        assert result is not None
        assert result["s_j_per_mol_k"] == 159.86  # exact, single-sourced value
        assert -278.5 <= result["dhf_kj_per_mol"] <= -274.5  # the AVG row, -276. +/- 2.
        assert result["phase"] == "liquid"

    def test_real_acetic_acid_page_has_no_avg_row_and_skips_the_extrapolation_outlier(self):
        result = parse_condensed_thermo(ACETIC_ACID_HTML)
        assert result is not None
        assert result["s_j_per_mol_k"] == 158.0  # Martin & Andon 1982, NOT the 193.7 extrapolation outlier
        assert result["dhf_kj_per_mol"] == -483.52  # the first (only) experimental row, Steele et al. 1997
        assert result["phase"] == "liquid"

    def test_a_dhf_with_no_entropy_row_is_refused_not_half_recorded(self):
        assert parse_condensed_thermo(_NO_ENTROPY_SNIPPET) is None

    def test_the_symbols_glossary_is_never_mistaken_for_a_measurement(self):
        # The full ethanol page has a "Symbols used in this document" table further down whose S(deg)liquid
        # row's second column is the PROSE "Entropy of liquid at standard conditions", not a number. If the
        # parser ever lost its scope to the Thermo-Condensed table, this prose could get read as an S(deg).
        assert "Entropy of liquid at standard conditions" in ETHANOL_HTML  # the trap really is in the page
        result = parse_condensed_thermo(ETHANOL_HTML)
        assert result is not None
        assert type(result["s_j_per_mol_k"]) is float
        assert result["s_j_per_mol_k"] == 159.86


class TestAutoloadThermo:
    def test_a_fake_fetch_resolves_a_registered_species_to_a_full_record(self):
        ethanol = parse_smiles("CCO")

        def fake_fetch(nist_id: str) -> str:
            assert nist_id == NIST_IDS["ethanol"]
            return ETHANOL_HTML

        with tempfile.TemporaryDirectory() as d:
            cache = ThermoCache.load(os.path.join(d, "c.json"))
            table = autoload_thermo([ethanol], base=DEFAULT_THERMO, fetch=fake_fetch, cache=cache)
        rec = table.for_named("C2H6O", "ethanol")
        assert rec is not None
        assert rec.s_j_per_mol_k == 159.86
        assert -278.5 <= rec.dhf_kj_per_mol <= -274.5
        assert rec.phase == "liquid"

    def test_a_species_with_no_nist_ids_entry_stays_absent(self):
        methanol = parse_smiles("CO")  # registered by name, but NOT in NIST_IDS
        assert "methanol" not in NIST_IDS

        def fake_fetch(nist_id: str) -> str:
            raise AssertionError("should never be called: methanol has no NIST_IDS entry")

        with tempfile.TemporaryDirectory() as d:
            cache = ThermoCache.load(os.path.join(d, "c.json"))
            table = autoload_thermo([methanol], base=DEFAULT_THERMO, fetch=fake_fetch, cache=cache)
        assert table.for_named("CH4O", "methanol") is None
