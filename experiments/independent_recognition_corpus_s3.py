"""INDEPENDENT-RECOGNITION-CORPUS-S3 -- a held-out, independently-grounded recognition benchmark (OPERATION §3).

Why a SECOND instrument.  The baseline :mod:`experiments.synthesis_coverage_corpus` builds its POSITIVES from the
generator's OWN capped scissions (``_derived``): a reaction the compiler emits, fed back to the compiler's oracle.
That is a useful non-regression lock, but it is NOT independent ground truth -- a generated reaction cannot be its
own ground truth, and a shared bug in the scission grammar would hide in both the generation and the check.  This
corpus is the directive's held-out instrument: every case's molecules are HAND-AUTHORED from named-reaction
chemistry, and every case's LABEL is assigned from chemistry BEFORE the oracle runs.  The oracle verdict is then
compared against that independent label -- the oracle's answer is never the source of truth.

The INDEPENDENCE discipline (the thing that makes this a second bearing, not a bigger copy):
  * Molecules: written by hand as SMILES from textbook named reactions, never pulled from ``capped_scissions``.
  * Labels: ``truth`` (REAL / FICTION / OUTSIDE_GRAMMAR), ``family`` (the chemical class), and ``in_whitelist``
    (is this family one of the oracle's attested classes) are set from chemistry, not from the oracle.
  * Grounding: each case names its chemical grounding.  These are canonical named reactions (esterification,
    Friedel-Crafts acylation, Diels-Alder, aldol, ...) whose EXISTENCE as a reaction class is textbook; the specific
    small-molecule substrate is this author's construction.  No primary-literature yield/condition claim is made --
    only the TYPE of transformation, which is what the oracle judges (Problem A).  Where a class's attribution would
    need a primary source to assert more than "this is a known reaction type", it is marked UNVERIFIED.

Outcome taxonomy (directive §3).  Each (label, observation) pair classifies into exactly one:
  * ``RECOGNIZED``                    -- builds, oracle vouches, truth REAL, family in the whitelist.  (recall hit)
  * ``CORRECTLY_DEMOTED``             -- builds, oracle abstains, truth FICTION.  (the cardinal must-abstain)
  * ``FALSE_VOUCH``                   -- builds, oracle vouches, truth FICTION.  **CARDINAL FAILURE; must be 0.**
  * ``COVERAGE_GAP``                  -- builds, oracle abstains, truth REAL, family OUTSIDE the whitelist.
                                        Honest non-recognition of a real reaction with no attested recognizer -- a
                                        FINDING (what the oracle does not yet cover), never a failure.
  * ``PERICYCLIC_CENTRELESS_RESIDUAL``-- builds, oracle abstains, truth REAL, family in the whitelist BUT the
                                        pericyclic Layer-C fail-closed blocks a centre-less hand-built step.  The
                                        issue #132 residual, surfaced as data, not a failure.
  * ``MUTATION_OFF``                  -- a positive perturbed in one load-bearing structural feature; recognition
                                        MUST flip off (an isomeric target the precursors do not assemble).
  * ``UNREPRESENTABLE``               -- the engine REFUSES to build the step (non-conserving / pathological).

Headline metrics ``measure()`` reports: recall over in-whitelist REAL members, the (must-be-0) FALSE_VOUCH count,
and the catalogue of COVERAGE_GAP + PERICYCLIC_CENTRELESS_RESIDUAL findings (the honest map of what is NOT covered).
``validate()`` asserts the soundness floor: FALSE_VOUCH == 0, every in-whitelist non-residual positive recognized,
every mutation off, every fiction demoted, every unrepresentable refused -- and that the findings match the recorded
expectation (so a silent coverage change is loud).

Run: ``.venv/bin/python -m experiments.independent_recognition_corpus_s3``
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from smartchem.smiles import parse_smiles
from smartchem.conditions import ConditionEnvelope
from smartchem.structure import structure_by_name
from smartchem.reaction_center import ReactionCenter
from smartchem.experiment.step import ExperimentStep
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type

_WATER = structure_by_name("water").molecule

# truth labels (independent of the oracle)
REAL, FICTION, OUTSIDE = "REAL", "FICTION", "OUTSIDE_GRAMMAR"
# outcome taxonomy
RECOGNIZED, CORRECTLY_DEMOTED, FALSE_VOUCH = "RECOGNIZED", "CORRECTLY_DEMOTED", "FALSE_VOUCH"
COVERAGE_GAP, RESIDUAL, MUTATION_OFF, UNREPRESENTABLE = (
    "COVERAGE_GAP", "PERICYCLIC_CENTRELESS_RESIDUAL", "MUTATION_OFF", "UNREPRESENTABLE")

# a forged elementary acyl/ester centre -- the #126 forge descriptor.  Advisory metadata the condensation
# recognizers never read; attaching it to a fiction changes nothing (content-determinism).
_ELEM = ReactionCenter.of((("C", "O", 1), ("H", "O", 1)), (("C", "O", 1), ("H", "O", 1)), 1)


def _hand(reactants, products, target, center=None) -> ExperimentStep:
    """Hand-author a step from SMILES (``"water"`` is the shared water molecule), targeting ``target``'s identity."""
    rs = tuple(parse_smiles(s) for s in reactants)
    ps = tuple(_WATER if s == "water" else parse_smiles(s) for s in products)
    tg = parse_smiles(target)
    tt = next((x for x in ps if dict(x.formula) == dict(tg.formula) and x.charge == tg.charge), ps[0])
    return ExperimentStep.assembling(tt, rs, ps, reagents=(), envelope=ConditionEnvelope.unknown(),
                                     reaction_center=center)


class _FakeTransform:
    """A duck-typed transform with no provider provenance -- the #126 ``from_transform`` forge route."""

    def __init__(self, reactant, products, reagents, center):
        self.reactant, self.products, self.reagents, self._center = reactant, products, reagents, center

    def reaction_center(self):
        return self._center


_LACTIC, _LACTIDE = "CC(O)C(=O)O", "CC1OC(=O)C(C)OC1=O"


def _da_center():
    """The all-carbon Diels-Alder [4+2] reaction centre, for the centre-carrying pericyclic case."""
    from smartchem.diels_alder import _DA_CENTER
    return _DA_CENTER


def _da_with_center() -> ExperimentStep:
    return _hand(("C=CC=C", "C=C"), ("C1CCC=CC1",), "C1CCC=CC1", _da_center())


def _lactide_fake_transform() -> ExperimentStep:
    fake = _FakeTransform(parse_smiles(_LACTIDE), (parse_smiles(_LACTIC), parse_smiles(_LACTIC)),
                          (_WATER, _WATER), _ELEM)
    return ExperimentStep.from_transform(fake)


@dataclass(frozen=True)
class Case:
    name: str
    family: str
    truth: str            # REAL / FICTION / OUTSIDE_GRAMMAR (the independent chemical label)
    in_whitelist: bool    # is ``family`` one of the oracle's attested classes?
    build: object         # () -> ExperimentStep  (may raise for the UNREPRESENTABLE cases)
    grounding: str        # chemical grounding of the LABEL (textbook named reaction, or UNVERIFIED)
    holdout: bool = False # substrate not present in the baseline corpus
    expect: str = ""      # the expected taxonomy outcome (set from the independent label)


def corpus() -> "tuple[Case, ...]":
    W = "textbook named reaction (type attested; specific substrate authored here)"
    return (
        # ========================= CHEMICAL corpus: real members of the whitelist families =========================
        # -- acyl condensation (esterification / amidation / thioesterification) --
        Case("esterification: propanoic acid + ethanol -> ethyl propanoate", "acyl condensation", REAL, True,
             lambda: _hand(("CCC(=O)O", "CCO"), ("CCC(=O)OCC", "water"), "CCC(=O)OCC"), W, expect=RECOGNIZED),
        Case("esterification (holdout): acetic acid + 1-butanol -> butyl acetate", "acyl condensation", REAL, True,
             lambda: _hand(("CC(=O)O", "CCCCO"), ("CC(=O)OCCCC", "water"), "CC(=O)OCCCC"), W, holdout=True,
             expect=RECOGNIZED),
        Case("amidation: acetic acid + methylamine -> N-methylacetamide", "acyl condensation", REAL, True,
             lambda: _hand(("CC(=O)O", "CN"), ("CC(=O)NC", "water"), "CC(=O)NC"), W, expect=RECOGNIZED),
        Case("amidation (holdout): formic acid + ethylamine -> N-ethylformamide", "acyl condensation", REAL, True,
             lambda: _hand(("OC=O", "CCN"), ("CCNC=O", "water"), "CCNC=O"), W, holdout=True, expect=RECOGNIZED),
        Case("thioesterification: acetic acid + methanethiol -> S-methyl thioacetate", "acyl condensation", REAL,
             True, lambda: _hand(("CC(=O)O", "CS"), ("CC(=O)SC", "water"), "CC(=O)SC"), W, holdout=True,
             expect=RECOGNIZED),
        # -- dehydrative etherification --
        Case("etherification: ethanol + methanol -> ethyl methyl ether", "etherification", REAL, True,
             lambda: _hand(("CCO", "CO"), ("CCOC", "water"), "CCOC"), W, expect=RECOGNIZED),
        Case("etherification (holdout): 2 isopropanol -> diisopropyl ether", "etherification", REAL, True,
             lambda: _hand(("CC(C)O", "CC(C)O"), ("CC(C)OC(C)C", "water"), "CC(C)OC(C)C"), W, holdout=True,
             expect=RECOGNIZED),
        # -- dehydrative N-alkylation --
        Case("N-alkylation: dimethylamine + ethanol -> N,N-dimethylethylamine", "N-alkylation", REAL, True,
             lambda: _hand(("CNC", "CCO"), ("CCN(C)C", "water"), "CCN(C)C"), W, expect=RECOGNIZED),
        # -- pericyclic (Diels-Alder [4+2], all-carbon) -- centre present --
        Case("Diels-Alder: butadiene + ethylene -> cyclohexene (centre carried)", "Diels-Alder [4+2]", REAL, True,
             _da_with_center, W, expect=RECOGNIZED),
        # -- pericyclic, centre ABSENT: the former #132 residual, now RECOGNIZED content-deterministically (the
        # pericyclic recognizers re-derive via Layer A alone; no centre is read) --
        Case("Diels-Alder: butadiene + ethylene -> cyclohexene (centre-less, hand-built; #132 closed)",
             "Diels-Alder [4+2]", REAL, True,
             lambda: _hand(("C=CC=C", "C=C"), ("C1CCC=CC1",), "C1CCC=CC1"), W, expect=RECOGNIZED),
        # -- hydrogenation (one single bond-order reduction + H2 -> saturated): the #114 recognizer (21st class).
        # Was a COVERAGE_GAP before #114; now a recognized in-whitelist positive -- the whitelist membership was
        # updated DELIBERATELY after the recognizer was independently established on these substrates (CI repair,
        # plan 1B), never to silence the drift --
        Case("catalytic hydrogenation: ethylene + H2 -> ethane (#114)", "hydrogenation", REAL, True,
             lambda: _hand(("C=C", "[H][H]"), ("CC",), "CC"), W, expect=RECOGNIZED),
        Case("hydrogenation (holdout): acetaldehyde + H2 -> ethanol (C=O reduced)", "hydrogenation", REAL, True,
             lambda: _hand(("CC=O", "[H][H]"), ("CCO",), "CCO"), W, holdout=True, expect=RECOGNIZED),

        # ========================= FICTIONS: mass-balanced but no real reaction (must abstain) ======================
        Case("forged-centre lactide double condensation (direct constructor)", "bundled double condensation",
             FICTION, False, lambda: _hand((_LACTIC, _LACTIC), (_LACTIDE, "water", "water"), _LACTIDE, _ELEM),
             "FICTION: two condensations bundled as one step (needs >=2 cuts); not a reaction",
             expect=CORRECTLY_DEMOTED),
        Case("forged-centre lactide double condensation (dataclasses.replace)", "bundled double condensation",
             FICTION, False,
             lambda: replace(_hand((_LACTIC, _LACTIC), (_LACTIDE, "water", "water"), _LACTIDE, None),
                             reaction_center=_ELEM),
             "FICTION: forge via dataclasses.replace", expect=CORRECTLY_DEMOTED),
        Case("forged-centre lactide double condensation (fake from_transform)", "bundled double condensation",
             FICTION, False, _lactide_fake_transform, "FICTION: forge via a provenance-free transform",
             expect=CORRECTLY_DEMOTED),
        Case("C-C glue fiction: 2 ethanol -> butane + peroxide", "C-C glue", FICTION, False,
             lambda: _hand(("CCO", "CCO"), ("CCCC", "OO"), "CCCC"),
             "FICTION: a new C-C bond, departing O's called 'peroxide'; no such reaction",
             expect=CORRECTLY_DEMOTED),
        Case("reachable glue fiction (R55): isopropanol + ethyl acetate -> isopentyl acetate + water", "C-C glue",
             FICTION, False, lambda: _hand(("CC(C)O", "CCOC(=O)C"), ("CC(C)CCOC(=O)C", "water"), "CC(C)CCOC(=O)C",
                                           _ELEM),
             "FICTION: the #109 reachable over-generation; new C-C bond, not a condensation", expect=CORRECTLY_DEMOTED),
        # -- withheld hydrogenation fiction (#114 no-false-VOUCH): conserved, right shape, +H2, but a SKELETAL
        # cyclization (acyclic diene -> carbocycle), NOT a single bond-order reduction.  The recognizer's
        # no-rearrangement guarantee must refuse it; not used to design the rule --
        Case("hydrogenation fiction: 1,3-butadiene + H2 -> cyclobutane", "hydrogenation (fiction)", FICTION, False,
             lambda: _hand(("C=CC=C", "[H][H]"), ("C1CCC1",), "C1CCC1"),
             "FICTION: +H2 conserves (C4H6 + H2 = C4H8) but butadiene does not cyclize to cyclobutane -- a skeletal "
             "rearrangement, not a bond-order reduction", holdout=True, expect=CORRECTLY_DEMOTED),

        # ========================= NULL: census fires, molecules do not re-derive (clean abstain) ===================
        Case("lactide bundle, centre-less (census fires, re-derivation abstains, no crash)",
             "bundled double condensation", FICTION, False,
             lambda: _hand((_LACTIC, _LACTIC), (_LACTIDE, "water", "water"), _LACTIDE, None),
             "FICTION: non-elementary bundle with no centre", expect=CORRECTLY_DEMOTED),

        # ========================= MUTATION: structural isomer discrimination (must flip off) =======================
        Case("mutation: acetic acid + methanol -> ethyl formate (isomer of methyl acetate)", "acyl condensation",
             FICTION, False, lambda: _hand(("CC(=O)O", "CO"), ("CCOC=O", "water"), "CCOC=O", _ELEM),
             "FICTION: ethyl formate is NOT the condensation product of acetic acid + methanol (isomer swap)",
             expect=MUTATION_OFF),
        Case("mutation: acetic acid + methylamine -> propanamide (isomer of N-methylacetamide)", "acyl condensation",
             FICTION, False, lambda: _hand(("CC(=O)O", "CN"), ("CCC(=O)N", "water"), "CCC(=O)N", _ELEM),
             "FICTION: propanamide is not assembled from acetic acid + methylamine (isomer swap)",
             expect=MUTATION_OFF),

        # ========================= OUTSIDE the grammar: real reactions with NO attested recognizer =================
        Case("aldol addition: 2 acetaldehyde -> 3-hydroxybutanal", "aldol addition", REAL, False,
             lambda: _hand(("CC=O", "CC=O"), ("CC(O)CC=O",), "CC(O)CC=O"), W, expect=COVERAGE_GAP),
        Case("Friedel-Crafts acylation: benzene + acetic anhydride -> acetophenone + acetic acid (#110)",
             "Friedel-Crafts acylation", REAL, False,
             lambda: _hand(("c1ccccc1", "CC(=O)OC(C)=O"), ("CC(=O)c1ccccc1", "CC(=O)O"), "CC(=O)c1ccccc1"), W,
             expect=COVERAGE_GAP),
        Case("nucleophilic substitution (charged): bromomethane + hydroxide -> methanol + bromide",
             "SN2 (charged)", REAL, False,
             lambda: _hand(("CBr", "[OH-]"), ("CO", "[Br-]"), "CO"),
             "textbook SN2; charged species -- representable + conserving, no attested recognizer", expect=COVERAGE_GAP),

        # ========================= UNREPRESENTABLE: the engine refuses to build =====================================
        Case("non-conserving: acetic acid -> methane (atoms dropped; engine refuses)", "non-conserving", OUTSIDE,
             False, lambda: _hand(("CC(=O)O",), ("C",), "C"), "not a reaction: mass not conserved",
             expect=UNREPRESENTABLE),
    )


def _classify(c: Case, built: bool, recognized: bool) -> str:
    if not built:
        return UNREPRESENTABLE
    if c.expect == MUTATION_OFF:
        return MUTATION_OFF if not recognized else FALSE_VOUCH
    if c.truth == FICTION:
        return FALSE_VOUCH if recognized else CORRECTLY_DEMOTED
    if c.truth == REAL and c.in_whitelist:
        if recognized:
            return RECOGNIZED
        return RESIDUAL if c.expect == RESIDUAL else COVERAGE_GAP  # unexpected miss shows up as a gap (loud)
    if c.truth == REAL:  # real, outside the whitelist
        return COVERAGE_GAP if not recognized else FALSE_VOUCH
    return UNREPRESENTABLE  # OUTSIDE truth that still built is handled above; fall-through guard


def measure() -> dict:
    rows = []
    false_vouch = 0
    recall_hits = recall_total = 0
    findings_gap, findings_residual = [], []
    mismatches = []
    for c in corpus():
        try:
            step = c.build()
            built = True
            klass = recognize_reaction_type(step)
            recognized = klass is not None
            err = None
        except Exception as exc:
            built, recognized, klass, err = False, False, None, f"{type(exc).__name__}: {exc}"
        outcome = _classify(c, built, recognized)
        if outcome == FALSE_VOUCH:
            false_vouch += 1
        if c.truth == REAL and c.in_whitelist and c.expect == RECOGNIZED:
            recall_total += 1
            recall_hits += int(outcome == RECOGNIZED)
        if outcome == COVERAGE_GAP:
            findings_gap.append(c.name)
        if outcome == RESIDUAL:
            findings_residual.append(c.name)
        if outcome != c.expect:
            mismatches.append((c.name, c.expect, outcome))
        rows.append((c, built, klass, err, outcome))
    return {
        "rows": rows,
        "false_vouch": false_vouch,
        "recall_hits": recall_hits, "recall_total": recall_total,
        "coverage_gaps": findings_gap, "pericyclic_residuals": findings_residual,
        "mismatches": mismatches,
    }


def validate() -> bool:
    """Soundness floor + no-silent-drift: FALSE_VOUCH == 0, full recall on in-whitelist positives, and every case's
    observed outcome equals its independently-set expectation (so a coverage change is a loud test failure)."""
    m = measure()
    return (m["false_vouch"] == 0
            and m["recall_hits"] == m["recall_total"]
            and not m["mismatches"])


def main() -> None:
    m = measure()
    print("INDEPENDENT-RECOGNITION-CORPUS-S3 -- held-out, hand-authored recognition benchmark\n")
    for c, built, klass, err, outcome in m["rows"]:
        mark = "OK " if outcome == c.expect else "!! "
        tag = "[holdout] " if c.holdout else ""
        got = err or (klass if klass is not None else "(abstain)")
        print(f"  {mark}{outcome:28s} {tag}{c.name}")
        print(f"        truth={c.truth} family='{c.family}' in_whitelist={c.in_whitelist} -> {got}")
    print(f"\n  recall (in-whitelist positives) : {m['recall_hits']}/{m['recall_total']}")
    print(f"  FALSE-VOUCH (must be 0)         : {m['false_vouch']}")
    print("  coverage gaps (real, un-attested, correctly abstained -- FINDINGS, not failures):")
    for n in m["coverage_gaps"]:
        print(f"      - {n}")
    print("  pericyclic centre-less residual (#132 -- FINDING):")
    for n in m["pericyclic_residuals"]:
        print(f"      - {n}")
    if m["mismatches"]:
        print("  !! MISMATCHES (observed != expected):")
        for name, exp, got in m["mismatches"]:
            print(f"      - {name}: expected {exp}, got {got}")
    print(f"\n  VERDICT: {'PASS' if validate() else 'FAIL'}")


if __name__ == "__main__":
    main()
