# Fold: the free-energy landscape frame → functorial physics (Move 2) and the Rung-B decoration slot

**Status:** research fold (internalizes an external framing against the tree; no code claim in this document)
**Date:** 2026-09-07
**Branch:** move1-rung-b-open-chem-diagram-2026-09-07
**Baseline:** main at `bb042b37cf76d9ab0313c96c24a70e85cc7ed3f9`
**Provenance of the framing:** a user-supplied ChatGPT exchange (chemistry as a thermodynamic-potential landscape rather than a Lagrangian). This document folds that framing **against the existing tree** the way the R21 ChatGPT external review was folded (`ONLOAD_REDERIVATION_SCOPE_DECISION_v0.2.md`): keep what the code already earns, name the genuinely new leverage, refuse the traps, and cite only what is verifiable.
**Scope:** a design fold that (a) sharpens the Move-1 keystone's decoration mechanism and (b) adds a Move-2 rung. It builds **no** new physics and asserts **no** new sourced value. Every external citation below was verified against arXiv/journal/ADS; anything not verified is marked.

---

## 0. The framing, in one line

The settling state of a synthesis is a **local minimum of a thermodynamic potential** (Gibbs free energy at fixed *T,P*), **not** a Lagrangian/least-action extremum; and *which* product forms is decided by **two distinct, non-collapsible quantities** — the thermodynamic drive `Δ_rG` (which basin) and the kinetic barrier `ΔG‡` (which basin is *reachable*). "Synthesis is controlled navigation of a metastable free-energy landscape."

This is a correction the user's original "Lagrangian" intuition and a sharpening of our own plan. We honor the correction (no MD/Lagrangian layer — §4) and use the sharpening (§2, §3).

---

## 1. What the tree already earns (do not re-derive)

Two of the three functors the framing calls for are **already computed in code** — they were simply never recognized or unified *as* functors.

- **Kinetic accessibility — the survival monoid functor `S: Process → ([0,1], ×)`.** Shipped R23. `surviving_fraction = exp(−k·t)`, `k = A·exp(−Ea/RT)` (`smartchem/experiment/stability_horizon.py:124-128`) — i.e. exactly the transition-state / Arrhenius rate. Its composition law `S(g∘f) = S(f)·S(g)` is implemented and named (`smartchem/experiment/composability.py:346-363`) and wired into E1's verdict, only-ever-tightening (`composability.py:391-464`). This *is* the `ΔG‡` axis.
- **Thermodynamic drive — a would-be functor `G: Process → (ℝ, +, ≤)`.** `smartchem/experiment/feasibility.py:245-247` computes `Δ_rG = Δ_rH − T·Δ_rS` by Hess's law from **sourced** ΔH_f°/S° tables (`smartchem/data/thermo.py`, `thermo_extended.py`; CODATA/NIST/CRC), graded FAVORABLE/UNFAVORABLE/BORDERLINE/UNKNOWN with σ(ΔG) propagation; `equilibrium.py:200` derives `K = exp(−ΔG/RT)`. **ΔG_f° is never tabulated — always derived** (`thermo.py:6-7`), which is the honest choice. This is the `Δ_rG` axis, present but **not** framed as a functor and **not** on the morphism backbone.

**The recognition that unifies them:** *Hess's law is functoriality.* A free-energy change is additive along composition, `Δ_rG(g∘f) = Δ_rG(f) + Δ_rG(g)` — a lax-monoidal functor into the ordered abelian group `(ℝ, +, ≤)`. Survival is its multiplicative twin into `([0,1], ×)` (`log` relates them). The two together are the content of Move 2 ("physics as functors into ordered semirings"); we now know two of its axes are built.

---

## 2. The genuinely new, operational content (the upgrade)

Not relabeling. Four concrete consequences:

1. **The composition law becomes a checkable invariant, and it surfaces a real discrepancy.** Today the convergent-DAG thermochemical rollup (DAG-THERMO-01) aggregates ΔG **worst-node-dominated**. That answers "does the route contain a thermodynamically stuck step?" — a legitimate *ranking* heuristic. It is **not** the additive Hess law, which answers a different question: "what is the *net* ΔG of the overall transformation?" The functorial framing separates these two aggregations and makes the additive one a *hard invariant* the code can assert (a property test `net_ΔG(route) == Σ steps`), where the ad-hoc version silently conflated them. **Candidate finding for the Move-2 rung — to be verified against the code, not asserted as a bug here.**
2. **The product order forbids collapse.** `(Δ_rG, S)` is a Pareto product, never one scalar — "favorable ≠ fast." This is the same discipline the Observability Score already enforces (3 axes, no `overall_score`). The Move-2 rung makes the product explicit and audits whether `_route_score`/`_dag_score`'s tier-folding is a true product or a lossy scalarization.
3. **The Move-1 decoration slot must be general.** Recon confirms `open_diagram.py` is topology-only with **no** apex-decoration slot (only transient per-edge opaque `str` labels at `canonicalize`; the survival monoid lives in a *different* subsystem). So the factored core (Rung B) must introduce a **general monoidal-decoration mechanism** — a payload with a declared combine-under-`then`/`tensor` and an interchange-invariance obligation — of which Rung B instantiates **only** conservation + provenance, and ΔG / survival / observability are declared *future instances of the same slot*. This is a design change to Rung B's core seam (see the keystone contract v0.2, §"the keystone: two levels").
4. **A cheap litmus win.** `feasibility.py` can already return the *thermodynamic* verdict on `Br₂ → 2 Br•` the moment Br/Br₂ ΔH_f°/S° are sourced (a data add, not a build). That advances the **walled** DOW-Br₂ litmus: the *thermodynamic* half becomes answerable while the *rate* stays walled (queue item 3b). "Favorable ≠ fast" is literally the DOW-Br₂ situation.

---

## 3. The reaction-network mathematics this rests on (verified precedent)

The framing's `dc/dt = S·v(c)`, affinity `𝒜 = −Sᵀμ = −Δ_rG`, and gradient flow `dc/dt = −M(c)∇G(c)` are established, and they name the exact categorical home of the keystone.

- **Open reaction networks *are* the keystone's mathematics.** J.C. Baez & B.S. Pollard, *A Compositional Framework for Reaction Networks*, **Rev. Math. Phys. 29 (2017), 1750028** (arXiv:1704.02051): open reaction networks as morphisms of a symmetric monoidal category, with a **black-boxing functor** to the **steady-state** input/output relation. This is more on-point than the circuit precedent and is the natural semantics target of `OpenChemDiagram.close()`. Lineage: Baez–Fong–Pollard, *Markov Processes* (JMP 57, 2016, 033301; arXiv:1508.06448); Baez–Fong, *Passive Linear Networks* (**TAC 33 (2018) No. 38**; decorated cospans; black box → Lagrangian linear relation); Baez–Courser, *Structured Cospans* (**TAC 35 (2020) No. 48**); open Petri nets = Baez–**Master** (MSCS 30(3), 2020) — *not* Courser.
- **Affinity = −Δ_rG** is the standard de Donder definition (de Donder 1922; Kondepudi–Prigogine, *Modern Thermodynamics*). Mass action `dc/dt = S·v(c)`: Feinberg, *Foundations of CRN Theory* (Springer, 2019); Érdi–Tóth (1989).
- **Free energy as a landscape — stated with the caveat the literature forces.** For **detailed-balanced** mass-action networks the free energy is both a Lyapunov function **and** the driving functional of an Onsager/gradient-flow structure `dc/dt = −M(c)∇G(c)` (Mielke, *Nonlinearity* 24, 2011; Maas–Mielke, *J. Stat. Phys.* 181, 2020, arXiv:2004.02831), the latter derivable from the large-deviation principle of the reversible microscopic process (Mielke–Peletier–Renger, *Potential Analysis* 41, 2014). For the **strictly larger complex-balanced class** the free energy remains a Lyapunov function (Horn–Jackson, **Arch. Rational Mech. Anal. 47 (1972), 81–116**; Feinberg deficiency theory) but the dynamics is generally **not** a pure gradient flow — it needs the GENERIC (reversible + irreversible) structure (Grmela–Öttinger, *Phys. Rev. E* 56, 1997). Cite ACGW 2015 (arXiv:1410.4820), not ACK 2010, for the deterministic-Lyapunov bridge.

**Thermodynamics-vs-kinetics textbook anchors:** equilibrium as `min G(ξ)`, `dG/dξ = Δ_rG = Σν_iμ_i`, stable at `d²G/dξ² > 0` (Atkins, *Physical Chemistry*); TST `k = κ·(k_BT/h)·exp(−ΔG‡/RT)` (Eyring 1935, *J. Chem. Phys.* 3, 107); diamond/graphite as the canonical kinetically-trapped metastable state (ΔG° ≈ −2.9 kJ/mol toward graphite, yet indefinitely persistent).

*(Not independently re-verified before quoting elsewhere: exact page ranges of Maas 2011 JFA / Mielke 2013 Calc. Var.; the very recent non-detailed-balance Hamiltonian/Hessian frontier papers' pagination; Evans–Polanyi 1935 pages. "Yong-Jung Kim" as a gradient-flow-of-CRN source is UNVERIFIED — dropped.)*

---

## 4. The traps refused

- **No Lagrangian/least-action / molecular-dynamics layer.** The framing itself corrects the user off it: a flask is open and dissipative (~10²³ particles), so the honest macroscopic object is *free energy + stochastic dynamics*, not a least-action trajectory. SmartChem is a symbolic/structural compiler; the gradient flow is our *semantic justification* ("the search settles into a basin"), never an ODE we integrate.
- **No fabricated thermochemistry.** The ΔG functor is only as real as its **sourced** ΔH_f°/S° records; missing data ⇒ fail-closed UNKNOWN, exactly as every other functor here. The DOW-Br₂ win is contingent on *sourcing* Br/Br₂ records, not on inventing them.
- **No claim of the gradient-flow structure.** It is a Move-6 lead (a candidate lawful form for the withdrawn conditions⤳effects distributive law) carried **with** the detailed-balance caveat above, not asserted as ours.
- **No scalar collapse.** The product order is the point; a single "reactivity score" is the anti-goal (invariants 5 & 7; the Observability precedent).

---

## 5. What this changes (the plan delta)

- **Rung B (building now): scope unchanged, seam sharpened.** Still `OpenChemDiagram` alongside `Reaction` + the 3-part gate, additive/byte-stable/fail-closed. The **change**: the factored core carries a *general monoidal-decoration slot*; Rung B populates it with conservation + provenance only, but designs it so the ΔG / survival / observability functors slot in with no second refactor. Folded into `OPEN_SMC_CHEMISTRY_BACKBONE_CONTRACT` v0.2.
- **New Move-2 rung (queued, the user's to schedule): the functorial-physics product.** Recognize `feasibility.py`'s ΔG as the additive functor `G: Process → (ℝ,+,≤)` (Hess = functoriality, a property test), pair it with R23's survival functor in an explicit Pareto product, and verify/repair the DAG rollup's worst-node-vs-additive conflation. Advances DOW-Br₂ (thermo half) + paracetamol (step feasibility × accessibility). Data-gated only where a *new* species is needed.
- **Later: object-level enrichment (Pathology B at the object).** A `Config`/state that carries a thermodynamic coordinate (G as a state function; a phase) — today Config stores only `species` (`category.py:709`), and phase lives only on sourced records. A quotient-discipline item (Move 4-adjacent), not now.
- **Move-6 lead recorded:** gradient flow `ċ=−M∇G` as a candidate distributive-law form, with the detailed-balance caveat.

---

*This fold builds nothing and sources nothing. It records that the free-energy landscape frame is largely a verification of the categorical plan, with one sharp new rung (the functorial-physics product), one concrete Rung-B seam change (the general decoration slot), one cheap litmus win (DOW-Br₂ thermo), and accurate precedent (Baez–Pollard). The Lagrangian reading is refused on the framing's own grounds.*
