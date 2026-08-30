# Autoloaded open chemical data — download and go

The Experiment Compiler needs physical property data (melting/boiling points and enthalpy of vaporisation
for E1's composability + Clausius–Clapeyron; formation enthalpies for E3's heat). It ships with a small
**sourced seed** that works offline immediately, and it can **autoload** more from open resources and cache
it locally, so an arbitrary chemical is covered without hand-entering data.

## How it resolves (never fabricates)

For each species, in order:

1. **seed / caller table** — hand-curated, highest quality; wins if it covers the compound.
2. **local cache** — a previously-fetched record (so the second run is offline).
3. **providers** — fetched from the open sources below, merged field-wise, written to the cache.
4. **nothing** — the compound is simply absent → the compiler reports `UNKNOWN`, loudly. Never a guess.

Network is optional. With no network (or `allow_network=False`) only the seed + cache are used. No API key
is ever required. Every fetched value carries its source and licence.

## The sources (all open)

| Provider | Data | Licence |
|---|---|---|
| **PubChem** (NIH, PUG-View) | experimental melting/boiling points (aggregated free text, parsed conservatively) | public domain |
| **Wikidata** | melting/boiling point + enthalpy of vaporisation (structured, cited) | CC0 |
| **Bradley Open Melting Point Dataset** | ~28k melting points (local CSV) | CC0 |

## Using it

Most users never call this directly — the CLI does it:

```
python -m smartchem.experiment "CC(=O)Nc1ccc(O)cc1" \
    --have "Nc1ccc(O)cc1" --reagents "O" "CC(=O)O" "CC(=O)OC(=O)C" \
    --max-temp 1473 --max-pressure 1.5
```

That enumerates routes, autoloads sourced data for every species (cached), fits them to the bench, and
prints the top drafted procedure. Add `--offline` to use only the seed + cache.

Bulk melting-point coverage (one-time, ~28k rows, CC0):

```
python -m smartchem.data.fetch_open_data bradley          # downloads + converts to the cache
python -m smartchem.data.fetch_open_data warm --smiles "CC(=O)O" "CCO"   # pre-fill the cache (SMILES)
python -m smartchem.data.fetch_open_data warm --name aspirin "acetic acid"   # ... or by NAME
python -m smartchem.data.fetch_open_data warm --name water ethanol --offline # registry-only, no network
```

Warming needs a **structure** — the cache is keyed by structural identity — so a name is resolved to one
first: the offline structure registry (any compound it carries, e.g. `water`, `paracetamol`,
`acetaminophen`), then PubChem's name→SMILES endpoint (unless `--offline`). A name that resolves nowhere is
a loud skip, never a guess.

## Adding a provider (the honest extension point)

The stack is a plain `PropertyProvider` interface (`base.py`): implement `fetch(*, identifier, formula=None)`
returning a `PropertyRecord` or `None`, add it to `default_providers`, and it participates in the
seed→cache→providers→UNKNOWN flow. The discipline is strict and non-negotiable: the parsing of a response is
a **pure function tested against a REAL recorded fixture** (`tests/fixtures/providers/`, captured live once),
separate from the network call. More open sources (NIST-linked thermochemistry, ChEBI) fit here directly —
they are not yet shipped because adding one means capturing its real response into a fixture rather than
guessing its schema, and this project never fabricates a data contract it hasn't seen.

Programmatically:

```python
from smartchem.data.autoload import autoload_stability
table = autoload_stability(species, identifiers={mol: "CC(=O)O"})   # name or SMILES per molecule
comp = verify_composability(route, stability=table)
```

The cache lives at `$SMARTCHEM_DATA_DIR` (default `~/.cache/smartchem/`).
