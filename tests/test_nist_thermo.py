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
from smartchem.data.providers.nist_thermo import NIST_IDS, parse_condensed_thermo, resolve_nist_id
from smartchem.data.thermo import DEFAULT_THERMO
from smartchem.smiles import parse_smiles

_FIX = Path(__file__).parent / "fixtures" / "providers"

ETHANOL_HTML = (_FIX / "nist_thermo_ethanol.html").read_text()
ACETIC_ACID_HTML = (_FIX / "nist_thermo_aceticacid.html").read_text()
METHANOL_HTML = (_FIX / "nist_thermo_methanol.html").read_text()
PARACETAMOL_HTML = (_FIX / "nist_thermo_paracetamol.html").read_text()
CUMENE_HTML = (_FIX / "nist_thermo_cumene.html").read_text()

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

    def test_a_registered_species_absent_from_nist_ids_is_reached_via_its_cas(self):
        # Methanol is registered (name + CAS 67-56-1) but NOT one of the two hand-verified NIST_IDS names.
        # The CAS->WebBook-ID convention (67-56-1 -> C67561) now reaches it -- the widened arbitrary-target
        # reach, and NOT a new hardcode (methanol is still absent from NIST_IDS).
        methanol = parse_smiles("CO")
        assert "methanol" not in NIST_IDS
        assert resolve_nist_id("67-56-1") == "C67561"

        def fake_fetch(nist_id: str) -> str:
            assert nist_id == "C67561"  # resolved via CAS, not a NIST_IDS name
            return METHANOL_HTML

        with tempfile.TemporaryDirectory() as d:
            cache = ThermoCache.load(os.path.join(d, "c.json"))
            table = autoload_thermo([methanol], base=DEFAULT_THERMO, fetch=fake_fetch, cache=cache)
        rec = table.for_named("CH4O", "methanol")
        assert rec is not None
        assert rec.s_j_per_mol_k == 127.19  # Carlson & Westrum 1971, read off the real captured page
        assert rec.phase == "liquid"

    def test_the_identity_guard_refuses_a_page_that_does_not_carry_the_requested_cas(self):
        # If a CAS-constructed id ever served the WRONG species, the fetched page would not carry the CAS we
        # asked for.  The guard must refuse (stay absent) rather than attribute another compound's thermo.
        methanol = parse_smiles("CO")
        assert "67-56-1" not in ETHANOL_HTML  # ethanol's page carries 64-17-5, not methanol's CAS

        def wrong_species_fetch(nist_id: str) -> str:
            return ETHANOL_HTML  # a real page, but for the wrong compound

        with tempfile.TemporaryDirectory() as d:
            cache = ThermoCache.load(os.path.join(d, "c.json"))
            table = autoload_thermo([methanol], base=DEFAULT_THERMO, fetch=wrong_species_fetch, cache=cache)
        assert table.for_named("CH4O", "methanol") is None  # mis-attribution refused, not silently accepted

    def test_a_species_with_no_registered_name_stays_absent_and_is_never_fetched(self):
        # No registered name => nothing to look up an id or a CAS by => absent, and fetch is never called.
        unnamed = parse_smiles("CCCCCCCCCC")  # decane: not in the structure registry

        def fake_fetch(nist_id: str) -> str:
            raise AssertionError("should never be called: an unnamed species has no id to query")

        with tempfile.TemporaryDirectory() as d:
            cache = ThermoCache.load(os.path.join(d, "c.json"))
            table = autoload_thermo([unnamed], base=DEFAULT_THERMO, fetch=fake_fetch, cache=cache)
        assert table.for_formula("C10H22") is None  # nothing added; the fail-closed gate held


class TestResolveNistId:
    def test_a_hand_verified_name_resolves(self):
        assert resolve_nist_id("ethanol") == NIST_IDS["ethanol"] == "C64175"

    def test_a_cas_number_resolves_by_the_webbook_convention(self):
        assert resolve_nist_id("64-17-5") == "C64175"     # ethanol
        assert resolve_nist_id("103-90-2") == "C103902"   # acetaminophen
        assert resolve_nist_id("98-82-8") == "C98828"     # cumene

    def test_neither_a_name_nor_a_cas_is_none_never_guessed(self):
        assert resolve_nist_id("definitely not a cas") is None
        assert resolve_nist_id("") is None
        assert resolve_nist_id("C64175") is None  # an id is neither a known name nor a CAS -> not re-resolved

    def test_the_cas_convention_is_confirmed_against_real_captured_pages(self):
        # The "C"+CAS-without-dashes convention is VERIFIED, not assumed: for each real captured page the
        # constructed id matches AND the page proves its identity by carrying that CAS.
        for cas, cid, html_text in [
            ("98-82-8", "C98828", CUMENE_HTML),
            ("103-90-2", "C103902", PARACETAMOL_HTML),
            ("67-56-1", "C67561", METHANOL_HTML),
        ]:
            assert resolve_nist_id(cas) == cid
            assert cas in html_text  # identity: the constructed id really served THIS species

    def test_the_real_pages_full_pair_vs_fail_closed(self):
        # cumene's real page yields a complete pair; the drug's real page correctly REFUSES (no S(cr)).
        cumene = parse_condensed_thermo(CUMENE_HTML)
        assert cumene is not None and cumene["dhf_kj_per_mol"] == -41.2 and cumene["phase"] == "liquid"
        assert parse_condensed_thermo(PARACETAMOL_HTML) is None  # fail-closed: the paracetamol entropy wall
