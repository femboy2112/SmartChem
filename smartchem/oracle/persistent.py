"""
Make the expensive knowledge outlive the process that paid for it.

``CachingOracle`` prices each distinct species once *per run* under a deterministic,
context-free oracle assumption; this is memoisation, not a functor law. On one measured
search workload it was worth 33.5x. But the table dies with the
process, so the cost of knowing a species is paid again on every restart -- and for the
species this project actually cares about, that cost is not small:

    C3H8         2515.9 s      HF/cc-pVTZ+d/geom
    CH3OC2H5     3444.2 s      HF/cc-pVTZ+d/geom

Forty minutes to re-learn something already known is not a performance detail; it is what
stops anybody iterating on a model that needs those numbers. This module persists the
table on the narrower justification that one immutable calculation specification should
produce one reusable species result.

THE CACHING IS TRIVIAL. THE KEY IS THE WHOLE PROBLEM.
-----------------------------------------------------
A memory cache lives inside one oracle object, so the tier is implicit in *which object
you are asking* and a bare species key is sound. A file does not have that protection. It
outlives the oracle, and a key of species-alone would happily serve an HF/cc-pVDZ number
to a CCSD(T)/cbs(TZ,QZ) question -- silently, with the wrong ``method`` string riding
along, producing a result that is wrong by an amount nobody would think to look for.

So the key carries the currently modeled calculation provenance: method, basis,
tight-d and geometry policies, size cap, environment, backend version and implementation
hash. That is what ``_fingerprint`` is for, and it is the part
worth testing. A test that only checks "the same species hits" would pass on a cache that
is catastrophically wrong.

This is not a complete semantic fingerprint. External files, transitive dependency changes,
hardware/numerical nondeterminism or undeclared mutable state can still change a result. New
oracle inputs must be declared in ``calculation_spec``. Each record repeats the exact
fingerprint and oracle identity and carries a SHA-256 integrity checksum; the checksum
detects accidental/torn edits but is not authentication against a malicious writer.

And because a key can be right by construction and still be wrong after somebody edits
the constructor, every read is cross-checked against those record fields and validated by
``Estimate`` before use. A mismatch is discarded as a miss and counted in ``rejected``.
Result method labels are deliberately not required to equal the wrapper's name: legitimate
backends add protocol suffixes such as ``/geom`` and composite heuristic labels.

ON REPORTING ``seconds`` HONESTLY
---------------------------------
A restored entry keeps the ``seconds`` it originally cost, not zero. Those two numbers
answer different questions and this project should not conflate them:

    seconds          what it cost to KNOW this. Unchanged by caching, and the right
                     number for "what did this model cost to build".
    saved_seconds    what this run did not have to spend. Reported by the cache itself.

Zeroing ``seconds`` on a hit would make a warm run look free, which is a claim about the
cost of the science rather than the cost of the invocation. The note on every restored
estimate says plainly where it came from, so nothing has to be inferred.

FAILURE IS ALWAYS A MISS, NEVER AN ERROR AND NEVER A GUESS
----------------------------------------------------------
A corrupt file, an unreadable directory, a record from a future schema, or a stored value
that will not parse is intended to degrade to "not cached". The cache can make this project
slower. Correctness still depends on complete keys, deterministic oracle semantics and the
validation described above.
"""
from __future__ import annotations

import json
import hashlib
import inspect
import math
import os
import tempfile
from collections.abc import Mapping as MappingABC
from contextlib import contextmanager
from dataclasses import fields, is_dataclass
from numbers import Real
from pathlib import Path

try:  # POSIX CI and scientific workstations; fallback keeps correctness within one writer
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None

from ..category import Molecule
from .base import BaseOracle, Estimate

#: Bumped when the record layout changes. A file from a different schema is ignored
#: wholesale rather than half-read, because a partially-understood cache is the one
#: failure mode here that could produce a wrong number instead of a slow one.
SCHEMA_VERSION = 4


def _jsonable(value):
    """A deterministic, delimiter-free representation of calculation settings.

    Unsupported objects are rejected instead of being reduced to a possibly non-unique
    ``repr``. A persistent cache may miss safely; it may never merge two calculation specs
    merely because their display strings happen to match.
    """
    # Every supported Python type receives an explicit envelope. Without it, ``[1]`` and
    # ``(1,)`` (or a list and a set with the same members) serialize identically even when
    # an oracle deliberately gives those settings different semantics.
    if value is None:
        return {"type": "none"}
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if isinstance(value, int):
        return {"type": "int", "value": value}
    if isinstance(value, str):
        return {"type": "str", "value": value}
    if isinstance(value, float):
        return {"type": "float", "value": value if math.isfinite(value) else repr(value)}
    if is_dataclass(value):
        return {
            "type": "dataclass",
            "class": f"{type(value).__module__}.{type(value).__qualname__}",
            "fields": _jsonable({
                member.name: getattr(value, member.name) for member in fields(value)
            }),
        }
    if isinstance(value, MappingABC):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("calculation-spec mapping keys must be strings")
        return {
            "type": "mapping",
            "items": [[key, _jsonable(value[key])] for key in sorted(value)],
        }
    if isinstance(value, tuple):
        return {"type": "tuple", "items": [_jsonable(item) for item in value]}
    if isinstance(value, list):
        return {"type": "list", "items": [_jsonable(item) for item in value]}
    if isinstance(value, (set, frozenset)):
        encoded = [_jsonable(item) for item in value]
        return {
            "type": "frozenset" if isinstance(value, frozenset) else "set",
            "items": sorted(encoded, key=lambda item: json.dumps(item, sort_keys=True)),
        }
    raise TypeError(
        "calculation spec contains unsupported value "
        f"{type(value).__module__}.{type(value).__qualname__}; override "
        "calculation_spec() with immutable JSON-like data"
    )


def species_signature(molecule: Molecule) -> str:
    """
    A deterministic string identifying a species, for use as a file-backed key.

    Every field of ``Molecule`` appears, because every field can change the energy: the
    atoms, the bond graph (sorted, since a frozenset has no order to rely on), the charge,
    and the internal state that ``#22`` added for carriers and excited species. Omitting
    ``state`` would merge a ground-state and an excited species into one entry, which is
    the sort of collision that produces a plausible number rather than an obvious crash.

    This is NOT canonicalisation -- the caller canonicalises first where it can. This
    function's only job is to turn a specific structure into a specific string, reversibly
    enough that two equal molecules always agree and two unequal ones never do.
    """
    payload = {
        "atoms": list(molecule.atoms),
        "bonds": [[b.i, b.j, b.order] for b in sorted(molecule.bonds)],
        "charge": molecule.charge,
        "state": molecule.state,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _chain_source_sha256(oracle) -> str:
    """
    Hash the implementation of EVERY oracle in the delegation chain, outermost first.

    Hashing only ``type(oracle)``'s module was a silent-wrong-answer path, and it was armed
    by the ordinary way this project composes oracles. ``PersistentCache(CachingOracle(
    PySCFOracle(...)))`` handed ``CachingOracle`` to this function, so the digest covered
    ``caching.py`` and never ``pyscf_oracle.py``. ``calculation_spec`` delegates correctly
    and carries the inner settings, but settings are not source: ``_model_inputs_sha256``
    is a deliberate WHITELIST of constants, so anything not on it -- ``conv_tol``,
    ``max_cycle``, ``_DESCENT_STEP_ANGSTROM``, the CBS extrapolation algebra, adding frozen
    core or density fitting to ``_parts`` -- changed every number the oracle produced and
    changed the cache key not at all.

    MEASURED, on a copy of the tree with ``mycc.frozen = 1`` added to ``_parts``::

        pristine   bare d87102f11f384b24   wrapped 34e5368ef7bf3d4c
        + frozen   bare 2ebcc929b73d639e   wrapped 34e5368ef7bf3d4c   <-- unchanged

    The bare oracle invalidated correctly; the wrapped one served the pre-edit number with
    ``rejected=0`` and no warning. That is the one defect this project refuses.

    Walking ``.inner`` is the fix rather than special-casing ``CachingOracle`` because the
    hazard is composition itself: any future wrapper reintroduces it otherwise. Cycles are
    guarded by identity, not by depth, so a self-referential chain terminates instead of
    recursing forever.
    """
    digest = hashlib.sha256()
    seen_ids: set[int] = set()
    seen_names: set[str] = set()
    node = oracle
    while node is not None and id(node) not in seen_ids:
        seen_ids.add(id(node))
        target = inspect.getmodule(type(node)) or type(node)
        name = getattr(target, "__name__", None) or type(node).__qualname__
        if name not in seen_names:
            seen_names.add(name)
            try:
                source = inspect.getsource(target).encode("utf-8")
            except (OSError, TypeError):
                source = b"unavailable"
            digest.update(name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(hashlib.sha256(source).digest())
        node = getattr(node, "inner", None)
    return digest.hexdigest()


def _fingerprint(oracle) -> str:
    """
    A string identifying the TIER, so a cached number is only ever served to a question
    asked at the same tier.

    The oracle supplies an explicit ``calculation_spec`` when possible. The conservative
    ``BaseOracle`` default snapshots every instance field: mutable telemetry can cause a
    harmless miss, while an omitted result-driving field could cause a wrong hit.
    """
    spec_provider = getattr(oracle, "calculation_spec", None)
    raw_spec = spec_provider() if callable(spec_provider) else dict(vars(oracle))
    settings = _jsonable(raw_spec)
    source_hash = _chain_source_sha256(oracle)
    descriptor = {
        "class": f"{type(oracle).__module__}.{type(oracle).__qualname__}",
        "name": getattr(oracle, "name", ""),
        "settings": settings,
        "implementation_sha256": source_hash,
        "cache_protocol": SCHEMA_VERSION,
    }
    encoded = json.dumps(descriptor, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _record_checksum(record: dict) -> str:
    """Detect accidental/torn record edits; integrity check, not authentication."""
    encoded = json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class PersistentCache(BaseOracle):
    """
    Wraps any oracle and memoises ``energy`` to a JSON file, keyed by (tier, species).

    Transparent in the same sense ``CachingOracle`` is: same answers, reported scales,
    named sensitivities, and ``None`` refusals. Refusals are *not* persisted by default
    because the current
    backend API does not distinguish stable Unsupported from retryable solver Failure.
    Stable callers may opt in with ``cache_refusals=True``.

    Writes merge under an inter-process file lock and replace atomically, so concurrent
    workers do not lose one another's completed calculations and an interrupted writer
    cannot leave a truncated file.
    """

    def __init__(
        self,
        inner,
        path: str | os.PathLike,
        autosave: bool = True,
        cache_refusals: bool = False,
    ):
        if type(autosave) is not bool:
            raise TypeError("autosave must be a boolean")
        if type(cache_refusals) is not bool:
            raise TypeError("cache_refusals must be a boolean")
        self.inner = inner
        self.name = inner.name
        self.nominal_accuracy_ev = getattr(inner, "nominal_accuracy_ev", float("nan"))
        self.path = Path(path)
        self.autosave = autosave
        self.cache_refusals = cache_refusals
        self.fingerprint = _fingerprint(inner)

        self.hits = 0
        self.misses = 0
        #: species too large to canonicalise, keyed as spelled -- correct, possibly missing
        self.uncanonicalised = 0
        #: entries discarded by the cross-check. Any value above zero is a bug worth
        #: chasing, not a tuning parameter: it means a key matched a record it should not.
        self.rejected = 0
        #: seconds this run did not have to spend, summed from the records it restored
        self.saved_seconds = 0.0
        #: set when the file could not be read; the run continues uncached
        self.load_error: str | None = None
        #: set when persistence failed; computed results are still returned from memory
        self.save_error: str | None = None
        #: Never replace a file whose schema/content this version cannot safely merge.
        self._write_disabled = False

        self._entries: dict[str, dict] = {}
        self._dirty: set[str] = set()
        self._load()

    # -- the file ------------------------------------------------------------------
    @property
    def domain(self):
        """
        The wrapped oracle's domain, unchanged. A cache alters latency, never coverage.

        Delegated rather than inherited: ``BaseOracle``'s default claims nothing, so a
        wrapper that forgot to forward this would silently erase a real declared boundary
        the moment an oracle was cached -- the same shape as the ``nominal_accuracy_ev``
        forwarding in ``__init__``.
        """
        from .base import domain_of

        return domain_of(self.inner)

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text())
            if raw.get("version") != SCHEMA_VERSION:
                self.load_error = (f"schema {raw.get('version')!r} is not "
                                   f"{SCHEMA_VERSION}; ignoring the file")
                self._write_disabled = True
                return
            entries = raw["entries"]
            if not isinstance(entries, dict):
                raise TypeError("entries is not an object")
            self._entries = entries
        except Exception as error:                      # noqa: BLE001 -- see module docs
            # Deliberately broad. Every way this can fail has the same correct response,
            # and enumerating them would only risk missing one and turning a slow run
            # into a crashed one.
            self.load_error = f"{type(error).__name__}: {error}"
            self._entries = {}
            self._write_disabled = True

    def save(self) -> bool:
        """Merge dirty entries under a lock and replace atomically; return success."""
        if self._write_disabled:
            return False
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._write_lock():
                merged: dict[str, dict] = {}
                if self.path.exists():
                    raw = json.loads(self.path.read_text())
                    if (raw.get("version") != SCHEMA_VERSION
                            or not isinstance(raw.get("entries"), dict)):
                        self._write_disabled = True
                        self.save_error = "existing cache became unreadable or changed schema"
                        return False
                    merged.update(raw["entries"])
                # Merge only entries this writer computed. Replaying its entire load-time
                # snapshot could overwrite a record another writer repaired meanwhile.
                merged.update({key: self._entries[key] for key in self._dirty})
                payload = {"version": SCHEMA_VERSION, "entries": merged}
                handle, temporary = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
                try:
                    with os.fdopen(handle, "w") as stream:
                        json.dump(payload, stream, indent=1, sort_keys=True)
                    os.replace(temporary, self.path)
                except BaseException:
                    Path(temporary).unlink(missing_ok=True)
                    raise
                self._entries = merged
                self._dirty.clear()
            self.save_error = None
            return True
        except Exception as error:  # persistence may cost time, never the computed answer
            self.save_error = f"{type(error).__name__}: {error}"
            return False

    @contextmanager
    def _write_lock(self):
        lock_path = self.path.with_name(self.path.name + ".lock")
        with lock_path.open("a+") as stream:
            if fcntl is not None:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    # -- the key -------------------------------------------------------------------
    def _key(self, molecule: Molecule) -> tuple[str, Molecule]:
        try:
            canonical = molecule.canonical()
        except NotImplementedError:
            self.uncanonicalised += 1
            canonical = molecule
        return f"{self.fingerprint}||{species_signature(canonical)}", canonical

    # -- the oracle ----------------------------------------------------------------
    def energy(self, molecule: Molecule) -> Estimate | None:
        key, canonical = self._key(molecule)
        record = self._entries.get(key)
        if record is not None:
            # A valid cached refusal is an optimization policy, not calculation data.
            # The default policy deliberately asks again because Unsupported and transient
            # Failure are not yet separate result types.
            if (not self.cache_refusals and isinstance(record, dict)
                    and record.get("declined") is True):
                record = None
            else:
                restored = self._restore(record, key)
                if restored is not False:
                    self.hits += 1
                    if restored is not None:
                        self.saved_seconds += restored.seconds
                    return restored
                # Integrity/identity validation failed or the record would not parse: absent;
                # recompute, so a bad entry costs time rather than correctness
                self.rejected += 1

        self.misses += 1
        result = self.inner.energy(canonical)
        if result is not None or self.cache_refusals:
            self._entries[key] = self._record(result, key)
            self._dirty.add(key)
            if self.autosave:
                self.save()
        return result

    def _record(self, estimate: Estimate | None, key: str) -> dict:
        if estimate is None:
            record = {
                "declined": True,
                "oracle_name": self.name,
                "fingerprint": self.fingerprint,
                "cache_key": key,
            }
        else:
            record = {
                "declined": False,
                "oracle_name": self.name,
                "value_ev": estimate.value_ev,
                "uncertainty_ev": estimate.uncertainty_ev,
                "method": estimate.method,
                "seconds": estimate.seconds,
                "notes": estimate.notes,
                "systematic_ev": estimate.systematic_ev,
                "methods": sorted(estimate.methods or ()),
                "systematic_terms": [list(item) for item in (estimate.systematic_terms or ())],
                "fingerprint": self.fingerprint,
                "cache_key": key,
            }
        record["checksum"] = _record_checksum(record)
        return record

    def _restore(self, record: dict, expected_key: str) -> Estimate | None | bool:
        """
        The stored estimate, or ``False`` meaning "do not trust this record".

        ``False`` rather than ``None`` because ``None`` is a legitimate cached value -- it
        is a refusal, and refusals are worth caching. Conflating "the oracle declined" with
        "this entry is unusable" would turn a corrupt record into a permanent refusal.
        """
        try:
            if not isinstance(record, dict):
                return False
            checksum = record.get("checksum")
            unsigned = {key: value for key, value in record.items() if key != "checksum"}
            if not isinstance(checksum, str) or checksum != _record_checksum(unsigned):
                return False
            if record.get("fingerprint") != self.fingerprint:
                return False
            if record.get("cache_key") != expected_key:
                return False
            if record.get("oracle_name") != self.name:
                return False
            declined = record.get("declined")
            if type(declined) is not bool:
                return False
            if declined:
                return None
            stored = record["method"]
            # Method labels need only be non-empty. Oracle identity and full calculation
            # fingerprint are cross-checked exactly above; legitimate result labels may add
            # suffixes such as /geom or describe a composite heuristic method.
            if not isinstance(stored, str) or not stored:
                return False
            raw_methods = record.get("methods", [stored])
            raw_terms = record.get("systematic_terms", [])
            if (not isinstance(raw_methods, list)
                    or any(not isinstance(item, str) or not item for item in raw_methods)
                    or not isinstance(raw_terms, list)
                    or any(not isinstance(item, list) or len(item) != 2 for item in raw_terms)):
                return False
            canonical_method = "+".join(sorted(set(raw_methods))) if raw_methods else "exact"
            if stored != canonical_method:
                return False
            for source, coefficient in raw_terms:
                if (not isinstance(source, str) or not source
                        or isinstance(coefficient, bool)
                        or not isinstance(coefficient, Real)):
                    return False
            numeric_fields = {
                field: record.get(field, 0.0 if field == "systematic_ev" else None)
                for field in ("value_ev", "uncertainty_ev", "seconds", "systematic_ev")
            }
            if any(
                value is None or isinstance(value, bool) or not isinstance(value, Real)
                for value in numeric_fields.values()
            ):
                return False
            notes = record["notes"]
            if not isinstance(notes, str):
                return False
            estimate = Estimate(
                value_ev=float(numeric_fields["value_ev"]),
                uncertainty_ev=float(numeric_fields["uncertainty_ev"]),
                method=stored,
                seconds=float(numeric_fields["seconds"]),
                notes=(f"{notes}; restored from persistent cache "
                       f"{self.path.name}").lstrip("; "),
                systematic_ev=float(numeric_fields["systematic_ev"]),
                methods=frozenset(raw_methods),
                systematic_terms=tuple(
                    (source, float(coefficient))
                    for source, coefficient in raw_terms
                ),
            )
            if estimate.systematic_ev != float(numeric_fields["systematic_ev"]):
                return False
            return estimate
        except (AttributeError, KeyError, OverflowError, TypeError, ValueError):
            return False

    # -- reporting -----------------------------------------------------------------
    @property
    def distinct_species(self) -> int:
        return len(self._entries)

    def certificate(self) -> str:
        """What the cache actually saved, for a run to report rather than assume."""
        asked = self.hits + self.misses
        saving = asked / self.misses if self.misses else float("inf")
        note = f", {self.rejected} REJECTED" if self.rejected else ""
        broken = f", file unreadable ({self.load_error})" if self.load_error else ""
        unsaved = f", save failed ({self.save_error})" if self.save_error else ""
        return (f"{self.name} via {self.path.name}: {asked} requests, {self.misses} priced,"
                f" {self.hits} restored, {self.distinct_species} on disk, "
                f"{saving:.2f}x saved, {self.saved_seconds:.1f} s not re-spent"
                f"{note}{broken}{unsaved}")

    def __repr__(self) -> str:
        return f"PersistentCache({self.inner!r}, {self.path}, {self.distinct_species})"
