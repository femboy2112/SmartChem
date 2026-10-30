"""ACTIVATOR-LEDGER-01 (#107) -- does a recognized reaction CLASS declare the stoichiometric ACTIVATOR it needs?

The gap this closes (W0.4 of the reaction-algebra coverage audit, Problem B). Reaction-TYPE recognition
(:mod:`~smartchem.experiment.reaction_type_oracle`) answers Problem A -- "is this a valid instance of class T?" --
as a pure function of the conserved molecules. It deliberately says nothing about the NON-conserved activation a
class needs to actually run: the Claisen condensation's recognizer (``_claisen_condensation``) vouches the
ester + ester -> 1,3-dicarbonyl skeleton while its own docstring defers the stoichiometric enolizing base to
"Problem B / #107". So a generated Claisen step whose conditions name no base ends REACTION_VOUCHED / disposition
CLEAN, and reads as poor-man-reachable on the affordability frontier -- a capability over-claim: a reaction that
cannot proceed without a strong base is presented as kitchen-runnable with nothing in the pot but the two esters.
This module is the missing organ: a typed ledger mapping a recognized class to the activator ROLE it requires, and
a route-level blocker that demotes an unmet requirement.

What it claims, and what it deliberately does NOT (the soundness law). This is a pure DEMOTER, so it is
no-false-VOUCH-safe BY CONSTRUCTION: it only ever ADDS a ``hard_blocker`` (disposition tier REAL_BUT_HARD -- a REAL
reaction that is merely out of reach without the reagent), and NEVER a ``fiction_blocker`` (NOT_A_REACTION) and
NEVER a feasibility/impossibility claim. Type-validity (Problem A) is untouched: a demoted step stays
REACTION_VOUCHED; only its poor-man REACHABILITY is withheld. The honest verdict is "type-valid; the activator this
class needs is not positively declared; NOT a claim the reaction is impossible or a claim of cost".

Because it can only demote, the only error it can commit is a FALSE-EXCLUDE (demoting a class that did not truly
need the activator, or whose real activator we failed to recognize). Two guards hold that in the safe region:

1. CLASS-KEYED, base-rate-safe (``REQUIRED_ACTIVATORS``). A requirement is attached ONLY to a positively recognized
   class with an UNAMBIGUOUS stoichiometric activation need -- today exactly ONE: the Claisen condensation, which
   always needs a stoichiometric enolizing base (alkoxide / metal hydride / metal amide) to form the enolate. The
   ~15 pericyclic/sigmatropic classes need no activator and get no entry; the activated-acyl-transfer (#110) and
   sulfonate-transfer (#111) classes are self-activating (the anhydride / sulfonyl halide carries the activation)
   and get no entry -- demanding one would false-EXCLUDE the paracetamol-via-Ac2O litmus route. The acyl
   condensation (Fischer esterification) is the base-rate TRAP -- "acid-catalysed" in most of the literature, yet
   the paracetamol and methyl-salicylate records deliberately declare no catalyst -- so it too gets NO entry.
   This is the lesson of base-rate-dependent fail-closed polarity (R51/R52): a fail-closed flip is sound only on a
   population where "unmet => genuinely blocked" holds, and it holds inside the Claisen population, not across every
   vouched step. [[base-rate-dependent-fail-closed-polarity]] [[a-capability-reward-must-be-gated-on-the-capability-model]]

2. SILENCE vs ABSENCE, resolved in favour of the CAPABILITY model, not the caller. ``envelope.catalysts == ()`` is
   the default for every generated step, so an undeclared catalyst is genuine silence -- and
   :mod:`~smartchem.experiment.catalyst_availability` (CATALYST-OBTAIN-01, a DIFFERENT and orthogonal gate: it asks
   whether a DECLARED catalyst is kitchen-OBTAINABLE, never whether a class NEEDS one) correctly treats that silence
   as neutral. Here the polarity is the opposite, and legitimately so: the requirement is a POSITIVE, type-level
   fact contributed by the recognized class, not by a caller string. For a REACHABILITY claim, silence about a
   known-necessary condition is not evidence the condition is met -- so an unmet requirement fails closed to
   REAL_BUT_HARD. (It is a recoverable demotion, not a refutation: declare a recognized enolizing base in the step
   conditions and the blocker lifts.) This is why the ledger is a SIBLING of catalyst_availability, not an
   extension of it: same machinery discipline, opposite and class-justified silence polarity.

How an activator ROLE is recognized (``classify_activator_roles``). Mirrors catalyst_availability's discipline
exactly: EXACT (case-normalized) name match against a curated positive whitelist, every lookup gated through
:func:`~smartchem.experiment.stock.case_fold_match_certifies` against the key's honest spelling (a string whose case
carries chemical meaning matches only its own spelling). There is deliberately NO substring/token scan over the
free-text name -- it is negation-blind ("base-free") and substring-catastrophic. Over-recognizing a base is the
UNSAFE direction here (it would wrongly CLEAR the requirement -> fail to demote -> a capability over-claim), so the
whitelist is conservative along BOTH failure axes: (strength) bases too weak to reliably enolize an ester alpha-C
(hydroxide, carbonate, the trialkylamines, amidine superbases) are EXCLUDED; (selectivity) nucleophilic
organometallics (alkyl/aryllithiums like n-BuLi, Grignards) are EXCLUDED too -- strong enough, but they ADD to the
carbonyl (1,2-addition) rather than cleanly enolize it, which is why the textbook enolate bases are the hindered,
non-nucleophilic amides (LDA/LiHMDS/KHMDS) and the alkoxides/hydrides, NEVER an alkyllithium (the d'Alembert #107
kill). Excluding any of these only costs a safe false-EXCLUDE; admitting it would risk the unsafe direction.

Scope (honest). The live consumer is the poor-man affordability frontier
(:func:`smartchem.service._affordability_frontier`), beside ``route_catalyst_blockers`` and
``route_reaction_type_blockers``; the loader (:meth:`CompilationResponse._check_frontier_coherence`) re-derives it
symmetrically from the identity-bound replay. (On the DEFAULT thin transport -- no replay, admission not required --
that re-derivation is skipped and a stripped blocker is not caught, the SAME inherited boundary
``route_catalyst_blockers``/``route_reaction_type_blockers`` ride; the demotion is verified end-to-end only when the
thick replay rides along.) It adds NO oracle recognizer (the 20-class count is unmoved), reads
NO conserved molecule into any recognition cache (recognition stays envelope-independent and content-deterministic),
and rides a channel (``hard_blockers``) that is excluded from both ``semantic_digest`` and ``result_digest`` -- a
pure MINOR feasibility-layer addition, exactly as #115 Claisen was logged (Problem A only, Problem B deferred here).
The thermo layer's acyl-condensation UNKNOWN guard (``feasibility.py`` ``_is_intermolecular_acyl_condensation``)
is a SEPARATE, complementary verdict (a DeltaG direction, keyed on bond topology) -- it is not duplicated here.
"""
from __future__ import annotations

import enum
import hashlib

from .reaction_type_oracle import _RECOGNIZERS, _step_equation, recognize_reaction_type
from .stock import case_fold_match_certifies

__all__ = [
    "ActivatorRole",
    "ROLE_PHRASE",
    "REQUIRED_ACTIVATORS",
    "classify_activator_roles",
    "step_activator_blockers",
    "route_activator_blockers",
]


class ActivatorRole(enum.Enum):
    """A non-conserved activation ROLE a reaction class may require of its declared conditions.

    Deliberately minimal: only the roles a currently-recognized class actually requires are defined. LEWIS_ACID
    (Friedel-Crafts) and BRONSTED_ACID (acid-catalysed condensation) remain obvious future members -- NOT
    pre-declared, because an unused role is dead surface and because each carries its own base-rate question that
    must be answered when (and only when) a class that needs it is recognized.
    """

    #: A stoichiometric base that forms a carbonyl enolate CLEANLY -- strong enough to deprotonate the alpha-C AND
    #: non-nucleophilic enough not to add to the carbonyl instead (alkoxide, metal hydride, hindered metal amide).
    #: The Claisen condensation's defining requirement.
    ENOLIZING_BASE = "enolizing_base"

    #: A transition-metal hydrogenation catalyst (CATALYTIC, not consumed) that activates H2 toward an unsaturated
    #: substrate -- Pd, Pt, Ni, Rh, Ru and their supported/oxide forms. The recognized ``hydrogenation`` class
    #: CONSUMES H2 (the recognizer checks "+H2 over the precursor"), and H2 + an unsaturated substrate does NOT
    #: react without such a catalyst -- a UNIVERSAL requirement of the H2-consuming pathway (the catalyst-free
    #: diimide / dissolving-metal reductions do not consume H2, so they are not this class). Distinct from the
    #: enolizing base: this role is CATALYTIC; its availability (every real one is an INDUSTRIAL metal) is the
    #: separate concern :mod:`~smartchem.experiment.catalyst_availability` owns -- this ledger imposes the
    #: REQUIREMENT, that module checks OBTAINABILITY of a declared one.
    TRANSITION_METAL_CATALYST = "transition_metal_catalyst"


#: Human-readable phrase per role, for the honest blocker reason text. Each phrase carries the role's ACTIVATION
#: NATURE (stoichiometric vs catalytic) so the blocker reason reads correctly for either.
ROLE_PHRASE: dict[ActivatorRole, str] = {
    ActivatorRole.ENOLIZING_BASE: "stoichiometric enolizing base (alkoxide / metal hydride / metal amide)",
    ActivatorRole.TRANSITION_METAL_CATALYST: "transition-metal hydrogenation catalyst (Pd / Pt / Ni / Rh / Ru)",
}


#: normalized reagent name -> its honest spelling, for the case-fold-certify guard (mirrors
#: catalyst_availability._CASE_EXACT_SPELLING). A key absent here is its own honest spelling (a fold fixed point).
#: Only keys whose case carries chemical meaning (a formula token) need an entry.
_CASE_EXACT_SPELLING: dict[str, str] = {
    "naoet": "NaOEt", "naome": "NaOMe", "kotbu": "KOtBu", "naotbu": "NaOtBu", "natbuo": "NaOtBu",
    "t-buok": "t-BuOK", "tbuok": "tBuOK",
    "nah": "NaH", "kh": "KH", "nanh2": "NaNH2", "lihmds": "LiHMDS", "nahmds": "NaHMDS", "khmds": "KHMDS",
    "lda": "LDA", "litmp": "LiTMP", "kda": "KDA",
    # hydrogenation-catalyst metal tokens (case carries the element identity)
    "pd": "Pd", "pt": "Pt", "ni": "Ni", "rh": "Rh", "ru": "Ru",
    "pd/c": "Pd/C", "pt/c": "Pt/C", "rh/c": "Rh/C", "ru/c": "Ru/C", "pd-c": "Pd-C",
    "pto2": "PtO2", "pd(oh)2": "Pd(OH)2",
    # multi-word catalyst names whose metal token is a formula (so the case must be certified, not defaulted)
    "raney ni": "Raney Ni", "raney-ni": "Raney-Ni", "pd black": "Pd black", "pt black": "Pt black",
}

#: Positive whitelist: normalized reagent names recognized as filling ``ENOLIZING_BASE``. Conservative -- every
#: entry is a base routinely used to generate an ester/ketone enolate for a Claisen; borderline-weak bases are
#: omitted on purpose (see the module docstring's classifier note). Grounded in reagent IDENTITY, not a token scan.
_ENOLIZING_BASE_NAMES: frozenset[str] = frozenset({
    # metal alkoxides
    "naoet", "naome", "kotbu", "naotbu", "natbuo", "t-buok", "tbuok",
    "sodium ethoxide", "sodium ethanolate", "sodium methoxide", "sodium methanolate",
    "potassium tert-butoxide", "potassium t-butoxide", "potassium tert butoxide",
    "sodium tert-butoxide", "sodium t-butoxide",
    # metal hydrides
    "nah", "kh", "sodium hydride", "potassium hydride",
    # metal amides (hindered, non-nucleophilic -- the textbook enolate bases)
    "lda", "lithium diisopropylamide", "nanh2", "sodium amide", "sodamide",
    "lihmds", "nahmds", "khmds",
    "lithium bis(trimethylsilyl)amide", "sodium bis(trimethylsilyl)amide", "potassium bis(trimethylsilyl)amide",
    "litmp", "lithium tetramethylpiperidide", "kda", "potassium diisopropylamide",
    # NOTE: alkyllithiums (n-BuLi, s-BuLi, t-BuLi, MeLi, PhLi, ...) are deliberately NOT here -- strong but
    # NUCLEOPHILIC, they 1,2-add to the ester/ketone instead of enolizing it, so clearing on them was a false-CLEAR
    # in the module's own-named unsafe direction (d'Alembert #107 kill). The regression is locked in the tests.
})

#: Positive whitelist: normalized reagent names recognized as filling ``TRANSITION_METAL_CATALYST`` -- the
#: transition-metal catalysts that activate H2 for a hydrogenation (Pd / Pt / Ni / Rh / Ru and their supported /
#: oxide / named forms). Grounded in reagent IDENTITY, exact-match (never a substring scan), case-certified like the
#: enolizing bases. Conservative: every entry is a textbook H2-hydrogenation catalyst. Omitting a valid one is the
#: SAFE direction -- a hydrogenation declaring an unlisted catalyst stays REAL_BUT_HARD (missing requirement), and
#: every real catalyst here is an INDUSTRIAL metal :mod:`catalyst_availability` demotes to REAL_BUT_HARD anyway, so
#: the clearing whitelist's precision changes the blocker REASON, never the kitchen disposition.
_HYDROGENATION_CATALYST_NAMES: frozenset[str] = frozenset({
    # palladium
    "pd", "pd/c", "pd-c", "pd/carbon", "palladium", "palladium on carbon", "palladium/carbon",
    "palladium on charcoal", "palladium black", "pd black",
    "pd(oh)2", "palladium hydroxide", "palladium hydroxide on carbon", "pearlman's catalyst", "pearlmans catalyst",
    # platinum
    "pt", "pt/c", "platinum", "platinum on carbon", "platinum black", "pt black",
    "pto2", "platinum oxide", "platinum dioxide", "adams' catalyst", "adams catalyst", "adam's catalyst",
    # nickel (Raney)
    "ni", "nickel", "raney nickel", "raney ni", "raney-nickel", "raney-ni", "nickel boride",
    # rhodium / ruthenium
    "rh", "rh/c", "rhodium", "rhodium on carbon", "rhodium on alumina", "wilkinson's catalyst", "wilkinsons catalyst",
    "ru", "ru/c", "ruthenium", "ruthenium on carbon",
})

#: normalized name -> the roles it positively fills. Keyed so a future role just adds a set.
_ROLE_NAMES: dict[ActivatorRole, frozenset[str]] = {
    ActivatorRole.ENOLIZING_BASE: _ENOLIZING_BASE_NAMES,
    ActivatorRole.TRANSITION_METAL_CATALYST: _HYDROGENATION_CATALYST_NAMES,
}


def _norm(name: str) -> str:
    return name.strip().casefold()


def classify_activator_roles(name: str) -> frozenset[ActivatorRole]:
    """The activation roles the reagent NAMED ``name`` is POSITIVELY recognized to fill, or an empty set.

    Fail-closed: a non-string, empty/blank name, or a name whose case does not certify against its honest spelling
    returns the empty set (unrecognized -> fills no role -> cannot clear any requirement). No substring scan.
    """
    if not isinstance(name, str):
        return frozenset()
    norm = _norm(name)
    if not norm:
        return frozenset()
    # A clear (non-demotion) is the unsafe direction, so a case-only hit counts only if it certifies against the
    # key's honest spelling -- mirrors catalyst_availability. "NaH" clears; "nAh" does not.
    if not case_fold_match_certifies(name, _CASE_EXACT_SPELLING.get(norm, norm)):
        return frozenset()
    roles = {role for role, names in _ROLE_NAMES.items() if norm in names}
    return frozenset(roles)


def _declared_roles(step) -> frozenset[ActivatorRole]:
    """Every activation role POSITIVELY declared in ``step``'s conditions (the ``catalysts`` free-reagent field --
    the same structured slot a declared Fischer catalyst rides). Fail-closed on any access/shape fault."""
    declared: set[ActivatorRole] = set()
    try:
        catalysts = tuple(step.envelope.catalysts)
    except Exception:
        return frozenset()
    for cat in catalysts:
        declared |= classify_activator_roles(cat)
    return frozenset(declared)


def _required_roles(reaction_class: str | None) -> frozenset[ActivatorRole]:
    """The activation roles a recognized ``reaction_class`` requires, or empty for an unrecognized/unlisted class."""
    if reaction_class is None:
        return frozenset()
    return REQUIRED_ACTIVATORS.get(reaction_class, frozenset())


def step_activator_blockers(step) -> tuple[str, ...]:
    """Ordered, deduplicated activator-requirement blockers for a single ``step``.

    Empty unless the step is positively recognized as a class in :data:`REQUIRED_ACTIVATORS` AND a required role is
    not positively filled by the step's declared conditions. Fail-closed and TOTAL: a recognition fault demotes the
    step to "unrecognized" (handled by ``route_reaction_type_blockers``, not here), never a spurious clear.
    """
    try:
        reaction_class = recognize_reaction_type(step)
    except Exception:
        return ()  # fail-closed: an unrecognized step is the oracle's demotion, not an activator question
    required = _required_roles(reaction_class)
    if not required:
        return ()
    declared = _declared_roles(step)
    missing = required - declared
    if not missing:
        return ()
    try:
        eq = _step_equation(step)
    except Exception:
        eq = "<unprintable step>"
    reasons = set()
    for role in missing:
        reasons.add(
            f"activator not declared: a {reaction_class} step requires a "
            f"{ROLE_PHRASE.get(role, role.value)}, none positively declared in the step conditions for "
            f"'{eq}' -- demoted REAL-BUT-HARD (Problem B activation; type-validity holds, NOT a claim of "
            f"impossibility or cost)"
        )
    return tuple(sorted(reasons))


def route_activator_blockers(route) -> tuple[str, ...]:
    """The poor-man ACTIVATOR blockers for ``route``: one deduplicated, ordered reason per step whose recognized
    class requires an activator its declared conditions do not supply.

    Mirrors :func:`~smartchem.experiment.reaction_type_oracle.route_reaction_type_blockers` and
    :func:`~smartchem.experiment.catalyst_availability.route_catalyst_blockers`: the reasons feed
    :func:`smartchem.service._affordability_frontier`'s ``hard_blockers`` (disposition REAL_BUT_HARD -- a real
    reaction merely out of reach), re-derived symmetrically on load. A 0-step route is vacuously unblocked.
    Fail-closed and total.
    """
    reasons: set[str] = set()
    try:
        steps = tuple(getattr(route, "steps", ()) or ())
    except TypeError:
        return ()  # a non-iterable ``steps`` is not a route we can read -- fail closed (honour "total")
    for step in steps:
        reasons.update(step_activator_blockers(step))
    return tuple(sorted(reasons))


#: The ledger. Keyed by the EXACT oracle display name (the stable wire identity -- never renamed; see the
#: import-time guard below). Conservative: an entry exists ONLY for a class with a UNIVERSAL, unambiguous
#: activation requirement -- the mechanism may generalize, but the DATA stays base-rate-safe.
#:
#: Mega-Round XI re-review (22 classes): the two new recognizers were reviewed against the guard's question --
#:   * ``hydrogenation``: this recognized class CONSUMES H2 (the recognizer requires exactly +H2 over the
#:     precursor), and H2 + an unsaturated substrate does NOT react without a transition-metal catalyst -- a
#:     UNIVERSAL requirement of the H2-consuming pathway (the catalyst-free diimide / dissolving-metal reductions
#:     do not consume H2, so they are structurally a DIFFERENT class, not this one). Added, TRANSITION_METAL_CATALYST.
#:     Not confused with stoichiometric consumption: the catalyst is catalytic; its OBTAINABILITY (every real one
#:     is INDUSTRIAL) is :mod:`catalyst_availability`'s separate gate, which composes with this requirement
#:     (undeclared -> REAL_BUT_HARD here; declared -> REAL_BUT_HARD there -- never a false CLEAN).
#:   * ``oxoacid ester condensation``: a dehydrative esterification of an oxoacid (nitric / phosphoric). Self-acidic
#:     like the acyl / ether condensations -- NO stoichiometric activator or catalyst is universally required, so
#:     NO entry (fabricating one from analogy is the banned move; feasibility stays the deferred Problem B UNKNOWN).
REQUIRED_ACTIVATORS: dict[str, frozenset[ActivatorRole]] = {
    "Claisen condensation (ester/ketone + ester/carbonate -> 1,3-dicarbonyl + alcohol)": frozenset(
        {ActivatorRole.ENOLIZING_BASE}
    ),
    "hydrogenation (partial bond-order edit, precursor + H2 -> saturated; one unsaturation reduced)": frozenset(
        {ActivatorRole.TRANSITION_METAL_CATALYST}
    ),
}


def _assert_ledger_keys_are_live_classes() -> None:
    """Fail-closed on a class RENAME: every ledger key MUST be a current oracle display name. If a recognizer is
    renamed without updating the ledger, the requirement would silently stop firing (a false-VOUCH-shaped
    regression). Raise at import instead -- loud, not silent."""
    live = {name for name, _predicate in _RECOGNIZERS}
    stale = set(REQUIRED_ACTIVATORS) - live
    if stale:
        raise AssertionError(
            "activator ledger references reaction class name(s) absent from the oracle registry -- a rename "
            f"silently disarmed a requirement: {sorted(stale)}"
        )


_assert_ledger_keys_are_live_classes()


#: A fingerprint of the FULL recognizer registry at the moment the ledger's base-rate scope was last reviewed
#: (sha256 of the sorted display names, first 16 hex; the count is carried for a legible failure message). The
#: rename guard above protects the PAST (a key that vanished); THIS protects the FUTURE (a class that APPEARED).
#: The base-rate argument -- "among the recognized classes, the Claisen condensation needs a stoichiometric
#: enolizing base and the hydrogenation needs a transition-metal catalyst" -- is a SNAPSHOT over exactly these 22
#: classes (Mega-Round XI re-review: +hydrogenation {TRANSITION_METAL_CATALYST}, +oxoacid ester {none}; see the
#: ledger table). The audit roadmap still plans aldol / Knoevenagel / Michael (enolizing base) and the metal
#: cross-couplings (catalyst): each WOULD need an entry when its recognizer lands, and a forgotten one is a
#: false-VOUCH on growth. If any recognizer is added / removed / renamed, this digest moves and import fails LOUD,
#: forcing a ledger re-decision rather than a silent gap.
_REVIEWED_CLASS_COUNT = 22
_REVIEWED_REGISTRY_DIGEST = "2a3bc34443129ff2"


def _assert_registry_unchanged_since_ledger_review() -> None:
    names = sorted(name for name, _predicate in _RECOGNIZERS)
    digest = hashlib.sha256("\n".join(names).encode()).hexdigest()[:16]
    if len(names) != _REVIEWED_CLASS_COUNT or digest != _REVIEWED_REGISTRY_DIGEST:
        raise AssertionError(
            f"the reaction-type recognizer registry changed since the activator ledger's base-rate scope was "
            f"last reviewed (reviewed {_REVIEWED_CLASS_COUNT} classes @ {_REVIEWED_REGISTRY_DIGEST}; now "
            f"{len(names)} @ {digest}). RE-REVIEW REQUIRED_ACTIVATORS: does any new or changed class require a "
            f"stoichiometric activator (an enolate-forming or catalysed class) that would otherwise read as "
            f"kitchen-runnable with nothing declared? Decide, then update _REVIEWED_REGISTRY_DIGEST/_COUNT."
        )


_assert_registry_unchanged_since_ledger_review()
