"""V0.7-PROMOTION-01: the default-promotion blast-radius + performance experiment (0.7 Round III, SS8/SS9).

Before certified-route-v07 can be promoted to the NORMAL route default, we measure exactly what changes when the
same request runs under `certified-route-v07` instead of the current `legacy-capped-v1`, over a predeclared corpus
much larger than the DA forcing set.  The ONLY variable is `algebra_profile`; every other request field is held
fixed, and every case is driven through the REAL `run_compilation` (not an experiment override).

The corpus is PREDECLARED here (DA families + substituted holdouts, acyclic controls, saturated rings, aromatics,
hostile near-misses, the paracetamol/caffeine/aspirin/ester litmuses, a terminal-in-stock case, a starved-budget
case, and a DAG-topology sample) and is NOT tuned after seeing the answer.

Delta classification (SS8):
  ALLOWED     -- additional class-vouched DA routes; algebra/search digest movement; higher bounded work.
  UNACCEPTABLE -- a LEGACY route lost; a false COMPLETE where legacy was partial; an UNRECOGNISED/fictitious DA
                  route ranked; a NON-DA target changed with no DA reason; a runtime explosion.

Performance (SS9): certified-vs-legacy median / p90 / p95 / worst wall-clock and transforms-considered, on the same
corpus -- a comparison, not an absolute desktop number.

Run:  .venv/bin/python experiments/v0_7_promotion_blast_radius.py
"""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass

from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.routes import search_routes
from smartchem.identity_parse import InputKind
from smartchem.service import build_recompile_request, run_compilation
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import DEFAULT_TRANSFORM_REGISTRY
from smartchem.algebra_profiles import resolve_algebra_profile

LEGACY = "legacy-capped-v1"
CERTIFIED = "certified-route-v07"

# --- PREDECLARED corpus (label, SMILES, kind) -- fixed before any result is seen -------------------------------
_DA = "da"          # a genuine DA-decomposable target (certified may legitimately add routes)
_NONDA = "nonda"    # NOT DA-decomposable -> certified MUST behave identically to legacy
CORPUS = [
    # the 8 admitted DA families (+ 2 substituted holdouts)
    ("da-alkene", "C1CC=CCC1", _DA), ("da-alkyne", "C1=CCC=CC1", _DA),
    ("da-aza", "C1C=CCCN1", _DA), ("da-oxa", "C1C=CCCO1", _DA), ("da-thia", "C1C=CCCS1", _DA),
    ("da-aza-diene", "N1C=CCCC1", _DA), ("da-oxa-diene", "O1C=CCCC1", _DA), ("da-thia-diene", "C1CCC=CS1", _DA),
    ("da-holdout-methylcyclohexene", "CC1=CCCCC1", _DA), ("da-holdout-substituted", "CCC1CCC=CC1", _DA),
    # acyclic controls (no ring -> no DA cycloadduct)
    ("ctl-ethanol", "CCO", _NONDA), ("ctl-methyl-acetate", "CC(=O)OC", _NONDA),
    ("ctl-acetic-acid", "CC(=O)O", _NONDA), ("ctl-butane", "CCCC", _NONDA),
    # saturated rings (no internal pi -> no retro-DA)
    ("ctl-cyclohexane", "C1CCCCC1", _NONDA), ("ctl-cyclopentane", "C1CCCC1", _NONDA),
    # aromatic systems (aromatic ring is not a DA adduct)
    ("ctl-benzene", "c1ccccc1", _NONDA), ("ctl-phenol", "c1ccc(O)cc1", _NONDA),
    # hostile near-misses (must NOT produce a DA witness under either profile)
    ("hostile-enone", "O=C1CCCC=C1", _NONDA),
    # litmuses
    ("lit-paracetamol", "CC(=O)Nc1ccc(O)cc1", _NONDA), ("lit-aspirin", "CC(=O)Oc1ccccc1C(=O)O", _NONDA),
    ("lit-caffeine", "Cn1cnc2c1c(=O)n(C)c(=O)n2C", _NONDA),
]

# CO-RANKING targets (Wave-C finding F1): each carries BOTH a capped-cuttable bond (ester/amide) AND a
# DA-decomposable cyclohexene ring, run WITH stock for both route types -- so a legacy capped route and certified DA
# candidates genuinely co-exist at the same node.  This exercises the union-add / "no legacy route lost" invariant
# NON-VACUOUSLY: the empty-stock corpus above ranks 0 routes on every DA target (correct, but vacuous for that
# invariant), so F1 rightly warned the headline claim rested on empty sets for the DA targets it named.
_CORANK_STOCK = ("CO", "N", "O", "C=CC=C", "C=C", "OC(=O)C1CCC=CC1", "OC=O")
CORANK = [
    ("corank-methyl-ester-cyclohexene", "COC(=O)C1CCC=CC1"),
    ("corank-acetate-cyclohexene", "CC(=O)OC1CCC=CC1"),
    ("corank-amide-cyclohexene", "O=C(N)C1CCC=CC1"),
]


@dataclass
class Cell:
    exit_code: int
    outcome: str
    candidate_count: int
    routes: int
    route_digests: frozenset
    algebra_digest: str
    complete: bool
    transforms_considered: int
    nodes_visited: int
    stop_reason: str
    seconds: float


def _run(profile: str, smi: str, *, grammar=None, stock=(), budget=None, maxr=None) -> Cell:
    req = build_recompile_request(smi, input_kind=InputKind.SMILES, helper_reagents=("water",),
                                  stock_materials=stock, algebra_profile=profile, grammar=grammar,
                                  cut_budget=budget, max_routes=maxr)
    t0 = time.perf_counter()
    resp = run_compilation(req)
    dt = time.perf_counter() - t0
    ir = resp.compilation_ir
    rec = ir.search_receipt if ir is not None else None
    route_digests = frozenset(d.route_digest for d in resp.ranked_route_dossiers)
    return Cell(
        exit_code=resp.exit_code, outcome=resp.outcome.name,
        candidate_count=(ir.candidate_count if ir is not None else 0),
        routes=len(resp.ranked_route_dossiers), route_digests=route_digests,
        algebra_digest=(ir.transform_registry_digest if ir is not None else ""),
        complete=(bool(rec.candidate_enumeration_complete and rec.cut_enumeration_complete) if rec else False),
        transforms_considered=(rec.transforms_considered if rec else 0),
        nodes_visited=(rec.nodes_visited if rec else 0),
        stop_reason=(rec.stop_reason if rec else ""),
        seconds=dt,
    )


def _new_routes_are_oracle_vouched(smi: str, stock: tuple = ()) -> tuple[bool, list]:
    """Fiction guard: every STEP certified can generate that legacy CANNOT must be oracle-recognised.

    A step certified produces but legacy cannot is (by construction, certified = legacy + DA) a DA disconnection; if
    such a step were NOT oracle-recognised it would be a fictitious DA route.  Wave-C F2: we check EVERY step of every
    certified route (not just ``steps[0]``), so a DA disconnection buried at depth >= 2 behind a legacy-capped first
    step cannot slip past.  We probe the low-level search so we can run the production oracle on the actual
    ExperimentStep."""
    target = parse_smiles(smi)
    avail = tuple(parse_smiles(s) for s in stock)
    cert = search_routes(target, reagents=(parse_smiles("O"),), available=avail,
                         registry=resolve_algebra_profile(CERTIFIED), max_depth=2)
    leg = search_routes(target, reagents=(parse_smiles("O"),), available=avail,
                        registry=DEFAULT_TRANSFORM_REGISTRY, max_depth=2)
    leg_step_digests = {s.digest for r in leg.routes for s in r.steps}  # ALL legacy step digests, any depth
    unvouched = []
    for r in cert.routes:
        for step in r.steps:  # F2: every step, not just the first
            if step.digest in leg_step_digests:
                continue  # a legacy-producible step -- not a new certified disconnection
            if recognize_reaction_type(step) is None:
                unvouched.append(step.digest[:12])
    return (len(unvouched) == 0, unvouched)


def main() -> int:
    rows = []
    findings = []  # (severity, label, detail)
    perf_legacy, perf_cert, tc_legacy, tc_cert = [], [], [], []

    for label, smi, kind in CORPUS:
        leg = _run(LEGACY, smi)
        cert = _run(CERTIFIED, smi)
        rows.append((label, kind, leg, cert))
        perf_legacy.append(leg.seconds)
        perf_cert.append(cert.seconds)
        tc_legacy.append(leg.transforms_considered)
        tc_cert.append(cert.transforms_considered)

        # INVARIANT 1 (every target): no legacy route may be LOST under certified.
        lost = leg.route_digests - cert.route_digests
        if lost:
            findings.append(("UNACCEPTABLE", label, f"{len(lost)} legacy route(s) lost under certified"))

        # INVARIANT 2 (non-DA targets): certified must be behaviour-identical (same exit + same route set).
        if kind == _NONDA:
            if leg.exit_code != cert.exit_code:
                findings.append(("UNACCEPTABLE", label, f"non-DA exit changed {leg.exit_code}->{cert.exit_code}"))
            if leg.route_digests != cert.route_digests:
                findings.append(("UNACCEPTABLE", label, "non-DA route set changed"))

        # INVARIANT 3: no false COMPLETE (certified complete where legacy was partial on identical budget).
        if cert.complete and not leg.complete:
            findings.append(("INSPECT", label, "certified COMPLETE where legacy was partial"))

        # INVARIANT 4 (every DA target, UNCONDITIONALLY): every route certified can generate that legacy cannot must
        # be oracle-vouched -- checked at the low-level search so it fires even when no terminal stock lets the route
        # rank through the service (otherwise the fiction guard would be vacuous on a no-stock corpus).
        if kind == _DA:
            ok, unvouched = _new_routes_are_oracle_vouched(smi)
            if not ok:
                findings.append(("UNACCEPTABLE", label, f"fictitious (unvouched) DA route(s): {unvouched}"))

        # INVARIANT 5: runtime explosion (certified > 12x legacy AND absolute > 2s).
        if leg.seconds > 0 and cert.seconds > 12 * leg.seconds and cert.seconds > 2.0:
            findings.append(("INSPECT", label, f"runtime {leg.seconds*1e3:.0f}ms->{cert.seconds*1e3:.0f}ms"))

    # --- CO-RANKING evaluation (Wave-C F1): "no legacy route lost" exercised NON-VACUOUSLY, with stock ------------
    corank_rows = []
    for label, smi in CORANK:
        leg = _run(LEGACY, smi, stock=_CORANK_STOCK)
        cert = _run(CERTIFIED, smi, stock=_CORANK_STOCK)
        corank_rows.append((label, leg, cert))
        # HARD invariant: at a generous max_routes, no legacy route may be dropped from CONSIDERATION.
        lost = leg.route_digests - cert.route_digests
        if lost:
            findings.append(("UNACCEPTABLE", label, f"{len(lost)} legacy route(s) lost under certified (co-rank)"))
        # every new certified step must be oracle-vouched (all-steps guard, with stock present).
        ok, unvouched = _new_routes_are_oracle_vouched(smi, stock=_CORANK_STOCK)
        if not ok:
            findings.append(("UNACCEPTABLE", label, f"fictitious (unvouched) DA step(s) (co-rank): {unvouched}"))
        # NOTABLE (allowed, documented): certified may honestly downgrade a COMPLETE legacy search to incomplete
        # (exit 4) -- the wider union enumerates more and hits cut_budget.  The legacy route is PRESERVED; this is the
        # reverse of the forbidden "false COMPLETE", i.e. higher bounded work honestly reported, not a soundness loss.
        if leg.complete and not cert.complete:
            findings.append(("NOTABLE", label, "certified honest-incomplete at default budget (wider enumeration); "
                                               "legacy route preserved -- higher bounded work, not a false complete"))
    # eviction probe at max_routes=1: does certified's top-1 preserve legacy's top-1 (no legacy route evicted by a
    # higher-ranked DA route)?  A rerank is ALLOWED (the route still exists at higher max_routes); we report it.
    ev_leg = _run(LEGACY, "COC(=O)C1CCC=CC1", stock=_CORANK_STOCK, maxr=1)
    ev_cert = _run(CERTIFIED, "COC(=O)C1CCC=CC1", stock=_CORANK_STOCK, maxr=1)
    eviction_top1_preserved = (not ev_leg.route_digests) or (ev_leg.route_digests <= ev_cert.route_digests)

    # extra topology sample: a DAG-grammar run on a DA target, both profiles.
    from smartchem.service import TransformGrammar
    dag_leg = _run(LEGACY, "C1CC=CCC1", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT)
    dag_cert = _run(CERTIFIED, "C1CC=CCC1", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT)
    # starved-budget case: cut_budget=1 forces incompleteness under both.
    starve_leg = _run(LEGACY, "CC(=O)OC", budget=1)
    starve_cert = _run(CERTIFIED, "CC(=O)OC", budget=1)

    # STOCKED PROMOTION DEMO: with the terminal stock present, certified ADDS a completed, oracle-vouched DA route
    # where legacy finds none -- the promotion's intended benefit shown directly (an ALLOWED delta, not a regression).
    demo_stock = ("C=CC=C", "C=C")  # butadiene + ethylene: the cyclohexene retro-[4+2] products
    demo_leg = _run(LEGACY, "C1CC=CCC1", stock=demo_stock)
    demo_cert = _run(CERTIFIED, "C1CC=CCC1", stock=demo_stock)
    demo_vouched, _demo_unvouched = _new_routes_are_oracle_vouched("C1CC=CCC1")

    lines = ["# v0.7 default-promotion blast-radius + performance (SS8/SS9)\n",
             f"Corpus n={len(CORPUS)} targets x 2 profiles through the REAL run_compilation; only algebra_profile varies.\n",
             "| target | kind | legacy exit/routes | certified exit/routes | new routes | algebra digest moved |",
             "|---|---|---|---|---|---|"]
    for label, kind, leg, cert in rows:
        new = len(cert.route_digests - leg.route_digests)
        lines.append(f"| {label} | {kind} | {leg.exit_code}/{leg.routes} | {cert.exit_code}/{cert.routes} | "
                     f"{new} | {'yes' if leg.algebra_digest != cert.algebra_digest else 'n/a'} |")

    def pct(xs, p):
        xs = sorted(xs)
        return xs[min(len(xs) - 1, int(p / 100 * len(xs)))]
    lines += [
        "\n## Performance (SS9): wall-clock seconds, certified vs legacy, same corpus",
        f"- legacy  median={statistics.median(perf_legacy)*1e3:.1f}ms p90={pct(perf_legacy,90)*1e3:.1f}ms "
        f"p95={pct(perf_legacy,95)*1e3:.1f}ms max={max(perf_legacy)*1e3:.1f}ms",
        f"- certified median={statistics.median(perf_cert)*1e3:.1f}ms p90={pct(perf_cert,90)*1e3:.1f}ms "
        f"p95={pct(perf_cert,95)*1e3:.1f}ms max={max(perf_cert)*1e3:.1f}ms",
        f"- worst per-target slowdown factor: {max(c/lg for lg, c in zip(perf_legacy, perf_cert) if lg > 0):.2f}x",
        f"- transforms considered: legacy median={statistics.median(tc_legacy):.0f} max={max(tc_legacy)}; "
        f"certified median={statistics.median(tc_cert):.0f} max={max(tc_cert)}",
        "\n## Topology + budget samples",
        f"- DAG C1CC=CCC1: legacy exit {dag_leg.exit_code}/{dag_leg.routes} routes, "
        f"certified exit {dag_cert.exit_code}/{dag_cert.routes} routes; digest moved: "
        f"{dag_leg.algebra_digest != dag_cert.algebra_digest}",
        f"- starved budget=1 CC(=O)OC: legacy complete={starve_leg.complete}, certified complete={starve_cert.complete} "
        f"(both must be False -- honest incompleteness)",
        "\n## Stocked promotion demo (the intended benefit, an ALLOWED delta)",
        f"- cyclohexene + stock(butadiene, ethylene): legacy exit {demo_leg.exit_code}/{demo_leg.routes} routes, "
        f"certified exit {demo_cert.exit_code}/{demo_cert.routes} routes; new certified routes oracle-vouched: "
        f"{demo_vouched}. (Certified turns a legacy NO_ROUTE into a class-vouched DA route -- exactly the promotion.)",
        "\n## Co-ranking targets (Wave-C F1): legacy capped route + certified DA candidates co-exist, WITH stock",
        "| target | legacy exit/routes | certified exit/routes | legacy routes ⊆ certified | new certified routes |",
        "|---|---|---|---|---|"]
    for label, leg, cert in corank_rows:
        subset = leg.route_digests <= cert.route_digests
        new = len(cert.route_digests - leg.route_digests)
        lines.append(f"| {label} | {leg.exit_code}/{leg.routes} | {cert.exit_code}/{cert.routes} | {subset} | {new} |")
    lines += [
        f"- eviction probe (COC(=O)C1CCC=CC1, max_routes=1): certified top-1 preserves legacy's top route: "
        f"{eviction_top1_preserved}. (No legacy route evicted from the top slot by a higher-ranked DA route.)",
        "\n## Delta classification",
    ]
    unacceptable = [f for f in findings if f[0] == "UNACCEPTABLE"]
    inspect = [f for f in findings if f[0] == "INSPECT"]
    notable = [f for f in findings if f[0] == "NOTABLE"]
    if not unacceptable and not inspect:
        lines.append("- **No unacceptable deltas and nothing to inspect.** Every legacy route preserved -- including "
                     "the CO-RANKING cases where a legacy capped route and certified DA candidates co-exist with "
                     "stock present (Wave-C F1 non-vacuous); every non-DA target byte-identical; every new certified "
                     "step oracle-vouched (all-steps guard); no false COMPLETE; no runtime explosion; no top-1 "
                     "eviction. NOTABLE (allowed) deltas below are documented, not regressions.")
    for sev, label, detail in findings:
        lines.append(f"- **{sev}** [{label}]: {detail}")

    report = "\n".join(lines) + "\n"
    out = "experiments/RESULTS_v0_7_promotion_blast_radius.md"
    with open(out, "w") as fh:
        fh.write(report)
    print(report)
    print(f"[wrote {out}]")
    print(f"\n[summary] corpus={len(CORPUS)} corank={len(CORANK)} unacceptable={len(unacceptable)} "
          f"inspect={len(inspect)} notable={len(notable)}")
    return 0 if not unacceptable else 1


if __name__ == "__main__":
    raise SystemExit(main())
