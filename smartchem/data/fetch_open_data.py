"""Fetch bulk open chemical data into the local cache -- the one-time "download and go" step.

The compiler already works offline on the bundled seed and enriches its cache from PubChem/Wikidata on the
first networked run (see :mod:`smartchem.data.autoload`).  This script adds the BULK offline source that is
too big to fetch one compound at a time:

    python -m smartchem.data.fetch_open_data bradley       # ~28k melting points (CC0), to the data dir
    python -m smartchem.data.fetch_open_data warm --smiles "CC(=O)O" "CCO"   # pre-fill the cache (SMILES)
    python -m smartchem.data.fetch_open_data warm --name aspirin "acetic acid"   # ... or by NAME
    python -m smartchem.data.fetch_open_data warm --name water ethanol --offline # registry-only, no network

The Bradley Open Melting Point Dataset ships as an XLSX; this converts it to the CSV the Bradley provider
reads, using only the standard library (no new dependency -- XLSX is zipped XML).  Everything downloaded is
CC0.  Nothing here fabricates data; it only relocates open datasets into the cache.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import zipfile
from xml.etree import ElementTree as ET

from .providers.bradley import default_bradley_csv

#: The Jean-Claude Bradley Open Melting Point Dataset (CC0), figshare DOI 10.6084/m9.figshare.1031637.
BRADLEY_XLSX_URL = "https://ndownloader.figshare.com/files/1503990"
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_UA = "smartchem/0.1 (chemistry education; open-data fetch)"


def _xlsx_first_sheet_rows(xlsx_bytes: bytes) -> list[list[str]]:
    """Read the first worksheet of an XLSX into rows of strings, using only the standard library."""
    z = zipfile.ZipFile(io.BytesIO(xlsx_bytes))
    shared: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(f"{_NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{_NS}t")))
    sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))

    def cell_value(c: ET.Element) -> str:
        v = c.find(f"{_NS}v")
        if v is None or v.text is None:
            return ""
        return shared[int(v.text)] if c.get("t") == "s" else v.text

    return [[cell_value(c) for c in row.findall(f"{_NS}c")] for row in sheet.findall(f".//{_NS}row")]


def fetch_bradley(dest: str | None = None, url: str = BRADLEY_XLSX_URL) -> str:
    """Download the Bradley XLSX and convert its first sheet to a CSV the provider reads.  Returns the path."""
    import urllib.request
    dest = dest or default_bradley_csv()
    print(f"downloading Bradley Open Melting Point Dataset (CC0) from {url} ...", flush=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": _UA}), timeout=60) as r:
        raw = r.read()
    rows = _xlsx_first_sheet_rows(raw)
    if not rows:
        raise SystemExit("downloaded workbook had no rows; check the --url")
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    with open(dest, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(rows)
    print(f"wrote {len(rows) - 1} data rows to {dest} (headers: {', '.join(rows[0])})", flush=True)
    return dest


def _resolve_to_molecule(ident: str, *, allow_network: bool):
    """Resolve one identifier (a SMILES OR a chemical name) to ``(molecule, name_hint)``, or ``(None, ident)``.

    Order: parse as a SMILES; else the offline structure registry (:func:`structure_by_name`); else, when
    the network is allowed, a live PubChem name->SMILES resolution.  The cache is keyed by STRUCTURAL
    identity, so a name must become a structure before it can be warmed -- this is what closes the
    "name-only warming not wired" gap.  Returns ``(None, ident)`` on a miss; never a fabricated structure.
    """
    from ..smiles import SmilesError, parse_smiles
    from ..structure import structure_by_name
    try:
        return parse_smiles(ident), ident              # a SMILES
    except SmilesError:
        pass
    named = structure_by_name(ident)                   # a registered name (offline)
    if named is not None:
        return named.molecule, ident
    if allow_network:                                  # a live name->structure resolution
        from .providers.pubchem import PubChemProvider
        smiles = PubChemProvider().resolve_smiles(ident)
        if smiles:
            try:
                return parse_smiles(smiles), ident
            except SmilesError:
                pass
    return None, ident


def warm_cache(identifiers: list[str], *, allow_network: bool = True) -> None:
    """Pre-populate the cache for a list of SMILES and/or names, so later runs are offline.

    Names are resolved to structures via the registry (offline) or PubChem (when ``allow_network``); the
    structural key is what the cache stores.  A name that resolves nowhere is a loud skip, never a guess.
    """
    from .autoload import autoload_stability
    mols = []
    hints = {}
    for ident in identifiers:
        m, name = _resolve_to_molecule(ident, allow_network=allow_network)
        if m is None:
            reason = ("not a SMILES, not a registered name, and PubChem could not resolve it"
                      if allow_network else "not a SMILES and not a registered name (offline)")
            print(f"  (skipping {ident!r}: {reason})", flush=True)
            continue
        mols.append(m)
        hints[m] = name
    if not mols:
        print("nothing to warm.", flush=True)
        return
    table = autoload_stability(mols, identifiers=hints, allow_network=allow_network)
    covered = sum(1 for m in mols if table.for_formula(_fkey(m)) is not None)
    print(f"warmed cache for {covered}/{len(mols)} compound(s).", flush=True)


def _fkey(molecule) -> str:
    from ..decompiler import Formula
    return repr(Formula.of(molecule.formula, molecule.charge))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="smartchem.data.fetch_open_data", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bradley", help="download the Bradley Open MP Dataset (CC0) to the cache")
    b.add_argument("--url", default=BRADLEY_XLSX_URL)
    b.add_argument("--dest", default=None)
    w = sub.add_parser("warm", help="pre-fill the cache for given SMILES and/or names")
    w.add_argument("--smiles", nargs="+", default=[], help="SMILES strings to warm the cache for")
    w.add_argument("--name", nargs="+", default=[],
                   help="chemical names to warm (resolved via the registry, or PubChem unless --offline)")
    w.add_argument("--offline", action="store_true",
                   help="registry-only name resolution and no network fetch")
    args = parser.parse_args(argv)
    if args.cmd == "bradley":
        fetch_bradley(args.dest, args.url)
    elif args.cmd == "warm":
        warm_cache([*args.smiles, *args.name], allow_network=not args.offline)
    return 0


if __name__ == "__main__":
    sys.exit(main())
