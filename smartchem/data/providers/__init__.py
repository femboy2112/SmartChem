"""Open-data providers for autoloaded chemical property data -- so a chemist can download and go.

The Experiment Compiler's data layers (stability thresholds for E1, thermochemistry for E3) ship with a
small SOURCED seed and degrade to a loud ``UNKNOWN`` off it.  This subpackage is the *coverage* answer: a
pluggable set of providers that fetch property data from OPEN resources and cache it locally, so the
compiler is useful out of the box on arbitrary chemicals without a chemist hand-injecting every record.

Three providers, one interface (:class:`~smartchem.data.providers.base.PropertyProvider`):

* **PubChem PUG-View** (NIH, public domain) -- broadest coverage of experimental melting/boiling points,
  aggregated from many sources as free text this package parses conservatively.
* **Wikidata** (CC0) -- structured melting/boiling points and enthalpy of vaporisation with source
  citations; cleaner provenance, thinner coverage.
* **Bradley Open Melting Point Dataset** (CC0) -- ~28k melting points from a local CSV (populated by the
  documented fetch script); melting points only.

The discipline is the same as everywhere in this repo, and it is the whole reason autoload is safe:

* **Sourced, never fabricated.**  Every fetched value carries its source and licence.  A value that cannot
  be parsed cleanly is dropped (``None``), never guessed.
* **UNKNOWN is not a default.**  A provider miss returns ``None`` -> the caller renders ``UNKNOWN``.
* **Offline-first, cached.**  Live fetches are cached to a local store, so after the first fetch the
  compiler runs offline; with no network (or ``allow_network=False``) it falls back to the cache and the
  bundled seed.  No API key is ever required.

See :mod:`smartchem.data.autoload` for the cache and the resolution order.
"""
from __future__ import annotations

from .base import PropertyProvider, PropertyRecord
from .bradley import BradleyMeltingPointProvider
from .pubchem import PubChemProvider
from .tempparse import aggregate_kelvin, celsius_to_k, fahrenheit_to_k, parse_temperature_values
from .wikidata import WikidataProvider

__all__ = [
    "PropertyProvider",
    "PropertyRecord",
    "PubChemProvider",
    "WikidataProvider",
    "BradleyMeltingPointProvider",
    "parse_temperature_values",
    "aggregate_kelvin",
    "celsius_to_k",
    "fahrenheit_to_k",
    "default_providers",
]


def default_providers(*, bradley_csv: str | None = None) -> tuple[PropertyProvider, ...]:
    """The standard provider stack, in resolution order: PubChem, Wikidata, then Bradley (if its CSV exists)."""
    providers: list[PropertyProvider] = [PubChemProvider(), WikidataProvider()]
    bradley = BradleyMeltingPointProvider(csv_path=bradley_csv)
    if bradley.available:
        providers.append(bradley)
    return tuple(providers)
