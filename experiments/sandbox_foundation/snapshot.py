"""Wave G/F -- a domain-neutral, DEEPLY IMMUTABLE PhysicalWorldSnapshot: the LibGibson observation boundary.

Ooh yeah, can do!  SYNTHETIC / experimental.  SmartChem supplies ONE narrow, immutable observation boundary and
its content identity; LibGibson (its own repo, epic #125) owns the renderer/TUI.  SmartChem must NOT implement
the renderer; a mock projection here is only enough to PROVE the contract.

THE CONTRACT (two separations, both load-bearing):
  1. AUTHORITATIVE physical state vs DISPLAY realization.  `model_digest` covers ONLY the authoritative scientific
     content (schema, geometry, species, amounts, masks, tick, time, units, conservation diagnostics,
     numerical uncertainty, boundary material, the receipt's model side).  Renderer-neutral `display_hints` and
     `illustration` (colours, labels, layout, decoration) are EXCLUDED, so a cosmetic change cannot move the model
     identity (Wave A3).
  2. MODEL identity vs EVIDENCE/ADMISSION identity.  `evidence_digest` covers which sources/checks/domains justify
     the model plus the receipt's admission side; it is independent of `model_digest`.  A source-revision change
     moves the evidence digest without silently reusing it as a model-identity receipt, and vice-versa.

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

WAVE F (trustworthy simulator -> LibGibson observation contract).  Two additions so that source validity and numerical
assumptions CANNOT vanish on the way to a pixel:
  * `ModelRunReceipt` -- admission level + scientific verdict of the mechanism(s) behind the state, the numerical
    assumptions (solver, tolerances, convergence status, residuals) and the orthogonal model-identity vs
    admission-identity digests.  `admitted` is DERIVED by a trusted factory (`from_executable`), never accepted from
    the public constructor ("a label is not a binding"); `numerically_verified` is COMPUTED from residuals vs
    tolerances and FAILS CLOSED on a missing residual.  An absent receipt reads as UNADMITTED / UNVERIFIED.
  * `QuantityKind` -- every quantity a frame carries is exactly one of CANONICAL / MODEL_DERIVED / UNSUPPORTED /
    ILLUSTRATION; the snapshot stores the illustration and unsupported-quantity declarations so a renderer can never
    present decoration or a missing value as a measurement.
The snapshot has NO write path back into the model: it owns private immutable copies, and `verify_integrity()` lets a
consumer re-derive both digests to detect an object-level tamper.

THE NON-NEGOTIABLE PROPERTY: rendering is a PURE read.  Rendering a snapshot zero, one or many times cannot alter
the canonical model state or either digest.  The headless replay test proves it: a trajectory rendered at every
step is byte-identical to one with no rendering at all.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from enum import Enum
from types import MappingProxyType
from typing import Optional

import numpy as np

from .mechanism_types import AdmissionLevel

SCHEMA_VERSION = "phys-world-snapshot-v2"   # v2: + receipt, illustration, unsupported_quantities (Wave F)


class QuantityKind(str, Enum):
    """The 4-way typing of every quantity in a frame (Wave F2).  Exactly one applies to any value."""
    CANONICAL = "CANONICAL"          # authoritative simulated state (amounts, volumes, tick, time)
    MODEL_DERIVED = "MODEL_DERIVED"  # computed from the model (e.g. concentration); inherits the receipt's admission
    UNSUPPORTED = "UNSUPPORTED"      # the model does not supply it / it is masked: serialises to null, NEVER 0
    ILLUSTRATION = "ILLUSTRATION"    # pure visual decoration; never a measurement


MEASUREMENT_KINDS = frozenset({QuantityKind.CANONICAL, QuantityKind.MODEL_DERIVED})
_CONVERGED_OK = ("CONVERGED", "NOT_ITERATIVE")   # statuses under which residuals may certify; anything else cannot


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
            h.update(json.dumps(_jsonify(p), sort_keys=True, allow_nan=False).encode())
        h.update(b"\x1e")  # record separator
    return h.hexdigest()


def _view(store: tuple) -> np.ndarray:
    """A read-only, UNLOCKABLE view onto an immutable bytes store (its base is `bytes`, so the WRITEABLE flag
    cannot be re-enabled, and there is no owning array to reach through `.base`)."""
    buf, dtype, shape = store
    return np.frombuffer(buf, dtype=dtype).reshape(shape)


# --------------------------------------------------------------------------------------------- the run receipt
def _is_real(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def numerics_verified(numerics) -> bool:
    """The ONE pure verdict on a numerics block (a Mapping, frozen or plain/JSON).  Fail-closed on everything odd:
    wrong container types, no tolerance, a missing / None / bool / non-finite residual, a bool / non-finite / negative
    tolerance, a non-converged status.  Shared by `ModelRunReceipt` and the frame validator, so a renderer re-derives
    exactly the verdict the simulator would."""
    if not isinstance(numerics, Mapping) or numerics.get("convergence_status") not in _CONVERGED_OK:
        return False
    tol, res = numerics.get("tolerances"), numerics.get("residuals")
    if not isinstance(tol, Mapping) or not isinstance(res, Mapping) or not tol:
        return False
    for k, t in tol.items():
        r = res.get(k)
        if not _is_real(r) or not _is_real(t) or t < 0 or r > t:
            return False
    return True


def trust_label(admitted: bool, level: str, verified: bool) -> str:
    a = "ADMITTED" if admitted else f"UNADMITTED({level})"
    return f"{a}+{'NUMERICS-VERIFIED' if verified else 'NUMERICS-UNVERIFIED'}"


class ModelRunReceipt:
    """What produced this state, and how much a reader may believe it -- readable WITHOUT re-deriving anything.

    model identity   `model_identity`            content identity of the authoritative model (moves with chemistry/params)
    admission        `admission_level`, `law_levels`, `admission_identities`, `admitted`  (the EVIDENCE side)
    numerics         `numerics`: solver, convergence_status, tolerances{name: tol}, residuals{name: value|None}, notes

    `admitted` is True ONLY when a trusted classmethod (`from_executable`) MINTS it from an ExecutableMechanism under an
    AdmissionPolicy.  The public constructor has NO stamp parameters at all (same pattern as SourceBinding: no public
    door, a private `_mint`), so it can record a DECLARED level but can never set `admitted` -- and there is no
    sentinel to import (a label is not a binding).  Conceded limit: `object.__setattr__` on a finished object is
    possible in Python; that is not cryptographic and not claimed to be.

    `numerically_verified` is COMPUTED by `numerics_verified`: status CONVERGED / NOT_ITERATIVE, at least one
    tolerance, and EVERY tolerance a finite non-negative real with a finite real residual <= it; a missing / None /
    bool / non-finite residual or tolerance FAILS CLOSED.  A NaN residual is ACCEPTED by this constructor (the verdict
    is then False); the construction-time REFUSAL only fires when the receipt enters a PhysicalWorldSnapshot
    (canonical JSON uses allow_nan=False).  What 'numerically verified' does NOT mean: it certifies the listed
    residuals (conservation, positivity, passivity), NOT a truncation-error bound against the exact PDE solution."""

    __slots__ = ("_model_identity", "_level", "_admitted", "_derived", "_law_levels", "_adm_ids", "_numerics")

    def __init__(self, model_identity: str, numerics: Mapping, *, admission_level="SYNTHETIC", law_levels=(),
                 admission_identities=()):
        if not isinstance(model_identity, str) or not model_identity:
            raise ValueError("model_identity must be a non-empty string")
        level = AdmissionLevel(admission_level).value          # unknown level -> ValueError, not a free-form label
        object.__setattr__(self, "_model_identity", model_identity)
        object.__setattr__(self, "_level", level)
        object.__setattr__(self, "_admitted", False)           # the public path is a DECLARATION, never an authority
        object.__setattr__(self, "_derived", False)
        object.__setattr__(self, "_law_levels", tuple(AdmissionLevel(x).value for x in law_levels))
        object.__setattr__(self, "_adm_ids", _deep_freeze([list(x) if isinstance(x, (tuple, list)) else x
                                                           for x in admission_identities]))
        object.__setattr__(self, "_numerics", _deep_freeze(dict(numerics)))

    def __setattr__(self, name, value):
        raise AttributeError("ModelRunReceipt is immutable")

    def __delattr__(self, name):
        raise AttributeError("ModelRunReceipt is immutable")

    # -- trusted factories ---------------------------------------------------------------------------
    @classmethod
    def _mint(cls, model_identity, numerics, *, admitted: bool, **kw) -> "ModelRunReceipt":
        """The ONLY place the admitted/derived stamp is written (private; the public __init__ cannot reach it)."""
        obj = cls(model_identity, numerics, **kw)
        object.__setattr__(obj, "_admitted", bool(admitted))
        object.__setattr__(obj, "_derived", True)
        return obj

    @classmethod
    def from_executable(cls, executable, policy, numerics) -> "ModelRunReceipt":
        """DERIVE the admission side from an ExecutableMechanism under `policy` (the trusted path)."""
        return cls._mint(executable.model_identity, numerics, admitted=executable.admitted_under(policy),
                         admission_level=executable.admission_level_under(policy).value,
                         law_levels=[lv.value for lv in executable.law_levels(policy)],
                         admission_identities=executable.admission_identities)

    @classmethod
    def unadmitted_transport(cls, model_identity: str, numerics: Mapping) -> "ModelRunReceipt":
        """A passive-transport-only model with caller-declared conductances: NO kinetic mechanism is admitted, so the
        derived verdict is SYNTHETIC / not admitted (derived, not merely declared)."""
        return cls._mint(model_identity, numerics, admitted=False, admission_level="SYNTHETIC")

    # -- reads -----------------------------------------------------------------------------------------
    model_identity = property(lambda self: self._model_identity)
    admission_level = property(lambda self: self._level)
    admitted = property(lambda self: self._admitted)
    admission_derived = property(lambda self: self._derived)
    law_levels = property(lambda self: self._law_levels)
    admission_identities = property(lambda self: self._adm_ids)
    numerics = property(lambda self: self._numerics)

    @property
    def numerically_verified(self) -> bool:
        return numerics_verified(self._numerics)

    @property
    def scientific_measurement(self) -> bool:
        """admitted AND numerically verified -- the only combination a renderer may call a validated measurement."""
        return self._admitted and self.numerically_verified

    @property
    def label(self) -> str:
        return trust_label(self._admitted, self._level, self.numerically_verified)

    # -- digest parts (model side vs evidence side stay orthogonal) -----------------------------------
    def model_part(self):
        return ("receipt-model", self._model_identity, self._numerics)

    def admission_part(self):
        return ("receipt-admission", self._level, self._admitted, self._derived, self._law_levels, self._adm_ids)

    def to_dict(self) -> dict:
        return {"present": True, "model_identity": self._model_identity, "admission_level": self._level,
                "admitted": self._admitted, "admission_derived": self._derived,
                "law_levels": list(self._law_levels), "admission_identities": _jsonify(self._adm_ids),
                "numerics": _jsonify(self._numerics), "numerically_verified": self.numerically_verified,
                "scientific_measurement": self.scientific_measurement, "label": self.label}


def absent_receipt_dict() -> dict:
    """What a frame says when NO receipt travelled with the state: unadmitted, unverified -- never silent."""
    return {"present": False, "admitted": False, "numerically_verified": False, "scientific_measurement": False,
            "label": "NO-RECEIPT(UNADMITTED+NUMERICS-UNVERIFIED)"}


def _digests(schema, species, vol, amt, mask, units, tick, time_s, cons, numunc, boundary, unsupported, rcpt_model,
             evidence, rcpt_adm) -> tuple:
    """The SINGLE definition of (model_digest, evidence_digest).  The snapshot calls it over its stores; the frame
    validator calls it over a frame's content (`compute_digests`), so the two cannot drift apart."""
    model = _canon(schema, species, vol, amt, mask, units, tick, time_s, cons, numunc, boundary, unsupported,
                   rcpt_model)
    return model, _canon(schema, evidence, rcpt_adm)


def compute_digests(*, schema_version, species, cell_volumes_m3, amounts_mol, valid_mask, units, model_tick,
                    physical_time_s, conservation_diagnostics, numerical_uncertainty, boundary_material, unsupported,
                    evidence, receipt_model_part, receipt_admission_part) -> tuple:
    """Recompute (model_digest, evidence_digest) from PLAIN content (what a frame carries).  Masked amounts are
    canonical 0.0 (see PhysicalWorldSnapshot), so a null in a frame reconstructs to the exact stored value."""
    mask = np.asarray(valid_mask, dtype=bool)
    amt = np.where(mask, np.asarray(amounts_mol, dtype=float), 0.0)
    return _digests(
        str(schema_version), tuple(species), _store_array(np.asarray(cell_volumes_m3, dtype=float), float),
        _store_array(amt, float), _store_array(mask, bool), _deep_freeze(units), int(model_tick),
        float(physical_time_s), _deep_freeze(conservation_diagnostics), _deep_freeze(numerical_uncertainty),
        _deep_freeze(tuple(boundary_material)), _deep_freeze(unsupported), _deep_freeze(receipt_model_part),
        _deep_freeze(evidence), _deep_freeze(receipt_admission_part))


# --------------------------------------------------------------------------------------------- the snapshot
class PhysicalWorldSnapshot:
    """An immutable observation of a physical world at one model tick.  Not a dataclass: the authoritative content
    is kept in immutable backing storage and exposed through read-only properties, so nothing a consumer (or a
    buggy/adversarial renderer) does can mutate it or desynchronise the digests.

    Authoritative scientific content (feeds model_digest): species, cell_volumes_m3, amounts_mol (cells x species),
    valid_mask (True = a real value; False = UNSUPPORTED/missing), units, model_tick, physical_time_s,
    conservation_diagnostics, numerical_uncertainty, boundary_material, unsupported_quantities, receipt (model side).
    Admission content (feeds evidence_digest): evidence (sources / checks / model domains), receipt (admission side).
    Renderer-neutral (EXCLUDED from both digests): display_hints, illustration."""

    __slots__ = ("_species", "_vol", "_amt", "_mask", "_units", "_model_tick", "_physical_time_s",
                 "_conservation_diagnostics", "_numerical_uncertainty", "_boundary_material", "_evidence",
                 "_display_hints", "_illustration", "_unsupported", "_receipt", "_schema_version",
                 "_model_digest", "_evidence_digest")

    def __init__(self, species, cell_volumes_m3, amounts_mol, valid_mask, units, model_tick, physical_time_s,
                 conservation_diagnostics=None, numerical_uncertainty=None, boundary_material=(),
                 evidence=None, display_hints=None, schema_version=SCHEMA_VERSION, *,
                 receipt: Optional[ModelRunReceipt] = None, illustration=None, unsupported_quantities=None):
        species = tuple(species)
        if not all(isinstance(s, str) for s in species):
            raise ValueError("species must be a tuple of string names")   # keep non-string content out of the digest
        if receipt is not None and not isinstance(receipt, ModelRunReceipt):
            raise TypeError("receipt must be a ModelRunReceipt (or None = explicitly unadmitted / unverified)")
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
        amt = np.where(mask, amt, 0.0)     # a MASKED amount is not authoritative content: canonical 0.0 (frame emits null)
        unsupported = dict(unsupported_quantities or {})
        illus = dict(illustration or {})
        clash = (set(unsupported) | set(illus)) & ({"amount_mol", "concentration_mol_per_m3"} | set(species))
        if clash or (set(unsupported) & set(illus)):
            raise ValueError(f"quantity names must be unique across kinds; clashing: {sorted(clash)}")

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
        object.__setattr__(self, "_illustration", _deep_freeze(illus))
        object.__setattr__(self, "_unsupported", _deep_freeze({str(k): str(v) for k, v in unsupported.items()}))
        object.__setattr__(self, "_receipt", receipt)
        object.__setattr__(self, "_schema_version", str(schema_version))

        m, e = self._compute_digests()
        object.__setattr__(self, "_model_digest", m)
        object.__setattr__(self, "_evidence_digest", e)

    def _compute_digests(self) -> tuple:
        """model identity: authoritative content ONLY (display_hints, illustration and evidence excluded), over the
        SAME immutable stores the properties hand out -- so a consumer's mutated copy can never desynchronise it."""
        rcpt_m = self._receipt.model_part() if self._receipt is not None else None
        rcpt_a = self._receipt.admission_part() if self._receipt is not None else None
        return _digests(self._schema_version, self._species, self._vol, self._amt, self._mask, self._units,
                        self._model_tick, self._physical_time_s, self._conservation_diagnostics,
                        self._numerical_uncertainty, self._boundary_material, self._unsupported, rcpt_m,
                        self._evidence, rcpt_a)

    def verify_integrity(self) -> bool:
        """Re-derive both digests from the stored content.  False means the object was tampered with at the object
        level (e.g. via object.__setattr__) after construction -- a consumer can detect, though Python cannot forbid."""
        return self._compute_digests() == (self._model_digest, self._evidence_digest)

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
    def illustration(self):
        """name -> {"values": [...], ...}: PURE VISUAL ILLUSTRATION.  Never a measurement; excluded from digests."""
        return self._illustration

    @property
    def unsupported_quantities(self):
        """name -> unit: quantities the model does NOT supply.  Serialised as null; never a fabricated 0."""
        return self._unsupported

    @property
    def receipt(self) -> Optional[ModelRunReceipt]:
        return self._receipt

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
        """A MODEL_DERIVED read; invalid cells/species are NaN, not a fabricated 0."""
        c = self.amounts_mol / self.cell_volumes_m3[:, None]
        return np.where(self.valid_mask, c, np.nan)

    def with_display_hints(self, **hints) -> "PhysicalWorldSnapshot":
        """A new snapshot with different COSMETIC hints only -- the model_digest is unchanged by construction."""
        return PhysicalWorldSnapshot(
            self._species, self.cell_volumes_m3, self.amounts_mol, self.valid_mask,
            _jsonify(self._units), self._model_tick, self._physical_time_s, _jsonify(self._conservation_diagnostics),
            _jsonify(self._numerical_uncertainty), self._boundary_material, _jsonify(self._evidence),
            {**_jsonify(self._display_hints), **hints}, self._schema_version,
            receipt=self._receipt, illustration=_jsonify(self._illustration),
            unsupported_quantities=_jsonify(self._unsupported))

    @classmethod
    def from_mesh(cls, system, state, *, model_tick: int = 0, evidence: Optional[dict] = None,
                  display_hints: Optional[dict] = None, numerical_uncertainty: Optional[dict] = None,
                  receipt: Optional[ModelRunReceipt] = None):
        """Build a snapshot from a Wave-D MeshSystem + MeshState (amounts per cell), with a conservation diagnostic
        from the mechanism's element/charge inventory where present."""
        vols = np.asarray(system.mesh.volumes_m3, float)
        amt = np.asarray(state.n, float)
        M = system.inventory_matrix
        totals = M @ amt.sum(axis=0)
        return cls(tuple(system.species), vols, amt, np.ones_like(amt, dtype=bool),
                   {"amount": "mol", "volume": "m^3", "time": "s"}, model_tick,
                   float(state.t), {"inventory_totals": totals.tolist()}, numerical_uncertainty or {}, (),
                   evidence or {}, display_hints or {}, receipt=receipt)


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
