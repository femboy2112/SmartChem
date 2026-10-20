"""Mechanism adapter: DERIVE a sandbox mechanism inventory from REAL SmartChem objects (Wave A1).

Ugh, fine -- the one rule here is trust nothing the caller hands us about conservation.  Everything in the
inventory is derived from the molecules' OWN ``formula`` (dict element->count) and ``charge`` (one global int
per Molecule), in EXACT integers (Python int -> numpy int64).  Floats appear only at the twocell boundary,
and that boundary lives in ``mechanism_types``, not here.

THE CENTRAL LAW: a caller-supplied E can never certify anything.  ``derive_inventory`` builds E itself, checks
``E_derived @ N == 0`` itself, and, if the caller also supplied an E, cross-checks it against the derived one
and REFUSES on any disagreement.  A forged E crafted so that ``E_forged @ N == 0`` still dies, because the
supplied matrix is only ever compared against the derived one, never used.

Representation walls (REFUSED, never defaulted): isotope, stereochemistry, per-atom/local formal charge,
material, phase.  ``Molecule`` is a constitution-only graph with ONE global charge (the #105 wall), so any claim
that needs more is a typed refusal.  ``parse_smiles`` silently drops those features, so ``source_smiles`` lets
a caller route the original text through ``parse_smiles_features`` and have the dropped features surface as
refusals instead of vanishing.

SYNTHETIC / experimental.  Nothing here edits or depends on anything but READING smartchem.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Sequence

import numpy as np

from smartchem.category import Molecule
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles_features, resonance_identity

CHARGE_LABEL = "charge"
MAX_MULTIPLICITY = 10**6   # same ceiling as twocell.MAX_COEFF; also keeps int64 arithmetic nowhere near overflow


# ------------------------------------------------------------------------------------------- refusals
class RefusalKind(str, Enum):
    NON_CONSERVING = "NON_CONSERVING"          # derived E @ N != 0
    FORGED_INVENTORY = "FORGED_INVENTORY"      # supplied E disagrees with the derived E
    VACUOUS_INVENTORY = "VACUOUS_INVENTORY"    # derived E is all zero: E @ N = 0 would certify nothing
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"    # isotope / stereo / local charge / material / phase
    MALFORMED_INPUT = "MALFORMED_INPUT"
    BOUND_EXCEEDED = "BOUND_EXCEEDED"


class UnsupportedClaim(str, Enum):
    ISOTOPE = "ISOTOPE"
    STEREO = "STEREO"
    LOCAL_CHARGE = "LOCAL_CHARGE"
    MATERIAL = "MATERIAL"
    PHASE = "PHASE"


class AdapterRefusal(Exception):
    """A typed, fail-closed refusal.  ``kind`` says why; ``claim`` is set for UNSUPPORTED_CLAIM."""

    def __init__(self, kind: RefusalKind, detail: str, claim: Optional[UnsupportedClaim] = None):
        super().__init__(f"{kind.value}: {detail}")
        self.kind = kind
        self.detail = detail
        self.claim = claim


@dataclass(frozen=True)
class Claim:
    """A claim a caller makes about a species that the Molecule representation cannot carry.  ANY claim refuses."""
    kind: UnsupportedClaim
    species: str = ""
    detail: str = ""


# ------------------------------------------------------------------------------------------- derived record
@dataclass(frozen=True, eq=False)
class InventoryDerivation:
    """Everything derived from the molecules, exact-integer.  Arrays are int64 and read-only.

    species          -- unique display names (Hill formula + charge, disambiguated by identity digest if needed)
    identities       -- per-species (resonance_identity, state) key
    compositions     -- per-species tuple of (element, count), sorted by element
    charges          -- per-species net charge (Molecule.charge)
    element_labels   -- sorted elements, then 'charge'
    reactant/product -- (S, 1) complex multiplicity matrices; N = product - reactant; E: (len(labels), S)
    """
    species: tuple
    identities: tuple
    compositions: tuple
    charges: tuple
    element_labels: tuple
    reactant: np.ndarray
    product: np.ndarray
    N: np.ndarray
    E: np.ndarray

    def residual(self) -> np.ndarray:
        return self.E @ self.N


# ------------------------------------------------------------------------------------------- helpers
def build_E(compositions: Sequence, charges: Sequence) -> tuple:
    """Exact-integer element+charge inventory from per-species compositions and charges.
    Returns (element_labels, E[int64]).  Independent of any caller-supplied matrix."""
    elements = sorted({el for comp in compositions for el, _ in comp})
    labels = tuple(elements) + (CHARGE_LABEL,)
    E = np.zeros((len(labels), len(compositions)), dtype=np.int64)
    row = {el: i for i, el in enumerate(elements)}
    for j, (comp, q) in enumerate(zip(compositions, charges)):
        for el, n in comp:
            E[row[el], j] = int(n)
        E[-1, j] = int(q)
    return labels, E


def _hill(comp, charge: int) -> str:
    d = dict(comp)
    order = (["C", "H"] if "C" in d else []) + sorted(k for k in d if not ("C" in d and k in ("C", "H")))
    s = "".join(f"{el}{d[el] if d[el] != 1 else ''}" for el in order if el in d) or "e"
    if charge:
        s += ("+" if charge > 0 else "-") + (str(abs(charge)) if abs(charge) != 1 else "")
    return s


def _label_claims(m: Molecule, name: str) -> list:
    """Atom labels that smuggle a feature the graph cannot carry (a label is a bare element symbol or component)."""
    out = []
    for a in m.atoms:
        if re.match(r"^\d", a) or a.startswith("["):
            out.append(Claim(UnsupportedClaim.ISOTOPE, name, f"atom label {a!r} looks isotope-labelled"))
        elif "@" in a:
            out.append(Claim(UnsupportedClaim.STEREO, name, f"atom label {a!r} carries a stereo marker"))
        elif re.search(r"[+\-]", a):
            out.append(Claim(UnsupportedClaim.LOCAL_CHARGE, name, f"atom label {a!r} carries a local charge"))
    return out


def smiles_claims(text: str) -> list:
    """Features a SMILES declares that Molecule cannot keep, as Claims (via the real parse_smiles_features)."""
    _, f = parse_smiles_features(text)
    out = []
    if f.isotopes:
        out.append(Claim(UnsupportedClaim.ISOTOPE, text, f"isotopes {f.isotopes}"))
    if f.tetrahedral_stereo or f.double_bond_stereo:
        out.append(Claim(UnsupportedClaim.STEREO, text, "tetrahedral/double-bond stereo marker"))
    # per-atom charge PLACEMENT is exactly what Molecule's single global charge cannot hold.  Use the codebase's
    # OWN sound predicate (smartchem.smiles.SmilesFeatures.has_local_charge_structure), not a re-derived heuristic:
    # charged_atoms >= 1 and (net_charge == 0 OR charged_atoms >= 2) -- so same-sign multi-site charge (e.g.
    # [NH3+]CC[NH3+], two +1 sites, net +2) is caught, which the weaker `charged_atoms > |net_charge|` missed.
    if f.has_local_charge_structure:
        out.append(Claim(UnsupportedClaim.LOCAL_CHARGE, text,
                         f"{f.charged_atoms} per-atom charge site(s), net {f.net_charge}: a per-atom charge "
                         "distribution the single global Molecule.charge cannot hold (#105 wall)"))
    return out


def _check_molecules(side: str, mols: Sequence) -> None:
    if type(mols) is not tuple and type(mols) is not list:
        raise AdapterRefusal(RefusalKind.MALFORMED_INPUT, f"{side} must be a sequence of Molecule")
    if not mols:
        raise AdapterRefusal(RefusalKind.MALFORMED_INPUT, f"{side} must be non-empty")
    for m in mols:
        if type(m) is not Molecule:
            raise AdapterRefusal(RefusalKind.MALFORMED_INPUT, f"{side} entry {m!r} is not a smartchem Molecule")


def _cross_check_supplied(derived_labels, derived_E, supplied_E, supplied_labels) -> None:
    """The supplied E is NEVER used -- only compared.  Same label set, same shape, identical integers per row."""
    try:
        sup = np.asarray(supplied_E)
        labels = tuple(supplied_labels)
    except Exception as exc:  # noqa: BLE001 -- an unparseable supplied E is itself a refusal
        raise AdapterRefusal(RefusalKind.FORGED_INVENTORY, f"supplied E is not array-like: {exc}") from exc
    if sup.ndim != 2 or sup.shape != (len(labels), derived_E.shape[1]):
        raise AdapterRefusal(RefusalKind.FORGED_INVENTORY,
                             f"supplied E shape {sup.shape} does not match {len(labels)} labels x "
                             f"{derived_E.shape[1]} species")
    if len(set(labels)) != len(labels) or set(labels) != set(derived_labels):
        raise AdapterRefusal(RefusalKind.FORGED_INVENTORY,
                             f"supplied labels {sorted(labels)} != derived inventory rows {sorted(derived_labels)} "
                             "(an omitted or invented conserved quantity)")
    for i, lab in enumerate(labels):
        want = derived_E[derived_labels.index(lab)]
        got = sup[i]
        if not (np.all(np.isfinite(got.astype(float))) and np.all(got == np.round(got))
                and np.array_equal(got.astype(np.int64), want)):
            raise AdapterRefusal(RefusalKind.FORGED_INVENTORY,
                                 f"supplied E row {lab!r} = {got.tolist()} disagrees with the row derived from the "
                                 f"molecules' own formulae/charge = {want.tolist()}")


# ------------------------------------------------------------------------------------------- the adapter
def derive_inventory(reactants: Sequence, products: Sequence, *, supplied_E=None, supplied_labels=None,
                     claims: Iterable = (), source_smiles: Iterable = ()) -> InventoryDerivation:
    """Derive the exact inventory of ONE transformation ``reactants -> products`` (multisets of Molecule).

    Works on raw molecule multisets, so a genuinely NON-conserving transformation (which ExperimentStep would
    refuse at construction) can still be presented and correctly refused HERE by independent derivation.

    Order of refusal: unsupported claims -> malformed/bounds -> derive -> forged supplied E -> E@N != 0 -> vacuous.
    """
    reactants, products = tuple(reactants), tuple(products)
    for c in claims:
        raise AdapterRefusal(RefusalKind.UNSUPPORTED_CLAIM,
                             f"{c.kind.value} claim on {c.species or '<unspecified>'!r} is not representable "
                             f"({c.detail or 'no detail'}); refused, not defaulted", c.kind)
    for text in source_smiles:
        found = smiles_claims(text)
        if found:
            c = found[0]
            raise AdapterRefusal(RefusalKind.UNSUPPORTED_CLAIM,
                                 f"source SMILES {text!r} declares {c.kind.value} ({c.detail}) which the "
                                 "constitution-only Molecule drops; refused, not silently flattened", c.kind)
    _check_molecules("reactants", reactants)
    _check_molecules("products", products)

    keys, records = [], []          # first-appearance order over reactants then products
    react_count: dict = {}
    prod_count: dict = {}
    for side, mols, counts in (("reactants", reactants, react_count), ("products", products, prod_count)):
        for m in mols:
            try:
                ident = resonance_identity(m)
            except Exception as exc:  # noqa: BLE001
                raise AdapterRefusal(RefusalKind.MALFORMED_INPUT, f"cannot identify {m!r}: {exc}") from exc
            key = (ident, m.state)
            comp = tuple(sorted((el, int(n)) for el, n in m.formula.items()))
            name_for_claims = _hill(comp, m.charge)
            found = _label_claims(m, name_for_claims)
            if found:
                c = found[0]
                raise AdapterRefusal(RefusalKind.UNSUPPORTED_CLAIM, f"{c.detail} on {side[:-1]} {name_for_claims}",
                                     c.kind)
            if key not in keys:
                keys.append(key)
                records.append((comp, int(m.charge), m.state))
            counts[key] = counts.get(key, 0) + 1

    S = len(keys)
    names, seen = [], {}
    for key, (comp, q, state) in zip(keys, records):
        base = _hill(comp, q) + (f"[{state}]" if state else "")
        if base in seen:           # isomers / distinct species with one formula: disambiguate by identity digest
            base = f"{base}~{key[0][:8]}"
        seen[base] = key
        names.append(base)

    reactant = np.zeros((S, 1), dtype=np.int64)
    product = np.zeros((S, 1), dtype=np.int64)
    for i, key in enumerate(keys):
        reactant[i, 0] = react_count.get(key, 0)
        product[i, 0] = prod_count.get(key, 0)
    if max(int(reactant.max()), int(product.max())) > MAX_MULTIPLICITY:
        raise AdapterRefusal(RefusalKind.BOUND_EXCEEDED, f"a multiplicity exceeds {MAX_MULTIPLICITY}")
    N = product - reactant
    compositions = tuple(r[0] for r in records)
    charges = tuple(r[1] for r in records)
    labels, E = build_E(compositions, charges)

    # --- THE CENTRAL LAW: the supplied E (if any) is compared, never trusted ------------------------------
    if supplied_E is not None:
        if supplied_labels is None:
            raise AdapterRefusal(RefusalKind.FORGED_INVENTORY, "a supplied E needs its row labels to be cross-checked")
        _cross_check_supplied(labels, E, supplied_E, supplied_labels)

    res = E @ N
    if np.any(res != 0):
        bad = {labels[i]: int(res[i, 0]) for i in range(len(labels)) if res[i, 0] != 0}
        raise AdapterRefusal(RefusalKind.NON_CONSERVING,
                             f"derived E @ N != 0 (net imbalance per conserved quantity: {bad}); this "
                             "transformation is not a mechanism")
    if not np.any(E):
        raise AdapterRefusal(RefusalKind.VACUOUS_INVENTORY, "derived inventory is all zero; conserves nothing")

    for arr in (reactant, product, N, E):
        arr.setflags(write=False)
    return InventoryDerivation(tuple(names), tuple(keys), compositions, charges, labels, reactant, product, N, E)


def adapt_step(step: ExperimentStep, *, supplied_E=None, supplied_labels=None, claims: Iterable = (),
               source_smiles: Iterable = ()) -> InventoryDerivation:
    """Derive the inventory of a REAL ExperimentStep.

    The step's own conservation certificate is NOT relied on: the inventory is re-derived from the step's
    molecules by this module's own code (same independent-path discipline the step itself uses)."""
    if type(step) is not ExperimentStep:
        raise AdapterRefusal(RefusalKind.MALFORMED_INPUT, "adapt_step needs a smartchem ExperimentStep")
    return derive_inventory(step.reactants, step.products, supplied_E=supplied_E, supplied_labels=supplied_labels,
                            claims=claims, source_smiles=source_smiles)
