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

from .reaction_type_oracle import (
    _RECOGNIZERS,
    _step_equation,
    hydrogenation_reduces_imine_or_nitrile,
    recognize_reaction_type,
    sn2_feasibility_signature,
    sn2_oxygen_base_regime,
)
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
    #: substrate -- Pd, Pt, Ni, Rh, Ru and their supported / oxide forms. Required for a hydrogenation reducing a
    #: C=C / C=O / C#C unsaturation: for these substrate classes a transition metal is the supported H2-activation
    #: route and no GENERAL metal-free catalytic route is established (the catalyst-free diimide / dissolving-metal
    #: reductions do not consume H2, so they are a DIFFERENT class). NOT universal across all hydrogenations -- the
    #: scientifically false "only a transition metal can reduce this" (OPERATION XII 1A): a C=N / C#N reduction
    #: (imine / nitrile) is ALSO catalysed metal-free by a frustrated Lewis pair (Stephan et al. 2007), so that
    #: sub-case takes the broader :attr:`HYDROGEN_ACTIVATION_CATALYST` instead. The requirement is keyed on the
    #: reduced bond by :func:`_conditional_required_roles`, never blanket class-keyed. This role is CATALYTIC; its
    #: availability (every real one is an INDUSTRIAL metal) is :mod:`~smartchem.experiment.catalyst_availability`'s
    #: separate concern -- this ledger imposes the REQUIREMENT, that module checks OBTAINABILITY of a declared one.
    TRANSITION_METAL_CATALYST = "transition_metal_catalyst"

    #: A stoichiometric base that deprotonates a NEUTRAL oxygen nucleophile (an alcohol ``R-O-H``) to its competent
    #: conjugate nucleophile (the alkoxide ``R-O-``) -- without it the bare ``R-O-H`` does not displace a halide by
    #: SN2 (the Williamson ether synthesis forms the alkoxide IN SITU with NaOEt / NaH). The SAME strong bases that
    #: form a carbonyl enolate form an alkoxide a fortiori (an alcohol, pKa ~16-18, is MORE acidic than an ester
    #: alpha-C-H, ~25), so the clearing whitelist is the enolizing-base set reused. Required only for the
    #: NEUTRAL-oxygen SN2 sub-case whose nucleophile is an ALCOHOL (a salt alkoxide is already competent; a neutral
    #: amine / thiol runs base-free; an ACIDIC oxygen takes the milder sibling role below).
    DEPROTONATING_BASE = "deprotonating_base"

    #: A base to deprotonate an ACIDIC oxygen nucleophile -- a carboxylic acid (pKa ~5) or a phenol / enol (pKa ~10),
    #: an ``O-H`` on an sp2 carbon whose conjugate base is resonance-stabilised. The pKa-regime sibling of
    #: ``DEPROTONATING_BASE`` (the sp3 ALCOHOL case, pKa ~16): because the acidic ``O-H`` is far weaker, a MILD base
    #: (carbonate / hydroxide / a strong amine) forms the carboxylate / phenoxide, so a mild base CLEARS this -- the
    #: carboxylate/phenoxide O-alkylation runs with K2CO3 / NaOH / Et3N. The asymmetry is load-bearing: a strong
    #: (alkoxide/hydride/amide) base clears this a fortiori, but a mild base does NOT clear the alcohol case, so the
    #: two requirements never collapse. Required only for the neutral-ACIDIC-oxygen SN2 sub-case (keyed on the step).
    ACIDIC_PROTON_BASE = "acidic_proton_base"

    #: A catalyst that activates molecular H2 for a C=N / C#N reduction (imine / nitrile), fillable EITHER by a
    #: transition-metal catalyst OR by an experimentally-validated metal-free frustrated-Lewis-pair catalyst
    #: (e.g. B(C6F5)3; Chase, Welch, Jurca & Stephan, Angew. Chem. Int. Ed. 2007, 46, 8050, DOI
    #: 10.1002/anie.200702908 -- it hydrogenates imines and lone-pair-sequestered nitriles, but NOT aldehydes, so the
    #: C=O case keeps the TM-only :attr:`TRANSITION_METAL_CATALYST`). This replaces the scientifically false universal
    #: "only a transition metal can reduce this" for the nitrogen-unsaturation domain. A transition metal clears it a
    #: fortiori (its clearing whitelist is the TM set UNION the metal-free FLP set); a metal-free FLP does NOT clear
    #: the C=C / C=O requirement (it is absent from that role's set) -- the substrate-scoped asymmetry that keeps the
    #: relaxation a true-CLEAR, never a false one. Filled only by EXACT, case-certified reagent identity, never an
    #: arbitrary "catalyst" text label.
    HYDROGEN_ACTIVATION_CATALYST = "hydrogen_activation_catalyst"


#: Human-readable phrase per role, for the honest blocker reason text. Each phrase carries the role's ACTIVATION
#: NATURE (stoichiometric vs catalytic) so the blocker reason reads correctly for either.
ROLE_PHRASE: dict[ActivatorRole, str] = {
    ActivatorRole.ENOLIZING_BASE: "stoichiometric enolizing base (alkoxide / metal hydride / metal amide)",
    ActivatorRole.TRANSITION_METAL_CATALYST: "transition-metal hydrogenation catalyst (Pd / Pt / Ni / Rh / Ru)",
    ActivatorRole.DEPROTONATING_BASE: "stoichiometric base to form the alkoxide nucleophile (alkoxide / metal hydride / metal amide)",
    ActivatorRole.ACIDIC_PROTON_BASE: "stoichiometric base to deprotonate the acidic oxygen nucleophile -- a mild base suffices (carbonate / hydroxide / strong amine, or any alkoxide / hydride / amide)",
    ActivatorRole.HYDROGEN_ACTIVATION_CATALYST: "catalyst that activates molecular H2 for this C=N / C#N reduction -- a transition metal (Pd / Pt / Ni / Rh / Ru) OR an experimentally-validated metal-free frustrated-Lewis-pair catalyst (e.g. B(C6F5)3; Stephan et al. 2007)",
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
    # mild-base (acidic-oxygen clearing) tokens whose case is a formula or an acronym
    "k2co3": "K2CO3", "cs2co3": "Cs2CO3", "na2co3": "Na2CO3", "li2co3": "Li2CO3",
    "naoh": "NaOH", "koh": "KOH", "lioh": "LiOH", "ba(oh)2": "Ba(OH)2",
    "k3po4": "K3PO4", "et3n": "Et3N", "dipea": "DIPEA", "dbu": "DBU", "dbn": "DBN", "tmg": "TMG",
    # metal-free (frustrated-Lewis-pair) H2-activation catalyst tokens whose case is a formula / acronym (Stephan 2007)
    "b(c6f5)3": "B(C6F5)3", "bcf": "BCF",
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

#: Positive whitelist: normalized reagent names recognized as a MILD base competent to deprotonate an ACIDIC oxygen
#: nucleophile to its oxy-anion for an SN2 -- a carboxylic acid (pKa ~5) or a phenol (pKa ~10). The set is the
#: conjugate-acid-pKa >~10 bases, which deprotonate a phenol (and a carboxylic acid a fortiori); every entry is a
#: textbook base for a carboxylate / phenoxide O-alkylation. Deliberately conservative, because a CLEAR is the unsafe
#: direction: BICARBONATE (conjugate-acid pKa ~6.3 -- clears a carboxylic acid but NOT a phenol, and this one role
#: serves both acidic sub-cases so it must clear the weaker-acid member) and the WEAKER amines (pyridine ~5,
#: DABCO ~8.8, DMAP ~9.7, N-methylmorpholine ~7.4) are OMITTED -- a SAFE under-claim (a base-free such step stays
#: REAL_BUT_HARD; a carboxylate-only clearing with bicarbonate is lost), never a false CLEAR. Crucially these do NOT
#: appear in :data:`_ENOLIZING_BASE_NAMES`, so a mild base can never clear the sp3-ALCOHOL ``DEPROTONATING_BASE``
#: requirement (an alcohol, pKa ~16, needs the strong alkoxide/hydride/amide base) -- the pKa asymmetry that keeps
#: the relaxation sound. Grounded in reagent IDENTITY, exact-match, case-certified like the enolizing bases.
_ACIDIC_OXYGEN_BASE_NAMES: frozenset[str] = frozenset({
    # carbonates
    "k2co3", "potassium carbonate", "cs2co3", "cesium carbonate", "caesium carbonate",
    "na2co3", "sodium carbonate", "li2co3", "lithium carbonate",
    # hydroxides
    "naoh", "sodium hydroxide", "koh", "potassium hydroxide", "lioh", "lithium hydroxide",
    "ba(oh)2", "barium hydroxide",
    # phosphate
    "k3po4", "potassium phosphate", "tripotassium phosphate",
    # strong tertiary-amine / amidine / guanidine bases (conjugate-acid pKa >~10.5)
    "et3n", "triethylamine", "dipea", "diisopropylethylamine", "n,n-diisopropylethylamine",
    "n-ethyl-n,n-diisopropylamine", "hunig's base", "hunigs base", "hünig's base",
    "dbu", "1,8-diazabicyclo[5.4.0]undec-7-ene", "dbn", "1,5-diazabicyclo[4.3.0]non-5-ene",
    "tmg", "tetramethylguanidine", "1,1,3,3-tetramethylguanidine",
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

#: Positive whitelist: normalized reagent names recognized as the METAL-FREE half of ``HYDROGEN_ACTIVATION_CATALYST``
#: -- an experimentally-validated metal-free (frustrated-Lewis-pair) catalyst that activates molecular H2 for a
#: C=N / C#N reduction. Grounded in Chase, Welch, Jurca & Stephan, Angew. Chem. Int. Ed. 2007, 46, 8050 (DOI
#: 10.1002/anie.200702908) and its 2008 Chem. Commun. follow-up (B(C6F5)3 a direct imine-hydrogenation catalyst).
#: Exact-match / case-certified like the metal set; conservative -- anchored on the nameable, catalytically-competent
#: B(C6F5)3 and its synonyms. Omitting a valid metal-free catalyst is the SAFE direction (a C=N hydrogenation
#: declaring only an unlisted one stays REAL_BUT_HARD, recoverable). Kept DISJOINT from the transition-metal set: a
#: metal-free catalyst must never read AS a transition metal (that disjointness is the whole scientific point).
_METAL_FREE_H2_CATALYST_NAMES: frozenset[str] = frozenset({
    "b(c6f5)3", "bcf", "tris(pentafluorophenyl)borane", "tris(pentafluorophenyl)boron",
})

#: normalized name -> the roles it positively fills. Keyed so a future role just adds a set.
_ROLE_NAMES: dict[ActivatorRole, frozenset[str]] = {
    ActivatorRole.ENOLIZING_BASE: _ENOLIZING_BASE_NAMES,
    ActivatorRole.TRANSITION_METAL_CATALYST: _HYDROGENATION_CATALYST_NAMES,
    # The C=N / C#N hydrogenation's H2-activation requirement is filled by a transition metal (a fortiori) OR a
    # metal-free FLP catalyst (Stephan 2007): the UNION. So a declared Pd/C clears it too; the metal-free set stays
    # DISJOINT from the TM set, so a metal-free catalyst is never mistaken for a transition metal.
    ActivatorRole.HYDROGEN_ACTIVATION_CATALYST: _HYDROGENATION_CATALYST_NAMES | _METAL_FREE_H2_CATALYST_NAMES,
    # The alkoxide-forming bases that clear the DEPROTONATING_BASE role are exactly the enolizing bases (an alcohol
    # is more acidic than an ester alpha-C-H, so every enolizing base forms the alkoxide a fortiori). Reused, not
    # re-listed, so the two sets never drift. Conservative: weaker bases (hydroxide/carbonate) are omitted -- a
    # SAFE false-EXCLUDE, never a false CLEAR.
    ActivatorRole.DEPROTONATING_BASE: _ENOLIZING_BASE_NAMES,
    # The ACIDIC-oxygen SN2 (carboxylic acid / phenol) clears with a MILD base; the STRONG enolizing/alkoxide bases
    # clear it a fortiori, so the clearing set is the mild whitelist UNION the strong set. The reverse does NOT hold
    # (a mild base is absent from _ENOLIZING_BASE_NAMES, so it cannot clear the sp3-ALCOHOL DEPROTONATING_BASE
    # requirement) -- the pKa asymmetry that makes the relaxation safe in the unsafe (clear) direction.
    ActivatorRole.ACIDIC_PROTON_BASE: _ACIDIC_OXYGEN_BASE_NAMES | _ENOLIZING_BASE_NAMES,
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


def _conditional_required_roles(step, reaction_class: str | None) -> frozenset[ActivatorRole]:
    """Activation roles a recognized class requires CONDITIONALLY on the STEP's content -- requirements that hold
    for a sub-population of the class, not universally, so they do not belong in the class-keyed
    :data:`REQUIRED_ACTIVATORS` (a blanket entry there would false-EXCLUDE the rest of the class).

    Today exactly one class: an SN2 whose nucleophile is a NEUTRAL (protonated) OXYGEN nucleophile (coproduct
    ``H-X``). Its competent nucleophile, the oxy-ANION, does NOT exist until a stoichiometric base forms it in situ,
    so the bare ``R-O-H + R'-X`` mixture is not kitchen-runnable -- but which STRENGTH of base is the defining need
    depends on the oxygen's pKa, so the requirement splits by :func:`sn2_oxygen_base_regime`:

    * an ALCOHOL ``R-O-H`` (hydroxyl on an sp3 carbon, pKa ~16) needs a STRONG base to form the alkoxide -- the
      Williamson situation, like the Claisen (a non-reactant base forms the nucleophile): ``DEPROTONATING_BASE``;
    * an ACIDIC oxygen -- a carboxylic acid (pKa ~5) or a phenol / enol (pKa ~10), hydroxyl on an sp2 carbon -- needs
      only a MILD base to form the carboxylate / phenoxide (the K2CO3 / NaOH / Et3N ester- and aryl-ether syntheses):
      the milder ``ACIDIC_PROTON_BASE`` (still a requirement, so a base-free such step is still demoted REAL_BUT_HARD;
      only the clearing set is wider). Fail-closed: an unclassifiable oxygen takes the conservative strong requirement.

    Excluded, each a CONSCIOUS boundary (an adversarial re-review set them): a metal-SALT oxy-nucleophile
    (``signature.is_neutral == False``) is already deprotonated and competent; a neutral AMINE (N) is itself a
    competent nucleophile and runs base-free; a neutral THIOL (S) is nucleophilic enough to react base-free, so
    demoting it would false-EXCLUDE real chemistry. Fail-closed: any fault -> empty.

    The SECOND conditional class is HYDROGENATION (OPERATION XII 1A). Every hydrogenation needs an H2-activation
    catalyst, but the SUPPORTED fulfillment depends on the reduced bond, so a blanket class-keyed
    ``TRANSITION_METAL_CATALYST`` would be the scientifically false universal "only a transition metal can do this":
    a C=N / C#N reduction (imine / nitrile) is ALSO catalysed metal-free by a frustrated Lewis pair (Stephan et al.,
    Angew. Chem. Int. Ed. 2007, 46, 8050), so it takes the broader ``HYDROGEN_ACTIVATION_CATALYST`` (a transition
    metal OR a metal-free FLP clears it). A C=C / C=O / C#C reduction has no established metal-free catalytic route
    (aldehydes do NOT react under FLP catalysis -- Stephan 2007), so it keeps the stricter ``TRANSITION_METAL_CATALYST``
    (TM only). The imine / nitrile domain is confirmed by :func:`hydrogenation_reduces_imine_or_nitrile`, which reads
    the reduced bond's ENVIRONMENT -- NOT merely its element pair: a C=N decorated as an oxime (C=N-O), a hydrazone
    (C=N-N), an amidine / guanidine (C bearing a 2nd N) or an isocyanate / carbodiimide cumulene also reduces through
    a C=N yet is NOT a metal-free-FLP substrate (evil-morty, OPERATION XII 1A), so each is EXCLUDED and keeps TM-only.
    Fail-closed to the STRICTER (TM-only) requirement whenever a genuine imine / nitrile cannot be POSITIVELY confirmed
    -- never grant the wider metal-free clearing set otherwise (the unsafe direction is a false-CLEAR)."""
    if not reaction_class:
        return frozenset()
    if "SN2 substitution" in reaction_class:
        try:
            signature = sn2_feasibility_signature(step)
        except Exception:
            return frozenset()
        if signature is not None and signature[0] == "O" and signature[1]:
            try:
                regime = sn2_oxygen_base_regime(step)
            except Exception:
                regime = "strong"  # fail-closed to the conservative strong-base requirement
            if regime == "mild":
                return frozenset({ActivatorRole.ACIDIC_PROTON_BASE})
            return frozenset({ActivatorRole.DEPROTONATING_BASE})
        return frozenset()
    if _HYDROGENATION_CLASS_ANCHOR in reaction_class:
        if hydrogenation_reduces_imine_or_nitrile(step):
            return frozenset({ActivatorRole.HYDROGEN_ACTIVATION_CATALYST})
        return frozenset({ActivatorRole.TRANSITION_METAL_CATALYST})  # not a plain imine/nitrile: TM-only, fail-closed
    return frozenset()


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
    required = _required_roles(reaction_class) | _conditional_required_roles(step, reaction_class)
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


#: The CLASS-KEYED ledger. Keyed by the EXACT oracle display name (the stable wire identity -- never renamed; see the
#: import-time guard below). Conservative: an entry exists ONLY for a class with a UNIVERSAL, unambiguous activation
#: requirement that holds for EVERY instance -- today exactly the Claisen condensation. A requirement that holds only
#: for a SUB-population (SN2 with a neutral-oxygen nucleophile; hydrogenation, whose H2-activation fulfillment is
#: substrate-scoped) rides :func:`_conditional_required_roles` instead, where it keys on the step without
#: false-EXCLUDING the rest of the class. The mechanism may generalize, but the DATA stays base-rate-safe.
#:
#: Mega-Round XI re-review (22 classes): the two new recognizers were reviewed against the guard's question --
#:   * ``hydrogenation``: this recognized class CONSUMES H2 (the recognizer requires exactly +H2 over the
#:     precursor), and H2 + an unsaturated substrate does NOT react without a catalyst that activates H2. First
#:     reviewed (Mega-Round XI) as a class-keyed {TRANSITION_METAL_CATALYST}; CORRECTED to STEP-CONDITIONAL
#:     (OPERATION XII 1A) because that was the scientifically false universal "only a transition metal can reduce
#:     this" -- a C=N / C#N reduction (imine / nitrile) is catalysed metal-free by a frustrated Lewis pair (Stephan
#:     et al., Angew. Chem. Int. Ed. 2007, 46, 8050). So the requirement now rides :func:`_conditional_required_roles`,
#:     keyed on the reduced bond: C=N / C#N -> HYDROGEN_ACTIVATION_CATALYST (TM or metal-free FLP); C=C / C=O / C#C ->
#:     the stricter TRANSITION_METAL_CATALYST (TM only; aldehydes do not react metal-free -- Stephan 2007). The
#:     catalyst-free diimide / dissolving-metal reductions do not consume H2, so they are a DIFFERENT class. Catalyst
#:     OBTAINABILITY (every real catalyst is specialized / INDUSTRIAL) is :mod:`catalyst_availability`'s separate
#:     gate, which composes with this requirement (undeclared -> REAL_BUT_HARD here; declared -> REAL_BUT_HARD there
#:     -- never a false CLEAN).
#:   * ``oxoacid ester condensation``: a dehydrative esterification of an oxoacid (nitric / phosphoric). Self-acidic
#:     like the acyl / ether condensations -- NO stoichiometric activator or catalyst is universally required, so
#:     NO entry (fabricating one from analogy is the banned move; feasibility stays the deferred Problem B UNKNOWN).
#:
#: 1.5 consolidation re-review (24 classes): the integration merged #112 SN2 substitution and #119 imine
#: condensation on top of the 22. Both reviewed against the guard's question and given NO entry:
#:   * ``SN2 substitution``: the recognizer vouches BOTH a metal-salt nucleophile (``R-Nu-M``) AND a NEUTRAL
#:     protonated one (``R-Nu-H``, coproduct H-X). A blanket "no entry" was KILLED by adversarial re-review
#:     (evil-morty): a NEUTRAL OXYGEN nucleophile (an alcohol ``R-O-H``) is NOT a competent SN2 nucleophile --
#:     ``EtOH + EtBr`` bare gives no ether; the Williamson synthesis forms the alkoxide IN SITU with a
#:     stoichiometric base (NaOEt / NaH). That is the Claisen situation, not the salt one. So SN2 takes a
#:     CONDITIONAL requirement via :func:`_conditional_required_roles` (keyed on the step's nucleophile, NOT a
#:     class-keyed REQUIRED_ACTIVATORS entry that would false-EXCLUDE the rest of the class): a neutral-oxygen SN2
#:     with no declared base demotes to REAL_BUT_HARD, recoverable. The base STRENGTH is pKa-regime-aware
#:     (:func:`sn2_oxygen_base_regime`): an ALCOHOL (sp3 ``C-O-H``, pKa ~16) needs a STRONG base
#:     (DEPROTONATING_BASE, cleared by the alkoxide/hydride/amide set); an ACIDIC oxygen -- a carboxylic acid
#:     (pKa ~5) or a phenol/enol (pKa ~10), an sp2 ``C-O-H`` -- needs only a MILD base (ACIDIC_PROTON_BASE, cleared
#:     by carbonate/hydroxide/strong-amine, or any strong base a fortiori). The split closes a SAFE under-claim
#:     evil-morty found (acidic-O routes were being forced onto a strong base) without ever letting a mild base
#:     clear the alcohol case -- the pKa asymmetry is load-bearing. No requirement for a metal-SALT oxy-nucleophile
#:     (already deprotonated), a neutral AMINE (competent base-free), or a neutral THIOL (nucleophilic enough
#:     base-free -- demoting it would false-EXCLUDE real chemistry).
#:   * ``imine condensation``: a dehydrative carbonyl + amine condensation (coproduct water). A Bronsted acid
#:     ACCELERATES the dehydration but is not a feasibility gate -- the reaction reaches equilibrium uncatalysed,
#:     driven by water removal -- so it sits in the SAME self-acidic condensation population as the acyl / ether /
#:     oxoacid ester classes that get no entry. A BRONSTED_ACID requirement here is precisely the banned base-rate
#:     trap (acid-catalysed in the literature, run catalyst-free in the records). NO entry.
#: Substring anchors identifying the classes whose activator requirement is STEP-CONDITIONAL (handled in
#: :func:`_conditional_required_roles`, not this class-keyed dict). Guarded live below alongside the ledger keys: a
#: renamed class would otherwise silently disarm its conditional requirement (a false-VOUCH-shaped regression).
_HYDROGENATION_CLASS_ANCHOR = "hydrogenation (partial bond-order edit"
_CONDITIONAL_CLASS_ANCHORS = ("SN2 substitution", _HYDROGENATION_CLASS_ANCHOR)

REQUIRED_ACTIVATORS: dict[str, frozenset[ActivatorRole]] = {
    "Claisen condensation (ester/ketone + ester/carbonate -> 1,3-dicarbonyl + alcohol)": frozenset(
        {ActivatorRole.ENOLIZING_BASE}
    ),
}


def _assert_ledger_keys_are_live_classes() -> None:
    """Fail-closed on a class RENAME: every class-keyed ledger key AND every step-conditional class anchor MUST match
    a current oracle display name. If a recognizer is renamed without updating the ledger, the requirement would
    silently stop firing (a false-VOUCH-shaped regression). Raise at import instead -- loud, not silent."""
    live = {name for name, _predicate in _RECOGNIZERS}
    stale = set(REQUIRED_ACTIVATORS) - live
    if stale:
        raise AssertionError(
            "activator ledger references reaction class name(s) absent from the oracle registry -- a rename "
            f"silently disarmed a requirement: {sorted(stale)}"
        )
    # The step-CONDITIONAL requirements (:func:`_conditional_required_roles`) key on a SUBSTRING anchor of a live
    # class display name, not a full ledger key, so the rename guard above cannot see them. Guard them here too: a
    # renamed SN2 or hydrogenation class would silently stop requiring its base / H2-activation catalyst.
    for anchor in _CONDITIONAL_CLASS_ANCHORS:
        if not any(anchor in name for name in live):
            raise AssertionError(
                f"activator ledger conditional-requirement anchor {anchor!r} matches no current oracle class -- a "
                f"rename silently disarmed a step-conditional activator requirement"
            )


_assert_ledger_keys_are_live_classes()


#: A fingerprint of the FULL recognizer registry at the moment the ledger's base-rate scope was last reviewed
#: (sha256 of the sorted display names, first 16 hex; the count is carried for a legible failure message). The
#: rename guard above protects the PAST (a key that vanished); THIS protects the FUTURE (a class that APPEARED).
#: The base-rate argument -- "among the recognized classes, the Claisen condensation always needs a stoichiometric
#: enolizing base; the hydrogenation and the neutral-oxygen SN2 need a step-conditional activator" -- is a SNAPSHOT
#: over exactly these 24 classes (Mega-Round XI reviewed hydrogenation + oxoacid ester; 1.5 consolidation reviewed
#: SN2 + imine condensation; OPERATION XII 1A moved hydrogenation from a class-keyed TRANSITION_METAL_CATALYST to the
#: step-conditional H2-activation split -- see the ledger table and :func:`_conditional_required_roles`). The audit
#: roadmap still plans aldol /
#: Knoevenagel / Michael (enolizing base) and the metal
#: cross-couplings (catalyst): each WOULD need an entry when its recognizer lands, and a forgotten one is a
#: false-VOUCH on growth. If any recognizer is added / removed / renamed, this digest moves and import fails LOUD,
#: forcing a ledger re-decision rather than a silent gap.
_REVIEWED_CLASS_COUNT = 24
_REVIEWED_REGISTRY_DIGEST = "0dfb95140ad927ef"


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
