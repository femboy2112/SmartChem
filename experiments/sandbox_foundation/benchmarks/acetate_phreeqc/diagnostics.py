import json
ph=json.load(open('phreeqc_results.json')); co=json.load(open('code_results.json'))
def P(case,db,u='molar-matched'): return [x for x in ph if x['case']==case and x['db']==db and x['units']==u][0]
core=["C1","C2","C3","C4","C5"]
print("DIAGNOSTICS (NOT part of the pre-registered verdict).  all pH; PH=PHREEQC molar-matched; dpH vs PHREEQC-with-pair")
print("%-4s %-9s | %7s | %8s %7s | D1:%8s %7s | D2 noPair:%7s %7s | D1+D2 dpH | ideal(conc) vs PH conc-pH"%("case","DB","PH","code(dav)","dpH","code","dpH","PH","dpH"))
out=[]
for c in co:
    if c['case'] not in core: continue
    for db,key in (("minteq.v4","minteq.v4"),("llnl","llnl_eff25")):
        p=P(c['case'],db); pn=P(c['case'],db+".noNaAcPair")
        d=c['davies']; d1=c['D1_davies_'+key]; idl=c['ideal']
        d0=abs(d['pH_activity']-p['pH']); d1p=abs(d1['pH_activity']-p['pH']); d2=abs(d['pH_activity']-pn['pH']); d12=abs(d1['pH_activity']-pn['pH'])
        ideal_vs=abs(idl['pH_concentration']-p['pH_conc_molar'])
        print("%-4s %-9s | %7.4f | %8.4f %7.4f | %8.4f %7.4f | %7.4f %7.4f | %7.4f | ideal %7.4f vs PHconc %7.4f (d=%.4f)  ideal-vs-PH-activity-pH d=%.4f"%(c['case'],db,p['pH'],d['pH_activity'],d0,d1['pH_activity'],d1p,pn['pH'],d2,d12,idl['pH_concentration'],p['pH_conc_molar'],ideal_vs,abs(idl['pH_concentration']-p['pH'])))
        out.append(dict(case=c['case'],db=db,PH=p['pH'],PH_noPair=pn['pH'],code_davies=d['pH_activity'],code_davies_D1=d1['pH_activity'],code_ideal_conc=idl['pH_concentration'],PH_conc_molar=p['pH_conc_molar']))
json.dump(out,open('diagnostics_table.json','w'),indent=1)
