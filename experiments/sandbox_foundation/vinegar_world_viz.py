"""OPERATION XXIII -- ONE self-contained, deterministic HTML view of the vented-vs-sealed vinegar world.

A PROJECTION of the scenario frames (vinegar_world_scenarios), nothing more: inline CSS/JS/SVG, no network, no external
libraries, no timestamps -- the same frames always produce byte-identical HTML.  Every panel is captioned with its
QuantityKind + claim tier.  The optional rising glyphs are an ILLUSTRATION layer (rate proportional to the modeled
Henry flux; bubble geometry not modeled) and are labeled as such every place they appear.

Nothing here flows back into the model: the page reads a JSON blob and draws it.  (It's a picture of a computation.
It is not the computation, and it is definitely not evidence.  I'm saying it twice because someone will screenshot it.)

CLI:  python -m experiments.sandbox_foundation.vinegar_world_viz --out <path.html>
"""
from __future__ import annotations

import argparse
import html
import json
import os

from experiments.sandbox_foundation.vinegar_world_scenarios import (
    REGIMES,
    SAFETY_NOTICE,
    DeclaredChemistry,
    run_both,
)

BANNER = ("projection of a computed model — no animated phenomenon certifies itself; ASSUMED kinetics; "
          "not a safety certification")
ILLUSTRATION_LABEL = "ILLUSTRATION — glyph rate ∝ modeled Henry flux; bubble geometry not modeled"

#: (key, title) -- the small-multiple panels, in display order
PANELS = (
    ("solid_NaHCO3_mol", "Solid NaHCO₃ remaining"),
    ("DIC_A_mol", "Dissolved inorganic carbon — cell A"),
    ("DIC_B_mol", "Dissolved inorganic carbon — cell B"),
    ("pH_A", "pH (activity) — cell A"),
    ("pH_B", "pH (activity) — cell B"),
    ("total_acetate_A_mol", "Total acetate — cell A"),
    ("total_acetate_B_mol", "Total acetate — cell B"),
    ("CO2_gas_mol", "Headspace CO₂(g) inventory"),
    ("p_CO2_atm", "p_CO₂ = nRT/V (CO₂ above initial headspace)"),
    ("henry_flux_B_to_gas_mol_per_s", "Henry flux B → gas (+ = degassing)"),
    ("export_flux_mol_per_s", "Export flux out of vessel"),
    ("cumulative_C_exported_mol", "Cumulative carbon exported"),
)
UNSUPPORTED_KEYS = ("bubble_diameter_m", "foam_height_m", "total_headspace_pressure_atm",
                    "ledger_C_external_flux_phase_mol")


def _series(scn: dict) -> dict:
    """Column-ise one regime's typed frames into compact series + per-panel metadata (kind/tier/unit/label)."""
    frames = scn["frames"]
    out = {"time_s": [f["time_s"] for f in frames], "phase": [f["phase"] for f in frames], "panels": {}}
    for key, title in PANELS:
        qs = [f["quantities"][key] for f in frames]
        kinds = sorted({q["kind"] for q in qs})
        tiers = sorted({q["tier"] for q in qs})
        out["panels"][key] = {"title": title, "unit": qs[0]["unit"], "kind": " / ".join(kinds),
                              "tier": " / ".join(tiers), "label": qs[0]["label"],
                              "values": [q["value"] for q in qs]}
    last = frames[-1]["quantities"]
    out["unsupported"] = {k: {"kind": last[k]["kind"], "tier": last[k]["tier"], "value": last[k]["value"],
                              "label": last[k]["label"]} for k in UNSUPPORTED_KEYS
                          if last[k]["kind"] == "UNSUPPORTED"}
    out["claim_tier"] = [f["quantities"]["claim_tier"]["value"] for f in frames]
    out["claim_label"] = last["claim_tier"]["label"]
    out["receipts"] = [{"phase": r["phase"], "admitted_tier": r["admitted_tier"],
                        "material_balance_closed": r["material_balance_closed"],
                        "component_resolution": r["component_resolution"],
                        "execution_identity_basis": r["execution_identity_basis"]} for r in scn["receipts"]]
    out["assumptions"] = last["active_assumptions"]["value"]
    out["identities"] = {k: v[:16] for k, v in scn["identities"].items()}
    out["boundary"] = scn["boundary"]
    out["notices"] = scn["notices"]
    return out


def build_payload(both: dict) -> dict:
    return {"api_version": both["vented"]["api_version"], "banner": BANNER, "safety": SAFETY_NOTICE,
            "illustration_label": ILLUSTRATION_LABEL, "panel_order": [k for k, _ in PANELS],
            "regimes": {r: _series(both[r]) for r in REGIMES},
            "difference": both["difference_sealed_minus_vented"]}


_CSS = r"""
:root{--bg:#f6f7f9;--card:#fff;--ink:#16181d;--mute:#5b6270;--line:#d9dde4;--vent:#0b7a75;--seal:#c2410c;
--warn-bg:#fff4e5;--warn-ink:#7a3a00;--gas:#94a3b8;--liq:#cfe8ff;--chip:#eef1f5}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#171a21;--ink:#e7e9ee;--mute:#9aa3b2;--line:#2a2f3a;
--vent:#2dd4bf;--seal:#fb923c;--warn-bg:#2a1c0c;--warn-ink:#fcd9a8;--gas:#475569;--liq:#1e3a5f;--chip:#222733}}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.banner{position:sticky;top:0;z-index:5;background:var(--warn-bg);color:var(--warn-ink);padding:.6rem 1rem;
font-weight:600;border-bottom:1px solid var(--line);text-align:center}
main{max-width:1200px;margin:0 auto;padding:1rem}
h1{font-size:1.35rem;margin:.4rem 0 .2rem}h2{font-size:1.05rem;margin:0 0 .4rem}
.sub{color:var(--mute);margin:0 0 1rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:.8rem}
.duo{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1rem;margin-bottom:1rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:.8rem}
.cap{font-size:.75rem;color:var(--mute);margin-top:.3rem}
.chip{display:inline-block;background:var(--chip);border-radius:999px;padding:.05rem .5rem;font-size:.72rem;
margin-right:.25rem;font-weight:600}
.vent{color:var(--vent)}.seal{color:var(--seal)}
.scrub{display:flex;gap:.6rem;align-items:center;flex-wrap:wrap;margin:0 0 1rem}
.scrub input[type=range]{flex:1;min-width:180px;accent-color:var(--vent)}
.glyphs-wrap svg{max-width:240px;margin:.4rem auto}
button{background:var(--chip);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:.35rem .8rem;
font:inherit;cursor:pointer}
table{border-collapse:collapse;width:100%;font-size:.82rem}td{padding:.15rem .3rem;border-bottom:1px solid var(--line)}
td.v{text-align:right;font-variant-numeric:tabular-nums}
svg{display:block;width:100%;height:auto}
.illu{font-size:.72rem;color:var(--mute);font-style:italic}
footer{color:var(--mute);font-size:.78rem;margin:1.5rem 0}
"""

_JS = r"""
(function(){
const D=JSON.parse(document.getElementById('data').textContent);
const R=['vented','sealed'];const COL={vented:'var(--vent)',sealed:'var(--seal)'};
const N=D.regimes.vented.time_s.length;
const slider=document.getElementById('t');slider.max=String(N-1);
const tlabel=document.getElementById('tl');
function fmt(v){if(v===null||v===undefined)return 'null';if(typeof v!=='number')return String(v);
 const a=Math.abs(v);if(a!==0&&(a<1e-3||a>=1e4))return v.toExponential(3);return v.toPrecision(4);}
function el(tag,attrs,txt){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);
 for(const k in attrs)e.setAttribute(k,attrs[k]);if(txt!==undefined)e.textContent=txt;return e;}
// ---- small multiples (both regimes overlaid, shared cursor)
const grid=document.getElementById('grid');const cursors=[];
D.panel_order.forEach(function(key){
 const pv=D.regimes.vented.panels[key],ps=D.regimes.sealed.panels[key];
 const card=document.createElement('div');card.className='card';
 const h=document.createElement('h2');h.textContent=pv.title;card.appendChild(h);
 const W=300,H=130,L=44,B=18,T=6,Rm=6;
 const svg=el('svg',{viewBox:'0 0 '+W+' '+H,role:'img','aria-label':pv.title});
 let lo=Infinity,hi=-Infinity;R.forEach(function(r){D.regimes[r].panels[key].values.forEach(function(v){
  if(typeof v==='number'){lo=Math.min(lo,v);hi=Math.max(hi,v);}});});
 if(!isFinite(lo)){lo=0;hi=1;}if(hi-lo<1e-15){hi=lo+1e-12;lo=lo-1e-12;}
 const t=D.regimes.vented.time_s,t0=t[0],t1=t[t.length-1];
 const X=function(x){return L+(W-L-Rm)*(x-t0)/(t1-t0||1);},Y=function(y){return T+(H-T-B)*(1-(y-lo)/(hi-lo));};
 svg.appendChild(el('rect',{x:L,y:T,width:W-L-Rm,height:H-T-B,fill:'none',stroke:'var(--line)'}));
 svg.appendChild(el('text',{x:L-4,y:T+9,'text-anchor':'end','font-size':'9',fill:'var(--mute)'},fmt(hi)));
 svg.appendChild(el('text',{x:L-4,y:H-B,'text-anchor':'end','font-size':'9',fill:'var(--mute)'},fmt(lo)));
 svg.appendChild(el('text',{x:W-Rm,y:H-4,'text-anchor':'end','font-size':'9',fill:'var(--mute)'},fmt(t1)+' s'));
 R.forEach(function(r){const vs=D.regimes[r].panels[key].values;let d='';
  vs.forEach(function(v,i){if(typeof v!=='number')return;d+=(d?'L':'M')+X(t[i]).toFixed(2)+' '+Y(v).toFixed(2);});
  svg.appendChild(el('path',{d:d,fill:'none',stroke:COL[r],'stroke-width':'1.8','stroke-dasharray':r==='sealed'?'':'5 3'}));});
 const cur=el('line',{y1:T,y2:H-B,stroke:'var(--mute)','stroke-width':'1'});svg.appendChild(cur);
 card.appendChild(svg);
 const read=document.createElement('div');read.className='cap';card.appendChild(read);
 const cap=document.createElement('div');cap.className='cap';
 cap.innerHTML='<span class="chip">'+pv.kind+'</span><span class="chip">'+pv.tier+'</span>'+pv.unit;
 card.appendChild(cap);const lab=document.createElement('div');lab.className='cap';lab.textContent=pv.label;card.appendChild(lab);
 grid.appendChild(card);cursors.push({cur:cur,X:X,read:read,key:key});
});
// ---- vessel schematics (side by side)
const rng=function(s){return function(){s=(s*1103515245+12345)%2147483648;return s/2147483648;};};
const vessels={};
R.forEach(function(r){
 const host=document.getElementById('v-'+r);const W=300,H=200;
 const svg=el('svg',{viewBox:'0 0 '+W+' '+H,role:'img','aria-label':r+' vessel schematic'});
 const gas=el('rect',{x:60,y:20,width:180,height:70,fill:'var(--gas)','fill-opacity':'0.1',stroke:'var(--line)'});
 svg.appendChild(gas);
 svg.appendChild(el('rect',{x:60,y:90,width:180,height:90,fill:'var(--liq)',stroke:'var(--line)'}));
 if(r==='vented'){svg.appendChild(el('path',{d:'M140 20 L140 8 M160 20 L160 8',stroke:'var(--vent)','stroke-width':'3'}));
  svg.appendChild(el('text',{x:172,y:12,'text-anchor':'start','font-size':'9',fill:'var(--mute)'},'vent (export)'));}
 else svg.appendChild(el('rect',{x:56,y:14,width:188,height:8,fill:'var(--seal)'}));
 const solid=el('rect',{x:70,y:170,width:0,height:8,fill:'var(--mute)'});svg.appendChild(solid);
 const g=el('g',{});svg.appendChild(g);
 const pt=el('text',{x:150,y:58,'text-anchor':'middle','font-size':'13','font-weight':'700',fill:'var(--ink)'},'');
 svg.appendChild(pt);
 const lt=el('text',{x:150,y:132,'text-anchor':'middle','font-size':'12',fill:'var(--ink)'},'');svg.appendChild(lt);
 host.appendChild(svg);
 const glyphs=[];const rand=rng(r==='vented'?7:11);
 for(let i=0;i<40;i++){const c=el('circle',{cx:(70+rand()*160).toFixed(1),cy:'178',r:(1.2+rand()*1.5).toFixed(2),
  fill:'none',stroke:'var(--ink)','stroke-opacity':'0.45'});c.style.display='none';g.appendChild(c);
  glyphs.push({c:c,y:178-rand()*85,on:false});}
 vessels[r]={gas:gas,solid:solid,pt:pt,lt:lt,glyphs:glyphs,tbl:document.getElementById('tb-'+r),acc:0};
});
const maxJ=Math.max.apply(null,R.map(function(r){return Math.max.apply(null,
 D.regimes[r].panels.henry_flux_B_to_gas_mol_per_s.values.map(function(v){return Math.abs(v||0);}));}))||1;
const maxP=Math.max.apply(null,R.map(function(r){return Math.max.apply(null,
 D.regimes[r].panels.p_CO2_atm.values.map(function(v){return v||0;}));}))||1;
const solid0=D.regimes.vented.panels.solid_NaHCO3_mol.values[0]||1;
let idx=0;
function draw(){
 tlabel.textContent='t = '+fmt(D.regimes.vented.time_s[idx])+' s · phase: '+D.regimes.vented.phase[idx];
 cursors.forEach(function(c){const x=c.X(D.regimes.vented.time_s[idx]);c.cur.setAttribute('x1',x);c.cur.setAttribute('x2',x);
  c.read.innerHTML='<span class="vent">vented '+fmt(D.regimes.vented.panels[c.key].values[idx])+'</span> · '+
  '<span class="seal">sealed '+fmt(D.regimes.sealed.panels[c.key].values[idx])+'</span>';});
 R.forEach(function(r){const P=D.regimes[r].panels,v=vessels[r];const p=P.p_CO2_atm.values[idx];
  v.gas.setAttribute('fill-opacity',(0.08+0.6*Math.max(0,p)/maxP).toFixed(3));
  v.pt.textContent='p_CO₂ '+fmt(p)+' atm';v.lt.textContent='pH_B '+fmt(P.pH_B.values[idx]);
  v.solid.setAttribute('width',(160*Math.max(0,P.solid_NaHCO3_mol.values[idx])/solid0).toFixed(1));
  let rows='';['solid_NaHCO3_mol','DIC_B_mol','pH_A','pH_B','CO2_gas_mol','p_CO2_atm','henry_flux_B_to_gas_mol_per_s',
   'cumulative_C_exported_mol'].forEach(function(k){rows+='<tr><td>'+P[k].title+'</td><td class="v">'+fmt(P[k].values[idx])+
   ' '+(P[k].unit==='1'?'':P[k].unit)+'</td></tr>';});
  rows+='<tr><td>claim tier</td><td class="v">'+D.regimes[r].claim_tier[idx]+'</td></tr>';v.tbl.innerHTML=rows;});
}
// ILLUSTRATION: glyph spawn rate proportional to the modeled Henry flux at the cursor (no bubble model exists)
function animate(){
 R.forEach(function(r){const v=vessels[r];const J=Math.max(0,D.regimes[r].panels.henry_flux_B_to_gas_mol_per_s.values[idx]||0);
  v.acc+=0.9*J/maxJ;while(v.acc>=1){v.acc-=1;const gl=v.glyphs.find(function(x){return !x.on;});if(!gl)break;gl.on=true;gl.y=178;gl.c.style.display='';}
  v.glyphs.forEach(function(gl){if(!gl.on)return;gl.y-=1.6;if(gl.y<92){gl.on=false;gl.c.style.display='none';}
   gl.c.setAttribute('cy',gl.y.toFixed(1));});});
 requestAnimationFrame(animate);
}
let playing=null;
slider.addEventListener('input',function(){idx=+slider.value;draw();});
document.getElementById('play').addEventListener('click',function(e){
 if(playing){clearInterval(playing);playing=null;e.target.textContent='▶ play';return;}
 e.target.textContent='❚❚ pause';playing=setInterval(function(){idx=(idx+1)%N;slider.value=String(idx);draw();},80);});
const illu=document.getElementById('illu');
illu.addEventListener('change',function(){document.querySelectorAll('.glyphs-wrap g').forEach(function(g){
 g.style.display=illu.checked?'':'none';});});
draw();animate();
})();
"""


def _side(regime: str, s: dict) -> str:
    cls = "vent" if regime == "vented" else "seal"
    bnd = "; ".join(f"{k}: {v['transport_mode']}, {'vented' if v['vented'] else 'sealed'}"
                    for k, v in s["boundary"].items())
    rec = "".join(
        f"<tr><td>{html.escape(r['phase'])}</td><td class='v'>{html.escape(r['admitted_tier'])} · "
        f"{'closed' if r['material_balance_closed'] else 'NOT closed'} · "
        f"{html.escape(', '.join(f'{k}:{v}' for k, v in sorted(r['component_resolution'].items())))} · "
        f"{html.escape(r['execution_identity_basis'])}</td></tr>" for r in s["receipts"])
    uns = "".join(f"<tr><td>{html.escape(k)}</td><td class='v'>null <span class='chip'>{html.escape(v['kind'])}"
                  f"</span><span class='chip'>{html.escape(v['tier'])}</span></td></tr>"
                  for k, v in s["unsupported"].items())
    ids = " · ".join(f"{k.replace('_digest', '')} {v}" for k, v in s["identities"].items())
    return (f"<section class='card'><h2 class='{cls}'>{regime.upper()}</h2>"
            f"<div class='cap'>boundary — {html.escape(bnd)}</div>"
            f"<div class='glyphs-wrap' id='v-{regime}'></div>"
            f"<div class='illu'>{html.escape(ILLUSTRATION_LABEL)}</div>"
            f"<table id='tb-{regime}'></table>"
            f"<h2 style='margin-top:.6rem'>Receipts</h2><table>{rec}</table>"
            f"<h2 style='margin-top:.6rem'>Not modeled</h2><table>{uns}</table>"
            f"<div class='cap'>identity: {html.escape(ids)}</div></section>")


def render_html(payload: dict) -> str:
    data = json.dumps(payload, sort_keys=True, allow_nan=False, separators=(",", ":")).replace("</", "<\\/")
    reg = payload["regimes"]
    assumptions = "".join(f"<tr><td>{html.escape(a['name'])}</td><td class='v'>{a['value']:.6g} "
                          f"{html.escape(a['unit'])} <span class='chip'>{html.escape(a['provenance_tier'])}</span>"
                          f"</td></tr>" for a in reg["vented"]["assumptions"])
    diff = payload["difference"]
    diff_rows = "".join(f"<tr><td>{html.escape(k)}</td><td class='v'>{('%+.4g' % v) if v is not None else 'null'}"
                        f"</td></tr>" for k, v in diff.items())
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>SmartChem vinegar world — vented vs sealed (research projection)</title>
<style>{_CSS}</style></head>
<body>
<div class="banner" role="note">{html.escape(payload['banner'])}</div>
<main>
<h1>Vinegar + baking soda: vented vs sealed headspace</h1>
<p class="sub">Same declared chemistry, two boundary regimes. {html.escape(payload['safety'])}.
API <code>{html.escape(payload['api_version'])}</code> (research-only, not stable).</p>
<div class="scrub card"><button id="play" type="button">▶ play</button>
<input id="t" type="range" min="0" value="0" step="1" aria-label="time scrubber">
<span id="tl" class="cap"></span>
<label class="cap"><input id="illu" type="checkbox" checked> show ILLUSTRATION glyphs</label></div>
<div class="duo">{_side('vented', reg['vented'])}{_side('sealed', reg['sealed'])}</div>
<p class="cap"><span class="vent">— — vented</span> &nbsp; <span class="seal">——— sealed</span> &nbsp;·&nbsp;
every panel: QuantityKind · claim tier · unit</p>
<div class="grid" id="grid"></div>
<div class="duo" style="margin-top:1rem">
<section class="card"><h2>End state: sealed − vented</h2><table>{diff_rows}</table>
<div class="cap">emergent from the boundary alone; MODEL_DERIVED · ASSUMED_PARAMETER</div></section>
<section class="card"><h2>Active assumptions (uncalibrated)</h2><table>{assumptions}</table>
<div class="cap">CANONICAL inputs · ASSUMED_PARAMETER — the dynamic claim cannot exceed these</div></section></div>
<footer>{html.escape(payload['banner'])}. Pressure is the ideal-gas projection of the modeled CO₂(g) inventory; air is not
modeled. Bubble size, foam and total pressure are UNSUPPORTED (null). Generated by
experiments/sandbox_foundation/vinegar_world_viz.py.</footer>
</main>
<script id="data" type="application/json">{data}</script>
<script>{_JS}</script>
</body></html>
"""


def write_html(out_path: str, chem: DeclaredChemistry = DeclaredChemistry()) -> str:
    text = render_html(build_payload(run_both(chem)))
    d = os.path.dirname(out_path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="write the vented-vs-sealed vinegar world HTML projection")
    ap.add_argument("--out", required=True, metavar="PATH.html")
    args = ap.parse_args(argv)
    write_html(args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
