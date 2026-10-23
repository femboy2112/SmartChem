"""ACTIVATED-ACYL-TRANSFER-110 -- the first new-chemistry coverage win (OPERATION §5(A), issue #110).

An ANHYDRIDE or ACYL HALIDE acylating an O/N/S nucleophile is a DISTINCT reaction class from the free-acid
dehydrative condensation: the pre-activated donor expels a CARBOXYLIC ACID (anhydride) or a HYDROGEN HALIDE (acyl
halide) as the coproduct, NOT water -- shape ``donor + Nu-H -> acyl-Nu + leaving-acid`` (2 reactants -> 2 products,
no water).  The capped-scission search ALREADY GENERATES these routes under a declared leaving-group helper + donor
stock (recon: OBSERVED), but the free-acid census demotes them for lacking a water coproduct.  The §5(A) directive:
make the already-generated-but-demoted route RECOGNIZED *without lifting any unrelated fiction*.

This corpus has two instruments:
  * RECOGNIZER MATRIX (hand-authored): genuine activated transfers (ester/amide/thioester onto O/N/S -- incl. the
    PARACETAMOL litmus route) must be MATCHed as "activated acyl transfer"; fictions and out-of-scope cases
    (free-acid condensation, C-C glue, hydrolysis, transesterification, C-nucleophile Friedel-Crafts) must NOT be.
  * REACHABILITY DEMO (actual search): on a benign target with the leaving-group acid as a helper and the donor in
    stock, the production search EMITS the 1-step activated route, and its ``route_reaction_type_blockers`` is now
    EMPTY (the demotion->vouch flip -- previously an "unrecognized reaction type" fiction blocker).

SCOPE / boundaries (honest): O/N/S nucleophiles only -- Friedel-Crafts C-acylation wants a Lewis-acid activator
(#107) + arene guards and is NOT vouched (coverage loss, never false-vouch).  Small targets reachable only via a
large donor (acetamide/methyl acetate via Ac2O) are blocked UPSTREAM by the #104 W1 atom-count wall, so the search
never emits them -- a generation boundary, not a recognizer gap.

Run: ``.venv/bin/python -m experiments.activated_acyl_transfer_110``
"""
from __future__ import annotations

from smartchem.smiles import parse_smiles
from smartchem.conditions import ConditionEnvelope
from smartchem.experiment.step import ExperimentStep
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type

_ACTIVATED = "activated acyl transfer"


def _hand(reactants: "tuple[str, ...]", products: "tuple[str, ...]") -> ExperimentStep:
    rs = tuple(parse_smiles(s) for s in reactants)
    ps = tuple(parse_smiles(s) for s in products)
    target = max(ps, key=lambda m: len(m.atoms))   # the acylated product is the larger non-leaving-group species
    return ExperimentStep.assembling(target, rs, ps, reagents=(), envelope=ConditionEnvelope.unknown())


#: (name, reactants, products, expected-class-substring or None).  POSITIVES expect the activated-transfer class;
#: the free-acid condensation expects its OWN class (not activated -- no poach); fictions/out-of-scope expect None.
_CASES = (
    ("ethyl acetate <- Ac2O + ethanol", ("CC(=O)OC(C)=O", "CCO"), ("CC(=O)OCC", "CC(=O)O"), _ACTIVATED),
    ("ethyl acetate <- AcCl + ethanol", ("CC(=O)Cl", "CCO"), ("CC(=O)OCC", "Cl"), _ACTIVATED),
    ("N-methylacetamide <- AcCl + methylamine", ("CC(=O)Cl", "CN"), ("CC(=O)NC", "Cl"), _ACTIVATED),
    ("N,N-dimethylacetamide <- Ac2O + dimethylamine", ("CC(=O)OC(C)=O", "CNC"), ("CC(=O)N(C)C", "CC(=O)O"), _ACTIVATED),
    ("paracetamol <- Ac2O + 4-aminophenol (litmus)", ("CC(=O)OC(C)=O", "Nc1ccc(O)cc1"),
     ("CC(=O)Nc1ccc(O)cc1", "CC(=O)O"), _ACTIVATED),
    ("S-methyl thioacetate <- AcCl + methanethiol", ("CC(=O)Cl", "CS"), ("CC(=O)SC", "Cl"), _ACTIVATED),
    # -- must NOT be vouched as activated transfer (no poach / no false-vouch) --
    ("free-acid esterification -> acyl condensation (not activated)", ("CC(=O)O", "CO"), ("CC(=O)OC", "O"),
     "acyl condensation"),
    ("C-C glue fiction with an acid 'leaving group'", ("CC(C)O", "CCOC(=O)C"), ("CC(C)CCOC(=O)C", "O"), None),
    ("acyl-halide hydrolysis (acid + HCl, no nucleophile acylated)", ("CC(=O)Cl", "O"), ("CC(=O)O", "Cl"), None),
    ("transesterification (no activated donor)", ("CC(=O)OC", "CCO"), ("CC(=O)OCC", "CO"), None),
    ("Friedel-Crafts C-acylation (out of scope -> abstain)", ("c1ccccc1", "CC(=O)OC(C)=O"),
     ("CC(=O)c1ccccc1", "CC(=O)O"), None),
)


def recognizer_matrix() -> dict:
    rows, ok = [], 0
    false_vouch = 0
    for name, rs, ps, expect in _CASES:
        try:
            klass = recognize_reaction_type(_hand(rs, ps))
        except Exception as exc:
            klass = f"ERROR: {type(exc).__name__}: {exc}"
        if expect is None:
            passed = klass is None
            if klass is not None and _ACTIVATED in str(klass):
                false_vouch += 1            # a fiction vouched AS activated transfer -- the cardinal sin
        else:
            passed = klass is not None and expect in str(klass)
        ok += int(passed)
        rows.append((name, expect, klass, passed))
    return {"rows": rows, "passed": ok, "total": len(_CASES), "false_vouch_as_activated": false_vouch,
            "recognized_activated": sum(1 for _n, e, k, _p in rows if e == _ACTIVATED and k and _ACTIVATED in str(k))}


def reachability_demo() -> dict:
    """The §5(A) success criterion on the ACTUAL search: ethyl acetate with acetic acid as a helper + Ac2O in stock
    emits the 1-step activated route ``ethanol + Ac2O -> ethyl acetate + AcOH``, whose step is now recognized as
    activated acyl transfer (EMPTY reaction-type blockers).  Content-determinism keeps the demonstration honest: the
    search also emits C4H6O3-containing routes whose product is a C4H8O2 ISOMER of ethyl acetate, or whose Ac2O is
    glued from scratch -- those stay DEMOTED (the win recognizes the genuine route WITHOUT lifting the fictions)."""
    from smartchem.service import (
        build_recompile_request, _canonical_helper_molecules, _canonical_commodities, resolve_algebra_profile,
    )
    from smartchem.identity_parse import resolve_identity
    from smartchem.experiment.routes import search_routes
    from smartchem.experiment.reaction_type_oracle import route_reaction_type_blockers, recognize_reaction_type
    from smartchem.smiles import resonance_identity, parse_smiles

    req = build_recompile_request("smiles:CCOC(C)=O", capability_profile="poor-man",
                                  helper_reagents=("water", "acetic acid"),
                                  stock_materials=("smiles:CC(=O)OC(C)=O", "smiles:CCO"),
                                  max_routes=1000)
    reagents, available = _canonical_helper_molecules(req)
    commodities = _canonical_commodities(req)
    registry = resolve_algebra_profile(req.algebra_profile)
    target = resolve_identity(req.target_input, req.input_kind).molecule.canonical()
    res = search_routes(target, reagents=reagents, available=available, commodities=commodities,
                        max_depth=req.search_bounds.value("max_depth"), max_routes=1000,
                        cut_budget=req.search_bounds.value("cut_budget"), registry=registry)
    etoac = resonance_identity(parse_smiles("CCOC(C)=O"))
    genuine_vouched = []     # 1-step routes whose Ac2O step yields GENUINE ethyl acetate and is now vouched
    isomer_demoted = 0       # C4H6O3-consuming routes whose product is NOT genuine ethyl acetate (stay demoted)
    for r in res.routes:
        actv = [s for s in r.steps if "C4H6O3" in s.equation()]
        if not actv:
            continue
        blockers = route_reaction_type_blockers(r)
        genuine = any(len(r.steps) == 1 and etoac in {resonance_identity(p) for p in s.products} for s in actv)
        if genuine and blockers == () and any(
                recognize_reaction_type(s) and "activated" in recognize_reaction_type(s) for s in actv):
            genuine_vouched.append(actv[0].equation())
        elif blockers != ():
            isomer_demoted += 1
    return {
        "n_routes": len(res.routes),
        "genuine_vouched": genuine_vouched,
        "isomer_or_glue_demoted": isomer_demoted,
        "won": bool(genuine_vouched),
    }


def validate() -> bool:
    m = recognizer_matrix()
    r = reachability_demo()
    return (m["passed"] == m["total"] and m["false_vouch_as_activated"] == 0 and m["recognized_activated"] == 6
            and r["won"])


def main() -> None:
    m = recognizer_matrix()
    print("ACTIVATED-ACYL-TRANSFER-110 -- recognizer matrix\n")
    for name, expect, klass, passed in m["rows"]:
        print(f"  {'OK ' if passed else '!! '}[{str(expect):18.18s}] {name}\n           -> {klass}")
    print(f"\n  recognized as activated transfer: {m['recognized_activated']}/6 positives")
    print(f"  passed: {m['passed']}/{m['total']}   false-vouch-as-activated (must be 0): {m['false_vouch_as_activated']}")
    r = reachability_demo()
    print("\n  REACHABILITY (actual search, ethyl acetate; acetic acid helper + Ac2O stock):")
    print(f"    routes returned: {r['n_routes']}")
    print(f"    GENUINE 1-step activated route(s) now VOUCHED (empty blockers): {r['genuine_vouched']}")
    print(f"    isomer/glue C4H6O3 routes kept DEMOTED (fictions, not lifted): {r['isomer_or_glue_demoted']}")
    print(f"\n  VERDICT: {'PASS' if validate() else 'FAIL'}")


if __name__ == "__main__":
    main()
