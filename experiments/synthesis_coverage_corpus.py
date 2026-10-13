"""SYNTHESIS-COVERAGE-CORPUS-01 -- a committed, independently verifiable recognition benchmark.

The campaign's baseline instrument (OPERATION SMARTCHEM, section 2): a small corpus of labelled cases that
measures the reaction-TYPE oracle's RECALL (genuine instances it recognizes) and, above all, its FALSE-VOUCH
rate (fictions / mutations it wrongly recognizes -- the cardinal sin, which must stay 0). Four case kinds:

  * POSITIVE  -- a genuine reaction; the oracle SHOULD recognize it (counts toward recall).
  * NEGATIVE  -- a mass-balanced FICTION / a forge; the oracle MUST NOT recognize it (any recognition is a false-vouch).
  * NULL      -- a data-insufficient / census-fires-but-non-elementary step; the oracle MUST abstain (no vouch, no crash).
  * MUTATION  -- a positive perturbed in one load-bearing MOLECULAR feature; recognition MUST flip off.

ISSUE-126 Phase II content-determinism.  Recognition of the condensation classes RE-DERIVES locality/elementarity
from the step's own molecules (an independent single-cut capped scission), reading NO caller-supplied
``reaction_center`` -- so a forged centre cannot buy a vouch through ANY public construction route (the bare
constructor, ``dataclasses.replace``, or a fake ``from_transform`` transform), and a genuine condensation is
recognized whether or not it carries a centre.  The negatives below exercise all three forge routes on the lactide
double condensation; the NULL and MUTATION exercise the "census fires but the molecules do not re-derive" path.

``measure()`` returns the matrix; ``main()`` prints it; ``validate()`` is the regression assertion
(recall == total positives AND false_vouch == 0 AND null/mutation all correct).

Run: ``.venv/bin/python -m experiments.synthesis_coverage_corpus``
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from smartchem.smiles import parse_smiles, resonance_identity
from smartchem.conditions import ConditionEnvelope
from smartchem.structure import structure_by_name
from smartchem.structure_descent import capped_scissions
from smartchem.reaction_center import ReactionCenter
from smartchem.experiment.step import ExperimentStep
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type

_WATER = structure_by_name("water").molecule
POSITIVE, NEGATIVE, NULL, MUTATION = "POSITIVE", "NEGATIVE", "NULL", "MUTATION"

# an elementary ester/acyl condensation centre -- the forged descriptor the Phase-I audit used.  Under Phase II it
# is advisory metadata the oracle never reads for a vouch; attaching it to a fiction changes nothing.
_ELEM = ReactionCenter.of((("C", "O", 1), ("H", "O", 1)), (("C", "O", 1), ("H", "O", 1)), 1)


def _derived(product_smiles: str, want: "tuple[str, ...]", k: int = 1) -> ExperimentStep:
    """A genuine engine-derived step: the capped scission of ``product`` whose fragments are ``want``, read
    backwards.  Keyed on constitution (``resonance_identity``), not formula, so isomers are not confused.
    Raises if the grammar does not generate it (so a stale corpus entry is loud)."""
    r = parse_smiles(product_smiles)
    target_frags = sorted(resonance_identity(parse_smiles(s)) for s in want)
    for cs in capped_scissions(r, tuple(parse_smiles("O") for _ in range(k)), max_reactant_cuts=k)[0]:
        if sorted(resonance_identity(p) for p in cs.products) == target_frags:
            return ExperimentStep.from_transform(cs)
    raise AssertionError(f"capped scission of {product_smiles} does not yield {want}")


def _hand(reactants: "tuple[str, ...]", products: "tuple[str, ...]", target: str,
          center: "ReactionCenter | None" = None) -> ExperimentStep:
    rs = tuple(parse_smiles(s) for s in reactants)
    ps = tuple(_WATER if s == "water" else parse_smiles(s) for s in products)
    tg = parse_smiles(target)
    tt = next((x for x in ps if dict(x.formula) == dict(tg.formula) and x.charge == tg.charge), ps[0])
    return ExperimentStep.assembling(tt, rs, ps, reagents=(), envelope=ConditionEnvelope.unknown(),
                                     reaction_center=center)


class _FakeTransform:
    """A duck-typed transform with NO provider provenance (the #126 ``from_transform`` forge route)."""

    def __init__(self, reactant, products, reagents, center):
        self.reactant, self.products, self.reagents, self._center = reactant, products, reagents, center

    def reaction_center(self):
        return self._center


_LACTIC, _LACTIDE = "CC(O)C(=O)O", "CC1OC(=O)C(C)OC1=O"


def _lactide_direct() -> ExperimentStep:
    return _hand((_LACTIC, _LACTIC), (_LACTIDE, "water", "water"), _LACTIDE, _ELEM)


def _lactide_replace() -> ExperimentStep:
    return replace(_lactide_direct(), reaction_center=_ELEM)  # the dataclasses.replace forge route


def _lactide_fake_transform() -> ExperimentStep:
    fake = _FakeTransform(parse_smiles(_LACTIDE), (parse_smiles(_LACTIC), parse_smiles(_LACTIC)),
                          (_WATER, _WATER), _ELEM)
    return ExperimentStep.from_transform(fake)


def _esterification_hand_built() -> ExperimentStep:
    # content-determinism recovery: a genuine esterification built by hand with NO centre still re-derives + vouches.
    return _hand(("CC(=O)O", "CO"), ("CC(=O)OC", "water"), "CC(=O)OC", None)


@dataclass(frozen=True)
class Case:
    name: str
    kind: str
    build: object   # () -> ExperimentStep

    def step(self) -> ExperimentStep:
        return self.build()


def corpus() -> "tuple[Case, ...]":
    return (
        # -- POSITIVES: genuine reactions the oracle should recognize (recall) --------------------------
        Case("esterification: acetic acid + methanol -> methyl acetate", POSITIVE,
             lambda: _derived("CC(=O)OC", ("CC(=O)O", "CO"))),
        Case("etherification: 2 methanol -> dimethyl ether", POSITIVE,
             lambda: _derived("COC", ("CO", "CO"))),
        Case("N-alkylation: aniline + methanol -> N-methylaniline", POSITIVE,
             lambda: _derived("CNc1ccccc1", ("Nc1ccccc1", "CO"))),
        # content-determinism: a HAND-BUILT genuine esterification (no centre) is now recognized by re-derivation.
        Case("esterification (hand-built, centre-less) -> recognized by re-derivation", POSITIVE,
             _esterification_hand_built),
        # -- NEGATIVES: the lactide double condensation forged through all three #126 routes + the R55 fiction ---
        Case("forged-centre lactide double condensation (direct public constructor)", NEGATIVE, _lactide_direct),
        Case("forged-centre lactide double condensation (dataclasses.replace)", NEGATIVE, _lactide_replace),
        Case("forged-centre lactide double condensation (fake from_transform transform)", NEGATIVE,
             _lactide_fake_transform),
        # #109 adversarial control: a REACHABLE capped-scission over-generation -- the generator EMITS this
        # formula-balanced glue-fiction (an engine-derived step), and the oracle's census must still demote it.
        # isopropanol + ethyl acetate do NOT condense to isopentyl acetate (a new C-C bond, departing atoms called
        # "water").  It must stay demoted PERMANENTLY -- coverage is never "solved" by certifying graph surgery.
        Case("reachable capped-scission fiction: isopropanol + ethyl acetate -> isopentyl acetate (R55)", NEGATIVE,
             lambda: _derived("CC(C)CCOC(=O)C", ("CC(C)O", "CCOC(=O)C"))),
        # -- NULL: the acyl census FIRES but the step is a non-elementary bundle with NO centre -> clean abstain ---
        Case("lactide bundle, centre-less (census fires, re-derivation abstains, no crash)", NULL,
             lambda: _hand((_LACTIC, _LACTIC), (_LACTIDE, "water", "water"), _LACTIDE, None)),
        # -- MUTATION: a positive whose target is swapped to an ISOMERIC ester not assembled from these precursors.
        # The acyl census still fires (an ester carbonyl net-forms, a free acid net-consumes), but the single-cut
        # re-derivation of ethyl formate yields {formic acid, ethanol}, NOT {acetic acid, methanol} -> flips OFF.
        Case("esterification target swapped to ethyl formate (census fires, re-derivation flips off)", MUTATION,
             lambda: _hand(("CC(=O)O", "CO"), ("CCOC=O", "water"), "CCOC=O", _ELEM)),
    )


def measure() -> dict:
    """Run every case; return the coverage matrix with recall and the (must-be-zero) false-vouch count."""
    rows, totals = [], {POSITIVE: 0, NEGATIVE: 0, NULL: 0, MUTATION: 0}
    recall = false_vouch = null_ok = mutation_ok = 0
    for c in corpus():
        totals[c.kind] += 1
        try:
            vouch = recognize_reaction_type(c.step())
            err = None
        except Exception as exc:
            vouch, err = None, f"{type(exc).__name__}: {exc}"
        recognized = vouch is not None
        if c.kind == POSITIVE:
            ok = recognized
            recall += int(recognized)
        elif c.kind == NEGATIVE:
            ok = not recognized
            false_vouch += int(recognized)
        elif c.kind == NULL:
            ok = (not recognized) and err is None
            null_ok += int(ok)
        else:  # MUTATION: must flip off
            ok = not recognized
            mutation_ok += int(ok)
        rows.append((c.name, c.kind, vouch, err, ok))
    return {
        "rows": rows, "totals": totals,
        "recall": recall, "positives": totals[POSITIVE],
        "false_vouch": false_vouch, "negatives": totals[NEGATIVE],
        "null_ok": null_ok, "mutation_ok": mutation_ok,
    }


def validate() -> bool:
    m = measure()
    return (m["recall"] == m["positives"] and m["false_vouch"] == 0
            and m["null_ok"] == m["totals"][NULL] and m["mutation_ok"] == m["totals"][MUTATION])


def main() -> None:
    m = measure()
    print("SYNTHESIS-COVERAGE-CORPUS-01 -- reaction-type recognition matrix\n")
    for name, kind, vouch, err, ok in m["rows"]:
        mark = "OK " if ok else "!! "
        got = err or (vouch if vouch is not None else "(abstain)")
        print(f"  {mark}[{kind:8s}] {name}\n           -> {got}")
    print(f"\n  recall      : {m['recall']}/{m['positives']} positives recognized")
    print(f"  FALSE-VOUCH : {m['false_vouch']}/{m['negatives']} negatives wrongly recognized  (must be 0)")
    print(f"  null abstain: {m['null_ok']}/{m['totals'][NULL]}")
    print(f"  mutation off: {m['mutation_ok']}/{m['totals'][MUTATION]}")
    print(f"\n  VERDICT: {'PASS' if validate() else 'FAIL'}")


if __name__ == "__main__":
    main()
