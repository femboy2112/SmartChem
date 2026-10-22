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

Floats appear only at the explicit boundary ExecutableMechanism.to_twocell (the twocell solver is float).
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Sequence

import numpy as np

from experiments.sandbox_foundation.mechanism_adapter import (
    AdapterRefusal, InventoryDerivation, RefusalKind, build_E)
from experiments.sandbox_foundation.twocell import Mechanism, ReactionRate, SandboxError


class ConversionRefusalKind(str, Enum):
    KINETICS_UNAVAILABLE = "KINETICS_UNAVAILABLE"
    INVALID_KINETIC_LAW = "INVALID_KINETIC_LAW"
    DIMENSION_MISMATCH = "DIMENSION_MISMATCH"
    PROVENANCE_MISSING = "PROVENANCE_MISSING"
    OMISSIONS_UNDECLARED = "OMISSIONS_UNDECLARED"
    SELECTION_INVALID = "SELECTION_INVALID"
    INVENTORY_REFUSED = "INVENTORY_REFUSED"
    ADMISSION_INVALID = "ADMISSION_INVALID"          # bad admission level / missing-or-unverified receipt


class ConversionRefusal(Exception):
    def __init__(self, kind: ConversionRefusalKind, detail: str):
        super().__init__(f"{kind.value}: {detail}")
        self.kind = kind
        self.detail = detail


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
    """A source-specific identity for a verified admission.  Its content digest IS its identity, so ANY source
    update (edition, parameters, conditions, species, range) changes the admission identity -- the old receipt
    cannot be silently reused for new data."""
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


@dataclass(frozen=True)
class AdmissionReceipt:
    """A reviewed admission receipt binding a rate law to a verified SourceRecord + a re-verification status.  Its
    identity includes the status, so a REVOKED receipt is a distinct identity from the VERIFIED one it replaces."""
    record: SourceRecord
    status: VerificationStatus
    reviewer: str = ""            # the policy / reviewer that performed the check
    benchmark: str = ""           # for BENCHMARK_VALIDATED: the independent physical benchmark passed

    def __post_init__(self):
        if not isinstance(self.record, SourceRecord):
            raise ConversionRefusal(ConversionRefusalKind.ADMISSION_INVALID, "receipt.record must be a SourceRecord")
        if not isinstance(self.status, VerificationStatus):
            raise ConversionRefusal(ConversionRefusalKind.ADMISSION_INVALID,
                                    f"receipt.status must be a VerificationStatus, got {self.status!r}")

    @property
    def identity(self) -> str:
        return _digest("AdmissionReceipt", self.record.identity, self.status.value, self.reviewer, self.benchmark)


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
            if self.admission == A.BENCHMARK_VALIDATED and not self.receipt.benchmark.strip():
                raise ConversionRefusal(ConversionRefusalKind.ADMISSION_INVALID,
                                        "BENCHMARK_VALIDATED requires the receipt to name the benchmark passed")
        if self.validity_T_K is not None:
            lo, hi = self.validity_T_K
            if not (_finite_nonneg(lo) and _finite_nonneg(hi) and 0 < lo <= hi):
                raise ConversionRefusal(ConversionRefusalKind.INVALID_KINETIC_LAW, "validity_T_K must be 0<lo<=hi")

    @property
    def is_complete(self) -> bool:
        return self.k_f is not None and (self.k_r is not None or not self.reversible)


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

    @property
    def admission_level(self) -> AdmissionLevel:
        """The WEAKEST law's admission caps the mechanism (fail-closed): a single SYNTHETIC or SOURCE_DECLARED law
        pulls the whole mechanism down to that level."""
        return min((law.admission for law in self.laws), key=lambda a: _ADMISSION_ORDER[a])

    @property
    def scientific_claim(self) -> bool:
        """True only if BOTH axes are satisfied: kinetics admission >= SOURCE_VERIFIED AND the species are bound to
        VERIFIED molecular identities.  A bare citation (SOURCE_DECLARED), a SYNTHETIC law, OR a forged /
        caller-declared composition table (UNTRUSTED species) all yield False."""
        return (_ADMISSION_ORDER[self.admission_level] >= _ADMISSION_ORDER[AdmissionLevel.SOURCE_VERIFIED]
                and self.species_identity == SpeciesIdentity.VERIFIED)

    @property
    def admission_identities(self) -> tuple:
        """Per-law admission identity: (level, receipt.identity or '') -- the EVIDENCE identity, independent of the
        model content.  A source update / revocation changes these without touching E / N / stoichiometry."""
        return tuple((law.admission.value, law.receipt.identity if law.receipt is not None else "")
                     for law in self.laws)

    @property
    def model_identity(self) -> str:
        """Content identity of the AUTHORITATIVE scientific model: species identity (the real Molecule keys when
        VERIFIED, else the declared compositions) + stoichiometry + element/charge inventory + per-law kinetic
        content.  EXCLUDES admission/evidence (so a source revision or a relabel does NOT move it) -- while a
        changed chemical identity or a changed kinetic parameter DOES.  The orthogonal companion of
        admission_identities (model identity _|_ evidence identity, the two-digest discipline)."""
        law_content = tuple((law.k_f, law.k_r, law.reversible, law.kinetics,
                             tuple(law.forward_orders) if law.forward_orders is not None else None,
                             tuple(law.reverse_orders) if law.reverse_orders is not None else None,
                             law.k_f_units, law.k_r_units, law.validity_T_K) for law in self.laws)
        species_key = (self.species_identities if self.species_identity == SpeciesIdentity.VERIFIED
                       else self.compositions)
        return _digest("ExecutableModel", self.species_identity.value, tuple(species_key),
                       self.reactant.tolist(), self.product.tolist(), self.E.tolist(), self.element_labels,
                       law_content)

    def to_twocell(self) -> Mechanism:
        """The explicit float boundary: hand the exact-integer structure to the (float) twocell solver."""
        rates = tuple(ReactionRate(k_f=float(law.k_f), k_r=None if law.k_r is None else float(law.k_r),
                                   reversible=law.reversible) for law in self.laws)
        label = self.admission_level.value
        kw = {}
        if any(law.kinetics == "empirical" for law in self.laws):
            fo = np.zeros(self.reactant.shape)
            ro = np.zeros(self.reactant.shape)
            for j, law in enumerate(self.laws):
                of, orr = self._orders(j, law, self.reactant, self.product)
                fo[:, j], ro[:, j] = of, orr
            kw = dict(kinetics="empirical", forward_orders=fo, reverse_orders=ro)
        try:
            return Mechanism(self.species, self.reactant.astype(float), self.product.astype(float),
                             self.element_labels, self.E.astype(float), rates, label=label, **kw)
        except SandboxError as exc:
            raise ConversionRefusal(ConversionRefusalKind.INVENTORY_REFUSED, str(exc)) from exc


__all__ = ["ConversionRefusal", "ConversionRefusalKind", "AdmissionLevel", "VerificationStatus", "SpeciesIdentity",
           "SourceRecord", "AdmissionReceipt", "KineticLaw", "DescriptiveMechanism", "ExecutableMechanism",
           "expected_rate_constant_units", "AdapterRefusal", "RefusalKind"]
