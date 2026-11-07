"""OPERATION XIV Track B / XV Wave A -- the GENERAL chemical-system carrier.

A reusable kernel in which a chemical system is DECLARED (typed species, phases, reactions) and evolved by a GENERIC
integrator that holds NO hardcoded knowledge of acetate, CO2, sodium, or any particular chemistry.  Vinegar +
baking soda is ONE declared system among many; the ARCHITECTURAL GATE is that switching to a different system (a
synthetic network, a weak-acid buffer) requires NO edit to the numerical integrator -- only a different declaration.

This is NOT a claim that every chemistry is implemented or validated.  It is a carrier that can support them as their
laws, species data and validated models become available; today it carries a KINETIC reaction network (mass action,
reversible mass action, with a declared source/sink), and refuses -- fail-closed -- to integrate a reaction whose
rate law is unknown.  An algebraic fast-equilibrium projection, activity models, and multiphase transfer are declared
future extensions (they attach through the same typed interfaces), not faked here.

THE MATHEMATICAL HEART (plan section 3):

    dn/dt = N r(n, T) + q                 (species inventories evolve by reaction + external source/sink)
    conservation requirement:  E N = 0    (every reaction conserves every element AND charge)

with
    n : species inventories (mol), a vector over the declared species
    N : stoichiometric matrix (species x reactions), N[i, k] = signed coeff of species i in reaction k
    E : element-charge conservation matrix (components x species), one row per element + one CHARGE row
    r : reaction-rate vector (mol/s), each entry V * r_vol from that reaction's declared (concentration-basis) law
    q : external source/sink vector (mol/s), default 0

Because E N = 0, E dn/dt = E N r + E q = E q, so with q = 0 the conserved totals E n are INVARIANT -- the integrator
inherits conservation from the algebra, it is not re-imposed numerically.  With q != 0 the totals change by EXACTLY
the integral of E q, and that ledger is verified independently (XV-1D).

CONCENTRATION / VOLUME BASIS (XV-1C):  a ChemicalSystem owns a first-class positive reactor volume ``volume_L``.
A rate law is written in the textbook CONCENTRATION form and returns a VOLUMETRIC rate r_vol (mol L^-1 s^-1) from
concentrations c_i = n_i / V; the kernel converts to the MOLAR rate r_mol = V * r_vol before applying it to the
inventory ODE.  So for a bimolecular A + B -> C, dn_C/dt = V * k * c_A * c_B = k * n_A * n_B / V -- the conventional
concentration-rate convention, with k carrying order-dependent units (an n-th order k is L^(n-1) mol^-(1-n) s^-1).
The STANDARD STATE for the concentration basis is 1 mol/L with ideal-solution activities taken equal to
concentrations; kf/kr is therefore the CONCENTRATION equilibrium quotient Kc under that ideal standard state, NOT an
activity-based thermodynamic K-degree (the plan's warning: no dimensionless-K claim for arbitrary order/phase).

EXACT CONSERVATION (XV-1A):  E N = 0 is proven with UNBOUNDED PYTHON INTEGERS at construction, never a fixed-width
machine-word product.  A NumPy int64 matrix product can OVERFLOW (e.g. 2^62 A -> 2^62 B with A=4X, B=8X has a true
imbalance of 2^64 that wraps to 0), which would be a FALSE conservation certificate.  The NumPy matrices are kept as
derived EXECUTION artifacts for the float RHS; they are not the authority establishing conservation.

EXECUTABLE PROOF OBLIGATIONS (asserted, not asserted-in-prose):
  1. every reaction balances every declared element AND charge: E N = 0, checked EXACTLY (unbounded Python integer
     arithmetic) at ChemicalSystem construction -- an unbalanced reaction is REFUSED (ConservationError);
  2. the generic integrator conserves E n to machine zero when q = 0, and closes the external ledger
     E (n_final - n0) = integral(E q dt) when q != 0 (both VERIFIED on every trajectory);
  3. a reaction with no rate law is RATE_UNKNOWN -> integrate() REFUSES it (MissingKineticsError), never a silent
     k = 0 that would quietly make it inert;
  4. nonnegative inventory is maintained, or the raw (pre-clamp) excursion is REPORTED, never hidden;
  5. the kernel imports NO species-specific constant -- the same integrate() runs every declared system (the gate);
  6. the trajectory's evidential tier is DERIVED from measured checks (XV-1E), capped at STRUCTURALLY_CONSERVING;
     a caller cannot supply a stronger tier and thereby make an unverified model predictive.

DEMONSTRATIONS (plan section 4): see general_chemistry_demo.py and the tests -- a synthetic A<->B, B+C->D network
and a weak-acid dissociation run through this SAME kernel with no solver edit.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from scipy.integrate import solve_ivp

from experiments.sandbox_foundation import admissibility as _adm
from experiments.sandbox_foundation.claim_tiers import (
    ASSUMED_PARAMETER,
    REFUSED,
    STRUCTURALLY_CONSERVING,
    rank,
    weakest,
)


class KernelError(ValueError):
    """Base fail-closed error for the general kernel."""


class ConservationError(KernelError):
    """A declared reaction does not conserve an element or charge (E N != 0)."""


class MissingKineticsError(KernelError):
    """A reaction has no rate law (RATE_UNKNOWN) and cannot be integrated -- never silently treated as k = 0."""


class ExecutionBasisError(KernelError):
    """A declared coefficient cannot be represented EXACTLY in the float64 execution basis (|coeff| > 2**53).  The
    conservation law was proven in unbounded integers, but the solver runs the float cast -- an inexact coefficient
    would silently execute a stoichiometry the integer certificate never proved, so such a model is refused (XVIII-2)."""


class SourceDomainError(KernelError):
    """XXIV-2A: a sourced constant was asked to execute outside its sourced domain (e.g. a 25 C Ksp at 350 K).  Raised
    on BOTH execution paths; no unvalidated extrapolation is performed."""


class StaleCertificateError(KernelError):
    """The live execution basis (species / E / N / volume) no longer matches the certificate proven at construction --
    the certified model was mutated afterward and must not integrate under the stale certificate (XVIII-2)."""


class Phase(Enum):
    """The phase a species lives in.  Distinguishing phases is load-bearing: an aqueous Na+ is NOT sodium metal and
    NOT a gas-phase molecule, even at equal elemental composition + charge."""
    AQUEOUS = "aqueous"
    GAS = "gas"
    SOLID = "solid"
    PURE_LIQUID = "pure_liquid"


def _as_strict_positive_int(value, what: str) -> int:
    """Coerce to a strictly-positive Python int WITHOUT silent float truncation (XV-1B).

    A bool, a non-integer float (1.9), or a value <= 0 is REJECTED rather than quietly repaired -- an element count
    of 1.9 is malformed input, not "1"."""
    if isinstance(value, bool):
        raise KernelError(f"{what} must be a positive integer, not a bool")
    if isinstance(value, int):
        iv = value
    elif isinstance(value, float):
        if not value.is_integer():
            raise KernelError(f"{what} must be an integer (got {value!r}); counts are not silently truncated")
        iv = int(value)
    else:
        raise KernelError(f"{what} must be an integer (got {type(value).__name__})")
    if iv <= 0:
        raise KernelError(f"{what} must be strictly positive (got {iv})")
    return iv


@dataclass(frozen=True)
class Species:
    """A typed chemical species: its identity is (name, composition, charge, phase, substance) TOGETHER -- never
    formula alone.

    ``composition`` is stored as a sorted tuple of (element, count) pairs with UNIQUE elements (XV-1B), so the species
    is hashable and its elemental content is explicit, canonical and conserved.  ``data_status`` records whether the
    thermodynamic/transport data a future model would need is present; ``NONE`` is a first-class value, never silently
    treated as 0 (missing data stays missing).

    ``substance`` (XVI-P0.1) is a PHASE-INDEPENDENT chemical-substance identity: two species with the same
    ``substance`` are declared to be the same chemical compound, differing only in phase/solvation label (CO2(aq) and
    CO2(g) share substance "CO2"; an aqueous A in cell 0 and in cell 1 share substance "A").  It exists because
    elemental composition + charge is NECESSARY BUT NOT SUFFICIENT for chemical identity -- ethanol and dimethyl ether
    are both C2H6O, charge 0, yet are different substances, and a passive interface transfer between them would be a
    REACTION smuggled in as transport.  It is an EXPLICITLY-TYPED, auditable declaration, NOT a structure inferred from
    the free-text ``name``; the kernel carries no bond graph, so the burden that a shared ``substance`` is chemically
    faithful rests on the declaration, and is guarded consistent with composition+charge wherever it licenses a
    transfer (InterfaceTransfer refuses a substance key that would span a different composition/charge).  It DEFAULTS
    to the species ``name`` -- fail-closed: two differently-named same-formula species are NOT silently identified, so
    a cross-species transfer must be explicitly licensed by declaring a shared substance."""
    name: str
    composition: tuple           # ((element, count), ...) sorted by element, elements unique
    charge: int
    phase: Phase
    # XVIII-1C: data_status is EVIDENCE provenance, NOT chemical identity -- compare=False keeps it out of the frozen
    # dataclass's __eq__/__hash__, so the same substance with an updated evidence tier stays the SAME species rather
    # than silently forging a second one.  It is carried in a SEPARATE source/evidence digest (general_chemistry_demo).
    data_status: str = field(default="NONE", compare=False)   # NONE | PARTIAL | SOURCED (no thermo data faked)
    substance: str | None = None  # XVI-P0.1 phase-independent substance identity; defaults to ``name`` (fail-closed)

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise KernelError("a Species needs a non-empty name")
        if self.substance is None:
            object.__setattr__(self, "substance", self.name)     # fail-closed default: each species is its own substance
        elif not isinstance(self.substance, str) or not self.substance.strip():
            raise KernelError("substance must be a non-empty string (a phase-independent substance identity) or None")
        if type(self.composition) is not tuple or not all(
                type(p) is tuple and len(p) == 2 and isinstance(p[0], str) and p[0].strip()
                and type(p[1]) is int and not isinstance(p[1], bool) and p[1] > 0
                for p in self.composition):
            raise KernelError("composition must be a tuple of (element:str, count:int>0) pairs")
        elems = [e for e, _ in self.composition]
        if elems != sorted(elems):
            raise KernelError("composition elements must be sorted (use Species.of)")
        if len(set(elems)) != len(elems):                     # XV-1B: no duplicate element hiding a larger count
            raise KernelError(f"composition has a duplicate element {sorted({e for e in elems if elems.count(e) > 1})};"
                              f" element counts must be canonical and unique")
        if type(self.charge) is not int or isinstance(self.charge, bool):
            raise KernelError("charge must be an int")
        if type(self.phase) is not Phase:
            raise KernelError("phase must be a Phase")
        if self.data_status not in ("NONE", "PARTIAL", "SOURCED"):
            raise KernelError("data_status must be NONE / PARTIAL / SOURCED")

    @classmethod
    def of(cls, name: str, composition: dict, charge: int = 0, phase: Phase = Phase.AQUEOUS,
           data_status: str = "NONE", substance: str | None = None) -> "Species":
        """Build a Species from a {element: count} dict (sorted into the canonical tuple).  Counts must be strictly
        positive integers -- a float count is rejected, never truncated (XV-1B).  ``substance`` is the phase-
        independent substance identity (XVI-P0.1); omit it to default to ``name`` (fail-closed)."""
        if type(composition) is not dict or not composition:
            raise KernelError("composition must be a non-empty {element: count} dict")
        comp = tuple(sorted((str(e), _as_strict_positive_int(c, f"count for element {e!r}"))
                            for e, c in composition.items()))
        if isinstance(charge, bool) or type(charge) is not int:
            raise KernelError("charge must be an int")
        return cls(name, comp, int(charge), phase, data_status, substance)

    @property
    def elements(self) -> frozenset:
        return frozenset(e for e, _ in self.composition)

    def count(self, element: str) -> int:
        """The (unique, canonical) count of ``element`` in this species; 0 if absent."""
        for e, c in self.composition:
            if e == element:
                return c
        return 0


# ---------------------------------------------------------------------------------------------- rate laws
class RateLaw:
    """A reaction's kinetic law in the CONCENTRATION basis.  ``evaluate(reaction, concentrations)`` returns the NET
    forward VOLUMETRIC rate r_vol (mol L^-1 s^-1) from a {Species: concentration mol/L} map; the kernel multiplies by
    the reactor volume V to obtain the molar rate (XV-1C).  A rate law carries a tier/provenance so a trajectory can
    never claim a confidence its kinetics lack."""
    tier: str = ASSUMED_PARAMETER

    def evaluate(self, reaction: "Reaction", concentrations: dict) -> float:
        raise NotImplementedError

    def descriptor(self) -> tuple:
        """XX-2B: a canonical, lossless, order-stable descriptor of EVERY parameter that changes what
        ``evaluate`` returns -- the unit a model/world certificate hashes so a post-construction mutation of
        the law is DETECTED rather than executed under a stale certificate.  A subclass that drives the RHS
        MUST override this and bind all its operative parameters (rate constants, equilibrium quotients, the
        species it reads).  The base REFUSES (NotImplementedError): an un-descriptor'd law is certified as
        UNVERIFIABLE -- the certificate makes no validity claim about it -- rather than hashed by a forgeable,
        collision-prone ``repr()`` of a mutable object."""
        raise NotImplementedError

    @staticmethod
    def _reactant_order(reaction: "Reaction") -> int:
        return sum(-coeff for _, coeff in reaction.stoich if coeff < 0)


# ---------------------------------------------------------------------- XXII-2 / XXIII-2: rate-law identity authority
# A ``descriptor()`` is PROOF of a law's executable identity only when someone has AUDITED that it faithfully binds every
# operative parameter ``evaluate`` reads AND that the law holds no hidden mutable dependency the descriptor omits.  An
# arbitrary user law can return a FROZEN descriptor while ``evaluate`` reads a MUTABLE hidden parameter (a LYING
# descriptor), so the mere presence of a ``descriptor()`` method cannot certify a class.
#
# XXIII-2 (RED -> GREEN): XXII-2 anchored certification in a registry, but the registry was an open, public ``set.add``
# -- ``register_certified_rate_law(Lying)`` from ANY caller made a lying law run under require_certified_execution with
# ``execution_identity_certified=True``, and a 10x hidden-parameter mutation then ran different physics under an
# unchanged world certificate.  The "audit" was a docstring.  The authority is now split into three explicit tiers:
#
#   AUDITED_BUILTIN            a CLOSED, in-tree table (``_AUDITED_BUILTIN_PINS``) of (module, qualname) -> sha256 of the
#                              reviewed class source.  Only a class whose canonical module attribute IS that class, whose
#                              current source matches the pin, and whose evaluate/descriptor code was compiled from that
#                              file can be sealed.  Editing an audited class without re-auditing (updating its pin)
#                              DEMOTES it, fail-closed.  No public call adds to this table.
#   CALLER_ATTESTED_EXTENSION  ``register_attested_rate_law(cls, attested_by=...)``: a plugin's author ATTESTS its
#                              descriptor is faithful.  Its descriptor is bound into the certificate (so a mutation of a
#                              bound parameter is still caught), but an attestation is a caller CLAIM, not an audit: it
#                              never sets ``execution_identity_certified``, strict mode refuses it unless the caller
#                              explicitly opts in (``accept_attested_extensions=True``), and it floors the kinetic tier.
#   UNVERIFIABLE               everything else (XXI-2): runs EXPLICITLY UNVERIFIED, refused under strict mode.
#
# HONEST BOUNDARY: this is an in-process, trusted-code authority, NOT cryptographic or independent validation.  Code that
# can rebind module globals, rewrite a module attribute, or forge a code object's filename is inside the trust boundary
# and can defeat it.  What it does guarantee: the PUBLIC API can no longer elevate a caller's class to the audited tier,
# a subclass / instance-level override / post-seal method swap of an audited class is demoted, and every receipt says
# WHICH authority (audited vs caller-attested) backs its execution identity.
AUDITED_BUILTIN = "AUDITED_BUILTIN"
CALLER_ATTESTED_EXTENSION = "CALLER_ATTESTED_EXTENSION"
UNVERIFIABLE_AUTHORITY = "UNVERIFIABLE"
_RATE_LAW_METHODS = ("evaluate", "descriptor")

#: The CLOSED audit table.  XXIV-1D: each pin is the sha256 of the class's in-tree DEPENDENCY CLOSURE
#: (``_audit_closure``: the class source, its in-tree bases, and every module-level helper function / constant it
#: references, transitively) -- not the class text alone, so an edit to a helper an audited law executes demotes it.
#: Changing an audited class OR any hashed dependency REQUIRES re-auditing and updating its pin here -- that edit is
#: the audit event, visible in review.  ``test_xxiii_s2_registry_authority`` fails loudly if a pin goes stale.
#: XXIV-1D re-audit event (2026-11-07): all five pins moved from class-source digests to closure digests; no class
#: body changed.
_AUDITED_BUILTIN_PINS: dict = {
    ("experiments.sandbox_foundation.general_kernel", "MassActionIrreversible"): "8599738277140ffe1bfa5e5125a4bae60892141fb6ae7db27f1cd94022cee547",
    ("experiments.sandbox_foundation.general_kernel", "MassActionReversible"): "190bac98c64fada169b38ae6acba5adf6ef7846f2529caf28c8ad8009d95aca7",
    ("experiments.sandbox_foundation.unified_chemical_world", "BicarbonateDissolutionRate"): "c3e6f662027fce6fd6555523920431e966397b0ffd6c071c2a8ab607e1cf02d5",
    # XXIII-S4 audit event: the two activity-based solid/speciation laws (Davies activities, I-domain guard, descriptor
    # binds k/K/stoich/species/A/I_max/precipitation switch).  Audited 2026-11 in solid_equilibrium.py; re-pin on edit.
    ("experiments.sandbox_foundation.solid_equilibrium", "ActivitySolubilityRate"): "abcd7eea12495725d1bcbbdb197b730111c3e61bb1df869006ecc5a61ed6d0ab",
    ("experiments.sandbox_foundation.solid_equilibrium", "ActivityReversibleRate"): "c0524db28918b99d58bedff1dfec6fc19d0589b63bcedfc5cf5fd41efaaeb737",
}


@dataclass(frozen=True)
class _SealRecord:
    """What a sealed rate-law type was at seal time: its authority, the exact method objects (a later swap demotes it),
    the source digest, and -- for an attestation -- who attested."""
    authority: str
    methods: tuple          # ((name, function object), ...) captured at seal time
    source_sha256: str
    attested_by: str = ""


_AUDITED_BUILTINS: dict = {}       # type -> _SealRecord   (only _seal_audited_builtin writes here)
_ATTESTED_EXTENSIONS: dict = {}    # type -> _SealRecord   (register_attested_rate_law writes here)
_AUDIT_FAILURES: dict = {}         # (module, qualname) -> reason a pinned built-in could NOT be sealed (fail-closed)


def _class_source(cls) -> tuple:
    """(source_text, path, first_line, last_line) of a TOP-LEVEL class, located by parsing its defining module's file
    with ``ast`` (decorators included, ``\r\n`` normalised).  Deterministic across Python versions (no reliance on
    ``inspect.getsource`` heuristics).  Raises KernelError if the source cannot be located -- callers fail closed."""
    import ast
    import sys
    mod = sys.modules.get(cls.__module__)
    path = getattr(mod, "__file__", None)
    if not path or "." in cls.__qualname__:
        raise KernelError(f"cannot locate top-level source for {cls.__module__}.{cls.__qualname__}")
    with open(path, encoding="utf-8") as fh:
        text = fh.read().replace("\r\n", "\n")
    lines = text.split("\n")
    for node in ast.parse(text).body:
        if isinstance(node, ast.ClassDef) and node.name == cls.__qualname__:
            first = min([node.lineno] + [d.lineno for d in node.decorator_list])
            return "\n".join(lines[first - 1:node.end_lineno]), path, first, node.end_lineno
    raise KernelError(f"no top-level class {cls.__qualname__!r} in {path}")


# XXIV-1D AUDIT DEPENDENCY CLOSURE (RED -> GREEN, probe P4).  A pin over the class source alone left every module-level
# helper the class executes OUTSIDE the audit: editing ``solid_equilibrium._constant_key`` so it stopped binding a Ksp
# VALUE left ActivitySolubilityRate SEALED, and two worlds with Ksp 1e-6 / 4e-6 then shared ONE certificate while their
# trajectories differed by 2x (a false execution-identity claim produced by an unaudited maintenance edit).  The pin is
# now the sha256 of the class's IN-TREE DEPENDENCY CLOSURE: the class source, the source of every in-tree base class,
# and -- transitively -- the source of every module-level FUNCTION and CONSTANT assignment the class body references,
# followed through ``from experiments.sandbox_foundation.X import name`` and ``X.name`` module-alias attribute access.
# Excluded, and declared rather than hidden (see ``audit_closure_inventory``):
#   * type dependencies (in-tree CLASSES the body names, e.g. Species, SourcedConstant): a trusted-code maintenance
#     assumption; species identity itself is bound per system by the XVIII-2 model certificate;
#   * external dependencies (stdlib / numpy / scipy): the trusted environment;
#   * runtime rebinding (monkeypatching a module global in-process): inside the trust boundary, as before.
_IN_TREE_PREFIX = "experiments.sandbox_foundation"
_MODULE_INDEX_CACHE: dict = {}


def _module_index(modname: str):
    """(text, path, defs, imports) of an in-tree module, parsed from its SOURCE FILE without executing it (so a closure
    can be computed at import time without import cycles).  defs: top-level name -> (kind, node); imports: local name
    -> (module, attr-or-None)."""
    import ast
    import importlib.util
    if modname in _MODULE_INDEX_CACHE:
        return _MODULE_INDEX_CACHE[modname]
    spec = importlib.util.find_spec(modname)
    if spec is None or not spec.origin or not spec.origin.endswith(".py"):
        raise KernelError(f"cannot locate the source of in-tree module {modname!r}")
    with open(spec.origin, encoding="utf-8") as fh:
        text = fh.read().replace("\r\n", "\n")
    defs, imports = {}, {}
    for node in ast.parse(text).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs[node.name] = ("function", node)
        elif isinstance(node, ast.ClassDef):
            defs[node.name] = ("class", node)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    defs[t.id] = ("constant", node)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defs[node.target.id] = ("constant", node)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for a in node.names:
                imports[a.asname or a.name] = (node.module, a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                imports[a.asname or a.name.split(".")[0]] = (a.name if a.asname else a.name.split(".")[0], None)
    out = (text, spec.origin, defs, imports)
    _MODULE_INDEX_CACHE[modname] = out
    return out


def _is_in_tree_module(name: str) -> bool:
    import importlib.util
    if not (name == _IN_TREE_PREFIX or name.startswith(_IN_TREE_PREFIX + ".")):
        return False
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):
        return False
    return spec is not None and bool(spec.origin) and spec.origin.endswith(".py") and not spec.origin.endswith("__init__.py")


def _node_refs(node):
    """Names and (alias, attr) pairs a node's body references (over-inclusive by design: a local that shadows a module
    name only ADDS to the hashed closure, it can never remove a dependency)."""
    import ast
    names, attrs = set(), set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            names.add(sub.id)
        elif isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
            attrs.add((sub.value.id, sub.attr))
    return names, attrs


def _segment(text: str, node) -> str:
    lines = text.split("\n")
    first = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    return "\n".join(lines[first - 1:node.end_lineno])


def _audit_closure(cls) -> tuple:
    """(digest, inventory) of ``cls``'s in-tree dependency closure (XXIV-1D).  inventory = {"hashed": [(module, name,
    kind)], "type_dependencies": [...], "external": [...]}.  Raises KernelError if any in-tree source cannot be read."""
    hashed, types, external = {}, set(), set()

    def resolve_module_attr(modname, attr):
        if _is_in_tree_module(modname):
            resolve(modname, attr)
        else:
            external.add(f"{modname}.{attr}")

    def walk(modname, node):
        _, _, defs, imports = _module_index(modname)
        names, attrs = _node_refs(node)
        for nm in sorted(names):
            resolve(modname, nm)
        for alias, attr in sorted(attrs):
            if alias in defs or alias not in imports:
                continue
            m, a = imports[alias]
            target = m if a is None else f"{m}.{a}"
            if a is None or _is_in_tree_module(target):
                resolve_module_attr(target, attr)

    def resolve(modname, name):
        text, _, defs, imports = _module_index(modname)
        if name in defs:
            kind, node = defs[name]
            key = (modname, name)
            if kind == "class":
                types.add(key)
                return
            if key in hashed:
                return
            hashed[key] = (kind, _segment(text, node))
            walk(modname, node)
        elif name in imports:
            m, a = imports[name]
            if a is None:
                return                                      # a bare module alias; its attributes resolve in walk()
            if _is_in_tree_module(f"{m}.{a}"):
                return                                      # ``from pkg import module`` -- a module alias
            if m == _IN_TREE_PREFIX or m.startswith(_IN_TREE_PREFIX + "."):
                resolve(m, a)
            else:
                external.add(f"{m}.{a}")

    roots = [cls] + [b for b in cls.__mro__[1:] if isinstance(b.__module__, str)
                     and b.__module__.startswith(_IN_TREE_PREFIX) and "." not in b.__qualname__]
    for k in roots:
        text, _, defs, _ = _module_index(k.__module__)
        if k.__qualname__ not in defs or defs[k.__qualname__][0] != "class":
            raise KernelError(f"no top-level class {k.__qualname__!r} in {k.__module__}")
        node = defs[k.__qualname__][1]
        hashed[(k.__module__, k.__qualname__)] = ("class" if k is cls else "base_class", _segment(text, node))
        walk(k.__module__, node)
    for k in roots:
        types.discard((k.__module__, k.__qualname__))
    blob = json.dumps(sorted([m, n, kind, src] for (m, n), (kind, src) in hashed.items()))
    inventory = {"hashed": sorted((m, n, kind) for (m, n), (kind, _) in hashed.items()),
                 "type_dependencies": sorted(types), "external": sorted(external)}
    return hashlib.sha256(blob.encode("utf-8")).hexdigest(), inventory


def audit_closure_inventory(cls) -> dict:
    """XXIV-1D: what an audit pin over ``cls`` covers (hashed), and what it DECLARES as a trusted assumption (type
    dependencies, external packages).  Reported, never hidden."""
    return _audit_closure(cls)[1]


def _check_rate_law_class(cls) -> None:
    if not (isinstance(cls, type) and issubclass(cls, RateLaw)):
        raise KernelError("expected a RateLaw subclass")
    if cls.evaluate is RateLaw.evaluate:
        raise KernelError(f"{cls.__qualname__} does not override evaluate(); a law with no kinetics cannot be certified")
    if cls.descriptor is RateLaw.descriptor:
        raise KernelError(f"{cls.__qualname__} does not override descriptor(); an un-descriptor'd law cannot be "
                          f"certified (its operative parameters are unbindable -- it runs EXPLICITLY UNVERIFIED)")


def _method_snapshot(cls, methods: tuple = _RATE_LAW_METHODS) -> tuple:
    return tuple((name, cls.__dict__.get(name)) for name in methods)


def _seal_class(cls, *, pins: dict, sealed: dict, failures: dict, methods: tuple, check) -> object:
    """Seal an in-tree class against a CLOSED pin table (shared by rate laws and, XXIV-1A, equilibrium operators).
    The pin is the class's audit DEPENDENCY CLOSURE digest (XXIV-1D).  Fail-closed: any mismatch records the reason in
    ``failures`` and leaves the class UNVERIFIABLE (it still runs, explicitly unverified) -- it never raises at import
    and never certifies a class the table does not pin.  Returns ``cls`` unchanged (decorator-safe)."""
    import sys
    key = (cls.__module__, cls.__qualname__)
    try:
        check(cls)
        pin = pins.get(key)
        if pin is None:
            raise KernelError(f"{key} is not in the closed audit table")
        mod = sys.modules.get(cls.__module__)
        if mod is None or getattr(mod, cls.__qualname__, None) is not cls:
            raise KernelError(f"{key}: the canonical module attribute is a different object")
        _src, path, first, last = _class_source(cls)
        digest = _audit_closure(cls)[0]
        if digest != pin:
            raise KernelError(f"{key}: audit-closure sha256 {digest} != audited pin {pin} (the class OR an in-tree "
                              f"helper/constant it references changed: re-audit and update the pin)")
        for name, fn in _method_snapshot(cls, methods):
            if fn is None:
                continue                                    # not defined on the class itself (an inherited base method)
            code = getattr(fn, "__code__", None)
            if code is None or code.co_filename != path or not (first <= code.co_firstlineno <= last):
                raise KernelError(f"{key}: {name} was not compiled from the audited source")
    except (KernelError, OSError, SyntaxError) as exc:
        failures[key] = str(exc)
        sealed.pop(cls, None)
        return cls
    failures.pop(key, None)
    sealed[cls] = _SealRecord(AUDITED_BUILTIN, _method_snapshot(cls, methods), digest)
    return cls


def _seal_audited_builtin(cls):
    """Seal an in-tree RateLaw against the closed rate-law audit table (see ``_seal_class``)."""
    return _seal_class(cls, pins=_AUDITED_BUILTIN_PINS, sealed=_AUDITED_BUILTINS, failures=_AUDIT_FAILURES,
                       methods=_RATE_LAW_METHODS, check=_check_rate_law_class)


def register_attested_rate_law(cls, *, attested_by: str):
    """Register a plugin RateLaw as a CALLER-ATTESTED extension: ``attested_by`` (a non-empty name of the person/project
    vouching for it) attests that ``descriptor()`` faithfully binds every operative parameter.  This is a CLAIM, not an
    audit -- the class gets a bound descriptor (mutations of bound parameters are detected) but NEVER the audited tier:
    the receipt reports ``execution_identity_basis='CALLER_ATTESTED'``, ``execution_identity_certified`` stays False,
    strict mode refuses it unless ``accept_attested_extensions=True``, and its kinetic tier is floored.  A class in the
    closed audit table cannot be re-registered as an attestation (it is audited or demoted, never downgraded-by-claim).
    Usable as ``register_attested_rate_law(MyLaw, attested_by="my-lab")``; returns the class unchanged."""
    _check_rate_law_class(cls)
    if not (isinstance(attested_by, str) and attested_by.strip()):
        raise KernelError("register_attested_rate_law requires a non-empty attested_by (who vouches for the descriptor)")
    if (cls.__module__, cls.__qualname__) in _AUDITED_BUILTIN_PINS or cls in _AUDITED_BUILTINS:
        raise KernelError(f"{cls.__qualname__} is governed by the closed audit table; it cannot be caller-attested")
    try:
        digest = _audit_closure(cls)[0]
    except (KernelError, OSError, SyntaxError):
        digest = "UNAVAILABLE"
    _ATTESTED_EXTENSIONS[cls] = _SealRecord(CALLER_ATTESTED_EXTENSION, _method_snapshot(cls), digest,
                                            attested_by.strip())
    return cls


def register_certified_rate_law(cls):
    """REMOVED in XXIII-2 (it let ANY caller self-certify a lying law).  Always raises KernelError naming the two
    truthful routes: add an audit pin to the closed table (in-tree code review), or ``register_attested_rate_law``."""
    raise KernelError(
        "register_certified_rate_law was removed (XXIII-2): self-registration cannot certify execution identity. "
        "Use register_attested_rate_law(cls, attested_by=...) for a plugin (a labeled caller claim, never audited), or "
        "add the class to the closed _AUDITED_BUILTIN_PINS table through code review.")


def rate_law_authority(rl) -> str:
    """The authority backing ``rl``'s execution identity: AUDITED_BUILTIN, CALLER_ATTESTED_EXTENSION or UNVERIFIABLE.
    Exact type only (a subclass inherits nothing); the sealed evaluate/descriptor objects must still be the class's
    own (a post-seal method swap demotes); an instance-level evaluate/descriptor override demotes."""
    if rl is None:
        return UNVERIFIABLE_AUTHORITY
    t = type(rl)
    inst = getattr(rl, "__dict__", {})
    if any(name in inst for name in _RATE_LAW_METHODS):
        return UNVERIFIABLE_AUTHORITY
    for table in (_AUDITED_BUILTINS, _ATTESTED_EXTENSIONS):
        rec = table.get(t)
        if rec is not None:
            return rec.authority if _method_snapshot(t) == rec.methods else UNVERIFIABLE_AUTHORITY
    return UNVERIFIABLE_AUTHORITY


def is_certified_rate_law_type(cls) -> bool:
    """True iff ``cls`` is a SEALED audited built-in whose methods are intact (XXIII-2).  A caller attestation is NOT
    certification and returns False."""
    rec = _AUDITED_BUILTINS.get(cls) if isinstance(cls, type) else None
    return rec is not None and _method_snapshot(cls) == rec.methods


def rate_law_attestation(cls) -> str:
    """Who attested a CALLER_ATTESTED_EXTENSION type ('' if none) -- surfaced on receipts so a claim names its source."""
    rec = _ATTESTED_EXTENSIONS.get(cls)
    return rec.attested_by if rec is not None else ""


def audit_status() -> dict:
    """{(module, qualname): 'SEALED' | 'NOT_LOADED' | <failure reason>} for every pinned built-in (a stale pin shows up
    here and in the receipt's demotion, never as a silent certification)."""
    out = {}
    sealed = {(t.__module__, t.__qualname__) for t in _AUDITED_BUILTINS}
    for key in _AUDITED_BUILTIN_PINS:
        out[key] = "SEALED" if key in sealed else _AUDIT_FAILURES.get(key, "NOT_LOADED")
    return out


@dataclass(frozen=True)
class MassActionIrreversible(RateLaw):
    """r_vol = k * prod(c[reactant]^|coeff|)  (mol L^-1 s^-1).  Forward only (no reverse term).

    ``k`` has order-dependent units: for overall reactant order n, k is L^(n-1) mol^(1-n) s^-1 (so r_vol is always
    mol L^-1 s^-1).  ``elementary`` is the caller's declaration that mass action is defensible for this step."""
    k: float
    tier: str = ASSUMED_PARAMETER
    source: str = "synthetic (declared)"

    def __post_init__(self):
        if isinstance(self.k, bool) or not (isinstance(self.k, (int, float)) and math.isfinite(self.k) and self.k >= 0):
            raise KernelError("mass-action k must be finite and >= 0")

    def evaluate(self, reaction, concentrations):
        r = float(self.k)
        for sp, coeff in reaction.stoich:
            if coeff < 0:
                r *= concentrations[sp] ** (-coeff)
        return r

    def descriptor(self):
        # XX-2B: bind the rate constant and provenance (repr(float) round-trips the exact IEEE-754 bits).
        return ("MassActionIrreversible", repr(float(self.k)), self.tier, self.source)


@dataclass(frozen=True)
class MassActionReversible(RateLaw):
    """r_vol = kf * prod(c[reactant]^|coeff|) - kr * prod(c[product]^coeff)  (mol L^-1 s^-1).

    The ratio kf/kr is the CONCENTRATION equilibrium quotient Kc -- detailed balance: at the fixed point r_vol = 0 and
    prod(c_product)/prod(c_reactant) = kf/kr.  Kc is defined on the ideal concentration standard state (1 mol/L,
    activities == concentrations); it is NOT the activity-based thermodynamic K-degree, and no such claim is made."""
    kf: float
    kr: float
    tier: str = ASSUMED_PARAMETER
    source: str = "synthetic (declared); kf/kr encodes the concentration equilibrium quotient Kc"

    def __post_init__(self):
        for nm, v in (("kf", self.kf), ("kr", self.kr)):
            if isinstance(v, bool) or not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
                raise KernelError(f"mass-action {nm} must be finite and >= 0")

    def evaluate(self, reaction, concentrations):
        fwd = float(self.kf)
        rev = float(self.kr)
        for sp, coeff in reaction.stoich:
            if coeff < 0:
                fwd *= concentrations[sp] ** (-coeff)
            elif coeff > 0:
                rev *= concentrations[sp] ** coeff
        return fwd - rev

    def descriptor(self):
        # XX-2B: bind BOTH rate constants (kf, kr encode Kc) and provenance.
        return ("MassActionReversible", repr(float(self.kf)), repr(float(self.kr)), self.tier, self.source)


# XXIII-2: seal the in-module audited built-ins against their closed pins (fail-closed on mismatch).
_seal_audited_builtin(MassActionIrreversible)
_seal_audited_builtin(MassActionReversible)


#: Sentinel: a reaction whose kinetics are unknown.  It is NOT a rate of 0 -- a system containing it refuses to
#: integrate (fail-closed) rather than silently treating the reaction as inert.
RATE_UNKNOWN = None


@dataclass(frozen=True)
class Reaction:
    """A declared transformation with signed stoichiometry and (optionally) a rate law.

    ``stoich`` is a tuple of (Species, int coeff): coeff < 0 reactant, coeff > 0 product.  ``rate_law`` is a RateLaw
    or ``RATE_UNKNOWN``.  Conservation is NOT checked here (it needs the whole species set's element basis) -- it is
    checked at ChemicalSystem construction, where an unbalanced reaction is refused."""
    name: str
    stoich: tuple                # ((Species, coeff:int!=0), ...)
    rate_law: object = RATE_UNKNOWN
    elementary: bool = True      # True = an elementary step (mass action is defensible); False = an effective/lumped law

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise KernelError("a Reaction needs a non-empty name")
        if type(self.stoich) is not tuple or len(self.stoich) < 1 or not all(
                type(p) is tuple and len(p) == 2 and type(p[0]) is Species
                and type(p[1]) is int and not isinstance(p[1], bool) and p[1] != 0
                for p in self.stoich):
            raise KernelError("stoich must be a tuple of (Species, nonzero-int coeff) pairs")
        seen = [sp for sp, _ in self.stoich]
        if len(set(seen)) != len(seen):
            raise KernelError("a species appears twice in one reaction's stoichiometry (combine the coefficients)")
        if self.rate_law is not RATE_UNKNOWN and not isinstance(self.rate_law, RateLaw):
            raise KernelError("rate_law must be a RateLaw or RATE_UNKNOWN")

    @property
    def reactants(self):
        return tuple((sp, -c) for sp, c in self.stoich if c < 0)

    @property
    def products(self):
        return tuple((sp, c) for sp, c in self.stoich if c > 0)


@dataclass(frozen=True)
class VerificationReceipt:
    """A DERIVED, non-self-certifying evidence receipt for a trajectory (XV-1E).

    Every verification field is a MEASURED fact about the integration; none is caller-supplied.  ``declared_kinetic_
    tier`` is the ONLY caller input -- the honest provenance of the rate laws -- and it can only ever LOWER the
    admitted tier (weakest-premise), never inflate it: ``structural_tier`` caps the kernel at STRUCTURALLY_CONSERVING
    (the bare kernel does no independent-algorithm, reference-solver, or measured-data check), so no declared tier can
    make an unverified model BENCHMARKED/CALIBRATED/PREDICTIVE.  If a check fails the structural tier collapses to
    REFUSED and caps everything there."""
    solver_completed: bool
    positivity_held: bool
    external_ledger_closed: bool          # E (n(t) - n0) == integral(E q dt) within tolerance (reduces to drift when closed)
    conservation_residual: float          # max |E n(t) - E n0| over the run (RAW change; ~0 for a closed system)
    external_ledger_residual: float       # max |E n(t) - E n0 - (E q) t| (LEDGER-closed residual; ~0 closed AND open)
    min_inventory: float
    tolerance: float
    structural_tier: str                  # DERIVED: STRUCTURALLY_CONSERVING if every check passed, else REFUSED
    declared_kinetic_tier: str            # caller INPUT: provenance of the rate laws (default ASSUMED_PARAMETER)
    admitted_tier: str                    # DERIVED AUTHORITY = weakest(structural_tier, declared_kinetic_tier)
    notes: tuple = ()
    positivity_verdict: str = "HELD"      # XXIV-1B: HELD | HELD_WITHIN_PHYSICAL_FLOOR | UNRESOLVED_AT_REQUESTED_TOLERANCE | VIOLATED (caller-independent floor)
    negative_minima: dict = field(default_factory=dict)   # XXIV-1B: {species name: raw most-negative amount (mol)} -- preserved, never clipped
    charge_validity: object = None        # XXIV-1C: admissibility.ChargeValidity (three separate charge claims)
    source_domain: str = "NO_SOURCED_CONSTANTS"   # XXIV-2A: SUPPORTED... | NO_SOURCED_CONSTANTS (an off-domain run is REFUSED)


@dataclass(frozen=True)
class NetworkTrajectory:
    """A generic reaction-network trajectory + its executable conservation/positivity verdicts."""
    times: tuple
    species: tuple               # the Species, in column order of `amounts`
    amounts: tuple               # tuple of per-time dicts {Species: mol}
    component_labels: tuple      # element names + "charge"
    volume_L: float              # the reactor volume the concentration basis used
    max_component_drift: float   # max |E n(t) - E n0| over the run (RAW; machine-zero when q = 0)
    external_ledger_residual: float  # max |E n(t) - E n0 - (E q) t| over the run (LEDGER-closed residual)
    min_amount: float            # the most-negative inventory seen (>= 0 means positivity held)
    solver_success: bool
    integrator: str
    receipt: VerificationReceipt
    tier: str                    # == receipt.admitted_tier (the DERIVED authority), surfaced for display
    note: str = ""
    caveats: tuple = field(default_factory=tuple)


def _species_identity_key(sp: Species) -> tuple:
    """The FULL species identity the model certificate binds (name, composition, charge, phase, substance) -- one
    definition, used for both the species columns and every reaction's stoichiometry, so the two cannot drift apart."""
    return (sp.name, sp.composition, sp.charge, sp.phase.value, sp.substance)


def _kernel_rate_law_descriptor(rl) -> tuple:
    """XXIII-2b (F1): the kernel-side canonical descriptor of a reaction's rate law, mirroring general_coupled's
    ``_rate_law_descriptor`` authority tiers (the coupled module imports the kernel, so the kernel cannot import it back).
    An AUDITED or CALLER-ATTESTED law binds its authority, class and full ``descriptor()``; anything else binds only
    ``UNVERIFIABLE`` + its class -- the certificate makes no claim about parameters it cannot see, and a post-construction
    demotion (a method swap) still MOVES the descriptor, because the authority token itself changes."""
    if rl is RATE_UNKNOWN:
        return ("RATE_UNKNOWN",)
    authority = rate_law_authority(rl)
    if authority in (AUDITED_BUILTIN, CALLER_ATTESTED_EXTENSION):
        try:
            desc = tuple(rl.descriptor())
        except NotImplementedError:
            return (UNVERIFIABLE_AUTHORITY, type(rl).__qualname__)
        return (authority, type(rl).__qualname__, rate_law_attestation(type(rl))) + desc
    return (UNVERIFIABLE_AUTHORITY, type(rl).__qualname__)


class ChemicalSystem:
    """The general carrier: an ordered species list + declared reactions + a reactor volume, with the stoichiometric
    matrix N and the element-charge conservation matrix E built and the conservation law E N = 0 PROVEN (EXACTLY, in
    unbounded Python integers) at construction."""

    def __init__(self, species: list, reactions: list, volume_L: float = 1.0):
        if not species or any(type(s) is not Species for s in species):
            raise KernelError("species must be a non-empty list of Species")
        if len(set(species)) != len(species):
            raise KernelError("duplicate species in the system")
        if any(type(r) is not Reaction for r in reactions):
            raise KernelError("reactions must be Reaction objects")
        if isinstance(volume_L, bool) or not (isinstance(volume_L, (int, float))
                                              and math.isfinite(volume_L) and volume_L > 0):
            raise KernelError("volume_L must be a finite reactor volume > 0 (litres)")
        for r in reactions:
            for sp, _ in r.stoich:
                if sp not in species:
                    raise KernelError(f"reaction {r.name!r} references species {sp.name!r} not in the system")
        self.species = tuple(species)
        self.reactions = tuple(reactions)
        self.volume_L = float(volume_L)
        self._index = {sp: i for i, sp in enumerate(self.species)}
        self.elements = sorted({e for sp in self.species for e in sp.elements})
        self.component_labels = tuple(self.elements) + ("charge",)
        # the EXACT (unbounded-integer) authorities for the conservation proof, frozen as tuples of tuples so the
        # integer certificate itself cannot be rewritten in place after it is proven:
        E_int = [[sp.count(el) for sp in self.species] for el in self.elements]
        E_int.append([sp.charge for sp in self.species])                # the charge-conservation row
        N_int = [[0] * len(self.reactions) for _ in self.species]
        for k, r in enumerate(self.reactions):
            for sp, coeff in r.stoich:
                N_int[self._index[sp]][k] = coeff
        self._E_int = tuple(tuple(row) for row in E_int)
        self._N_int = tuple(tuple(row) for row in N_int)
        self._assert_conservation()                                     # E N = 0 proven (exactly) BEFORE any numpy cast
        # XVIII-2: the SYMBOLIC model is valid for ANY balanced integer coefficients (XV-1A), but a coefficient with
        # |v| > 2**53 is not float64-exact, so it is not NUMERICALLY EXECUTABLE -- flag it here and refuse it at
        # integrate() ("a symbolic certificate does not imply a numerically executable model"), never over-refusing
        # construction (a huge balanced system is still a legitimate object for conservation analysis).
        self._float_exact = self._is_float_exact()
        # derived EXECUTION artifacts for the float RHS (NOT the conservation authority).  XVIII-2: freeze them as
        # read-only VIEWS over read-only bases.  A view of a non-writeable base cannot have writeable re-enabled -- an
        # OWNING array CAN (the XVII hole), so viewing is what makes the thaw-then-mutate attack impossible.
        E_base = np.array(self._E_int, dtype=float)
        E_base.flags.writeable = False
        self.E = E_base[:]
        N_base = (np.array(self._N_int, dtype=float) if self.reactions
                  else np.zeros((len(self.species), 0), dtype=float))
        N_base.flags.writeable = False
        self.N = N_base[:]
        # XVIII-2: a model certificate over the EXACT execution basis (species identity+order, float E, float N,
        # volume).  integrate() re-derives it from the LIVE attributes and refuses to run under a stale one, so a
        # rebind of self.N / self.E or a species reorder after construction cannot execute silently.
        self._model_certificate = self._compute_certificate()

    def _assert_conservation(self) -> None:
        """Prove E N = 0 with UNBOUNDED PYTHON INTEGERS (XV-1A): a fixed-width int64 product can wrap on large
        coefficients and FALSELY certify an unbalanced reaction.  This product cannot overflow."""
        if not self.reactions:
            return
        ncomp, nsp, nrxn = len(self._E_int), len(self.species), len(self.reactions)
        bad = []
        for k in range(nrxn):
            off = {}
            for c in range(ncomp):
                s = 0
                for i in range(nsp):                                    # pure Python int: exact, no wraparound
                    s += self._E_int[c][i] * self._N_int[i][k]
                if s != 0:
                    off[self.component_labels[c]] = s
            if off:
                bad.append(f"{self.reactions[k].name!r} violates {off}")
        if bad:
            raise ConservationError("reaction(s) do not conserve elements/charge (E N != 0): " + "; ".join(bad))

    def _is_float_exact(self) -> bool:
        """XVIII-2: whether every integer-authority entry survives the float64 cast EXACTLY (|v| <= 2**53).  The
        symbolic conservation proof (E N = 0 in unbounded integers) holds for ANY balanced coefficients, but the solver
        executes the float cast -- a coefficient beyond 2**53 would run a matrix diverging from the certified one.
        Construction stays valid (XV-1A); integrate() consults this flag and refuses a non-executable model."""
        limit = 2 ** 53
        for rows in (self._E_int, self._N_int):
            for row in rows:
                for v in row:
                    if abs(int(v)) > limit:
                        return False
        return True

    def _compute_certificate(self) -> str:
        """A deterministic hash over the EXACT execution basis the integrator runs against: species identity (name,
        composition, charge, phase, substance) in column order, the float E and N matrices, the reactor volume, and --
        XXIII-2b (F1) -- a canonical descriptor of EVERY reaction re-derived from the CURRENT ``self.reactions``: its
        name, its ordered stoichiometry as (full species identity, coeff), and its rate-law descriptor + authority.

        Why the reactions themselves: the RHS reads ``self.reactions`` live (each law's ``evaluate`` takes its own
        reaction's stoich to form the rate), while the old hash bound only the stored ``self.N``.  Rebinding
        ``self.reactions`` to 2A -> 2B therefore ran a second-order rate under an unchanged certificate.  The chart
        described a patient who had already left the table."""
        h = hashlib.sha256()
        keys = [_species_identity_key(sp) for sp in self.species]
        h.update(repr(keys).encode())
        for m in (self.E, self.N):
            arr = np.ascontiguousarray(m, dtype=float)
            h.update(str(arr.shape).encode())
            h.update(arr.tobytes())
        h.update(repr(float(self.volume_L)).encode())
        rxns = [(r.name, tuple((_species_identity_key(sp), int(c)) for sp, c in r.stoich),
                 _kernel_rate_law_descriptor(r.rate_law)) for r in self.reactions]
        h.update(repr(rxns).encode())
        return h.hexdigest()

    def _rederive_N_int(self) -> tuple:
        """XXIII-2b (F1): the integer stoichiometric matrix the CURRENT ``self.reactions`` imply, over the certified
        species columns.  Raises StaleCertificateError if a reaction is malformed or names a species outside them."""
        rows = [[0] * len(self.reactions) for _ in self.species]
        for k, r in enumerate(self.reactions):
            if type(r) is not Reaction:
                raise StaleCertificateError(f"reaction slot {k} holds a {type(r).__name__}, not a Reaction")
            for sp, coeff in r.stoich:
                i = self._index.get(sp)
                if i is None:
                    raise StaleCertificateError(
                        f"reaction {r.name!r} references species {getattr(sp, 'name', sp)!r} outside the certified set")
                rows[i][k] = coeff
        return tuple(tuple(row) for row in rows)

    def _verify_certificate(self) -> None:
        """XVIII-2: refuse to execute if the live execution basis no longer matches the certificate proven at
        construction (self.E/self.N rebound, species reordered, or the volume changed afterward).

        XXIII-2b (F1): ALSO refuse if the reactions were rebound (their descriptors are in the hash), and -- separately,
        so a re-sealed hash cannot relicense it -- if the stored N (the matrix the exact E N = 0 proof was made over)
        is no longer the N the current reactions re-derive to.  A certificate re-stamped over a new stoichiometry
        without a new conservation proof is a forged signature on someone else's operative note."""
        try:
            current = self._compute_certificate()
            n_live = self._rederive_N_int()
        except StaleCertificateError:
            raise
        except (AttributeError, TypeError, ValueError, KeyError) as exc:   # a malformed rebind cannot be re-derived
            raise StaleCertificateError(
                f"the model's reactions can no longer be re-derived ({type(exc).__name__}: {exc}); refusing to "
                f"integrate under a stale certificate (XXIII-2b).") from exc
        if current != self._model_certificate:
            raise StaleCertificateError(
                "the model's execution basis (species / E / N / volume / reactions) was mutated after certification; "
                "refusing to integrate under a stale certificate (XVIII-2 deep-immutability, XXIII-2b).")
        n_float = (np.array(n_live, dtype=float) if self.reactions
                   else np.zeros((len(self.species), 0), dtype=float))
        if n_live != self._N_int or np.asarray(self.N).shape != n_float.shape \
                or not np.array_equal(np.asarray(self.N, dtype=float), n_float):
            raise StaleCertificateError(
                "the stored stoichiometric matrix N no longer equals the N re-derived from the current reactions; the "
                "exact conservation proof covers a stoichiometry that is no longer the one declared -- refusing to "
                "integrate (XXIII-2b).")

    def component_amounts(self, amounts: dict) -> dict:
        """E n: the conserved element + charge totals of an inventory dict."""
        for sp in amounts:
            if sp not in self._index:
                raise KernelError(f"component_amounts references unknown species {getattr(sp, 'name', sp)!r}")
        n = np.array([float(amounts.get(sp, 0.0)) for sp in self.species])
        totals = self.E @ n
        return {self.component_labels[i]: float(totals[i]) for i in range(len(totals))}

    def integrate(self, n0: dict, *, duration: float, source: dict | None = None, temperature_K: float = 298.15,
                  n_samples: int = 50, method: str = "BDF", rtol: float = 1e-9, atol: float = 1e-15,
                  declared_kinetic_tier: str = ASSUMED_PARAMETER) -> NetworkTrajectory:
        """Evolve dn/dt = N r(n) + q from inventories ``n0`` over ``duration`` seconds (concentration basis, XV-1C).

        FAIL-CLOSED on missing kinetics: every reaction MUST carry a rate law, else MissingKineticsError.  ``source``
        is the external q (mol/s) per species, default 0 (XV-1D: finite, typed, known species only; the external
        ledger is verified independently).  The default method is BDF (implicit, stiff-capable) because a reaction
        network with disparate rate constants is typically stiff.  Conservation, the external ledger and positivity
        are VERIFIED on the trajectory (XV-1E) and the evidential tier is DERIVED from those checks, never the
        caller's word (``declared_kinetic_tier`` can only lower the admitted tier, never inflate it)."""
        self._verify_certificate()                                      # XVIII-2: never integrate under a stale certificate
        if not self._float_exact:                                       # XVIII-2: symbolic cert != numerically executable
            raise ExecutionBasisError(
                "this model carries a coefficient with |coeff| > 2**53: the symbolic conservation certificate holds, "
                "but the float64 execution basis cannot represent it exactly, so the integrated trajectory would "
                "diverge from the certified model. Refusing to integrate (XVIII-2).")
        missing = [r.name for r in self.reactions if r.rate_law is RATE_UNKNOWN]
        if missing:
            raise MissingKineticsError(
                f"RATE_UNKNOWN for reaction(s) {missing}: refusing to integrate (never a silent k = 0). Declare a "
                f"rate law or remove the reaction.")
        if not (isinstance(duration, (int, float)) and math.isfinite(duration) and duration > 0):
            raise KernelError("duration must be finite and > 0")
        rank(declared_kinetic_tier)                                     # a typo in the declared tier fails loudly
        owned = [("system", r) for r in self.reactions]                 # XXIV-2A: no sourced constant off its domain
        off_domain = _adm.temperature_domain_violations(owned, temperature_K)
        if off_domain:
            raise SourceDomainError(
                f"temperature_K={float(temperature_K):.2f} is outside the sourced domain of {off_domain} "
                f"(reaction, field, sourced T_K): no validated temperature law is declared, so the constant would "
                f"execute unchanged at the wrong temperature. Refusing (XXIV-2A); no extrapolation is performed.")
        for sp in n0:                                                   # XV-1D: no unknown initial species silently ignored
            if sp not in self._index:
                raise KernelError(f"initial inventory references unknown species {getattr(sp, 'name', sp)!r}")
        q = np.zeros(len(self.species))
        if source:
            for sp, val in source.items():
                if sp not in self._index:
                    raise KernelError(f"source references unknown species {getattr(sp, 'name', sp)!r}")
                if isinstance(val, bool) or not (isinstance(val, (int, float)) and math.isfinite(val)):
                    raise KernelError(f"source rate for {sp.name!r} must be a finite mol/s value")
                q[self._index[sp]] = float(val)

        order = self.species
        idx = self._index
        V = self.volume_L

        def rhs(_t, y):
            conc = {sp: y[idx[sp]] / V for sp in order}                 # mol/L
            dn = q.copy()
            for k, r in enumerate(self.reactions):
                r_vol = r.rate_law.evaluate(r, conc)                    # mol L^-1 s^-1
                dn = dn + (V * r_vol) * self.N[:, k]                    # molar rate mol/s
            return dn

        y0 = np.array([float(n0.get(sp, 0.0)) for sp in order])
        if not np.all(np.isfinite(y0)):                                  # XV-1D/XVII-D3: NaN slips `< 0` (NaN<0 False)
            raise KernelError("initial inventories must be finite (no NaN/Inf)")
        if np.any(y0 < 0):
            raise KernelError("initial inventories must be >= 0")
        t_eval = np.linspace(0.0, float(duration), n_samples)
        sol = solve_ivp(rhs, (0.0, float(duration)), y0, method=method, t_eval=t_eval, rtol=rtol, atol=atol)
        if not sol.success:
            raise KernelError(f"integration failed ({method}): {sol.message}")

        comp0 = self.E @ y0                                             # conserved totals at t0
        comp_rate = self.E @ q                                          # d(E n)/dt from the external feed (components/s)
        max_drift = 0.0                                                 # RAW change in conserved totals
        max_ledger_residual = 0.0                                       # LEDGER-closed residual (closed AND open)
        min_amount = float("inf")
        amounts_series = []
        for j, t in enumerate(sol.t):
            yj = sol.y[:, j]
            min_amount = min(min_amount, float(yj.min()))
            comp_j = self.E @ yj
            max_drift = max(max_drift, float(np.max(np.abs(comp_j - comp0))))
            # independent ledger: the SOLVER's integrated totals vs the DECLARED feed integral (E q) t -- not a tautology
            max_ledger_residual = max(max_ledger_residual, float(np.max(np.abs(comp_j - comp0 - comp_rate * t))))
            amounts_series.append({sp: float(yj[idx[sp]]) for sp in order})

        # DERIVED verification (XV-1E): tolerance scales with the magnitude of material present/moved
        scale = max(1.0, float(np.max(np.abs(comp0))) if comp0.size else 1.0,
                    float(np.max(np.abs(comp_rate))) * float(duration) if comp_rate.size else 0.0)
        ledger_tol = 1e-6 * scale
        # XXIV-1B: the PHYSICAL positivity floor is caller-independent (1e-12 mol + 1e-9 x the species' own peak); the
        # caller's atol only defines the band within which the sign is numerically UNRESOLVED -- never a pass.
        slot_min = sol.y.min(axis=1)
        slot_scale = np.maximum(np.abs(y0), np.abs(sol.y).max(axis=1))
        pos = _adm.positivity_audit(slot_min, slot_scale, abs_floor=1e-12, solver_atol=atol, solver_rtol=rtol,
                                    atol_factor=10.0)
        positivity_held = pos.held
        negative_minima = {order[j].name: v for j, v in pos.negative_minima.items()}
        external_ledger_closed = max_ledger_residual <= ledger_tol
        # XXIV-1C: three separate charge claims (the charge row is the LAST row of E).
        zrow = self.E[-1]
        ionic_series = np.abs(zrow) @ np.abs(sol.y)
        supplied = float(zrow @ q) * float(duration)
        q_series = zrow @ sol.y
        charge_ledger_resid = float(np.max(np.abs(q_series - float(zrow @ y0) - float(zrow @ q) * sol.t)))
        ionic_scale = max(float(np.max(ionic_series)), abs(supplied))
        cv = _adm.charge_validity(charged=any(sp.charge for sp in order), supplied=supplied,
                                  accounted=charge_ledger_resid <= 1e-12 + 1e-6 * ionic_scale, ionic_scale=ionic_scale,
                                  declared_net=float(zrow @ y0))
        solver_completed = bool(sol.success)
        notes = ()
        if not external_ledger_closed:
            notes += (f"external material ledger did NOT close (residual {max_ledger_residual:.3e} > tol "
                      f"{ledger_tol:.3e}); the integrated inventories do not match the declared source integral",)
        structural_ok = solver_completed and positivity_held and external_ledger_closed
        structural_tier = STRUCTURALLY_CONSERVING if structural_ok else REFUSED
        admitted_tier = weakest(structural_tier, declared_kinetic_tier)
        if cv.floors_admitted_tier:                                     # XXIV-1C: physically unsupported net charge
            admitted_tier = REFUSED
        receipt = VerificationReceipt(
            solver_completed=solver_completed, positivity_held=positivity_held,
            external_ledger_closed=external_ledger_closed, conservation_residual=max_drift,
            external_ledger_residual=max_ledger_residual, min_inventory=min_amount, tolerance=ledger_tol,
            structural_tier=structural_tier, declared_kinetic_tier=declared_kinetic_tier,
            admitted_tier=admitted_tier, notes=notes, positivity_verdict=pos.verdict, negative_minima=negative_minima,
            charge_validity=cv, source_domain=_adm.source_domain_label(owned, temperature_K))

        caveats = ()
        if not positivity_held:
            caveats += (f"positivity {pos.verdict}: a species inventory went negative (min {min_amount:.3e}) beyond its "
                        f"caller-independent physical floor -- no physical admissibility claim (XXIV-1B)",)
        if cv.floors_admitted_tier:
            caveats += (f"charge: {cv.bulk_electroneutrality} -- {cv.explanation}; admitted tier REFUSED (XXIV-1C)",)
        if not external_ledger_closed:
            caveats += notes
        return NetworkTrajectory(
            times=tuple(float(t) for t in sol.t), species=tuple(order), amounts=tuple(amounts_series),
            component_labels=self.component_labels, volume_L=V, max_component_drift=max_drift,
            external_ledger_residual=max_ledger_residual, min_amount=min_amount,
            solver_success=solver_completed, integrator=f"scipy.solve_ivp/{method}", receipt=receipt,
            tier=admitted_tier, caveats=caveats)
