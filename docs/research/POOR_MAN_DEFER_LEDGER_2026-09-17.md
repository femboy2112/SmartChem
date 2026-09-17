# POOR_MAN_DEFER_LEDGER_2026-09-17

**Status:** record of four VERIFIED-DEFER decisions + two engineering lessons, taken together after ROUND 61
(N-methylation recognizer, PR #73) and ROUND 62 (tamper-hardening, PR #74). Nothing here changes code or
tests — it is the memory of *why* four open items on the queue stay open, so the next reader does not re-open
them without re-deriving the same answer.

Each entry below is checked at `origin/main @ afbf39f` (the tip this ledger was written against).

---

## #5 — Problem-B feasibility as a real-but-hard disposition source

**Verdict: VERIFIED-DEFER.**

**The decision.** `smartchem/experiment/feasibility.py`'s ΔG model (M1) stays out of `hard_blockers` /
`Disposition`. It is not wired as a `REAL_BUT_HARD` source, and it should not be until a new
capability-measuring model is built.

**The evidence.**
- `smartchem/experiment/feasibility.py:11-16` — the module's own docstring states the model computes a
  sourced, Hess's-law ΔG (`ΔH_rxn` by Hess's law, `ΔG = ΔH - TΔS`) where standard thermodynamic data covers
  every species, and fails loudly to `UNKNOWN` where it doesn't. This is a genuine *measurement* — it is
  **not** the R49–R55 bounded-radius trap (it doesn't hand-enumerate a hazard/safety space; it derives a
  physical quantity from sourced constants).
- `smartchem/experiment/feasibility.py:19-22` — but the same docstring disclaims the capability reading
  directly: `UNFAVORABLE` is described as "a sourced *disfavour*, NOT a claim of impossibility... We say
  'disfavored', never 'cannot happen'." A high ΔG measures thermodynamic *drive*, not the poor-man capability
  property `REAL_BUT_HARD` needs (can a kitchen bench actually run this).
- `smartchem/experiment/drafter.py:413` and `:708-717` — the DAG-THERMO-01 rollup is architecturally declared
  RANKING-ONLY: `_dag_score` orders otherwise-tied candidates on the feasibility verdict but it "NEVER"
  changes `fit.status`, exactly mirroring the linear `fit_route`. `smartchem/experiment/dag.py:1030-1058`
  (`dag_thermo_rollup`) carries the identical discipline on the DAG side, reusing the same per-step providers
  and never producing an invented verdict.
- `grep -n "feasibility" smartchem/experiment/affordability.py` returns **zero** hits — the module that owns
  `hard_blockers` / `Disposition` / `dominates` does not import `feasibility.py` at all today.

**Why deferred, not just "no".** Wiring `feasibility.py`'s ΔG into `hard_blockers` would reverse a standing
architectural decision (ranking-only, never a gate) without a new model that maps *thermodynamic drive* onto
*bench capability* — those are different properties that happen to correlate in easy cases and diverge in
hard ones (an endergonic step can still be driven by coupling, concentration, or Le Chatelier removal of a
product; the docstring says so explicitly). Doing this properly needs the equilibrium/coupling model (M2) the
feasibility module itself names as future roadmap, not a shortcut through the existing ΔG sign.

**Corpse, labeled.** No code was tried and withdrawn here — this is a defer against a *temptation*, not a
retracted build. The temptation is real: `POOR_MAN_DISPOSITION_CHANNEL_v0.1.md:70` and `ROADMAP.md:842` both
name "feasibility wiring (Problem B)" as the most obvious way to make `REAL_BUT_HARD` reachable without a
metal-catalyzed source. It stays unbuilt because the soundness question (does a sourced ΔG-unfavorable verdict
actually mean "hard to run on a kitchen bench") is open, not because it's hard to code.

**Links.** Supersedes nothing; constrained by [[a-capability-reward-must-be-gated-on-the-capability-model]]
(R49's lesson: a proxy that doesn't encode the capability property confidently rewards things that lack it —
here the risk runs the other way, an honest measurement wrongly read as the capability verdict). Feeds the
new lesson below (*A sound measurement is not automatically a sound capability-verdict source*). See also the
naming-collision fix in §B — the ledger below is also where "Problem B" gets disambiguated.

---

## #6 — aromatic-heteroatom kekulizer

**Verdict: VERIFIED-DEFER (the framing itself is stale).**

**The evidence.** The originally-named gap — "aromatic purine doesn't kekulize" — was already closed by
ROUND 46. Verified live:

```
>>> parse_smiles('Cn1cnc2c1c(=O)n(C)c(=O)n2C')   # caffeine, RDKit's default aromatic spelling
caffeine parsed OK, 24 atoms
```

`smartchem/smiles.py::_aromatic_matchings` (function at `smartchem/smiles.py:396`, the acceptor/donor
classification described at `smiles.py:396-410`) already handles C/N/O/S: a neutral carbon bearing an
exocyclic multiple bond is a π-donor (ROUND 46), an aromatic N is classed pyridine-type-acceptor or
pyrrole-type-donor by substitution/valence (ROUND 41-era), and O/S are always donors.

**Why still deferred.** What remains under the old "aromatic-heteroatom kekulizer" heading is not one brick,
it's several unrelated ones, confirmed at `smiles.py:504-508`: any element outside `{C, N, O, S}` in an
aromatic ring raises `SmilesError("aromatic heteroatom ... is a v1 gap")` — that's every non-{C,N,O,S}
aromatic-ring element (P, Se, As, …) as its own future brick, each needing its own soundness proof (electron
count, donor/acceptor role differ per element). Beyond that, charged committed-π aromatic systems past what
ROUND 41 already covers are a second, separate brick. Phosphorus-in-ring aromaticity in particular is
chemically murky (weakly aromatic at best) — building a generic "aromatic-heteroatom kekulizer" now would be
guessing at a soundness proof for a case nobody has asked for.

**Corpse, labeled.** None — no code was built and withdrawn. The corpse here is the *framing*: the gap as
originally named (purine/xanthine aromaticity) is dead — solved — and calling the residual "the same gap" was
the error being corrected in this ledger entry.

**Why deferred, not built.** No north-star molecule (paracetamol, DOW bromine, caffeine) forces any of the
remaining element cases. Building a generic mechanism ahead of a forcing consumer is exactly the YAGNI trap
[[an-oracle-driven-existence-check-can-prove-a-defer]] warns against.

---

## #7 — monocyclic ring-strain correction tier

**Verdict: VERIFIED-DEFER — strong: currently unreachable by construction, not merely low-priority.**

**The evidence — the R47 guard exists and is honest.** `smartchem/experiment/bond_enthalpy.py`'s
`reaction_delta_h_kj` fails closed to `None` (→ `BORDERLINE`) whenever the *endocyclic*-bond-type multiset
changes between reactants and products (guard documented at `bond_enthalpy.py:34`, implemented via
`_endocyclic_bond_types` at `bond_enthalpy.py:133`, applied inside `reaction_delta_h_kj` at
`bond_enthalpy.py:163-188`). This guard exists precisely because bond additivity inverts sign on ring-strain
release and aromatization (cyclopropane→propene: est +80 kJ vs true −33 kJ; 1,3-CHD→benzene: est +125 kJ vs
true −22 kJ — ROUND 47's own adversarial finding).

**The evidence — that guard is dead code for the live search.** A single-bond ring-bond cut never
*disconnects* the reactant graph (a ring, by definition, has an alternate path around any one of its bonds),
and `structure_descent.py` only ever emits a decomposition when a cut disconnects the graph: "a cut that does
*not* disconnect ... is no decomposition at all and is never emitted" (`structure_descent.py:37-38`,
enforced in `try_cut` at `structure_descent.py:472-480`, which only registers an edge when
`len(comps) >= 2`). So a ring-opening or ring-strain-relieving move is unreachable unless multiple bonds are
cut in the same step (`max_reactant_cuts >= 2`) with ring-aware enumeration on. Both are off by default:
`CappedScissionProvider.max_reactant_cuts: int = 1` and `.ring_aware: bool = False`
(`transform_provider.py:110-111`), and `DEFAULT_TRANSFORM_REGISTRY` (`transform_provider.py:274`) is built
from that same default `CappedScissionProvider()`. Neither public compiler entry point exposes a way to
override it — `compile_synthesis` (`smartchem/experiment/compile.py:306-324`) and `run_compilation`
(`smartchem/service.py:2220-2221`) take no `registry` or `ring_aware` kwarg.

**Empirical corroboration.** The codebase's own census pattern (`docs/research/
CATALYST_OBTAINABILITY_SCOPE_v0.1.md:43`, `docs/research/POOR_MAN_OUT_OF_CENTER_RECOGNIZER_SCOPE_DECISION_v0.1.md:35`)
establishes 45 registered structures compiling to 59 steps across the registry under the default (bounded,
`max_reactant_cuts=1`) search — the same 45/59 figures this defer relies on for "0 `reaction_delta_h_kj`
None-returns from a ring-topology change in production." **Labeled Conjectured, not independently re-run this
round**: I did not re-execute a fresh sweep counting `None`-returns specifically for the endocyclic guard; the
45-structures/59-steps census is corroborated by precedent in two other committed docs, but the "0
None-returns" figure itself is carried forward from the requesting brief, not freshly re-derived by this
doc-only pass.

**Why deferred, not built.** The precondition — exposing ring-opening/multi-bond-cut search as a *default*
capability — is a combinatorially-costly, separate architectural decision (enumeration cost, new soundness
questions about which multi-bond cuts to trust) that is prior to and orthogonal to the strain-math itself. The
strain correction has nowhere to attach until that precondition is decided; building the correction first
would be dead code stacked on dead code.

**Links.** Constrained by [[a-derived-estimate-must-guard-its-domain-of-validity]] (the R47 lesson this guard
already embodies). This entry does not revisit ROUND 47's decision — it confirms the guard is *sound and
currently inert*, which is a different, stronger claim than "not yet built."

---

## #8 — CIP rules 4b/4c/6 · Move 5(b) · item-5 phase residuals

**Verdict: VERIFIED-DEFER, all four discharged, docs current at `afbf39f`.**

- **CIP 4b/4c/6.** A structure theorem, not a missing feature: the auxiliary CIP pass draws only from
  already-resolved centres, so the target it would need to force a decision on is empty by construction. See
  `docs/research/CIP_TARGET_RELATIVE_RULES_SCOPE_v0.1.md` and
  `docs/research/CIP_RULE6_CONSUMER_SCOPE_DECISION_v0.1.md` (both present in the tree). No chiral consumer
  exists today — paracetamol and aspirin, the two north-star molecules, are stereocenter-free.
- **Move 5(b).** No new cross-domain ranker has landed since the scope decision —
  `docs/research/MOVE5_DOMAIN_NEUTRAL_PARAMETERIZATION_SCOPE_DECISION_v0.2.md` is the current record (v0.1
  superseded by v0.2, both present in the tree).
- **item-5 phase residuals.** `fit_status` phase-invariance is a soundness property to *preserve*, not carried
  debt — `docs/research/ITEM5_PHASE_AWARE_RANKING_SCOPE_v0.1.md` (linear side) and
  `ITEM5_DAG_PHASE_AWARE_RANKING_SCOPE_v0.1.md` (DAG side, ROUND 44's `phases`-threading discharge) both
  confirm this reading.

**A flagged-not-actioned nag, recorded so it isn't lost.** Three separate intra-chemistry Pareto-frontier
implementations exist today, confirmed live in the tree:
- `smartchem/experiment/drafter.py:490` — `_pareto_front_indices`
- `smartchem/experiment/affordability.py:215,293` — `dominates` / `pareto_frontier`
- `smartchem/experiment/meta_compile.py:85` — `pareto_frontier`

This is a candidate for a future R42-style intra-chemistry consolidation (R42 consolidated the ranker
similarly) — but it is **distinct from Move 5(b)'s question**, which is about a shared ranker *across* domains
(chemistry/circuits/EM), not three within-chemistry Pareto implementations. Not actioned this round; flagged
so a future consolidation pass doesn't have to rediscover it from scratch.

---

## Two engineering lessons this round earned

### A sound MEASUREMENT is not automatically a sound CAPABILITY-VERDICT SOURCE

A sibling of [[a-capability-reward-must-be-gated-on-the-capability-model]] (R49), narrower and sharper: R49's
lesson was about a *proxy* that doesn't encode a capability property confidently rewarding things that lack
it. This round's #5 defer is the honest-measurement version of the same trap: `feasibility.py`'s ΔG is not a
weak proxy standing in for a capability it can't see — it is a *correct, sourced measurement of a different
thing* (thermodynamic drive) that happens to sit next to the capability question (can a kitchen bench run
this) closely enough to tempt a direct wire-in. The mapping from "measured quantity" to "capability verdict"
needs its own justification every time, even when — especially when — the measurement itself is unimpeachable.
Here the module's own author disclaimed the reading in the docstring (`feasibility.py:19-22`); the discipline
is to treat that disclaimer as load-bearing, not defensive throat-clearing.

### A verifier that cannot verify its input must FAIL CLOSED, never fail open

[[a-declared-unrecognized-input-must-block]] was stated for *recognizers* (R51: an unrecognized catalyst
should block). ROUND 61 and ROUND 62's gate findings show the same discipline applies to *verifiers* — code
whose job is to check a *claim*, not classify a substrate:

- ROUND 61 (`b6960b6`): the N-methylation recognizer, run on a step with `reaction_center=None`, VOUCHED it as
  a genuine N-methylation by whole-molecule census alone — the census couldn't see that the methyl group
  migrated rather than transferred, so it read a spurious 0→1 rise. "Can't verify the mechanism → trust the
  census" was the fail-open hole; the fix makes an absent centre an automatic `False` (false-UNRECOGNIZED,
  safe), never a census-only VOUCH (false-VOUCH, catastrophic).
- ROUND 62 (`7087db7`/`4866d6a`): the frontier-coherence load-time check, absent a digest-bound replay, had no
  evidence to re-derive blockers from — and the original gate finding was that this was silently treated as
  "nothing to check" rather than "cannot verify, so don't claim closure." The fix (KILL-1) binds the
  reconstructed replay route to the entry's own digest before trusting it, and the tamper-hardening doc is
  explicit that the *default* (thin, no-replay) transport is an honestly-scoped, tracked-open boundary
  (`POOR_MAN_TAMPER_HARDENING_v0.1.md`, the "default-transport boundary" section) rather than a silently
  claimed closure.

The common shape: "I cannot verify X" was being read as "assume X is fine" instead of "refuse to certify X."
A verifier's silence on evidence it doesn't have must degrade the verdict, never default it to pass.

---

## Confidence

- **Verified** (re-derived from source this round): #5's docstring/architecture claims (feasibility.py:11-22,
  drafter.py:413/708-717, dag.py:1030-1058, zero affordability.py import); #6's caffeine re-parse and
  smiles.py:396-410/504-508 element handling; #7's guard code, `structure_descent.py`/`transform_provider.py`
  wiring, and both public entry-point signatures; #8's four scope docs present and stating what's claimed; the
  Pareto-triple existing at the cited lines; the Problem-B naming collision at the two cited sites.
- **Conjectured** (plausible, corroborated by precedent but not freshly re-run this round): #7's specific "59
  calls / 45 targets / 0 None-returns" empirical figure — corroborated by the same 45-structure/59-step census
  appearing in two other committed docs, but I did not re-execute a fresh sweep against `reaction_delta_h_kj`
  specifically to recount `None`-returns this round.
- **UNVERIFIED / not attempted**: whether a future equilibrium/coupling model (M2, named in feasibility.py's
  own roadmap) would resolve #5's mapping question — that model doesn't exist yet, so this is speculative
  forward-reference only, not a claim about today's code.

## Links

Constrains/extends: [[a-capability-reward-must-be-gated-on-the-capability-model]],
[[a-declared-unrecognized-input-must-block]], [[a-derived-estimate-must-guard-its-domain-of-validity]],
[[an-oracle-driven-existence-check-can-prove-a-defer]]. Cross-referenced by `ROADMAP.md`'s defer/next-blast
section (§C of the commit that adds this doc).
