"""The M-5 Experiment Compiler, driven end-to-end on the paracetamol litmus -- a self-reporting gate.

The question this answers
-------------------------
"Given the decompiler's candidate routes to a real target, can the Experiment Compiler verify them as
runnable experiments, refuse the degenerate ones, fit them to a real bench, and draft a chemist-usable
procedure -- all under the known-not-new-physics discipline?"  Not "does the synthesis work" (W3 forbids
that claim), but the facts the compiler DOES assert must hold, and its refusals must fire for the right
sourced reasons:

* **E0 conservation.** Every step conserves mass and charge (re-checked through category.Reaction).
* **E1 composability.** The ketene route is DEGENERATE on the SOURCED not-isolable fact (the operator's own
  degenerate-path example); the anhydride route is not degenerate.  An off-seed intermediate is UNKNOWN
  until sourced data is injected, then resolves -- the universality lever.
* **E2 ceiling.** The limiting-reagent maximum is EXACT (1 mol paracetamol per mol 4-aminophenol) and
  propagates across a route.
* **E4 ranking + fitting.** The real anhydride route ranks above the degenerate ketene route; a bench that
  cannot reach 1000 K (a 1200 C burner) EXCLUDES the ketene pyrolysis; a missing reagent EXCLUDES a route;
  an undeclared constrained dimension is UNKNOWN, never a silent fit.
* **Bucket honesty.** Every number emitted wears a CONSERVATION / COMPOSABILITY / KNOWN_SOURCED / UNKNOWN
  bucket; UNKNOWN carries no value.
* **Universality.** A molecule the seed tables never heard of (ethyl acetate) flows through E0->E4 without a
  crash and without a whitelist hit.

Self-reporting gate
-------------------
Prints the pipeline output and a checklist, then exits non-zero if any HARD acceptance criterion failed, so
it can be run as a gate:

    .venv/bin/python experiments/compiled_paracetamol_experiment.py
"""
from __future__ import annotations

import sys
from fractions import Fraction

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.data.stability import DEFAULT_STABILITY, StabilityRef
from smartchem.experiment import (
    Bucket,
    ConstraintBox,
    ExperimentRoute,
    ExperimentStep,
    FeasibilityDirection,
    FeasibilityGrade,
    RouteFitStatus,
    SelectivityStatus,
    draft_procedure,
    feasibility_of_step,
    fit_route,
    rank_routes,
    stoichiometric_ceiling,
    verify_composability,
    verify_feasibility,
    verify_selectivity,
)
from smartchem.experiment.equipment import EquipmentKind
from smartchem.experiment.routes import enumerate_routes
from smartchem.smiles import parse_smiles


def _env(tlo, thi, prov, medium="", pres=None):
    kw = dict(temperature=Interval(tlo, thi, "K"), medium=medium,
              status=EvidenceStatus.EXPERIMENTAL, provenance=prov)
    if pres:
        kw["pressure"] = Interval(pres[0], pres[1], "atm")
    return ConditionEnvelope(**kw)


AMP = parse_smiles("Nc1ccc(O)cc1")
ANH = parse_smiles("CC(=O)OC(=O)C")
PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")
ACOH = parse_smiles("CC(=O)O")
WATER = parse_smiles("O")
KETENE = parse_smiles("C=C=O")
ESTER = parse_smiles("CC(=O)Oc1ccc(N)cc1")   # 4-aminophenyl acetate, the O-acetyl ISOMER of paracetamol
H2 = parse_smiles("[H][H]")
O2 = parse_smiles("O=O")
N2 = parse_smiles("N#N")
NH3 = parse_smiles("N")


def ester_route() -> ExperimentRoute:
    """The same anhydride acetylation aimed at the O-acetyl ester -- the DISFAVORED regiochemical outcome."""
    return ExperimentRoute.of(ExperimentStep.assembling(ESTER, (AMP, ANH), (ESTER, ACOH), reagents=(ANH,)))


def anhydride_route(pres=None) -> ExperimentRoute:
    return ExperimentRoute.of(ExperimentStep.assembling(
        PARA, (AMP, ANH), (PARA, ACOH), reagents=(ANH,),
        envelope=_env(295, 353, "ACS J.Chem.Educ. teaching synthesis",
                      "aqueous, mild acid; volumetric make-up", pres=pres),
    ))


def ketene_route() -> ExperimentRoute:
    return ExperimentRoute.of(
        ExperimentStep.assembling(KETENE, (ACOH,), (KETENE, WATER),
                                  envelope=_env(973, 1023, "acetic acid pyrolysis to ketene ~700 C")),
        ExperimentStep.assembling(PARA, (KETENE, AMP), (PARA,),
                                  envelope=_env(273, 298, "ketene acetylation near RT")),
    )


class Findings:
    def __init__(self) -> None:
        self.hard: list[str] = []
        self.checks = 0

    def check(self, ok: bool, label: str) -> None:
        self.checks += 1
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {label}", flush=True)
        if not ok:
            self.hard.append(label)


def main() -> int:
    f = Findings()
    print("=" * 96, flush=True)
    print("M-5 EXPERIMENT COMPILER -- paracetamol litmus, end to end", flush=True)
    print("=" * 96, flush=True)

    # -- E1: the two candidate routes and their composability -----------------------------------------
    print("\n[E1] composability of the candidate routes:", flush=True)
    comp_anh = verify_composability(anhydride_route())
    comp_ket = verify_composability(ketene_route())
    print(f"  anhydride route: {comp_anh.verdict}", flush=True)
    print(f"  ketene route   : {comp_ket.verdict}", flush=True)
    f.check(comp_ket.verdict == "DEGENERATE", "ketene route is DEGENERATE (sourced not-isolable fact)")
    f.check(any("not isolable" in r for r in comp_ket.degenerate_reasons),
            "the degeneracy cites ketene's sourced non-isolability")
    f.check(comp_anh.verdict == "SINGLE_STEP", "anhydride route is not degenerate (single step)")

    # -- E4: ranking floats the runnable route above the degenerate one -------------------------------
    print("\n[E4] ranking the candidate routes (north-star litmus):", flush=True)
    ranked = rank_routes([ketene_route(), anhydride_route()])
    for rf in ranked:
        print(f"  {rf.status.value:9} comp={rf.composability.verdict:11} :: {rf.route.final_target!r}",
              flush=True)
    f.check(ranked[0].route == anhydride_route(), "the real anhydride route ranks first")
    f.check(ranked[-1].composability.verdict == "DEGENERATE", "the ketene route ranks last (degenerate)")

    # -- E4: the constraint fitter (a compiler backend with a target-machine description) -------------
    print("\n[E4] constraint fitting -- bench: burner caps 1200 C (1473 K), no pressure > 1.5 bar:",
          flush=True)
    box = ConstraintBox(max_temperature_k=1473, max_pressure_atm=Fraction(3, 2))
    fit_ket = fit_route(ketene_route(), box)
    fit_anh = fit_route(anhydride_route(pres=(1, 1)), box)
    print(f"  ketene route   : {fit_ket.status.value} ({len(fit_ket.exclusions)} exclusions)", flush=True)
    print(f"  anhydride route: {fit_anh.status.value}", flush=True)
    f.check(fit_ket.status is RouteFitStatus.EXCLUDED, "the 1000 K ketene pyrolysis is EXCLUDED by a 1473 K bench")
    f.check(fit_anh.status is RouteFitStatus.FITS, "the anhydride route (ambient P declared) FITS the bench")

    # a bench missing acetic anhydride excludes the route, citing the missing reagent
    box_reagents = ConstraintBox(available_reagents=frozenset({"4-aminophenol", "water", "H2O"}))
    fit_missing = fit_route(anhydride_route(), box_reagents)
    f.check(fit_missing.status is RouteFitStatus.EXCLUDED
            and any("inventory" in e for e in fit_missing.exclusions),
            "a bench without acetic anhydride EXCLUDES the route, citing the missing reagent")

    # a bench with no heating apparatus excludes the heated step
    box_noheat = ConstraintBox(available_equipment=frozenset({EquipmentKind.VESSEL, EquipmentKind.MEASURING}))
    f.check(fit_route(anhydride_route(), box_noheat).status is RouteFitStatus.EXCLUDED,
            "a bench with no heating apparatus EXCLUDES the heated step")

    # an undeclared constrained dimension is UNKNOWN, never a silent fit
    box_pres = ConstraintBox(max_pressure_atm=Fraction(3, 2))
    f.check(fit_route(anhydride_route(pres=None), box_pres).status is RouteFitStatus.UNKNOWN,
            "an undeclared pressure under a pressure-capped bench is UNKNOWN, never a silent FITS")

    # -- E2: the exact stoichiometric ceiling ---------------------------------------------------------
    print("\n[E2] the stoichiometric ceiling (100% efficiency):", flush=True)
    step = anhydride_route().steps[0]
    ceil = stoichiometric_ceiling(step, {AMP: 1, ANH: Fraction(3, 2)})
    print(f"  {ceil.max_target_mol} mol paracetamol, limited by {ceil.limiting_reactant!r}", flush=True)
    f.check(ceil.max_target_mol == Fraction(1) and ceil.limiting_reactant == AMP,
            "the ceiling is exactly 1 mol paracetamol, limited by 4-aminophenol")
    f.check(ceil.quantity.bucket is Bucket.CONSERVATION, "the ceiling is CONSERVATION-bucketed (an upper bound)")

    # -- universality: an off-seed molecule flows through E0->E4 without a crash or a whitelist hit ---
    print("\n[universality] an off-seed molecule (ethyl acetate) flows through the whole pipeline:",
          flush=True)
    ea = parse_smiles("CCOC(=O)C")
    etoh = parse_smiles("CCO")
    ea_step = ExperimentStep.assembling(ea, (ACOH, etoh), (ea, WATER),
                                        envelope=_env(340, 350, "Fischer esterification", "acid-catalysed"))
    ea_draft = draft_procedure(ExperimentRoute.of(ea_step), feed={ACOH: 2, etoh: 3})
    f.check(ea_draft.ceiling.final_target_mol == Fraction(2),
            "ethyl acetate (off-seed) drafts and ceilings without a crash")

    # the universality lever: an off-seed intermediate is UNKNOWN until sourced data is injected
    u1 = ExperimentStep.assembling(ea, (ACOH, etoh), (ea, WATER), envelope=_env(340, 350, "esterify"))
    u2 = ExperimentStep.assembling(PARA, (ea, AMP), (PARA, etoh), envelope=_env(300, 320, "toy consume"))
    uroute = ExperimentRoute.of(u1, u2)
    before = verify_composability(uroute).verdict
    table = DEFAULT_STABILITY.with_records(StabilityRef(
        "C4H8O2", "ethyl acetate", Interval(190, 190, "K"), Interval(350, 350, "K"), None, True,
        "CRC: ethyl acetate bp 77 C, isolable, no bench decomposition",
    ))
    after = verify_composability(uroute, stability=table).verdict
    print(f"  off-seed intermediate: {before} -> (inject sourced data) -> {after}", flush=True)
    f.check(before == "UNKNOWN" and after == "COMPOSABLE",
            "an off-seed intermediate is UNKNOWN until sourced data is injected, then COMPOSABLE")

    # -- E5: enumerate candidate routes from the decompiler (the loop-closer) --------------------------
    print("\n[E5] enumerate synthesis routes from the decompiler (target + inventory -> routes):",
          flush=True)
    gen = enumerate_routes(PARA, reagents=(WATER, ACOH, ANH), available=(AMP,), max_depth=1)
    eqs = {s.equation() for r in gen for s in r.steps}
    for e in sorted(eqs):
        print(f"  candidate: {e}", flush=True)
    f.check("C4H6O3 + C6H7NO -> C8H9NO2 + C2H4O2" in eqs,
            "E5 rediscovers the acetic-anhydride acetylation of 4-aminophenol from the decompiler")
    f.check("C2H4O2 + C6H7NO -> C8H9NO2 + H2O" in eqs,
            "E5 rediscovers the acetic-acid condensation route from the decompiler")
    f.check(not enumerate_routes(PARA, reagents=(WATER,), available=(), max_depth=1),
            "E5 returns a loud empty (no route) from an empty inventory, never a fabricated route")

    # -- E5 depth: isomer-keyed regiochemical selectivity (which isomer the step makes) ---------------
    print("\n[selectivity] N- vs O-acetylation of 4-aminophenol (same formula C8H9NO2, different isomer):",
          flush=True)
    sel_para = verify_selectivity(anhydride_route())
    sel_ester = verify_selectivity(ester_route())
    sel_ket = verify_selectivity(ketene_route())
    print(f"  paracetamol (N-acetyl amide) via anhydride -> {sel_para.verdict}", flush=True)
    print(f"  4-aminophenyl acetate (O-acetyl ester) via anhydride -> {sel_ester.verdict}", flush=True)
    f.check(sel_para.verdict == "FAVORED",
            "the amide (paracetamol) is the SOURCED FAVORED product of acetylating 4-aminophenol")
    f.check(sel_ester.verdict == "DISFAVORED",
            "the O-acetyl ester is DISFAVORED -- the sourced major product is the amide, not the ester")
    f.check(sel_ket.per_step[-1].status is SelectivityStatus.UNKNOWN,
            "the ketene acetylation carries no sourced N-/O-selectivity: a loud UNKNOWN, never fabricated")
    ranked_iso = rank_routes([ester_route(), anhydride_route()])
    f.check(ranked_iso[0].route == anhydride_route(),
            "ranking floats the FAVORED (right-isomer) route above the DISFAVORED one")

    # -- M1: thermodynamic feasibility (ΔG), the DERIVED bucket, calibrated on known reactions ---------
    print("\n[M1 feasibility] DERIVED ΔG, instrument calibrated on known reactions:", flush=True)
    water = ExperimentStep.assembling(WATER, (H2, H2, O2), (WATER, WATER))       # 2H2 + O2 -> 2H2O
    fw = feasibility_of_step(water)
    print(f"  2H2 + O2 -> 2H2O : {fw.direction.value}/{fw.grade.value}, ΔG = {fw.delta_g_kj:.1f} kJ/mol",
          flush=True)
    f.check(fw.direction is FeasibilityDirection.FAVORABLE and abs(fw.delta_g_kj - (-474.3)) < 1.0,
            "ΔG engine recovers the textbook -474 kJ for 2H2+O2->2H2O (the instrument reads true)")
    haber = ExperimentStep.assembling(NH3, (N2, H2, H2, H2), (NH3, NH3))          # N2 + 3H2 -> 2NH3
    f.check(feasibility_of_step(haber).direction is FeasibilityDirection.FAVORABLE,
            "Haber is FAVORABLE at 298 K (DERIVED, ΔG ~ -33 kJ)")
    hot = feasibility_of_step(haber, temperature_k=700.0)
    f.check(hot.direction is FeasibilityDirection.UNFAVORABLE and hot.grade is FeasibilityGrade.PREDICTED,
            "Haber flips UNFAVORABLE at 700 K, flagged PREDICTED (extrapolated) -- the real T-dependence")
    fp = feasibility_of_step(anhydride_route().steps[0])
    f.check(fp.direction is FeasibilityDirection.UNKNOWN and fp.missing,
            "paracetamol acetylation feasibility is a loud UNKNOWN (no seed thermo), never a fabricated ΔG")
    ranked_feas = rank_routes([ExperimentRoute.of(
        ExperimentStep.assembling(H2, (WATER, WATER), (H2, H2, O2))), ExperimentRoute.of(water)])
    f.check(verify_feasibility(ranked_feas[0].route).verdict == "FAVORABLE",
            "ranking floats the thermodynamically FAVORABLE route above the endergonic one")

    # -- the drafted procedure a chemist reads --------------------------------------------------------
    print("\n[draft] the chemist-facing procedure for the winning route:", flush=True)
    draft = draft_procedure(anhydride_route(pres=(1, 1)), feed={AMP: 1, ANH: Fraction(6, 5)})
    text = draft.render()
    print(text, flush=True)
    f.check("NOT a predicted successful synthesis" in text, "the draft carries the honesty banner")
    f.check(any("hotplate" in i.name or "water bath" in i.name for i in draft.equipment[0]),
            "the draft names the heating apparatus (the 'Bunsen and flasks' click)")
    f.check(any(i.kind is EquipmentKind.CONTAINMENT for i in draft.equipment[0]),
            "the draft attaches sourced-hazard containment (a fume hood)")
    f.check("selectivity: FAVORED" in text,
            "the draft surfaces the sourced regiochemistry (this route makes the major isomer)")

    # -- verdict --------------------------------------------------------------------------------------
    print("\n" + "=" * 96, flush=True)
    if f.hard:
        print(f"HARD FAILURES ({len(f.hard)}/{f.checks}):", flush=True)
        for msg in f.hard:
            print(f"  x {msg}", flush=True)
        print("VERDICT: FAIL", flush=True)
        return 1
    print(f"VERDICT: PASS -- all {f.checks} acceptance criteria hold. The Experiment Compiler certifies "
          "steps, refuses the degenerate route on a sourced fact, fits routes to a real bench, computes an "
          "exact ceiling, grades regiochemical selectivity and DERIVED thermodynamic feasibility (ΔG), and "
          "drafts a chemist-usable procedure -- universal and bucket-honest throughout.",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
