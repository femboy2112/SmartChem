"""Typed authority for mechanisms: Descriptive (inspect) vs Executable (run) + the ADMISSION model -- Waves A1-A4.

Resolves the standing V2.0 ambiguity.  Naming a reaction family is not the same as having a rate law, a rate law
is not the same as sourced science, a bare citation is not the same as a verified source, and a caller-supplied
composition table is not the same as a verified molecular identity.  This module makes each of those a TYPE fact
instead of a vibe.

TWO ORTHOGONAL AUTHORITY AXES (Round IV):
  * KINETIC ADMISSION (per law), a 4-level facet -- NOT a one-string boolean:
      SYNTHETIC            hypothetical caller rate law; runs for labelled experiments; NO prediction authority.
      SOURCE_DECLARED      a citation string is attached, but nothing about it has been checked.
      SOURCE_VERIFIED      a structured AdmissionReceipt (source record + version + species + units + conditions +
                           model form + applicable range) was checked VERIFIED under a stated policy.
      BENCHMARK_VALIDATED  the model additionally survived a named independent physical benchmark.
    A1: the admission value is runtime-validated to be an AdmissionLevel -- an unknown string/int/None is a
    fail-closed refusal, never silently folded to "sourced".
    A2: a bare citation reaches only SOURCE_DECLARED; SOURCE_VERIFIED requires the receipt, so a fabricated source
    STRING can never mint a verified scientific claim.  The receipt is content-identified, so a source update
    changes the admission identity (and can REVOKE it) WITHOUT touching the model content.
  * SPECIES IDENTITY (per mechanism):
      UNTRUSTED  compositions/charges came straight from a public constructor -- structural DECLARATIONS only.
      VERIFIED   built via from_derivations from InventoryDerivation, i.e. bound to real SmartChem Molecule
                 identities whose composition was derived (the adapter's central law).
    A3: a forged composition table (public constructor) is UNTRUSTED and can never mint verified chemical
    authority, even carrying a verified kinetic receipt.

scientific_claim (a scientifically ADMITTED physical prediction) requires BOTH axes: kinetics >= SOURCE_VERIFIED
AND species identity VERIFIED.  This module cannot establish real-world source correctness (sigma) from code; it
enforces the STRUCTURE of admission -- completeness, content identity, the policy gate, the species binding -- and
fails closed everywhere else.  The 1.x readiness enum is NOT touched.

WAVE B -- WHO may say "verified" (a label is not a binding).  Four concepts, four types, never conflated:
  DECLARATION  SourceRecord / AdmissionReceipt(...)   a caller PROPOSES a source.  Inert: it can name any handbook,
                                                      reviewer or version it likes and it still proves nothing.
  INSPECTION   SourceStore + SourceBinding            the verifier reads a specific on-disk artifact, recomputes its
                                                      content digest, and checks the law's numbers/units/orders/
                                                      species/conditions against it.  Only the store can mint a
                                                      SourceBinding (no public constructor, not pickleable), and only
                                                      the store can attach one to a receipt (AdmissionReceipt.binding
                                                      is init=False).
  ADMISSION    AdmissionPolicy                        an explicit statement of WHICH stores are trusted roots.  The
                                                      default policy trusts only DEFAULT_STORE (``verified_sources/``
                                                      beside this file, currently ABSENT/EMPTY: no real inspected
                                                      source ships yet, so nothing is scientifically admitted by
                                                      default).
  VALIDATION   artifact "validation" block            BENCHMARK_VALIDATED needs the artifact itself to carry an
                                                      independent benchmark; a receipt string cannot declare one.
TRUST BOUNDARY (realistic, not cryptographic): ordinary public APIs, serialization and loading cannot forge a binding;
code that deliberately bypasses them (object.__setattr__, a writable trusted directory) can.  A deserialised receipt
(AdmissionReceipt.from_dict) NEVER carries a binding -- it comes back as a declaration and must be re-issued by a store.
A binding is bound to the law's exact numbers (params digest), the reaction's species identity + sides (checked at
to_executable against the mechanism's real Molecule identity keys), and the source's T / concentration domain, which
ExecutableMechanism.to_twocell carries INTO the numerical Mechanism so twocell.reaction_cell re-checks it on every
reaction transition (a changed T, or a superseded source, refuses rather than silently running as science).

Floats appear only at the explicit boundary ExecutableMechanism.to_twocell (the twocell solver is float).
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from experiments.sandbox_foundation.mechanism_adapter import (
    AdapterRefusal, InventoryDerivation, RefusalKind, build_E, identity_key)
from experiments.sandbox_foundation.twocell import Mechanism, ReactionRate, SandboxError
from smartchem.smiles import parse_smiles


class ConversionRefusalKind(str, Enum):
    KINETICS_UNAVAILABLE = "KINETICS_UNAVAILABLE"
    INVALID_KINETIC_LAW = "INVALID_KINETIC_LAW"
    DIMENSION_MISMATCH = "DIMENSION_MISMATCH"
    PROVENANCE_MISSING = "PROVENANCE_MISSING"
    OMISSIONS_UNDECLARED = "OMISSIONS_UNDECLARED"
    SELECTION_INVALID = "SELECTION_INVALID"
    INVENTORY_REFUSED = "INVENTORY_REFUSED"
    ADMISSION_INVALID = "ADMISSION_INVALID"          # bad admission level / missing-or-unverified receipt
    SOURCE_MISMATCH = "SOURCE_MISMATCH"              # the inspected source does not say what the law/mechanism says


class ConversionRefusal(Exception):
    def __init__(self, kind: ConversionRefusalKind, detail: str):
        super().__init__(f"{kind.value}: {detail}")
        self.kind = kind
        self.detail = detail


class AdmissionDomainError(SandboxError):
    """Raised at execution when a transition falls outside the admitted domain (T / concentration window) or the
    admitting source is no longer current / trusted.  A refusal, never a silent downgrade to 'still science'."""


# ------------------------------------------------------------------------------------------- admission facets
class AdmissionLevel(str, Enum):
    SYNTHETIC = "SYNTHETIC"
    SOURCE_DECLARED = "SOURCE_DECLARED"
    SOURCE_VERIFIED = "SOURCE_VERIFIED"
    BENCHMARK_VALIDATED = "BENCHMARK_VALIDATED"


_ADMISSION_ORDER = {
    AdmissionLevel.SYNTHETIC: 0,
    AdmissionLevel.SOURCE_DECLARED: 1,
    AdmissionLevel.SOURCE_VERIFIED: 2,
    AdmissionLevel.BENCHMARK_VALIDATED: 3,
}


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REVOKED = "REVOKED"          # a source update / retraction invalidates a previously-verified admission


class SpeciesIdentity(str, Enum):
    UNTRUSTED = "UNTRUSTED"      # caller-declared compositions (public constructor)
    VERIFIED = "VERIFIED"        # bound to real Molecule identities via InventoryDerivation


def _digest(*parts) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(json.dumps(p, sort_keys=True, default=str).encode())
        h.update(b"\x1e")
    return h.hexdigest()


@dataclass(frozen=True)
class SourceRecord:
    """A DECLARED source (a proposal).  Its content digest is its declared identity, but nothing here says anyone
    ever opened the source: a SourceRecord/AdmissionReceipt built through a public constructor is a DECLARATION
    and can never back SOURCE_VERIFIED.  Only a SourceStore-issued binding does."""
    citation: str
    version: str
    species: tuple
    units: str
    conditions: str
    model_form: str
    parameter_range: str

    def __post_init__(self):
        for nm in ("citation", "version", "units", "conditions", "model_form", "parameter_range"):
            if not str(getattr(self, nm)).strip():
                raise ConversionRefusal(ConversionRefusalKind.PROVENANCE_MISSING,
                                        f"SourceRecord.{nm} must be a non-empty statement")
        if not tuple(self.species):
            raise ConversionRefusal(ConversionRefusalKind.PROVENANCE_MISSING,
                                    "SourceRecord must name the species it speaks to")

    @property
    def identity(self) -> str:
        return _digest("SourceRecord", self.citation, self.version, tuple(self.species), self.units,
                       self.conditions, self.model_form, self.parameter_range)


def _norm_floats(xs):
    return None if xs is None else tuple(float(x) for x in xs)


def law_params_digest(*, kinetics, reversible, k_f, k_r, k_f_units, k_r_units, forward_orders, reverse_orders,
                      validity_T_K) -> str:
    """Digest of EXACTLY the numbers/units/orders/domain a source can certify.  A source entry and a KineticLaw
    both reduce to this; equal digests <=> the law says what the source says (B2).  A different rate under the
    same citation text has a different digest."""
    return _digest("LawParams", str(kinetics), bool(reversible), None if k_f is None else float(k_f),
                   None if k_r is None else float(k_r), k_f_units, k_r_units, _norm_floats(forward_orders),
                   _norm_floats(reverse_orders), _norm_floats(validity_T_K))


_MINT = object()        # module-private: only SourceStore holds the means to call SourceBinding._mint


@dataclass(frozen=True, init=False, eq=False)
class SourceBinding:
    """INSPECTION result: the verifier opened artifact ``record_id@version`` in ``store_root``, recomputed its
    content digest, and confirmed the law's parameters (``params_digest``) equal the artifact entry's.  It also
    carries the reaction's species/sides, and the T / concentration / phase / standard-state domain.

    There is NO public constructor, no ``dataclasses.replace``, no copy/pickle (all raise), so ordinary public
    APIs, serialization and loading cannot forge one.  (Bypassing with object.__setattr__ is in-process code
    execution; that is outside this boundary and says so.)"""
    store_root: str
    record_id: str
    version: str
    entry_id: str
    artifact_digest: str
    params_digest: str
    reactants: tuple            # sorted ((identity_key, count), ...)
    products: tuple
    T_K: tuple
    conc_max_mol_m3: Optional[float]
    phase: str
    standard_state: str
    assumptions: tuple
    benchmark: str              # "" unless the ARTIFACT carries an independent validation block

    def __init__(self, *a, **k):
        raise TypeError("SourceBinding has no public constructor; it is issued only by SourceStore.issue_receipt")

    def __reduce__(self):
        raise TypeError("SourceBinding is not serialisable; re-issue it from a SourceStore")

    def __copy__(self):
        raise TypeError("SourceBinding cannot be copied; re-issue it from a SourceStore")

    def __deepcopy__(self, memo):
        raise TypeError("SourceBinding cannot be copied; re-issue it from a SourceStore")

    @classmethod
    def _mint(cls, token, **fields) -> "SourceBinding":
        if token is not _MINT:
            raise TypeError("SourceBinding can only be minted by SourceStore")
        obj = object.__new__(cls)
        for k, v in fields.items():
            object.__setattr__(obj, k, v)
        return obj

    @property
    def identity(self) -> str:
        return _digest("SourceBinding", self.store_root, self.record_id, self.version, self.entry_id,
                       self.artifact_digest, self.params_digest, self.reactants, self.products, self.T_K,
                       self.conc_max_mol_m3, self.phase, self.standard_state, self.assumptions, self.benchmark)

    def structure_matches(self, reactant: dict, product: dict) -> bool:
        return (dict(self.reactants) == {k: v for k, v in reactant.items() if v}
                and dict(self.products) == {k: v for k, v in product.items() if v})


@dataclass(frozen=True)
class AdmissionReceipt:
    """A caller-visible receipt.  ``record``/``status``/``reviewer``/``benchmark`` are DECLARATIONS.  The only
    authoritative field is ``binding`` (init=False): set solely by SourceStore.issue_receipt, never by a caller,
    never restored from a dict.  A receipt without a binding is inert for SOURCE_VERIFIED."""
    record: SourceRecord
    status: VerificationStatus
    reviewer: str = ""            # DECLARED reviewer (a string; carries no authority)
    benchmark: str = ""           # DECLARED benchmark (a string; BENCHMARK_VALIDATED needs the artifact's own block)
    binding: Optional[SourceBinding] = field(init=False, default=None, compare=False)

    def __post_init__(self):
        if not isinstance(self.record, SourceRecord):
            raise ConversionRefusal(ConversionRefusalKind.ADMISSION_INVALID, "receipt.record must be a SourceRecord")
        if not isinstance(self.status, VerificationStatus):
            raise ConversionRefusal(ConversionRefusalKind.ADMISSION_INVALID,
                                    f"receipt.status must be a VerificationStatus, got {self.status!r}")

    @property
    def is_inspected(self) -> bool:
        return isinstance(self.binding, SourceBinding)

    @property
    def identity(self) -> str:
        return _digest("AdmissionReceipt", self.record.identity, self.status.value, self.reviewer, self.benchmark,
                       self.binding.identity if self.binding is not None else "")

    def to_dict(self) -> dict:
        r = self.record
        return {"record": {"citation": r.citation, "version": r.version, "species": list(r.species),
                           "units": r.units, "conditions": r.conditions, "model_form": r.model_form,
                           "parameter_range": r.parameter_range},
                "status": self.status.value, "reviewer": self.reviewer, "benchmark": self.benchmark,
                "inspected": self.is_inspected,
                "binding_identity": self.binding.identity if self.binding is not None else ""}

    @classmethod
    def from_dict(cls, d: dict) -> "AdmissionReceipt":
        """Loading NEVER restores authority: whatever 'binding'/'inspected' the dict claims is ignored, so the
        result is a declaration.  To get a verified receipt again, ask a SourceStore to issue one."""
        rec = d["record"]
        return cls(SourceRecord(rec["citation"], rec["version"], tuple(rec["species"]), rec["units"],
                                rec["conditions"], rec["model_form"], rec["parameter_range"]),
                   VerificationStatus(d["status"]), d.get("reviewer", ""), d.get("benchmark", ""))


# ------------------------------------------------------------------------------------------- the verifier
def _bad(detail: str, kind=ConversionRefusalKind.SOURCE_MISMATCH):
    return ConversionRefusal(kind, detail)


class SourceStore:
    """The verifier.  A directory of source artifacts, one JSON file per ``<record_id>@<version>.json``::

        {"record_id", "version", "title", "status": "current"|"superseded"|"retracted", "supersedes": "<ver>"?,
         "entries": {"<entry_id>": {
            "reactants": [{"smiles", "count"}], "products": [...],
            "kinetics": "elementary"|"empirical", "reversible": bool,
            "k_f": {"value", "units"}, "k_r": {"value", "units"}?, "forward_orders": [...]?, "reverse_orders": [...]?,
            "conditions": {"T_K": [lo, hi], "conc_max_mol_m3"?, "phase", "standard_state"},
            "assumptions": [..non-empty..], "validation": {"benchmark", ...}?}}}

    ``issue_receipt`` opens the artifact, recomputes its digest, and only if the law's numbers/units/orders/domain
    equal the entry's issues an AdmissionReceipt carrying a SourceBinding.  A source is CURRENT iff its file still
    hashes to the digest bound at issue, says status 'current', and no other artifact in the store supersedes it.
    The store reads the disk each call (small files; a revision must be visible immediately)."""

    def __init__(self, root):
        self.root = Path(root).resolve()

    # -- reading ----------------------------------------------------------------------------------
    def _path(self, record_id: str, version: str) -> Path:
        for part in (record_id, version):
            if not part or "/" in part or "\\" in part or part.startswith(".") or "@" in part:
                raise _bad(f"bad source id/version {part!r}", ConversionRefusalKind.PROVENANCE_MISSING)
        return self.root / f"{record_id}@{version}.json"

    def _load(self, record_id: str, version: str):
        path = self._path(record_id, version)
        if not path.is_file():
            raise _bad(f"no source artifact {record_id}@{version} in {self.root}; nothing was inspected",
                       ConversionRefusalKind.PROVENANCE_MISSING)
        try:
            art = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            raise _bad(f"unreadable source artifact {path.name}: {exc}") from exc
        if not isinstance(art, dict) or art.get("record_id") != record_id or art.get("version") != version:
            raise _bad(f"artifact {path.name} does not identify itself as {record_id}@{version}")
        return art, _digest("SourceArtifact", art)

    def _superseded_by_other(self, record_id: str, version: str) -> bool:
        if not self.root.is_dir():
            return False
        for f in self.root.glob(f"{record_id}@*.json"):
            try:
                other = json.loads(f.read_text())
            except (OSError, ValueError):
                continue
            if (isinstance(other, dict) and other.get("supersedes") == version
                    and other.get("status", "current") == "current"):
                return True
        return False

    def is_current(self, binding: SourceBinding) -> bool:
        if str(self.root) != binding.store_root:
            return False
        try:
            art, digest = self._load(binding.record_id, binding.version)
        except ConversionRefusal:
            return False
        return (digest == binding.artifact_digest and art.get("status") == "current"
                and not self._superseded_by_other(binding.record_id, binding.version))

    # -- inspection -------------------------------------------------------------------------------
    @staticmethod
    def _entry_params(entry: dict) -> dict:
        try:
            kf, kr = entry["k_f"], entry.get("k_r")
            conds = entry["conditions"]
            T = conds["T_K"]
            return dict(kinetics=entry["kinetics"], reversible=bool(entry["reversible"]), k_f=kf["value"],
                        k_r=None if kr is None else kr["value"], k_f_units=kf["units"],
                        k_r_units="" if kr is None else kr["units"], forward_orders=entry.get("forward_orders"),
                        reverse_orders=entry.get("reverse_orders"), validity_T_K=(T[0], T[1]))
        except (KeyError, TypeError, IndexError) as exc:
            raise _bad(f"source entry is missing a required parameter field: {exc!r}") from exc

    def issue_receipt(self, record_id: str, version: str, entry_id: str, *, k_f, k_r, reversible, k_f_units,
                      k_r_units, kinetics="elementary", forward_orders=None, reverse_orders=None,
                      validity_T_K=None) -> AdmissionReceipt:
        art, digest = self._load(record_id, version)
        if art.get("status") != "current" or self._superseded_by_other(record_id, version):
            raise _bad(f"{record_id}@{version} is not a current source (status {art.get('status')!r} or superseded)")
        entry = (art.get("entries") or {}).get(entry_id)
        if not isinstance(entry, dict):
            raise _bad(f"{record_id}@{version} has no entry {entry_id!r}")
        want = self._entry_params(entry)
        have = law_params_digest(kinetics=kinetics, reversible=reversible, k_f=k_f, k_r=k_r, k_f_units=k_f_units,
                                 k_r_units=k_r_units, forward_orders=forward_orders, reverse_orders=reverse_orders,
                                 validity_T_K=validity_T_K)
        if have != law_params_digest(**want):
            raise _bad(f"the law's rate/units/orders/domain differ from {record_id}@{version}:{entry_id}; a "
                       "citation certifies only the numbers it actually states")
        conds = entry["conditions"]
        for req in ("phase", "standard_state"):
            if not str(conds.get(req, "")).strip():
                raise _bad(f"source entry must state conditions.{req}", ConversionRefusalKind.PROVENANCE_MISSING)
        assumptions = tuple(str(x) for x in entry.get("assumptions") or () if str(x).strip())
        if not assumptions:
            raise _bad("source entry must state its experimental/numerical assumptions",
                       ConversionRefusalKind.PROVENANCE_MISSING)

        def side(items):
            acc: dict = {}
            for it in items:
                n = int(it["count"])
                if n < 1:
                    raise _bad("source entry species counts must be >= 1")
                k = identity_key(parse_smiles(it["smiles"]))
                acc[k] = acc.get(k, 0) + n
            return tuple(sorted(acc.items(), key=lambda kv: repr(kv[0])))
        try:
            reactants, products = side(entry["reactants"]), side(entry["products"])
        except (KeyError, TypeError, ValueError) as exc:
            raise _bad(f"source entry species are not inspectable: {exc!r}") from exc
        val = entry.get("validation")
        bench = str(val.get("benchmark", "")).strip() if isinstance(val, dict) else ""
        cmax = conds.get("conc_max_mol_m3")
        binding = SourceBinding._mint(
            _MINT, store_root=str(self.root), record_id=record_id, version=version, entry_id=entry_id,
            artifact_digest=digest, params_digest=have, reactants=reactants, products=products,
            T_K=tuple(float(x) for x in conds["T_K"]), conc_max_mol_m3=None if cmax is None else float(cmax),
            phase=str(conds["phase"]), standard_state=str(conds["standard_state"]), assumptions=assumptions,
            benchmark=bench)
        record = SourceRecord(str(art.get("title") or record_id), version,
                              tuple(it["smiles"] for it in list(entry["reactants"]) + list(entry["products"])),
                              f"{k_f_units}", json.dumps(conds, sort_keys=True), f"{kinetics}", f"T_K {conds['T_K']}")
        rec = AdmissionReceipt(record, VerificationStatus.VERIFIED, reviewer=f"SourceStore@{self.root}",
                               benchmark=bench)
        object.__setattr__(rec, "binding", binding)
        return rec

    def law_from_source(self, record_id: str, version: str, entry_id: str, *, level=None) -> "KineticLaw":
        """Build a KineticLaw whose numbers come FROM the inspected artifact (the safest way to hold a verified law)."""
        level = AdmissionLevel.SOURCE_VERIFIED if level is None else level
        art, _ = self._load(record_id, version)
        entry = (art.get("entries") or {}).get(entry_id)
        if not isinstance(entry, dict):
            raise _bad(f"{record_id}@{version} has no entry {entry_id!r}")
        p = self._entry_params(entry)
        rec = self.issue_receipt(record_id, version, entry_id, **p)
        return KineticLaw(p["k_f"], p["k_r"], p["reversible"], level, p["k_f_units"], p["k_r_units"], p["kinetics"],
                          _tup(p["forward_orders"]), _tup(p["reverse_orders"]), receipt=rec,
                          validity_T_K=tuple(float(x) for x in p["validity_T_K"]))


def _tup(x):
    return None if x is None else tuple(x)


DEFAULT_STORE = SourceStore(Path(__file__).resolve().parent / "verified_sources")


@dataclass(frozen=True)
class AdmissionPolicy:
    """ADMISSION: which verifier roots this reader trusts.  A binding from any other store is a genuine inspection
    of SOMEONE's directory -- but not admitted here.  The default policy trusts DEFAULT_STORE only."""
    stores: tuple = ()

    def trusts(self, binding: SourceBinding) -> bool:
        return any(str(st.root) == binding.store_root for st in self.stores)

    def current(self, binding: SourceBinding) -> bool:
        """Trusted AND the trusted store still says this exact source is current."""
        return any(str(st.root) == binding.store_root and st.is_current(binding) for st in self.stores)


DEFAULT_POLICY = AdmissionPolicy((DEFAULT_STORE,))


# ------------------------------------------------------------------------------------------- units
def _fmt_exp(base: str, e: float) -> str:
    if e == 0:
        return ""
    e = int(e) if float(e).is_integer() else e
    return base if e == 1 else f"{base}^{e}"


def expected_rate_constant_units(total_order: float) -> str:
    """SI units of a mass-action rate constant for overall kinetic order n: rate [mol m^-3 s^-1] = k [conc^n].
    k has m^(3(n-1)) mol^(1-n) s^-1."""
    n = total_order
    parts = [_fmt_exp("m", 3 * (n - 1)), _fmt_exp("mol", 1 - n), "s^-1"]
    return " ".join(p for p in parts if p)


# ------------------------------------------------------------------------------------------- kinetic law
def _finite_nonneg(x) -> bool:
    return (isinstance(x, (int, float, np.integer, np.floating)) and not isinstance(x, bool)
            and math.isfinite(x) and x >= 0)


@dataclass(frozen=True)
class KineticLaw:
    """One reaction's ADMITTED mass-action law.  Never defaulted: every field that matters is explicit.

    kinetics 'elementary' => orders are the complex multiplicities; 'empirical' => forward_orders (and
    reverse_orders if reversible) per species are REQUIRED and are never inferred.  ``k_*_units`` must equal the SI
    units implied by the overall order (checked on conversion).  ``admission`` is a strictly-typed AdmissionLevel:
    SYNTHETIC needs a non-empty ``assumption``; SOURCE_DECLARED needs a non-empty ``source`` citation;
    SOURCE_VERIFIED / BENCHMARK_VALIDATED need an AdmissionReceipt whose status is VERIFIED (and, for the
    benchmark level, a named benchmark)."""
    k_f: Optional[float]
    k_r: Optional[float]
    reversible: bool
    admission: AdmissionLevel
    k_f_units: str = ""
    k_r_units: str = ""
    kinetics: str = "elementary"
    forward_orders: Optional[tuple] = None
    reverse_orders: Optional[tuple] = None
    source: str = ""
    assumption: str = ""
    receipt: Optional[AdmissionReceipt] = None
    validity_T_K: Optional[tuple] = None      # (lo, hi) if the law is only valid in a window

    def __post_init__(self):
        if self.kinetics not in ("elementary", "empirical"):
            raise ConversionRefusal(ConversionRefusalKind.INVALID_KINETIC_LAW, f"unknown kinetics {self.kinetics!r}")
        # A1: the admission value MUST be an AdmissionLevel -- an unknown string / int / None / enum lookalike is a
        # fail-closed refusal, never silently treated as sourced.  (A type annotation is not runtime validation.)
        if not isinstance(self.admission, AdmissionLevel):
            raise ConversionRefusal(ConversionRefusalKind.ADMISSION_INVALID,
                                    f"admission must be an AdmissionLevel, got {self.admission!r} "
                                    f"({type(self.admission).__name__})")
        A = AdmissionLevel
        if self.admission == A.SYNTHETIC:
            if not self.assumption.strip():
                raise ConversionRefusal(ConversionRefusalKind.PROVENANCE_MISSING,
                                        "a SYNTHETIC law must state its hypothetical assumption")
        elif self.admission == A.SOURCE_DECLARED:
            if not self.source.strip():
                raise ConversionRefusal(ConversionRefusalKind.PROVENANCE_MISSING,
                                        "a SOURCE_DECLARED law must carry a source citation")
        else:  # SOURCE_VERIFIED or BENCHMARK_VALIDATED
            if not isinstance(self.receipt, AdmissionReceipt):
                raise ConversionRefusal(ConversionRefusalKind.ADMISSION_INVALID,
                                        f"{self.admission.value} requires an AdmissionReceipt (a structured, "
                                        "content-identified source record), not a bare citation string")
            if self.receipt.status != VerificationStatus.VERIFIED:
                raise ConversionRefusal(ConversionRefusalKind.ADMISSION_INVALID,
                                        f"{self.admission.value} requires a VERIFIED receipt; receipt status is "
                                        f"{self.receipt.status.value}")
            # Wave B1: a label is not a binding.  A receipt that merely SAYS verified is a declaration; the law
            # needs the verifier-issued SourceBinding (init=False on the receipt, minted only by SourceStore).
            if not self.receipt.is_inspected:
                raise ConversionRefusal(ConversionRefusalKind.ADMISSION_INVALID,
                                        f"{self.admission.value} requires a receipt issued by a SourceStore "
                                        "verifier (an inspected source binding); a receipt built from caller "
                                        "statements is only a declaration")
            # Wave B2: the binding certifies THESE numbers only.  Swap a rate/unit/order/window under the same
            # citation and the digest no longer matches -> not certified.
            if self.receipt.binding.params_digest != self.params_digest():
                raise ConversionRefusal(ConversionRefusalKind.ADMISSION_INVALID,
                                        "the law's rate/units/orders/domain differ from the inspected source "
                                        f"{self.receipt.binding.record_id}@{self.receipt.binding.version}:"
                                        f"{self.receipt.binding.entry_id}; the receipt certifies only what the "
                                        "source states")
            if self.admission == A.BENCHMARK_VALIDATED and not self.receipt.binding.benchmark:
                raise ConversionRefusal(ConversionRefusalKind.ADMISSION_INVALID,
                                        "BENCHMARK_VALIDATED requires the inspected SOURCE ARTIFACT to carry an "
                                        "independent validation block; a receipt string cannot declare one")
        if self.validity_T_K is not None:
            lo, hi = self.validity_T_K
            if not (_finite_nonneg(lo) and _finite_nonneg(hi) and 0 < lo <= hi):
                raise ConversionRefusal(ConversionRefusalKind.INVALID_KINETIC_LAW, "validity_T_K must be 0<lo<=hi")

    @property
    def is_complete(self) -> bool:
        return self.k_f is not None and (self.k_r is not None or not self.reversible)

    def params_digest(self) -> str:
        return law_params_digest(kinetics=self.kinetics, reversible=self.reversible, k_f=self.k_f, k_r=self.k_r,
                                 k_f_units=self.k_f_units, k_r_units=self.k_r_units,
                                 forward_orders=self.forward_orders, reverse_orders=self.reverse_orders,
                                 validity_T_K=self.validity_T_K)


# ------------------------------------------------------------------------------------------- descriptive
@dataclass(frozen=True, eq=False)
class DescriptiveMechanism:
    """Verified structure; thermo/kinetic facets optional and possibly UNKNOWN.  NEVER executable.

    ``recognized_family`` is advisory text (e.g. a reaction recognizer's verdict).  It confers NO authority.
    ``species_identity`` records whether the compositions were caller-DECLARED (UNTRUSTED, the public constructor)
    or bound to real Molecule identities (VERIFIED, via from_derivations)."""
    species: tuple
    compositions: tuple
    charges: tuple
    reactant: np.ndarray            # (S, R) int64
    product: np.ndarray
    reaction_labels: tuple
    kinetics: tuple                 # per reaction: KineticLaw or None (= UNKNOWN)
    thermo: dict = field(default_factory=dict)   # facet name -> value or None (= UNKNOWN)
    recognized_family: Optional[str] = None
    # species identity is NOT a public constructor argument (evil-morty Round IV Finding 1): a hand construction
    # cannot DECLARE itself VERIFIED.  It defaults UNTRUSTED and is stamped VERIFIED only by from_derivations, which
    # binds every species to a real Molecule identity key -- so no forged composition table can mint the claim.
    species_identity: SpeciesIdentity = field(init=False, default=SpeciesIdentity.UNTRUSTED)
    species_identities: tuple = field(init=False, default=())   # per-species identity keys when VERIFIED
    E: np.ndarray = field(init=False)
    element_labels: tuple = field(init=False)
    N: np.ndarray = field(init=False)

    def __post_init__(self):
        S = len(self.species)
        reactant = np.array(self.reactant, dtype=np.int64)
        product = np.array(self.product, dtype=np.int64)
        if reactant.ndim != 2 or reactant.shape != product.shape or reactant.shape[0] != S:
            raise ConversionRefusal(ConversionRefusalKind.SELECTION_INVALID, "complex matrices must be (S, R)")
        if np.any(reactant < 0) or np.any(product < 0):
            raise ConversionRefusal(ConversionRefusalKind.SELECTION_INVALID, "complex multiplicities must be >= 0")
        R = reactant.shape[1]
        if len(self.reaction_labels) != R or len(self.kinetics) != R:
            raise ConversionRefusal(ConversionRefusalKind.SELECTION_INVALID, "one label and one kinetics slot per reaction")
        if len(set(self.species)) != S:
            raise ConversionRefusal(ConversionRefusalKind.SELECTION_INVALID, "species names must be unique")
        if any(k is not None and not isinstance(k, KineticLaw) for k in self.kinetics):
            raise ConversionRefusal(ConversionRefusalKind.INVALID_KINETIC_LAW, "kinetics slots are KineticLaw or None")
        labels, E = build_E(self.compositions, self.charges)        # DERIVED here; no E can be passed in
        N = product - reactant
        if not np.any(E):
            raise ConversionRefusal(ConversionRefusalKind.INVENTORY_REFUSED, "vacuous inventory")
        if np.any(E @ N != 0):
            raise ConversionRefusal(ConversionRefusalKind.INVENTORY_REFUSED,
                                    f"derived E @ N != 0:\n{E @ N}")
        for arr in (reactant, product, N, E):
            arr.setflags(write=False)
        object.__setattr__(self, "reactant", reactant)
        object.__setattr__(self, "product", product)
        object.__setattr__(self, "E", E)
        object.__setattr__(self, "N", N)
        object.__setattr__(self, "element_labels", labels)

    # -- authority ---------------------------------------------------------------------------------
    @property
    def is_executable(self) -> bool:
        return False

    @property
    def unknowns(self) -> tuple:
        out = [f"kinetics[{lab}]" for lab, k in zip(self.reaction_labels, self.kinetics) if k is None or not k.is_complete]
        out += [f"thermo.{name}" for name, v in sorted(self.thermo.items()) if v is None]
        return tuple(out)

    # -- construction ------------------------------------------------------------------------------
    @classmethod
    def from_derivations(cls, derivations: Sequence[InventoryDerivation], *, reaction_labels=None,
                         kinetics=None, thermo=None, recognized_family: Optional[str] = None
                         ) -> "DescriptiveMechanism":
        """Merge verified single-reaction derivations (species unified by identity) into one descriptive mechanism.
        The result is species-identity VERIFIED: every species is bound to a real Molecule identity key."""
        if not derivations:
            raise ConversionRefusal(ConversionRefusalKind.SELECTION_INVALID, "no reactions selected")
        keys, names, comps, charges = [], [], [], []
        for d in derivations:
            for k, n, c, q in zip(d.identities, d.species, d.compositions, d.charges):
                if k not in keys:
                    keys.append(k)
                    names.append(n)
                    comps.append(c)
                    charges.append(q)
        S, R = len(keys), len(derivations)
        reactant = np.zeros((S, R), dtype=np.int64)
        product = np.zeros((S, R), dtype=np.int64)
        for j, d in enumerate(derivations):
            for i, k in enumerate(d.identities):
                reactant[keys.index(k), j] = d.reactant[i, 0]
                product[keys.index(k), j] = d.product[i, 0]
        labels = tuple(reaction_labels) if reaction_labels is not None else tuple(f"R{j}" for j in range(R))
        obj = cls(tuple(names), tuple(comps), tuple(charges), reactant, product, labels,
                  tuple(kinetics) if kinetics is not None else (None,) * R, dict(thermo or {}), recognized_family)
        # the ONLY path that may stamp VERIFIED: these species ARE bound to real Molecule identities (the keys
        # come from InventoryDerivation, which the adapter derived from real Molecule.formula/charge).
        object.__setattr__(obj, "species_identity", SpeciesIdentity.VERIFIED)
        object.__setattr__(obj, "species_identities", tuple(keys))
        return obj

    # -- conversion --------------------------------------------------------------------------------
    def to_executable(self, laws: Optional[Sequence] = None, *, omissions: Sequence = (),
                      selected: Optional[Sequence] = None) -> "ExecutableMechanism":
        """Promote to executable.  REQUIRES one admitted law per selected reaction (``laws`` overrides this
        mechanism's own facets), a non-empty list of omissions of competing chemistry, and valid units.  The
        species-identity axis is carried through unchanged (an UNTRUSTED descriptive stays UNTRUSTED executable).

        Refuses with KINETICS_UNAVAILABLE on any missing / incomplete law -- never invents a rate, never a zero."""
        sel = tuple(range(len(self.reaction_labels))) if selected is None else tuple(selected)
        if not sel or len(set(sel)) != len(sel) or any(type(j) is not int or not (0 <= j < len(self.reaction_labels))
                                                      for j in sel):
            raise ConversionRefusal(ConversionRefusalKind.SELECTION_INVALID, f"bad reaction selection {selected!r}")
        chosen = tuple(laws) if laws is not None else tuple(self.kinetics[j] for j in sel)
        if len(chosen) != len(sel):
            raise ConversionRefusal(ConversionRefusalKind.KINETICS_UNAVAILABLE,
                                    f"{len(chosen)} laws supplied for {len(sel)} selected reactions")
        for j, law in zip(sel, chosen):
            if law is None or not isinstance(law, KineticLaw) or not law.is_complete:
                raise ConversionRefusal(ConversionRefusalKind.KINETICS_UNAVAILABLE,
                                        f"reaction {self.reaction_labels[j]!r} has no complete admitted kinetic "
                                        "law; a recognizer naming its family is not a rate law")
        if not [o for o in omissions if isinstance(o, str) and o.strip()]:
            raise ConversionRefusal(ConversionRefusalKind.OMISSIONS_UNDECLARED,
                                    "an executable mechanism must explicitly list the competing chemistry it omits")
        ex = ExecutableMechanism(self.species, self.compositions, self.charges,
                                 self.reactant[:, sel], self.product[:, sel],
                                 tuple(self.reaction_labels[j] for j in sel), chosen, tuple(omissions))
        if self.species_identity == SpeciesIdentity.VERIFIED:   # carry the trusted binding through the conversion
            object.__setattr__(ex, "species_identity", SpeciesIdentity.VERIFIED)
            object.__setattr__(ex, "species_identities", self.species_identities)
            # Wave B2: bind each inspected source to THIS reaction.  The source's reactant/product species (as real
            # Molecule identity keys) must equal this column's sides; a correct source for a DIFFERENT reaction
            # must not certify this one, whatever the citation text says.  Only this trusted path stamps it.
            bound = []
            for j, law in enumerate(chosen):
                b = law.receipt.binding if law.receipt is not None else None
                if b is None:
                    bound.append(False)
                    continue
                side_r = {k: int(ex.reactant[i, j]) for i, k in enumerate(self.species_identities)}
                side_p = {k: int(ex.product[i, j]) for i, k in enumerate(self.species_identities)}
                if not b.structure_matches(side_r, side_p):
                    raise ConversionRefusal(
                        ConversionRefusalKind.SOURCE_MISMATCH,
                        f"inspected source {b.record_id}@{b.version}:{b.entry_id} describes a different "
                        f"reaction (species/sides) than {ex.reaction_labels[j]!r}; it cannot certify this one")
                bound.append(True)
            object.__setattr__(ex, "structure_bound", tuple(bound))
        return ex


# ------------------------------------------------------------------------------------------- executable
@dataclass(frozen=True, eq=False)
class ExecutableMechanism:
    """A selected, fully-lawed reaction set.  Construct via ``DescriptiveMechanism.to_executable``; the
    constructor re-validates everything itself so a hand-built instance gets no free pass -- in particular a
    hand-built instance is species-identity UNTRUSTED by default and so can never claim verified chemistry."""
    species: tuple
    compositions: tuple
    charges: tuple
    reactant: np.ndarray
    product: np.ndarray
    reaction_labels: tuple
    laws: tuple
    omissions: tuple
    # NOT public constructor arguments (evil-morty Finding 1): a hand-built ExecutableMechanism is UNTRUSTED and
    # cannot claim verified chemistry.  Only to_executable (from a from_derivations-built descriptive) stamps VERIFIED.
    species_identity: SpeciesIdentity = field(init=False, default=SpeciesIdentity.UNTRUSTED)
    species_identities: tuple = field(init=False, default=())
    # per-law: True only if to_executable confirmed the inspected source's species/sides == this reaction column.
    # init=False: a hand-built ExecutableMechanism has NO structure binding, so its verified laws cap at DECLARED.
    structure_bound: tuple = field(init=False, default=())
    E: np.ndarray = field(init=False)
    element_labels: tuple = field(init=False)
    N: np.ndarray = field(init=False)

    def __post_init__(self):
        reactant = np.array(self.reactant, dtype=np.int64)
        product = np.array(self.product, dtype=np.int64)
        S, R = len(self.species), reactant.shape[1] if reactant.ndim == 2 else -1
        if reactant.shape != (S, R) or product.shape != (S, R) or len(self.laws) != R or len(self.reaction_labels) != R:
            raise ConversionRefusal(ConversionRefusalKind.SELECTION_INVALID, "shape mismatch in executable mechanism")
        if np.any(reactant < 0) or np.any(product < 0):
            raise ConversionRefusal(ConversionRefusalKind.SELECTION_INVALID, "complex multiplicities must be >= 0")
        for j, law in enumerate(self.laws):
            if not isinstance(law, KineticLaw) or not law.is_complete:
                raise ConversionRefusal(ConversionRefusalKind.KINETICS_UNAVAILABLE, f"reaction {j} lacks a complete law")
            for nm, v in (("k_f", law.k_f), ("k_r", law.k_r if law.reversible else 0.0)):
                if not _finite_nonneg(v):
                    raise ConversionRefusal(ConversionRefusalKind.INVALID_KINETIC_LAW,
                                            f"reaction {j} {nm}={v!r} must be a finite non-negative number")
            of, orr = self._orders(j, law, reactant, product)
            self._check_units(j, law, of, orr)
        if not [o for o in self.omissions if isinstance(o, str) and o.strip()]:
            raise ConversionRefusal(ConversionRefusalKind.OMISSIONS_UNDECLARED, "omissions must be declared")
        labels, E = build_E(self.compositions, self.charges)
        N = product - reactant
        if not np.any(E) or np.any(E @ N != 0):
            raise ConversionRefusal(ConversionRefusalKind.INVENTORY_REFUSED, "derived E @ N != 0 (or vacuous)")
        for arr in (reactant, product, N, E):
            arr.setflags(write=False)
        object.__setattr__(self, "reactant", reactant)
        object.__setattr__(self, "product", product)
        object.__setattr__(self, "E", E)
        object.__setattr__(self, "N", N)
        object.__setattr__(self, "element_labels", labels)

    @staticmethod
    def _orders(j, law, reactant, product):
        if law.kinetics == "elementary":
            return reactant[:, j].astype(float), product[:, j].astype(float)
        S = reactant.shape[0]
        if law.forward_orders is None or len(law.forward_orders) != S:
            raise ConversionRefusal(ConversionRefusalKind.INVALID_KINETIC_LAW,
                                    f"reaction {j}: empirical law needs explicit forward_orders of length {S}")
        if law.reversible and (law.reverse_orders is None or len(law.reverse_orders) != S):
            raise ConversionRefusal(ConversionRefusalKind.INVALID_KINETIC_LAW,
                                    f"reaction {j}: reversible empirical law needs explicit reverse_orders")
        of = np.array(law.forward_orders, dtype=float)
        orr = np.array(law.reverse_orders, dtype=float) if law.reverse_orders is not None else np.zeros(S)
        if not (np.all(np.isfinite(of)) and np.all(np.isfinite(orr)) and np.all(of >= 0) and np.all(orr >= 0)):
            raise ConversionRefusal(ConversionRefusalKind.INVALID_KINETIC_LAW, f"reaction {j}: orders must be finite >= 0")
        return of, orr

    @staticmethod
    def _check_units(j, law, of, orr):
        want_f = expected_rate_constant_units(float(of.sum()))
        if law.k_f_units != want_f:
            raise ConversionRefusal(ConversionRefusalKind.DIMENSION_MISMATCH,
                                    f"reaction {j}: k_f units {law.k_f_units!r} != expected {want_f!r} for overall "
                                    f"forward order {float(of.sum()):g}")
        if law.reversible:
            want_r = expected_rate_constant_units(float(orr.sum()))
            if law.k_r_units != want_r:
                raise ConversionRefusal(ConversionRefusalKind.DIMENSION_MISMATCH,
                                        f"reaction {j}: k_r units {law.k_r_units!r} != expected {want_r!r}")

    @property
    def is_executable(self) -> bool:
        return True

    def law_levels(self, policy: Optional[AdmissionPolicy] = None) -> tuple:
        """Per-law EFFECTIVE admission under ``policy`` (default: DEFAULT_POLICY).  A law's declared level is capped
        to SOURCE_DECLARED unless (a) its inspected source is structure-bound to THIS reaction (to_executable
        stamped it), (b) the policy trusts the store that inspected it, and (c) that store still says the exact
        source is current.  So no layer can strengthen a declaration, and an obsolete receipt stops certifying."""
        policy = DEFAULT_POLICY if policy is None else policy
        out = []
        for j, law in enumerate(self.laws):
            lvl = law.admission
            if _ADMISSION_ORDER[lvl] >= _ADMISSION_ORDER[AdmissionLevel.SOURCE_VERIFIED]:
                b = law.receipt.binding if law.receipt is not None else None
                ok = (b is not None and j < len(self.structure_bound) and self.structure_bound[j]
                      and policy.current(b))
                if not ok:
                    lvl = AdmissionLevel.SOURCE_DECLARED
            out.append(lvl)
        return tuple(out)

    def admission_level_under(self, policy: Optional[AdmissionPolicy] = None) -> AdmissionLevel:
        """The WEAKEST law's effective admission caps the mechanism (fail-closed)."""
        return min(self.law_levels(policy), key=lambda a: _ADMISSION_ORDER[a])

    @property
    def admission_level(self) -> AdmissionLevel:
        return self.admission_level_under(DEFAULT_POLICY)

    def admitted_under(self, policy: AdmissionPolicy) -> bool:
        """A scientifically ADMITTED prediction under ``policy``: kinetics >= SOURCE_VERIFIED (inspected, structure-
        bound, trusted, current) AND species bound to VERIFIED molecular identities."""
        return (_ADMISSION_ORDER[self.admission_level_under(policy)] >= _ADMISSION_ORDER[AdmissionLevel.SOURCE_VERIFIED]
                and self.species_identity == SpeciesIdentity.VERIFIED)

    @property
    def scientific_claim(self) -> bool:
        """admitted_under(DEFAULT_POLICY).  A bare citation, a SYNTHETIC law, a caller-assembled receipt, a source
        from an untrusted store, a superseded source, OR forged (UNTRUSTED) species all yield False."""
        return self.admitted_under(DEFAULT_POLICY)

    @property
    def admission_identities(self) -> tuple:
        """Per-law admission identity: (level, receipt.identity or '') -- the EVIDENCE identity, independent of the
        model content.  The receipt identity includes the inspected binding (source id, version, artifact digest),
        so a source revision changes it without touching E / N / stoichiometry."""
        return tuple((law.admission.value, law.receipt.identity if law.receipt is not None else "")
                     for law in self.laws)

    @property
    def model_identity(self) -> str:
        """Content identity of the AUTHORITATIVE scientific model: species identity (the real Molecule keys when
        VERIFIED, else the declared compositions) + stoichiometry + element/charge inventory + per-law kinetic
        content (rates, orders, units, T window).  EXCLUDES admission/evidence (a re-issued identical source or a
        relabel does NOT move it) -- while a changed chemical identity or an actually-revised parameter DOES, so a
        source revision that changes a rate moves BOTH identities, and one that only re-certifies moves evidence
        alone.  The orthogonal companion of admission_identities (the two-digest discipline)."""
        law_content = tuple((law.k_f, law.k_r, law.reversible, law.kinetics,
                             tuple(law.forward_orders) if law.forward_orders is not None else None,
                             tuple(law.reverse_orders) if law.reverse_orders is not None else None,
                             law.k_f_units, law.k_r_units, law.validity_T_K) for law in self.laws)
        species_key = (self.species_identities if self.species_identity == SpeciesIdentity.VERIFIED
                       else self.compositions)
        return _digest("ExecutableModel", self.species_identity.value, tuple(species_key),
                       self.reactant.tolist(), self.product.tolist(), self.E.tolist(), self.element_labels,
                       law_content)

    def to_twocell(self, policy: Optional[AdmissionPolicy] = None) -> Mechanism:
        """The explicit float boundary: hand the exact-integer structure to the (float) twocell solver.

        Wave B3: the numerical Mechanism does NOT shed its admission.  Its ``label`` is the EFFECTIVE level under
        ``policy`` and it carries ``applicability`` -- the per-law T window (every law's validity_T_K, plus the
        inspected source's concentration cap), the policy, and the laws that were source-verified at conversion --
        which twocell.reaction_cell re-checks on EVERY reaction transition (so a changed T, or a source that has
        since been superseded, refuses instead of silently running as science).  Design chosen: carry the
        applicability WITH the (immutable) mechanism, not a separate run-context, because the Mechanism already
        travels unchanged through System / MeshSystem / run -- a side-channel RunAdmission would need a new
        argument threaded through every operator (including mesh.py, not ours) or it would be silently dropped."""
        policy = DEFAULT_POLICY if policy is None else policy
        rates = tuple(ReactionRate(k_f=float(law.k_f), k_r=None if law.k_r is None else float(law.k_r),
                                   reversible=law.reversible) for law in self.laws)
        levels = self.law_levels(policy)
        label = min(levels, key=lambda a: _ADMISSION_ORDER[a]).value
        kw = {}
        if any(law.kinetics == "empirical" for law in self.laws):
            fo = np.zeros(self.reactant.shape)
            ro = np.zeros(self.reactant.shape)
            for j, law in enumerate(self.laws):
                of, orr = self._orders(j, law, self.reactant, self.product)
                fo[:, j], ro[:, j] = of, orr
            kw = dict(kinetics="empirical", forward_orders=fo, reverse_orders=ro)
        domains, guarded = [], []
        for j, (law, lvl) in enumerate(zip(self.laws, levels)):
            b = law.receipt.binding if (law.receipt is not None and
                                        _ADMISSION_ORDER[lvl] >= _ADMISSION_ORDER[AdmissionLevel.SOURCE_VERIFIED]) else None
            domains.append((self.reaction_labels[j], law.validity_T_K, None if b is None else b.conc_max_mol_m3))
            guarded.append(b)
        applicability = Applicability(tuple(domains), tuple(guarded), policy)
        try:
            return Mechanism(self.species, self.reactant.astype(float), self.product.astype(float),
                             self.element_labels, self.E.astype(float), rates, label=label,
                             applicability=applicability, **kw)
        except SandboxError as exc:
            raise ConversionRefusal(ConversionRefusalKind.INVENTORY_REFUSED, str(exc)) from exc


@dataclass(frozen=True, eq=False)
class Applicability:
    """The admitted DOMAIN carried into the numerical Mechanism.  ``domains[j]`` = (reaction label, (T_lo, T_hi) or
    None, conc cap mol/m^3 or None); ``guarded[j]`` = the SourceBinding that was current+trusted+structure-bound
    for reaction j at conversion (None for unsourced laws).  ``assert_applicable`` is called by
    twocell.reaction_cell before every reaction transition; it FAILS CLOSED:
      * a windowed law with no temperature supplied is refused (cannot confirm applicability);
      * T outside the window, or a concentration above the cap, is refused;
      * a law that was verified at conversion but whose source is no longer trusted/current is refused.
    Not enforceable here (UNVERIFIED): pressure and phase -- the twocell state carries neither."""
    domains: tuple
    guarded: tuple
    policy: AdmissionPolicy

    def assert_applicable(self, *, T_K, conc_mol_m3) -> None:
        for (label, window, cmax), b in zip(self.domains, self.guarded):
            if b is not None and not self.policy.current(b):
                raise AdmissionDomainError(
                    f"reaction {label!r}: its admitting source {b.record_id}@{b.version} is no longer current/"
                    "trusted; an obsolete receipt does not certify this transition")
            if window is not None:
                if T_K is None:
                    raise AdmissionDomainError(
                        f"reaction {label!r} is valid only for T in {window} K but the caller supplied no "
                        "temperature; applicability cannot be confirmed (fail closed)")
                if not (window[0] <= float(T_K) <= window[1]):
                    raise AdmissionDomainError(
                        f"reaction {label!r}: T={float(T_K):g} K is outside its admitted window {window} K; "
                        "this is not a supported prediction there")
            if cmax is not None and conc_mol_m3 is not None and float(np.max(conc_mol_m3, initial=0.0)) > cmax:
                raise AdmissionDomainError(
                    f"reaction {label!r}: concentration {float(np.max(conc_mol_m3)):g} mol/m^3 exceeds the "
                    f"admitted cap {cmax:g}")


__all__ = ["ConversionRefusal", "ConversionRefusalKind", "AdmissionLevel", "VerificationStatus", "SpeciesIdentity",
           "SourceRecord", "AdmissionReceipt", "SourceBinding", "SourceStore", "AdmissionPolicy", "DEFAULT_STORE",
           "DEFAULT_POLICY", "Applicability", "AdmissionDomainError", "law_params_digest", "KineticLaw",
           "DescriptiveMechanism", "ExecutableMechanism", "expected_rate_constant_units", "AdapterRefusal",
           "RefusalKind"]
