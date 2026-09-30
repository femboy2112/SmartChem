"""TRANSFORM-PROVIDER-01: the typed closed provider boundary the bounded search is parameterized by.

The genericity reorientation's central verdict is that SmartChem is a generic bounded chemical-SEARCH compiler
parameterized by a still-NARROW transform algebra.  This module is the seam that makes the algebra a PARAMETER: the
recompiler's route/DAG search and the structural decompile no longer call one hard-wired enumeration
(:func:`~smartchem.structure_descent.capped_scissions`) directly -- they call a :class:`TransformProviderRegistry`,
a CLOSED ordered set of typed :class:`TransformProvider` s, each of which enumerates one transform FAMILY behind a
stable typed identity (id + version + capability manifest).

Two honesty contracts hold at this boundary:

* **exclusivity** -- capped-scission enumeration now runs ONLY inside :class:`CappedScissionProvider`; the search
  and the IR reach it through the registry, never by calling ``capped_scissions`` directly.  A new family is added
  by registering a provider, NOT by forking the search (that is the whole point -- CHEM-ALG-01 composes through the
  UNCHANGED search).
* **partiality never aggregates to a false complete** -- the registry's completeness is the AND of every provider's
  own completeness, so one provider hitting its budget makes the aggregate incomplete; a provider that exhausted
  its family cannot mask another that did not.

The DEFAULT registry holds exactly the one capped-scission provider, so rerouting through it is behavior-identical
to the direct call it replaces -- the search is now generic, and passing a different registry (a wider algebra) is
the ONLY thing that changes what it enumerates.

A "transform" here is any family's structural rewrite exposing the uniform interface the recompiler's step-builder
(:meth:`~smartchem.experiment.step.ExperimentStep.from_transform`), the conditions gate
(:func:`~smartchem.decompiler_conditions.assembly_conditions`), and the structural decompile IR all consume:
``reactant`` (a :class:`~smartchem.category.Molecule`), ``reagents`` (a tuple of consumed mediator Molecules, empty
for a family that consumes none), ``products`` (the derived product Molecules), ``forget()`` (its forgetful
composition edge), ``equation()``, and ``digest``.  :class:`~smartchem.structure_descent.CappedScission` already
satisfies it structurally.

Categorically (Move 3, ``docs/research/PROVIDER_ALGEBRA_AS_SMC_GENERATORS_v0.1.md``): the providers are a
*generating set* of morphisms, and ``ExperimentStep.from_transform(t).open()`` is the on-generators action of a
*semantics functor* into the open SMC (:mod:`smartchem.open_chem_diagram`).  This is a functor, NOT a proven-free
category; the ``(witness_kind, projection_kind)`` pairs are PROVENANCE tags, not composition-gating hom-types
(composition at the Molecule altitude is total -- a charged family's products can feed a neutral one); and IR-COMMUTE
(``tests/test_ir_commute.py``) is a forgetful NATURALITY square between two functors, not the monoidal coherence law
(interchange/braid/hexagon coherence lives in and is proven on :mod:`smartchem.open_core`).
``tests/test_provider_category.py`` pins the functor's laws: provenance is out of the categorical identity (the R24
congruence discipline), F quotients symmetric cuts but stays faithful on distinct reactions, and forget/open agree
per generator.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import canonical_digest
from .structure_descent import capped_scissions, heterolytic_scissions, redox_couples

__all__ = [
    "TransformProvider",
    "CappedScissionProvider",
    "HeterolyticScissionProvider",
    "RedoxHalfReactionProvider",
    "EnumeratedTransform",
    "TransformProviderRegistry",
    "DEFAULT_TRANSFORM_REGISTRY",
    "search_algebra_digest",
    "ProviderUse",
    "ProviderSemanticDescriptor",
    "UnsupportedProviderUseError",
    "assert_registry_supports_use",
]


class ProviderUse(Enum):
    """The consumer TOPOLOGY a provider declares it is admissible for (Course-Correction 1, 0.7 Round II).

    A provider does not owe the same evidence in every consumer: the same family can be sound as a one-step
    STRUCTURE_DECOMPILE and unsound (or crashing) inside the recursive LINEAR_ROUTE / CONVERGENT_DAG search.  A
    consumer validates its registry against ITS use BEFORE enumeration (:func:`assert_registry_supports_use`), so a
    wrong-lane provider is refused with a typed error rather than silently filtered (which would let a receipt name a
    caller-selected algebra while executing a hidden subset) or -- as measured on the pre-0.7 code -- crashing the
    whole search mid-enumeration and taking valid candidates down with it.

    The values coincide with the search-topology strings :func:`search_algebra_digest` stamps ("linear-route",
    "convergent-dag") so a consumer's use and the digest's topology are one vocabulary.
    """

    STRUCTURE_DECOMPILE = "structure-decompile"
    LINEAR_ROUTE = "linear-route"
    CONVERGENT_DAG = "convergent-dag"


@dataclass(frozen=True)
class ProviderSemanticDescriptor:
    """A CONTENT-bound descriptor of what a provider's grammar actually does -- the 0.7 hardening of provider
    identity (plan §4).  The pre-0.7 identity was ``(provider_id, provider_version, capability_manifest)``: three
    hand-declared values, so a developer could change the actual rewrite rule or a load-bearing guard without bumping
    the hand-typed version, producing a BYTE-IDENTICAL identity for a semantically different grammar.  This descriptor
    folds the pieces that MUST move when the chemistry moves into the identity via :attr:`digest`.

    Epistemic boundary (deliberate, not a hedge): :attr:`digest` GUARANTEES that a change to a *declarative* rule
    (``structural_rule_digest``), a typed *guard policy* (``guard_spec_digest``), the ``supported_uses`` set, the
    ``witness_kind`` / ``projection_kind``, a typed ``behavior_params`` knob, or the ``reagentless_capable`` capability
    (0.7 Round III -- it gates whether a search runs on an empty reagent pool) forces an identity change.  It does
    NOT and cannot detect an arbitrary edit to *imperative* enumerator Python (e.g. the capped-scission cut-selection
    body, or a verifier's own logic) -- for those, ``structural_rule_digest``/``guard_spec_digest`` are ``None`` and
    the honest tracker of an implementation change remains ``provider_version`` + tool/schema versioning.  No source
    text is hashed for ceremony; a family gets a rule/guard digest only where a genuine declarative artifact exists.
    """

    family: str
    supported_uses: tuple           # sorted tuple[str] of ProviderUse values
    witness_kind: str
    projection_kind: str
    behavior_params: tuple          # sorted tuple[tuple[str, str|int|bool]] -- the typed knobs, not prose
    structural_rule_digest: "str | None"
    guard_spec_digest: "str | None"
    authority: str
    #: whether the family can GENERATE with an empty helper-reagent pool.  This is a SEMANTIC, identity-bearing
    #: property (0.7 Round III): the service reads it to decide whether an empty helper pool is a runnable search or
    #: an INVALID_INPUT refusal, so two registries differing only in this flag accept/reject the same request
    #: differently -- flipping it MUST move the digest, or the one-way "equal digest => same executed search" law
    #: leaks.  It is a family-structural fact (a concerted Diels-Alder needs no reagent; capped-scission does), not
    #: the request-time fact of WHICH reagent is on hand (that stays ``helper_reagents``).  Defaulted for
    #: back-compat with any direct descriptor construction; the base builder always supplies the provider's value.
    reagentless_capable: bool = True

    @property
    def digest(self) -> str:
        return canonical_digest(
            (
                # v2 (0.7 Round III): schema gains ``reagentless_capable`` -- a bump to mark the payload-shape change.
                "provider-semantic-descriptor-v2",
                self.family,
                self.supported_uses,
                self.witness_kind,
                self.projection_kind,
                self.behavior_params,
                self.structural_rule_digest,
                self.guard_spec_digest,
                self.authority,
                self.reagentless_capable,
            )
        )


def search_algebra_digest(topology: str, registry: "TransformProviderRegistry") -> str:
    """The section-8.4 provenance a bounded SEARCH stamps on its receipt: the search TOPOLOGY (a linear route vs a
    convergent DAG) combined with the transform ALGEBRA (the provider registry) that generated the candidates.

    So the receipt's "all pathways generated by transform registry <digest>" moves when the ALGEBRA widens (a new
    provider, a version/manifest bump) as well as when the topology changes -- red-team fold: the route/DAG receipts
    used to stamp a FIXED capped-scission grammar digest that was invisible to the ``registry`` parameter, so a
    wider algebra (which really does generate different pathways) left the provenance byte-unchanged and naming the
    wrong grammar.  (The one-step structural decompile has no topology dimension, so it stamps ``registry.digest``
    directly; a route/DAG additionally carries its topology, hence this combined form.)
    """
    return canonical_digest(("search-transform-algebra-v1", topology, registry.digest))


class TransformProvider:
    """One transform FAMILY behind a typed identity.  Subclasses declare ``provider_id`` / ``provider_version``,
    a ``capability_manifest`` (a declared descriptor of what the family does -- bond operations, charge handling,
    the witness/projection kinds it emits), and ``enumerate_transforms``.  0.7 Round III: the identity the registry
    digest is built from is ``(provider_id, provider_version, semantic_descriptor.digest)`` -- prose-independent.
    The ``semantic_descriptor`` binds every load-bearing manifest value (typed knobs, family/projection/authority,
    the reagentless capability) plus a family's declarative rule/guard digests, so a chemistry-bearing change moves
    the digest while a mechanism-PROSE edit does not.  The imperative enumerator body still relies on the declared
    ``provider_version`` discipline (a digest cannot bind arbitrary Python; see ProviderSemanticDescriptor)."""

    provider_id: str
    provider_version: str
    #: the witness/projection kind pair the family's StructuralCandidate carries (IR-STRUCT-01); the IR's
    #: ``_WITNESS_PROJECTION`` map is the authority on which pairs are admissible.
    witness_kind: str
    #: the consumer topologies this family is admissible for (Course-Correction 1).  Fail-closed default: a provider
    #: that does not DECLARE its uses supports NONE, so an unclassified family is refused by every consumer rather
    #: than allowed to crash one.  Every concrete provider overrides this with its measured, honest use set.
    supported_uses: "frozenset[ProviderUse]" = frozenset()
    #: whether this family can GENERATE with an empty helper-reagent pool.  Most families are reagentless (DA,
    #: heterolytic, redox, bond-order ignore the pool); capped-scission REQUIRES a cutting reagent and overrides this
    #: to False.  Read by the service's reagent guard so an empty pool is refused only when NO provider in the
    #: selected algebra can run reagentless.  0.7 Round III: this IS part of provider identity (it rides
    #: ``semantic_descriptor``) -- Round II's "deliberately NOT part of identity" was wrong.  It gates whether a
    #: search executes at all, so two registries differing only in this flag run different searches under an empty
    #: pool; leaving it out of the digest broke the one-way "equal digest => same executed search" law.  It is a
    #: family-structural capability, not the request-time fact of which reagent is on hand (that stays a request field).
    reagentless_capable: bool = True

    @property
    def capability_manifest(self) -> tuple:
        raise NotImplementedError

    @property
    def semantic_descriptor(self) -> ProviderSemanticDescriptor:
        """The content-bound descriptor folded into :attr:`identity`.  The base builds it from the declared manifest
        + ``supported_uses`` with NO rule/guard digest (an imperative family has no declarative artifact to bind);
        a family whose rewrite IS a declarative rule (Diels-Alder) overrides this to supply ``structural_rule_digest``
        / ``guard_spec_digest`` (see :mod:`smartchem.diels_alder`)."""
        manifest = dict(self.capability_manifest)
        return ProviderSemanticDescriptor(
            family=str(manifest.get("family", self.provider_id)),
            supported_uses=tuple(sorted(u.value for u in self.supported_uses)),
            witness_kind=self.witness_kind,
            projection_kind=str(manifest.get("projection_kind", "")),
            # the typed knobs are the manifest entries whose value is not free prose (int/bool ceilings, flags);
            # prose ("mechanism", "family", ...) is documentation, not behavior identity.
            behavior_params=tuple(sorted((k, v) for k, v in self.capability_manifest if not isinstance(v, str))),
            structural_rule_digest=None,
            guard_spec_digest=None,
            # authority/scope declarations pulled by name: the deployment domain, the chemical-authority claim, and
            # the replay-verification discipline a provider claims (``structural_replay`` -- the one string manifest
            # key that is neither prose nor auto-folded).  Named here so dropping the raw manifest from ``identity``
            # (0.7 Round III) loses no scope/authority content: a relabel of any of these still moves the digest.
            authority="|".join(
                str(manifest[k]) for k in ("state_domain", "chemical_authority", "structural_replay") if k in manifest
            ),
            reagentless_capable=self.reagentless_capable,
        )

    @property
    def identity(self) -> tuple:
        # 0.7 Round III: identity is PROSE-INDEPENDENT.  The raw ``capability_manifest`` (which carries human
        # "mechanism" prose) is no longer in identity; the 3rd element is the semantic descriptor digest, which binds
        # every LOAD-BEARING manifest value (typed knobs auto-fold into ``behavior_params``; family/projection/
        # authority/structural_replay are name-extracted) plus the rule/guard digests and the reagentless capability.
        # So a behavior/guard/rule/use/witness/reagent-policy edit moves identity (and thus ``registry.digest`` /
        # ``search_algebra_digest``), while a mechanism-PROSE edit does NOT -- the noise Round II left in the digest is
        # gone.  The manifest survives as documentation/provenance via ``capability_manifest``; the imperative-body
        # blind spot (ProviderSemanticDescriptor's docstring) is still tracked by ``provider_version``.
        return (self.provider_id, self.provider_version, self.semantic_descriptor.digest)

    def enumerate_transforms(self, reactant, reagents, *, budget):
        """Return ``(transforms, complete)`` for this family: a tuple of transform objects (each exposing the
        uniform interface) and whether the family's enumeration was exhaustive within ``budget`` (False iff a
        budget was hit).  MUST NOT raise on an empty reagent pool -- a family that consumes no reagents ignores it,
        one that requires reagents returns ``((), True)``."""
        raise NotImplementedError


@dataclass(frozen=True)
class CappedScissionProvider(TransformProvider):
    """The capped-scission family (valence-preserving whole-bond rewrites, reagent-mediated, neutral) as a typed
    provider.  The one and only place :func:`~smartchem.structure_descent.capped_scissions` is now called."""

    provider_id: str = "capped-scission-mediated"
    provider_version: str = "v1"
    witness_kind: str = "CAPPED_SCISSION"
    max_reactant_cuts: int = 1
    ring_aware: bool = False
    # neutral, size-reducing, and IR-wired (DecompositionEdge/MediatedEdge): admissible in all three consumers.
    supported_uses = frozenset(
        {ProviderUse.STRUCTURE_DECOMPILE, ProviderUse.LINEAR_ROUTE, ProviderUse.CONVERGENT_DAG}
    )
    # a mediated cleavage MUST consume a capping reagent -- with an empty pool it enumerates nothing (see
    # enumerate_transforms below), so the service refuses an empty-reagent request under a capped-only algebra.
    reagentless_capable = False

    def __post_init__(self) -> None:
        # 0.9.5 (Wave C3 F2): the typed knobs ARE behaviour identity -- only NON-string manifest values fold into the
        # semantic descriptor -- so a knob given as a string (``ring_aware="yes"``) would steer enumeration while
        # dropping out of the registry digest (a bad enumeration-cache hit).  A knob is exactly its declared type.
        if type(self.max_reactant_cuts) is not int or self.max_reactant_cuts < 1:
            raise TypeError(f"max_reactant_cuts must be a positive int, got {self.max_reactant_cuts!r}")
        if type(self.ring_aware) is not bool:
            raise TypeError(f"ring_aware must be a bool, got {self.ring_aware!r}")

    @property
    def capability_manifest(self) -> tuple:
        return (
            ("family", "capped-scission"),
            ("mechanism", "valence-preserving whole-bond rewrite, reagent-mediated, neutral"),
            ("witness_kind", self.witness_kind),
            ("projection_kind", "MEDIATED_EDGE"),
            ("max_reactant_cuts", self.max_reactant_cuts),
            ("ring_aware", self.ring_aware),
        )

    def enumerate_transforms(self, reactant, reagents, *, budget):
        # the boundary contract: a family that CANNOT apply enumerates nothing and is trivially complete -- it never
        # raises (so it composes in a mixed registry without taking the whole decompile down; red-team fold).
        if reactant.charge != 0:
            # capped scission is neutral-only (its CappedScission certificate refuses a charged reactant); in a
            # mixed registry a charged target must fall through to a charged family, not crash the capped provider.
            return (), True
        if not reagents:
            # a mediated cleavage needs at least one reagent to cap the broken bond; with none, nothing to enumerate.
            return (), True
        return capped_scissions(
            reactant, reagents, max_reactant_cuts=self.max_reactant_cuts, budget=budget, ring_aware=self.ring_aware
        )


@dataclass(frozen=True)
class HeterolyticScissionProvider(TransformProvider):
    """The heterolytic-scission family (item 3): single-bond heterolysis into two CHARGED ions, reagentless, under
    the localized-charge model.  The first CHARGED family to ride the transform algebra -- it forgets to a
    charge-carrying :class:`~smartchem.structure_descent.ChargedDecompositionEdge` (the neutral MediatedEdge/
    DecompositionEdge refuse a charged species), demonstrating the algebra widening past neutral rewrites with no
    engine fork.  Enumerates through the UNCHANGED registry seam; charged fragments do not terminate at neutral
    stock, so this widens the DECOMPILE algebra (it is not forced through the neutral route search)."""

    provider_id: str = "heterolytic-scission"
    provider_version: str = "v1"
    witness_kind: str = "HETEROLYTIC_SCISSION"
    # charged products do not terminate the neutral route search (they trip _refuse_charged_target in recursion);
    # DECOMPILE-only, and it is fully wired into the IR StructuralCandidate witness/projection path.
    supported_uses = frozenset({ProviderUse.STRUCTURE_DECOMPILE})

    @property
    def capability_manifest(self) -> tuple:
        return (
            ("family", "heterolytic-scission"),
            ("mechanism", "single-bond heterolysis into two charged ions (localized-charge model), reagentless"),
            ("witness_kind", self.witness_kind),
            ("projection_kind", "CHARGED_DECOMPOSITION_EDGE"),
            ("charged", True),
        )

    def enumerate_transforms(self, reactant, reagents, *, budget):
        # reagentless: the reagent pool is ignored.  heterolytic_scissions enumerates every single-bond bridge split
        # exhaustively (no budget dimension), so it is always complete within its family.
        return heterolytic_scissions(reactant), True


@dataclass(frozen=True)
class RedoxHalfReactionProvider(TransformProvider):
    """The redox (electron-transfer) family (item 1): oxidation half-reactions ``reduced -> oxidized + n e-``,
    reagentless, CHARGE-ONLY (a redox step makes and breaks no bonds -- same atoms, same bonds).  The chemical<->EM
    bridge family: it forgets to an :class:`~smartchem.structure_descent.ElectronTransferEdge` (mass conserved
    trivially since electrons are massless; CHARGE is the conserved quantity the certificate turns on).

    DECOMPILE-only and OPT-IN (absent from the DEFAULT registry): a redox step does NOT reduce a species' size (its
    product is the SAME molecule but charged, plus electrons), so it is not a size-reducing descent and is not forced
    through the neutral route search -- it widens the DECOMPILE algebra only.  ``max_electrons`` bounds the oxidation
    states enumerated and rides the capability manifest, so bumping it changes the registry digest."""

    provider_id: str = "redox-half-reaction"
    provider_version: str = "v1"
    witness_kind: str = "REDOX_HALF_REACTION"
    max_electrons: int = 2
    # charge-only (no size reduction) and charged: not a route/DAG descent; DECOMPILE-only, IR-wired.
    supported_uses = frozenset({ProviderUse.STRUCTURE_DECOMPILE})

    @property
    def capability_manifest(self) -> tuple:
        return (
            ("family", "redox-half-reaction"),
            ("mechanism", "electron-transfer (oxidation) half-reaction, reagentless, charge-only (same atoms/bonds)"),
            ("witness_kind", self.witness_kind),
            ("projection_kind", "ELECTRON_TRANSFER_EDGE"),
            ("charged", True),
            ("max_electrons", self.max_electrons),
        )

    def enumerate_transforms(self, reactant, reagents, *, budget):
        # reagentless: the reagent pool is ignored.  redox_couples enumerates n=1..max_electrons oxidations
        # exhaustively within the declared max_electrons (no budget dimension), so it is complete within its family.
        return redox_couples(reactant, max_electrons=self.max_electrons), True


@dataclass(frozen=True)
class EnumeratedTransform:
    """One transform the registry produced, tagged with the provider that produced it (so a candidate can record
    WHICH family/version made it -- the IR-STRUCT-01 provider provenance) and the family's ``witness_kind`` (so the
    structural candidate knows which witness/projection pair it carries without dispatching on the transform type)."""

    transform: object
    provider_id: str
    provider_version: str
    witness_kind: str


@dataclass(frozen=True)
class TransformProviderRegistry:
    """A CLOSED, ordered set of transform providers -- the transform algebra the bounded search is parameterized by.

    ``digest`` changes whenever the provider SET, any provider's id/version, or any capability manifest changes
    (section 8.4 / section 4.1: "all pathways generated by transform registry <digest>").  ``enumerate`` fans out
    to every provider and returns the union of their transforms (deduped by transform digest, canonical order) with
    completeness = AND of every provider's completeness -- so provider-local partiality never becomes a false
    aggregate "complete".
    """

    providers: tuple

    def __post_init__(self) -> None:
        if type(self.providers) is not tuple or not self.providers:
            raise ValueError("a transform registry needs at least one provider")
        if any(not isinstance(p, TransformProvider) for p in self.providers):
            raise TypeError("every registry member must be a TransformProvider")
        ids = [p.provider_id for p in self.providers]
        if len(set(ids)) != len(ids):
            raise ValueError("provider ids must be distinct (a registry is a closed set, not a multiset)")

    @property
    def digest(self) -> str:
        # ORDER-SENSITIVE by design: the provider list is an ordered PRIORITY list, not a bare set -- when two
        # families would emit the same transform digest, the earlier provider owns it (its id/version tags the
        # candidate), so provider order is a semantic parameter (dedup provenance), not presentation.  Two registries
        # with the same providers in a different order are different configurations and get different digests.
        return canonical_digest(("transform-provider-registry-v1",) + tuple(p.identity for p in self.providers))

    @property
    def provider_ids(self) -> tuple:
        return tuple(p.provider_id for p in self.providers)

    def enumerate(self, reactant, reagents, *, budget) -> "tuple[tuple[EnumeratedTransform, ...], bool]":
        merged: dict[str, EnumeratedTransform] = {}
        complete = True
        for provider in self.providers:
            transforms, provider_complete = provider.enumerate_transforms(reactant, reagents, budget=budget)
            complete = complete and provider_complete
            for transform in transforms:
                # first provider to emit a given transform digest owns it; a later provider re-emitting the SAME
                # rewrite does not double-count (canonical dedup across the union).
                merged.setdefault(
                    transform.digest,
                    EnumeratedTransform(
                        transform, provider.provider_id, provider.provider_version, provider.witness_kind
                    ),
                )
        ordered = tuple(sorted(merged.values(), key=lambda et: et.transform.digest))
        return ordered, complete


#: The default algebra: exactly the capped-scission family.  Rerouting through this is behavior-identical to the
#: direct ``capped_scissions`` call it replaces, so the whole existing suite is unaffected; a wider algebra is a
#: different registry passed explicitly.
DEFAULT_TRANSFORM_REGISTRY = TransformProviderRegistry((CappedScissionProvider(),))


class UnsupportedProviderUseError(ValueError):
    """Raised by :func:`assert_registry_supports_use` when a registry handed to a consumer contains a provider that
    does not declare that consumer's :class:`ProviderUse`.  A ``ValueError`` (a programming/boundary error), not a
    domain refusal: the caller selected an algebra incompatible with the topology it asked for."""


def assert_registry_supports_use(registry: "TransformProviderRegistry", use: "ProviderUse") -> None:
    """Fail closed BEFORE enumeration if any provider in ``registry`` does not support ``use`` (Course-Correction 1).

    A search/decompile engine calls this at entry.  The alternative measured on the pre-0.7 code was worse than a
    late error: a wrong-lane provider enumerated cleanly (``registry.enumerate`` even reported ``complete=True``),
    then the mismatch surfaced DOWNSTREAM as an uncaught crash in step-building / conditions-lookup / witness
    dispatch, destroying the otherwise-valid candidates of the OTHER providers in the same call.  Silently FILTERING
    the unsupported provider instead would be a different lie -- the receipt would name a caller-selected algebra
    while a hidden subset actually ran.  So the only honest option is a typed refusal naming the offenders."""
    offenders = tuple(p.provider_id for p in registry.providers if use not in p.supported_uses)
    if offenders:
        raise UnsupportedProviderUseError(
            f"a {use.value!r} consumer was handed a registry whose providers {offenders} do not support that use; "
            "refusing before enumeration (an incompatible registry is a programming boundary, not a search result)"
        )
