"""Wikidata (CC0) property provider -- structured, cited melting/boiling points + enthalpy of vaporisation.

Wikidata exposes melting point (P2101), boiling point (P2102) and enthalpy of vaporisation (P2116) as
structured quantities with unit QIDs and source references, all under CC0 (fully redistributable).  This
provider runs a SPARQL query and converts by the unit QID -- cleaner provenance than PubChem's free text,
thinner coverage.  As with PubChem, the SPARQL parsing is a pure function tested against a recorded fixture;
the live call is opt-in.  A unit it does not recognise is skipped, never guessed.
"""
from __future__ import annotations

import json

from .base import PropertyProvider, PropertyRecord
from .tempparse import aggregate_kelvin, celsius_to_k, fahrenheit_to_k

__all__ = ["WikidataProvider"]

_SPARQL = "https://query.wikidata.org/sparql"
_SEARCH = "https://www.wikidata.org/w/api.php"
_UA = "smartchem/0.1 (chemistry education; open-data autoload)"

#: Temperature unit QIDs Wikidata uses for P2101/P2102.  A unit outside this set is skipped (not guessed).
_TEMP_UNIT = {"Q25267": "C", "Q42289": "F", "Q11579": "K"}
#: Energy-per-mole unit QIDs for P2116 (enthalpy of vaporisation) mapped to a kJ/mol scale factor.  Only
#: units confidently known are listed; any other unit is SKIPPED (dHvap -> None -> UNKNOWN), never guessed.
_ENERGY_PER_MOL_KJ = {"Q752197": 1.0}  # Q752197 = kilojoule per mole


def _qid_suffix(uri: str | None) -> str | None:
    if not uri:
        return None
    return uri.rsplit("/", 1)[-1]


def _temp_to_k(value: float, unit_qid: str | None) -> float | None:
    kind = _TEMP_UNIT.get(unit_qid or "")
    if kind == "C":
        return celsius_to_k(value)
    if kind == "F":
        return fahrenheit_to_k(value)
    if kind == "K":
        return value
    return None  # unknown unit -> skip, never guess


def record_from_sparql(sparql_json: str, qid: str | None = None) -> PropertyRecord:
    """Build a :class:`PropertyRecord` from a Wikidata SPARQL JSON result (the pure, testable core)."""
    try:
        bindings = json.loads(sparql_json)["results"]["bindings"]
    except (ValueError, TypeError, KeyError):
        return PropertyRecord()

    mp_k: list[tuple[float, float]] = []
    bp_k: list[tuple[float, float]] = []
    hvap_vals: list[float] = []
    for b in bindings:
        for var, bucket in (("mp", mp_k), ("bp", bp_k)):
            if var in b:
                try:
                    val = float(b[var]["value"])
                except (ValueError, KeyError):
                    continue
                k = _temp_to_k(val, _qid_suffix(b.get(f"{var}Unit", {}).get("value")))
                if k is not None:
                    bucket.append((k, k))
        if "hvap" in b:
            try:
                hv = float(b["hvap"]["value"])
            except (ValueError, KeyError):
                hv = None
            unit = _qid_suffix(b.get("hvapUnit", {}).get("value"))
            if hv is not None and unit in _ENERGY_PER_MOL_KJ:
                hvap_vals.append(hv * _ENERGY_PER_MOL_KJ[unit])

    melting = aggregate_kelvin(mp_k)
    boiling = aggregate_kelvin(bp_k)
    dhvap = (sum(hvap_vals) / len(hvap_vals)) if hvap_vals else None
    sources: dict[str, str] = {}
    tag = f"Wikidata {qid}" if qid else "Wikidata"
    if melting is not None:
        sources["melting"] = f"{tag} P2101 (CC0)"
    if boiling is not None:
        sources["boiling"] = f"{tag} P2102 (CC0)"
    if dhvap is not None:
        sources["dhvap"] = f"{tag} P2116 (CC0)"
    return PropertyRecord(
        melting=melting, boiling=boiling, dhvap_kj_per_mol=dhvap, sources=sources,
        licence="CC0 (Wikidata)", source_name="Wikidata",
    )


_QUERY_TEMPLATE = """SELECT ?mp ?mpUnit ?bp ?bpUnit ?hvap ?hvapUnit WHERE {{
  OPTIONAL {{ wd:{qid} p:P2101 ?ms. ?ms ps:P2101 ?mp. OPTIONAL{{?ms psv:P2101 ?mv. ?mv wikibase:quantityUnit ?mpUnit.}} }}
  OPTIONAL {{ wd:{qid} p:P2102 ?bs. ?bs ps:P2102 ?bp. OPTIONAL{{?bs psv:P2102 ?bv. ?bv wikibase:quantityUnit ?bpUnit.}} }}
  OPTIONAL {{ wd:{qid} p:P2116 ?hs. ?hs ps:P2116 ?hvap. OPTIONAL{{?hs psv:P2116 ?hv. ?hv wikibase:quantityUnit ?hvapUnit.}} }}
}} LIMIT 40"""


class WikidataProvider(PropertyProvider):
    name = "Wikidata"
    licence = "CC0 (Wikidata)"

    def __init__(self, *, timeout: float = 15.0) -> None:
        self.timeout = timeout

    def _get(self, url: str) -> str:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return resp.read().decode("utf-8")

    def _qid_for(self, name: str) -> str | None:
        import urllib.parse
        params = urllib.parse.urlencode({
            "action": "wbsearchentities", "search": name, "language": "en",
            "type": "item", "format": "json", "limit": 1,
        })
        data = json.loads(self._get(f"{_SEARCH}?{params}"))
        hits = data.get("search", [])
        return hits[0]["id"] if hits else None

    def fetch(self, *, identifier: str, formula: str | None = None) -> PropertyRecord | None:
        if not identifier:
            return None
        try:
            import urllib.parse
            qid = self._qid_for(identifier)  # a name resolves; a SMILES search simply returns no item
            if qid is None:
                return None
            query = _QUERY_TEMPLATE.format(qid=qid)
            url = f"{_SPARQL}?format=json&query={urllib.parse.quote(query)}"
            record = record_from_sparql(self._get(url), qid)
            return None if record.is_empty else record
        except Exception:  # noqa: BLE001 -- an unreachable provider is a miss, not a crash
            return None
