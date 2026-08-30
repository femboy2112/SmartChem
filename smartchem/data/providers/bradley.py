"""Bradley Open Melting Point Dataset (CC0) provider -- ~28k melting points from a local CSV.

The Jean-Claude Bradley Open Melting Point Dataset is a large, openly-licensed (CC0) collection of curated
melting points.  It is not bundled into this repo (it is big, and kept where the fetch script puts it); this
provider reads it from a local CSV path.  With no CSV present the provider is simply *unavailable* -- a clean
absence, not an error -- so the compiler still runs on the seed + the other providers.

Populate it once with ``python -m smartchem.data.fetch_open_data bradley`` (see that module), or point
``SMARTCHEM_BRADLEY_CSV`` at a copy you already have.  Melting points only.
"""
from __future__ import annotations

import csv
import os
from statistics import median

from ...conditions import Interval
from .base import PropertyProvider, PropertyRecord
from .tempparse import celsius_to_k

__all__ = ["BradleyMeltingPointProvider", "default_bradley_csv"]

#: Header names (lower-cased) this loader recognises for the compound name and the melting point in Celsius.
_NAME_KEYS = ("name", "compound", "chemical name", "iupac_name")
_MP_C_KEYS = ("mpc", "mp_c", "mp", "meltingpoint", "melting point (c)", "mp (c)", "mp_celsius")


def default_bradley_csv() -> str:
    """The default CSV location: ``$SMARTCHEM_BRADLEY_CSV`` or ``<data dir>/bradley_open_mp.csv``."""
    env = os.environ.get("SMARTCHEM_BRADLEY_CSV")
    if env:
        return env
    base = os.environ.get("SMARTCHEM_DATA_DIR") or os.path.join(
        os.path.expanduser("~"), ".cache", "smartchem"
    )
    return os.path.join(base, "bradley_open_mp.csv")


class BradleyMeltingPointProvider(PropertyProvider):
    name = "Bradley Open Melting Point Dataset"
    licence = "CC0 (Bradley Open Melting Point Dataset)"

    def __init__(self, *, csv_path: str | None = None) -> None:
        self.csv_path = csv_path or default_bradley_csv()
        self._index: dict[str, float] | None = None

    @property
    def available(self) -> bool:
        return os.path.isfile(self.csv_path)

    def _load(self) -> dict[str, float]:
        if self._index is not None:
            return self._index
        collected: dict[str, list[float]] = {}
        if self.available:
            with open(self.csv_path, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                headers = {(h or "").strip().lower(): h for h in (reader.fieldnames or [])}
                name_col = next((headers[k] for k in _NAME_KEYS if k in headers), None)
                mp_col = next((headers[k] for k in _MP_C_KEYS if k in headers), None)
                donotuse_col = headers.get("donotuse")  # Bradley flags dubious rows; honour it
                if name_col and mp_col:
                    for row in reader:
                        if donotuse_col and (row.get(donotuse_col) or "").strip():
                            continue  # a row the dataset itself marks unusable
                        nm = (row.get(name_col) or "").strip().lower()
                        raw = (row.get(mp_col) or "").strip()
                        if not nm or not raw:
                            continue
                        try:
                            collected.setdefault(nm, []).append(float(raw))
                        except ValueError:
                            continue  # a non-numeric cell is skipped, never guessed
        # a name can appear in many rows (many sources): take the MEDIAN, robust to duplicates/outliers
        self._index = {nm: median(vals) for nm, vals in collected.items()}
        return self._index

    def fetch(self, *, identifier: str, formula: str | None = None) -> PropertyRecord | None:
        if not identifier:
            return None
        mp_c = self._load().get(identifier.strip().lower())  # Bradley is name-keyed; a SMILES simply misses
        if mp_c is None:
            return None
        k = celsius_to_k(mp_c)
        return PropertyRecord(
            melting=Interval(k, k, "K"),
            sources={"melting": f"Bradley Open Melting Point Dataset (CC0): {mp_c} C"},
            licence=self.licence, source_name="Bradley Open MP Dataset",
        )
