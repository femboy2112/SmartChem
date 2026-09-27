"""ALGEBRA-PROFILE-01: the closed, versioned registry of selectable transform-algebra profiles (0.7 Round II).

A production compiler request selects an ALGEBRA by a stable profile ID, not by dynamically importing a provider
from a deserialized string.  This module is the ONLY authority mapping a profile ID to an exact, reviewed provider
registry.  It is CLOSED (a fixed dict), TYPED, and VERSIONED: an unknown or tampered ID is a typed refusal, never a
bare ``KeyError`` reaching a user and never an arbitrary import.

Orthogonality (Course-Correction 2): a profile selects the TRANSFORM ALGEBRA (which provider families generate
candidates).  It is independent of the SEARCH TOPOLOGY (linear route vs convergent DAG), which the request's
``transform_grammar`` still carries.  The same profile runs under either topology; a topology runs under any profile
whose providers support that topology's :class:`~smartchem.transform_provider.ProviderUse`.

Promotion policy: the default profile stays ``legacy-capped-v1`` (behaviour-identical to
``DEFAULT_TRANSFORM_REGISTRY``) until the certified profile earns promotion through the full gate.  Constructing
``certified-route-v07`` here does NOT flip the default and does NOT mutate ``DEFAULT_TRANSFORM_REGISTRY`` -- a
default promotion, if earned, is a separate auditable commit.
"""
from __future__ import annotations

from .diels_alder import (
    AlkyneDielsAlderProvider,
    AzaDieneDielsAlderProvider,
    AzaDielsAlderProvider,
    DielsAlderProvider,
    OxaDieneDielsAlderProvider,
    OxaDielsAlderProvider,
    ThiaDieneDielsAlderProvider,
    ThiaDielsAlderProvider,
)
from .transform_provider import (
    CappedScissionProvider,
    HeterolyticScissionProvider,
    ProviderUse,
    RedoxHalfReactionProvider,
    TransformProviderRegistry,
)

__all__ = [
    "ALGEBRA_PROFILES",
    "DEFAULT_ALGEBRA_PROFILE",
    "LEGACY_MISSING_ALGEBRA_PROFILE",
    "DEFAULT_ROUTE_ALGEBRA_PROFILE",
    "PROFILE_USES",
    "UnknownAlgebraProfileError",
    "resolve_algebra_profile",
    "algebra_profile_ids",
    "profile_supports_use",
]

#: The conservative low-level default profile: what a :class:`CompilationRequest` gets when constructed directly
#: with no ``algebra_profile``, and the profile a DECOMPILE request is pinned to (formula descent selects no route
#: algebra).  It STAYS ``legacy-capped-v1`` across a default promotion -- promotion happens at the SERVICE/CLI route
#: builder (:data:`DEFAULT_ROUTE_ALGEBRA_PROFILE`), not in the raw dataclass default.
DEFAULT_ALGEBRA_PROFILE = "legacy-capped-v1"

#: The FROZEN wire-migration law (0.7 Round III).  A pre-0.7 serialized request carries no ``algebra_profile`` field
#: and historically meant the capped-scission algebra; ``request_from_payload`` reconstructs a MISSING field as THIS,
#: forever.  It is a LITERAL, deliberately decoupled from the promotable build default below, so that promoting the
#: route default never silently reinterprets an old payload as the wider algebra.  This value must never change.
LEGACY_MISSING_ALGEBRA_PROFILE = "legacy-capped-v1"

#: The route/DAG build-time default the SERVICE/CLI front door stamps on a request that names no algebra
#: (``build_recompile_request`` -> ``recompile`` / ``plan``).  This is the ONE constant a default-promotion commit
#: flips (to ``certified-route-v07``); it is SEPARATE from the frozen missing-field law above and from the low-level
#: :data:`DEFAULT_ALGEBRA_PROFILE`, so the three meanings can never be confused.  Round III ships it still ==
#: legacy; the default promotion, if the gate closes, is a later separately-auditable commit that edits only this.
DEFAULT_ROUTE_ALGEBRA_PROFILE = "legacy-capped-v1"

# The 8 admitted Diels-Alder families in deterministic order (Lane D admission audit): all-carbon first (the most
# heavily adversary-tested family and the plan's chosen forcing vertical), then alkyne, then the hetero-dienophile
# trio, then the hetero-diene trio.  Order is NOT load-bearing for correctness -- transform digests are class-tagged
# (contracts.py canonical_payload bakes the qualified class name in) so DA edge classes cannot digest-collide with
# each other or with capped-scission -- but it is fixed here for reproducible ownership/provenance.
_CERTIFIED_DA_FAMILIES = (
    DielsAlderProvider(),
    AlkyneDielsAlderProvider(),
    AzaDielsAlderProvider(),
    OxaDielsAlderProvider(),
    ThiaDielsAlderProvider(),
    AzaDieneDielsAlderProvider(),
    OxaDieneDielsAlderProvider(),
    ThiaDieneDielsAlderProvider(),
)

ALGEBRA_PROFILES: "dict[str, TransformProviderRegistry]" = {
    # the production DEFAULT: exactly the capped-scission family (== DEFAULT_TRANSFORM_REGISTRY membership).
    "legacy-capped-v1": TransformProviderRegistry((CappedScissionProvider(),)),
    # the certified widened ROUTE algebra: capped-scission (first, unconditional) + the 8 admitted DA families.
    # AuditedCappedScissionProvider is deliberately NOT placed beside CappedScissionProvider -- it emits
    # byte-identical capped transforms and would fully shadow it under first-provider-wins, adding nothing.
    "certified-route-v07": TransformProviderRegistry((CappedScissionProvider(),) + _CERTIFIED_DA_FAMILIES),
    # a certified STRUCTURE-DECOMPILE-only algebra: the two charged families that are fully IR-wired
    # (StructuralCandidate witness/projection/independent-recompute).  Route/DAG-incompatible by construction, so
    # search_routes/search_dags refuse it (a negative control the tests pin).  redox-displacement is excluded: its
    # multi-species edge has no _WITNESS_PROJECTION entry yet (0.7 decompile-lane ledger item).
    "certified-decompile-v07": TransformProviderRegistry(
        (HeterolyticScissionProvider(), RedoxHalfReactionProvider())
    ),
}


def _intersect_uses(registry: TransformProviderRegistry) -> frozenset:
    """The ProviderUses ALL of a registry's providers support -- the uses the profile as a whole can serve without
    tripping :func:`~smartchem.transform_provider.assert_registry_supports_use`.  Computed (not hand-declared) so it
    can never drift from the membership."""
    uses: "frozenset | None" = None
    for provider in registry.providers:
        uses = provider.supported_uses if uses is None else (uses & provider.supported_uses)
    return uses or frozenset()


#: which ProviderUse(s) each profile is coherent for -- lets the request layer give a clean "this profile is
#: decompile-only, it cannot serve a route search" refusal BEFORE the per-provider guard fires.  Derived, not typed.
PROFILE_USES: "dict[str, frozenset]" = {pid: _intersect_uses(reg) for pid, reg in ALGEBRA_PROFILES.items()}


class UnknownAlgebraProfileError(KeyError):
    """Raised when a profile ID is not in the closed :data:`ALGEBRA_PROFILES`.  A ``KeyError`` subclass (it IS a bad
    key), but the request/service layer catches it and returns a typed ``INVALID_INPUT`` refusal -- an unknown or
    tampered profile string must never dynamically import a provider nor crash a caller with a bare ``KeyError``."""


def algebra_profile_ids() -> tuple:
    """The closed set of known profile IDs, in declaration order."""
    return tuple(ALGEBRA_PROFILES)


def resolve_algebra_profile(profile_id: str) -> TransformProviderRegistry:
    """Map a profile ID to its exact, reviewed provider registry.  Closed lookup only -- no dynamic import.  Raises
    :class:`UnknownAlgebraProfileError` on an unknown ID (the caller turns that into a typed refusal)."""
    try:
        return ALGEBRA_PROFILES[profile_id]
    except KeyError:
        raise UnknownAlgebraProfileError(
            f"unknown transform-algebra profile {profile_id!r}; known profiles: {algebra_profile_ids()}"
        ) from None


def profile_supports_use(profile_id: str, use: ProviderUse) -> bool:
    """Whether every provider in ``profile_id`` supports ``use`` (i.e. the profile can serve that consumer topology).
    Raises :class:`UnknownAlgebraProfileError` for an unknown profile."""
    resolve_algebra_profile(profile_id)  # validate membership (raises on unknown)
    return use in PROFILE_USES[profile_id]
