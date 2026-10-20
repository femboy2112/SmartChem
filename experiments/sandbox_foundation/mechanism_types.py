"""Typed authority for mechanisms: Descriptive (inspect) vs Executable (run) -- Wave A2.

Resolves the standing V2.0 ambiguity.  Yeah, naming a reaction family is not the same as having a rate law,
and this module makes that a type error instead of a vibe.

* ``DescriptiveMechanism``  -- verified species + stoichiometry + element/charge inventory, with OPTIONAL
  thermo / kinetic facets that may be explicitly UNKNOWN (None).  For inspection.  ``is_executable`` is always
  False, and nothing about it -- including a recognizer's family name -- can change that.
* ``ExecutableMechanism``   -- an explicitly selected finite reaction set, COMPLETE admitted kinetic laws for
  exactly that selection, dimension-checked units, a structural inventory it re-derives itself, provenance, and
  explicit omissions of competing chemistry.  Its E is NOT a constructor argument (``init=False``): it is
  derived in ``__post_init__`` from compositions+charges, so a forged E cannot even be passed in.
* Conversion ``DescriptiveMechanism.to_executable`` REQUIRES laws.  A missing/None law is a typed
  ``KINETICS_UNAVAILABLE`` refusal, never a fabricated rate and never a silent zero.
* Two provenances.  SOURCED needs a non-empty source citation.  SYNTHETIC needs a non-empty assumption
  statement and yields a mechanism whose ``scientific_claim`` is False: hypothetical user rate laws run, but are
  never relabelled as sourced science.  Any SYNTHETIC law makes the whole mechanism SYNTHETIC.

Floats appear only at the explicit boundary ``ExecutableMechanism.to_twocell`` (the twocell solver is float).
"""
from __future__ import annotations

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


class ConversionRefusal(Exception):
    def __init__(self, kind: ConversionRefusalKind, detail: str):
        super().__init__(f"{kind.value}: {detail}")
        self.kind = kind
        self.detail = detail


class Provenance(str, Enum):
    SOURCED = "SOURCED"
    SYNTHETIC = "SYNTHETIC"


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
    units implied by the overall order (checked on conversion).  ``source`` (SOURCED) or ``assumption``
    (SYNTHETIC) must be a non-empty statement."""
    k_f: Optional[float]
    k_r: Optional[float]
    reversible: bool
    provenance: Provenance
    k_f_units: str = ""
    k_r_units: str = ""
    kinetics: str = "elementary"
    forward_orders: Optional[tuple] = None
    reverse_orders: Optional[tuple] = None
    source: str = ""
    assumption: str = ""
    validity_T_K: Optional[tuple] = None      # (lo, hi) if the law is only valid in a window

    def __post_init__(self):
        if self.kinetics not in ("elementary", "empirical"):
            raise ConversionRefusal(ConversionRefusalKind.INVALID_KINETIC_LAW, f"unknown kinetics {self.kinetics!r}")
        if self.provenance == Provenance.SOURCED and not self.source.strip():
            raise ConversionRefusal(ConversionRefusalKind.PROVENANCE_MISSING,
                                    "a SOURCED law must cite its source")
        if self.provenance == Provenance.SYNTHETIC and not self.assumption.strip():
            raise ConversionRefusal(ConversionRefusalKind.PROVENANCE_MISSING,
                                    "a SYNTHETIC law must state its hypothetical assumption")
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

    ``recognized_family`` is advisory text (e.g. a reaction recognizer's verdict).  It confers NO authority."""
    species: tuple
    compositions: tuple
    charges: tuple
    reactant: np.ndarray            # (S, R) int64
    product: np.ndarray
    reaction_labels: tuple
    kinetics: tuple                 # per reaction: KineticLaw or None (= UNKNOWN)
    thermo: dict = field(default_factory=dict)   # facet name -> value or None (= UNKNOWN)
    recognized_family: Optional[str] = None
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
        """Merge verified single-reaction derivations (species unified by identity) into one descriptive mechanism."""
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
        return cls(tuple(names), tuple(comps), tuple(charges), reactant, product, labels,
                   tuple(kinetics) if kinetics is not None else (None,) * R, dict(thermo or {}), recognized_family)

    # -- conversion --------------------------------------------------------------------------------
    def to_executable(self, laws: Optional[Sequence] = None, *, omissions: Sequence = (),
                      selected: Optional[Sequence] = None) -> "ExecutableMechanism":
        """Promote to executable.  REQUIRES one admitted law per selected reaction (``laws`` overrides this
        mechanism's own facets), a non-empty list of omissions of competing chemistry, and valid units.

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
        return ExecutableMechanism(self.species, self.compositions, self.charges,
                                   self.reactant[:, sel], self.product[:, sel],
                                   tuple(self.reaction_labels[j] for j in sel), chosen, tuple(omissions))


# ------------------------------------------------------------------------------------------- executable
@dataclass(frozen=True, eq=False)
class ExecutableMechanism:
    """A selected, fully-lawed reaction set.  Construct via ``DescriptiveMechanism.to_executable``; the
    constructor re-validates everything itself so a hand-built instance gets no free pass either."""
    species: tuple
    compositions: tuple
    charges: tuple
    reactant: np.ndarray
    product: np.ndarray
    reaction_labels: tuple
    laws: tuple
    omissions: tuple
    E: np.ndarray = field(init=False)
    element_labels: tuple = field(init=False)
    N: np.ndarray = field(init=False)
    provenance: Provenance = field(init=False)

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
        prov = Provenance.SYNTHETIC if any(law.provenance == Provenance.SYNTHETIC for law in self.laws) else Provenance.SOURCED
        object.__setattr__(self, "provenance", prov)

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
    def scientific_claim(self) -> bool:
        """True only if EVERY law is SOURCED.  SYNTHETIC/hypothetical laws run but are never a scientific claim."""
        return self.provenance == Provenance.SOURCED

    def to_twocell(self) -> Mechanism:
        """The explicit float boundary: hand the exact-integer structure to the (float) twocell solver."""
        rates = tuple(ReactionRate(k_f=float(law.k_f), k_r=None if law.k_r is None else float(law.k_r),
                                   reversible=law.reversible) for law in self.laws)
        label = "SYNTHETIC" if self.provenance == Provenance.SYNTHETIC else "SOURCED"
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


__all__ = ["ConversionRefusal", "ConversionRefusalKind", "Provenance", "KineticLaw", "DescriptiveMechanism",
           "ExecutableMechanism", "expected_rate_constant_units", "AdapterRefusal", "RefusalKind"]
