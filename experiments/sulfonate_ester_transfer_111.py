"""SULFONATE-ESTER-TRANSFER-111 -- a narrow, defensible #111 coverage win (ALKYL sulfonate esters).

A sulfonyl halide sulfonylating an ALKYL alcohol oxygen -- ``R-OH + R'-SO2-X -> R-O-SO2-R' + H-X`` (methyl / ethyl /
isopropyl / benzyl mesylate / triflate formation) -- is a DISTINCT recognized reaction class. It is the
activated-transfer SHAPE of #110 (2 reactants -> 2 products, no water, a leaving acid) with a SULFONYL electrophile
(S(=O)2) rather than an ACYL one (C=O), so by construction it cannot poach #110 and #110 cannot poach it (the donor
gates are mutually exclusive: acyl carbonyl C vs sulfonyl S).

ONE instrument -- a hand-authored RECOGNIZER MATRIX. Genuine alkyl sulfonate-ester transfers must MATCH
"sulfonate-ester transfer"; cross-poach controls (acyl-halide transfer, dehydrative ether, free-acid esterification)
must match their OWN class, NOT sulfonate; out-of-scope nucleophiles (sulfonamide N, thiosulfonate S, ARYL phenol-O),
the sulfonic-anhydride donor, hydrolysis, bundled/glue fictions, AND the three evil-morty Wave-C false-vouches
(carboxylic-acid mixed anhydride, masked-carbonyl gem-diol, enol) must NOT be vouched as sulfonate (the CARDINAL
no-false-vouch -- those three kills are retained here as permanent regression controls).

SCOPE / boundaries (honest, narrow): an sp3 ALKYL-carbinol O nucleophile (-> an alkyl sulfonate ESTER) + a
HYDROGEN-HALIDE leaving group only. Deliberately NOT vouched, each honest coverage loss deferred behind its own gate:
an N nucleophile (sulfonamide), an S nucleophile (thiosulfonate), a sulfonic-ANHYDRIDE donor, and an ARYL-O
nucleophile (a PHENOL sulfonate -- a Kekulized aryl carbinol carbon is indistinguishable from an acyclic enol in this
aromaticity-free graph, so aryl-O waits on a 2.0 aromaticity model, #105). A carboxylic-acid O gives a mixed
carboxylic-sulfonic ANHYDRIDE, not an ester, and the alkyl-carbinol census excludes it. Whether the production search
GENERATES these routes is a separate measurement (sulfonyl-halide stock + an H-X helper); this corpus proves the
RECOGNIZER is sound, which is the §5 cardinal (recognition wins are the cheap, safe investment).

Run: ``.venv/bin/python -m experiments.sulfonate_ester_transfer_111``
"""
from __future__ import annotations

from smartchem.conditions import ConditionEnvelope
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

_SULFONATE = "sulfonate-ester transfer"


def _hand(reactants: "tuple[str, ...]", products: "tuple[str, ...]") -> ExperimentStep:
    rs = tuple(parse_smiles(s) for s in reactants)
    ps = tuple(parse_smiles(s) for s in products)
    target = max(ps, key=lambda m: len(m.atoms))   # the sulfonylated ester is the larger non-leaving species
    return ExperimentStep.assembling(target, rs, ps, reagents=(), envelope=ConditionEnvelope.unknown())


#: (name, reactants, products, expected-class-substring or None). POSITIVES expect the sulfonate class; the
#: cross-poach controls expect their OWN class (never sulfonate); out-of-scope / fictions expect None.
_CASES = (
    ("methyl tosylate <- methanol + TsCl", ("CO", "Cc1ccc(cc1)S(=O)(=O)Cl"),
     ("Cc1ccc(cc1)S(=O)(=O)OC", "Cl"), _SULFONATE),
    ("ethyl mesylate <- ethanol + MsCl", ("CCO", "CS(=O)(=O)Cl"), ("CCOS(=O)(=O)C", "Cl"), _SULFONATE),
    ("isopropyl triflate <- 2-propanol + TfCl", ("CC(C)O", "FC(F)(F)S(=O)(=O)Cl"),
     ("CC(C)OS(=O)(=O)C(F)(F)F", "Cl"), _SULFONATE),
    ("benzyl mesylate <- benzyl alcohol + MsCl (sp3 carbinol, aryl only at BETA)", ("OCc1ccccc1", "CS(=O)(=O)Cl"),
     ("C(c1ccccc1)OS(=O)(=O)C", "Cl"), _SULFONATE),
    # -- cross-poach controls: must stay their OWN class, NOT sulfonate --
    ("acyl transfer (AcCl + methanol) -> activated acyl (not sulfonate)", ("CC(=O)Cl", "CO"),
     ("COC(C)=O", "Cl"), "activated acyl transfer"),
    ("dehydrative ether (2 methanol) -> etherification (not sulfonate)", ("CO", "CO"), ("COC", "O"),
     "etherification"),
    ("free-acid esterification (AcOH + methanol) -> acyl condensation", ("CC(=O)O", "CO"),
     ("COC(C)=O", "O"), "acyl condensation"),
    # -- out-of-scope O/N/S nucleophiles + donor (abstain, honest coverage loss, never a false-vouch) --
    ("sulfonamide (TsCl + methylamine, N nucleophile -> out of O-only scope)", ("Cc1ccc(cc1)S(=O)(=O)Cl", "CN"),
     ("Cc1ccc(cc1)S(=O)(=O)NC", "Cl"), None),
    ("thiosulfonate (MsCl + methanethiol, S nucleophile -> out of scope)", ("CS(=O)(=O)Cl", "CS"),
     ("CS(=O)(=O)SC", "Cl"), None),
    ("phenyl mesylate (phenol, ARYL-O -> deferred to a 2.0 aromaticity model, not a false-vouch)",
     ("Oc1ccccc1", "CS(=O)(=O)Cl"), ("O(c1ccccc1)S(=O)(=O)C", "Cl"), None),
    # -- fictions / degenerate: must NOT be vouched as sulfonate --
    ("sulfonyl-halide hydrolysis (TsCl + water -> sulfonic acid + HCl, no ester)", ("Cc1ccc(cc1)S(=O)(=O)Cl", "O"),
     ("Cc1ccc(cc1)S(=O)(=O)O", "Cl"), None),
    ("transsulfonylation (no sulfonyl HALIDE donor present)", ("CCOS(=O)(=O)C", "CO"),
     ("COS(=O)(=O)C", "CCO"), None),
    # -- evil-morty Wave-C false-vouch kills, retained as permanent regression controls (CARDINAL) --
    ("MIXED ANHYDRIDE (MsCl + acetic acid -> acetyl mesylate; acyl-O, NOT a sulfonate ester) [F1]",
     ("CS(=O)(=O)Cl", "CC(=O)O"), ("CC(=O)OS(=O)(=O)C", "Cl"), None),
    ("GEM-DIOL masked carbonyl (MsCl + methanediol = formaldehyde hydrate) [F2a]",
     ("CS(=O)(=O)Cl", "OCO"), ("OCOS(=O)(=O)C", "Cl"), None),
    ("ENOL masked carbonyl (MsCl + vinyl alcohol = acetaldehyde enol) [F2b]",
     ("CS(=O)(=O)Cl", "C=CO"), ("C=COS(=O)(=O)C", "Cl"), None),
)


def recognizer_matrix() -> dict:
    rows, ok, false_vouch = [], 0, 0
    for name, rs, ps, expect in _CASES:
        try:
            klass = recognize_reaction_type(_hand(rs, ps))
        except Exception as exc:  # noqa: BLE001 -- a recognizer fault is itself a matrix fact
            klass = f"ERROR: {type(exc).__name__}: {exc}"
        if expect is None:
            passed = klass is None
        else:
            passed = klass is not None and expect in str(klass)
        if expect != _SULFONATE and klass is not None and _SULFONATE in str(klass):
            false_vouch += 1   # a non-sulfonate case vouched AS sulfonate -- the cardinal sin
        ok += int(passed)
        rows.append((name, expect, klass, passed))
    return {"rows": rows, "passed": ok, "total": len(_CASES), "false_vouch_as_sulfonate": false_vouch,
            "recognized_sulfonate": sum(1 for _n, e, k, _p in rows
                                        if e == _SULFONATE and k and _SULFONATE in str(k))}


def validate() -> bool:
    m = recognizer_matrix()
    return (m["passed"] == m["total"] and m["false_vouch_as_sulfonate"] == 0
            and m["recognized_sulfonate"] == 4)


def main() -> None:
    m = recognizer_matrix()
    print("SULFONATE-ESTER-TRANSFER-111 -- recognizer matrix\n")
    for name, expect, klass, passed in m["rows"]:
        print(f"  {'OK ' if passed else '!! '}[{str(expect):22.22s}] {name}\n           -> {klass}")
    print(f"\n  recognized as sulfonate transfer: {m['recognized_sulfonate']}/4 positives")
    print(f"  passed: {m['passed']}/{m['total']}   false-vouch-as-sulfonate (must be 0): {m['false_vouch_as_sulfonate']}")
    print(f"\n  VERDICT: {'PASS' if validate() else 'FAIL'}")


if __name__ == "__main__":
    main()
