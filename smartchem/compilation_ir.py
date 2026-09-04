"""IR-CHEM-01 (first brick) -- the shared ``ChemicalCompilationIR`` both compiler directions speak.

The standard (section 4.1) requires ONE versioned intermediate representation that ``decompile`` emits and
``recompile`` consumes, so the two operations are views of a single typed artifact rather than two adjacent
search kinds.  This module builds the IR *envelope*, wires both compiler directions to emit it, carries
first-class typed section-5.3 :class:`~smartchem.identity.IdentityLoss` records inside the IR (IR-LOSS-01), and
carries the FULL section 8.1 :class:`Section81ReceiptView` -- the ~20 mandated search-receipt counters
(nodes_visited, transforms_considered, candidates_rejected_by_reason, the enumeration-complete flags, ...) --
so a consumer reading the transported IR sees the whole receipt, not just its digest (IR-CHEM-01).

The one property that makes this an IR and not a display struct (section 4.1, verbatim)
------------------------------------------------------------------------------------------
> The serialized digest MUST change when any semantic input changes, including identity state, transform/evidence
> provider version, terminal policy, search bound, constraint, or evidence grade. Display labels and ordering
> MUST NOT change a semantic digest.

So every field here is a *semantic* fact -- a canonical identity digest, a canonical terminal-policy digest, the
declared search bounds, the search status, and the candidate set in canonical (digest-sorted) order.  No display
label, no presentation order, and no wall-clock enters the value.  Two IRs built from the same semantic request
over the same registry share a digest; changing the target, the inventory, or a search bound changes it -- even
when the change does not happen to alter the candidate set (the bounds ride in ``request_digest``, a field, so
they are part of the value's own digest).

What this is NOT (stated loudly, W3): the IR certifies the *bookkeeping* of a bounded search -- what was asked,
what was searched, how complete it was, and which conservation-valid candidates came back.  It asserts nothing
about chemistry.  A formula-level candidate is ``FORMAL_CANDIDATE`` and is never lifted to a structure claim.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum

from .category import Bond, Molecule
from .contracts import Digestible, canonical_digest
from .decompiler import DecompositionEdge, DecompositionGraph, Formula, search_decomposition
from .decompiler_mediated import MediatedEdge
from .structure_descent import _fkey
from .identity import IdentityLoss, identity_loss_from_payload, identity_loss_to_payload
from .search import PRIMARY_RESOLVABLE_8_2_STATUSES, STANDARD_8_2_STATUSES, SearchStatus
from .transform_provider import DEFAULT_TRANSFORM_REGISTRY, TransformProviderRegistry
# the transform-registry identity lives in a shared leaf (below both the search and IR layers) so the receipts
# and the IR stamp the SAME digest (see smartchem.transform_registry).
from .transform_registry import transform_registry_digest as _transform_registry_digest

__all__ = [
    "CHEMICAL_COMPILATION_IR_SCHEMA",
    "CHEMICAL_IDENTITY_SCHEMA",
    "CANDIDATE_SUMMARY_SCHEMA",
    "SEARCH_RECEIPT_VIEW_SCHEMA",
    "STRUCTURAL_SPECIES_SCHEMA",
    "STRUCTURAL_CANDIDATE_SCHEMA",
    "CompilationOperation",
    "IdentityLayer",
    "TransformDirection",
    "ChemicalIdentity",
    "CandidateSummary",
    "StructuralSpecies",
    "StructuralCandidate",
    "Section81ReceiptView",
    "ChemicalCompilationIR",
    "InverseStatus",
    "InverseResult",
    "decompile_to_ir",
    "recompile_to_ir",
    "decompile_structure_to_ir",
    "ir_to_payload",
    "ir_from_payload",
    "serialize_ir",
    "deserialize_ir",
    "recompile_from_serialized",
]

# v1alpha3 (IR-LOSS-01): identity_losses became typed IdentityLoss records (array[str] -> array[object]).
# v1alpha4 (IR-CHEM-01): the IR carries the FULL section 8.1 receipt (Section81ReceiptView) instead of only its
# digest -- search_receipt_digest (str) -> search_receipt (object with the ~20 mandated counters).
# v1alpha5 (IR-STRUCT-01): the IR carries first-class typed StructuralCandidate records -- a structural
# decomposition (parent/product STRUCTURE identities, the scission edit witness, primitive stoichiometry, the
# producing provider's id/version, and the EXACT forgetful formula projection) rides INSIDE the IR, no longer
# reduced to a formula edge as the sole shared artifact.  All are genuine serialized-shape changes, so the schema
# version bumps with each (and the value digest shifts, since structural_candidates is a covered field).
CHEMICAL_COMPILATION_IR_SCHEMA = "smartchem.compilation-ir/chemical-compilation-ir-v1alpha5"
CHEMICAL_IDENTITY_SCHEMA = "smartchem.compilation-ir/chemical-identity-v1alpha1"
CANDIDATE_SUMMARY_SCHEMA = "smartchem.compilation-ir/candidate-summary-v1alpha1"
SEARCH_RECEIPT_VIEW_SCHEMA = "smartchem.compilation-ir/search-receipt-view-v1alpha1"
# v1alpha2 (IR-STRUCT-01 red-team fold): the species carries its canonical molecular graph (atoms/bonds/charge/
# state) so its structure identity and formula are RE-VERIFIABLE on read -- a forged identity/formula/isomer swap
# is refused, not trusted.  A genuine serialized-shape change, so the record schema bumps.
STRUCTURAL_SPECIES_SCHEMA = "smartchem.compilation-ir/structural-species-v1alpha2"
STRUCTURAL_CANDIDATE_SCHEMA = "smartchem.compilation-ir/structural-candidate-v1alpha1"

# The closed set of section-8.1 search kinds the engine receipts emit (routes.py / decompiler.py) plus the
# structural decompile descent (structure_descent.capped_scissions, IR-STRUCT-01).  A view is a projection off
# exactly one of them, so a search_kind outside this set is a tampered payload (red-team fold).
_KNOWN_SEARCH_KINDS = ("LINEAR_ROUTE", "CONVERGENT_DAG", "FORMULA_DECOMPOSITION", "STRUCTURE_DECOMPOSITION")


class CompilationOperation(str, Enum):
    DECOMPILE = "DECOMPILE"
    RECOMPILE = "RECOMPILE"


class IdentityLayer(str, Enum):
    """The identity layer a claim is made at -- a minimal first cut of section 5.1's FormulaIdentity/
    MoleculeIdentity distinction.  It records WHICH layer a species is known at so a formula-level target is never
    silently treated as a structure-level one; the full stereo/isotope/salt/mixture model is ID-LAYER-01 (TODO).
    """

    FORMULA = "FORMULA"        # elemental counts + charge, no topology claim
    STRUCTURE = "STRUCTURE"    # an atom/bond graph (a Molecule)


@dataclass(frozen=True)
class ChemicalIdentity(Digestible):
    """A typed target identity: the layer it is known at, a canonical string, and the underlying value's digest."""

    schema_version: str
    layer: IdentityLayer
    canonical_repr: str
    identity_digest: str

    def __post_init__(self) -> None:
        if self.schema_version != CHEMICAL_IDENTITY_SCHEMA:
            raise ValueError(f"schema_version must be exactly {CHEMICAL_IDENTITY_SCHEMA!r}")
        if not isinstance(self.layer, IdentityLayer):
            raise TypeError("layer must be an IdentityLayer")
        for name in ("canonical_repr", "identity_digest"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")

    @classmethod
    def of_formula(cls, formula: Formula) -> "ChemicalIdentity":
        if type(formula) is not Formula:
            raise TypeError("of_formula needs a Formula")
        return cls(CHEMICAL_IDENTITY_SCHEMA, IdentityLayer.FORMULA, repr(formula), canonical_digest(formula))

    @classmethod
    def of_molecule(cls, molecule: "object") -> "ChemicalIdentity":
        """A STRUCTURE-layer identity for a :class:`~smartchem.category.Molecule`.

        The ``identity_digest`` is byte-congruent with the pipeline's own molecular identity
        (:func:`_structure_ident`, the same ``canonical()``/``asgiven:`` fallback that
        :mod:`smartchem.experiment.routes`/``step``/``dag`` use), so a structural IR target is the SAME
        value the route/DAG search keys on -- a same-formula isomer is a distinct identity here (section 5.4),
        never collapsed to its formula.
        """
        from .category import Molecule
        if type(molecule) is not Molecule:
            raise TypeError("of_molecule needs a smartchem.category.Molecule")
        return cls(CHEMICAL_IDENTITY_SCHEMA, IdentityLayer.STRUCTURE, repr(molecule), _structure_ident(molecule))


@dataclass(frozen=True)
class CandidateSummary(Digestible):
    """A presentation-invariant summary of one candidate in the IR: its kind, its canonical digest, its balanced
    equation (already canonical, sorted at the source), and the readiness tier it was generated at.

    The ``candidate_digest`` -- not the equation string -- is the identity; the equation is a human convenience
    that rides along.  A formula edge is a ``FORMAL_CANDIDATE`` (conservation only), never a structure claim.
    """

    schema_version: str
    candidate_kind: str
    candidate_digest: str
    equation: str
    readiness_tier: str

    _KINDS = ("FORMULA_EDGE", "ROUTE", "DAG")

    def __post_init__(self) -> None:
        if self.schema_version != CANDIDATE_SUMMARY_SCHEMA:
            raise ValueError(f"schema_version must be exactly {CANDIDATE_SUMMARY_SCHEMA!r}")
        if self.candidate_kind not in self._KINDS:
            raise ValueError(f"candidate_kind must be one of {self._KINDS}")
        for name in ("candidate_digest", "equation", "readiness_tier"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")


class TransformDirection(str, Enum):
    """The direction a structural transform primitive is stated in.

    A ``DECOMPOSE`` primitive reads a parent into products (its reverse is the assembly step a synthesis route
    takes).  A structural DECOMPILE emits ``DECOMPOSE`` candidates; the reverse orientation is the recompiler's
    job and is represented by the route/DAG candidates, not by flipping this field.
    """

    DECOMPOSE = "DECOMPOSE"


@dataclass(frozen=True)
class StructuralSpecies(Digestible):
    """One species in a :class:`StructuralCandidate`, carrying its canonical molecular GRAPH (IR-STRUCT-01).

    ``structure`` is the STRUCTURE-layer identity -- WHICH isomer; a same-formula isomer is a distinct species
    here (section 5.4), never collapsed to its formula.  ``formula`` is the exact composition it forgets to.  But
    an identity digest is one-way and a formula is a free field, so a payload could once forge either -- swapping
    the structure identity for a DIFFERENT real isomer while leaving the formula (hence the whole forgetful square)
    intact (red-team fold).  So the species now also carries the canonical molecular graph (``atoms``/``bonds``/
    ``charge``/``state``) as the RE-VERIFIABLE source of truth: ``__post_init__`` rebuilds the
    :class:`~smartchem.category.Molecule` and refuses unless the stored ``structure`` identity AND ``formula`` are
    exactly what that graph actually is.  A forged identity, ``canonical_repr``, formula, or isomer swap is thus
    refused on read; and the structure genuinely RIDES inside the artifact (the point of IR-STRUCT-01), not as an
    opaque digest a tampered payload could reassign.  The graph is stored CANONICAL, so the record's identity is
    presentation-invariant (two presentations of one molecule store one graph).
    """

    schema_version: str
    structure: ChemicalIdentity
    formula: Formula
    atoms: tuple[str, ...]
    bonds: tuple[tuple[int, int, int], ...]
    charge: int
    state: str

    def __post_init__(self) -> None:
        if self.schema_version != STRUCTURAL_SPECIES_SCHEMA:
            raise ValueError(f"schema_version must be exactly {STRUCTURAL_SPECIES_SCHEMA!r}")
        if type(self.structure) is not ChemicalIdentity:
            raise TypeError("structure must be a ChemicalIdentity")
        if self.structure.layer is not IdentityLayer.STRUCTURE:
            raise ValueError("a structural species' structure identity must be at the STRUCTURE layer")
        if type(self.formula) is not Formula:
            raise TypeError("formula must be a Formula")
        if type(self.atoms) is not tuple or not self.atoms or any(not isinstance(a, str) or not a for a in self.atoms):
            raise ValueError("atoms must be a non-empty tuple of element-symbol strings")
        if type(self.bonds) is not tuple:
            raise TypeError("bonds must be a tuple of (i, j, order) triples")
        n = len(self.atoms)
        prev: "tuple[int, int, int] | None" = None
        seen: set[tuple[int, int]] = set()
        for triple in self.bonds:
            if type(triple) is not tuple or len(triple) != 3 or any(type(x) is not int for x in triple):
                raise TypeError("each bond must be an (i, j, order) triple of ints")
            i, j, order = triple
            if not (0 <= i < j < n):
                raise ValueError(f"bond ({i}, {j}) must have 0 <= i < j < {n} (canonical undirected order)")
            if order < 1:
                raise ValueError("bond order must be a positive int")
            if prev is not None and triple < prev:
                raise ValueError("bonds must be in canonical sorted order")
            if (i, j) in seen:
                raise ValueError(f"bond ({i}, {j}) appears twice")
            seen.add((i, j))
            prev = triple
        if type(self.charge) is not int:
            raise TypeError("charge must be an int")
        if type(self.state) is not str:
            raise TypeError("state must be a str")
        # THE CERTIFICATE: the stored identity and formula MUST be what the stored graph actually is.  A forged
        # structure identity (a different real isomer's digest), canonical_repr, or formula that disagrees with the
        # graph is refused here -- the structure identity is no longer an unverifiable label (red-team fold).
        rebuilt = self.molecule
        if rebuilt.charge != self.charge:
            raise ValueError("charge disagrees with the rebuilt molecular graph")
        actual_identity = ChemicalIdentity.of_molecule(rebuilt)
        if actual_identity != self.structure:
            raise ValueError(
                "the stored structure identity does not match the stored molecular graph "
                f"(graph is {actual_identity.identity_digest}, stored {self.structure.identity_digest}); "
                "a forged or isomer-swapped structure identity is refused, not trusted"
            )
        if Formula.of(rebuilt.formula, rebuilt.charge) != self.formula:
            raise ValueError("the stored formula does not match the stored molecular graph; a forged formula is refused")

    @property
    def molecule(self) -> "Molecule":
        """Rebuild the :class:`~smartchem.category.Molecule` from the stored canonical graph (its
        ``__post_init__`` re-validates the graph itself)."""
        return Molecule(tuple(self.atoms), frozenset(Bond(i, j, order) for i, j, order in self.bonds),
                        self.charge, self.state)

    @classmethod
    def of_molecule(cls, molecule: "object") -> "StructuralSpecies":
        """The species record for a :class:`~smartchem.category.Molecule`: its STRUCTURE identity, its exact
        formula, AND its canonical molecular graph (the re-verifiable source of truth).  The graph is stored
        ``canonical()`` where the canonicaliser succeeds (presentation-invariant), else the graph as given (the
        ``asgiven:`` fallback the identity system uses for a graph it cannot canonicalise)."""
        if type(molecule) is not Molecule:
            raise TypeError("of_molecule needs a smartchem.category.Molecule")
        try:
            canon = molecule.canonical()
        except NotImplementedError:
            canon = molecule
        bonds = tuple(sorted((b.i, b.j, b.order) for b in canon.bonds))
        return cls(
            STRUCTURAL_SPECIES_SCHEMA,
            ChemicalIdentity.of_molecule(canon),
            Formula.of(canon.formula, canon.charge),
            tuple(canon.atoms),
            bonds,
            canon.charge,
            canon.state,
        )


# The closed witness->projection pairing, one entry per registered transform family:
#  * a capped-scission (valence-preserving whole-bond rewrite, reagent-mediated) forgets to a MediatedEdge;
#  * a bond-order edit (dehydrogenation, no reagent consumed -- CHEM-ALG-01) forgets to a plain DecompositionEdge.
# A new family registered through TransformProvider (TRANSFORM-PROVIDER-01) adds its pair here and a matching branch
# in _recompute_projection; the search, step-builder, and conditions gate need no change.
_WITNESS_PROJECTION = {
    "CAPPED_SCISSION": "MEDIATED_EDGE",
    "BOND_ORDER_EDIT": "DECOMPOSITION_EDGE",
}
# families whose transform consumes NO reagent (its LHS is just the parent) -- their candidate carries empty reagents.
_REAGENTLESS_WITNESS = frozenset({"BOND_ORDER_EDIT"})


@dataclass(frozen=True)
class StructuralCandidate(Digestible):
    """A first-class structural decomposition candidate carried INSIDE the IR (IR-STRUCT-01).

    Where a :class:`CandidateSummary` is a formula edge reduced to a digest and a string, a StructuralCandidate
    RETAINS the structure the transform acted on: the parent and product species at both layers, the primitive
    stoichiometry (species + multiplicity on each side), the scission EDIT witness (which specific
    valence-preserving bond rewrite, by its own digest and human equation), the producing provider's id and
    version, and the EXACT forgetful formula projection this structure refines.  W3 is unchanged: it is a
    ``FORMAL_CANDIDATE`` -- structure enumerates a conservation- and valence-valid rewrite within a grammar,
    never a claim the reaction runs or under what conditions.

    THE FORGETFUL SQUARE (IR-FORGET-01, section 7.3) is a FORMULA-level statement, enforced across three layers so
    no single unverified field is load-bearing (this discipline is the red-team fold that closed a vacuity where
    the square trusted the structure identity blindly):
      * the square proper -- :meth:`_recompute_projection` rebuilds the forgetful edge from the parent/reagent/
        product FORMULAS and refuses unless it equals the stored projection byte-for-byte (digest AND equation),
        independently of the live scission the producer forgot: ``forget(structural candidate) == its stored
        formula projection``, a construction invariant checked from stored fields, mismatch refused not coerced;
      * the structure identities are NOT trusted as bare digests -- each :class:`StructuralSpecies` carries its
        canonical molecular GRAPH and re-derives its own identity/formula, so a forged or isomer-swapped structure
        is refused THERE (the formula the square consumes is thus itself graph-backed, not a free field);
      * the parent is pinned to the IR target at the :class:`ChemicalCompilationIR` level (a wrong-subject
        artifact -- a decomposition of Y advertised under target X -- is refused).
    Exact edit-fidelity (which same-formula isomer each PRODUCT is, beyond its formula) is carried by the witness
    (``witness_digest`` / ``edit_equation``) as a provenance label; re-deriving it needs the graph-level scission
    replay that is the structure-rebuilding inverse's job (a named follow-on), so the square itself, being
    formula-level, does not distinguish a product's same-formula isomers.
    """

    schema_version: str
    direction: TransformDirection
    provider_id: str
    provider_version: str
    parent: StructuralSpecies
    reagents: tuple[tuple[StructuralSpecies, int], ...]
    products: tuple[tuple[StructuralSpecies, int], ...]
    witness_kind: str
    witness_digest: str
    edit_equation: str
    projection_kind: str
    projection_digest: str
    projection_equation: str
    readiness_tier: str
    identity_losses: tuple[IdentityLoss, ...]

    def __post_init__(self) -> None:
        if self.schema_version != STRUCTURAL_CANDIDATE_SCHEMA:
            raise ValueError(f"schema_version must be exactly {STRUCTURAL_CANDIDATE_SCHEMA!r}")
        if not isinstance(self.direction, TransformDirection):
            raise TypeError("direction must be a TransformDirection")
        for name in ("provider_id", "provider_version", "witness_digest", "edit_equation",
                     "projection_digest", "projection_equation"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")
        if type(self.parent) is not StructuralSpecies:
            raise TypeError("parent must be a StructuralSpecies")
        if self.witness_kind not in _WITNESS_PROJECTION:
            raise ValueError(f"witness_kind must be one of {tuple(_WITNESS_PROJECTION)}, not {self.witness_kind!r}")
        # reagent stoichiometry is FAMILY-specific: a reagent-consuming family (capped scission) consumes >= 1
        # reagent; a reagentless family (bond-order edit) carries none.  Products are always >= 1 distinct species.
        # The stoich tuples are canonical (species-digest-sorted, one entry per distinct species + its multiplicity).
        reagentless = self.witness_kind in _REAGENTLESS_WITNESS
        self._check_stoich("reagents", self.reagents, allow_empty=reagentless)
        if reagentless and self.reagents:
            raise ValueError(f"a {self.witness_kind} consumes no reagent; its reagents must be empty")
        self._check_stoich("products", self.products, allow_empty=False)
        expected_projection = _WITNESS_PROJECTION[self.witness_kind]
        if self.projection_kind != expected_projection:
            raise ValueError(
                f"projection_kind for a {self.witness_kind} witness must be {expected_projection!r}, "
                f"not {self.projection_kind!r}"
            )
        if self.readiness_tier != "FORMAL_CANDIDATE":
            raise ValueError(
                "a structural candidate is a FORMAL_CANDIDATE (W3: structure enumerates a valence-valid rewrite, "
                "it never claims the reaction runs)"
            )
        if type(self.identity_losses) is not tuple or any(type(x) is not IdentityLoss for x in self.identity_losses):
            raise TypeError("identity_losses must be a tuple of IdentityLoss records")
        loss_digests = [x.digest for x in self.identity_losses]
        if loss_digests != sorted(loss_digests):
            raise ValueError("identity_losses must be in canonical (digest-sorted) order; display order is not identity")
        if len(set(loss_digests)) != len(loss_digests):
            raise ValueError("identity_losses must be distinct by digest")
        # THE FORGETFUL SQUARE: rebuild the forgetful edge from the stored species and demand it equal the stored
        # projection -- byte-for-byte (its digest AND its human equation).  A mismatch is refused, not coerced.
        try:
            edge = self._recompute_projection()
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"the stored structural species do not forget to a valid formula edge: {exc}"
            ) from exc
        if edge.digest != self.projection_digest or edge.equation() != self.projection_equation:
            raise ValueError(
                "the stored formula projection is not the forget of the stored structure (section-7.3 commuting "
                "square broken: forget(structure) != stored projection); a mismatch is refused, not coerced"
            )

    @staticmethod
    def _check_stoich(name: str, pairs: "object", *, allow_empty: bool = False) -> None:
        if type(pairs) is not tuple:
            raise TypeError(f"{name} must be a tuple of (StructuralSpecies, multiplicity) pairs")
        if not allow_empty and not pairs:
            raise ValueError(f"{name} must be a non-empty tuple of (StructuralSpecies, multiplicity) pairs")
        digests: list[str] = []
        for pair in pairs:
            if type(pair) is not tuple or len(pair) != 2:
                raise TypeError(f"each {name} entry must be a (StructuralSpecies, multiplicity) pair")
            species, mult = pair
            if type(species) is not StructuralSpecies:
                raise TypeError(f"each {name} species must be a StructuralSpecies")
            if type(mult) is not int or mult < 1:
                raise ValueError(f"each {name} multiplicity must be an int >= 1")
            digests.append(species.digest)
        if digests != sorted(digests):
            raise ValueError(f"{name} must be in canonical (species-digest-sorted) order; display order is not identity")
        if len(set(digests)) != len(digests):
            raise ValueError(f"a {name} species appears twice; merge its multiplicity")

    def _recompute_projection(self) -> "MediatedEdge | DecompositionEdge":
        """Independently rebuild the forgetful composition edge from the STORED species formulas.

        Mirrors each family's ``forget`` verbatim -- the element-bucket merge (a single-element product/reagent
        collapses to its unit bucket carrying the atom count as multiplicity) and the SAME canonical sort -- so an
        HONEST candidate's recompute is byte-identical to what the producer forgot, and any drift makes the producer
        fail its own construction (and the tests catch it).  It is the certificate the forgetful-square check
        compares the stored projection against:
          * CAPPED_SCISSION -> a reagent-mediated MediatedEdge (mirrors CappedScission.forget);
          * BOND_ORDER_EDIT -> a reagentless DecompositionEdge (mirrors BondOrderEdit.forget / ScissionEdge.forget).
        """
        def _bucket_merge(pairs, sort_key) -> tuple[tuple[Formula, int], ...]:
            counts: dict[Formula, int] = {}
            for species, mult in pairs:
                f = species.formula
                if f.is_element:
                    (symbol, count), = f.counts
                    bucket = Formula.bucket(symbol)
                    counts[bucket] = counts.get(bucket, 0) + count * mult
                else:
                    counts[f] = counts.get(f, 0) + mult
            return tuple(sorted(counts.items(), key=sort_key))

        if self.witness_kind == "CAPPED_SCISSION":
            return MediatedEdge(
                self.parent.formula,
                1,
                _bucket_merge(self.reagents, lambda pm: ((pm[0].counts, pm[0].charge), pm[1])),
                _bucket_merge(self.products, lambda pm: ((pm[0].counts, pm[0].charge), pm[1])),
            )
        if self.witness_kind == "BOND_ORDER_EDIT":
            return DecompositionEdge(
                self.parent.formula, 1, _bucket_merge(self.products, lambda pm: (_fkey(pm[0]), pm[1]))
            )
        raise ValueError(f"no forgetful projection defined for witness_kind {self.witness_kind!r}")

    @classmethod
    def from_transform(
        cls,
        transform: "object",
        *,
        witness_kind: str = "CAPPED_SCISSION",
        provider_id: str = "capped-scission-mediated",
        provider_version: str = "v1",
        identity_losses: "tuple[IdentityLoss, ...]" = (),
    ) -> "StructuralCandidate":
        """Build the structural candidate for ANY structural transform (TRANSFORM-PROVIDER-01 / CHEM-ALG-01).

        Family-agnostic: it reads the transform's uniform interface (``reactant`` / ``reagents`` / ``products`` /
        ``forget()`` / ``digest`` / ``equation()``) and the family's ``witness_kind`` (from the producing
        provider), pairs the projection kind via ``_WITNESS_PROJECTION``, and carries the EXACT forgetful
        projection (``transform.forget()`` -- a mediated edge for a capped scission, a decomposition edge for a
        bond-order edit).  The candidate re-checks that projection against a recompute from its own stored species
        in ``__post_init__``, so this producer path is self-verifying: a mapping error fails construction at once.
        """
        def _group(mols: "tuple[object, ...]") -> tuple[tuple[StructuralSpecies, int], ...]:
            by_digest: dict[str, list] = {}
            for m in mols:
                species = StructuralSpecies.of_molecule(m)
                slot = by_digest.setdefault(species.structure.identity_digest, [species, 0])
                slot[1] += 1
            return tuple(
                sorted(((slot[0], slot[1]) for slot in by_digest.values()), key=lambda pm: pm[0].digest)
            )

        if witness_kind not in _WITNESS_PROJECTION:
            raise ValueError(f"unknown witness_kind {witness_kind!r}; known: {tuple(_WITNESS_PROJECTION)}")
        projection = transform.forget()
        return cls(
            STRUCTURAL_CANDIDATE_SCHEMA,
            TransformDirection.DECOMPOSE,
            provider_id,
            provider_version,
            StructuralSpecies.of_molecule(transform.reactant),
            _group(transform.reagents),
            _group(transform.products),
            witness_kind,
            transform.digest,
            transform.equation(),
            _WITNESS_PROJECTION[witness_kind],
            projection.digest,
            projection.equation(),
            "FORMAL_CANDIDATE",
            tuple(sorted(identity_losses, key=lambda loss: loss.digest)),
        )

    @classmethod
    def from_capped_scission(
        cls,
        edge: "object",
        *,
        provider_id: str = "capped-scission-mediated",
        provider_version: str = "v1",
        identity_losses: "tuple[IdentityLoss, ...]" = (),
    ) -> "StructuralCandidate":
        """The capped-scission-named entry to :meth:`from_transform` (kept for callers naming the family)."""
        return cls.from_transform(
            edge, witness_kind="CAPPED_SCISSION", provider_id=provider_id,
            provider_version=provider_version, identity_losses=identity_losses,
        )


def _receipt_first(receipt: "object", *names: str) -> "object | None":
    """The first attribute among ``names`` the receipt actually has -- the bridge for the section-8.1 fields the
    three receipts name differently (``cut_budget_per_expansion`` vs ``budget``; ``result_limit`` vs
    ``max_edges``; ``results_returned`` vs ``edges_emitted``)."""
    for name in names:
        if hasattr(receipt, name):
            return getattr(receipt, name)
    return None


@dataclass(frozen=True)
class Section81ReceiptView(Digestible):
    """The full section 8.1 ``SearchReceipt`` the standard mandates, projected off ANY of the three engine
    receipts (route / DAG / formula) into ONE canonical shape carried inside the IR (IR-CHEM-01).

    Section 8.1 requires every search to return a receipt with the ~20 counters below, and "counters that are not
    yet available MUST be null/UNKNOWN, not zero".  The three engine receipts already MEASURE these, but the IR
    used to carry only their DIGEST -- a fingerprint a consumer cannot read.  This view carries the counters
    THEMSELVES, so a transported IR exposes nodes_visited, transforms_considered, the rejection histogram, the
    enumeration-complete flags and the rest, not just a hash of them.

    It is a lossy PROJECTION of the native receipt (it drops engine-private fields the standard does not ask for),
    so it cannot be cross-checked against the native receipt's own digest on deserialize.  Instead its
    ``__post_init__`` re-validates its OWN internal consistency -- the section-8.1 counter invariants and the
    status/standard_status agreement -- exactly as the engine receipts do, so a tampered payload is refused on
    read rather than trusted.  As a :class:`Digestible` field of the IR it is covered by the IR's own digest.

    Per-receipt bridging (never a fabricated value): ``max_depth`` is ``None`` for the formula descent (it has no
    depth bound); ``candidate_limit`` is ``None`` on every current receipt (no engine stops on a distinct
    emitted-candidate cap); ``candidates_emitted`` is ``None`` for the formula descent (it does not measure a
    separate pre-dedup emit count); ``stop_reason`` is the formula receipt's own text, or the section-8.2 status
    for a truncated route/DAG search (which name the stop via their flags, not a text field), or "" when complete.
    """

    schema_version: str
    search_kind: str
    status: str                      # SearchStatus.value (native completeness enum)
    standard_status: str             # the section 8.2 terminal-status name
    cut_budget_scope: str
    target_identity_digest: "str | None"
    terminal_policy_digest: "str | None"
    transform_registry_digest: "str | None"
    max_depth: "int | None"
    cut_budget: "int | None"
    candidate_limit: "int | None"
    result_limit: "int | None"
    nodes_visited: "int | None"
    transforms_considered: "int | None"
    candidates_emitted: "int | None"
    results_returned: "int | None"
    candidates_rejected_by_reason: tuple[tuple[str, int], ...]
    cut_enumeration_complete: bool
    candidate_enumeration_complete: bool
    result_limit_saturated: bool
    stop_reason: str

    @classmethod
    def from_receipt(cls, receipt: "object") -> "Section81ReceiptView":
        """Project a route / DAG / formula search receipt onto the canonical section-8.1 view (never fabricating a
        counter a receipt does not measure -- an absent field maps to ``None``, per section 8.1's "null, not zero")."""
        stop_reason = _receipt_first(receipt, "stop_reason")
        if stop_reason is None:  # route/DAG name the stop via their flags, not a text field
            stop_reason = "" if receipt.complete_within_bounds else receipt.standard_status
        return cls(
            SEARCH_RECEIPT_VIEW_SCHEMA,
            receipt.search_kind,
            receipt.status.value,
            receipt.standard_status,
            receipt.cut_budget_scope,
            receipt.target_identity_digest,
            receipt.terminal_policy_digest,
            receipt.transform_registry_digest,
            _receipt_first(receipt, "max_depth"),
            _receipt_first(receipt, "cut_budget_per_expansion", "budget"),
            None,  # candidate_limit: no engine stops on a distinct emitted-candidate cap (section 8.1 UNKNOWN)
            _receipt_first(receipt, "result_limit", "max_edges"),
            receipt.nodes_visited,
            receipt.transforms_considered,
            _receipt_first(receipt, "candidates_emitted"),
            _receipt_first(receipt, "results_returned", "edges_emitted"),
            receipt.candidates_rejected_by_reason,
            receipt.cut_enumeration_complete,
            receipt.candidate_enumeration_complete,
            receipt.result_limit_saturated,
            stop_reason,
        )

    def __post_init__(self) -> None:
        if self.schema_version != SEARCH_RECEIPT_VIEW_SCHEMA:
            raise ValueError(f"schema_version must be exactly {SEARCH_RECEIPT_VIEW_SCHEMA!r}")
        if self.search_kind not in _KNOWN_SEARCH_KINDS:
            raise ValueError(f"search_kind must be one of {_KNOWN_SEARCH_KINDS}, not {self.search_kind!r}")
        # native status must be a real SearchStatus, and standard_status a real section-8.2 name that AGREES with
        # it -- for a single-limit member exactly its standard_name; for PARTIAL_MULTIPLE_LIMITS (no single 8.2
        # name) a resolvable primary.  A tampered payload whose standard_status contradicts its status is refused.
        try:
            native = SearchStatus(self.status)
        except ValueError as exc:
            raise ValueError(f"status must be a SearchStatus value, got {self.status!r}") from exc
        if self.standard_status not in STANDARD_8_2_STATUSES:
            raise ValueError(f"standard_status must be one of the section 8.2 statuses {STANDARD_8_2_STATUSES}")
        native_8_2 = native.standard_name
        if native_8_2 is not None:
            if self.standard_status != native_8_2:
                raise ValueError(
                    f"standard_status {self.standard_status!r} must equal {native_8_2!r} for {self.status}"
                )
        elif self.standard_status not in PRIMARY_RESOLVABLE_8_2_STATUSES:
            raise ValueError(
                f"a {self.status} view must resolve to a primary in {sorted(PRIMARY_RESOLVABLE_8_2_STATUSES)}, "
                f"not {self.standard_status!r}"
            )
        if self.cut_budget_scope not in ("PER_NODE", "GLOBAL"):
            raise ValueError("cut_budget_scope must be 'PER_NODE' or 'GLOBAL'")
        for name in ("target_identity_digest", "terminal_policy_digest", "transform_registry_digest", "stop_reason"):
            value = getattr(self, name)
            if name == "stop_reason":
                if not isinstance(value, str):
                    raise TypeError("stop_reason must be a string ('' when complete)")
            elif value is not None and (not isinstance(value, str) or not value):
                raise ValueError(f"{name} must be None (UNKNOWN) or a non-empty string")
        for name in ("max_depth", "cut_budget", "candidate_limit", "result_limit", "nodes_visited",
                     "transforms_considered", "candidates_emitted", "results_returned"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} must be None (UNKNOWN) or a non-negative integer")
        if (self.candidates_emitted is not None and self.results_returned is not None
                and self.candidates_emitted < self.results_returned):
            raise ValueError("candidates_emitted cannot be fewer than results_returned")
        # The section-8.1 "honest null" bridging fields are enforced ON READ, not just at projection time (red-team
        # fold): candidate_limit has no engine source anywhere, so it is null on EVERY receipt; and the formula
        # descent has no depth bound and measures no separate pre-dedup emit count, so a FORMULA view's max_depth
        # and candidates_emitted are null.  A tampered payload fabricating any of these is refused.
        if self.candidate_limit is not None:
            raise ValueError("candidate_limit must be None -- no search stops on a distinct emitted-candidate cap")
        if self.search_kind == "FORMULA_DECOMPOSITION":
            if self.max_depth is not None:
                raise ValueError("a FORMULA_DECOMPOSITION view has no depth bound; max_depth must be None")
            if self.candidates_emitted is not None:
                raise ValueError("a FORMULA_DECOMPOSITION view measures no candidates_emitted; it must be None")
            # the native formula invariant (transforms_considered >= edges_emitted): a distinct decomposition edge
            # needs >=1 admissible transform, and edges_emitted is projected to results_returned.  candidates_emitted
            # is None for a formula view, so the generic candidates_emitted>=results_returned check above is vacuous
            # here -- re-impose the pre-dedup>=distinct invariant on transforms_considered, exactly as the receipt does.
            if (self.transforms_considered is not None and self.results_returned is not None
                    and self.transforms_considered < self.results_returned):
                raise ValueError(
                    "a FORMULA_DECOMPOSITION view's transforms_considered cannot be fewer than results_returned "
                    "(each distinct edge needs >=1 transform application)"
                )
        for name in ("cut_enumeration_complete", "candidate_enumeration_complete", "result_limit_saturated"):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be bool")
        # completeness coherence: a search complete within its declared space cannot also report the result cap
        # saturated, and a COMPLETE native status must carry all three flags consistent with completeness.
        if native is SearchStatus.COMPLETE_WITHIN_BOUNDS:
            if self.result_limit_saturated or not self.cut_enumeration_complete or not self.candidate_enumeration_complete:
                raise ValueError("a COMPLETE_WITHIN_BOUNDS view cannot report a truncating limit")
            if self.stop_reason:
                raise ValueError("a complete search view carries no stop reason")
        _validate_rejection_histogram(self.candidates_rejected_by_reason)


def _validate_rejection_histogram(rejected: "object") -> None:
    """The shared section-8.1 invariant on ``candidates_rejected_by_reason``: a tuple of ``(reason, positive
    count)`` pairs, sorted by reason, distinct -- the same shape the engine receipts enforce at the source."""
    if type(rejected) is not tuple:
        raise TypeError("candidates_rejected_by_reason must be a tuple of (reason, count) pairs")
    seen: set[str] = set()
    prev: "str | None" = None
    for pair in rejected:
        if type(pair) is not tuple or len(pair) != 2:
            raise TypeError("each candidates_rejected_by_reason entry must be a (reason, count) pair")
        reason, count = pair
        if not isinstance(reason, str) or not reason:
            raise ValueError("a rejection reason must be a non-empty string")
        if type(count) is not int or count <= 0:
            raise ValueError(f"rejection count for {reason!r} must be a positive int")
        if reason in seen:
            raise ValueError(f"rejection reason {reason!r} appears twice; reasons must be distinct")
        if prev is not None and reason < prev:
            raise ValueError("candidates_rejected_by_reason must be sorted by reason (canonical order)")
        seen.add(reason)
        prev = reason


@dataclass(frozen=True)
class ChemicalCompilationIR(Digestible):
    """The versioned shared artifact both compiler directions consume or emit (standard section 4.1).

    DEFINING PROPERTY: the value's :attr:`digest` changes when any SEMANTIC input changes -- the target identity,
    the terminal policy, the transform-registry (grammar) version, a search bound (carried in
    :attr:`request_digest`), the search status, the candidate set, or the diagnostics -- and NEVER for a
    display-only or ordering difference.  ``request_digest`` identifies the REQUEST (target + terminal policy +
    transform registry + bounds) and is stable across re-runs; the full value digest additionally covers the
    result (candidates, status, diagnostics).  ``transform_registry_digest`` names WHICH grammar generated the
    candidates -- the identity section 8.4's "all pathways generated by transform registry <digest>" refers to.
    """

    schema_version: str
    tool_version: str
    operation: CompilationOperation
    target: ChemicalIdentity
    request_digest: str
    identity_losses: tuple[IdentityLoss, ...]
    terminal_policy_digest: str
    transform_registry_digest: str
    search_status: SearchStatus
    # the SAME completeness fact as search_status, named in the standard's section 8.2 terminal-status vocabulary
    # (COMPLETE_WITHIN_DECLARED_SPACE / INCOMPLETE_* / ...).  Carried as a stored field, not derived on the fly,
    # because the engine's PARTIAL_MULTIPLE_LIMITS has no single section 8.2 name -- it must be resolved to one
    # primary from the receipt's per-limit flags at construction, where the receipt is live (the IR is not).
    standard_status: str
    # the FULL section 8.1 SearchReceipt (the ~20 mandated counters), not just its digest (IR-CHEM-01): a
    # consumer reading the transported IR sees nodes_visited/transforms_considered/the rejection histogram/the
    # enumeration-complete flags themselves.  As a Digestible field it is covered by the IR's own digest.
    search_receipt: Section81ReceiptView
    candidates: tuple[CandidateSummary, ...]
    diagnostics: tuple[str, ...]
    # IR-STRUCT-01 (v1alpha5): first-class typed structural decomposition candidates ride INSIDE the IR.  A
    # structural DECOMPILE (decompile_structure_to_ir) populates these; the formula/route/DAG producers leave them
    # empty.  Digest-sorted/distinct like every other candidate tuple and covered by the IR's own digest.  Given a
    # default so the formula/route/DAG producers' positional constructions are unchanged by the new field.
    structural_candidates: tuple[StructuralCandidate, ...] = ()

    def __post_init__(self) -> None:
        if self.schema_version != CHEMICAL_COMPILATION_IR_SCHEMA:
            raise ValueError(f"schema_version must be exactly {CHEMICAL_COMPILATION_IR_SCHEMA!r}")
        if not isinstance(self.tool_version, str) or not self.tool_version:
            raise ValueError("tool_version must be a non-empty string")
        if not isinstance(self.operation, CompilationOperation):
            raise TypeError("operation must be a CompilationOperation")
        if type(self.target) is not ChemicalIdentity:
            raise TypeError("target must be a ChemicalIdentity")
        if not isinstance(self.search_status, SearchStatus):
            raise TypeError("search_status must be a SearchStatus")
        # standard_status must be a real section 8.2 name AND faithful to the native search_status: for a status
        # that maps 1:1 it must be exactly search_status.standard_name; for PARTIAL_MULTIPLE_LIMITS (no single 8.2
        # name) it must be one of the primaries that resolution can LEGALLY produce.  This forbids a section 8.2
        # status that contradicts the native one -- for a single-limit status exactly, and for PARTIAL_MULTIPLE_
        # LIMITS up to the primary CHOICE: the enum member alone cannot pin WHICH resolvable primary THIS receipt
        # implies (that is pinned upstream in SearchReceipt.standard_status, where the per-limit flags are live).
        # Every value it admits is INCOMPLETE_*, so a partial is never laundered toward complete either way; every
        # real producer passes receipt.standard_status, so the looseness is reachable only by a hand-built,
        # internally-inconsistent payload -- and the search_receipt view's own status/standard_status must match
        # this IR's (checked below), so such a payload is caught there too.
        if self.standard_status not in STANDARD_8_2_STATUSES:
            raise ValueError(f"standard_status must be one of the section 8.2 statuses {STANDARD_8_2_STATUSES}")
        _native_8_2 = self.search_status.standard_name
        if _native_8_2 is not None:
            if self.standard_status != _native_8_2:
                raise ValueError(
                    f"standard_status {self.standard_status!r} must equal search_status.standard_name "
                    f"{_native_8_2!r} for the single-limit status {self.search_status.value}"
                )
        elif self.standard_status not in PRIMARY_RESOLVABLE_8_2_STATUSES:
            raise ValueError(
                f"a {self.search_status.value} status must resolve to a primary stop reason in "
                f"{sorted(PRIMARY_RESOLVABLE_8_2_STATUSES)}, not {self.standard_status!r}"
            )
        for name in ("request_digest", "terminal_policy_digest", "transform_registry_digest"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")
        # the section 8.1 receipt view must be a real one, and it must describe the SAME search this IR does: its
        # native status and section-8.2 status must match the IR's own, AND its non-null identity digests (WHAT
        # was searched -- target, terminal policy, transform grammar) must equal the IR's own.  A hand-built payload
        # pairing a receipt view with a contradicting status OR a FOREIGN target/policy/grammar is refused -- the
        # two describe one search or neither is trusted (red-team fold: the digest agreement was documented but not
        # enforced, so a foreign-search receipt -- incl. a forged section-8.4 transform_registry_digest -- rode
        # inside the IR and passed deserialize_ir; now it is enforced, not merely asserted in the comment).
        if type(self.search_receipt) is not Section81ReceiptView:
            raise TypeError("search_receipt must be a Section81ReceiptView")
        if self.search_receipt.status != self.search_status.value:
            raise ValueError(
                f"search_receipt.status {self.search_receipt.status!r} must equal the IR search_status "
                f"{self.search_status.value!r} (they describe one search)"
            )
        if self.search_receipt.standard_status != self.standard_status:
            raise ValueError(
                f"search_receipt.standard_status {self.search_receipt.standard_status!r} must equal the IR "
                f"standard_status {self.standard_status!r}"
            )
        for _view_field, _ir_value in (
            ("target_identity_digest", self.target.identity_digest),
            ("terminal_policy_digest", self.terminal_policy_digest),
            ("transform_registry_digest", self.transform_registry_digest),
        ):
            _view_value = getattr(self.search_receipt, _view_field)
            if _view_value is not None and _view_value != _ir_value:
                raise ValueError(
                    f"search_receipt.{_view_field} {_view_value!r} must equal the IR's {_ir_value!r} -- the "
                    "receipt must describe the SAME search (target/terminal policy/transform grammar) as the IR"
                )
        if type(self.diagnostics) is not tuple or any(not isinstance(x, str) for x in self.diagnostics):
            raise TypeError("diagnostics must be a tuple of strings")
        # identity_losses are first-class typed section-5.3 records (IR-LOSS-01), carried in canonical
        # (digest-sorted, distinct) order so presentation order is never part of the IR identity -- the same
        # discipline the candidate tuple obeys.
        if type(self.identity_losses) is not tuple or any(
            type(x) is not IdentityLoss for x in self.identity_losses
        ):
            raise TypeError("identity_losses must be a tuple of IdentityLoss records")
        loss_digests = [x.digest for x in self.identity_losses]
        if loss_digests != sorted(loss_digests):
            raise ValueError("identity_losses must be in canonical (digest-sorted) order; display order is not identity")
        if len(set(loss_digests)) != len(loss_digests):
            raise ValueError("identity_losses must be distinct by digest")
        if type(self.candidates) is not tuple or any(type(c) is not CandidateSummary for c in self.candidates):
            raise TypeError("candidates must be a tuple of CandidateSummary values")
        # canonical order: candidates are sorted by their digest, so presentation order is not part of identity
        digests = [c.candidate_digest for c in self.candidates]
        if digests != sorted(digests):
            raise ValueError("candidates must be in canonical (digest-sorted) order; display order is not identity")
        if len(set(digests)) != len(digests):
            raise ValueError("candidates must be distinct by digest")
        # structural_candidates obey the same canonical/distinct discipline, and their presence is coherent only on
        # a STRUCTURE-layer target: a structural candidate carries structure-level claims (a specific isomer parent,
        # its scission), so a formula-layer IR carrying one would assert structure over a target known only at the
        # formula layer -- refused.
        if type(self.structural_candidates) is not tuple or any(
            type(s) is not StructuralCandidate for s in self.structural_candidates
        ):
            raise TypeError("structural_candidates must be a tuple of StructuralCandidate values")
        struct_digests = [s.digest for s in self.structural_candidates]
        if struct_digests != sorted(struct_digests):
            raise ValueError(
                "structural_candidates must be in canonical (digest-sorted) order; display order is not identity"
            )
        if len(set(struct_digests)) != len(struct_digests):
            raise ValueError("structural_candidates must be distinct by digest")
        if self.structural_candidates:
            # a structural candidate is a DECOMPOSE primitive keyed on a STRUCTURE-layer parent; it can only ride a
            # STRUCTURE-layer DECOMPILE of that exact target.  (red-team fold, two confirmed coherence holes:)
            #  * a formula-layer target would assert structure over a target known only at the formula layer;
            #  * a candidate whose parent is NOT the IR target is a wrong-subject artifact -- an IR advertising
            #    target X carrying a decomposition OF Y -- which defeats IR-STRUCT-01's whole point (retain the
            #    structure the transform acted on).  The honest producer always sets parent == target; enforce it.
            if self.target.layer is not IdentityLayer.STRUCTURE:
                raise ValueError(
                    "structural_candidates require a STRUCTURE-layer target (they carry structure-level claims); "
                    f"this IR's target is at the {self.target.layer.value} layer"
                )
            if self.operation is not CompilationOperation.DECOMPILE:
                raise ValueError(
                    "structural_candidates are DECOMPOSE primitives and ride only a DECOMPILE IR; "
                    f"this IR's operation is {self.operation.value}"
                )
            for _sc in self.structural_candidates:
                if _sc.parent.structure.identity_digest != self.target.identity_digest:
                    raise ValueError(
                        "every structural candidate's parent must be the IR target (a structural decompile OF this "
                        f"target); a candidate's parent is {_sc.parent.structure.identity_digest} but the target is "
                        f"{self.target.identity_digest} -- a wrong-subject artifact is refused"
                    )

    @property
    def complete_within_bounds(self) -> bool:
        return self.search_status is SearchStatus.COMPLETE_WITHIN_BOUNDS

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    @property
    def identity_loss_summaries(self) -> tuple[str, ...]:
        """The one-line ``summary()`` of each carried loss -- the human/JSON-agreement string form of the typed
        records (CLI-JSON-01).  Derived, never stored: the IR's identity is the typed records themselves."""
        return tuple(loss.summary() for loss in self.identity_losses)

    def render(self) -> str:
        structural = (
            f"  structural candidates: {len(self.structural_candidates)} (structure-preserving, forgetful "
            f"projection carried)\n"
            if self.structural_candidates
            else ""
        )
        return (
            f"CHEMICAL COMPILATION IR ({self.operation.value}, {self.schema_version}, tool {self.tool_version})\n"
            f"  target: {self.target.canonical_repr} [{self.target.layer.value}]\n"
            f"  search: {self.standard_status} (engine: {self.search_status.value}); "
            f"candidates: {self.candidate_count}\n"
            f"{structural}"
            f"  request digest: {self.request_digest}\n"
            f"  transform registry: {self.transform_registry_digest}\n"
            f"  losses: {len(self.identity_losses)}; diagnostics: {len(self.diagnostics)}\n"
            "  Scope: bounded-search bookkeeping (what was asked / searched / found), conservation only -- "
            "NOT a chemistry claim."
        )


def _tool_version() -> str:
    from . import __version__
    return __version__


def _structure_ident(molecule: "object") -> str:
    """The pipeline's presentation-invariant molecular identity: canonical digest, ``asgiven:`` for a graph the
    canonicaliser refuses (a symmetric ring).  Byte-for-byte the ``_ident`` used in routes/step/dag, so a
    structural IR keys on the SAME identity the search does."""
    from .category import Molecule
    if type(molecule) is not Molecule:
        raise TypeError("_structure_ident needs a smartchem.category.Molecule")
    try:
        return canonical_digest(molecule.canonical())
    except NotImplementedError:
        return "asgiven:" + canonical_digest(molecule)


def _terminal_policy_digest(inventory: tuple[Formula, ...]) -> str:
    """A canonical digest of the declared formula terminal policy: the match mode plus the canonical inventory.

    Formula decompile uses ``FORMULA_ONLY`` matching by construction (section 7).  The inventory is already
    canonicalized/deduplicated by :func:`~smartchem.decompiler.search_decomposition`, so this is order-invariant.
    """
    return canonical_digest(("terminal-policy", "FORMULA_ONLY") + tuple(inventory))


def decompile_to_ir(
    target: "str | dict[str, int] | Formula",
    inventory: "tuple[Formula, ...] | tuple[str, ...]" = (),
    *,
    max_multiplicity: int = 1,
    budget: int = 100_000,
    max_edges: int = 5_000,
    identity_losses: "tuple[IdentityLoss, ...]" = (),
    tool_version: str | None = None,
) -> ChemicalCompilationIR:
    """Emit a :class:`ChemicalCompilationIR` for the formula decomposition of ``target`` over ``inventory``.

    The first concrete producer of the shared IR (IR-CHEM-01): it runs :func:`~smartchem.decompiler.search_decomposition`
    and packages the target identity, the terminal policy, the search status/receipt, and the conservation-valid
    decomposition edges as canonical, digest-identified candidates.  The IR's own digest is presentation-invariant
    and semantic-input-sensitive (see the class docstring).
    """
    result = search_decomposition(
        target, inventory, max_multiplicity=max_multiplicity, budget=budget, max_edges=max_edges
    )
    graph: DecompositionGraph = result.graph
    receipt = result.receipt
    target_id = ChemicalIdentity.of_formula(graph.target)
    terminal_digest = _terminal_policy_digest(graph.inventory)
    # candidates in canonical (digest-sorted) order -- display order is never part of the IR identity
    candidates = tuple(
        sorted(
            (
                CandidateSummary(
                    CANDIDATE_SUMMARY_SCHEMA, "FORMULA_EDGE", edge.digest, edge.equation(), "FORMAL_CANDIDATE"
                )
                for edge in graph.edges
            ),
            key=lambda c: c.candidate_digest,
        )
    )
    registry_digest = _transform_registry_digest("formula-decomposition")
    # the request digest covers exactly the semantic REQUEST inputs, so changing a bound (or the transform
    # registry version) changes the IR digest even when the returned candidate set happens to be identical.
    request_digest = canonical_digest(
        (
            "decompile-request",
            target_id.identity_digest,
            terminal_digest,
            ("transform-registry", registry_digest),
            ("bounds", max_multiplicity, budget, max_edges),
        )
    )
    diagnostics = () if receipt.complete_within_bounds else (receipt.stop_reason,)
    return ChemicalCompilationIR(
        CHEMICAL_COMPILATION_IR_SCHEMA,
        tool_version or _tool_version(),
        CompilationOperation.DECOMPILE,
        target_id,
        request_digest,
        # A formula decompile forgets topology; when the target REACHED this producer as a structure (a SMILES the
        # caller reduced), that reduction is a first-class typed section-5.3 IdentityLoss (IR-LOSS-01) the caller
        # passes in here so the machine response carries the structured record, not a string.  Digest-sorted for
        # canonical (presentation-invariant) IR identity.
        tuple(sorted(identity_losses, key=lambda loss: loss.digest)),
        terminal_digest,
        registry_digest,
        receipt.status,
        receipt.standard_status,
        Section81ReceiptView.from_receipt(receipt),
        candidates,
        diagnostics,
    )
    # -- decompile_to_ir sentinel above; the recompile producer is below ------------------------------------


def _recompile_terminal_policy_digest(
    reagents: tuple, available: tuple, commodities: tuple
) -> str:
    """A canonical digest of the structural terminal policy: match mode plus the SET of terminal identities.

    Section 7: a structural search terminates a branch at any node whose canonical STRUCTURE identity is on
    hand.  :func:`~smartchem.experiment.routes.search_routes`/``search_dags`` put every one of
    ``available``/``reagents``/``commodities`` into that on-hand set, so the *terminal set* is their union,
    keyed by :func:`_structure_ident` (never by formula -- a same-formula isomer does not terminate).  A
    frozenset makes the digest order-invariant, so permuting any inventory list leaves the policy unchanged.
    """
    terminals = frozenset(_structure_ident(m) for m in (*available, *reagents, *commodities))
    return canonical_digest(("terminal-policy", "STRUCTURE", terminals))


def recompile_to_ir(
    target: "object",
    *,
    reagents: tuple,
    available: tuple = (),
    commodities: tuple = (),
    max_depth: int = 2,
    max_results: int = 100,
    cut_budget: int = 20_000,
    mode: str = "routes",
    identity_losses: "tuple[IdentityLoss, ...]" = (),
    tool_version: str | None = None,
    search_result: "object | None" = None,
) -> ChemicalCompilationIR:
    """Emit a :class:`ChemicalCompilationIR` for the *structural* recompilation (synthesis) of ``target``.

    The second concrete producer of the shared IR (advancing IR-CHEM-01): where :func:`decompile_to_ir` packages
    the formula decomposition, this packages the recompiler's route or DAG search
    (:func:`~smartchem.experiment.routes.search_routes` when ``mode='routes'``,
    :func:`~smartchem.experiment.routes.search_dags` when ``mode='dags'``) as canonical, digest-identified
    ``ROUTE``/``DAG`` candidates over a STRUCTURE-layer target identity.

    The IR's digest keeps the section 4.1 discipline: it is presentation-invariant (permuting ``reagents`` or
    ``available`` does not change it -- the terminal policy is a frozenset and candidates are digest-sorted) and
    semantic-input-sensitive (a search-bound change alters ``request_digest``, hence the value digest, even when
    the returned candidate set is byte-for-byte identical).  ``request_digest`` additionally distinguishes the
    reagent HELPER pool from the plain terminal stock, because moving a molecule from ``reagents`` (a pool the
    cleavage may consume) to ``available`` (mere on-hand stock) genuinely changes which candidates exist.

    W3 unchanged: every candidate is a ``FORMAL_CANDIDATE`` -- a conservation-valid assembly within the current
    capped-scission grammar and the declared search bounds, never a claim that the synthesis works.

    ``search_result`` (CLI-CAN-02 brick 2): a precomputed :class:`~smartchem.experiment.routes.RouteSearchResult`
    (mode ``'routes'``) or ``DAGSearchResult`` (mode ``'dags'``) to package INSTEAD of searching again.  The
    recompiler service searches ONCE and reuses the very same result both here (to package the IR) and to rank the
    routes against the section-11 bench box -- so the IR's candidates and the ranked dossiers describe the identical
    search.  It MUST have been produced with the same ``target``/terminal policy/bounds; a mismatched result would
    silently package a foreign search, so the mode/type is validated but the search identity is the caller's to keep.
    """
    from .category import Molecule
    if type(target) is not Molecule:
        raise TypeError("recompile_to_ir target must be a smartchem.category.Molecule")
    if mode not in ("routes", "dags"):
        raise ValueError("mode must be 'routes' or 'dags'")
    from .experiment.routes import search_dags, search_routes

    if search_result is not None:
        needed = "routes" if mode == "routes" else "dags"
        if not hasattr(search_result, needed):
            raise TypeError(f"a precomputed search_result for mode={mode!r} must expose .{needed}")

    if mode == "routes":
        result = search_result if search_result is not None else search_routes(
            target, reagents=reagents, available=available, commodities=commodities,
            max_depth=max_depth, max_routes=max_results, cut_budget=cut_budget,
        )
        candidate_kind = "ROUTE"
        candidate_objs: tuple = result.routes
        def _equation(obj) -> str:
            return " ; ".join(obj.equation_lines())
    else:
        result = search_result if search_result is not None else search_dags(
            target, reagents=reagents, available=available, commodities=commodities,
            max_depth=max_depth, max_dags=max_results, cut_budget=cut_budget,
        )
        candidate_kind = "DAG"
        candidate_objs = result.dags
        def _equation(obj) -> str:
            return " ; ".join(s.equation() for s in obj.topological_order())

    receipt = result.receipt
    target_id = ChemicalIdentity.of_molecule(target)
    terminal_digest = _recompile_terminal_policy_digest(reagents, available, commodities)
    candidates = tuple(
        sorted(
            (
                CandidateSummary(
                    CANDIDATE_SUMMARY_SCHEMA, candidate_kind, obj.digest,
                    _equation(obj) or repr(obj), "FORMAL_CANDIDATE",
                )
                for obj in candidate_objs
            ),
            key=lambda c: c.candidate_digest,
        )
    )
    registry_digest = _transform_registry_digest(
        "capped-scission-linear" if mode == "routes" else "capped-scission-convergent"
    )
    # request_digest identifies the REQUEST: target + terminal set + the reagent HELPER pool (distinct from
    # plain stock) + the transform registry + mode + bounds -- so a bound change (or a reagent-vs-available move,
    # or a transform-registry version bump) changes the IR digest even when the candidate set is identical.
    reagent_pool = frozenset(_structure_ident(m) for m in reagents)
    request_digest = canonical_digest(
        (
            "recompile-request",
            target_id.identity_digest,
            terminal_digest,
            ("reagent-pool", reagent_pool),
            ("transform-registry", registry_digest),
            ("mode", mode),
            ("bounds", max_depth, max_results, cut_budget),
        )
    )
    if result.target_in_terminal_stock:
        diagnostics: tuple[str, ...] = (
            "target is already present in the active terminal stock; no synthesis is required (section 7)",
        )
    elif not receipt.complete_within_bounds:
        diagnostics = (f"search incomplete within bounds: {receipt.status.value}",)
    elif not candidates:
        # complete-within-bounds AND zero candidates AND not in stock: NO limit fired, so this mode's search
        # EXHAUSTED its grammar at these bounds and found no conservation-valid assembly terminating in stock.
        # This MUST be said precisely -- a silent "complete + empty" is indistinguishable from a truncated
        # search that gave up (the laundering SRCH-DEPTH-01 outlawed one layer down).  But the claim is scoped
        # EXACTLY to what the receipt proves: exhaustion of THIS mode's grammar at THESE bounds -- NOT a
        # registry-wide "no route exists anywhere" (a different mode or higher bounds is not excluded; the same
        # request under mode='dags' can still be truncated).  Overclaiming that scope was a red-team finding.
        diagnostics = (
            f"no route to the target from the declared terminals exists within the '{mode}' search grammar at "
            f"the declared bounds (max_depth={max_depth}); the search was exhaustive there (no limit fired), but "
            f"that is exhaustion of THIS grammar/mode at THESE bounds -- not a proof that no route exists under a "
            f"different mode or higher bounds (section 8.3, no-route: exhaustive-within-bounds)",
        )
    else:
        diagnostics = ()
    return ChemicalCompilationIR(
        CHEMICAL_COMPILATION_IR_SCHEMA,
        tool_version or _tool_version(),
        CompilationOperation.RECOMPILE,
        target_id,
        request_digest,
        # identity_losses: the structure layer keeps constitution but drops finer features (stereo/isotope/local
        # charge).  A structural target parsed from a plain graph forgets nothing (()), but a SMILES target that
        # DECLARED those finer features carries the typed section-5.3 blockers here (ID-STEREO-01), digest-sorted.
        tuple(sorted(identity_losses, key=lambda loss: loss.digest)),
        terminal_digest,
        registry_digest,
        receipt.status,
        receipt.standard_status,
        Section81ReceiptView.from_receipt(receipt),
        candidates,
        diagnostics,
    )


def _structure_decompile_terminal_digest(reagents: tuple) -> str:
    """The structural-decompile 'terminal policy': the reagent TYPE set the capper may consume.

    A one-step capped-scission enumeration has no on-hand stock to terminate at (section 7's terminal set is a
    search concept); its one policy parameter is WHICH reagent types the capper may draw from.  A frozenset of the
    reagent structure identities makes the digest order-invariant (permuting the reagent list leaves it unchanged).
    """
    reagent_types = frozenset(_structure_ident(m) for m in reagents)
    return canonical_digest(("terminal-policy", "STRUCTURE_DECOMPOSE", reagent_types))


def _structure_decompose_receipt_view(
    *,
    complete: bool,
    results_returned: int,
    target_identity_digest: str,
    terminal_policy_digest: str,
    transform_registry_digest: str,
    cut_budget: int,
) -> Section81ReceiptView:
    """An honest section-8.1 receipt view for one capped-scission descent (``capped_scissions``).

    The descent returns only ``(edges, complete)``, so every counter it does not measure is UNKNOWN (``None``),
    per section 8.1's "null, not zero" -- nodes_visited, transforms_considered, candidates_emitted are null; only
    ``results_returned`` (the distinct emitted candidates) and the completeness flags are known.  ``complete`` is
    the capper's own flag (``False`` iff its budget was hit), which maps to COMPLETE_WITHIN_BOUNDS /
    PARTIAL_SEARCH_BUDGET -- never a fabricated exhaustion.
    """
    status = SearchStatus.COMPLETE_WITHIN_BOUNDS if complete else SearchStatus.PARTIAL_SEARCH_BUDGET
    return Section81ReceiptView(
        SEARCH_RECEIPT_VIEW_SCHEMA,
        "STRUCTURE_DECOMPOSITION",
        status.value,
        status.standard_name,
        "GLOBAL",                    # the capper's budget is a single global cut budget, not a per-node one
        target_identity_digest,
        terminal_policy_digest,
        transform_registry_digest,
        None,                        # max_depth: a one-step scission enumeration has no descent-depth bound
        cut_budget,
        None,                        # candidate_limit: no distinct-candidate cap anywhere (section 8.1 UNKNOWN)
        None,                        # result_limit: the capper has no result cap, only the cut budget
        None,                        # nodes_visited: not measured -> UNKNOWN
        None,                        # transforms_considered: not measured -> UNKNOWN
        None,                        # candidates_emitted: no separate pre-dedup emit count -> UNKNOWN
        results_returned,            # results_returned: the distinct capped scissions emitted
        (),                          # candidates_rejected_by_reason: not attributed by reason at this layer
        complete,                    # cut_enumeration_complete
        complete,                    # candidate_enumeration_complete
        False,                       # result_limit_saturated: no result cap to saturate
        "" if complete else status.standard_name,   # stop_reason ("" only when complete)
    )


def decompile_structure_to_ir(
    target: "object",
    *,
    reagents: tuple,
    registry: "TransformProviderRegistry" = DEFAULT_TRANSFORM_REGISTRY,
    budget: int = 50_000,
    identity_losses: "tuple[IdentityLoss, ...]" = (),
    tool_version: str | None = None,
) -> ChemicalCompilationIR:
    """Emit a STRUCTURE-layer DECOMPILE IR whose candidates are first-class :class:`StructuralCandidate` records.

    The structure-preserving decompile path (IR-STRUCT-01), now parameterized by a transform algebra
    (TRANSFORM-PROVIDER-01).  Where :func:`decompile_to_ir` reduces the target to a formula and emits formula edges
    (the sole shared artifact being a composition), this enumerates ``target``'s structural transforms through the
    typed :class:`~smartchem.transform_provider.TransformProviderRegistry` and packages each as a structural
    candidate that RETAINS the structure: parent/product STRUCTURE identities, primitive stoichiometry, the scission
    edit witness, the producing provider's id/version (from the registry), and the EXACT forgetful formula
    projection.  Each candidate re-checks that projection against a recompute from its own stored species (the
    section-7.3 commuting square), so this producer is self-verifying.  A wider algebra (a registry with more
    providers) enumerates more families with NO change to this producer -- the genericity seam.

    The IR digest keeps the section 4.1 discipline: presentation-invariant (permuting ``reagents`` does not change
    it -- the terminal policy is a frozenset and candidates are digest-sorted) and semantic-input-sensitive (a
    bound change or a registry change -- provider set / id / version / capability manifest -- alters
    ``request_digest``, hence the value digest, even when the candidate set is identical).  W3 unchanged: every
    candidate is a ``FORMAL_CANDIDATE`` -- a conservation- and valence-valid rewrite within the declared algebra
    and bounds, never a claim any synthesis works.
    """
    from .category import Molecule

    if type(target) is not Molecule:
        raise TypeError("decompile_structure_to_ir target must be a smartchem.category.Molecule")
    if type(reagents) is not tuple or not reagents or any(type(r) is not Molecule for r in reagents):
        raise TypeError("reagents must be a non-empty tuple of reagent-TYPE Molecules")

    enumerated, complete = registry.enumerate(target, reagents, budget=budget)
    losses_sorted = tuple(sorted(identity_losses, key=lambda loss: loss.digest))
    structural_candidates = tuple(
        sorted(
            (
                StructuralCandidate.from_transform(
                    et.transform,
                    witness_kind=et.witness_kind,
                    provider_id=et.provider_id,
                    provider_version=et.provider_version,
                    identity_losses=losses_sorted,
                )
                for et in enumerated
            ),
            key=lambda s: s.digest,
        )
    )
    target_id = ChemicalIdentity.of_molecule(target)
    terminal_digest = _structure_decompile_terminal_digest(reagents)
    # the IR names the PROVIDER REGISTRY (the whole transform algebra) that generated its candidates -- the section
    # 8.4 "all pathways generated by transform registry <digest>".  The registry digest already covers every
    # provider's id / version / capability manifest, so a provider set/version/manifest change (section 4.1's
    # "transform/evidence provider version") moves the IR digest even when the candidate set is identical.
    registry_digest = registry.digest
    reagent_pool = frozenset(_structure_ident(m) for m in reagents)
    request_digest = canonical_digest(
        (
            "structure-decompile-request",
            target_id.identity_digest,
            terminal_digest,
            ("reagent-pool", reagent_pool),
            ("transform-registry", registry_digest),
            ("bounds", budget),
        )
    )
    status = SearchStatus.COMPLETE_WITHIN_BOUNDS if complete else SearchStatus.PARTIAL_SEARCH_BUDGET
    receipt_view = _structure_decompose_receipt_view(
        complete=complete,
        results_returned=len(enumerated),
        target_identity_digest=target_id.identity_digest,
        terminal_policy_digest=terminal_digest,
        transform_registry_digest=registry_digest,
        cut_budget=budget,
    )
    if not complete:
        diagnostics: tuple[str, ...] = (
            f"structural decompile incomplete within bounds: {status.value} (cut budget {budget} hit); the "
            f"enumerated candidates are a partial sample, not an exhaustive set",
        )
    elif not structural_candidates:
        diagnostics = (
            f"no structural transform of the target exists over the declared reagent types within the algebra "
            f"(providers {list(registry.provider_ids)}) at the declared bounds; the enumeration was exhaustive "
            f"there (no budget fired), but that is exhaustion of THIS algebra at THESE bounds -- not a proof that "
            f"no transform exists under a wider algebra or higher bounds (section 8.3, no-route: "
            f"exhaustive-within-bounds)",
        )
    else:
        diagnostics = ()
    return ChemicalCompilationIR(
        CHEMICAL_COMPILATION_IR_SCHEMA,
        tool_version or _tool_version(),
        CompilationOperation.DECOMPILE,
        target_id,
        request_digest,
        losses_sorted,
        terminal_digest,
        registry_digest,
        status,
        status.standard_name,
        receipt_view,
        (),   # no formula-edge CandidateSummary candidates: the structural candidates carry the decompile payload
        diagnostics,
        structural_candidates,
    )


# -- serialization (advancing IR-CHEM-01: the IR is a transportable artifact, not just an in-memory value) --
#
# The one property that must survive the round trip is IDENTITY: deserialize(serialize(ir)).digest == ir.digest.
# So the payload captures exactly the semantic fields (enums by their .value, nested records as nested dicts,
# tuples as lists) and from_payload rebuilds the SAME frozen dataclasses -- which re-run their __post_init__
# invariants, so a tampered payload (unsorted/duplicate candidates, an unknown enum, a bad schema) is REFUSED on
# read rather than silently trusted. json is written sort_keys=True, so the serialized string is canonical too.


def _receipt_view_to_payload(view: Section81ReceiptView) -> dict:
    """A JSON-compatible dict of the full section 8.1 receipt view (nulls preserved, histogram as [reason, count])."""
    return {
        "schema_version": view.schema_version,
        "search_kind": view.search_kind,
        "status": view.status,
        "standard_status": view.standard_status,
        "cut_budget_scope": view.cut_budget_scope,
        "target_identity_digest": view.target_identity_digest,
        "terminal_policy_digest": view.terminal_policy_digest,
        "transform_registry_digest": view.transform_registry_digest,
        "max_depth": view.max_depth,
        "cut_budget": view.cut_budget,
        "candidate_limit": view.candidate_limit,
        "result_limit": view.result_limit,
        "nodes_visited": view.nodes_visited,
        "transforms_considered": view.transforms_considered,
        "candidates_emitted": view.candidates_emitted,
        "results_returned": view.results_returned,
        "candidates_rejected_by_reason": [[r, c] for r, c in view.candidates_rejected_by_reason],
        "cut_enumeration_complete": view.cut_enumeration_complete,
        "candidate_enumeration_complete": view.candidate_enumeration_complete,
        "result_limit_saturated": view.result_limit_saturated,
        "stop_reason": view.stop_reason,
    }


def _receipt_view_from_payload(p: dict) -> Section81ReceiptView:
    """Rebuild a :class:`Section81ReceiptView` from its payload, re-running its __post_init__ (a tampered view --
    a status that contradicts its standard_status, a negative counter, an unsorted histogram -- is refused here)."""
    return Section81ReceiptView(
        p["schema_version"], p["search_kind"], p["status"], p["standard_status"], p["cut_budget_scope"],
        p["target_identity_digest"], p["terminal_policy_digest"], p["transform_registry_digest"],
        p["max_depth"], p["cut_budget"], p["candidate_limit"], p["result_limit"], p["nodes_visited"],
        p["transforms_considered"], p["candidates_emitted"], p["results_returned"],
        tuple((r, c) for r, c in p["candidates_rejected_by_reason"]),
        p["cut_enumeration_complete"], p["candidate_enumeration_complete"], p["result_limit_saturated"],
        p["stop_reason"],
    )


def _identity_to_payload(identity: ChemicalIdentity) -> dict:
    return {
        "schema_version": identity.schema_version,
        "layer": identity.layer.value,
        "canonical_repr": identity.canonical_repr,
        "identity_digest": identity.identity_digest,
    }


def _identity_from_payload(p: dict) -> ChemicalIdentity:
    return ChemicalIdentity(p["schema_version"], IdentityLayer(p["layer"]), p["canonical_repr"], p["identity_digest"])


def _formula_to_payload(formula: Formula) -> dict:
    return {"counts": [[symbol, count] for symbol, count in formula.counts], "charge": formula.charge}


def _formula_from_payload(p: dict) -> Formula:
    return Formula(tuple((symbol, count) for symbol, count in p["counts"]), p["charge"])


def _structural_species_to_payload(species: StructuralSpecies) -> dict:
    return {
        "schema_version": species.schema_version,
        "structure": _identity_to_payload(species.structure),
        "formula": _formula_to_payload(species.formula),
        "atoms": list(species.atoms),
        "bonds": [[i, j, order] for i, j, order in species.bonds],
        "charge": species.charge,
        "state": species.state,
    }


def _structural_species_from_payload(p: dict) -> StructuralSpecies:
    return StructuralSpecies(
        p["schema_version"],
        _identity_from_payload(p["structure"]),
        _formula_from_payload(p["formula"]),
        tuple(p["atoms"]),
        tuple((i, j, order) for i, j, order in p["bonds"]),
        p["charge"],
        p["state"],
    )


def _stoich_to_payload(pairs: "tuple[tuple[StructuralSpecies, int], ...]") -> list:
    return [{"species": _structural_species_to_payload(s), "multiplicity": m} for s, m in pairs]


def _stoich_from_payload(items: list) -> tuple:
    return tuple((_structural_species_from_payload(i["species"]), i["multiplicity"]) for i in items)


def _structural_candidate_to_payload(candidate: StructuralCandidate) -> dict:
    return {
        "schema_version": candidate.schema_version,
        "direction": candidate.direction.value,
        "provider_id": candidate.provider_id,
        "provider_version": candidate.provider_version,
        "parent": _structural_species_to_payload(candidate.parent),
        "reagents": _stoich_to_payload(candidate.reagents),
        "products": _stoich_to_payload(candidate.products),
        "witness_kind": candidate.witness_kind,
        "witness_digest": candidate.witness_digest,
        "edit_equation": candidate.edit_equation,
        "projection_kind": candidate.projection_kind,
        "projection_digest": candidate.projection_digest,
        "projection_equation": candidate.projection_equation,
        "readiness_tier": candidate.readiness_tier,
        "identity_losses": [identity_loss_to_payload(loss) for loss in candidate.identity_losses],
    }


def _structural_candidate_from_payload(p: dict) -> StructuralCandidate:
    return StructuralCandidate(
        p["schema_version"],
        TransformDirection(p["direction"]),
        p["provider_id"],
        p["provider_version"],
        _structural_species_from_payload(p["parent"]),
        _stoich_from_payload(p["reagents"]),
        _stoich_from_payload(p["products"]),
        p["witness_kind"],
        p["witness_digest"],
        p["edit_equation"],
        p["projection_kind"],
        p["projection_digest"],
        p["projection_equation"],
        p["readiness_tier"],
        tuple(identity_loss_from_payload(loss) for loss in p["identity_losses"]),
    )


def ir_to_payload(ir: ChemicalCompilationIR) -> dict:
    """A JSON-compatible dict capturing every SEMANTIC field of ``ir`` (enums by value, tuples as lists)."""
    if type(ir) is not ChemicalCompilationIR:
        raise TypeError("ir_to_payload needs a ChemicalCompilationIR")
    return {
        "schema_version": ir.schema_version,
        "tool_version": ir.tool_version,
        "operation": ir.operation.value,
        "target": {
            "schema_version": ir.target.schema_version,
            "layer": ir.target.layer.value,
            "canonical_repr": ir.target.canonical_repr,
            "identity_digest": ir.target.identity_digest,
        },
        "request_digest": ir.request_digest,
        "identity_losses": [identity_loss_to_payload(loss) for loss in ir.identity_losses],
        "terminal_policy_digest": ir.terminal_policy_digest,
        "transform_registry_digest": ir.transform_registry_digest,
        "search_status": ir.search_status.value,
        "standard_status": ir.standard_status,
        "search_receipt": _receipt_view_to_payload(ir.search_receipt),
        "candidates": [
            {
                "schema_version": c.schema_version,
                "candidate_kind": c.candidate_kind,
                "candidate_digest": c.candidate_digest,
                "equation": c.equation,
                "readiness_tier": c.readiness_tier,
            }
            for c in ir.candidates
        ],
        "diagnostics": list(ir.diagnostics),
        "structural_candidates": [_structural_candidate_to_payload(s) for s in ir.structural_candidates],
    }


def ir_from_payload(payload: dict) -> ChemicalCompilationIR:
    """Rebuild a :class:`ChemicalCompilationIR` from :func:`ir_to_payload`'s dict, re-validating every invariant.

    Every frozen record is reconstructed and its ``__post_init__`` re-runs, so a payload that violates a schema
    string, an enum domain, or the canonical/distinct candidate ordering is REFUSED here -- deserialization never
    trusts a value it would not have constructed itself.
    """
    if not isinstance(payload, dict):
        raise TypeError("ir_from_payload needs a dict")
    # check the schema version FIRST, before dereferencing any versioned key: an older payload (e.g. v1alpha3,
    # which carried search_receipt_digest and NO search_receipt object) must fail with a CLEAR cross-version
    # message, not an opaque KeyError from a missing key while assembling constructor args (red-team fold).
    if payload.get("schema_version") != CHEMICAL_COMPILATION_IR_SCHEMA:
        raise ValueError(
            f"schema_version must be exactly {CHEMICAL_COMPILATION_IR_SCHEMA!r}, got "
            f"{payload.get('schema_version')!r}; this reader does not consume an older IR payload shape"
        )
    t = payload["target"]
    target = ChemicalIdentity(
        t["schema_version"], IdentityLayer(t["layer"]), t["canonical_repr"], t["identity_digest"]
    )
    candidates = tuple(
        CandidateSummary(
            c["schema_version"], c["candidate_kind"], c["candidate_digest"], c["equation"], c["readiness_tier"]
        )
        for c in payload["candidates"]
    )
    return ChemicalCompilationIR(
        payload["schema_version"],
        payload["tool_version"],
        CompilationOperation(payload["operation"]),
        target,
        payload["request_digest"],
        tuple(identity_loss_from_payload(loss) for loss in payload["identity_losses"]),
        payload["terminal_policy_digest"],
        payload["transform_registry_digest"],
        SearchStatus(payload["search_status"]),
        payload["standard_status"],
        _receipt_view_from_payload(payload["search_receipt"]),
        candidates,
        tuple(payload["diagnostics"]),
        tuple(_structural_candidate_from_payload(s) for s in payload["structural_candidates"]),
    )


def serialize_ir(ir: ChemicalCompilationIR) -> str:
    """A canonical JSON string for ``ir`` -- deterministic (``sort_keys``) and round-trip identity-preserving."""
    return json.dumps(ir_to_payload(ir), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def deserialize_ir(text: str) -> ChemicalCompilationIR:
    """Parse a :func:`serialize_ir` string back into a validated :class:`ChemicalCompilationIR`."""
    if not isinstance(text, str):
        raise TypeError("deserialize_ir needs a str")
    return ir_from_payload(json.loads(text))


# == IR-INV-01: the recompiler consumes a SERIALIZED decompile artifact, end to end =======================
#
# This is where the two compiler directions actually MEET across the serialization boundary (section 4.1): a
# decompile artifact is emitted, serialized to a transportable string, and then a recompile is driven FROM it.
#
# The load-bearing honesty is the formula->structure gap (section 5.4).  A decompile artifact is a FORMULA-layer
# fact ("H2O decomposes to the {H, O} buckets"); the recompiler is a STRUCTURE-layer search (it needs a Molecule
# and structural terminals).  A formula does NOT determine a structure -- so the caller MUST supply the structural
# hypothesis, and the bridge's one non-trivial consumption of the artifact is to GATE that hypothesis on the
# decompiled formula: the reconstitution target's formula must equal the formula the decompile analysed, or the
# request is not an inverse of that artifact at all and is refused.
#
# The named acceptance (IR-INV-01): water.  ``recompile`` cannot build H2O from H2/O2 terminals -- elemental
# redox is outside the capped-scission organic grammar.  We do NOT invent a water transform (that would fabricate
# a reaction, W3-forbidden); instead the bridge classifies the outcome and, for water, returns a PRECISE
# unsupported-transform refusal (``NO_ROUTE_IN_GRAMMAR``).  The one distinction that makes the refusal honest is
# separating an EXHAUSTIVE empty search (a real grammar dead end) from a TRUNCATED empty search (inconclusive) --
# the same split SRCH-DEPTH-01 enforced one layer down; a truncated search is NEVER reported as a dead end.


class InverseStatus(str, Enum):
    """The verdict of driving a recompile FROM a decompile artifact (section 4.1 / IR-INV-01).

    Two of these are pre-search refusals (no recompile IR is produced); the rest classify a recompile that ran.
    Only ``ROUTES_FOUND`` and ``TARGET_ALREADY_TERMINAL`` are successes; every other member carries a ``refusal``
    explaining precisely why the inverse did not (or could not) reconstitute the target.
    """

    NOT_A_DECOMPILE_ARTIFACT = "NOT_A_DECOMPILE_ARTIFACT"  # the serialized IR is not a DECOMPILE/FORMULA artifact
    FORMULA_MISMATCH = "FORMULA_MISMATCH"                  # the structural hypothesis is not the decompiled species
    TARGET_ALREADY_TERMINAL = "TARGET_ALREADY_TERMINAL"    # trivially reconstituted: target is itself on-hand stock
    ROUTES_FOUND = "ROUTES_FOUND"                          # >=1 formal-candidate route/DAG (completeness: see the IR)
    NO_ROUTE_IN_GRAMMAR = "NO_ROUTE_IN_GRAMMAR"            # EXHAUSTIVE empty search: a real grammar-level dead end
    INCONCLUSIVE_BOUNDS_HIT = "INCONCLUSIVE_BOUNDS_HIT"    # TRUNCATED empty search: cannot conclude no-route


@dataclass(frozen=True)
class InverseResult:
    """The end-to-end outcome of consuming a serialized decompile artifact and driving a recompile from it.

    ``decompile_ir`` is always the (re-validated) artifact that was consumed.  ``recompile_ir`` is the structural
    recompilation that ran, or ``None`` for a pre-search refusal (``NOT_A_DECOMPILE_ARTIFACT``/``FORMULA_MISMATCH``).
    ``refusal`` is a precise, human-readable explanation for every non-success status and ``None`` for a success.

    This is deliberately NOT a :class:`Digestible`: it is a report bundling two already-identified IRs plus a
    verdict, not a new identity.  The transportable identities are the two IRs it carries.
    """

    decompile_ir: ChemicalCompilationIR
    recompile_ir: "ChemicalCompilationIR | None"
    inverse_status: InverseStatus
    refusal: "str | None"

    def __post_init__(self) -> None:
        if type(self.decompile_ir) is not ChemicalCompilationIR:
            raise TypeError("decompile_ir must be a ChemicalCompilationIR")
        if self.recompile_ir is not None and type(self.recompile_ir) is not ChemicalCompilationIR:
            raise TypeError("recompile_ir must be a ChemicalCompilationIR or None")
        if not isinstance(self.inverse_status, InverseStatus):
            raise TypeError("inverse_status must be an InverseStatus")
        # the two slots must actually carry the operations the field names advertise -- a DECOMPILE artifact in
        # the recompile slot (or vice versa) is an incoherent bundle even if every other invariant holds
        # (red-team finding: enforce the coherence the docstring promises, do not merely document it).  The ONE
        # exemption is NOT_A_DECOMPILE_ARTIFACT, whose whole job is to report the wrong-operation artifact it was
        # handed -- so the decompile slot there deliberately carries a non-DECOMPILE op.
        if self.inverse_status is not InverseStatus.NOT_A_DECOMPILE_ARTIFACT:
            if self.decompile_ir.operation is not CompilationOperation.DECOMPILE:
                raise ValueError("decompile_ir must carry the DECOMPILE operation")
        if self.recompile_ir is not None and self.recompile_ir.operation is not CompilationOperation.RECOMPILE:
            raise ValueError("recompile_ir must carry the RECOMPILE operation")
        _successes = (InverseStatus.ROUTES_FOUND, InverseStatus.TARGET_ALREADY_TERMINAL)
        if self.inverse_status in _successes:
            if self.refusal is not None:
                raise ValueError("a success status carries no refusal")
        elif not isinstance(self.refusal, str) or not self.refusal:
            raise ValueError("a non-success status must carry a non-empty refusal string")
        # a pre-search refusal produced no recompile IR; a post-search status must carry one
        _pre_search = (InverseStatus.NOT_A_DECOMPILE_ARTIFACT, InverseStatus.FORMULA_MISMATCH)
        if self.inverse_status in _pre_search and self.recompile_ir is not None:
            raise ValueError("a pre-search refusal must not carry a recompile IR")
        if self.inverse_status not in _pre_search and self.recompile_ir is None:
            raise ValueError("a post-search status must carry a recompile IR")

    @property
    def reconstituted(self) -> bool:
        """True iff the inverse produced at least one route (or the target was already terminal stock)."""
        return self.inverse_status in (InverseStatus.ROUTES_FOUND, InverseStatus.TARGET_ALREADY_TERMINAL)

    def render(self) -> str:
        head = (
            f"INVERSE COMPILATION ({self.inverse_status.value})\n"
            f"  decompiled: {self.decompile_ir.target.canonical_repr} "
            f"[{self.decompile_ir.target.layer.value}] -> {self.decompile_ir.candidate_count} bucket edge(s)\n"
        )
        if self.recompile_ir is not None:
            head += (
                f"  recompiled: {self.recompile_ir.target.canonical_repr} "
                f"[{self.recompile_ir.target.layer.value}]; search {self.recompile_ir.standard_status} "
                f"(engine: {self.recompile_ir.search_status.value}); "
                f"{self.recompile_ir.candidate_count} candidate(s)\n"
            )
        # NB: a decompile artifact is formula-level, so a success confirms only that the SUPPLIED structural
        # hypothesis routes -- never that the artifact was about that specific isomer (a formula does not fix
        # one). Say exactly that, so the word does not read as structure-level identity confirmation.
        head += f"  refusal: {self.refusal}" if self.refusal else "  refusal: none (routes for the supplied structure)"
        return head


def recompile_from_serialized(
    decompile_ir_text: str,
    *,
    structure: "object",
    reagents: tuple,
    available: tuple = (),
    commodities: tuple = (),
    max_depth: int = 2,
    max_results: int = 100,
    cut_budget: int = 20_000,
    mode: str = "routes",
    tool_version: str | None = None,
) -> InverseResult:
    """Consume a SERIALIZED decompile artifact and drive a recompile from it, end to end (IR-INV-01).

    ``decompile_ir_text`` is a :func:`serialize_ir` string of a DECOMPILE artifact (as produced by
    :func:`decompile_to_ir`); ``structure`` is the caller's STRUCTURE-layer hypothesis (a
    :class:`~smartchem.category.Molecule`) for the decompiled species.  The bridge:

    1. deserializes and re-validates the artifact (a tampered payload is refused on read);
    2. refuses unless the artifact is a DECOMPILE at the FORMULA layer (``NOT_A_DECOMPILE_ARTIFACT``);
    3. gates the structural hypothesis on the decompiled formula -- the reconstitution target's formula MUST
       equal the analysed formula, else the request is not an inverse of THIS artifact (``FORMULA_MISMATCH``);
       this is the one place the artifact genuinely CONSTRAINS the recompile across the section 5.4 gap;
    4. runs :func:`recompile_to_ir` over the structural hypothesis and terminals; and
    5. classifies the outcome, keeping the honest distinction between an EXHAUSTIVE empty search
       (``NO_ROUTE_IN_GRAMMAR`` -- a real grammar dead end, e.g. water from H2/O2) and a TRUNCATED empty
       search (``INCONCLUSIVE_BOUNDS_HIT`` -- cannot conclude no-route).

    W3 unchanged: a ``ROUTES_FOUND`` verdict means conservation-valid formal candidates exist within the grammar
    and bounds, never that any synthesis is validated; read ``recompile_ir.search_status`` for completeness.
    """
    from .category import Molecule

    decompile_ir = deserialize_ir(decompile_ir_text)

    if decompile_ir.operation is not CompilationOperation.DECOMPILE or decompile_ir.target.layer is not IdentityLayer.FORMULA:
        return InverseResult(
            decompile_ir,
            None,
            InverseStatus.NOT_A_DECOMPILE_ARTIFACT,
            (
                f"the serialized artifact is {decompile_ir.operation.value} at the "
                f"{decompile_ir.target.layer.value} layer; recompile_from_serialized inverts a DECOMPILE/FORMULA "
                f"artifact (section 4.1)"
            ),
        )

    if type(structure) is not Molecule:
        raise TypeError("structure must be a smartchem.category.Molecule (the structural hypothesis)")

    struct_formula = ChemicalIdentity.of_formula(Formula.of(structure.formula, structure.charge))
    if struct_formula.identity_digest != decompile_ir.target.identity_digest:
        return InverseResult(
            decompile_ir,
            None,
            InverseStatus.FORMULA_MISMATCH,
            (
                f"the structural hypothesis has formula {struct_formula.canonical_repr}, but the decompile artifact "
                f"analysed {decompile_ir.target.canonical_repr}; the inverse must reconstitute the SAME species "
                f"(section 5.4: a formula does not fix a structure, but the target's formula must equal the "
                f"decompiled formula)"
            ),
        )

    recompile_ir = recompile_to_ir(
        structure,
        reagents=reagents,
        available=available,
        commodities=commodities,
        max_depth=max_depth,
        max_results=max_results,
        cut_budget=cut_budget,
        mode=mode,
        tool_version=tool_version,
    )

    # classify from STRUCTURED facts, never by string-matching a diagnostic.  target-in-stock is decided the same
    # way the search decides it: the target's structure identity lies in the union of the declared terminals.
    terminal_idents = frozenset(_structure_ident(m) for m in (*available, *reagents, *commodities))
    target_terminal = _structure_ident(structure) in terminal_idents

    if target_terminal:
        return InverseResult(decompile_ir, recompile_ir, InverseStatus.TARGET_ALREADY_TERMINAL, None)
    if recompile_ir.candidate_count > 0:
        return InverseResult(decompile_ir, recompile_ir, InverseStatus.ROUTES_FOUND, None)
    if recompile_ir.complete_within_bounds:
        return InverseResult(
            decompile_ir,
            recompile_ir,
            InverseStatus.NO_ROUTE_IN_GRAMMAR,
            (
                f"no route reconstitutes {decompile_ir.target.canonical_repr} from the declared terminals within "
                f"the '{mode}' grammar at the declared bounds (max_depth={max_depth}); the search was exhaustive "
                f"there (no limit fired), but exhaustion is of THIS grammar/mode at THESE bounds -- NOT a proof "
                f"that no route exists under a different mode or higher bounds. No bridge reaction is invented "
                f"(W3, section 8.3, no-route: exhaustive-within-bounds)."
            ),
        )
    return InverseResult(
        decompile_ir,
        recompile_ir,
        InverseStatus.INCONCLUSIVE_BOUNDS_HIT,
        (
            f"the recompile search for {decompile_ir.target.canonical_repr} was TRUNCATED "
            f"({recompile_ir.standard_status}) before finding any route or exhausting the grammar; no-route "
            f"cannot be concluded -- raise the bounds to decide (stop reason per section 8.2; this zero-candidate "
            f"incomplete outcome is section 8.3's INCOMPLETE_NO_ROUTE_OBSERVED)"
        ),
    )
