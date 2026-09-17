"""REACTION-TYPE-ORACLE-01 (R56) -- does a derived step match a KNOWN reaction TYPE at all?

The gap this closes (the R55 consumer, proven). The compiler DERIVES reactions by capped-scission graph
surgery that conserves molecular FORMULA, not chemical feasibility, so the search OVER-GENERATES
formula-balanced-but-FAKE steps -- steps that are *no real reaction at all* (PROBLEM A: reaction-TYPE fiction,
distinct from PROBLEM B, substrate feasibility). R55 measured that the production affordability frontier
(:func:`smartchem.service._affordability_frontier`) ships the majority of its routes as such fictions with EMPTY
``hard_blockers`` -- e.g. ``isopropanol + ethyl acetate -> isopentyl acetate + water`` (gluing two alkyl
fragments with a new C-C bond and calling the departing atoms "water"), presented as a ~4.5c fully-commodity
route. This module is the demoter that sinks them.

Why this is NOT the R49-R55 escape #7 (a different KIND, not a bounded-radius real/fake discriminator).
R49-R55 all tried to CARRY an unbounded property (feasibility, then type-validity) with a bounded-radius local
feature via a decision function ``valid = g(f(step))`` -- and every one collided, because a bounded feature is
shared by some real and some fake step (the R55 theorem). This module makes a strictly WEAKER, different claim: a
POSITIVE WHITELIST of attested reaction-class recognizers. A step is VOUCHED iff it POSITIVELY matches a known
reaction class; otherwise it is FAIL-CLOSED demoted as *"unrecognized reaction type"* -- which is NOT the claim
"proven fake", it is honest non-recognition. The unbounded-ness therefore surfaces as COVERAGE LOSS (a real but
unregistered reaction is demoted-as-unrecognized), NEVER as a false-VOUCH. This is the R53/R54 "invert to a
positive safe-set whitelist" prescription, now over reaction-TYPE TRANSFORMATIONS (Problem A) rather than the
substrate ELEMENT census R54 deferred (Problem B).

The per-recognizer admission law (the load-bearing soundness discipline, from the R56 design gate).
Each recognizer in :data:`_RECOGNIZERS` must fire ONLY when the net functional-group change is IDENTITY-unique to
one real reaction class WITHIN a tight elementary shape -- so that formula conservation FORCES a match to be a
genuine instance of that class (a "conservation-lock" proof). The shipped acyl-condensation recognizer passes:
within the elementary intermolecular shape (2 non-water reactants -> 1 non-water product, water expelled) a new
ester/amide/thioester carbonyl cannot be minted de novo without an extra oxidation product the shape excludes, so
a fired step is FORCED onto a real acyl transfer (R48-hardened; verified 0 false-VOUCH over all 29 production
frontier routes at the R56 gate). The dehydrative-etherification recognizer passes too: within the same shape,
a net-formed dialkyl (sp3 C-O-C) ether with a net-consumed sp3 alcohol and water expelled is the signature of a
real etherification -- a formula-conserving fake cannot share it (peroxide coupling consumes no alcohol; the
aryl-ether fake forms no dialkyl ether). As of R58 the elementary single-condensation requirement is CHECKED on the
reaction-centre span rather than assumed from the config (see the LOCALITY boundary below), which is what excludes
the bundled fictions -- so the R57 whole-molecule "no reactant ether" blacklist clause is retired for
centre-carrying steps.
A GENERAL "new C-N bond" recognizer FAILS this admission gate -- it fires on
both caffeine N-methylation (real, must-vouch) AND aromatic phenol->aniline amination (fake, must-not-vouch), the
R55 theorem one alphabet over -- so a general recognizer is deliberately NOT shipped. R60 recovers the R45 caffeine
genericity win the honest way the R56 record prescribed: a CLASS-SPECIFIC conservation-locked N-methylation
recognizer (:func:`_n_methylation`), NOT a bounded-radius patch. Its lock: the two collide on a BYTE-IDENTICAL
reaction centre, so the span check cannot separate them; the whole-molecule census does -- the consumed alcohol
must be methanol-specific (literally CH3-OH, which excludes aromatic phenol-O and every longer alcohol, so general
N-alkylation is not admitted) and the formed N-methyl amine must sit on a non-carbonyl N (excludes the aryl-
amination fake and stays disjoint from the acyl/amidation class). Do NOT add a recognizer without its
conservation-lock proof.

What a VOUCH means, and what it deliberately does NOT (the disposition law -- type-validity != feasibility).
A VOUCH says ONLY "a mechanism of this reaction TYPE exists" (Problem A). It is NOT a feasibility claim (Problem B,
still deferred): the acyl recognizer VOUCHES the direct free-acid esterification/amidation class that
:func:`smartchem.experiment.feasibility.feasibility_of_step` itself FAILS CLOSED on (the aqueous salt-sink / the
activation requirement -- the R47 domain guard). Both are correct at their own scope, so this demoter only ever
ADDS a blocker; it NEVER removes one, and it must not be read as lifting the feasibility guard. The reason strings
say "unrecognized reaction type ... NOT a claim of cost or feasibility" so the disposition is not misread.

How it wires in (the proven sibling pattern). :func:`route_reaction_type_blockers` mirrors
:func:`smartchem.experiment.catalyst_availability.route_catalyst_blockers` exactly: one deduplicated reason string
per unrecognized step, fed into :func:`smartchem.service._affordability_frontier`'s ``hard_blockers`` (section-10.4
G6: a hard blocker dominates cost), so a route with any unrecognized step sinks on the affordability frontier. It
runs DOWNSTREAM of ``ranked``; it never touches ``_score_tuple``.

Boundaries carried as documented debt (R56 acyl + R57 etherification + R60 N-methylation scope, per the gates).
* THREE CLASSES -- acyl condensation (R56), dehydrative etherification (R57), and dehydrative N-methylation (R60),
  each with its own conservation-lock proof. Other real condensations (Friedel-Crafts, Kolbe-Schmitt, Claisen) and
  N-alkylation BEYOND methylation (by any longer alcohol -- the methanol clause admits only CH3-OH) are
  demoted-as-unrecognized: honest coverage loss, NOT false-VOUCH. Each is a future round behind its own gate.
* LOCALITY (R57 debt, CLOSED by R58 span reading) -- a whole-molecule census is non-local, so R56/R57 borrowed
  the generator's k=1 single-cut invariant (``max_reactant_cuts = 1``, the production default). R58 distils the
  reaction-centre span the generator already computes (``CappedScission.cut``/``.caps``) into a coordinate-free
  :class:`~smartchem.reaction_center.ReactionCenter` carried on the step, and both recognizers now CHECK the centre
  is a single connected elementary condensation (:meth:`ReactionCenter.is_elementary_condensation`) rather than
  trusting the config. This makes the k=1 assumption a structural FACT (config-robust: 48 reachable k=2 acyl bundles
  and the k=2 ether bundles that forge the elementary net signature are demoted by their non-elementary spans), and
  the span-local ether check retires the R57 clause (iii) blacklist -- RECOVERING 40 production-reachable genuine
  etherifications whose reactant contains an unrelated ether (``methanol + 2-methoxyethanol ->
  1,2-dimethoxyethane + water``). A step lacking a centre (hand-built / non-scission transform) falls back to the
  whole-molecule census, sound at the production k=1 config; centre-carrying live and replayed steps read
  identically (the centre round-trips through the replay payload).
* DISPOSITION FLATTENING -- the fiction blocker shares the ``hard_blockers`` tuple with catalyst/section-11
  blockers, so a "real reaction, needs industrial catalyst" route and a "not a reaction at all" route are both
  G6-sunk equally (the partial order "real-but-hard strictly outranks not-a-reaction" is lost). A distinct
  disposition channel is a named follow-up; the honest reason vocabulary is the minimal correct thing this round.
* FAIL-CLOSED TOTALITY -- the affordability-frontier build is OUTSIDE the compile path's ScissionError guard, so a
  recognizer that raised would crash compilation OR (worse, if wrapped wrongly) skip a step (a silent vouch).
  Every recognizer call here is guarded so an exception is treated as "did NOT fire" -- an error can only make a
  step LESS recognized (more likely demoted), NEVER spuriously vouched.
"""
from __future__ import annotations

from ..decompiler import Formula

__all__ = [
    "recognize_reaction_type",
    "route_reaction_type_blockers",
]


def _acyl_condensation(step) -> bool:
    """Recognizer: an intermolecular acyl condensation (esterification / amidation / thioesterification), R58.

    Class identity is the R48-hardened whole-molecule predicate (a free acid net-consumed, an acyl carbonyl
    net-formed within the elementary intermolecular shape).  Its fail-OPEN use as a feasibility DOMAIN GUARD in
    :mod:`smartchem.experiment.feasibility` (firing means "refuse to vouch the derived DeltaG") is a DIFFERENT job
    than this module's fail-CLOSED type VOUCH; the shared thing is only the detector, which this module leaves
    untouched.

    R58 span-local elementarity.  When the step carries a reaction centre (:attr:`ExperimentStep.reaction_center`,
    present for every generator-derived step), a VOUCH additionally requires that centre to be a SINGLE, connected,
    elementary dehydrative condensation onto an ``{O, N, S}`` nucleophile (ester/amide/thioester) --
    :meth:`~smartchem.reaction_center.ReactionCenter.is_elementary_condensation`.  This turns the borrowed k=1
    single-cut assumption into a CHECKED structural fact: a bundled multi-cut step that forges the same net acyl
    signature (48 reachable k=2 examples were measured) forms/breaks extra bonds or splits into >1 component, so it
    is demoted.  A step without a centre (hand-built, or a non-scission transform) falls back to the whole-molecule
    predicate alone (sound at the production k=1 config).  This is verdict-IDENTICAL to R57 at k=1 (measured 0
    recovered / 0 lost) -- config-robustness hardening, not a k=1 behaviour change."""
    from .feasibility import _is_intermolecular_acyl_condensation
    if not _is_intermolecular_acyl_condensation(step):
        return False
    center = getattr(step, "reaction_center", None)
    if center is None:
        return True  # span absent: the whole-molecule predicate stands (sound at the production k=1 config)
    return center.is_elementary_condensation(("O", "N", "S"))


def _etherification(step) -> bool:
    """Recognizer: an intermolecular DEHYDRATIVE etherification (2 R-OH -> R-O-R + water), R58 span-local.

    Class identity is the whole-molecule shape+net census (:func:`~smartchem.experiment.feasibility.
    _ether_shape_and_net_change`): within the elementary intermolecular shape, a dialkyl (sp3 C-O-C) ether is
    net-FORMED and an sp3 alcohol net-CONSUMED (this excludes the aryl-ether fake, which forms no dialkyl ether, and
    the peroxide coupling, which consumes no alcohol; and it excludes esterification, whose formed C-O is an
    ester-O with a carbonyl neighbour, not a dialkyl ether -- so ether and ester share a centre signature but the
    census separates them).

    R58 REPLACES the R57 whole-molecule clause (iii) ("no ether among the reactants") with a span-LOCAL check.
    When the step carries a reaction centre, a VOUCH requires that centre to be a single, connected, elementary
    dehydrative condensation onto oxygen (:meth:`~smartchem.reaction_center.ReactionCenter.is_elementary_condensation`
    with ``("O",)``).  Clause (iii) was a non-local blacklist that FALSE-DEMOTED a genuine etherification whose
    reactant merely CONTAINS an unrelated ether (``methanol + 2-methoxyethanol -> 1,2-dimethoxyethane + water``, a
    production k=1 miss); the span reads the actual centre, so those 40 reachable steps are RECOVERED while the
    bundled fakes (which have a non-elementary span) stay demoted.  A step without a centre falls back to the R57
    predicate (clause iii intact), sound at k=1."""
    from .feasibility import _ether_shape_and_net_change, _is_intermolecular_etherification
    center = getattr(step, "reaction_center", None)
    if center is None:
        return _is_intermolecular_etherification(step)  # span absent: R57 predicate (clause iii) stands
    return _ether_shape_and_net_change(step) and center.is_elementary_condensation(("O",))


def _n_methylation(step) -> bool:
    """Recognizer: an intermolecular dehydrative N-METHYLATION (R2N-H + CH3-OH -> R2N-CH3 + water), R60.

    The THIRD conservation-locked class, and the one the R56 record explicitly deferred: a GENERAL "new C-N bond"
    recognizer collides -- it fires on both real caffeine N-methylation and the fake phenol->aniline aryl
    amination, the R55 theorem one alphabet over.  The two even share a BYTE-IDENTICAL reaction centre
    (``formed={C-N, O-H}``, ``broken={C-O, N-H}``, one component), so the span check alone (mirroring
    :func:`_etherification`, :meth:`~smartchem.reaction_center.ReactionCenter.is_elementary_condensation` with
    ``("N",)``) does NOT lock.  The census supplies what the span cannot: the whole-molecule predicate
    (:func:`~smartchem.experiment.feasibility._methylation_shape_and_net_change`) requires a METHANOL-specific
    alcohol net-consumed (literally CH3-OH -- excludes phenol-O and every longer alcohol, so general N-alkylation
    is not admitted) and an N-methyl amine net-formed on a non-carbonyl N (excludes the aryl-amination fake and
    stays disjoint from the acyl/amidation class).

    FAIL-CLOSED on an absent centre (the gate finding).  Unlike acyl/ether, this recognizer does NOT fall back to
    the whole-molecule census when a step carries no reaction centre -- it BLOCKS.  The census is non-local, and a
    centre-less homologation forges the net signature: ``N-methylformamide + methanol -> CNCC=O + water`` inserts
    methanol's carbon as a CH2 and MIGRATES the carbonyl off the N, unmasking the amide's PRE-EXISTING methyl, so
    ``_n_methyl_amine_count`` reads a spurious 0->1 rise with no methyl actually transferred.  The R58 span closes
    exactly this ([[a-whole-set-count-classifier-is-fooled-by-non-locality]]), so a VOUCH REQUIRES a readable,
    elementary N-centre.  A centre-less step is honest coverage loss (false-UNRECOGNIZED, safe), never a census-only
    vouch (false-VOUCH, catastrophic) -- the arch's declared-but-unrecognizable-input-must-BLOCK polarity."""
    from .feasibility import _methylation_shape_and_net_change
    center = getattr(step, "reaction_center", None)
    if center is None:
        return False  # fail-closed: no readable centre -> the non-local census cannot vouch alone (gate finding)
    return _methylation_shape_and_net_change(step) and center.is_elementary_condensation(("N",))


#: The positive whitelist of attested reaction-class recognizers: ``(class_name, predicate)``. A step is
#: recognized iff SOME predicate fires. Every entry MUST carry a conservation-lock proof (see the module
#: docstring); a general bounded-radius recognizer is exactly escape #7 and is not admitted. R56 shipped acyl;
#: R57 added dehydrative etherification; R60 adds dehydrative N-methylation (each a conservation-locked class,
#: NOT a bounded-radius patch).
_RECOGNIZERS: tuple[tuple[str, "object"], ...] = (
    ("acyl condensation (esterification/amidation)", _acyl_condensation),
    ("etherification (dehydrative, R-OH + R'-OH -> ether + water)", _etherification),
    ("N-methylation (dehydrative, R2N-H + CH3-OH -> R2N-CH3 + water)", _n_methylation),
)


def _fstr(molecule) -> str:
    return repr(Formula.of(molecule.formula, molecule.charge))


def _step_equation(step) -> str:
    lhs = " + ".join(sorted(_fstr(m) for m in step.reactants))
    rhs = " + ".join(sorted(_fstr(m) for m in step.products))
    return f"{lhs} -> {rhs}"


def recognize_reaction_type(step) -> str | None:
    """The name of the attested reaction CLASS ``step`` matches, or ``None`` if it matches none.

    TOTAL + FAIL-CLOSED: a recognizer that raises is treated as abstaining (``continue``), never a spurious match,
    so an internal error can only make a step LESS recognized (more likely demoted), NEVER spuriously vouched. A
    ``None`` return is "unrecognized reaction type", which :func:`route_reaction_type_blockers` turns into a
    demotion -- it is honest non-recognition, never the claim "proven fake".
    """
    for name, predicate in _RECOGNIZERS:
        try:
            if predicate(step):
                return name
        except Exception:
            # a recognizer that chokes on some Molecule the search emitted ABSTAINS (fail-closed); it never
            # produces a spurious VOUCH, and the step remains subject to the other recognizers / demotion.
            continue
    return None


def route_reaction_type_blockers(route) -> tuple[str, ...]:
    """The poor-man reaction-TYPE fiction blockers for ``route``: one deduplicated, ordered reason string per step
    that matches NO attested reaction class.

    A route is VOUCHED (no blocker) iff EVERY step is positively recognized (a 0-step route -- target already
    available -- is vacuously vouched). Any unrecognized step contributes a hard blocker, so the route is
    G6-dominated on the affordability frontier (:func:`smartchem.service._affordability_frontier`), exactly like an
    unobtainable catalyst (:func:`smartchem.experiment.catalyst_availability.route_catalyst_blockers`). The reason
    is honest: "unrecognized reaction type", explicitly NOT a claim of cost or feasibility (type-validity is
    Problem A; feasibility is the still-deferred Problem B). Fail-closed and total: a step whose recognition raises
    at any layer is treated as unrecognized (blocked), never silently vouched.
    """
    reasons: set[str] = set()
    for step in getattr(route, "steps", ()) or ():
        try:
            klass = recognize_reaction_type(step)
        except Exception:
            klass = None  # fail-closed: an unexpected fault demotes, never vouches
        if klass is None:
            try:
                eq = _step_equation(step)
            except Exception:
                eq = "<unprintable step>"
            reasons.add(
                f"unrecognized reaction type: no attested reaction class matches step '{eq}' -- demoted as "
                f"not-a-known-reaction (Problem A; NOT a claim of cost or feasibility)"
            )
    return tuple(sorted(reasons))
