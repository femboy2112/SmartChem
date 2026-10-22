"""Wave G -- a domain-neutral, DEEPLY IMMUTABLE PhysicalWorldSnapshot: the LibGibson observation boundary.

Ooh yeah, can do!  SYNTHETIC / experimental.  SmartChem supplies ONE narrow, immutable observation boundary and
its content identity; LibGibson (its own repo, epic #125) owns the renderer/TUI.  SmartChem must NOT implement
the renderer; a mock projection here is only enough to PROVE the contract.

THE CONTRACT (two separations, both load-bearing):
  1. AUTHORITATIVE physical state vs DISPLAY realization.  `model_digest` covers ONLY the authoritative scientific
     content (schema, geometry, species, amounts, masks, tick, time, units, conservation diagnostics,
     numerical uncertainty, boundary material).  Renderer-neutral `display_hints` (colours, labels, layout) are
     EXCLUDED, so a cosmetic change cannot move the model identity (Wave A3).
  2. MODEL identity vs EVIDENCE/ADMISSION identity.  `evidence_digest` covers which sources/checks/domains justify
     the model; it is independent of `model_digest`.  A source-revision change moves the evidence digest without
     silently reusing it as a model-identity receipt, and vice-versa.

DEEP IMMUTABILITY (the Round-IV C3 repair).  A frozen dataclass whose fields are still mutable dicts and
own-their-data numpy arrays is NOT immutable: a caller could mutate `units`/`evidence`/... in place, or re-enable
an array's write flag (`setflags(write=True)` succeeds on an array that owns its buffer), and leave the already
computed digest STALE.  So the authoritative content is now stored in genuinely immutable backing storage:
  * numeric arrays live as `bytes` and are exposed as `np.frombuffer(...)` VIEWS -- read-only AND unlockable,
    because their base is an immutable `bytes` object (setflags(write=True) raises, and there is no owning array
    to reach through `.base`).  Each access regenerates the view from the SAME bytes the digest was taken over, so
    a mutated copy can never desynchronise the digest.
  * dict/list content is deep-frozen to `MappingProxyType` / tuples (recursively), so in-place mutation raises.
  * the digest is a canonical SHA-256 over exactly that frozen content -- never `str()` of an arbitrary object
    (an un-serialisable value fails closed rather than hashing an unstable repr).

THE NON-NEGOTIABLE PROPERTY: rendering is a PURE read.  Rendering a snapshot zero, one or many times cannot alter
the canonical model state or either digest.  The headless replay test proves it: a trajectory rendered at every
step is byte-identical to one with no rendering at all.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from types import MappingProxyType
from typing import Optional

import numpy as np

SCHEMA_VERSION = "phys-world-snapshot-v1"


# ------------------------------------------------------------------------------------- immutability helpers
def _deep_freeze(obj):
    """Recursively convert dict/list/tuple of JSON-canonical scalars into an immutable structure
    (MappingProxyType / tuple).  Refuses an arbitrary object -- there is NO str() fallback, because a snapshot
    digest must be a guaranteed canonical scientific serialisation, not an unstable repr."""
    if isinstance(obj, Mapping):
        return MappingProxyType({str(k): _deep_freeze(v) for k, v in obj.items()})
    if isinstance(obj, (list, tuple)):
        return tuple(_deep_freeze(v) for v in obj)
    if isinstance(obj, np.ndarray):
        return _deep_freeze(obj.tolist())
    if isinstance(obj, (str, bool, type(None))):
        return obj
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return float(obj)
    raise TypeError(f"snapshot content {type(obj).__name__} is not canonically serialisable (dict/list/tuple of "
                    "str/bool/int/float/None only); refused rather than hashed via str()")


def _jsonify(obj):
    """Frozen structure -> JSON-safe (MappingProxyType -> dict, tuple -> list)."""
    if isinstance(obj, Mapping):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return obj


class _ArrayStore(tuple):
    """Typed marker for an authoritative (bytes, dtype_str, shape) array store.  `_canon` dispatches on this TYPE,
    NOT on a fragile 'any bytes-led 3-tuple' shape heuristic (evil-morty Round IV Finding 2) -- so an ordinary
    content tuple (e.g. a species tuple) can never be misread as an array buffer."""
    __slots__ = ()


def _store_array(a, dtype) -> "_ArrayStore":
    """The immutable backing store for an authoritative array: (bytes, dtype_str, shape), typed _ArrayStore."""
    arr = np.ascontiguousarray(np.asarray(a, dtype=dtype))
    return _ArrayStore((arr.tobytes(), arr.dtype.str, arr.shape))


def _canon(*parts) -> str:
    """Stable SHA-256 over a canonical serialization of the parts.  An _ArrayStore is hashed as a raw numeric
    buffer with its dtype/shape/bytes DELIMITED (so bytes cannot shift across the boundaries and collide); every
    other part is hashed as sorted-key JSON (NO default= fallback).  Each branch carries a domain tag, so a
    JSON-encoded value and an array store can never hash-collide."""
    h = hashlib.sha256()
    for p in parts:
        if isinstance(p, _ArrayStore):
            buf, dtype, shape = p
            h.update(b"ndarray\x1e")
            h.update(str(dtype).encode())
            h.update(b"\x1e")
            h.update(str(tuple(shape)).encode())
            h.update(b"\x1e")
            h.update(bytes(buf))
        else:
            h.update(b"json\x1e")
            h.update(json.dumps(_jsonify(p), sort_keys=True).encode())
        h.update(b"\x1e")  # record separator
    return h.hexdigest()


def _view(store: tuple) -> np.ndarray:
    """A read-only, UNLOCKABLE view onto an immutable bytes store (its base is `bytes`, so the WRITEABLE flag
    cannot be re-enabled, and there is no owning array to reach through `.base`)."""
    buf, dtype, shape = store
    return np.frombuffer(buf, dtype=dtype).reshape(shape)


class PhysicalWorldSnapshot:
    """An immutable observation of a physical world at one model tick.  Not a dataclass: the authoritative content
    is kept in immutable backing storage and exposed through read-only properties, so nothing a consumer (or a
    buggy/adversarial renderer) does can mutate it or desynchronise the digests.

    Authoritative scientific content (feeds model_digest): species, cell_volumes_m3, amounts_mol (cells x species),
    valid_mask (True = a real value; False = invalid/missing), units, model_tick, physical_time_s,
    conservation_diagnostics, numerical_uncertainty, boundary_material.
    Admission content (feeds evidence_digest): evidence (sources / checks / model domains).
    Renderer-neutral (EXCLUDED from both digests): display_hints."""

    __slots__ = ("_species", "_vol", "_amt", "_mask", "_units", "_model_tick", "_physical_time_s",
                 "_conservation_diagnostics", "_numerical_uncertainty", "_boundary_material", "_evidence",
                 "_display_hints", "_schema_version", "_model_digest", "_evidence_digest")

    def __init__(self, species, cell_volumes_m3, amounts_mol, valid_mask, units, model_tick, physical_time_s,
                 conservation_diagnostics=None, numerical_uncertainty=None, boundary_material=(),
                 evidence=None, display_hints=None, schema_version=SCHEMA_VERSION):
        species = tuple(species)
        if not all(isinstance(s, str) for s in species):
            raise ValueError("species must be a tuple of string names")   # keep non-string content out of the digest
        vols = np.asarray(cell_volumes_m3, dtype=float)
        amt = np.asarray(amounts_mol, dtype=float)
        mask = np.asarray(valid_mask, dtype=bool)
        C, S = len(vols), len(species)
        if amt.shape != (C, S) or mask.shape != (C, S):
            raise ValueError("amounts_mol and valid_mask must both be (n_cells, n_species)")
        if not np.all(np.isfinite(vols)) or np.any(vols <= 0):
            raise ValueError("cell volumes must be finite and > 0")
        if np.any(~np.isfinite(amt) & mask):
            raise ValueError("a cell/species marked valid carries a non-finite amount")

        object.__setattr__(self, "_species", species)
        object.__setattr__(self, "_vol", _store_array(vols, float))
        object.__setattr__(self, "_amt", _store_array(amt, float))
        object.__setattr__(self, "_mask", _store_array(mask, bool))
        object.__setattr__(self, "_units", _deep_freeze(units))
        object.__setattr__(self, "_model_tick", int(model_tick))
        object.__setattr__(self, "_physical_time_s", float(physical_time_s))
        object.__setattr__(self, "_conservation_diagnostics", _deep_freeze(conservation_diagnostics or {}))
        object.__setattr__(self, "_numerical_uncertainty", _deep_freeze(numerical_uncertainty or {}))
        object.__setattr__(self, "_boundary_material", _deep_freeze(tuple(boundary_material)))
        object.__setattr__(self, "_evidence", _deep_freeze(evidence or {}))
        object.__setattr__(self, "_display_hints", _deep_freeze(display_hints or {}))
        object.__setattr__(self, "_schema_version", str(schema_version))

        # model identity: authoritative content ONLY (display_hints and evidence excluded), over the SAME immutable
        # stores the properties hand out -- so a consumer's mutated copy can never desynchronise the digest.
        model = _canon(self._schema_version, species, self._vol, self._amt, self._mask, self._units,
                       self._model_tick, self._physical_time_s, self._conservation_diagnostics,
                       self._numerical_uncertainty, self._boundary_material)
        evidence_digest = _canon(self._schema_version, self._evidence)
        object.__setattr__(self, "_model_digest", model)
        object.__setattr__(self, "_evidence_digest", evidence_digest)

    def __setattr__(self, name, value):  # belt-and-suspenders: the instance is frozen after construction
        raise AttributeError("PhysicalWorldSnapshot is immutable")

    def __delattr__(self, name):
        raise AttributeError("PhysicalWorldSnapshot is immutable")

    # -- read-only authoritative content -----------------------------------------------------------
    @property
    def species(self) -> tuple:
        return self._species

    @property
    def cell_volumes_m3(self) -> np.ndarray:
        return _view(self._vol)

    @property
    def amounts_mol(self) -> np.ndarray:
        return _view(self._amt)

    @property
    def valid_mask(self) -> np.ndarray:
        return _view(self._mask)

    @property
    def units(self):
        return self._units

    @property
    def model_tick(self) -> int:
        return self._model_tick

    @property
    def physical_time_s(self) -> float:
        return self._physical_time_s

    @property
    def conservation_diagnostics(self):
        return self._conservation_diagnostics

    @property
    def numerical_uncertainty(self):
        return self._numerical_uncertainty

    @property
    def boundary_material(self) -> tuple:
        return self._boundary_material

    @property
    def evidence(self):
        return self._evidence

    @property
    def display_hints(self):
        return self._display_hints

    @property
    def schema_version(self) -> str:
        return self._schema_version

    @property
    def model_digest(self) -> str:
        return self._model_digest

    @property
    def evidence_digest(self) -> str:
        return self._evidence_digest

    # -- derived reads -----------------------------------------------------------------------------
    def concentration_mol_per_m3(self) -> np.ndarray:
        """A derived read; invalid cells/species are NaN, not a fabricated 0."""
        c = self.amounts_mol / self.cell_volumes_m3[:, None]
        return np.where(self.valid_mask, c, np.nan)

    def with_display_hints(self, **hints) -> "PhysicalWorldSnapshot":
        """A new snapshot with different COSMETIC hints only -- the model_digest is unchanged by construction."""
        return PhysicalWorldSnapshot(
            self._species, self.cell_volumes_m3, self.amounts_mol, self.valid_mask,
            _jsonify(self._units), self._model_tick, self._physical_time_s, _jsonify(self._conservation_diagnostics),
            _jsonify(self._numerical_uncertainty), self._boundary_material, _jsonify(self._evidence),
            {**_jsonify(self._display_hints), **hints}, self._schema_version)

    @classmethod
    def from_mesh(cls, system, state, *, model_tick: int = 0, evidence: Optional[dict] = None,
                  display_hints: Optional[dict] = None, numerical_uncertainty: Optional[dict] = None):
        """Build a snapshot from a Wave-D MeshSystem + MeshState (amounts per cell), with a conservation diagnostic
        from the mechanism's element/charge inventory where present."""
        vols = np.asarray(system.mesh.volumes_m3, float)
        amt = np.asarray(state.n, float)
        M = system.inventory_matrix
        totals = M @ amt.sum(axis=0)
        return cls(tuple(system.species), vols, amt, np.ones_like(amt, dtype=bool),
                   {"amount": "mol", "volume": "m^3", "time": "s"}, model_tick,
                   float(state.t), {"inventory_totals": totals.tolist()}, numerical_uncertainty or {}, (),
                   evidence or {}, display_hints or {})


# --------------------------------------------------------------------------------------------- mock renderer
def ascii_render(snap: PhysicalWorldSnapshot) -> str:
    """A MOCK renderer (LibGibson's job in its own repo).  A PURE read: it returns a string and touches nothing.
    display_hints may style it; the authoritative data is read from amounts_mol / valid_mask only."""
    sep = snap.display_hints.get("sep", " | ")
    amt = snap.amounts_mol
    mask = snap.valid_mask
    rows = []
    for i in range(len(snap.cell_volumes_m3)):
        cells = []
        for s, nm in enumerate(snap.species):
            v = f"{amt[i, s]:.3g}" if mask[i, s] else "--"
            cells.append(f"{nm}={v}")
        rows.append(sep.join(cells))
    return "\n".join(rows)
