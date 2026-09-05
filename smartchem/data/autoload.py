"""Autoload: resolve stability data from the seed, a local cache, and open providers -- download and go.

This is the *coverage* layer.  It composes the bundled sourced seed, a local on-disk cache, and the open-data
providers into one :class:`~smartchem.data.stability.StabilityTable` for a set of molecules, in a fixed
resolution order:

1. **the seed / caller table** (`base`) -- hand-curated, highest quality; if it covers a compound, it wins
   and nothing is fetched;
2. **the local cache** -- a previously-fetched record, so after the first fetch the compiler runs offline;
3. **the providers** (PubChem, Wikidata, Bradley) -- fetched, merged field-wise, and written to the cache;
4. **nothing** -- the compound is simply absent -> the caller renders ``UNKNOWN``.

Everything fetched carries its source and licence, a value that cannot be sourced stays absent, and network
is optional (``allow_network=False``, or no reachable provider, uses only the seed + cache).  No API key is
ever required.  This is how a chemist downloads the project and *goes*: the seed works offline immediately,
and the first run with network enriches the cache for everything after.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from ..category import Molecule
from ..conditions import Interval
from ..contracts import canonical_digest
from ..decompiler import Formula
from ..decompiler_review import molecule_name
from .providers.base import PropertyProvider, PropertyRecord
from .stability import DEFAULT_STABILITY, StabilityRef, StabilityTable
from .thermo import ThermoRef, ThermoTable

__all__ = [
    "smartchem_data_dir",
    "StabilityCache",
    "autoload_stability",
    "merge_records",
    "ThermoCache",
    "autoload_thermo",
]


def smartchem_data_dir() -> str:
    """The data/cache directory: ``$SMARTCHEM_DATA_DIR`` or ``~/.cache/smartchem``."""
    return os.environ.get("SMARTCHEM_DATA_DIR") or os.path.join(
        os.path.expanduser("~"), ".cache", "smartchem"
    )


def _formula_str(molecule: Molecule) -> str:
    return repr(Formula.of(molecule.formula, molecule.charge))


def _struct_key(molecule: Molecule) -> str:
    """A stable structural identity for the cache -- independent of how a caller identified the molecule."""
    try:
        return canonical_digest(molecule.canonical())
    except NotImplementedError:
        return "asgiven:" + canonical_digest(molecule)


def _interval_to_json(iv: Interval | None) -> list | None:
    return None if iv is None else [iv.lo, iv.hi, iv.unit]


def _interval_from_json(v: object) -> Interval | None:
    if not v:
        return None
    lo, hi, unit = v  # type: ignore[misc]
    return Interval(lo, hi, unit)


def _ref_to_json(ref: StabilityRef) -> dict:
    return {
        "formula": ref.formula,
        "name": ref.name,
        "melting": _interval_to_json(ref.melting),
        "boiling": _interval_to_json(ref.boiling),
        "decomposition_onset": _interval_to_json(ref.decomposition_onset),
        "isolable": ref.isolable,
        "provenance": ref.provenance,
        "dhvap_kj_per_mol": ref.dhvap_kj_per_mol,
    }


def _ref_from_json(d: dict) -> StabilityRef:
    return StabilityRef(
        formula=d["formula"], name=d["name"],
        melting=_interval_from_json(d.get("melting")),
        boiling=_interval_from_json(d.get("boiling")),
        decomposition_onset=_interval_from_json(d.get("decomposition_onset")),
        isolable=bool(d.get("isolable", True)),
        provenance=d["provenance"],
        dhvap_kj_per_mol=d.get("dhvap_kj_per_mol"),
    )


@dataclass
class StabilityCache:
    """A local on-disk cache of fetched :class:`StabilityRef` records, keyed by STRUCTURAL identity.

    Keying by structure (not by the query string a caller happened to use) makes the cache stable across
    runs: whether a molecule was identified by name once and by SMILES the next time, it resolves to the
    same cached record.
    """

    path: str
    _by_key: dict[str, StabilityRef]

    @classmethod
    def load(cls, path: str | None = None) -> "StabilityCache":
        path = path or os.path.join(smartchem_data_dir(), "stability_cache.json")
        by_key: dict[str, StabilityRef] = {}
        try:
            with open(path, encoding="utf-8") as fh:
                for row in json.load(fh):
                    by_key[row["key"]] = _ref_from_json(row)
        except (OSError, ValueError, KeyError, TypeError):
            by_key = {}  # a missing or corrupt cache is simply empty, never a crash
        return cls(path, by_key)

    def get(self, struct_key: str) -> StabilityRef | None:
        return self._by_key.get(struct_key)

    def put(self, struct_key: str, ref: StabilityRef) -> None:
        self._by_key[struct_key] = ref

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        rows = [{"key": key, **_ref_to_json(ref)} for key, ref in self._by_key.items()]
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=2)

    def records(self) -> tuple[StabilityRef, ...]:
        return tuple(self._by_key.values())


def merge_records(records: list[PropertyRecord | None]) -> PropertyRecord:
    """Merge several providers' partial records field-wise (first non-None wins), accumulating provenance."""
    present = [r for r in records if r is not None and not r.is_empty]
    if not present:
        return PropertyRecord()
    merged: dict[str, object] = {}
    sources: dict[str, str] = {}
    licences: list[str] = []
    names: list[str] = []
    for field_name in ("melting", "boiling", "decomposition", "dhvap_kj_per_mol", "isolable"):
        for r in present:
            value = getattr(r, field_name)
            if value is not None and field_name not in merged:
                merged[field_name] = value
                src_key = "dhvap" if field_name == "dhvap_kj_per_mol" else field_name
                if src_key in r.sources:
                    sources[field_name] = r.sources[src_key]
    for r in present:
        if r.licence and r.licence not in licences:
            licences.append(r.licence)
        if r.source_name and r.source_name not in names:
            names.append(r.source_name)
    return PropertyRecord(
        melting=merged.get("melting"), boiling=merged.get("boiling"),
        decomposition=merged.get("decomposition"), dhvap_kj_per_mol=merged.get("dhvap_kj_per_mol"),
        isolable=merged.get("isolable"), sources=sources,
        licence="; ".join(licences), source_name=", ".join(names),
    )


def _ref_from_merged(formula: str, name: str, merged: PropertyRecord) -> StabilityRef | None:
    """Turn a merged :class:`PropertyRecord` into a :class:`StabilityRef`, or ``None`` if it sourced nothing."""
    if merged.is_empty:
        return None
    prov_bits = [f"{k}: {v}" for k, v in sorted(merged.sources.items())]
    provenance = "; ".join(prov_bits) or merged.source_name or "autoloaded"
    if merged.licence:
        provenance += f" [licence: {merged.licence}]"
    # isolability is not something these providers source; a compound with phase-transition data is treated
    # as isolable by default (the not-isolable flag is a special sourced fact, e.g. ketene, in the seed).
    isolable = True if merged.isolable is None else bool(merged.isolable)
    return StabilityRef(
        formula=formula, name=name,
        melting=merged.melting, boiling=merged.boiling, decomposition_onset=merged.decomposition,
        isolable=isolable, provenance=provenance, dhvap_kj_per_mol=merged.dhvap_kj_per_mol,
    )


def autoload_stability(
    molecules,
    *,
    identifiers: "dict[Molecule, str] | None" = None,
    providers: tuple[PropertyProvider, ...] | None = None,
    cache: StabilityCache | None = None,
    allow_network: bool = True,
    base: StabilityTable = DEFAULT_STABILITY,
) -> StabilityTable:
    """Resolve stability records for ``molecules`` from seed -> cache -> providers, returning an extended table.

    ``identifiers`` optionally maps a molecule to the query string a provider should use -- a name
    (``"aspirin"``) or a SMILES the caller already has (``"CC(=O)O"``).  When absent for a molecule, the
    registered structure name is used; a molecule with neither a hint nor a registered name is not fetched
    (there is nothing to query it by) and stays ``UNKNOWN`` -- never guessed.

    ``providers`` defaults to the standard stack (PubChem, Wikidata, Bradley) only when ``allow_network`` is
    set; pass ``allow_network=False`` (or ``providers=()``) to use the seed + cache alone.  Fetched records
    are written to ``cache`` (a shared on-disk store), so the second run is offline.  Never fabricates: a
    compound no source covers is simply absent from the returned table (-> ``UNKNOWN`` downstream).
    """
    identifiers = identifiers or {}
    if providers is None:
        if allow_network:
            from .providers import default_providers
            providers = default_providers()
        else:
            providers = ()
    cache = cache if cache is not None else StabilityCache.load()

    new_refs: list[StabilityRef] = []
    fetched_refs: list[StabilityRef] = []  # SNAPSHOT-13.2: only the LIVE-fetched refs (step 3), for the dated stamp
    seen: set[str] = set()
    dirty = False
    for m in molecules:
        struct_key = _struct_key(m)
        if struct_key in seen:
            continue
        seen.add(struct_key)
        formula = _formula_str(m)
        name = molecule_name(m)
        identifier = identifiers.get(m) or name
        key_name = name or identifier or formula
        # 1) the seed/caller table wins -- do not re-fetch what is already curated
        if base.for_named(formula, key_name) is not None or (
            name is not None and base.for_named(formula, name) is not None
        ):
            continue
        # 2) the local cache (keyed by structure, so it is stable across runs and identifiers)
        cached = cache.get(struct_key)
        if cached is not None:
            new_refs.append(cached)
            continue
        # 3) the providers (only if we have something to query by and network is allowed)
        if allow_network and providers and identifier:
            merged = merge_records([p.fetch(identifier=identifier, formula=formula) for p in providers])
            ref = _ref_from_merged(formula, key_name, merged)
            if ref is not None:
                cache.put(struct_key, ref)
                new_refs.append(ref)
                fetched_refs.append(ref)
                dirty = True
    if dirty:
        cache.save()
    table = base.with_records(*new_refs)
    if fetched_refs:
        # SNAPSHOT-13.2 / G8: a LIVE fetch happened, so stamp the returned provider data with a dated snapshot
        # (which providers, how many records, a deterministic content id, and the wall-clock).  A pure seed/cache
        # read never reaches here, so a reproducible offline run is never stamped with a spurious fetch time.
        from dataclasses import replace
        from datetime import datetime, timezone
        from .provider_snapshot import provider_snapshot
        snap = provider_snapshot(
            tuple(r.digest for r in fetched_refs),
            tuple(type(p).__name__ for p in providers),
            fetched_at=datetime.now(timezone.utc).isoformat(),
            allow_network=allow_network,
        )
        table = replace(table, provider_snapshot=snap)
    return table


def _thermo_ref_to_json(ref: ThermoRef) -> dict:
    return {
        "formula": ref.formula,
        "name": ref.name,
        "dhf_kj_per_mol": ref.dhf_kj_per_mol,
        "s_j_per_mol_k": ref.s_j_per_mol_k,
        "phase": ref.phase,
        "provenance": ref.provenance,
    }


def _thermo_ref_from_json(d: dict) -> ThermoRef:
    return ThermoRef(
        formula=d["formula"], name=d["name"],
        dhf_kj_per_mol=d["dhf_kj_per_mol"], s_j_per_mol_k=d["s_j_per_mol_k"],
        phase=d["phase"], provenance=d["provenance"],
    )


@dataclass
class ThermoCache:
    """A local on-disk cache of fetched :class:`ThermoRef` records, keyed by STRUCTURAL identity.

    The thermo path's own errand, right next to :class:`StabilityCache` -- SAME structural-key idiom (a
    molecule warmed by name today is served by structure tomorrow, whatever string a caller looks it up
    with), same "a missing or corrupt cache is simply empty" discipline. Two tables, two caches, one habit.
    """

    path: str
    _by_key: dict[str, ThermoRef]

    @classmethod
    def load(cls, path: str | None = None) -> "ThermoCache":
        path = path or os.path.join(smartchem_data_dir(), "thermo_cache.json")
        by_key: dict[str, ThermoRef] = {}
        try:
            with open(path, encoding="utf-8") as fh:
                for row in json.load(fh):
                    by_key[row["key"]] = _thermo_ref_from_json(row)
        except (OSError, ValueError, KeyError, TypeError):
            by_key = {}  # a missing or corrupt cache is simply empty, never a crash
        return cls(path, by_key)

    def get(self, struct_key: str) -> ThermoRef | None:
        return self._by_key.get(struct_key)

    def put(self, struct_key: str, ref: ThermoRef) -> None:
        self._by_key[struct_key] = ref

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        rows = [{"key": key, **_thermo_ref_to_json(ref)} for key, ref in self._by_key.items()]
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=2)

    def records(self) -> tuple[ThermoRef, ...]:
        return tuple(self._by_key.values())


def _registry_cas(name: str) -> str | None:
    """The CAS registry number for a registered species name, or ``None`` -- the key the NIST CAS->ID
    convention needs.  The structure registry is imported lazily so :mod:`smartchem.data.autoload` stays
    free of an import cycle (structure -> parser -> ... would otherwise close a loop at module load)."""
    from ..structure import structure_by_name

    s = structure_by_name(name)
    cas = getattr(s, "cas", "") if s is not None else ""
    return cas or None


def autoload_thermo(
    molecules,
    *,
    base: ThermoTable | None = None,
    fetch=None,
    cache: ThermoCache | None = None,
) -> ThermoTable:
    """Resolve ΔfH°/S° thermo records for ``molecules`` from seed -> cache -> the NIST WebBook.

    *Look at me, a SECOND autoload for a SECOND table!* :class:`ThermoTable` cannot carry mp/bp/dHvap and
    :class:`~.providers.base.PropertyRecord` cannot carry ΔfH°/S° -- so this is a separate path, not a
    branch bolted onto :func:`autoload_stability`, mirroring its exact resolution order one level over:

    1. **the seed/caller table** (``base``, default :func:`~.thermo_extended.extended_thermo`) -- wins if it
       already resolves the species by its registered ``(formula, name)``, and nothing is fetched;
    2. **the local cache** (keyed by STRUCTURE, so it is stable across runs and identifiers);
    3. **the NIST WebBook** -- for a species resolvable by its registered name OR by its registry CAS number
       (via :func:`~.providers.nist_thermo.resolve_nist_id`'s CAS->WebBook-ID convention), fetched then
       CONFIRMED (a CAS-constructed id is trusted only if the fetched page actually carries that CAS -- an
       identity guard against a convention miss); ``fetch`` defaults to
       :func:`~.providers.nist_thermo.fetch_nist_html` and is overridable (a fake, for offline tests);
    4. **nothing** -- an unresolved species, an unreachable page, or a page missing ΔfH° or S° all leave the
       species simply absent from the returned table (``UNKNOWN`` downstream), never a fabricated record.
    """
    from .providers.nist_thermo import fetch_nist_html, parse_condensed_thermo, resolve_nist_id
    from .thermo_extended import extended_thermo

    base = base if base is not None else extended_thermo()
    fetch = fetch if fetch is not None else fetch_nist_html
    cache = cache if cache is not None else ThermoCache.load()

    new_refs: list[ThermoRef] = []
    seen: set[str] = set()
    dirty = False
    for m in molecules:
        struct_key = _struct_key(m)
        if struct_key in seen:
            continue
        seen.add(struct_key)
        formula = _formula_str(m)
        name = molecule_name(m)
        # 1) the seed/caller table wins -- do not re-fetch what is already curated
        if name is not None and base.for_named(formula, name) is not None:
            continue
        # 2) the local cache (keyed by structure, so it is stable across runs and identifiers)
        cached = cache.get(struct_key)
        if cached is not None:
            new_refs.append(cached)
            continue
        # 3) the NIST WebBook -- reachable by a REGISTERED name OR by the registry's CAS number (the
        #    CAS->WebBook-ID convention); an unnamed/unresolvable species has nothing to query it by and
        #    stays absent, exactly like autoload_stability's identifier gate
        if name is None:
            continue
        cas = _registry_cas(name)
        nist_id = resolve_nist_id(name)
        confirm_cas = None
        if nist_id is None and cas is not None:
            nist_id = resolve_nist_id(cas)  # the CAS convention -- only a CANDIDATE, confirmed just below
            confirm_cas = cas
        if nist_id is None:
            continue
        page = fetch(nist_id)
        if page is None:
            continue
        # identity guard: a CAS-constructed id must serve the RIGHT species -- require the requested CAS to
        # appear on the fetched page, so a convention miss can never silently attribute another compound here
        if confirm_cas is not None and confirm_cas not in page:
            continue
        parsed = parse_condensed_thermo(page)
        if parsed is None:
            continue  # a page missing ΔfH° or S° is a miss, not a half-fabricated record
        ref = ThermoRef(
            formula=formula, name=name,
            dhf_kj_per_mol=parsed["dhf_kj_per_mol"], s_j_per_mol_k=parsed["s_j_per_mol_k"],
            phase=parsed["phase"],
            provenance=f"{parsed['dhf_provenance']} | {parsed['s_provenance']}",
        )
        cache.put(struct_key, ref)
        new_refs.append(ref)
        dirty = True
    if dirty:
        cache.save()
    return base.with_records(*new_refs)
