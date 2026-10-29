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
* EIGHTEEN ACTIVE CLASSES -- three dehydrative condensations + one activated acyl transfer + eight Diels-Alder [4+2]
  families + four [3,3] sigmatropic isomerizations + two electrocyclizations, each with its own conservation-lock
  (condensation / activated transfer) or re-derivation-certificate (pericyclic / sigmatropic / electrocyclic) proof:
  (1) acyl condensation (R56), (2) dehydrative etherification (R57), (3) dehydrative N-alkylation (R63, generalising
  and SUBSUMING the R60 N-methylation sub-case -- it REPLACES the R60 entry rather than adding one; it covers any
  non-carbonyl N nucleophile -- amine, azole, sulfonamide, hydrazide, hydroxylamine, amidine/guanidine -- by an ALKYL
  alcohol); (3b) ACTIVATED acyl transfer (#110 -- an anhydride / acyl halide acylating an O/N/S nucleophile, coproduct
  a carboxylic acid / H-X, NOT water; the free-acid condensation's pre-activated sibling, re-derived by a single-cut
  scission capped with the leaving-group acid -- O/N/S only, C-acylation/Friedel-Crafts deferred to #107);
  (4) all-carbon DA, ALKENE dienophile -> cyclohexene (the first PERICYCLIC, non-condensation class); (5) its ALKYNE
  sibling -> 1,4-cyclohexadiene (the first pericyclic class that keeps a second unsaturation); (6) aza-DA + (7) oxa-DA
  (imine / carbonyl dienophile, the first HETEROATOM pericyclic classes); (8) thia-DA (thiocarbonyl dienophile ->
  dihydrothiopyran, the third heteroatom-dienophile family, whose neutral-valence guard-2c bound S:2 is load-bearing
  against a thiocarbenium false-vouch); (9) 1-azadiene DA + (10) 1-oxadiene (inverse-electron-demand) DA + (13)
  1-thiadiene DA -- the DIENE-position hetero families completing the 3x2 heteroatom x {dienophile, diene} matrix,
  each of which shares a formed/broken bond STRUCTURE with its same-heteroatom DIENOPHILE sibling ((C,X,.) is
  position-invariant), so they are separated by the family RE-DERIVATION ALONE (ISSUE-132: no reaction-centre is read
  -- each family's guarded retro re-derives only its own regioisomer; fuzz-verified as a clean separator);
  (11) Cope [3,3] + (12) Claisen [3,3] + (14) aza-Claisen [3,3] + (15) thia-Claisen [3,3] sigmatropic isomerizations
  -- the rank-FLAT (1->1) classes, promoting the opt-in :mod:`smartchem.lateral_rewrite` seam (a lateral rewrite has
  no strict-descent decomposition image, so it cannot ride ``search_routes`` auto-discovery -- W1; its consumer is a
  hand-assembled or bounded-lateral-search route (:mod:`smartchem.lateral_search`) the oracle now vouches instead of
  demoting);
  (16) 4-pi electrocyclization (butadiene -> cyclobutene) + (17) 6-pi electrocyclization (hexatriene -> cyclohexadiene)
  -- the THIRD pericyclic archetype, rank-flat ring-open/close isomerizations on the same lateral seam.
  All EIGHT DA classes are locked apart, and the four [3,3] and two electrocyclic classes from each other and from
  every DA class, by their per-family guarded RE-DERIVATION alone (ISSUE-132: no centre is read; the re-derivation is
  the load-bearing separator wherever families share a bond structure) -- none poaches another's steps (the 14x14
  identity matrix in PERICYCLIC-LAYER-A-FUZZ-132 pins this).  ARYL amination (the phenol->aniline fake)
  and masked-carbonyl donors (hemiaminal/acetal condensations) are excluded; other real condensations
  (Friedel-Crafts, Kolbe-Schmitt) and non-sigmatropic isomerizations (tautomerization) are demoted-as-unrecognized:
  honest coverage loss, NOT false-VOUCH. Each remaining class is a future round behind its own gate.
* LOCALITY (R57 debt, CLOSED by R58 span reading) -- a whole-molecule census is non-local, so R56/R57 borrowed
  the generator's k=1 single-cut invariant (``max_reactant_cuts = 1``, the production default). R58 distils the
  reaction-centre span the generator already computes (``CappedScission.cut``/``.caps``) into a coordinate-free
  :class:`~smartchem.reaction_center.ReactionCenter` carried on the step, and both condensation recognizers CHECKED
  the centre is a single connected elementary condensation (:meth:`ReactionCenter.is_elementary_condensation`) rather
  than trusting the config. This made the k=1 assumption a structural FACT (config-robust: 48 reachable k=2 acyl
  bundles and the k=2 ether bundles that forge the elementary net signature are demoted by their non-elementary
  spans), and the span-local ether check retired the R57 clause (iii) blacklist -- RECOVERING 40 production-reachable
  genuine etherifications whose reactant contains an unrelated ether (``methanol + 2-methoxyethanol ->
  1,2-dimethoxyethane + water``).
  CONTENT-DETERMINISM (ISSUE-126 for the condensations, ISSUE-132 for the pericyclics) now SUPERSEDES the R58
  trusted-centre read entirely: NO recognizer reads the step's ``reaction_center`` for a vouch any longer.  The three
  condensation recognizers re-derive their locality witness by an independent single-cut scission
  (:func:`_condensation_rederives`); the fourteen pericyclic recognizers re-derive theirs by their family's guarded
  retro (``_reactant_*_disconnects_to`` / ``_reactant_rewrites_to``).  Recognition is therefore a PURE FUNCTION of
  the conserved reactant/product molecules: a forged OR absent centre can neither mint nor block a vouch, a genuine
  centre-less step is recognized, and a bundled multi-cut fiction (needing >=2 cuts / an extra retro event) is never
  re-derived.  So centre-omission or forgery can never mint a vouch (the no-false-vouch cardinal holds for a caller
  controlling every untrusted input field) nor, now, cost one.  The load-time authority
  :meth:`CompilationResponse._check_frontier_coherence` re-derives the same content-deterministic fiction channel.
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

from dataclasses import dataclass

from ..decompiler import Formula

__all__ = [
    "recognize_reaction_type",
    "recognize_reaction_type_outcome",
    "route_reaction_type_blockers",
    "route_reaction_type_diagnostics",
    "RecognitionOutcome",
]

#: ISSUE-131 recognition-outcome kinds.  Three materially different scientific outcomes the old ``str | None``
#: API conflated: a genuine class MATCH, an honest ABSTAIN (no attested class matched), and an
#: INTERNAL_RECOGNIZER_ERROR (a recognizer raised -- an INSTRUMENT failure, NOT evidence of non-reaction).
MATCH = "MATCH"
ABSTAIN = "ABSTAIN"
INTERNAL_RECOGNIZER_ERROR = "INTERNAL_RECOGNIZER_ERROR"


@dataclass(frozen=True)
class RecognitionOutcome:
    """The typed result of reaction-TYPE recognition (ISSUE-131).

    The no-false-vouch law is preserved EXACTLY: an exception NEVER becomes a MATCH (a raising recognizer is
    recorded as a fault and recognition continues), so an internal error can only make a step LESS recognized.
    The added value is pure OBSERVABILITY -- a caller/telemetry can now tell an instrument failure
    (``INTERNAL_RECOGNIZER_ERROR``, with the offending recognizer + exception carried in ``faults``) apart from a
    genuine ``ABSTAIN``, which the fail-closed ``str | None`` API and ``route_reaction_type_blockers`` still
    collapse to the same demotion.
    """

    kind: str
    reaction_class: "str | None" = None
    #: ((recognizer_name, "ExcType: message"), ...) -- the recognizers that RAISED, for provenance/diagnostics.
    faults: tuple = ()

    @property
    def is_match(self) -> bool:
        return self.kind == MATCH

    @property
    def is_internal_error(self) -> bool:
        return self.kind == INTERNAL_RECOGNIZER_ERROR


def recognize_reaction_type_outcome(step) -> RecognitionOutcome:
    """Typed recognition (ISSUE-131): MATCH(class) / ABSTAIN / INTERNAL_RECOGNIZER_ERROR(faults).

    First positive predicate wins a MATCH (recording any faults seen before it, for provenance).  A recognizer
    that RAISES is recorded as a fault and the scan continues -- it never yields a MATCH.  If no recognizer
    matched and at least one raised, the outcome is INTERNAL_RECOGNIZER_ERROR (the step is still demoted by the
    fail-closed API, but the caller can now see it was an instrument failure, not a clean non-match).  No raise,
    no match -> ABSTAIN.
    """
    faults: list[tuple[str, str]] = []
    for name, predicate in _RECOGNIZERS:
        try:
            if predicate(step):
                return RecognitionOutcome(MATCH, name, tuple(faults))
        except Exception as exc:  # fail-closed: a raising recognizer ABSTAINS, recorded as an instrument fault
            faults.append((name, f"{type(exc).__name__}: {exc}"))
    if faults:
        return RecognitionOutcome(INTERNAL_RECOGNIZER_ERROR, None, tuple(faults))
    return RecognitionOutcome(ABSTAIN, None, ())


_WATER_CACHE: list = []
#: Content-keyed memo for the re-derivation (ISSUE-126 Phase II).  Recognition is content-deterministic, so the
#: verdict depends only on (target identity, the two precursor identities, the nucleophile set); caching it collapses
#: the repeated recognition of the same step across candidate routes in the ranking hot path (the #127 cost surface)
#: to one scission enumeration.  Bounded to stay safe in a long-lived process.
_REDERIVE_CACHE: dict = {}
_REDERIVE_CACHE_MAX = 65_536


def _water():
    """A cached neutral water molecule, the coproduct the condensation re-derivation expels (lazy -- avoids an
    import-time dependency on the SMILES parser from this module)."""
    if not _WATER_CACHE:
        from ..smiles import parse_smiles
        _WATER_CACHE.append(parse_smiles("O"))
    return _WATER_CACHE[0]


def _condensation_rederives(step, nucleophiles) -> bool:
    """INDEPENDENTLY re-derive an elementary dehydrative condensation from the step's OWN molecules (ISSUE-126 PhII).

    The acyl / ether / N-alkylation recognizers need a LOCALITY/elementarity witness: that the step is a SINGLE
    elementary condensation, not a bundled multi-cut fiction that forges the same whole-molecule census (the lactide
    ``2 lactic acid -> lactide + 2 water`` double condensation).  R58 read that witness off a ``reaction_center``
    carried on the step -- but a stored field is forgeable (``dataclasses.replace``, an arbitrary duck-typed
    ``from_transform`` transform), so it is no longer trusted for ANY vouch.

    This re-derives the witness the way the Diels-Alder families derive their Layer A: it reruns the GENERATOR'S OWN
    single-cut capped scission on the step's TARGET, consuming one water, and asks whether SOME single cut
    disconnects the target into EXACTLY the step's two non-water precursors with an elementary-condensation centre
    onto ``nucleophiles``.  The reverse of one single-cut elementary scission IS, by construction, one genuine
    elementary condensation; a bundled fiction needs ``>= 2`` cuts and so can NEVER be re-derived here -- it is
    demoted independently of whatever centre was attached.

    COST (the #127 hot-path surface).  An elementary dehydrative condensation forms an order-1 ``C-X`` bond, so the
    only cut that can disconnect the target into the precursors is at one of the target's order-1 ``C-X`` bonds --
    the enumeration is restricted to those (:func:`~smartchem.structure_descent.single_cut_capped_scissions`) rather
    than every C-H/C-C bond, and the content-deterministic verdict is memoised.  Restricting the bonds cannot miss a
    genuine condensation (its formed bond is exactly such a bond), so it is a pure pre-filter.

    Sound and FAIL-CLOSED (never a false-vouch).  A target the capper refuses (a charged species / pathological
    graph), a budget-truncated enumeration, or simply no matching single cut all return ``False`` -- honest coverage
    loss, never a vouch.  A ``True`` is returned ONLY when the target provably assembles from the two precursors by
    one elementary condensation, so the witness is exactly the generator's single-cut invariant, now INDEPENDENTLY
    recomputed from the molecules rather than asserted by a trusted field (the content-determinism invariant).
    ([[a-whole-set-count-classifier-is-fooled-by-non-locality]] [[a-verifier-that-cannot-verify-must-fail-closed]])
    """
    from ..smiles import resonance_identity
    from .feasibility import _is_water
    non_water_products = [m for m in getattr(step, "products", ()) if not _is_water(m)]
    non_water_reactants = [m for m in getattr(step, "reactants", ()) if not _is_water(m)]
    if len(non_water_products) != 1 or len(non_water_reactants) != 2:
        return False
    target = non_water_products[0]
    from ..diels_alder import is_closed_shell_neutral
    if not (is_closed_shell_neutral(target) and all(is_closed_shell_neutral(m) for m in non_water_reactants)):
        return False  # #132 hardening: a radical / charged / ylide partner is not a condensation reactant (fail-closed)
    try:
        want = tuple(sorted(resonance_identity(r) for r in non_water_reactants))
        key = (resonance_identity(target), want, tuple(nucleophiles))
    except (NotImplementedError, TypeError, ValueError):
        return False  # a species that will not canonicalise -> fail-closed demote
    cached = _REDERIVE_CACHE.get(key)
    if cached is not None:
        return cached
    result = _rederive_condensation(target, want, nucleophiles)
    if len(_REDERIVE_CACHE) < _REDERIVE_CACHE_MAX:
        _REDERIVE_CACHE[key] = result
    return result


def _rederive_condensation(target, want: tuple, nucleophiles) -> bool:
    """The uncached re-derivation: does ``target`` single-cut-disconnect into the precursor identities ``want`` via
    one elementary dehydrative condensation onto ``nucleophiles``?  Restricted to the target's order-1 ``C-X`` bonds
    (the only bonds an elementary condensation can form), then gated by the full :class:`CappedScission` certificate
    and :meth:`~smartchem.reaction_center.ReactionCenter.is_elementary_condensation`."""
    from ..structure_descent import single_cut_capped_scissions, ScissionError
    from ..smiles import resonance_identity
    nuc = set(nucleophiles)
    atoms = getattr(target, "atoms", ())
    candidate = []
    for b in sorted(getattr(target, "bonds", ())):
        if getattr(b, "order", None) != 1:
            continue
        pair = {atoms[b.i], atoms[b.j]}
        if "C" in pair and (pair & nuc):  # an order-1 carbon--nucleophile bond: the condensation locus
            candidate.append(b)
    if not candidate:
        return False
    try:
        scissions, _complete = single_cut_capped_scissions(target, (_water(),), tuple(candidate))
    except (ScissionError, NotImplementedError, TypeError, ValueError):
        return False  # target cannot be single-cut re-derived (e.g. charged) -> fail-closed demote, never vouch
    for cs in scissions:
        try:
            if tuple(sorted(resonance_identity(p) for p in cs.products)) != want:
                continue
            if cs.reaction_center().is_elementary_condensation(nucleophiles):
                return True
        except Exception:
            continue  # a pathological scission is skipped; an error can only make the step LESS recognized
    return False


def _acyl_condensation(step) -> bool:
    """Recognizer: an intermolecular acyl condensation (esterification / amidation / thioesterification), R58.

    Class identity is the R48-hardened whole-molecule predicate (a free acid net-consumed, an acyl carbonyl
    net-formed within the elementary intermolecular shape).  Its fail-OPEN use as a feasibility DOMAIN GUARD in
    :mod:`smartchem.experiment.feasibility` (firing means "refuse to vouch the derived DeltaG") is a DIFFERENT job
    than this module's fail-CLOSED type VOUCH; the shared thing is only the detector, which this module leaves
    untouched.

    ELEMENTARITY by RE-DERIVATION (ISSUE-126 Phase II, replacing the R58 trusted-centre read).  The census is
    non-local -- it also fires on a bundled multi-cut step that forges the same net acyl signature (48 reachable k=2
    examples were measured, e.g. the lactide ``2 lactic acid -> lactide + 2 water`` double condensation).  R58
    excluded those by reading a single-elementary-condensation :class:`~smartchem.reaction_center.ReactionCenter`
    CARRIED on the step; but a stored centre is forgeable (``dataclasses.replace``, a fake ``from_transform``
    transform), so a VOUCH now instead requires :func:`_condensation_rederives` to INDEPENDENTLY re-derive the
    elementary condensation from the molecules -- a single-cut scission of the target disconnecting back into
    EXACTLY the two precursors onto ``{O, N, S}``.  A bundled fiction needs ``>= 2`` cuts and so is never re-derived,
    and is demoted regardless of any attached centre.  Content-deterministic: recognition reads only the conserved
    molecules, so a genuine acyl condensation is vouched whether or not it carries a centre, and no forged annotation
    buys a vouch ([[a-whole-set-count-classifier-is-fooled-by-non-locality]] [[a-verifier-that-cannot-verify-must-fail-closed]])."""
    from .feasibility import _is_intermolecular_acyl_condensation
    if not _is_intermolecular_acyl_condensation(step):
        return False
    # ISSUE-126 Phase II: elementarity/locality is RE-DERIVED from the molecules (an independent single-cut scission),
    # never read from a forgeable supplied centre -- a bundled double condensation (lactide) is not re-derivable here.
    return _condensation_rederives(step, ("O", "N", "S"))


def _etherification(step) -> bool:
    """Recognizer: an intermolecular DEHYDRATIVE etherification (2 R-OH -> R-O-R + water), R58 span-local.

    Class identity is the whole-molecule shape+net census (:func:`~smartchem.experiment.feasibility.
    _ether_shape_and_net_change`): within the elementary intermolecular shape, a dialkyl (sp3 C-O-C) ether is
    net-FORMED and an sp3 alcohol net-CONSUMED (this excludes the aryl-ether fake, which forms no dialkyl ether, and
    the peroxide coupling, which consumes no alcohol; and it excludes esterification, whose formed C-O is an
    ester-O with a carbonyl neighbour, not a dialkyl ether -- so ether and ester share a centre signature but the
    census separates them).

    ELEMENTARITY by RE-DERIVATION (ISSUE-126 Phase II, replacing the R57 clause (iii) blacklist AND the R58 trusted
    centre).  Clause (iii) ("no ether among the reactants") was a non-local blacklist that FALSE-DEMOTED a genuine
    etherification whose reactant merely CONTAINS an unrelated ether (``methanol + 2-methoxyethanol ->
    1,2-dimethoxyethane + water``, a production k=1 miss).  A VOUCH now requires :func:`_condensation_rederives` to
    INDEPENDENTLY re-derive a single elementary dehydrative condensation onto oxygen (``("O",)``) from the molecules
    -- a single-cut scission of the target disconnecting back into exactly the two alcohols.  The spectator ether is
    irrelevant to the re-derived cut, so those 40 reachable steps are recognized, while a bundled fake (needing
    ``>= 2`` cuts) is never re-derived and stays demoted -- content-deterministically, reading no forgeable supplied
    centre (``dataclasses.replace`` / a fake ``from_transform`` transform cannot buy a vouch)."""
    from .feasibility import _ether_shape_and_net_change
    if not _ether_shape_and_net_change(step):
        return False
    # ISSUE-126 Phase II: elementarity RE-DERIVED from the molecules, not read from a forgeable supplied centre.
    return _condensation_rederives(step, ("O",))


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
    run adversaries SEPARATELY from acceptance).  The elementary-condensation check alone (now RE-DERIVED from the
    molecules by :func:`_condensation_rederives` onto ``("N",)``, the SAME signature methylation used -- element pairs
    do not change with chain length) does NOT lock: it certifies "one C-N single bond forms displacing one C-O, H
    migrating N->O", but NOT that the carbon is alkyl nor that the N is a real amine.  The census
    (:func:`~smartchem.experiment.feasibility._n_alkylation_shape_and_net_change`) supplies both,
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

    ELEMENTARITY by RE-DERIVATION (ISSUE-126 Phase II, replacing the R60/R63 trusted-centre read).  The census is
    non-local, and a centre-less homologation forges the net signature: ``N-methylformamide + methanol -> CNCC=O +
    water`` MIGRATES the carbonyl off the N, unmasking a pre-existing alkyl, so the bond census reads a spurious rise
    with no alkyl actually transferred.  A VOUCH therefore requires :func:`_condensation_rederives` to INDEPENDENTLY
    re-derive a single elementary condensation onto nitrogen (``("N",)``) from the molecules; a fiction that merely
    forges the census does NOT disconnect, by one elementary cut, back into the step's declared precursors (if it
    did, it WOULD be a genuine N-alkylation), so it is never re-derived and stays demoted -- content-deterministically,
    reading no forgeable supplied centre ([[a-whole-set-count-classifier-is-fooled-by-non-locality]]
    [[a-verifier-that-cannot-verify-must-fail-closed]])."""
    from .feasibility import _n_alkylation_shape_and_net_change
    if not _n_alkylation_shape_and_net_change(step):
        return False
    # ISSUE-126 Phase II: elementarity RE-DERIVED from the molecules, not read from a forgeable supplied centre.
    return _condensation_rederives(step, ("N",))


_HALOGENS = frozenset({"F", "Cl", "Br", "I"})


def _acyl_adjacency(molecule):
    adj: dict = {}
    for b in molecule.bonds:
        adj.setdefault(b.i, []).append((b.j, b.order))
        adj.setdefault(b.j, []).append((b.i, b.order))
    return adj


def _is_leaving_group_acid(molecule) -> bool:
    """The activated-transfer coproduct: a carboxylic acid / carboxylate (``R-COOH`` / ``R-COO-``, the anhydride
    leaving group) or a hydrogen halide ``H-X`` (the acyl-halide leaving group)."""
    from .feasibility import _acyl_group_counts
    if _acyl_group_counts(molecule)[0] >= 1:   # a free acid / carboxylate carbonyl
        return True
    counts = dict(molecule.formula)
    heavy = {k: v for k, v in counts.items() if k != "H"}
    return (getattr(molecule, "charge", 0) == 0 and counts.get("H", 0) == 1 and len(heavy) == 1
            and next(iter(heavy)) in _HALOGENS and heavy[next(iter(heavy))] == 1)   # exactly H-X


def _is_activated_donor(molecule) -> bool:
    """An activated acyl donor: an ANHYDRIDE (a carbonyl C whose single-bonded O bridges to a SECOND carbonyl C) or
    an ACYL HALIDE (a carbonyl C single-bonded to a halogen).  Distinct from a free acid (the condensation donor),
    whose carbonyl O has no heavy neighbour -- so this recognizer never poaches the free-acid condensation class."""
    from .feasibility import _is_carbonyl_carbon
    atoms = molecule.atoms
    adj = _acyl_adjacency(molecule)
    for c in range(len(atoms)):
        if not (atoms[c] == "C" and _is_carbonyl_carbon(c, atoms, adj)):
            continue
        for n, order in adj.get(c, ()):
            if order != 1:
                continue
            if atoms[n] in _HALOGENS:
                return True                                  # acyl halide
            if atoms[n] == "O" and any(n2 != c and atoms[n2] == "C" and _is_carbonyl_carbon(n2, atoms, adj)
                                       for n2, _o in adj.get(n, ())):
                return True                                  # anhydride (bridging O to a 2nd carbonyl)
    return False


def _acyl_ester_amide_thioester_total(molecule) -> int:
    from .feasibility import _acyl_group_counts
    _acid, amide, ester, thioester = _acyl_group_counts(molecule)
    return amide + ester + thioester


def _activated_transfer_rederives(step, target, donor, nucleophile, leaving_group) -> bool:
    """Re-derive the activated acyl transfer FROM THE MOLECULES: does the acylated ``target`` disconnect by ONE
    elementary cut -- capping with the LEAVING-GROUP acid (not water) -- into EXACTLY the declared ``donor`` and
    ``nucleophile``?  The reverse of one single-cut leaving-group-capped scission IS, by construction, one genuine
    elementary acyl transfer; a bundle / a non-transfer needs >=2 cuts or does not reconstruct both precursors, so it
    is never re-derived.  Restricted to the target's order-1 C--(O/N/S) bonds (the acyl--nucleophile locus).  The
    content-determinism analogue of :func:`_condensation_rederives`, with the leaving group in place of water."""
    from ..smiles import resonance_identity
    from ..structure_descent import single_cut_capped_scissions, ScissionError
    atoms = target.atoms
    candidate = tuple(b for b in sorted(target.bonds)
                      if getattr(b, "order", None) == 1 and "C" in {atoms[b.i], atoms[b.j]}
                      and ({atoms[b.i], atoms[b.j]} & {"O", "N", "S"}))
    if not candidate:
        return False
    try:
        want = sorted(resonance_identity(m) for m in (donor, nucleophile))
        scissions, _complete = single_cut_capped_scissions(target, (leaving_group,), candidate)
    except (ScissionError, NotImplementedError, TypeError, ValueError):
        return False   # a target the capper refuses (charged / pathological) -> fail-closed demote, never vouch
    for cs in scissions:
        try:
            if sorted(resonance_identity(p) for p in cs.products) == want:
                return True
        except Exception:
            continue
    return False


def _activated_acyl_transfer(step) -> bool:
    """Recognizer: ACTIVATED acyl transfer -- an anhydride / acyl halide acylates an O/N/S nucleophile (#110).

    A DISTINCT class from the free-acid dehydrative condensation (:func:`_acyl_condensation`): the acyl donor is
    pre-activated, so the coproduct is a CARBOXYLIC ACID (anhydride) or a HYDROGEN HALIDE (acyl halide), NOT water --
    the activated shape is ``donor + Nu-H -> acyl-Nu + leaving-acid`` (2 reactants -> 2 products, no water).  This is
    the §5(A) win: the capped-scission search ALREADY GENERATES these routes (e.g. ``Ac2O + 4-aminophenol ->
    paracetamol + AcOH``, ``AcCl + MeNH2 -> N-methylacetamide + HCl``) but the free-acid census demotes them for
    lacking a water coproduct; this recognizer vouches the genuine ones WITHOUT lifting any unrelated fiction.

    SCOPE (honest): O/N/S nucleophiles only -- a C-nucleophile Friedel-Crafts acylation (``benzene + Ac2O ->
    acetophenone``) is a real activated transfer this does NOT vouch (it wants a Lewis-acid activator #107 + arene
    guards), honest coverage loss, never a false-vouch.  Small targets reachable only via a large donor (acetamide /
    methyl acetate via Ac2O) are blocked UPSTREAM by the #104 W1 atom-count wall (the donor would be a larger
    fragment than the target), so the search never emits them -- a generation boundary, not a recognizer gap.

    CONSERVATION-LOCK (the admission proof, mirroring the condensation recognizers).  Within the activated shape and
    with every species CLOSED-SHELL NEUTRAL (#132 guard), a vouch requires :func:`_activated_transfer_rederives` to
    INDEPENDENTLY re-derive the transfer: the acylated target must disconnect by ONE elementary cut, capping with the
    declared leaving-group acid, into EXACTLY the declared donor + nucleophile.  The census fixes the functional
    TYPES (an anhydride/acyl-halide donor consumed, an ester/amide/thioester net-formed, a carboxylic-acid/H-X
    leaving group produced); the single-cut re-derivation then forces those types onto one genuine elementary acyl
    transfer -- a bundle or a non-transfer cannot reconstruct both declared precursors by one leaving-group cut.
    Content-deterministic: reads only the conserved molecules, no caller-supplied centre.  (Problem A type-validity
    only; feasibility -- these want the activation they already carry -- is Problem B.)
    ([[a-whole-set-count-classifier-is-fooled-by-non-locality]] [[a-verifier-that-cannot-verify-must-fail-closed]])"""
    from .feasibility import _is_water
    from ..diels_alder import is_closed_shell_neutral
    reactants = tuple(getattr(step, "reactants", ()))
    products = tuple(getattr(step, "products", ()))
    if len(reactants) != 2 or len(products) != 2:
        return False
    if any(_is_water(m) for m in reactants) or any(_is_water(m) for m in products):
        return False   # a water coproduct is the free-acid condensation class, not activated transfer
    if not all(is_closed_shell_neutral(m) for m in reactants + products):
        return False   # #132 hardening: a radical / charged / ylide partner is not an acyl-transfer species
    lg = [i for i, m in enumerate(products) if _is_leaving_group_acid(m)]
    donors = [i for i, m in enumerate(reactants) if _is_activated_donor(m)]
    if len(lg) != 1 or len(donors) != 1:
        return False
    leaving_group, target = products[lg[0]], products[1 - lg[0]]
    donor, nucleophile = reactants[donors[0]], reactants[1 - donors[0]]
    if _is_activated_donor(target):
        return False   # the "target" must be the acylated product, not another donor (a disproportionation guard)
    # NET: an ester/amide/thioester carbonyl net-forms on the target that the reactants did not carry.
    if _acyl_ester_amide_thioester_total(target) <= (
            _acyl_ester_amide_thioester_total(donor) + _acyl_ester_amide_thioester_total(nucleophile)):
        return False
    return _activated_transfer_rederives(step, target, donor, nucleophile, leaving_group)


def _is_sulfonyl_halide(molecule) -> bool:
    """An activated SULFONYL donor R-SO2-X: a sulfur double-bonded to exactly two oxygens, single-bonded to a
    halogen, and single-bonded to its R carbon.  Distinct from an acyl halide (whose electrophile is a CARBONYL
    carbon, not sulfur), so the #111 sulfonate recognizer never poaches the #110 acyl-transfer donor -- and vice
    versa, an acyl halide is never a sulfonyl halide (no sulfur)."""
    atoms = molecule.atoms
    adj = _acyl_adjacency(molecule)
    for s in range(len(atoms)):
        if atoms[s] != "S":
            continue
        nbrs = adj.get(s, ())
        dbl_o = sum(1 for n, o in nbrs if atoms[n] == "O" and o == 2)
        has_halide = any(atoms[n] in _HALOGENS and o == 1 for n, o in nbrs)
        has_carbon = any(atoms[n] == "C" and o == 1 for n, o in nbrs)
        if dbl_o == 2 and has_halide and has_carbon:
            return True
    return False


def _sulfonate_ester_bond_count(molecule) -> int:
    """Count GENUINE alkyl sulfonate-ester linkages C(sp3)-O-SO2-C: an oxygen single-bonded to an sp3 non-aromatic
    ALKYL-carbinol carbon AND single-bonded to a SULFONATE sulfur (a sulfur bearing two =O AND its own single-bonded
    carbon, the R'-SO2- group).  This is the bond an alkyl sulfonate transfer FORMS; counting it lets the net check
    see exactly one such linkage appear on the sulfonylated target.

    Hardened against three Wave-C adversary false-vouches (evil-morty) -- the earlier loose count (any O on any
    single-bonded carbon and any two-=O sulfur) was a non-local signature SHARED by other classes, the R48 lesson
    one alphabet over:
    * the carbinol carbon must be an sp3 non-aromatic ALKYL carbinol (every bond single) whose only heteroatom
      neighbour is this ester O -- so a CARBOXYLIC-acid O (an acyl C=O carbon; MsCl + R-COOH is a mixed
      carboxylic-sulfonic ANHYDRIDE, a DIFFERENT class, not a sulfonate ester) and a MASKED-carbonyl O (a gem-diol /
      hemiacetal / enol -- a hydrate or tautomer of a carbonyl, not an isolable alcohol) are NOT counted.  This is
      exactly :func:`~smartchem.experiment.feasibility._alkyl_carbinol_alcohol_count`'s donor-half lock (dalembert
      KILL 1), applied at the formed O-S locus.
    * ARYL-O (a phenol sulfonate) is honest COVERAGE LOSS here, NOT a false-vouch: a Kekulized aryl carbinol carbon
      carries a ring C=C indistinguishable from an acyclic enol in this aromaticity-free graph representation, so
      the sound narrow scope is ALKYL-O only; aryl sulfonate esters are deferred to a 2.0 aromaticity model (#105).
    * the sulfonate sulfur must bear its OWN single-bonded carbon (R'-SO2-), so a dialkyl SULFATE's O-SO2-O bridge
      and a chlorosulfate are not miscounted as sulfonate-ester linkages (Finding 3 hardening, closed before any
      donor-gate widening could make it bite).

    CALLER CONTRACT: this census reads bond ORDERS, not a per-atom valence/charge model, so it trusts its caller to
    have gated CLOSED-SHELL NEUTRALITY first -- a hypervalent / drawn-neutral sulfur is kept out of the count only by
    the ``is_closed_shell_neutral`` guard that :func:`_sulfonate_ester_transfer` evaluates BEFORE this (the sole call
    site).  A future caller invoking this without that preceding gate inherits a potential miscount."""
    atoms = molecule.atoms
    adj = _acyl_adjacency(molecule)

    def _is_sulfonate_s(n: int) -> bool:
        nbrs = adj.get(n, ())
        return (atoms[n] == "S"
                and sum(1 for n2, o2 in nbrs if atoms[n2] == "O" and o2 == 2) == 2
                and any(atoms[n2] == "C" and o2 == 1 for n2, o2 in nbrs))

    def _is_alkyl_carbinol_c(c: int, ester_o: int) -> bool:
        nbrs = adj.get(c, ())
        if atoms[c] != "C" or any(order != 1 for _n, order in nbrs):
            return False   # sp3, non-aromatic, non-carbonyl, non-enol: every bond single (kekulized aryl/C=O/C=C out)
        other_heavy = [n for n, _o in nbrs if atoms[n] != "H" and n != ester_o]
        return all(atoms[n] == "C" for n in other_heavy)   # only heteroatom neighbour is this ester O (no masked C=O)

    count = 0
    for o in range(len(atoms)):
        if atoms[o] != "O":
            continue
        nbrs = adj.get(o, ())
        on_sulfonate_s = any(atoms[n] == "S" and order == 1 and _is_sulfonate_s(n) for n, order in nbrs)
        carbinol = any(order == 1 and _is_alkyl_carbinol_c(n, o) for n, order in nbrs)
        if on_sulfonate_s and carbinol:
            count += 1
    return count


def _is_hydrogen_halide(molecule) -> bool:
    """Exactly H-X (HF / HCl / HBr / HI): the sulfonyl-halide leaving group -- neutral, one H and one halogen, no
    other heavy atom.  (The H-X half of :func:`_is_leaving_group_acid`, narrowed to exclude the carboxylic-acid
    leaving group so the sulfonate recognizer admits only the sulfonyl-HALIDE donor, not a sulfonic anhydride.)"""
    counts = dict(molecule.formula)
    heavy = {k: v for k, v in counts.items() if k != "H"}
    return (getattr(molecule, "charge", 0) == 0 and counts.get("H", 0) == 1 and len(heavy) == 1
            and next(iter(heavy)) in _HALOGENS and heavy[next(iter(heavy))] == 1)


def _sulfonate_transfer_rederives(step, target, donor, nucleophile, leaving_group) -> bool:
    """Re-derive the sulfonate transfer FROM THE MOLECULES: does the sulfonylated ``target`` disconnect by ONE
    elementary cut -- capping with the HYDROGEN-HALIDE leaving group -- into EXACTLY the declared sulfonyl-halide
    ``donor`` and alcohol ``nucleophile``?  Restricted to the target's order-1 O--S(sulfonyl) bonds (the sulfonate
    ester locus -- the bond the transfer forms).  The content-determinism analogue of
    :func:`_activated_transfer_rederives`, cutting the O-S ester bond instead of the acyl C-Nu bond; the reverse of
    one such single-cut capped scission IS one genuine elementary sulfonyl transfer, and a bundle / non-transfer
    cannot reconstruct both declared precursors by one cut.  Fail-closed: a capper refusal / no matching cut -> False."""
    from ..smiles import resonance_identity
    from ..structure_descent import ScissionError, single_cut_capped_scissions
    atoms = target.atoms
    adj = _acyl_adjacency(target)

    def _is_sulfonyl_s(n: int) -> bool:
        return atoms[n] == "S" and sum(1 for n2, o2 in adj.get(n, ()) if atoms[n2] == "O" and o2 == 2) == 2

    candidate = tuple(b for b in sorted(target.bonds)
                      if getattr(b, "order", None) == 1
                      and ((atoms[b.i] == "O" and _is_sulfonyl_s(b.j))
                           or (atoms[b.j] == "O" and _is_sulfonyl_s(b.i))))
    if not candidate:
        return False
    try:
        want = sorted(resonance_identity(m) for m in (donor, nucleophile))
        scissions, _complete = single_cut_capped_scissions(target, (leaving_group,), candidate)
    except (ScissionError, NotImplementedError, TypeError, ValueError):
        return False   # a target the capper refuses (charged / pathological) -> fail-closed demote, never vouch
    for cs in scissions:
        try:
            if sorted(resonance_identity(p) for p in cs.products) == want:
                return True
        except Exception:
            continue
    return False


def _sulfonate_ester_transfer(step) -> bool:
    """Recognizer: SULFONATE-ESTER transfer -- a sulfonyl halide sulfonylates an alcohol O (#111 sub-family).

    The narrow, defensible #111 opening: ``R-OH + R'-SO2-X -> R-O-SO2-R' + H-X`` for an ALKYL carbinol R (methyl
    mesylate / ethyl / isopropyl / benzyl / triflate ester formation).  Structurally the activated-transfer SHAPE of
    #110 (2 reactants -> 2 products, no water, a leaving acid) but with a SULFONYL electrophile (S(=O)2) rather than
    an ACYL one (C=O), so it CANNOT poach #110: #110's donor gate (:func:`_is_activated_donor`) requires an acyl
    carbonyl carbon a sulfonyl halide lacks, and this gate (:func:`_is_sulfonyl_halide`) requires a sulfonyl sulfur
    an acyl halide lacks -- mutually exclusive.

    SCOPE (honest, narrow): an sp3 ALKYL-carbinol O nucleophile (-> an alkyl sulfonate ESTER) and a HYDROGEN-HALIDE
    leaving group only.  Deliberately NOT vouched -- real sulfonyl transfers that are honest COVERAGE LOSS, never a
    false-vouch, each deferred behind its own later gate: an N nucleophile (sulfonamide), an S nucleophile
    (thiosulfonate), a sulfonic-ANHYDRIDE donor, and an ARYL-O nucleophile (a PHENOL sulfonate -- a Kekulized aryl
    carbinol carbon is indistinguishable from an acyclic enol in this aromaticity-free graph, so aryl-O waits on a
    2.0 aromaticity model, #105).  A CARBOXYLIC-acid O is not in scope at all: MsCl/TsCl + R-COOH forms a mixed
    carboxylic-sulfonic ANHYDRIDE (a different #110-adjacent class), and the alkyl-carbinol census below excludes it.

    CONSERVATION-LOCK (mirroring #110, adversary-hardened -- evil-morty Wave C).  Within the activated shape and with
    every species CLOSED-SHELL NEUTRAL, the census fixes the TYPES (exactly one sulfonyl-halide donor consumed,
    exactly one H-X produced, exactly one GENUINE alkyl sulfonate-ester linkage net-formed on the target --
    :func:`_sulfonate_ester_bond_count`, whose sp3-alkyl-carbinol + sulfonate-S discipline is what excludes the
    mixed-anhydride, masked-carbonyl/enol and sulfate false-vouches -- and the target itself not a sulfonyl halide,
    the disproportionation guard); the single-cut re-derivation (:func:`_sulfonate_transfer_rederives`) then forces
    those types onto ONE genuine elementary sulfonyl transfer -- a bundle or a non-transfer cannot reconstruct both
    declared precursors by one H-X-capped O-S cut.  Content-deterministic: reads only the conserved molecules, no
    caller-supplied centre.  (Problem A type-validity only; feasibility -- these want the activation they carry --
    is Problem B.) ([[a-whole-set-count-classifier-is-fooled-by-non-locality]] [[a-verifier-that-cannot-verify-must-fail-closed]])"""
    from ..diels_alder import is_closed_shell_neutral
    from .feasibility import _is_water
    reactants = tuple(getattr(step, "reactants", ()))
    products = tuple(getattr(step, "products", ()))
    if len(reactants) != 2 or len(products) != 2:
        return False
    if any(_is_water(m) for m in reactants + products):
        return False   # a water coproduct is a dehydrative class, not activated sulfonyl transfer
    if not all(is_closed_shell_neutral(m) for m in reactants + products):
        return False   # #132 hardening: a radical / charged / ylide partner is not a sulfonyl-transfer species
    lg = [i for i, m in enumerate(products) if _is_hydrogen_halide(m)]
    donors = [i for i, m in enumerate(reactants) if _is_sulfonyl_halide(m)]
    if len(lg) != 1 or len(donors) != 1:
        return False
    leaving_group, target = products[lg[0]], products[1 - lg[0]]
    donor, nucleophile = reactants[donors[0]], reactants[1 - donors[0]]
    if _is_sulfonyl_halide(target):
        return False   # the product must be the sulfonate ester, not another sulfonyl halide (disproportionation guard)
    # NET: exactly one sulfonate-ester linkage net-forms on the target that the reactants did not carry.
    if _sulfonate_ester_bond_count(target) <= (
            _sulfonate_ester_bond_count(donor) + _sulfonate_ester_bond_count(nucleophile)):
        return False
    return _sulfonate_transfer_rederives(step, target, donor, nucleophile, leaving_group)


def _is_claisen_coproduct_alcohol(molecule) -> bool:
    """The Claisen-condensation coproduct: the protonated leaving alkoxide -- an ALKYL-carbinol MONO-ol
    (methanol / ethanol / ...).  Uses :func:`~smartchem.experiment.feasibility._alkyl_carbinol_alcohol_count`
    (the donor-half lock) so a carboxylic acid, an enol / masked carbonyl or a diol is not miscounted as the
    alcohol coproduct; exactly one oxygen pins it to a mono-ol."""
    from .feasibility import _alkyl_carbinol_alcohol_count
    return _alkyl_carbinol_alcohol_count(molecule) == 1 and sum(1 for a in molecule.atoms if a == "O") == 1


def _claisen_acyl_substituents_ok(adj, atoms, c, alpha) -> bool:
    """The target's ACYL carbon ``c`` (the C=O joined to ``alpha`` by the new C--C bond): its remaining
    substituents must be only C / H / O-alkyl -- an ester / ketone / carbonate acyl -- never a free -OH (acid),
    N (amide), S (thioester) or halogen.  So the donor half was a genuine ester / ketone / carbonate, not an acid
    or an amide (which belong to other classes)."""
    from .feasibility import _is_carbonyl_carbon
    for n, order in adj[c]:
        if n == alpha or (order == 2 and atoms[n] == "O"):
            continue                                       # the new C--C bond, or the carbonyl =O
        if atoms[n] in ("C", "H"):
            continue
        if atoms[n] == "O" and order == 1:                 # an ester alkoxy O--C(sp3 alkyl), not a free -OH / enol
            heavy = [x for x, _o in adj[n] if atoms[x] != "H" and x != c]
            if len(heavy) == 1 and atoms[heavy[0]] == "C" and not _is_carbonyl_carbon(heavy[0], atoms, adj):
                continue
        return False
    return True


def _claisen_flank_ok(adj, atoms, flank, alpha) -> bool:
    """The nucleophile-side FLANK carbonyl ``flank`` (1,3 to the acyl across ``alpha``) must be a KETONE (its one
    non-carbonyl substituent a carbon) or an ESTER (an O-alkyl) -- never an aldehyde (H), amide (N), acid (-OH) or
    thioester (S).  This is the 1,3-dicarbonyl lock's nucleophile half."""
    from .feasibility import _is_carbonyl_carbon
    subs = [(n, order) for n, order in adj[flank] if n != alpha and not (order == 2 and atoms[n] == "O")]
    if len(subs) != 1:
        return False
    n, order = subs[0]
    if atoms[n] == "C":
        return True
    if atoms[n] == "O" and order == 1:
        heavy = [x for x, _o in adj[n] if atoms[x] != "H" and x != flank]
        return len(heavy) == 1 and atoms[heavy[0]] == "C" and not _is_carbonyl_carbon(heavy[0], atoms, adj)
    return False


def _claisen_condensation(step) -> bool:
    """Recognizer: CLAISEN CONDENSATION -- the 1,3-dicarbonyl / beta-ketoester family (#115).

    NOT the Claisen [3,3] sigmatropic rearrangement (that is :func:`_claisen_rearrangement`, a 1->1 isomerization).
    The net class is a 2->2 condensation forming a new C--C bond with loss of an alkoxide (as its alcohol):
        donor-C(=O)-OR'  +  H-CHR-C(=O)-X  ->  donor-C(=O)-CHR-C(=O)-X  +  R'OH
    (two reactants -> two products, no water; one product the alkyl-carbinol mono-ol coproduct, the other the
    1,3-dicarbonyl target).  Genuine members: 2 EtOAc -> ethyl acetoacetate + EtOH; acetone + diethyl carbonate ->
    ethyl acetoacetate + EtOH; acetophenone + EtOAc -> benzoylacetone + EtOH.

    CONSERVATION-LOCK (the admission proof, mirroring #110/#111).  Within the 2->2 shape and with every species
    CLOSED-SHELL NEUTRAL, the census fixes the TYPES (exactly one alkyl-carbinol mono-ol coproduct; a target that
    is a 1,3-dicarbonyl -- an sp3 alpha carbon that RETAINS an H, flanked by a ketone/ester carbonyl, joined to an
    acyl carbon whose substituents are C/H/O-alkyl only).  The single-cut re-derivation then forces those types
    onto ONE genuine elementary condensation: the target must disconnect by ONE elementary C--C cut, capping with
    the ALCOHOL coproduct, into EXACTLY the declared reactants -- AND with the ORIENTATION witness that the alcohol
    caps the ACYL carbon with its O and the ALPHA carbon with its H.  The flipped cap (acyl gets the H -> an
    aldehyde, alpha gets the OR -> an ether/ester) reconstructs a DIFFERENT, fictitious pair -- that is exactly how
    the butanone fiction (AcOH + ethane -> butanone) and the MeCHO + methyl-methoxyacetate orientation fake would
    otherwise slip through -- so without the witness the recognizer would false-vouch; with it they are rejected.
    Content-deterministic: reads only the conserved molecules, no caller-supplied centre; a capper refusal
    (charged / pathological target) fails closed to demote, never vouch.

    SCOPE (honest).  Problem A type-validity only.  The stoichiometric alkoxide/enolate BASE is OUTSIDE the
    conserved equation and is a Problem B / #107 capability-fit question -- a vouch asserts the reaction TYPE, not
    bench feasibility (same honesty as #110).  Dieckmann (intramolecular, 1->2), aldehyde / amide / acid flanks,
    an alpha with no retained H, and donors reachable only via the #104 W1 atom-count wall are honest coverage
    loss (false-UNRECOGNIZED), never false-vouch.
    ([[a-whole-set-count-classifier-is-fooled-by-non-locality]] [[a-verifier-that-cannot-verify-must-fail-closed]])"""
    from ..diels_alder import is_closed_shell_neutral
    from ..smiles import resonance_identity
    from ..structure_descent import ScissionError, _join, single_cut_capped_scissions
    from .feasibility import _is_carbonyl_carbon, _is_water
    reactants = tuple(getattr(step, "reactants", ()))
    products = tuple(getattr(step, "products", ()))
    if len(reactants) != 2 or len(products) != 2:
        return False
    if any(_is_water(m) for m in reactants + products):
        return False                                       # a water coproduct is a dehydrative class, not Claisen
    if not all(is_closed_shell_neutral(m) for m in reactants + products):
        return False                                       # #132: a radical / charged / ylide partner is out
    alc = [i for i, m in enumerate(products) if _is_claisen_coproduct_alcohol(m)]
    if len(alc) != 1:
        return False
    cap, target = products[alc[0]], products[1 - alc[0]]
    if _is_claisen_coproduct_alcohol(target):
        return False                                       # the other product must be the 1,3-dicarbonyl target
    atoms = target.atoms
    adj = _acyl_adjacency(target)
    candidates: list = []
    meta: dict = {}
    for b in sorted(target.bonds):
        if b.order != 1 or atoms[b.i] != "C" or atoms[b.j] != "C":
            continue                                       # the formed Claisen bond is an order-1 C--C bond
        for a, c in ((b.i, b.j), (b.j, b.i)):              # a = alpha carbon, c = acyl carbon
            if not _is_carbonyl_carbon(c, atoms, adj):
                continue
            if any(order != 1 for _n, order in adj[a]):
                continue                                   # alpha must be sp3 (every bond single)
            if sum(1 for n, _o in adj[a] if atoms[n] == "H") < 1:
                continue                                   # the product alpha carbon retains an H
            flank = [n for n, _o in adj[a] if n != c and atoms[n] == "C"
                     and _is_carbonyl_carbon(n, atoms, adj) and _claisen_flank_ok(adj, atoms, n, a)]
            if not flank:
                continue                                   # the 1,3-dicarbonyl lock
            if not _claisen_acyl_substituents_ok(adj, atoms, c, a):
                continue
            candidates.append(b)
            meta.setdefault(b, []).append((a, c))
    if not candidates:
        return False
    want = sorted(resonance_identity(m) for m in reactants)
    try:
        scissions, _complete = single_cut_capped_scissions(target, (cap,), tuple(candidates))
    except (ScissionError, NotImplementedError, TypeError, ValueError):
        return False                                       # a target the capper refuses -> fail-closed demote
    n = len(target.atoms)
    for cs in scissions:
        try:
            if sorted(resonance_identity(p) for p in cs.products) != want:
                continue
            joined_atoms, _bonds, _off = _join(cs.reactant, cs.reagents)   # the capper's own joined index space
            internal = [b for b in cs.cut if b.i < n and b.j < n]
            if len(internal) != 1 or len(cs.cut) != 2:
                continue                                   # exactly one target C--C cut + the alcohol's O--H cut
            cap_pairs = [(b.i, b.j) for b in cs.caps]
            for a, c in meta.get(internal[0], []):
                acyl_gets_o = any(c in p and any(q >= n and joined_atoms[q] == "O" for q in p) for p in cap_pairs)
                alpha_gets_h = any(a in p and any(q >= n and joined_atoms[q] == "H" for q in p) for p in cap_pairs)
                if acyl_gets_o and alpha_gets_h:
                    return True                            # genuine orientation: acyl<-O, alpha<-H
        except Exception:
            continue
    return False


def _alkyne_diels_alder(step) -> bool:
    """Recognizer: an all-carbon Diels-Alder [4+2] cycloaddition (diene + ALKYNE dienophile -> 1,4-cyclohexadiene).

    The fifth active class, and the FIRST pericyclic recognizer that keeps a second unsaturation in the adduct: an
    alkyne dienophile donates its second pi bond into the ring, so the product is 1,4-cyclohexadiene (verified
    chemistry), not the fully-saturated-except-one-alkene cyclohexene the alkene family makes.  It is a straight
    clone of :func:`_diels_alder`'s re-derivation discipline against the alkyne sibling family
    (:func:`~smartchem.diels_alder._reactant_alkyne_da_disconnects_to`), so it inherits the SAME soundness argument
    rather than a hand-rolled second one: the guarded alkyne [4+2] retro is re-derived from the step's own molecules
    (never the transform type, never a caller-supplied centre), and its distinct formed/broken bond structure keeps
    the alkyne class from cross-poaching the alkene one -- a fuzz-verified sound sole gate + separator (ISSUE-132).

    SCOPE: only alkyne-dienophile -> 1,4-cyclohexadiene.  An allene dienophile or an alkyne embedded in a larger
    conjugated system is genuine [4+2] chemistry this recognizer does NOT vouch -- honest coverage loss
    (false-UNRECOGNIZED, safe), never a false-vouch."""
    from ..diels_alder import _reactant_alkyne_da_disconnects_to
    reactants = tuple(step.reactants)
    products = tuple(step.products)
    if len(products) != 1 or len(reactants) != 2:
        return False
    # ISSUE-132 content-determinism: the guarded alkyne [4+2] retro re-derived from the molecules IS the vouch; no
    # caller-supplied centre is read (a fuzz-verified sound sole gate + separator -- PERICYCLIC-LAYER-A-FUZZ-132).
    return _reactant_alkyne_da_disconnects_to(products[0], reactants)


def _diels_alder(step) -> bool:
    """Recognizer: an all-carbon Diels-Alder [4+2] cycloaddition (diene + ALKENE dienophile -> cyclohexene adduct).

    SCOPE (honest, per the adversary gate): only the alkene-dienophile -> cyclohexene family is recognized.  An
    alkyne dienophile (butadiene + acetylene -> 1,3-cyclohexadiene) or an allene/exocyclic-alkene dienophile is a
    genuine [4+2] this recognizer does NOT vouch -- honest coverage loss (false-UNRECOGNIZED, safe), never a
    false-vouch; the family rule fixes an alkene dienophile.

    Conservation-locked like its siblings, but the lock is the DA family's own re-derivation certificate rather than
    a functional-group census (a pericyclic reaction has no dehydrative signature).  The vouch is a single content
    re-derivation (ISSUE-132: no caller-supplied centre is read):
    re-derive [4+2]-ness FROM THE STEP'S OWN MOLECULES, never from the transform type -- the step must be a 2->1
    combination whose single product admits a GUARDED retro-Diels-Alder disconnecting into exactly the two reactants
    (:func:`smartchem.diels_alder._reactant_da_disconnects_to`).  A mass-balancing 2->1 combination that is NOT a
    genuine [4+2] is refused -- conservation alone does not prove a cycloaddition (the load-bearing certificate; a
    budget-exhausted retro DEMOTES, never vouches -- fail-closed).  Elementarity is intrinsic: one guarded retro
    yielding EXACTLY the two declared reactants cannot be a bundled double adduct.  The guarded retro is a
    fuzz-verified sound sole gate + separator (PERICYCLIC-LAYER-A-FUZZ-132), so no reaction-centre read is needed for
    soundness, tamper-resistance (re-derivation reads molecules, not a forgeable field) or separation; a genuine
    centre-less step is recognized.  Structural type-validity only (Problem A): no feasibility/endo-exo/regiochemistry.

    HOT PATH (load-bearing reachability, evil-morty): this runs via :func:`route_reaction_type_blockers` in
    production route ranking for ALL users, so Layer A's retro runs on every 2->1 step's product (cheap ~1 ms; the
    pre-filter in ``_reactant_da_disconnects_to`` skips the common acyclic fragment).  It is a no-op for non-opt-in
    users ONLY because the default single-cut (``max_reactant_cuts = 1``) CappedScission cannot emit a ring-forming
    2->1 step -- a reachability property, NOT structural.  Enable a carbocyclic 2->1 provider (or raise the cut
    budget) and DA vouches begin firing in production: the intended, sound behaviour, not a regression."""
    from ..diels_alder import _reactant_da_disconnects_to
    reactants = tuple(step.reactants)
    products = tuple(step.products)
    if len(products) != 1 or len(reactants) != 2:
        return False
    # ISSUE-132 content-determinism: the guarded [4+2] retro re-derived from the molecules IS the vouch; no
    # caller-supplied centre is read (a fuzz-verified sound sole gate + separator -- PERICYCLIC-LAYER-A-FUZZ-132).
    return _reactant_da_disconnects_to(products[0], reactants)


def _hetero_diels_alder(step, family) -> bool:
    """The shared re-derivation discipline for a HETEROATOM-dienophile Diels-Alder [4+2] family (aza: X=N, oxa: X=O),
    parameterized by the family descriptor (:data:`smartchem.diels_alder.AZA_DA` / :data:`~smartchem.diels_alder.
    OXA_DA`).  Identical soundness argument to :func:`_diels_alder`, against the family's own relabeled re-derivation:
    the guarded [4+2] retro for THIS family is re-derived from the step's own molecules
    (:func:`~smartchem.diels_alder._reactant_hetero_da_disconnects_to`), whose ``(C, X, .)`` bond structure is
    distinct from every other family's -- so the families cannot cross-poach even where they share a centre, which is
    exactly why the re-derivation (not the centre) is the separator (PERICYCLIC-LAYER-A-FUZZ-132)."""
    from ..diels_alder import _reactant_hetero_da_disconnects_to
    reactants = tuple(step.reactants)
    products = tuple(step.products)
    if len(products) != 1 or len(reactants) != 2:
        return False
    # ISSUE-132 content-determinism: this family's guarded hetero [4+2] retro re-derived from the molecules IS the
    # vouch; no caller-supplied centre is read (a fuzz-verified sound sole gate + separator).
    return _reactant_hetero_da_disconnects_to(family, products[0], reactants)


def _aza_diels_alder(step) -> bool:
    """Recognizer: an aza-Diels-Alder [4+2] cycloaddition (diene + imine C=N -> tetrahydropyridine).

    The SIXTH active class, and the FIRST heteroatom (non-all-carbon) pericyclic recognizer -- the ground the
    all-carbon DA families opened onto a heteroatom dienophile.  Delegates to :func:`_hetero_diels_alder` bound to
    :data:`smartchem.diels_alder.AZA_DA`, so it inherits the DA re-derivation soundness argument (the family's
    guarded retro IS the gate) against the aza family's own ``(C, N, .)`` bond structure, which no other family's
    re-derivation reconstructs -- no cross-poach, no centre read (ISSUE-132).

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

    The NINTH active class, and the FIRST recognizer whose separation from a sibling rests on the RE-DERIVATION
    alone.  The heteroatom is now in the DIENE (vertex 0), not the dienophile, so this family and
    :func:`_aza_diels_alder` share an IDENTICAL formed/broken bond structure (the ``(C,N,.)`` multiset is invariant to
    where the single N sits in the ring) -- a reaction-centre would NOT distinguish them (which is one reason ISSUE-132
    stopped reading one).  The re-derivation does: the two adducts are distinct regio-isomers (N adjacent to the ring
    C=C for THIS diene family, N isolated for the dienophile family), so
    :func:`~smartchem.diels_alder._reactant_hetero_da_disconnects_to` bound to :data:`AZA_DIENE_DA` re-derives ONLY the
    1-azadiene adduct into these reactants and abstains on the dienophile adduct (fuzz-verified no cross-poach --
    PERICYCLIC-LAYER-A-FUZZ-132).  Delegates to :func:`_hetero_diels_alder`, so the re-derivation-is-the-gate soundness
    argument is inherited unchanged."""
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
    """The shared re-derivation discipline for the rank-FLAT (1->1) lateral recognizers -- the [3,3] sigmatropic
    isomerizations (Cope / Claisen) AND the electrocyclizations.  Same soundness argument as the DA recognizers
    against the lateral family's own re-derivation: THIS family's guarded [3,3]/electrocyclic rewrite is re-derived
    from the step's own single molecule (:func:`~smartchem.lateral_rewrite._reactant_rewrites_to` -- conservation
    alone proves nothing, since every isomer balances mass, so the re-derivation IS the gate, and it is a
    fuzz-verified sound sole gate + separator, PERICYCLIC-LAYER-A-FUZZ-132).  A 1->1 shape early-out keeps this a
    cheap no-op for the common (2->1 / 2->2) production step."""
    from ..lateral_rewrite import _reactant_rewrites_to
    reactants = tuple(step.reactants)
    products = tuple(step.products)
    if len(reactants) != 1 or len(products) != 1:
        return False
    # ISSUE-132 content-determinism: the guarded rank-flat rewrite re-derived from the molecules IS the vouch; no
    # caller-supplied centre is read (every isomer balances mass, so the re-derivation alone is load-bearing).
    return _reactant_rewrites_to(family, products[0], reactants)


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
#: alkyne-dienophile sibling ADDS a fifth entry (its own distinct re-derivation), the first pericyclic class
#: that keeps a second unsaturation in the adduct (1,4-cyclohexadiene, not cyclohexene).  The aza- and oxa-DA
#: recognizers ADD a SIXTH and SEVENTH entry -- the first HETEROATOM pericyclic classes (diene + imine ->
#: tetrahydropyridine; diene + carbonyl -> dihydropyran), each with its own heteroatom-bearing re-derivation.  All
#: 14 pericyclic classes are locked apart by their per-family guarded RE-DERIVATION alone (ISSUE-132: no centre is
#: read; the 14x14 identity matrix in PERICYCLIC-LAYER-A-FUZZ-132 pins no cross-poach), so none can poach another's
#: steps.
def _is_dihydrogen(mol) -> bool:
    """True iff ``mol`` is neutral dihydrogen H2 (the pair a hydrogenation consumes)."""
    atoms = getattr(mol, "atoms", ())
    return len(atoms) == 2 and all(a == "H" for a in atoms) and getattr(mol, "charge", 0) == 0


def _is_conjugated_ring_system(mol) -> bool:
    """Fail-closed proxy for an aromatic / conjugated-RING species: the (connected) molecule is CYCLIC
    (|bonds| >= |atoms|) AND carries >= 2 multiple (order >= 2) bonds. Benzene (3 ring doubles) and the
    cyclohexadienes (2) match; an ISOLATED ring double (cyclohexene) and an ACYCLIC polyene (butadiene)
    do not. Used to DEFER aromatic-ring bond-order reductions: an aromatic ring does not partial-
    hydrogenate as a clean single-H2 step (the Kekule-edit fiction #114's adversary flagged)."""
    atoms = getattr(mol, "atoms", ())
    bonds = getattr(mol, "bonds", ())
    if len(bonds) < len(atoms):  # a tree (|E| = |V|-1) is acyclic
        return False
    return sum(1 for b in bonds if getattr(b, "order", 1) >= 2) >= 2


def _reduce_one_unsaturation(mol, a: int, b: int):
    """The candidate PRECURSOR obtained from ``mol`` by raising the heavy-heavy bond ``(a, b)`` one order and
    removing one explicit H from EACH endpoint -- the exact graph-inverse of adding H2 across one unsaturation.
    Returns the canonical :class:`Molecule`, or ``None`` if an endpoint has no strippable H, if ``(a, b)`` is not
    a bond, or if the result will not materialise (disconnected / malformed).

    This reads ONLY ``mol``: it is the STRUCTURALLY-INDEPENDENT recognition witness, deliberately NOT a call into
    the ``bond_order_edit`` family enumerator -- manifest G3 (provider locality) forbids the oracle from naming a
    family enumerator, and the family regenerating its own precursor would be self-agreement, not independent
    evidence (#114 CI repair). Note the rewrite is VALENCE-PRESERVING by construction (-1 H, +1 bond order = net
    zero at each endpoint), so it can never mint a hypervalent fiction out of a valence-sane product."""
    from ..category import Bond, Molecule
    atoms = mol.atoms
    key = (min(a, b), max(a, b))
    if not any((min(x.i, x.j), max(x.i, x.j)) == key for x in mol.bonds):
        return None

    def _an_h_neighbour(v: int):
        # H has valence 1, so a's and b's H neighbours are necessarily distinct atoms (no double-strip risk).
        for x in mol.bonds:
            other = x.j if x.i == v else (x.i if x.j == v else None)
            if other is not None and atoms[other] == "H":
                return other
        return None

    h_a, h_b = _an_h_neighbour(a), _an_h_neighbour(b)
    if h_a is None or h_b is None:
        return None
    removed = {h_a, h_b}
    keep = [i for i in range(len(atoms)) if i not in removed]
    remap = {old: new for new, old in enumerate(keep)}
    new_atoms = tuple(atoms[i] for i in keep)
    new_bonds = set()
    for x in mol.bonds:
        if x.i in removed or x.j in removed:
            continue
        order = x.order + 1 if (min(x.i, x.j), max(x.i, x.j)) == key else x.order
        new_bonds.add(Bond(remap[x.i], remap[x.j], order))
    try:
        return Molecule(new_atoms, frozenset(new_bonds), mol.charge).canonical()
    except (ValueError, TypeError, NotImplementedError):
        return None


def _hydrogenation(step) -> bool:
    """Recognizer (#114): one single unsaturation reduced in the SYNTHESIS direction --
    ``precursor + H2 -> saturated`` (one C=C / C#C / C=O / C=N / C#N reduced by one order, consuming H2).

    SOUND BY A STRUCTURALLY-INDEPENDENT WITNESS (no ``reaction_center`` read -- ISSUE-126/132; no family
    enumerator -- manifest G3). For each heavy-heavy bond of the single heavy PRODUCT whose two endpoints each
    carry an explicit H, :func:`_reduce_one_unsaturation` constructs the candidate precursor (that bond raised one
    order, one H stripped from each end) and the step vouches iff some candidate is canonically IDENTICAL to the
    step's heavy reactant (:func:`~smartchem.smiles.resonance_identity`). The witness is a direct graph comparison
    of the two given molecules -- the oracle's own construction plus the shared canonicaliser, never the
    ``bond_order_edit`` generator regenerating its own output (that would be self-agreement, #114 CI repair).

    WHY THIS IS A CONSERVATION-LOCK (no false-VOUCH): the candidate is the product's heavy skeleton with exactly
    one bond order raised and two H removed at that bond -- it can NEVER add or delete a heavy-heavy edge, so a
    RING-OPENING hydrogenolysis (cyclopropane + H2 -> propane) or any skeletal rearrangement has no candidate
    equal to its precursor and abstains. A same-formula decoy (cyclopropane / cyclobutane / oxirane) differs in
    the heavy edge SET, so no raise-one-order candidate reaches it; recognition rests on ``resonance_identity``
    never merging two distinct constitutions (pinned by the injectivity tests).

    FAIL-CLOSED: a reactant pair that is not exactly {heavy, H2}, a charged/radical partner, a non-(+H2) formula
    delta, a species that will not canonicalise, or no matching candidate all return False -- honest coverage
    loss, never a vouch.

    DEFERRED SCOPE (honest coverage loss, like #111's aryl-O): a CONJUGATED-RING reduction (precursor cyclic with
    >= 2 multiple bonds, e.g. benzene -> cyclohexadiene) abstains; an aromatic ring does not partial-hydrogenate
    as a clean single-H2 step. Isolated ring doubles (cyclohexene -> cyclohexane) and acyclic selective
    hydrogenations (acrolein -> propanal) are kept.

    GEOMETRIC / ISOTOPE BOUNDARY (Problem B, deferred -- a vouch means only "a reduction of this TYPE exists"):
    the graph model carries no bond-angle / ring-strain geometry, so a GEOMETRICALLY impossible precursor
    (anti-Bredt, trans-cycloalkene, strained bridgehead alkene) is still vouched as a TYPE-valid single bond-order
    reduction -- a caller must NOT read the vouch as "the unsaturated precursor can physically exist" (that is
    feasibility, #107). D2/HD are read as H2 (isotope-blind). (dalembert audit.)
    """
    reactants = getattr(step, "reactants", ())
    products = getattr(step, "products", ())
    if len(reactants) != 2 or len(products) != 1:
        return False
    target = products[0]
    heavy = [m for m in reactants if not _is_dihydrogen(m)]
    if len(heavy) != 1 or len(reactants) - len(heavy) != 1:  # exactly one H2 and one heavy precursor
        return False
    precursor = heavy[0]
    from ..diels_alder import is_closed_shell_neutral
    if not (is_closed_shell_neutral(target) and is_closed_shell_neutral(precursor)):
        return False  # a radical / charged / ylide partner is not a hydrogenation reactant (fail-closed)
    if _is_conjugated_ring_system(precursor):
        return False  # defer aromatic-ring reduction (not a clean single-H2 step)
    # fail-closed formula pre-check: a genuine single hydrogenation is EXACTLY +H2 over the precursor.
    tf, pf = target.formula, precursor.formula
    if tf.get("H", 0) - pf.get("H", 0) != 2:
        return False
    if {k: v for k, v in tf.items() if k != "H"} != {k: v for k, v in pf.items() if k != "H"}:
        return False
    from ..smiles import resonance_identity
    try:
        want = resonance_identity(precursor)
    except (NotImplementedError, TypeError, ValueError):
        return False
    heavy_set = {i for i, s in enumerate(target.atoms) if s != "H"}
    for bond in target.bonds:
        if bond.i not in heavy_set or bond.j not in heavy_set:
            continue  # only a heavy-heavy bond carries an unsaturation to reduce
        candidate = _reduce_one_unsaturation(target, bond.i, bond.j)
        if candidate is None:
            continue
        try:
            if resonance_identity(candidate) == want:
                return True  # precursor IS the product with one bond reduced + 2 H at its ends: a hydrogenation
        except (NotImplementedError, TypeError, ValueError):
            continue
    return False


def _valence_upper_bound_sane(mol) -> bool:
    """The ABSOLUTE-valence gate capped scission does NOT provide: every atom's bond-order-sum must not EXCEED the
    maximum closed-shell valence for its element, and the element must be known. Capped scission is valence-
    PRESERVING, not valence-SANE (it checks only relative valence; :class:`Molecule` carries no absolute valence),
    so a hypervalent fiction (a carbon at bond-order-sum 5) is preserved, not refused. This upper-bound check
    rejects that fiction while ACCEPTING the charge-separated nitrate (N at degree 5 = max{3,5}), which the
    stricter exact-valence :func:`is_closed_shell_neutral` wrongly rejects (its terminal [O-] reads degree 1).
    (dalembert kill: a vouched valence-insane 'nitrate ester' walked through the dropped #132 gate.)"""
    from ..diels_alder import _CLOSED_SHELL_VALENCES
    degree: dict = {}
    for b in getattr(mol, "bonds", ()):
        degree[b.i] = degree.get(b.i, 0) + getattr(b, "order", 1)
        degree[b.j] = degree.get(b.j, 0) + getattr(b, "order", 1)
    for idx, el in enumerate(getattr(mol, "atoms", ())):
        allowed = _CLOSED_SHELL_VALENCES.get(el)
        if allowed is None or degree.get(idx, 0) > max(allowed):
            return False
    return True


def _oxoacid_center(mol, z: int) -> bool:
    """Is atom ``z`` (an N or P) a neutral-representation OXOACID centre -- bonded to >= 2 oxygens with at
    least one oxo (=O) bond? Separates a genuine nitrate/phosphate (N/P with oxo) from a hydroxylamine
    O-ether (N, no oxo) or a phosphite (P(III), no oxo)."""
    o_count, has_oxo = 0, False
    for b in getattr(mol, "bonds", ()):
        other = b.j if b.i == z else (b.i if b.j == z else None)
        if other is None:
            continue
        if mol.atoms[other] == "O":
            o_count += 1
            if getattr(b, "order", 1) >= 2:
                has_oxo = True
    return o_count >= 2 and has_oxo


def _oxoacid_ester_loci(mol) -> tuple:
    """The order-1 O-Z ester bonds of ``mol`` where Z in {N, P} is an oxoacid centre and the O is an ALKYL
    ester oxygen (also bonded to a carbon) -- the single condensation locus a nitrate / phosphate ester forms.
    Sulfur is EXCLUDED: the #111 sulfonate recognizer owns C-S oxoacid esters, so keeping Z in {N, P} here
    makes the two recognizers provably disjoint (no cross-poach)."""
    centers = {"N", "P"}
    out = []
    for b in getattr(mol, "bonds", ()):
        if getattr(b, "order", 1) != 1:
            continue
        ai, aj = mol.atoms[b.i], mol.atoms[b.j]
        if "O" not in (ai, aj) or not ({ai, aj} & centers):
            continue
        o_idx = b.i if ai == "O" else b.j
        z_idx = b.j if o_idx == b.i else b.i
        o_has_c = any(
            mol.atoms[(bb.j if bb.i == o_idx else bb.i)] == "C"
            for bb in mol.bonds
            if (bb.i == o_idx or bb.j == o_idx) and (bb.j if bb.i == o_idx else bb.i) != z_idx
        )
        if o_has_c and _oxoacid_center(mol, z_idx):
            out.append(b)
    return tuple(out)


def _oxoacid_ester(step) -> bool:
    """Recognizer (#111 extension): a dehydrative OXOACID ester condensation forming an O-Z ester bond,
    Z in {N, P} -- a NITRATE or PHOSPHATE ester -- with water as coproduct
    (``R-OH + (HO)Z(=O).. -> R-O-Z(=O).. + H2O``).

    SOUND BY RE-DERIVATION (ISSUE-126/132 discipline; no ``reaction_center`` read). It reruns the generator's
    OWN single-cut capped scission on the step's ester target, restricted to its O-Z oxoacid-ester loci and
    capped with water, and vouches ONLY if some single cut disconnects the ester into EXACTLY the step's two
    non-water reactants. The :class:`CappedScission` certificate conserves + W1-descends, so a bundled / multi-cut
    fiction (>= 2 cuts) can never be re-derived -- demoted independently of any stored field.

    SCOPE / FAIL-CLOSED. Z in {N, P} ONLY (sulfur oxoacid esters are the #111 sulfonate recognizer's; sulfate
    esters are a separate deferred extension -- the disjoint scope is what keeps the two from cross-poaching).
    The oxoacid-centre gate separates a genuine nitrate/phosphate from a hydroxylamine O-ether (N, no oxo) or a
    phosphite (P(III), no oxo), which abstain. A nitrate's nitro group carries internal formal +/- yet is NET
    neutral, which capped scission accepts; so -- unlike the C-X condensations -- this does NOT gate on the exact
    ``is_closed_shell_neutral`` (its terminal [O-] reads degree 1 and would reject a genuine nitrate). Capped
    scission is valence-PRESERVING, not valence-SANE, so soundness instead rests on an explicit UPPER-BOUND valence
    gate (:func:`_valence_upper_bound_sane` -- rejects a hypervalent fiction, accepts the nitrate) PLUS the exact-
    identity re-derivation match PLUS the oxoacid-centre gate. No matching cut, a budget-truncated enumeration, a
    valence-insane species, or a non-canonicalising one all return False (honest coverage loss).
    """
    from ..smiles import resonance_identity
    from ..structure_descent import ScissionError, single_cut_capped_scissions
    from .feasibility import _is_water
    non_water_products = [m for m in getattr(step, "products", ()) if not _is_water(m)]
    non_water_reactants = [m for m in getattr(step, "reactants", ()) if not _is_water(m)]
    water_products = [m for m in getattr(step, "products", ()) if _is_water(m)]
    if len(non_water_products) != 1 or len(non_water_reactants) != 2 or not water_products:
        return False
    ester = non_water_products[0]
    # ABSOLUTE-valence sanity (dalembert kill): capped scission PRESERVES but never CHECKS valence, so a
    # hypervalent fiction (a carbon at bond-order-sum 5) would otherwise re-derive and false-vouch.
    if not (_valence_upper_bound_sane(ester) and all(_valence_upper_bound_sane(r) for r in non_water_reactants)):
        return False
    loci = _oxoacid_ester_loci(ester)
    if not loci:
        return False
    try:
        want = tuple(sorted(resonance_identity(r) for r in non_water_reactants))
    except (NotImplementedError, TypeError, ValueError):
        return False
    try:
        scissions, _complete = single_cut_capped_scissions(ester, (_water(),), loci)
    except (ScissionError, NotImplementedError, TypeError, ValueError):
        return False
    for cs in scissions:
        try:
            if tuple(sorted(resonance_identity(p) for p in cs.products)) == want:
                return True  # the ester provably single-cut-disconnects into exactly the declared alcohol + oxoacid
        except Exception:
            continue
    return False


_RECOGNIZERS: tuple[tuple[str, "object"], ...] = (
    ("acyl condensation (esterification/amidation)", _acyl_condensation),
    ("etherification (dehydrative, R-OH + R'-OH -> ether + water)", _etherification),
    ("N-alkylation (dehydrative, non-carbonyl N-H + alkyl-OH -> N-alkyl + water)", _n_alkylation),
    ("activated acyl transfer (anhydride/acyl-halide + R-OH/R-NH/R-SH -> ester/amide/thioester + acid/HX)",
     _activated_acyl_transfer),
    ("sulfonate-ester transfer (sulfonyl halide + R-OH -> sulfonate ester + HX)", _sulfonate_ester_transfer),
    ("Claisen condensation (ester/ketone + ester/carbonate -> 1,3-dicarbonyl + alcohol)", _claisen_condensation),
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
    ("hydrogenation (partial bond-order edit, precursor + H2 -> saturated; one unsaturation reduced)",
     _hydrogenation),
    ("oxoacid ester condensation (alcohol + nitric/phosphoric acid -> nitrate/phosphate ester + water)",
     _oxoacid_ester),
)


def _fstr(molecule) -> str:
    return repr(Formula.of(molecule.formula, molecule.charge))


def _step_equation(step) -> str:
    lhs = " + ".join(sorted(_fstr(m) for m in step.reactants))
    rhs = " + ".join(sorted(_fstr(m) for m in step.products))
    return f"{lhs} -> {rhs}"


def recognize_reaction_type(step) -> str | None:
    """The name of the attested reaction CLASS ``step`` matches, or ``None`` if it matches none.

    TOTAL + FAIL-CLOSED: a recognizer that raises is treated as abstaining, never a spurious match, so an internal
    error can only make a step LESS recognized (more likely demoted), NEVER spuriously vouched. A ``None`` return is
    "unrecognized reaction type", which :func:`route_reaction_type_blockers` turns into a demotion -- it is honest
    non-recognition, never the claim "proven fake".

    This is the STABLE ``str | None`` contract: it collapses both ABSTAIN and INTERNAL_RECOGNIZER_ERROR to ``None``.
    A caller that needs to tell those apart uses :func:`recognize_reaction_type_outcome` (ISSUE-131); this wrapper
    is behaviour-identical to the pre-ISSUE-131 loop.
    """
    return recognize_reaction_type_outcome(step).reaction_class


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


def route_reaction_type_diagnostics(route) -> "tuple[RecognitionOutcome, ...]":
    """Per-step typed recognition outcomes for a route (ISSUE-131 observability).

    :func:`route_reaction_type_blockers` is fail-closed and collapses a genuine ABSTAIN and an
    INTERNAL_RECOGNIZER_ERROR to the SAME "unrecognized reaction type" demotion -- correct for soundness, but it
    leaves release/deployment telemetry unable to tell "insufficient rule coverage" from "a recognizer faulted on
    this substrate".  This additive channel exposes the distinction WITHOUT changing the blocker strings or the
    ``str | None`` recognizer: one :class:`RecognitionOutcome` per step, in step order.  A step whose outcome
    computation itself raises is reported as INTERNAL_RECOGNIZER_ERROR (never silently dropped)."""
    out: list[RecognitionOutcome] = []
    for step in getattr(route, "steps", ()) or ():
        try:
            out.append(recognize_reaction_type_outcome(step))
        except Exception as exc:  # the recognizer harness itself faulted -- an instrument failure, reported as such
            out.append(RecognitionOutcome(INTERNAL_RECOGNIZER_ERROR, None, (("<recognize>", f"{type(exc).__name__}: {exc}"),)))
    return tuple(out)
