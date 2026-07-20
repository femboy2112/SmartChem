"""
Make the expensive knowledge outlive the process that paid for it.

``CachingOracle`` prices each distinct species once *per run*. That is the functor law
used as a lookup table, and within a search it is worth 33.5x. But the table dies with the
process, so the cost of knowing a species is paid again on every restart -- and for the
species this project actually cares about, that cost is not small:

    C3H8         2515.9 s      HF/cc-pVTZ+d/geom
    CH3OC2H5     3444.2 s      HF/cc-pVTZ+d/geom

Forty minutes to re-learn something already known is not a performance detail; it is what
stops anybody iterating on a model that needs those numbers. This module persists the
table, on exactly the same justification: energy is a functor, so a species has one energy
wherever it occurs -- and *whenever*. Time is just another place.

THE CACHING IS TRIVIAL. THE KEY IS THE WHOLE PROBLEM.
-----------------------------------------------------
A memory cache lives inside one oracle object, so the tier is implicit in *which object
you are asking* and a bare species key is sound. A file does not have that protection. It
outlives the oracle, and a key of species-alone would happily serve an HF/cc-pVDZ number
to a CCSD(T)/cbs(TZ,QZ) question -- silently, with the wrong ``method`` string riding
along, producing a result that is wrong by an amount nobody would think to look for.

So the key carries the full provenance of the tier that computed it: method, basis,
tight-d policy, geometry tier. That is what ``_fingerprint`` is for, and it is the part
worth testing. A test that only checks "the same species hits" would pass on a cache that
is catastrophically wrong.

And because a key can be right by construction and still be wrong after somebody edits
the constructor, every read is CROSS-CHECKED: a record whose stored ``method`` disagrees
with the asking oracle's name is discarded as a miss and counted in ``rejected``. The key
says the entry should match; the check confirms it does. Cheap, and it catches exactly the
collision that would otherwise be invisible.

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
A corrupt file, an unreadable directory, a record from a future schema, a stored value
that will not parse -- every one of them degrades to "not cached", which costs time and
nothing else. The cache can make this project slower. It must never make it wrong.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from ..category import Molecule
from .base import BaseOracle, Estimate

#: Bumped when the record layout changes. A file from a different schema is ignored
#: wholesale rather than half-read, because a partially-understood cache is the one
#: failure mode here that could produce a wrong number instead of a slow one.
SCHEMA_VERSION = 1


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
    bonds = ",".join(f"{b.i}-{b.j}:{b.order}"
                     for b in sorted(molecule.bonds, key=lambda b: (b.i, b.j, b.order)))
    return (f"atoms={'.'.join(molecule.atoms)}|bonds={bonds}"
            f"|charge={molecule.charge}|state={molecule.state}")


def _fingerprint(oracle) -> str:
    """
    A string identifying the TIER, so a cached number is only ever served to a question
    asked at the same tier.

    ``PySCFOracle.name`` already encodes method, basis, the tight-d policy and the
    geometry tier -- it was built to be a provenance string and this reuses it as one. The
    explicit attribute sweep is belt-and-braces for oracles that carry a distinguishing
    setting their name does not mention; anything unnamed falls back to the class name, so
    an oracle this function does not understand still cannot collide with one it does.
    """
    parts = [type(oracle).__name__, getattr(oracle, "name", "")]
    for attribute in ("method", "basis", "tight_d", "geometry_tier"):
        if hasattr(oracle, attribute):
            parts.append(f"{attribute}={getattr(oracle, attribute)!r}")
    return "|".join(parts)


class PersistentCache(BaseOracle):
    """
    Wraps any oracle and memoises ``energy`` to a JSON file, keyed by (tier, species).

    Transparent in the same sense ``CachingOracle`` is: same answers, same error bars,
    same ``None`` refusals -- and refusals are cached too, since an oracle that declines a
    species declines it every time and re-asking is pure cost.

    Writes are atomic (temp file plus ``os.replace``), so a run killed mid-write leaves the
    previous good file rather than a truncated one. That matters here more than usual: the
    runs this cache exists to protect are the ones long enough that somebody eventually
    kills them.
    """

    def __init__(self, inner, path: str | os.PathLike, autosave: bool = True):
        self.inner = inner
        self.name = inner.name
        self.nominal_accuracy_ev = getattr(inner, "nominal_accuracy_ev", float("nan"))
        self.path = Path(path)
        self.autosave = autosave
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

        self._entries: dict[str, dict] = {}
        self._load()

    # -- the file ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text())
            if raw.get("version") != SCHEMA_VERSION:
                self.load_error = (f"schema {raw.get('version')!r} is not "
                                   f"{SCHEMA_VERSION}; ignoring the file")
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

    def save(self) -> None:
        """Write the table atomically. Safe to call repeatedly."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": SCHEMA_VERSION, "entries": self._entries}
        handle, temporary = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(handle, "w") as stream:
                json.dump(payload, stream, indent=1, sort_keys=True)
            os.replace(temporary, self.path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise

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
            restored = self._restore(record)
            if restored is not False:
                self.hits += 1
                if restored is not None:
                    self.saved_seconds += restored.seconds
                return restored
            # cross-check failed or the record would not parse: treat as absent and
            # recompute, so a bad entry costs time rather than correctness
            self.rejected += 1

        self.misses += 1
        result = self.inner.energy(canonical)
        self._entries[key] = self._record(result)
        if self.autosave:
            self.save()
        return result

    def _record(self, estimate: Estimate | None) -> dict:
        if estimate is None:
            return {"declined": True, "method": self.name}
        return {
            "declined": False,
            "value_ev": estimate.value_ev,
            "uncertainty_ev": estimate.uncertainty_ev,
            "method": estimate.method,
            "seconds": estimate.seconds,
            "notes": estimate.notes,
            "systematic_ev": estimate.systematic_ev,
        }

    def _restore(self, record: dict) -> Estimate | None | bool:
        """
        The stored estimate, or ``False`` meaning "do not trust this record".

        ``False`` rather than ``None`` because ``None`` is a legitimate cached value -- it
        is a refusal, and refusals are worth caching. Conflating "the oracle declined" with
        "this entry is unusable" would turn a corrupt record into a permanent refusal.
        """
        try:
            if record.get("declined"):
                return None
            stored = record["method"]
            # THE CROSS-CHECK. The key should already guarantee this; the point is that a
            # key is a claim and this is the confirmation. A mismatch means an entry from
            # one tier is being served to another, which is the one failure here capable
            # of producing a wrong number instead of a slow run.
            if not str(stored).startswith(self.name):
                return False
            return Estimate(
                value_ev=float(record["value_ev"]),
                uncertainty_ev=float(record["uncertainty_ev"]),
                method=stored,
                seconds=float(record["seconds"]),
                notes=(f"{record['notes']}; restored from persistent cache "
                       f"{self.path.name}").lstrip("; "),
                systematic_ev=float(record.get("systematic_ev", 0.0)),
            )
        except (KeyError, TypeError, ValueError):
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
        return (f"{self.name} via {self.path.name}: {asked} requests, {self.misses} priced,"
                f" {self.hits} restored, {self.distinct_species} on disk, "
                f"{saving:.2f}x saved, {self.saved_seconds:.1f} s not re-spent"
                f"{note}{broken}")

    def __repr__(self) -> str:
        return f"PersistentCache({self.inner!r}, {self.path}, {self.distinct_species})"
