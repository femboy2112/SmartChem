"""Run AcetateWaterSystem.solve over the pre-registered grid (READ-ONLY import of the repo module)."""
import sys, json, math
sys.dont_write_bytecode = True
sys.path.insert(0, "/home/leah/SmartChem")
from experiments.sandbox_foundation import aqueous_equilibrium as ae

def pack(r):
    return dict(pH=r.pH, pH_concentration=r.pH_concentration, pH_activity=r.pH_activity, verdict=r.verdict,
                h=r.h_plus_M, oh=r.oh_minus_M, hac=r.hac_M, ac=r.ac_minus_M, I=r.ionic_strength_M,
                gamma=r.gamma_monovalent, charge_resid=r.charge_balance_residual, solver_resid=r.solver_agreement_residual,
                iters=r.davies_iterations, activity_model=r.activity_model)

def run(CT, Na, model, Ka=None, Kw=None):
    kw = {}
    if Ka is not None: kw["Ka"]=Ka
    if Kw is not None: kw["Kw"]=Kw
    try:
        r = ae.solve(ae.AcetateWaterSystem(total_acetic_M=CT, sodium_M=Na, activity_model=model, **kw))
        return pack(r)
    except Exception as e:
        return dict(refused=True, exc=type(e).__name__, verdict=getattr(e,"verdict",None), msg=str(e)[:300])

def SC(name, v):  # diagnostic-only constants (scratch); uncertainty is a placeholder the solver never reads
    return ae.SourcedConstant(name, v, v*1e-3, "dimensionless (molar, ideal reference)", 298.15, "DIAGNOSTIC D1 scratch (PHREEQC DB log_k)", "SOURCED")

if __name__=="__main__":
    grid=json.load(open(sys.argv[1])); out=[]
    D1 = {"minteq.v4": (SC("Ka",10**-4.757), SC("Kw",10**-13.997)),
          "llnl_eff25":(SC("Ka",10**-4.7722), SC("Kw",10**-14.0162))}
    for c in grid:
        row=dict(case=c["id"], CT=c["CT"], Na=c["Na"])
        row["ideal"]=run(c["CT"],c["Na"],"ideal"); row["davies"]=run(c["CT"],c["Na"],"davies")
        for k,(Ka,Kw) in D1.items():
            row["D1_ideal_"+k]=run(c["CT"],c["Na"],"ideal",Ka,Kw); row["D1_davies_"+k]=run(c["CT"],c["Na"],"davies",Ka,Kw)
        out.append(row)
    json.dump(out,open(sys.argv[2],"w"),indent=1); print("wrote",len(out))
