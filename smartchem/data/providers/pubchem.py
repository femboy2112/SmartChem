"""PubChem (NIH) property provider -- broadest coverage, aggregated free-text mp/bp, public domain.

PubChem's experimental melting/boiling points live in PUG-View annotations as free text aggregated from many
sources.  This provider fetches the annotation, extracts every string value, and hands them to the
conservative :mod:`~smartchem.data.providers.tempparse` aggregator -- so a value is only ever a consensus of
sourced numbers, never a guess.  The network call and the parsing are SEPARATE, so the parsing is tested
against recorded fixtures offline; the live call is exercised only by an opt-in smoke.
"""
from __future__ import annotations

import json

from .base import PropertyProvider, PropertyRecord
from .tempparse import aggregate_kelvin, parse_temperature_values

__all__ = ["PubChemProvider", "smiles_from_property_json"]

_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest"
_UA = "smartchem/0.1 (chemistry education; open-data autoload)"


def smiles_from_property_json(text: str) -> str | None:
    """Extract a SMILES from a PUG-REST property response (the pure, testable core).

    PubChem's property key is ``SMILES`` (it renamed the former ``CanonicalSMILES`` in 2025);
    ``ConnectivitySMILES`` (the former ``IsomericSMILES``) and the historical names are accepted as
    fallbacks, so the parser survives the endpoint's own churn.  Returns the first non-empty string, or
    ``None`` -- never a fabricated structure.
    """
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        return None
    props = obj.get("PropertyTable", {}).get("Properties", [])
    if not isinstance(props, list) or not props or not isinstance(props[0], dict):
        return None
    first = props[0]
    for key in ("SMILES", "CanonicalSMILES", "ConnectivitySMILES", "IsomericSMILES"):
        val = first.get(key)
        if isinstance(val, str) and val:
            return val
    return None


def _extract_strings(obj: object) -> list[str]:
    """Every ``String`` value anywhere in a PUG-View annotation JSON object."""
    out: list[str] = []

    def walk(x: object) -> None:
        if isinstance(x, dict):
            s = x.get("String")
            if isinstance(s, str):
                out.append(s)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for y in x:
                walk(y)

    walk(obj)
    return out


def _interval_from_annotation(annotation_json: str):
    """Aggregate a PUG-View mp/bp annotation JSON string into one Kelvin :class:`Interval`, or ``None``."""
    try:
        obj = json.loads(annotation_json)
    except (ValueError, TypeError):
        return None
    intervals: list[tuple[float, float]] = []
    for s in _extract_strings(obj):
        intervals.extend(parse_temperature_values(s))
    return aggregate_kelvin(intervals)


def record_from_annotations(mp_json: str | None, bp_json: str | None, cid: int | None) -> PropertyRecord:
    """Build a :class:`PropertyRecord` from raw mp/bp PUG-View annotation JSON (the pure, testable core)."""
    melting = _interval_from_annotation(mp_json) if mp_json else None
    boiling = _interval_from_annotation(bp_json) if bp_json else None
    sources: dict[str, str] = {}
    tag = f"PubChem CID {cid}" if cid is not None else "PubChem"
    if melting is not None:
        sources["melting"] = f"{tag} experimental melting point (aggregated, PUG-View)"
    if boiling is not None:
        sources["boiling"] = f"{tag} experimental boiling point (aggregated, PUG-View)"
    return PropertyRecord(
        melting=melting, boiling=boiling, sources=sources,
        licence="public domain (U.S. NIH / PubChem)", source_name="PubChem",
    )


class PubChemProvider(PropertyProvider):
    name = "PubChem"
    licence = "public domain (U.S. NIH / PubChem)"

    def __init__(self, *, timeout: float = 12.0) -> None:
        self.timeout = timeout

    def _get(self, url: str) -> str:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return resp.read().decode("utf-8")

    def _cid_by(self, namespace: str, value: str) -> int | None:
        import urllib.parse
        url = f"{_BASE}/pug/compound/{namespace}/{urllib.parse.quote(value, safe='')}/cids/JSON"
        data = json.loads(self._get(url))
        cids = data.get("IdentifierList", {}).get("CID", [])
        return int(cids[0]) if cids else None

    def resolve_smiles(self, name: str) -> str | None:
        """Resolve a chemical NAME to a SMILES via PUG-REST (network), or ``None`` on a miss.

        The parsing is factored into :func:`smiles_from_property_json` (tested offline against a recorded
        response); this method is the thin live call, which degrades to ``None`` on any error.
        """
        if not name:
            return None
        import urllib.parse
        url = (
            f"{_BASE}/pug/compound/name/{urllib.parse.quote(name, safe='')}"
            f"/property/SMILES,ConnectivitySMILES/JSON"
        )
        try:
            return smiles_from_property_json(self._get(url))
        except Exception:  # noqa: BLE001 -- an unreachable/404 name is a miss, not a crash
            return None

    def _cid_for(self, identifier: str) -> int | None:
        """Resolve a CID by NAME first, then by SMILES -- so an arbitrary structure is still found."""
        for namespace in ("name", "smiles"):
            try:
                cid = self._cid_by(namespace, identifier)
            except Exception:  # noqa: BLE001 -- a 404/400 for one namespace just means try the next
                cid = None
            if cid is not None:
                return cid
        return None

    def fetch(self, *, identifier: str, formula: str | None = None) -> PropertyRecord | None:
        if not identifier:
            return None
        try:
            cid = self._cid_for(identifier)
            if cid is None:
                return None
            mp = self._annotation(cid, "Melting+Point")
            bp = self._annotation(cid, "Boiling+Point")
            record = record_from_annotations(mp, bp, cid)
            return None if record.is_empty else record
        except Exception:  # noqa: BLE001 -- an unreachable/erroring provider is a miss, not a crash
            return None

    def _annotation(self, cid: int, heading: str) -> str | None:
        try:
            return self._get(f"{_BASE}/pug_view/data/compound/{cid}/JSON?heading={heading}")
        except Exception:  # noqa: BLE001
            return None
