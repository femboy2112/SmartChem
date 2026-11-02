import json, math
ph=json.load(open('phreeqc_results.json')); co=json.load(open('code_results.json'))
def P(case,db,units): 
    return [x for x in ph if x['case']==case and x['db']==db and x['units']==units][0]
HAC={"minteq.v4":"H(Acetate)","llnl":"HAcetate"}
def cls(d): return "AGREE" if d<=0.02 else ("MARGINAL" if d<=0.05 else "DIVERGE")
rows=[]; 
print("%-16s %6s %6s | %-9s %8s | %8s %8s %8s %8s | %7s %7s %7s | %s"%("case","CT","Na","DB","I_ph(m)","pH_ph","pH_dav","|dpH|","cls","dH+%","dAc%","dHAc%","verdict/gamma(code vs ph H+)"))
for c in co:
    d=c['davies']
    for db in ("minteq.v4","llnl"):
        p=P(c['case'],db,'molar-matched'); pk=P(c['case'],db,'mol/kgw')
        if d.get('refused'):
            print("%-16s %6g %6g | %-9s %8.4f | %8.4f %8s %8s %8s | code REFUSED: %s"%(c['case'],c['CT'],c['Na'],db,p['I_molal'],p['pH'],'-','-','REFUSED',d['exc']+' '+str(d['verdict']))); continue
        dp=abs(d['pH_activity']-p['pH'])
        m=p['molarity']
        e=lambda a,b:(abs(a-b)/b*100 if b>0 else float('nan'))
        # No acetate in the glass means no acetate relative-error to speak of: emit None (a JSON null that
        # survives strict cross-language parsers), not a bare NaN that only Python's permissive loader tolerates.
        dH=e(d['h'],m['H+']); dAc=e(d['ac'],m['Acetate-']) if c['CT']>0 else None; dHA=e(d['hac'],m[HAC[db]]) if c['CT']>0 else None
        row=dict(case=c['case'],CT=c['CT'],Na=c['Na'],db=db,I_ph=p['I_molal'],I_code=d['I'],pH_ph=p['pH'],pH_ph_kgw=pk['pH'],pH_code=d['pH_activity'],dpH=dp,cls=cls(dp),dH=dH,dAc=dAc,dHAc=dHA,
                 gamma_code=d['gamma'],gamma_H_ph=p['gamma']['H+'],gamma_Ac_ph=p['gamma'].get('Acetate-'),NaAc_pair_frac=(p['molarity'].get('Na(Acetate)',p['molarity'].get('NaAcetate',0))/c['CT'] if c['CT']>0 else 0))
        if c['CT']==0: row['rel_err_undefined_reason']="REFERENCE_SPECIES_ABSENT"   # name the diagnosis; absent otherwise, so CT>0 rows stay byte-identical
        rows.append(row)
        print("%-16s %6g %6g | %-9s %8.4f | %8.4f %8.4f %8.4f %8s | %7.2f %7.2f %7.2f | g_code=%.4f g_H,ph=%.4f"%(c['case'],c['CT'],c['Na'],db,p['I_molal'],p['pH'],d['pH_activity'],dp,cls(dp),dH,dAc,dHA,d['gamma'],p['gamma']['H+']))
json.dump(rows,open('comparison_table.json','w'),indent=1,allow_nan=False)   # reject any future nonfinite loudly at export rather than writing a token no other parser reads
