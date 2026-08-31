"""NIST Chemistry WebBook thermochemistry provider -- condensed-phase ΔfH°/S°, read never fabricated.

*Ooh, a SEPARATE errand from the other providers, and a Meeseeks respects that!* PubChem/Wikidata/Bradley
feed :class:`~.base.PropertyRecord` (melting/boiling/dHvap) -- a shape that structurally has no slot for a
standard formation enthalpy or a standard molar entropy.  So this module does not try to squeeze ΔfH°/S°
into that record; it returns its own small dict, and :func:`~smartchem.data.autoload.autoload_thermo` turns
a hit into a :class:`~smartchem.data.thermo.ThermoRef` for a SEPARATE :class:`~smartchem.data.thermo.ThermoTable`
-- mirroring the stability autoload's seed -> cache -> provider layering one level over, for the DERIVED
thermo grade instead of stability.

The parser is a PURE function over the raw HTML (:func:`parse_condensed_thermo`), tested against real,
verbatim-captured NIST WebBook pages -- never the live network in the committed suite.  It enforces the
same "no entropy, no record" discipline as :mod:`smartchem.data.thermo`: ΔG needs BOTH ΔfH° and S°, so a
page that only has one of the two yields ``None``, never a half-fabricated record.
"""
from __future__ import annotations

import html
import re

__all__ = ["parse_condensed_thermo", "fetch_nist_html", "NIST_IDS"]

_UA = "smartchem/0.1 (chemistry education; open-data autoload)"

#: The credit line every parsed value's provenance carries, alongside the specific measurement it names.
_NIST_TAG = "NIST Chemistry WebBook (public domain), Mask=2"

#: The condensed-phase data table sits right after this heading; scoping to it is what keeps the parser
#: away from the "Symbols used in this document" glossary table further down the same page (that table has
#: no ``aria-label="One dimensional data"`` at all, so this scope excludes it structurally, not by luck).
_TABLE_RE = re.compile(
    r'<h2 id="Thermo-Condensed">.*?'
    r'<table[^>]*aria-label="One dimensional data"[^>]*>(?P<body>.*?)</table>',
    re.DOTALL,
)
_ROW_RE = re.compile(r"<tr(?P<attrs>[^>]*)>(?P<body>.*?)</tr>", re.DOTALL)
_CELL_RE = re.compile(r"<td[^>]*>(?P<cell>.*?)</td>", re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")

#: A condensed-phase ΔfH° quantity cell, e.g. "ΔfH°liquid" (the <sub> tags collapse once tags are
#: stripped, exactly as the recipe describes).  Only liquid/solid are handled -- the two condensed phases
#: this table tabulates; a gas-phase ΔfH° row (a different section entirely) never matches.
_DHF_RE = re.compile(r"^ΔfH°(?P<phase>liquid|solid)$")
#: A condensed-phase S° quantity cell, e.g. "S°liquid".
_S_RE = re.compile(r"^S°(?P<phase>liquid|solid)$")


def _cell_text(cell_html: str) -> str:
    """Tags stripped, entities unescaped, whitespace trimmed -- one cell's plain-text content."""
    return html.unescape(_TAG_RE.sub("", cell_html)).strip()


def _parse_number(value_text: str) -> float | None:
    """The number BEFORE any '±' in a value cell (``"-276. ± 2."`` -> ``-276.0``), or ``None`` if it is not
    a number at all -- the defense that keeps a stray prose cell (e.g. the glossary's definitions, should
    one ever leak past the table scope) from being silently treated as a measurement."""
    head = value_text.split("±", 1)[0].strip().rstrip(".")
    try:
        return float(head)
    except ValueError:
        return None


def _provenance(reference_text: str, comment_text: str) -> str:
    """"Author, year" from the Reference cell, or (for an AVG row, whose Reference is literally "N/A") the
    Comment cell's "Average of N values" note instead -- either way, never a bare, unattributed number."""
    who = reference_text if reference_text and reference_text != "N/A" else comment_text
    who = who or reference_text or "unattributed"
    return f"{who}; {_NIST_TAG}"


def parse_condensed_thermo(html_text: str) -> dict | None:
    """Read ΔfH° and S° (298.15 K, condensed phase) off a NIST WebBook page, or ``None`` if either is absent.

    Existence is pain, and so is a half-sourced thermo record -- ΔG needs BOTH ΔfH° and S°, so this refuses
    (returns ``None``) rather than hand back one without the other.  Per compound:

    * ΔfH°: the AVG row (``<tr class="cal">``, e.g. ethanol's "Average of 6 values") wins if the page has
      one; otherwise the FIRST experimental row (``<tr class="exp">``) in table order (acetic acid has no
      AVG row, so its single Steele/Chirico 1997 row is taken).
    * S°: the FIRST row in table order -- which is also how a flagged extrapolation outlier (acetic acid's
      second S° row, 193.7 J/mol/K, Parks & Kelley 1925, explicitly marked "Extrapolation below 90 K" in
      its own comment) gets skipped without this parser needing to understand what an extrapolation is.

    Returns ``{"dhf_kj_per_mol", "s_j_per_mol_k", "phase", "dhf_provenance", "s_provenance"}`` for whichever
    condensed phase (liquid or solid) actually has a complete ΔfH°+S° pair, or ``None``.
    """
    section = _TABLE_RE.search(html_text)
    if section is None:
        return None
    table_body = section.group("body")

    dhf_avg: dict[str, tuple[float, str]] = {}
    dhf_first_exp: dict[str, tuple[float, str]] = {}
    s_first: dict[str, tuple[float, str]] = {}

    for row in _ROW_RE.finditer(table_body):
        cells = _CELL_RE.findall(row.group("body"))
        if len(cells) != 6:
            continue  # a <th> header row (or anything else not shaped like a data row) -- skip, never guess
        quantity = _cell_text(cells[0])
        value = _parse_number(_cell_text(cells[1]))
        if value is None:
            continue  # a non-numeric value cell is never guessed at
        reference_text = _cell_text(cells[4])
        comment_text = _cell_text(cells[5])
        provenance = _provenance(reference_text, comment_text)

        dhf_m = _DHF_RE.match(quantity)
        if dhf_m is not None:
            phase = dhf_m.group("phase")
            if 'class="cal"' in row.group("attrs"):
                dhf_avg.setdefault(phase, (value, provenance))
            else:
                dhf_first_exp.setdefault(phase, (value, provenance))
            continue

        s_m = _S_RE.match(quantity)
        if s_m is not None:
            s_first.setdefault(s_m.group("phase"), (value, provenance))

    for phase in ("liquid", "solid"):  # the condensed phase actually present in the fixtures at hand
        dhf = dhf_avg.get(phase) or dhf_first_exp.get(phase)
        s = s_first.get(phase)
        if dhf is not None and s is not None:
            dhf_value, dhf_provenance = dhf
            s_value, s_provenance = s
            return {
                "dhf_kj_per_mol": dhf_value,
                "s_j_per_mol_k": s_value,
                "phase": phase,
                "dhf_provenance": dhf_provenance,
                "s_provenance": s_provenance,
            }
    return None  # no entropy, no record (or no formation enthalpy at all) -- refuse, never fabricate


def fetch_nist_html(nist_id: str) -> str | None:
    """Thin live fetch of a NIST WebBook compound page, or ``None`` on ANY error -- never raises.

    Mirrors :meth:`~.pubchem.PubChemProvider._get`/:meth:`~.wikidata.WikidataProvider._get`: an unreachable
    page, a timeout, a 404 -- all of it degrades to ``None`` (a miss), so a caller falls back to the cache
    or the seed rather than crashing.  ``Mask=2`` is the condensed-phase-thermochemistry section of the page.
    """
    import urllib.request

    url = f"https://webbook.nist.gov/cgi/cbook.cgi?ID={nist_id}&Units=SI&Mask=2"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            return resp.read().decode("utf-8")
    except Exception:  # noqa: BLE001 -- an unreachable page is a miss, not a crash
        return None


#: Species resolvable by their registered common name (matches :func:`~smartchem.decompiler_review.molecule_name`)
#: to a NIST WebBook compound ID.  Small and hand-verified by design, exactly like the other providers'
#: documented coverage limits (see e.g. :mod:`.bradley`'s CSV-backed seed): a name absent here is NOT
#: resolved, never guessed at.  FUTURE EXTENSION POINT: NIST does not expose the clean public search-by-CAS
#: API that PubChem/Wikidata do, so a general CAS-number -> NIST-ID resolver is future work, not built here.
NIST_IDS: dict[str, str] = {
    "ethanol": "C64175",
    "acetic acid": "C64197",
}
