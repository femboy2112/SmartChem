"""OPERATION XXIV Phase I/II -- PREDECLARED P0 certification-gap probes (version-agnostic harness).

The script runs UNCHANGED against the pre-fix kernel (main 7314e2a) and against the XXIV kernel, so one script produces
the RED receipt and the GREEN receipt.  Every outcome below was FIXED BEFORE THE FIRST RUN (see
docs/research/OPERATION_XXIV_PREREGISTRATION.md, committed together with this file before any repair).

  P1  F2-gap   equilibrium-operator authority
      PASS       a caller-defined operator whose own ``descriptor()`` OMITS an operative solve parameter cannot obtain a
                 certified execution identity, and strict certified execution refuses it, on a one-compartment world AND
                 on a two-compartment coupled-transport world.
      FAIL       it obtains certified execution identity: two worlds with different physics share one certificate and
                 both run under ``require_certified_execution=True`` with ``execution_identity_certified=True``.
      AMBIGUOUS  it is not certified, but the receipt does not name the operator or the authority it lacks.

  P2  p6b      caller-controlled positivity floor
      PASS       for EVERY requested solver tolerance, a conserving trajectory with a legitimate signed feed ledger whose
                 inventory reaches a MACROSCOPIC negative (<= -10% of the species' declared amount) never receives
                 positivity_held=True together with structural_tier STRUCTURALLY_CONSERVING and no resolution flag --
                 on the coupled path AND the single-system kernel path; the non-negative control stays conserving.
      FAIL       some tolerance yields that unqualified verdict on some path.
      AMBIGUOUS  the strong tier survives but carries a resolution-limited flag or a caveat only.

  P3  charge   one stoichiometric system through three execution paths
      PASS       every path returns ONE shared typed charge-validity verdict that separates (a) reaction charge
                 conservation E_q N = 0, (b) accounting of externally supplied charge, (c) bulk electroneutrality; an
                 unbalanced charged feed is never reported physically supported on ANY path; the neutral controls are.
      FAIL       some path reports an unqualified physically admissible result (STRUCTURALLY_CONSERVING admitted tier,
                 no typed charge verdict saying otherwise) for net charge injected with no counter-ion or electrode.
      AMBIGUOUS  no path falsely admits, but the paths do not share a typed verdict (inconsistent contracts).

  P4  closure  certificate dependency closure of the audited rate-law pins
      PASS       an edit to a module-level helper that an audited law's ``descriptor()`` executes either DEMOTES the law
                 or cannot make two physically different worlds share a certificate.
      FAIL       after the helper edit the law is still SEALED, two worlds with different Ksp share one world
                 certificate, and their trajectories differ (a false execution-identity claim).
      AMBIGUOUS  the law stays sealed and the certificate collides, but the trajectories happen to coincide.
      (control)  an edit INSIDE the pinned class body must demote it on every commit.

  P5  temperature  source-domain transport of a 25 C solubility constant
      PASS       a world at the constant's sourced temperature runs; a world at 350 K is refused or explicitly demoted
                 with a typed source-domain reason (no unvalidated extrapolation), on the coupled AND kernel paths.
      FAIL       the 350 K world runs the 25 C constant under strict certified execution with no domain flag.
      AMBIGUOUS  it runs with a caveat, but the tier is not demoted.

    PYTHONPATH=. python -m experiments.sandbox_foundation.xxiv_p0_probes            # prints the JSON receipt
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

from experiments.sandbox_foundation.aqueous_equilibrium import SourcedConstant
from experiments.sandbox_foundation.claim_tiers import STRUCTURALLY_CONSERVING
from experiments.sandbox_foundation.general_coupled import (Compartment, CoupledError, CoupledWorld, EquilibriumCoupling,
                                                            ExternalBoundary, InterfaceTransfer)
from experiments.sandbox_foundation.general_equilibrium import EquilibriumOperator, EquilibriumState
from experiments.sandbox_foundation.general_kernel import ChemicalSystem, KernelError, Phase, Reaction, Species

AQ = Phase.AQUEOUS


def _get(obj, name, default="<no field>"):
    return getattr(obj, name, default)


# ===================================================================================================== P1 F2-gap
X1 = Species.of("X1", {"Q": 1}, 0, AQ)
X2 = Species.of("X2", {"Q": 1}, 0, AQ)


class TwoIsomerOperator(EquilibriumOperator):
    """A conserving user operator: total x partitions X1:X2 = frac:(1-frac).  ``frac`` is OPERATIVE (speciate reads it)
    but the operator's OWN descriptor omits it -- a seemingly faithful descriptor that lies by omission."""
    components = frozenset({"x"})
    species = ("X1", "X2")
    species_signature = {"X1": ((("Q", 1),), 0), "X2": ((("Q", 1),), 0)}
    accepted_solver_verdicts = frozenset({"SOLVED"})

    def __init__(self, frac: float):
        self.frac = float(frac)

    def descriptor(self) -> list:
        return self._class_descriptor() + [["model", "two-isomer partition"]]       # frac omitted

    def speciate(self, component_amounts, *, volume_L, temperature_K=298.15):
        self._validate(component_amounts, volume_L, temperature_K)
        x = float(component_amounts.get("x", 0.0))
        return EquilibriumState(species_amounts={"X1": self.frac * x, "X2": (1.0 - self.frac) * x}, volume_L=volume_L,
                                temperature_K=temperature_K, component_inputs=dict(component_amounts),
                                component_residuals={}, derived={}, structural_tier=STRUCTURALLY_CONSERVING,
                                solver_verdict="SOLVED")

    def component_totals(self, species_amounts):
        return {"x": species_amounts.get("X1", 0.0) + species_amounts.get("X2", 0.0)}


def _iso_compartment(name, op):
    return Compartment(name, ChemicalSystem([X1, X2], [], volume_L=1.0),
                       equilibrium=EquilibriumCoupling(op, {"X1": X1, "X2": X2}))


def _f2_world(frac, two_cell: bool):
    op = TwoIsomerOperator(frac)
    if not two_cell:
        return CoupledWorld([_iso_compartment("c", op)]), op, {"c": {X1: 1.0}}
    b = Compartment("b", ChemicalSystem([X1, X2], [], volume_L=1.0))
    iface = InterfaceTransfer("x1 a<->b", "c", "b", X1, X1, k_transfer=0.1)
    return CoupledWorld([_iso_compartment("c", op), b], [iface]), op, {"c": {X1: 1.0}, "b": {}}


def probe_f2() -> dict:
    out = {}
    for label, two in (("one_compartment", False), ("two_compartment_transport", True)):
        rec = {}
        wa, _, ia = _f2_world(0.2, two)
        wb, _, ib = _f2_world(0.8, two)
        rec["certificates_equal"] = wa._world_certificate == wb._world_certificate
        ta = wa.integrate(ia, duration=1.0, n_steps=5)
        tb = wb.integrate(ib, duration=1.0, n_steps=5)
        fa, fb = ta.amounts["c"][-1][X1], tb.amounts["c"][-1][X1]
        rec["final_X1"] = [fa, fb]
        rec["physics_differs"] = abs(fa - fb) > 1e-6
        rec["certified"] = _get(ta.receipt, "execution_identity_certified")
        rec["basis"] = _get(ta.receipt, "execution_identity_basis")
        rec["named_in_receipt"] = "TwoIsomerOperator" in json.dumps(
            [str(_get(ta.receipt, "uncertified_equilibrium_operators", "")),
             str(_get(ta.receipt, "attested_equilibrium_operators", "")), list(ta.caveats)])
        try:
            ts = wa.integrate(ia, duration=1.0, n_steps=5, require_certified_execution=True)
            rec["strict"] = "RAN"
            rec["strict_certified"] = _get(ts.receipt, "execution_identity_certified")
        except CoupledError as exc:
            rec["strict"] = "REFUSED"
            rec["strict_reason"] = str(exc)[:160]
        wm, opm, im = _f2_world(0.2, two)                       # post-construction mutation of the omitted parameter
        opm.frac = 0.9
        try:
            tm = wm.integrate(im, duration=1.0, n_steps=5)
            rec["mutation"] = "RAN"
            rec["mutation_certified"] = _get(tm.receipt, "execution_identity_certified")
        except (CoupledError, KernelError) as exc:
            rec["mutation"] = "REFUSED"
            rec["mutation_reason"] = str(exc)[:120]
        out[label] = rec
    forged = any(r["strict"] == "RAN" and r.get("strict_certified") is True and r["certificates_equal"]
                 and r["physics_differs"] for r in out.values())
    hidden = any(r["certified"] is not True and not r["named_in_receipt"] for r in out.values())
    out["verdict"] = "FAIL" if forged else ("AMBIGUOUS" if hidden else "PASS")
    return out


# ===================================================================================================== P2 p6b
A = Species.of("A", {"Q": 1}, 0, AQ)
B = Species.of("B", {"Q": 1}, 0, AQ)


def _p6b_coupled(atol, duration):
    w = CoupledWorld([Compartment("c", ChemicalSystem([A, B], [], volume_L=1.0))],
                     boundaries=[ExternalBoundary("drain A", "c", A, "feed", rate=-1.0)])
    tr = w.integrate({"c": {A: 2.0}}, duration=duration, n_steps=25, atol=atol)
    r = tr.receipt
    return {"atol": atol, "min_inventory": r.min_inventory, "positivity_held": r.positivity_held,
            "positivity_resolution_limited": _get(r, "positivity_resolution_limited"),
            "positivity_verdict": _get(r, "positivity_verdict"),
            "material_balance_closed": r.material_balance_closed, "structural_tier": r.structural_tier,
            "admitted_tier": r.admitted_tier}


def _p6b_kernel(atol, duration):
    s = ChemicalSystem([A, B], [], volume_L=1.0)
    tr = s.integrate({A: 2.0}, duration=duration, source={A: -1.0}, atol=atol, rtol=1e-9)
    r = tr.receipt
    return {"atol": atol, "min_inventory": r.min_inventory, "positivity_held": r.positivity_held,
            "positivity_resolution_limited": _get(r, "positivity_resolution_limited"),
            "positivity_verdict": _get(r, "positivity_verdict"),
            "external_ledger_closed": r.external_ledger_closed, "structural_tier": r.structural_tier,
            "admitted_tier": r.admitted_tier}


def probe_p6b() -> dict:
    out = {"coupled_negative": [_p6b_coupled(a, 2.5) for a in (1e-14, 1e-8, 1e-4, 1e-2)],
           "coupled_control": [_p6b_coupled(a, 1.5) for a in (1e-14, 1e-2)],
           "kernel_negative": [_p6b_kernel(a, 2.5) for a in (1e-15, 1e-8, 1e-2, 1e-1)],
           "kernel_control": [_p6b_kernel(a, 1.5) for a in (1e-15, 1e-1)]}

    def unqualified(r):
        return (r["min_inventory"] <= -0.2 and r["positivity_held"] is True and r["structural_tier"] == STRUCTURALLY_CONSERVING
                and r["positivity_resolution_limited"] is not True)

    def flagged_strong(r):
        return r["min_inventory"] <= -0.2 and r["structural_tier"] == STRUCTURALLY_CONSERVING

    neg = out["coupled_negative"] + out["kernel_negative"]
    controls_ok = all(r["structural_tier"] == STRUCTURALLY_CONSERVING for r in out["coupled_control"] + out["kernel_control"])
    out["controls_conserving"] = controls_ok
    out["verdict"] = ("FAIL" if any(unqualified(r) for r in neg) else
                      "AMBIGUOUS" if (any(flagged_strong(r) for r in neg) or not controls_ok) else "PASS")
    return out


# ===================================================================================================== P3 charge
NA = Species.of("Na+", {"Na": 1}, 1, AQ)
CL = Species.of("Cl-", {"Cl": 1}, -1, AQ)


def _charge_fields(r):
    cv = _get(r, "charge_validity", None)
    return {"structural_tier": r.structural_tier, "admitted_tier": r.admitted_tier,
            "charge_balance_claim": _get(r, "charge_balance_claim"),
            "charge_validity": (None if cv is None else
                                {k: _get(cv, k) for k in ("reaction_charge_conservation", "external_charge_supplied_mol",
                                                          "external_charge_accounted", "bulk_electroneutrality",
                                                          "physically_supported")})}


def probe_charge() -> dict:
    out = {}
    n0 = {NA: 0.1, CL: 0.1}
    s = ChemicalSystem([NA, CL], [], volume_L=1.0)
    out["kernel_unbalanced_feed"] = _charge_fields(s.integrate(dict(n0), duration=1.0, source={NA: 0.01}).receipt)
    out["kernel_neutral_feed"] = _charge_fields(s.integrate(dict(n0), duration=1.0,
                                                            source={NA: 0.01, CL: 0.01}).receipt)
    w1 = CoupledWorld([Compartment("c", ChemicalSystem([NA, CL], [], volume_L=1.0))],
                      boundaries=[ExternalBoundary("Na feed", "c", NA, "feed", rate=0.01)])
    out["coupled1_unbalanced_feed"] = _charge_fields(w1.integrate({"c": dict(n0)}, duration=1.0, n_steps=10).receipt)
    w1n = CoupledWorld([Compartment("c", ChemicalSystem([NA, CL], [], volume_L=1.0))],
                       boundaries=[ExternalBoundary("Na feed", "c", NA, "feed", rate=0.01),
                                   ExternalBoundary("Cl feed", "c", CL, "feed", rate=0.01)])
    out["coupled1_neutral_feed"] = _charge_fields(w1n.integrate({"c": dict(n0)}, duration=1.0, n_steps=10).receipt)
    cells = [Compartment("a", ChemicalSystem([NA, CL], [], volume_L=1.0)),
             Compartment("b", ChemicalSystem([NA, CL], [], volume_L=1.0))]
    w2 = CoupledWorld(cells, [InterfaceTransfer("Na a<->b", "a", "b", NA, NA, k_transfer=0.05)])
    out["coupled2_single_ion_transport"] = _charge_fields(
        w2.integrate({"a": {NA: 0.2, CL: 0.2}, "b": {NA: 0.0, CL: 0.0}}, duration=1.0, n_steps=10).receipt)
    w2n = CoupledWorld(cells, [InterfaceTransfer("Na a<->b", "a", "b", NA, NA, k_transfer=0.05),
                               InterfaceTransfer("Cl a<->b", "a", "b", CL, CL, k_transfer=0.05)])
    out["coupled2_neutral_salt_transport"] = _charge_fields(
        w2n.integrate({"a": {NA: 0.2, CL: 0.2}, "b": {NA: 0.0, CL: 0.0}}, duration=1.0, n_steps=10).receipt)

    unbalanced = ("kernel_unbalanced_feed", "coupled1_unbalanced_feed", "coupled2_single_ion_transport")
    neutral = ("kernel_neutral_feed", "coupled1_neutral_feed", "coupled2_neutral_salt_transport")

    def falsely_admitted(r):
        cv = r["charge_validity"]
        claims_ok = cv is None or cv["physically_supported"] is not False
        return r["admitted_tier"] != "REFUSED" and r["structural_tier"] == STRUCTURALLY_CONSERVING and claims_ok

    typed_everywhere = all(out[k]["charge_validity"] is not None for k in unbalanced + neutral)
    neutral_ok = all(out[k]["structural_tier"] == STRUCTURALLY_CONSERVING
                     and (out[k]["charge_validity"] is None or out[k]["charge_validity"]["physically_supported"] is True)
                     for k in neutral)
    out["verdict"] = ("FAIL" if any(falsely_admitted(out[k]) for k in unbalanced) else
                      "PASS" if (typed_everywhere and neutral_ok) else "AMBIGUOUS")
    return out


# ===================================================================================================== P4 closure
_P4_CHILD = r'''
import json, sys
from experiments.sandbox_foundation import general_kernel as gk
from experiments.sandbox_foundation import solid_equilibrium as se
from experiments.sandbox_foundation.aqueous_equilibrium import SourcedConstant
from experiments.sandbox_foundation.general_coupled import Compartment, CoupledWorld
from experiments.sandbox_foundation.general_kernel import ChemicalSystem, Phase, Reaction, Species
M = Species.of("M+", {"M": 1}, 1, Phase.AQUEOUS); X = Species.of("X-", {"X": 1}, -1, Phase.AQUEOUS)
S = Species.of("MX(s)", {"M": 1, "X": 1}, 0, Phase.SOLID)
st = ((S, -1), (M, 1), (X, 1))
def world(ksp):
    c = SourcedConstant("Ksp", ksp, ksp * 0.01, "dimensionless", 298.15, "probe synthetic", "SOURCED")
    law = se.ActivitySolubilityRate(1e-3, c, st)
    return CoupledWorld([Compartment("c", ChemicalSystem([M, X, S], [Reaction("diss", st, law)], 1.0))])
wa, wb = world(1e-6), world(4e-6)
ini = {"c": {S: 1e-2}}
st_ = gk.audit_status()[("experiments.sandbox_foundation.solid_equilibrium", "ActivitySolubilityRate")]
ta = wa.integrate(ini, duration=200.0, n_steps=20)      # not strict: a demoted law must still REPORT, not crash the child
tb = wb.integrate(ini, duration=200.0, n_steps=20)
print(json.dumps({"audit_status": st_, "certificates_equal": wa._world_certificate == wb._world_certificate,
                  "final_M": [ta.amounts["c"][-1][M], tb.amounts["c"][-1][M]],
                  "certified": [ta.receipt.execution_identity_certified, tb.receipt.execution_identity_certified]}))
'''


def _p4_run(mutate) -> dict:
    """Copy the package to a temp tree, apply ``mutate`` to solid_equilibrium.py there, and run the child in a FRESH
    interpreter whose import path resolves ``experiments`` to the copy (the seal reads the copy's own source file)."""
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(os.path.dirname(here))
    tmp = tempfile.mkdtemp(prefix="xxiv_p4_")
    try:
        dst = os.path.join(tmp, "experiments", "sandbox_foundation")
        os.makedirs(dst)
        shutil.copy(os.path.join(repo, "experiments", "__init__.py"), os.path.join(tmp, "experiments", "__init__.py"))
        for fn in os.listdir(here):
            if fn.endswith(".py"):
                shutil.copy(os.path.join(here, fn), os.path.join(dst, fn))
        path = os.path.join(dst, "solid_equilibrium.py")
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        new = mutate(src)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new)
        env = dict(os.environ, PYTHONPATH=tmp + os.pathsep + repo)
        res = subprocess.run([sys.executable, "-I", "-c", "import sys; sys.path[:0] = %r; " % [tmp, repo] + _P4_CHILD],
                             capture_output=True, text=True, env=env, cwd=tmp, timeout=300)
        if res.returncode != 0:
            return {"error": res.stderr.strip().splitlines()[-1] if res.stderr.strip() else f"rc={res.returncode}",
                    "mutation_applied": new != src}
        rec = json.loads(res.stdout.strip().splitlines()[-1])
        rec["mutation_applied"] = new != src
        return rec
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def probe_closure() -> dict:
    helper_old = "return (c.name, _canon_num(c.value), _canon_num(c.uncertainty),"
    helper_new = "return (c.name, _canon_num(c.uncertainty / c.value),"          # value dropped; rel. uncertainty kept
    body_old = "        omega = iap / self.ksp.value\n"
    body_new = "        omega = iap / self.ksp.value  # audited-body edit (control)\n"
    out = {"baseline": _p4_run(lambda s: s),
           "helper_edit": _p4_run(lambda s: s.replace(helper_old, helper_new)),
           "class_body_edit_control": _p4_run(lambda s: s.replace(body_old, body_new))}
    h = out["helper_edit"]
    ctl = out["class_body_edit_control"]
    out["control_demoted"] = ctl.get("audit_status") not in (None, "SEALED")
    if "error" in h or not h.get("mutation_applied"):
        out["verdict"] = "AMBIGUOUS"
    elif h["audit_status"] == "SEALED" and h["certificates_equal"]:
        differs = abs(h["final_M"][0] - h["final_M"][1]) > 1e-9
        out["verdict"] = "FAIL" if differs else "AMBIGUOUS"
    else:
        out["verdict"] = "PASS"
    return out


# ===================================================================================================== P5 temperature
M_ = Species.of("M+", {"M": 1}, 1, AQ)
X_ = Species.of("X-", {"X": 1}, -1, AQ)
S_ = Species.of("MX(s)", {"M": 1, "X": 1}, 0, Phase.SOLID)
ST_ = ((S_, -1), (M_, 1), (X_, 1))


def _p5_system():
    from experiments.sandbox_foundation.solid_equilibrium import ActivitySolubilityRate
    ksp = SourcedConstant("Ksp", 1e-6, 1e-8, "dimensionless (activity, 1 mol/L std)", 298.15,
                          "probe synthetic 25 C constant", "SOURCED")
    return ChemicalSystem([M_, X_, S_], [Reaction("diss", ST_, ActivitySolubilityRate(1e-3, ksp, ST_))], 1.0)


def probe_temperature() -> dict:
    out = {}
    for T in (298.15, 350.0):
        rec = {}
        try:
            w = CoupledWorld([Compartment("c", _p5_system())], temperature_K=T)
            tr = w.integrate({"c": {S_: 1e-2}}, duration=200.0, n_steps=20, require_certified_execution=True)
            rec.update(coupled="RAN", final_M=tr.amounts["c"][-1][M_], admitted_tier=tr.receipt.admitted_tier,
                       certified=tr.receipt.execution_identity_certified,
                       source_domain=str(_get(tr.receipt, "source_domain", "<no field>")))
        except (CoupledError, KernelError) as exc:
            rec.update(coupled="REFUSED", coupled_reason=f"{type(exc).__name__}: {str(exc)[:140]}")
        try:
            tk = _p5_system().integrate({S_: 1e-2}, duration=200.0, temperature_K=T)
            rec.update(kernel="RAN", kernel_final_M=tk.amounts[-1][M_], kernel_admitted=tk.receipt.admitted_tier,
                       kernel_source_domain=str(_get(tk.receipt, "source_domain", "<no field>")))
        except KernelError as exc:
            rec.update(kernel="REFUSED", kernel_reason=f"{type(exc).__name__}: {str(exc)[:140]}")
        out[str(T)] = rec
    hot, ref = out["350.0"], out["298.15"]
    ref_ok = ref.get("coupled") == "RAN" and ref.get("kernel") == "RAN"
    silent = ((hot.get("coupled") == "RAN" and hot.get("certified") is True and hot.get("source_domain") == "<no field>")
              or (hot.get("kernel") == "RAN" and hot.get("kernel_source_domain") == "<no field>"))
    demoted = all(hot.get(k) == "REFUSED" or "UNSUPPORTED" in str(hot.get(f)) or "REFUSED" in str(hot.get(f))
                  for k, f in (("coupled", "source_domain"), ("kernel", "kernel_source_domain")))
    out["verdict"] = "FAIL" if silent else ("PASS" if (demoted and ref_ok) else "AMBIGUOUS")
    return out


def run() -> dict:
    return {"P1_f2_operator_authority": probe_f2(), "P2_p6b_positivity": probe_p6b(), "P3_charge_contract": probe_charge(),
            "P4_dependency_closure": probe_closure(), "P5_temperature_transport": probe_temperature()}


def main() -> int:
    res = run()
    print(json.dumps(res, indent=1, sort_keys=True, default=str))
    print("VERDICTS", {k: v["verdict"] for k, v in res.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
