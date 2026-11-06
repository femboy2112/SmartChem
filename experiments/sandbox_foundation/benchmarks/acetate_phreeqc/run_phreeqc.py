"""PHREEQC runner (phreeqpython 1.6.2, isolated venv).  Tool-computed numbers only."""
import json, sys, math
from pathlib import Path
from phreeqpython import PhreeqPython

HERE = Path(__file__).resolve().parent
DBS = {
  "minteq.v4":           (HERE/"db_dl", "minteq.v4.dat", "Acetate", "Acetate-", ["H(Acetate)","Acetate-","Na(Acetate)"]),
  "llnl":                (HERE/"db_dl", "llnl.dat", "Acetate", "HAcetate", ["HAcetate","Acetate-","NaAcetate"]),
  "minteq.v4.noNaAcPair":(HERE/"db_variants", "minteq.v4.noNaAcPair.dat", "Acetate", "Acetate-", ["H(Acetate)","Acetate-","Na(Acetate)"]),
  "llnl.noNaAcPair":     (HERE/"db_variants", "llnl.noNaAcPair.dat", "Acetate", "HAcetate", ["HAcetate","Acetate-","NaAcetate"]),
}
# species table: name -> (charge, nNa, nAc, gfw)  [Ac = CH3COO-]
SP={"H+":(1,0,0,1.008),"OH-":(-1,0,0,17.007),"Na+":(1,1,0,22.990),"Acetate-":(-1,0,1,59.045),
    "H(Acetate)":(0,0,1,60.053),"HAcetate":(0,0,1,60.053),"Na(Acetate)":(0,1,1,82.035),"NaAcetate":(0,1,1,82.035),
    "Na(Acetate)2-":(-1,1,2,141.080),"NaOH":(0,1,0,39.997)}
IGNORE={"H2O","H2","O2"}   # H2/O2 are ~1e-30 redox artefacts
def run(dbkey, CT, Na, units):
    d, f, el, _, acet = DBS[dbkey]
    pp = PhreeqPython(database=f, database_directory=d)
    lines = ["SOLUTION 1", f"  units {units}", "  temp 25", "  pH 7 charge"]
    if Na>0: lines.append(f"  Na {Na!r}")
    if CT>0: lines.append(f"  {el} {CT!r}")
    lines.append("END")
    pp.ip.run_string("\n".join(lines))
    s = pp.get_solution(1)
    mol = {k:v for k,v in s.species_molalities.items()}
    act = {k:v for k,v in s.species_activities.items()}
    nmol = {k:v for k,v in s.species_moles.items()}
    V = s.volume
    out = dict(db=dbkey, units=units, CT=CT, Na=Na, pH=s.pH, I_molal=s.I, volume_L=V, density=s.density, mass_kg=s.mass)
    unk=[k for k,v in mol.items() if k not in SP and k not in IGNORE and v>1e-12]
    if unk: raise RuntimeError(f"unmodelled species above 1e-12 mol/kgw: {unk}")
    keys=[k for k in SP if k in mol]
    out["molality"]={k:mol[k] for k in keys}
    out["activity"]={k:act.get(k,0.0) for k in keys}
    out["moles"]={k:nmol.get(k,0.0) for k in keys}
    out["gamma"]={k:(act[k]/mol[k] if mol[k]>0 and k in act else None) for k in keys}
    # molarity from molality via PHREEQC density (AMENDMENT-1: get_volume() is water-only, not solution volume)
    solute_g_per_kgw=sum(mol[k]*SP[k][3] for k in keys)
    f=s.density/(1.0+solute_g_per_kgw/1000.0)   # kg water per L solution
    out["kgw_per_L_solution"]=f
    out["molarity"]={k:mol[k]*f for k in keys}
    out["molarity_Na_total_check"]=sum(out["molarity"][k]*SP[k][1] for k in keys)
    out["acetate_total_molarity"]=sum(out["molarity"][k]*SP[k][2] for k in keys)
    out["acetate_total_molality"]=sum(mol[k]*SP[k][2] for k in keys)
    out["charge_residual_molal"]=sum(mol[k]*SP[k][0] for k in keys)
    out["pH_conc_molar"]=-math.log10(out["molarity"]["H+"])
    out["pH_conc_molal"]=-math.log10(mol["H+"])
    return out

def run_any(db, CT, Na, units):
    """AMENDMENT-2 (before any code-vs-PHREEQC comparison): PHREEQC's own `units mol/l` converts to molality assuming
    density 1.0 g/mL (observed: Na_total_molarity/input = rho_calc), so the 'mol/l' input is not a true molar input.
    'molar-matched' = fixed-point iteration on kgw input so that the sum of species molarities, with
    molarity_i = m_i * rho_PHREEQC/(1+sum m_j M_j/1000), reproduces the requested C_T and Na to <1e-10."""
    if units=="mol/kgw":
        return run(db,CT,Na,"mol/kgw")
    f=0.9970
    for _ in range(60):
        o=run(db,CT/f,Na/f,"mol/kgw")
        fn=o["kgw_per_L_solution"]
        if abs(fn-f)<1e-13: break
        f=fn
    o["units"]="molar-matched"; o["CT_requested_molar"]=CT; o["Na_requested_molar"]=Na; o["fixed_point_f"]=f
    return o

if __name__=="__main__":
    grid=json.load(open(sys.argv[1])); res=[]
    for c in grid:
        for db in DBS:
            for units in ("mol/kgw","molar-matched"):
                try: res.append(dict(case=c["id"], **run_any(db,c["CT"],c["Na"],units)))
                except Exception as e: res.append(dict(case=c["id"],db=db,units=units,CT=c["CT"],Na=c["Na"],error=repr(e)))
    json.dump(res,open(sys.argv[2],"w"),indent=1)
    print("wrote",len(res))
