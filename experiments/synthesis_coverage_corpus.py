"""SYNTHESIS-COVERAGE-CORPUS-01 -- a committed, independently verifiable recognition benchmark.

The campaign's baseline instrument (OPERATION SMARTCHEM, section 2): a small corpus of labelled cases that
measures the reaction-TYPE oracle's RECALL (genuine instances it recognizes) and, above all, its FALSE-VOUCH
rate (fictions / mutations it wrongly recognizes -- the cardinal sin, which must stay 0). Four case kinds:

  * POSITIVE  -- a genuine engine-derived reaction; the oracle SHOULD recognize it (counts toward recall).
  * NEGATIVE  -- a mass-balanced FICTION; the oracle MUST NOT recognize it (a recognition here is a false-vouch).
  * NULL      -- a data-insufficient step (e.g. centre-less); the oracle MUST abstain (no vouch, no crash).
  * MUTATION  -- a positive perturbed in one load-bearing feature; recognition MUST flip off.

Positives are built through ``ExperimentStep.from_transform`` (a real capped scission read backwards: a TRUSTED,
engine-derived centre); negatives/nulls/mutations are hand-built through the public ``assembling`` constructor
(an UNTRUSTED centre -- neutral metadata, never evidence, per ISSUE-126). ``measure()`` returns the matrix;
``main()`` prints it; ``validate()`` is the regression assertion (recall == total positives AND false_vouch == 0).

Run: ``.venv/bin/python -m experiments.synthesis_coverage_corpus``
"""
from __future__ import annotations

from dataclasses import dataclass

from smartchem.smiles import parse_smiles
from smartchem.conditions import ConditionEnvelope
from smartchem.structure import structure_by_name
from smartchem.structure_descent import capped_scissions
from smartchem.reaction_center import ReactionCenter
from smartchem.experiment.step import ExperimentStep
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type

_WATER = structure_by_name("water").molecule
POSITIVE, NEGATIVE, NULL, MUTATION = "POSITIVE", "NEGATIVE", "NULL", "MUTATION"


def _derived(product_smiles: str, want: "tuple[str, ...]", k: int = 1) -> ExperimentStep:
    """A genuine engine-derived step: the capped scission of ``product`` whose fragments are ``want``, read
    backwards (TRUSTED centre). Raises if the grammar does not generate it (so a stale corpus entry is loud)."""
    r = parse_smiles(product_smiles)
    target_frags = sorted(parse_smiles(s).canonical().__repr__() for s in want)
    for cs in capped_scissions(r, tuple(parse_smiles("O") for _ in range(k)), max_reactant_cuts=k)[0]:
        if sorted(p.canonical().__repr__() for p in cs.products) == target_frags:
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


# an elementary ester/acyl condensation centre (for the forged-centre negatives/mutations).
_ELEM = ReactionCenter.of((("C", "O", 1), ("H", "O", 1)), (("C", "O", 1), ("H", "O", 1)), 1)


@dataclass(frozen=True)
class Case:
    name: str
    kind: str
    build: object   # () -> ExperimentStep

    def step(self) -> ExperimentStep:
        return self.build()


def corpus() -> "tuple[Case, ...]":
    return (
        # -- POSITIVES: genuine engine-derived reactions the oracle should recognize ------------------
        Case("esterification: acetic acid + methanol -> methyl acetate", POSITIVE,
             lambda: _derived("CC(=O)OC", ("CC(=O)O", "CO"))),
        Case("etherification: 2 methanol -> dimethyl ether", POSITIVE,
             lambda: _derived("COC", ("CO", "CO"))),
        Case("N-alkylation: aniline + methanol -> N-methylaniline", POSITIVE,
             lambda: _derived("CNc1ccccc1", ("Nc1ccccc1", "CO"))),
        # -- NEGATIVES: mass-balanced fictions the oracle MUST NOT vouch (false-vouch = cardinal sin) --
        Case("forged-centre bundled double condensation (2 lactic -> lactide)", NEGATIVE,
             lambda: _hand(("CC(O)C(=O)O", "CC(O)C(=O)O"), ("CC1OC(=O)C(C)OC1=O", "water", "water"),
                           "CC1OC(=O)C(C)OC1=O", _ELEM)),
        Case("forged acyl centre on a non-acyl pairing (2 methanol -> dimethyl ether, acyl centre)", NEGATIVE,
             lambda: _hand(("CO", "CO"), ("COC", "water"), "COC", _ELEM)),
        # #109 adversarial control: a REACHABLE capped-scission over-generation -- the generator EMITS this
        # formula-balanced glue-fiction (an engine-derived step with a TRUSTED centre), and the oracle's census +
        # span must still demote it. This is the R55 motivating example (gluing two alkyl fragments with a new C-C
        # bond and calling the departing atoms "water"); isopropanol + ethyl acetate do NOT condense to isopentyl
        # acetate. It must stay demoted PERMANENTLY -- coverage is never "solved" by certifying graph surgery.
        Case("reachable capped-scission fiction: isopropanol + ethyl acetate -> isopentyl acetate (R55)", NEGATIVE,
             lambda: _derived("CC(C)CCOC(=O)C", ("CC(C)O", "CCOC(=O)C"))),
        # -- NULL: data-insufficient (centre-less genuine shape) -> must ABSTAIN, not crash ------------
        Case("centre-less acyl shape (no trusted centre)", NULL,
             lambda: _hand(("CC(=O)O", "CO"), ("CC(=O)OC", "water"), "CC(=O)OC", None)),
        # -- MUTATION: a positive whose trusted centre is replaced by a hand-forged copy -> flips off --
        Case("esterification with its centre hand-copied (trust stripped)", MUTATION,
             lambda: _esterification_centre_copied()),
    )


def _esterification_centre_copied() -> ExperimentStep:
    genuine = _derived("CC(=O)OC", ("CC(=O)O", "CO"))
    return ExperimentStep.assembling(genuine.target, genuine.reactants, genuine.products,
                                     reagents=genuine.reagents, envelope=genuine.envelope,
                                     reaction_center=genuine.reaction_center)   # same centre, now untrusted


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
