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
both real N-alkylation (must-vouch) AND aromatic phenol->aniline aryl amination (fake, must-not-vouch), the
R55 theorem one alphabet over -- so a general recognizer is deliberately NOT shipped. R60 recovered the R45 caffeine
genericity win the honest way the R56 record prescribed: a CLASS-SPECIFIC conservation-locked N-methylation
recognizer; R63 GENERALISES it to dehydrative N-ALKYLATION by any ALKYL alcohol onto ANY non-carbonyl N nucleophile
(:func:`_n_alkylation`, subsuming the R60 methyl sub-case), still NOT a bounded-radius patch.
Its lock (hardened against TWO adversary kills the review gate caught): the real class and the aryl-amination fake
collide on a BYTE-IDENTICAL reaction centre, so the span check cannot separate them; the whole-molecule census does
-- the consumed alcohol must be an ALKYL-carbinol alcohol (an alkyl carbinol, NOT a masked-carbonyl hemiaminal/gem-
diol/hemiacetal -- KILL 1, dalembert; also excludes aromatic phenol-O) and an sp3-C--to--(non-carbonyl-N) BOND must
net-form (counting BONDS not N atoms makes the net rise by exactly one per alkylation even for an already-alkylated
secondary amine). The N may be any non-carbonyl nucleophile -- an aliphatic amine, a pyrrole-type azole N (all-
single-bond, e.g. the caffeine xanthine N7 -- KILL 2, evil-morty: the old "aromatic N carries an order-2 bond"
premise was FALSE; azole N-alkylation is a real class, ADMITTED), or a sulfonamide/hydrazide/hydroxylamine/amidine
N (a dalembert re-attack confirmed all are genuine N-alkylation TYPES, no fiction -- operator-confirmed broad
scope); the aryl-amination fake is excluded by the CARBON clause (an aryl C-N is not an sp3 C-N), not the N clause.
Do NOT add a recognizer without its conservation-lock proof.

What a VOUCH means, and what it deliberately does NOT (the disposition law -- type-validity != feasibility).
A VOUCH says ONLY "a mechanism of this reaction TYPE exists" (Problem A). It is NOT a feasibility claim (Problem B,
still deferred): the acyl recognizer VOUCHES the direct free-acid esterification/amidation class that
:func:`smartchem.experiment.feasibility.feasibility_of_step` itself FAILS CLOSED on (the aqueous salt-sink / the
activation requirement -- the R47 domain guard). Both are correct at their own scope, so this demoter only ever
ADDS a blocker; it NEVER removes one, and it must not be read as lifting the feasibility guard. The reason strings
say "unrecognized reaction type ... NOT a claim of cost or feasibility" so the disposition is not misread.

How it wires in (the proven sibling pattern). :func:`route_reaction_type_blockers` mirrors
:func:`smartchem.experiment.catalyst_availability.route_catalyst_blockers` exactly: one deduplicated reason string
per unrecognized step, fed into :func:`smartchem.service._affordability_frontier`'s ``fiction_blockers`` channel
(the NOT_A_REACTION disposition, a distinct tuple from ``hard_blockers`` = REAL_BUT_HARD since R59; both are
section-10.4 G6 -- a blocker dominates cost), so a route with any unrecognized step sinks on the affordability
frontier. It runs DOWNSTREAM of ``ranked``; it never touches ``_score_tuple``.

Boundaries carried as documented debt (R56 acyl + R57 etherification + R63 N-alkylation scope, per the gates).
* SEVENTEEN ACTIVE CLASSES -- three dehydrative condensations + eight Diels-Alder [4+2] families + four [3,3]
  sigmatropic isomerizations + two electrocyclizations, each with its own conservation-lock (condensations) or
  double-certificate (pericyclic / sigmatropic / electrocyclic) proof:
  (1) acyl condensation (R56), (2) dehydrative etherification (R57), (3) dehydrative N-alkylation (R63, generalising
  and SUBSUMING the R60 N-methylation sub-case -- it REPLACES the R60 entry rather than adding one; it covers any
  non-carbonyl N nucleophile -- amine, azole, sulfonamide, hydrazide, hydroxylamine, amidine/guanidine -- by an ALKYL
  alcohol);
  (4) all-carbon DA, ALKENE dienophile -> cyclohexene (the first PERICYCLIC, non-condensation class); (5) its ALKYNE
  sibling -> 1,4-cyclohexadiene (the first pericyclic class that keeps a second unsaturation); (6) aza-DA + (7) oxa-DA
  (imine / carbonyl dienophile, the first HETEROATOM pericyclic classes); (8) thia-DA (thiocarbonyl dienophile ->
  dihydrothiopyran, the third heteroatom-dienophile family, whose neutral-valence guard-2c bound S:2 is load-bearing
  against a thiocarbenium false-vouch); (9) 1-azadiene DA + (10) 1-oxadiene (inverse-electron-demand) DA + (13)
  1-thiadiene DA -- the DIENE-position hetero families completing the 3x2 heteroatom x {dienophile, diene} matrix,
  each of which SHARES a reaction centre with its same-heteroatom DIENOPHILE sibling ((C,X,.) is position-invariant),
  so they are separated by Layer A ALONE (the centre check, Layer B, is necessary but not a separator; Layer A's
  re-derivation is);
  (11) Cope [3,3] + (12) Claisen [3,3] + (14) aza-Claisen [3,3] + (15) thia-Claisen [3,3] sigmatropic isomerizations
  -- the rank-FLAT (1->1) classes, promoting the opt-in :mod:`smartchem.lateral_rewrite` seam (a lateral rewrite has
  no strict-descent decomposition image, so it cannot ride ``search_routes`` auto-discovery -- W1; its consumer is a
  hand-assembled or bounded-lateral-search route (:mod:`smartchem.lateral_search`) the oracle now vouches instead of
  demoting);
  (16) 4-pi electrocyclization (butadiene -> cyclobutene) + (17) 6-pi electrocyclization (hexatriene -> cyclohexadiene)
  -- the THIRD pericyclic archetype, rank-flat ring-open/close isomerizations on the same lateral seam.
  All EIGHT DA classes are locked apart, and the four [3,3] and two electrocyclic classes from each other and from
  every DA class, by the exact-equality centre check PLUS Layer A (the load-bearing separator wherever centres
  collide) -- none poaches another's steps (a DA matrix + a lateral/DA matrix pin this).  ARYL amination (the phenol->aniline fake)
  and masked-carbonyl donors (hemiaminal/acetal condensations) are excluded; other real condensations
  (Friedel-Crafts, Kolbe-Schmitt) and non-sigmatropic isomerizations (tautomerization) are demoted-as-unrecognized:
  honest coverage loss, NOT false-VOUCH. Each remaining class is a future round behind its own gate.
* LOCALITY (R57 debt, CLOSED by R58 span reading) -- a whole-molecule census is non-local, so R56/R57 borrowed
  the generator's k=1 single-cut invariant (``max_reactant_cuts = 1``, the production default). R58 distils the
  reaction-centre span the generator already computes (``CappedScission.cut``/``.caps``) into a coordinate-free
  :class:`~smartchem.reaction_center.ReactionCenter` carried on the step, and both recognizers now CHECK the centre
  is a single connected elementary condensation (:meth:`ReactionCenter.is_elementary_condensation`) rather than
  trusting the config. This makes the k=1 assumption a structural FACT (config-robust: 48 reachable k=2 acyl bundles
  and the k=2 ether bundles that forge the elementary net signature are demoted by their non-elementary spans), and
  the span-local ether check retires the R57 clause (iii) blacklist -- RECOVERING 40 production-reachable genuine
  etherifications whose reactant contains an unrelated ether (``methanol + 2-methoxyethanol ->
  1,2-dimethoxyethane + water``). A step lacking a centre (hand-built / non-scission transform / a serialized replay
  whose centre was NULLED) is FAIL-CLOSED demoted -- ALL THREE recognizers now BLOCK on an absent centre
  (TAMPER-HARDENING-01, extending the R60 N-methylation gate finding to acyl + ether); the non-local census is never
  trusted alone, so centre-omission can only cost a vouch (false-UNRECOGNIZED, safe), never mint one (false-VOUCH,
  catastrophic). Centre-carrying live and replayed steps read identically (the centre round-trips through the replay
  payload), so this is the load-time authority :meth:`CompilationResponse._check_frontier_coherence` re-derives the
  fiction channel with.
* DISPOSITION FLATTENING (R56 debt, CLOSED by R59 disposition channel) -- historically the fiction blocker shared
  the ``hard_blockers`` tuple with catalyst/section-11 blockers, so a "real reaction, needs industrial catalyst"
  route and a "not a reaction at all" route were both G6-sunk equally (the partial order "real-but-hard strictly
  outranks not-a-reaction" was lost). R59 SPLIT the channels: ``route_reaction_type_blockers`` now populates a
  distinct ``fiction_blockers`` tuple (NOT_A_REACTION), separate from ``hard_blockers`` (REAL_BUT_HARD = process +
  catalyst), giving the disposition its own re-derived, tamper-hardened channel. The ranking-INVERSION that
  distinction would drive (a real-but-hard route outranking a fiction) still awaits a real metal-catalyst source
  (escape #7); R59 delivered the VISIBILITY, not yet the inversion.
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
    is demoted.

    FAIL-CLOSED on an absent centre (TAMPER-HARDENING-01, extending the R60 gate finding to acyl).  A step that
    carries NO reaction centre used to fall back to the whole-molecule predicate alone; it no longer does -- it
    BLOCKS.  The census is non-local (the R48 lesson), and a serialized replay whose ``reaction_center`` was NULLED
    is exactly a step with no readable centre.  Under the old fallback a tamperer could strip the centre off a fake
    to buy a census-only vouch; now centre-omission can only DEMOTE (false-UNRECOGNIZED, safe), never false-VOUCH
    (catastrophic).  A genuine hand-built acyl step loses its vouch too -- accepted coverage loss, the same trade
    :func:`_n_alkylation` already makes ([[a-whole-set-count-classifier-is-fooled-by-non-locality]])."""
    from .feasibility import _is_intermolecular_acyl_condensation
    if not _is_intermolecular_acyl_condensation(step):
        return False
    center = getattr(step, "reaction_center", None)
    if center is None:
        return False  # fail-closed: no readable centre -> the non-local census cannot vouch alone (TAMPER-HARDENING-01)
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
    bundled fakes (which have a non-elementary span) stay demoted.

    FAIL-CLOSED on an absent centre (TAMPER-HARDENING-01).  Like :func:`_acyl_condensation` and
    :func:`_n_alkylation`, a centre-less step now BLOCKS rather than falling back to the non-local R57 census: a
    nulled ``reaction_center`` in a serialized replay can therefore only DEMOTE, never buy a census-only vouch --
    centre-omission is false-UNRECOGNIZED (safe), not false-VOUCH."""
    from .feasibility import _ether_shape_and_net_change
    center = getattr(step, "reaction_center", None)
    if center is None:
        return False  # fail-closed: no readable centre -> the non-local census cannot vouch alone (TAMPER-HARDENING-01)
    return _ether_shape_and_net_change(step) and center.is_elementary_condensation(("O",))


def _n_alkylation(step) -> bool:
    """Recognizer: an intermolecular dehydrative N-ALKYLATION (non-carbonyl N-H + alkyl-OH -> N-alkyl + water), R63.

    The fourth conservation-locked class DEVELOPED (it SUBSUMES the R60 N-methylation entry rather than adding a
    recognizer), GENERALISING the R60 N-methylation recognizer to any ALKYL alcohol donor
    and any non-carbonyl nitrogen nucleophile -- the class the R56/R60 record deferred to "a future round
    behind its own gate".  It subsumes N-methylation (methanol is an alkyl alcohol; a methyl bond is an sp3 C-N
    bond), so it REPLACES rather than supplements it: caffeine (theophylline + methanol -> caffeine + water) is
    still vouched here, and the tight methanol sub-case census is retained in :mod:`smartchem.experiment.feasibility`
    as the R60 anchor proof.  SCOPE (R63 direction, operator-confirmed): the vouched class is dehydrative
    N-alkylation onto ANY non-carbonyl nitrogen nucleophile -- an aliphatic amine, a pyrrole-type heterocyclic ring
    N (imidazole/pyrrole/indole, the caffeine-class xanthine N7), a sulfonamide, hydrazide/hydrazine, hydroxylamine,
    or amidine/guanidine N -- all real N-alkylation reaction TYPES (Problem A; an adversary re-attack confirmed every
    admitted N is a genuine N-alkylation, no fiction).  Feasibility (Problem B: these want an activator) stays
    deferred, exactly as the acyl recognizer vouches activator-requiring esterification.  The label reads
    "non-carbonyl N-H" to name this scope honestly rather than understate it as "amine".

    The lock is R60's, widened -- and hardened against two adversary kills the review gate caught (the meta-lesson:
    run adversaries SEPARATELY from acceptance).  The span check alone
    (:meth:`~smartchem.reaction_center.ReactionCenter.is_elementary_condensation` with ``("N",)``, the SAME signature
    methylation used -- element pairs do not change with chain length) does NOT lock: it certifies "one C-N single
    bond forms displacing one C-O, H migrating N->O", but NOT that the carbon is alkyl nor that the N is a real
    amine.  The census (:func:`~smartchem.experiment.feasibility._n_alkylation_shape_and_net_change`) supplies both,
    with each clause carrying a kill it closes:
    * an ALKYL-carbinol alcohol net-consumed (:func:`~smartchem.experiment.feasibility._alkyl_carbinol_alcohol_count`,
      NOT the looser ``_alcohol_counts``).  KILL 1 (dalembert): ``_alcohol_counts`` is blind to a carbinol carbon's
      alpha-heteroatom neighbours, so a hemiaminal / gem-diol / hemiacetal (a MASKED carbonyl) posed as an alcohol
      and vouched an aminal/acetal condensation (``ammonia + aminomethanol -> methylenediamine + water``).  The
      alkyl-carbinol predicate forbids the carbonyl oxidation level, closing it with no genuine-case loss.  It also
      keeps the phenol->aniline aryl-amination fake demoted (phenol-O is aromatic, not an alkyl carbinol).
    * an sp3-C--to--(non-carbonyl-N) BOND net-formed (:func:`~smartchem.experiment.feasibility._n_alkyl_amine_bond_count`).
      Counting BONDS not N atoms makes the net rise by exactly one per alkylation even for an already-alkylated
      secondary amine.  KILL 2 (evil-morty): the old comment claimed "aromatic N carries an order-2 bond" -- FALSE
      for a pyrrole-type N, which is all-single, so azole N slipped through mislabelled as an aliphatic amine.  The
      R63 direction RESOLVES this by admitting azole N as a real class (see SCOPE); the aryl-amination fake is still
      excluded, but through the CARBON clause (an aryl C-N is not an sp3 C-N), never the N clause.
    Within the elementary shape + this centre, formula conservation then FORCES the (now provably alkyl) carbinol
    carbon onto the (amine-or-azole) nitrogen -- a genuine N-alkylation (the conservation-lock proof).

    FAIL-CLOSED on an absent centre (TAMPER-HARDENING-01, inherited from R60).  This recognizer does NOT fall back to
    the whole-molecule census when a step carries no reaction centre -- it BLOCKS (as acyl and ether do too).  The
    census is non-local, and a centre-less homologation forges the net signature: ``N-methylformamide + methanol ->
    CNCC=O + water`` MIGRATES the carbonyl off the N, unmasking a pre-existing alkyl, so the bond census reads a
    spurious rise with no alkyl actually transferred.  The span closes exactly this
    ([[a-whole-set-count-classifier-is-fooled-by-non-locality]]), so a VOUCH REQUIRES a readable, elementary
    N-centre.  A centre-less step is honest coverage loss (false-UNRECOGNIZED, safe), never a census-only vouch
    (false-VOUCH, catastrophic) -- the arch's declared-but-unrecognizable-input-must-BLOCK polarity."""
    from .feasibility import _n_alkylation_shape_and_net_change
    center = getattr(step, "reaction_center", None)
    if center is None:
        return False  # fail-closed: no readable centre -> the non-local census cannot vouch alone (gate finding)
    return _n_alkylation_shape_and_net_change(step) and center.is_elementary_condensation(("N",))


def _alkyne_diels_alder(step) -> bool:
    """Recognizer: an all-carbon Diels-Alder [4+2] cycloaddition (diene + ALKYNE dienophile -> 1,4-cyclohexadiene).

    The fifth active class, and the FIRST pericyclic recognizer that keeps a second unsaturation in the adduct: an
    alkyne dienophile donates its second pi bond into the ring, so the product is 1,4-cyclohexadiene (verified
    chemistry), not the fully-saturated-except-one-alkene cyclohexene the alkene family makes.  It is a straight
    clone of :func:`_diels_alder`'s three-layer discipline against the alkyne sibling family
    (:mod:`smartchem.diels_alder`'s :data:`_ALKYNE_DA_CENTER` /
    :func:`~smartchem.diels_alder._reactant_alkyne_da_disconnects_to`), so it inherits the SAME soundness argument
    rather than a hand-rolled second one: Layer A re-derives [4+2]-ness from the step's own molecules (never the
    transform type), Layer B pins the exact alkyne-family reaction centre (distinct from the alkene family's, so the
    two classes cannot cross-poach each other), and Layer C fail-closed blocks a centre-less step.

    SCOPE: only alkyne-dienophile -> 1,4-cyclohexadiene.  An allene dienophile or an alkyne embedded in a larger
    conjugated system is genuine [4+2] chemistry this recognizer does NOT vouch -- honest coverage loss
    (false-UNRECOGNIZED, safe), never a false-vouch."""
    from ..diels_alder import _ALKYNE_DA_CENTER, _reactant_alkyne_da_disconnects_to
    reactants = tuple(step.reactants)
    products = tuple(step.products)
    if len(products) != 1 or len(reactants) != 2:
        return False
    if not _reactant_alkyne_da_disconnects_to(products[0], reactants):
        return False  # Layer A: the adduct does not re-derive a guarded alkyne [4+2] retro into these two reactants
    center = getattr(step, "reaction_center", None)
    if center is None:
        return False  # Layer C fail-closed: no readable centre -> the family re-derivation cannot vouch alone
    return center == _ALKYNE_DA_CENTER  # Layer B: the centre is exactly the alkyne-family pericyclic [4+2] signature


def _diels_alder(step) -> bool:
    """Recognizer: an all-carbon Diels-Alder [4+2] cycloaddition (diene + ALKENE dienophile -> cyclohexene adduct).

    SCOPE (honest, per the adversary gate): only the alkene-dienophile -> cyclohexene family is recognized.  An
    alkyne dienophile (butadiene + acetylene -> 1,3-cyclohexadiene) or an allene/exocyclic-alkene dienophile is a
    genuine [4+2] this recognizer does NOT vouch -- honest coverage loss (false-UNRECOGNIZED, safe), never a
    false-vouch; the family rule fixes an alkene dienophile.

    Conservation-locked like its siblings, but the lock is the DA family's own double certificate rather than a
    functional-group census (a pericyclic reaction has no dehydrative signature).  Three layers:
    * Layer A (the census analogue) -- re-derive [4+2]-ness FROM THE STEP'S OWN MOLECULES, never from the
      transform type: the step must be a 2->1 combination whose single product admits a GUARDED retro-Diels-Alder
      disconnecting into exactly the two reactants (:func:`smartchem.diels_alder._reactant_da_disconnects_to`).  A
      mass-balancing 2->1 combination that is NOT a genuine [4+2] is refused -- conservation alone does not prove a
      cycloaddition (the load-bearing certificate; a budget-exhausted retro DEMOTES, never vouches -- fail-closed).
    * Layer B (span-local) -- the reaction centre must be the pericyclic [4+2] signature
      (:data:`smartchem.diels_alder._DA_CENTER`: two sigma C-C formed + the central pi shift, three pi broken, one
      connected six-carbon cluster), matched by exact equality.
    * Layer C (fail-closed, TAMPER-HARDENING-01) -- a step with no readable centre BLOCKS.
    Soundness rests on Layer A's independent re-derivation; the centre supplies elementarity + tamper-resistance,
    never the vouch alone.  Structural type-validity only (Problem A): no feasibility/endo-exo/regiochemistry.

    HOT PATH (load-bearing reachability, evil-morty): this runs via :func:`route_reaction_type_blockers` in
    production route ranking for ALL users, so Layer A's retro runs on every 2->1 step's product (cheap ~1 ms; the
    pre-filter in ``_reactant_da_disconnects_to`` skips the common acyclic fragment).  It is a no-op for non-opt-in
    users ONLY because the default single-cut (``max_reactant_cuts = 1``) CappedScission cannot emit a ring-forming
    2->1 step -- a reachability property, NOT structural.  Enable a carbocyclic 2->1 provider (or raise the cut
    budget) and DA vouches begin firing in production: the intended, sound behaviour, not a regression."""
    from ..diels_alder import _DA_CENTER, _reactant_da_disconnects_to
    reactants = tuple(step.reactants)
    products = tuple(step.products)
    if len(products) != 1 or len(reactants) != 2:
        return False
    if not _reactant_da_disconnects_to(products[0], reactants):
        return False  # Layer A: the adduct does not re-derive a guarded [4+2] retro into these two reactants
    center = getattr(step, "reaction_center", None)
    if center is None:
        return False  # Layer C fail-closed: no readable centre -> the family re-derivation cannot vouch alone
    return center == _DA_CENTER  # Layer B: the centre is exactly the pericyclic [4+2] signature


def _hetero_diels_alder(step, family) -> bool:
    """The shared three-layer discipline for a HETEROATOM-dienophile Diels-Alder [4+2] family (aza: X=N, oxa: X=O),
    parameterized by the family descriptor (:data:`smartchem.diels_alder.AZA_DA` / :data:`~smartchem.diels_alder.
    OXA_DA`).  Identical soundness argument to :func:`_diels_alder`, just against the family's own relabeled
    re-derivation + centre: Layer A re-derives THIS family's guarded [4+2] retro from the step's own molecules
    (:func:`~smartchem.diels_alder._reactant_hetero_da_disconnects_to`), Layer B pins the exact family centre
    (``(C, X, .)`` bond pairs, distinct from every other family's, so the classes cannot cross-poach), Layer C
    fail-closed blocks a centre-less step."""
    from ..diels_alder import _reactant_hetero_da_disconnects_to
    reactants = tuple(step.reactants)
    products = tuple(step.products)
    if len(products) != 1 or len(reactants) != 2:
        return False
    if not _reactant_hetero_da_disconnects_to(family, products[0], reactants):
        return False  # Layer A: the adduct does not re-derive a guarded hetero [4+2] retro into these two reactants
    center = getattr(step, "reaction_center", None)
    if center is None:
        return False  # Layer C fail-closed: no readable centre -> the family re-derivation cannot vouch alone
    return center == family.center  # Layer B: exactly this hetero family's pericyclic [4+2] signature


def _aza_diels_alder(step) -> bool:
    """Recognizer: an aza-Diels-Alder [4+2] cycloaddition (diene + imine C=N -> tetrahydropyridine).

    The SIXTH active class, and the FIRST heteroatom (non-all-carbon) pericyclic recognizer -- the ground the
    all-carbon DA families opened onto a heteroatom dienophile.  Delegates to :func:`_hetero_diels_alder` bound to
    :data:`smartchem.diels_alder.AZA_DA`, so it inherits the DA double-certificate soundness argument (Layer A
    re-derivation is the gate) against the aza family's own centre (which carries ``(C, N, .)`` pairs no other
    family's centre carries -- no cross-poach).

    SCOPE: only imine-dienophile -> tetrahydropyridine.  Other aza-[4+2] variants (an N-in-the-diene 1-aza-diene,
    a nitroso/azo dienophile) are genuine chemistry this recognizer does NOT vouch -- honest coverage loss
    (false-UNRECOGNIZED, safe), never a false-vouch."""
    from ..diels_alder import AZA_DA
    return _hetero_diels_alder(step, AZA_DA)


def _oxa_diels_alder(step) -> bool:
    """Recognizer: an oxa-Diels-Alder [4+2] cycloaddition (diene + carbonyl C=O -> dihydropyran).

    The SEVENTH active class, the aza recognizer's sibling with oxygen in place of nitrogen.  Delegates to
    :func:`_hetero_diels_alder` bound to :data:`smartchem.diels_alder.OXA_DA`; its centre carries ``(C, O, .)``
    pairs, distinct from the aza ``(C, N, .)`` and every all-carbon centre, so the four DA classes are locked apart
    by exact-equality.

    SCOPE: only carbonyl-dienophile -> dihydropyran (the parent thermal oxa-DA; many want a Lewis acid -- Problem B,
    deferred).  A thiocarbonyl (thia-DA) is a sibling class of its own; a 1-oxadiene (inverse-demand) is a separate
    class too (:func:`_oxa_diene_diels_alder`).  Both are honest coverage loss here, never a false-vouch."""
    from ..diels_alder import OXA_DA
    return _hetero_diels_alder(step, OXA_DA)


def _thia_diels_alder(step) -> bool:
    """Recognizer: a thia-Diels-Alder [4+2] cycloaddition (diene + thiocarbonyl C=S -> dihydrothiopyran).

    The EIGHTH active class, the third heteroatom-dienophile family (S in place of O).  Delegates to
    :func:`_hetero_diels_alder` bound to :data:`smartchem.diels_alder.THIA_DA`; its centre carries ``(C, S, .)``
    pairs, distinct from aza ``(C, N, .)``, oxa ``(C, O, .)`` and every all-carbon centre, so it is locked apart
    from the other classes.  Its neutral-valence guard (S: 2, whose charge-agnostic ceiling is 6) is the family
    whose guard 2c bound is load-bearing against a thiocarbenium/sulfonium false-vouch.

    SCOPE: only thiocarbonyl-dienophile -> dihydrothiopyran.  A 1-thiadiene is honest coverage loss, never a
    false-vouch."""
    from ..diels_alder import THIA_DA
    return _hetero_diels_alder(step, THIA_DA)


def _aza_diene_diels_alder(step) -> bool:
    """Recognizer: a 1-azadiene Diels-Alder [4+2] (an N-terminus diene + alkene -> a tetrahydropyridine isomer).

    The NINTH active class, and the FIRST recognizer whose separation from a sibling rests on Layer A ALONE.  The
    heteroatom is now in the DIENE (vertex 0), not the dienophile, so this family and :func:`_aza_diels_alder` share
    an IDENTICAL reaction centre (the ``(C,N,.)`` formed/broken multiset is invariant to where the single N sits in
    the ring) -- Layer B (:data:`AZA_DIENE_DA`'s ``center``) does NOT distinguish them.  Layer A does: the two
    adducts are distinct regio-isomers (N adjacent to the ring C=C for THIS diene family, N isolated for the
    dienophile family), so :func:`~smartchem.diels_alder._reactant_hetero_da_disconnects_to` bound to
    :data:`AZA_DIENE_DA` re-derives ONLY the 1-azadiene adduct into these reactants and abstains on the dienophile
    adduct (verified no cross-poach).  Delegates to :func:`_hetero_diels_alder`, so the soundness argument (Layer A
    is the gate) is inherited unchanged."""
    from ..diels_alder import AZA_DIENE_DA
    return _hetero_diels_alder(step, AZA_DIENE_DA)


def _oxa_diene_diels_alder(step) -> bool:
    """Recognizer: a 1-oxadiene (inverse-electron-demand) Diels-Alder [4+2] (an enone/enal 4-pi diene + alkene ->
    a dihydropyran isomer).

    The TENTH active class, the oxygen sibling of :func:`_aza_diene_diels_alder`.  Shares its reaction centre with
    :func:`_oxa_diels_alder` (the ``(C,O,.)`` multiset is position-invariant), so it too is separated from its
    dienophile sibling by Layer A alone -- the O-terminus diene adduct re-derives only under
    :data:`OXA_DIENE_DA`.  Delegates to :func:`_hetero_diels_alder`.

    SCOPE: only the parent thermal inverse-demand oxa-DA (a Lewis acid accelerates many -- Problem B, deferred)."""
    from ..diels_alder import OXA_DIENE_DA
    return _hetero_diels_alder(step, OXA_DIENE_DA)


def _thia_diene_diels_alder(step) -> bool:
    """Recognizer: a 1-thiadiene Diels-Alder [4+2] (an S-terminus diene + alkene -> a dihydrothiopyran isomer).

    The THIRTEENTH active class, the sulfur sibling of :func:`_aza_diene_diels_alder` / :func:`_oxa_diene_diels_alder`
    and the SIXTH (final) cell of the 3x2 heteroatom x {dienophile, diene} matrix.  Shares its reaction centre with
    :func:`_thia_diels_alder` (the ``(C,S,.)`` multiset is position-invariant), so it too is separated from its
    dienophile sibling by Layer A alone -- the S-terminus diene adduct re-derives only under
    :data:`smartchem.diels_alder.THIA_DIENE_DA`.  Delegates to :func:`_hetero_diels_alder`."""
    from ..diels_alder import THIA_DIENE_DA
    return _hetero_diels_alder(step, THIA_DIENE_DA)


def _sigmatropic_rearrangement(step, family) -> bool:
    """The shared three-layer discipline for a [3,3] sigmatropic ISOMERIZATION (Cope / Claisen), the first
    rank-FLAT (1->1) recognizers.  Same soundness argument as the DA recognizers against the lateral family's own
    re-derivation + centre: Layer A re-derives THIS family's guarded [3,3] rewrite from the step's own single
    molecule (:func:`~smartchem.lateral_rewrite._reactant_rewrites_to` -- conservation alone proves nothing, since
    every isomer balances mass, so the re-derivation IS the gate), Layer B pins the exact family centre, Layer C
    fail-closed blocks a centre-less step.  A 1->1 shape early-out keeps this a cheap no-op for the common (2->1 /
    2->2) production step."""
    from ..lateral_rewrite import _reactant_rewrites_to
    reactants = tuple(step.reactants)
    products = tuple(step.products)
    if len(reactants) != 1 or len(products) != 1:
        return False
    if not _reactant_rewrites_to(family, products[0], reactants):
        return False  # Layer A: the product does not re-derive a guarded [3,3] rewrite into the reactant isomer
    center = getattr(step, "reaction_center", None)
    if center is None:
        return False  # Layer C fail-closed: no readable centre -> the re-derivation cannot vouch alone
    return center == family.center  # Layer B: exactly this sigmatropic family's [3,3] centre


def _cope_rearrangement(step) -> bool:
    """Recognizer: an all-carbon Cope [3,3] sigmatropic rearrangement (a 1,5-diene -> its [3,3] isomer).

    The ELEVENTH active class, and (with Claisen) the FIRST rank-flat 1->1 recognizer -- the lateral-rewrite seam's
    reachable consumer.  Delegates to :func:`_sigmatropic_rearrangement` bound to
    :data:`smartchem.lateral_rewrite.COPE`; its centre carries only ``(C,C,.)`` pairs but is distinct from every DA
    centre (a [3,3] forms one sigma + migrates two pi with NO net ring closure, so its formed/broken multiset is its
    own).  SCOPE: only a genuine [3,3] shift (Layer A re-derives it); a non-sigmatropic isomerization
    (tautomerization, other rearrangements) is honest coverage loss, never a false-vouch."""
    from ..lateral_rewrite import COPE
    return _sigmatropic_rearrangement(step, COPE)


def _claisen_rearrangement(step) -> bool:
    """Recognizer: a Claisen [3,3] sigmatropic rearrangement (an allyl vinyl ether -> a gamma,delta-unsaturated
    carbonyl).

    The TWELFTH active class, the oxa sibling of :func:`_cope_rearrangement` (array atom 2 is the O, which migrates
    into a carbonyl).  Its centre carries a ``(C,O,.)`` pair distinct from Cope's all-carbon centre and from every
    oxa-DA centre (a [3,3] is not a [4+2]), so the two sigmatropic classes and the DA classes are all locked apart
    by exact-equality.  Delegates to :func:`_sigmatropic_rearrangement` bound to
    :data:`smartchem.lateral_rewrite.CLAISEN`."""
    from ..lateral_rewrite import CLAISEN
    return _sigmatropic_rearrangement(step, CLAISEN)


def _aza_claisen_rearrangement(step) -> bool:
    """Recognizer: an aza-Claisen (3-aza-Cope) [3,3] sigmatropic rearrangement (an allyl vinyl amine ->
    gamma,delta-unsaturated imine).

    The FOURTEENTH active class, the nitrogen sibling of :func:`_claisen_rearrangement` (array atom 2 is the N, which
    migrates into a C=N imine).  Its centre carries a ``(C,N,.)`` pair distinct from Claisen's ``(C,O,.)``, Cope's
    all-carbon centre, and every DA centre, so all the [3,3] and [4+2] classes stay locked apart by exact equality.
    Delegates to :func:`_sigmatropic_rearrangement` bound to :data:`smartchem.lateral_rewrite.AZA_CLAISEN`."""
    from ..lateral_rewrite import AZA_CLAISEN
    return _sigmatropic_rearrangement(step, AZA_CLAISEN)


def _thia_claisen_rearrangement(step) -> bool:
    """Recognizer: a thia-Claisen [3,3] sigmatropic rearrangement (an allyl vinyl sulfide ->
    gamma,delta-unsaturated thiocarbonyl).

    The FIFTEENTH active class, the sulfur sibling of :func:`_claisen_rearrangement`, completing the hetero-[3,3] set
    {O, N, S} on the same array.  Its ``(C,S,.)`` centre is distinct from every other [3,3] and [4+2] centre.
    Delegates to :func:`_sigmatropic_rearrangement` bound to :data:`smartchem.lateral_rewrite.THIA_CLAISEN`."""
    from ..lateral_rewrite import THIA_CLAISEN
    return _sigmatropic_rearrangement(step, THIA_CLAISEN)


def _electrocyclization_4pi(step) -> bool:
    """Recognizer: a 4-pi electrocyclization (1,3-butadiene -> cyclobutene, and substituted analogues).

    The SIXTEENTH active class, and the FIRST of the THIRD pericyclic archetype -- an electrocyclic ring-open/close,
    after [4+2] cycloaddition and [3,3] sigmatropic shift.  A rank-flat 1->1 isomerization that FORMS/BREAKS a ring
    sigma bond (its centre carries the new ring-closure ``(C,C,1)`` bond, distinct from the sigmatropic centres), so
    it rides the same lateral-rewrite machinery.  Delegates to :func:`_sigmatropic_rearrangement` bound to
    :data:`smartchem.lateral_rewrite.ELECTRO_4PI`.  4 pi electrons -> thermally CONROTATORY (Woodward-Hoffmann); that
    stereochemical selection rule is annotated by :mod:`smartchem.pericyclic_selection`, not asserted here (Problem A
    type-validity only)."""
    from ..lateral_rewrite import ELECTRO_4PI
    return _sigmatropic_rearrangement(step, ELECTRO_4PI)


def _electrocyclization_6pi(step) -> bool:
    """Recognizer: a 6-pi electrocyclization ((Z)-1,3,5-hexatriene -> 1,3-cyclohexadiene, and substituted analogues).

    The SEVENTEENTH active class, the 6-electron sibling of :func:`_electrocyclization_4pi`.  Its centre (a larger
    ring-closure) is distinct from the 4-pi centre and from every sigmatropic and DA centre.  Delegates to
    :func:`_sigmatropic_rearrangement` bound to :data:`smartchem.lateral_rewrite.ELECTRO_6PI`.  6 pi electrons ->
    thermally DISROTATORY (Woodward-Hoffmann); annotated by :mod:`smartchem.pericyclic_selection`."""
    from ..lateral_rewrite import ELECTRO_6PI
    return _sigmatropic_rearrangement(step, ELECTRO_6PI)


#: The positive whitelist of attested reaction-class recognizers: ``(class_name, predicate)``. A step is
#: recognized iff SOME predicate fires. Every entry MUST carry a conservation-lock proof (see the module
#: docstring); a general bounded-radius recognizer is exactly escape #7 and is not admitted. R56 shipped acyl;
#: R57 added dehydrative etherification; R60 added dehydrative N-methylation and R63 GENERALISES it to dehydrative
#: N-alkylation by any sp3 alcohol (subsuming the methyl sub-case; each a conservation-locked class, NOT a
#: bounded-radius patch). The Diels-Alder [4+2] recognizer promotes the opt-in rule-calculus DA family into the
#: oracle -- the first pericyclic, non-condensation class, locked by the family's own re-derivation certificate; the
#: alkyne-dienophile sibling ADDS a fifth entry (its own distinct centre + re-derivation), the first pericyclic class
#: that keeps a second unsaturation in the adduct (1,4-cyclohexadiene, not cyclohexene).  The aza- and oxa-DA
#: recognizers ADD a SIXTH and SEVENTH entry -- the first HETEROATOM pericyclic classes (diene + imine ->
#: tetrahydropyridine; diene + carbonyl -> dihydropyran), each with its own heteroatom-bearing centre and
#: re-derivation.  All FOUR DA classes are locked apart by their exact-equality centre check, so none can poach
#: another's steps.
_RECOGNIZERS: tuple[tuple[str, "object"], ...] = (
    ("acyl condensation (esterification/amidation)", _acyl_condensation),
    ("etherification (dehydrative, R-OH + R'-OH -> ether + water)", _etherification),
    ("N-alkylation (dehydrative, non-carbonyl N-H + alkyl-OH -> N-alkyl + water)", _n_alkylation),
    ("Diels-Alder [4+2] cycloaddition (all-carbon diene + alkene dienophile -> cyclohexene adduct)", _diels_alder),
    ("Diels-Alder [4+2] cycloaddition (all-carbon diene + alkyne dienophile -> 1,4-cyclohexadiene)",
     _alkyne_diels_alder),
    ("aza-Diels-Alder [4+2] cycloaddition (diene + imine dienophile -> tetrahydropyridine)", _aza_diels_alder),
    ("oxa-Diels-Alder [4+2] cycloaddition (diene + carbonyl dienophile -> dihydropyran)", _oxa_diels_alder),
    ("thia-Diels-Alder [4+2] cycloaddition (diene + thiocarbonyl dienophile -> dihydrothiopyran)", _thia_diels_alder),
    ("aza-Diels-Alder [4+2] cycloaddition (1-azadiene + alkene dienophile -> tetrahydropyridine isomer)",
     _aza_diene_diels_alder),
    ("oxa-Diels-Alder [4+2] cycloaddition (1-oxadiene inverse-demand + alkene dienophile -> dihydropyran isomer)",
     _oxa_diene_diels_alder),
    ("thia-Diels-Alder [4+2] cycloaddition (1-thiadiene + alkene dienophile -> dihydrothiopyran isomer)",
     _thia_diene_diels_alder),
    ("Cope [3,3] sigmatropic rearrangement (1,5-diene -> [3,3] isomer)", _cope_rearrangement),
    ("Claisen [3,3] sigmatropic rearrangement (allyl vinyl ether -> gamma,delta-unsaturated carbonyl)",
     _claisen_rearrangement),
    ("aza-Claisen [3,3] sigmatropic rearrangement (allyl vinyl amine -> gamma,delta-unsaturated imine)",
     _aza_claisen_rearrangement),
    ("thia-Claisen [3,3] sigmatropic rearrangement (allyl vinyl sulfide -> gamma,delta-unsaturated thiocarbonyl)",
     _thia_claisen_rearrangement),
    ("electrocyclization 4pi (1,3-butadiene -> cyclobutene)", _electrocyclization_4pi),
    ("electrocyclization 6pi ((Z)-1,3,5-hexatriene -> 1,3-cyclohexadiene)", _electrocyclization_6pi),
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
