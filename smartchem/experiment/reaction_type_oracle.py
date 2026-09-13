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
frontier routes at the R56 gate). The R57 dehydrative-etherification recognizer passes too: within the same shape,
a net-formed dialkyl (sp3 C-O-C) ether with a net-consumed sp3 alcohol, water expelled, and no reactant ether is
the signature of a real etherification -- a formula-conserving fake cannot share it (peroxide coupling consumes no
alcohol; the aryl-ether fake forms no dialkyl ether; the glycol+ether bundle reuses a reactant ether).
A GENERAL "new C-N bond" recognizer FAILS this admission gate -- it fires on
both caffeine N-methylation (real, must-vouch) AND aromatic phenol->aniline amination (fake, must-not-vouch), the
R55 theorem one alphabet over -- so it is deliberately NOT shipped (the R45 caffeine genericity win is DEMOTED as
honest coverage loss this round, to be recovered only behind a class-specific conservation-locked recognizer, not
a bounded-radius patch). Do NOT add a recognizer without its conservation-lock proof.

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

Boundaries carried as documented debt (R56 acyl + R57 etherification scope, per the design gates).
* TWO CLASSES this round -- acyl condensation (R56) and dehydrative etherification (R57), each with its own
  conservation-lock proof. Other real condensations (Friedel-Crafts, Kolbe-Schmitt, Claisen, N-alkylation) are
  demoted-as-unrecognized: honest coverage loss, NOT false-VOUCH. Each is a future round behind its own gate.
* LOCALITY (R57 design gate, dalembert) -- both census predicates are WHOLE-MOLECULE, so their soundness silently
  borrows the generator's k=1 single-cut invariant (``max_reactant_cuts = 1``, the production default). At k >= 2 a
  bundled multi-cut step can present the same net-group signature as an elementary reaction; the etherification
  reactant-ether clause demotes the specific glycol+ether bundled fake even then, but GENERAL config-robustness
  needs the reaction-center span the generator already computes (``CappedScission.cut``/``.caps``) carried onto the
  step and read locally -- the span-reading root fix (R58), which also hardens acyl. Sound at the production config.
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
    """The one shipped recognizer: an intermolecular acyl condensation (esterification / amidation /
    thioesterification / formylation), reusing the R48-hardened predicate.

    The predicate DETECTS the acyl-condensation reaction TYPE -- a polarity-neutral structural fact. Its
    fail-OPEN use as a feasibility DOMAIN GUARD in :mod:`smartchem.experiment.feasibility` (where firing means
    "refuse to vouch the derived DeltaG") is a DIFFERENT job than this module's fail-CLOSED type VOUCH; the shared
    thing is only the detector. (Promoting the shared FG census to a neutral module is a named future refactor;
    the frozen R56 probe + tests pin this module's behaviour so a drift in the borrowed predicate breaks a test.)
    """
    from .feasibility import _is_intermolecular_acyl_condensation
    return _is_intermolecular_acyl_condensation(step)


def _etherification(step) -> bool:
    """The R57 recognizer: an intermolecular DEHYDRATIVE etherification (2 R-OH -> R-O-R + water), delegating to
    the conservation-locked predicate in :mod:`smartchem.experiment.feasibility`.

    Conservation-lock (see the module docstring): within the elementary intermolecular shape, a fired step must
    net-FORM a dialkyl (sp3 C-O-C) ether, net-CONSUME an sp3 alcohol, and carry NO ether among its reactants -- a
    signature a formula-conserving fake cannot share for a REAL etherification class within the shape (the peroxide
    coupling has no alcohol consumed; the aryl-ether fake forms no dialkyl ether; the glycol + ether bundled fiction
    consumes a reactant ether).  Like acyl, its whole-molecule census borrows the generator's k=1 locality; the
    span-reading root fix (R58) is the general hardening."""
    from .feasibility import _is_intermolecular_etherification
    return _is_intermolecular_etherification(step)


#: The positive whitelist of attested reaction-class recognizers: ``(class_name, predicate)``. A step is
#: recognized iff SOME predicate fires. Every entry MUST carry a conservation-lock proof (see the module
#: docstring); a general bounded-radius recognizer is exactly escape #7 and is not admitted. R56 shipped acyl;
#: R57 adds dehydrative etherification (a second conservation-locked class, NOT a bounded-radius patch).
_RECOGNIZERS: tuple[tuple[str, "object"], ...] = (
    ("acyl condensation (esterification/amidation)", _acyl_condensation),
    ("etherification (dehydrative, R-OH + R'-OH -> ether + water)", _etherification),
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
