# On-load re-derivation of composability + physical — scope decision **v0.2** (ROADMAP queue item 2)

> Status: **DECIDED, build-ready (v0.2).** Supersedes [`ONLOAD_REDERIVATION_SCOPE_DECISION_v0.1.md`](ONLOAD_REDERIVATION_SCOPE_DECISION_v0.1.md).
> This revision folds the external ChatGPT design review (see [`ONLOAD_REDERIVATION_CHATGPT_PROMPT_v0.1.md`](ONLOAD_REDERIVATION_CHATGPT_PROMPT_v0.1.md))
> **against the actual dev-branch tree** (`cip-load-stability-2026-09-06 @ 510ed8b`, 5 commits past the `main@8a312a5` the reviewer read) rather than
> accepting it on faith. Every load-bearing claim was independently re-verified at its `file:line` anchor by an 8-agent recon+adversary pass
> (workflow `wf_c2a0e0f8-732`, 6 read-only recon bearings + 2 adversaries). **Two holes in v0.1 were found and closed; one factual error was corrected.**
> The invariant, serialization contract, gating policy, and test list below are the build spec.

## Answer map (the 5 questions the prompt asked)

| Q | Answer (short) | Where |
|---|---|---|
| **Q1** protection-equivalence hole | **TWO holes.** (1) coherence ≠ route binding → substitution attack (ChatGPT). (2) the `compare=False` payload is bypassable by **deletion** under the tree's fail-open idiom (adversary — ChatGPT missed this). Both close structurally, no key. | §1 |
| **Q2** sound-and-tight invariant | The real fitter fold `F` verbatim, checked by **exact equality** (not lower-bound) against a **pinned eval-context**, plus component + projection binding. | §2 |
| **Q3** serialization contract | Mirror the existing digest-stable graph round-trip `_graph_payload`/`_graph_from_payload`; reconstruct through the real constructors; harden the parser. | §3 |
| **Q4** adversarial tests | ChatGPT's table **+** the deletion test, the conservative-relabel boundary, the eval-context test, the positional round-trip, the edges int-coercion, verifier mutation tests. | §4 |
| **Q5** gated vs mandatory | **Consumer-selected policy, not payload-selected flag.** Verified-admission mode fail-**closes**; legacy inspection is a separate, non-verified path. This is the fix for hole #2. | §1.2, §5 |

---

## 1. The protection story, corrected (Q1)

### 1.1 Hole #1 — coherence is not route binding (ChatGPT; CONFIRMED on tree)

v0.1's check re-derives composability/physical from the **declared** thick payload and compares to the **declared** verdict. `route_digest` never enters the re-derivation — the *only* structural tie between `route_digest` and the search output is a set-membership check (`ranked route digest must identify a returned IR candidate`, `service.py:1276-1282`); it never checks that the declared fields *belong to that candidate*. So an attacker can:

```
route_digest   = R_bad          (a composability/physical-EXCLUDED route)
fit_status     = FITS
replay_payload = R_good's steps  (a genuinely-FITS OTHER route, real & conserving)
```

The coherence check passes — the payload really *does* re-derive `FITS` — and `R_bad` is admitted. No key, no fabrication (`evaluate_process_requirements(r.process_requirements, bounds)` is a pure function of the declared fields; `test_key_holding_forger_residual_...` is the weaker self-consistent-lie cousin of this).

**Fix — the binding invariant.** Reconstruct the complete route/DAG from the payload and require

```
reconstruct(payload).digest == summary.route_digest
```

This is **cheap and total** on our tree: `route_digest` is `ExperimentRoute.digest` / `SynthesisDAG.digest`, i.e. `canonical_digest(self)` (`contracts.py:248-249`) which recursively hashes **every** `compare=True`, non-underscore field. `ExperimentStep`'s fields are `target, reactants, products, reagents, envelope` (`step.py:85-90`), all public; `ConditionEnvelope`'s 10 fields (`conditions.py:109-118`) all public; **no `compare=False` field exists anywhere on the step-content surface** (the only ones are the transient `Reaction.name/generator_id/generator_word`, `category.py:822-825`, never stored on a step). Measured probes confirmed an envelope-only diff and a reagent-only diff each change `route_digest`. So binding to `route_digest` binds molecules (positional), reagents multiset, and the full 10-field envelope — **no new hash term, `route_digest` unchanged.**

For DAGs, also bind the two projections (both are one-liners against data the reconstruction already produces; both close residuals the codebase's own docstrings name as open — `service.py:1005-1006`, `:1076-1080`, `:1412-1413`):

```
EdgeProjection(reconstruct)    == summary.edges              # DAG only; edges is a pure fn of steps (dag.py:101-119,219-222)
ProcessProjection(reconstruct) == summary.process_requirements  # == tuple(step.envelope.process ...) (service.py:993/1188)
```

### 1.2 Hole #2 — the digest-excluded payload is bypassable by DELETION (adversary HIGH; ChatGPT Q5 pre-empts it, v0.1 build-step-4 gets it wrong)

v0.1 build step 4 says the check is *"gated on the thick payload being present (zero overhead otherwise)."* **That is the vulnerable design.** A `compare=False` payload is invisible to `route_digest`, to `result_digest` (`canonical_payload` skips `compare=False`, `contracts.py:150-154`; `result_digest` folds only dossier digests, `service.py:1654-1666`), **and to the HMAC** (signed over `result_digest`, `service.py:2797`). The tree defaults *every* absent digest-excluded field fail-**open** via `.get(default)` (`serial_holds` `:2560`, `provider_snapshots` `:2782`, `ranked_dag_dossiers` `:2785`) — and v0.1 *cites `serial_holds` as its precedent*, priming exactly this idiom. So:

1. bare-relabel an EXCLUDED route to `fit_status=FITS` (`fit_status` is `compare=True` → dossier digest → `result_digest` moves);
2. recompute `result_digest` **for free** (plain public SHA-256, `contracts.py:183-191` — no key);
3. **delete** the replay payload from the JSON.

A presence-gated check never fires → the route is admitted. The exact hole item 2 exists to close, reopened at zero cost.

**Fix (= ChatGPT Q5).** Verified admission is a **consumer policy that fail-CLOSES**, not a payload-selected flag. The admissible set is **computed from the re-derivation**; a `FITS` route with an absent-or-malformed payload is `UNVERIFIED`, never admitted. For a verified-admission consumer to reject a *stripped* response (rather than mistake it for a legitimately payload-less legacy one), the closure needs a **`schema_version` bump** so the policy can require *"new schema ⟹ payload present for any admitted route."* This is the direct analogue of the existing opt-in `require_signature` consumer flag.

> **Superseded optimism.** v0.1's DECISION section (lines 45–60) sold "byte-stable, no golden regen." That was half right: **`route_digest` (route identity) is byte-stable** — the payload lives on the *summary*, not the route object. But `result_digest`/summary digests for *populated* responses **do** change (schema bump + the new-field fold), so `response_schema.json` and any populated-dossier golden (`recompile_routes_found.json`) **are regenerated** — which v0.1 build-step-5 already budgeted. The regen is now **load-bearing**, not optional: it is what lets the fail-closed policy hold structurally without a key.

### 1.3 Correction — the HMAC conflation (recon bearing 2; the code's own test proves it)

v0.1 lines 55–57: *"edit both the payload and the claimed verdict → changes `result_digest` → the existing key-holding-forger residual, closed only by the opt-in producer signature."* This **conflates a free public-checksum recompute** (any unsigned editor; `result_digest` is a plain SHA, `contracts.py:183-191`) **with a MAC forge** (needs the key). The code's own `test_key_holding_forger_residual_is_not_closable_by_a_signature` (`tests/test_process_service.py:138-162`) + the `response_from_payload` residual docstring prove the **key-holding residual is IRREDUCIBLE** — a signature closes only a **keyless out-of-band** edit.

**Corrected statement (this must be the phrasing item 2's own docstrings use — do NOT echo v0.1's):**
- The **structural closure** (route-binding + fail-closed re-derivation, §1.1–1.2) makes an **unsigned** bare-relabel *or* substitution **detectable with no key**.
- The **producer signature** closes a **keyless out-of-band tamper** of digest-covered fields (a consumer that sets `require_signature`).
- A **key-holding forger** is **irreducible** by any of this — the standing boundary. Item 2 is structural closure that **complements, never replaces**, the authentication layer.

---

## 2. The invariant (Q2) — corrected and tightened

On load, for each ranked route/DAG dossier eligible for verified admission:

1. **Reconstruct** the complete `ExperimentRoute`/`SynthesisDAG` from the replay payload, through the real `ExperimentStep.__post_init__` (target ∈ products; reagents ⊆ reactants multiset; `Reaction(Config.of(*reactants), Config.of(*products))` conservation certificate — `step.py:107-119`). A non-conserving forged step is refused at construction.
2. **Bind** (§1.1): `reconstruct.digest == summary.route_digest`; DAG also `EdgeProjection == summary.edges`; both `ProcessProjection == summary.process_requirements`.
3. **Pin the eval-context** and re-derive the fold with it — do **not** substitute unconstrained defaults:
   - `box = ConstraintBox.of_bounds(request.bounds, request.constraints.process)` — reconstructable and digest-bound from the request (`service.py:2402-2406`, `:2462-2467`).
   - `stability = DEFAULT_STABILITY` — the service **never** injects an extended table (`service.py:1879`, `:1172`; `verify_composability(route, *, stability=DEFAULT_STABILITY)` `composability.py:388-390`).
   - **Landmine:** substituting an unconstrained `ProcessBounds` silently drops the whole-process/**workup**-extrema exclusion+gap branch (`drafter.py:247-261`, `process_constraints.py:87-91`) into silence — a real regression, not a nicety.
4. **Fold `F`** = the real fitter fold, verbatim (`drafter.py:347-356` linear, `:457-465` DAG — byte-identical):
   `exclusions → EXCLUDED; elif gaps → UNKNOWN; elif box.constrains_anything → FITS; else UNCONSTRAINED`.
   (`SINGLE_STEP`/`NO_TRANSITIONS` contribute neither exclusion nor gap — `composability.py:377-378`, `dag.py:707-708`; `UNCONSTRAINED` is a distinct outcome, *not* a rank below FITS — `drafter.py:198`.)
5. **Check EXACT EQUALITY** `claimed.fit_status == F(reconstruct)` — **not** a lower bound. Because the reconstruction re-derives **all** reasons (the whole route), equality is achievable and strictly tighter: it rejects lenient forgeries (EXCLUDED→FITS) **and** conservative forgeries (FITS→EXCLUDED with a fabricated reason — the adversary MED tightness break, which a lower-bound admits over an empty re-derived set). Equality is **sound** here precisely because step 3 pins the context. *(Lower-bound would only be needed for a future partial-replay mode; item 2 has none.)*
6. **Component check:** the displayed `composability_verdict` equals the freshly-derived one — reconcile the linear name `SINGLE_STEP` (`composability.py:342`) with the DAG name `NO_TRANSITIONS` (`dag.py:708`). Require every re-derived exclusion/gap to be represented in the claimed diagnostics; prefer **structured findings** over free-text string-subset comparison (the `'{:g}'` float-format false-reject residual — `drafter.py:259-285`).

7. **Ranking-verdict binding (FORK RESOLVED → include, §6).** The four displayed ranking verdicts (`selectivity/feasibility/equilibrium/kinetics`, `service.py:927-930`) live on the *summary*, **not** the route object, so step-2 `route_digest` binding does **not** cover them. Re-run the same four per-step providers against the **reconstructed** route under the pinned eval-context (§2.3) and **equality-check** each displayed verdict. Because the reconstruction is already `route_digest`-bound (authentic route content), the re-derived ranking verdicts are authentic; this closes the "fabricate ranking → float a bad route to #1 recommendation via `_route_score` (`drafter.py:494-501`)" gap on the unsigned path.

### Boundaries (explicit — named, not silently entrenched)
- **Eval-context binding** is valid for **service-produced** responses (context pinned + reconstructable). A future extended-`StabilityTable` or inventory-carrying (`available_reagents`/`available_equipment`, `drafter.py:288-309`) producer must **carry + reconstruct** the eval-context or the re-derivation is unsound for it (adversary HIGH #5 — conjectured, does **not** bite the service today).
- **Linear/DAG edge semantics:** `ExperimentRoute` requires an intermediate to be **net-consumed** (`step.py:157-162`, `:258-265`); the DAG edge builder records an edge on mere **presence** among a consumer's reactants (`dag.py:101-119`). `EdgeProjection` is self-consistent (both sides use `_edges`), but item 2 inherits the looser presence-only rule. Named here so the round does not silently entrench it.
- **`FITS` ≠ "hazards cleared / safe to execute".** The readiness `BLOCKED` axis (`drafter.py:87`) is a separate layer, untouched.

---

## 3. Serialization contract (Q3)

**Mirror the existing digest-stable graph round-trip** `_graph_payload`/`_graph_from_payload` (`compilation_ir.py:347-358` — *"reconstructs the EXACT family transform (digest-preserving), with no canonical-permutation remap"*, round-trip tested `test_ir_struct.py:136-140` `assert back.digest == ir.digest`). **Do NOT re-parse from SMILES or canonicalize** — `Molecule` digest is **positional** (`category.py:471-474`); a reorder breaks `route_digest` for an *honest* route (a false-REJECT / availability bug, adversary LOW). There is **no** existing Molecule/Bond/Envelope payload codec — this is the genuinely new work; the flat-record pattern to imitate for the *scalar* parts is `_process_requirements_to_payload`/`_from_payload` and `provider_snapshot_to_payload`/`_from_payload` (flatten → exact-field-set guard → reconstruct through the real constructor so `__post_init__` re-validates).

- **Molecule:** raw `atoms` tuple (order preserved), `bonds` as undirected `Bond(i,j,order)` (`i<j` self-normalized — `category.py:441-464`; the directional `[i,j,order]` list is parser-internal only, `smiles.py`), `charge`, `state` (**identity-bearing though non-conserved — must round-trip**). **Zero-atom species are legal** (charge carriers / quantum tokens, `category.py:533-576`) — no nonempty-graph shortcut.
- **ConditionEnvelope (10 fields):** reconstruct through the real `__post_init__` — K/atm unit lock, `_ALLOWED_STATUS` cap, declared/provenance/`source` consistency (`conditions.py:131-187`). Lossy-round-trip risks that would silently flip a verdict: interval bounds replaced by an average; unit substitution (K↔°C, atm); `null`→`0`; `medium` collapse; `EvidenceStatus` promotion; `SourceCitation` must keep **both** `locator` and `review` (`provenance.py:29-34`); `ProcessRequirements` must keep `equipment=None` (unknown) vs `()` (declares none) vs `workup_included` distinct, plus `min_elapsed_minutes`/`min_active_minutes` (`process_constraints.py:80-111`).
- **Steps:** ordered `reactants`/`products`/`reagents` tuples (**multiplicity + byproducts preserved** — no set/reorder), reagents a multiset subset of reactants, target among products.
- **Parser hardening (none exists today — bearing 5):** strict JSON for the payload — reject duplicate keys (`object_pairs_hook`), reject `NaN`/`Infinity`/`1e400` (`parse_constant`/`parse_float`); fix the **edges int-coercion trap** — `tuple((int(a), int(b)) for a, b in payload["edges"])` (`service.py:2552`) coerces `True`/`1.9`/`"1"` **before** the exact-int guard at `:1009` ever sees them; validate wire types first. Any **new `compare=False` field** needs its own finite guard (`math.isinf`) — `Interval.__post_init__` already rejects non-finite (`conditions.py:91-92`), but a raw float triple like `serial_holds` does not.
- **Round-trip acceptance:** for every producer fixture — `decode(encode(x)) == constructor-normalized x`; `reconstruct.digest == route_digest`; `ProcessProjection == thin process_requirements`; `re-derived F == original fit_status`.

---

## 4. Adversarial test list (Q4)

ChatGPT's full table (round-trip/identity preservation; every 3-axis status combo × bench-constrained flag; component-mismatch rejects; conservation/target/reagent-multiplicity rejects; zero-atom carrier controls; duplicate-key/nonfinite/overflow rejects; resource-exhaustion bounds; cache-revalidation) **plus** the on-tree-earned tests:

- **DELETION (hole #2):** relabel EXCLUDED→FITS, recompute the public digest, **strip the payload** → a verified-admission consumer **rejects/UNVERIFIED**, never admits. (The one the presence-gate design fails.)
- **Substitution (hole #1):** another route's genuinely-FITS payload under a bad `route_digest` → **`reconstruct.digest != route_digest`** rejects, even though coherence passes.
- **Conservative relabel:** honest FITS→EXCLUDED with a fabricated exclusion string → **exact-equality** rejects (documents the boundary a lower-bound would miss).
- **Eval-context:** an extended-`StabilityTable` producer's honest FITS re-derived under `DEFAULT_STABILITY` → the pinned-context assertion must not false-reject a *service* response and must be explicit for non-service callers.
- **Positional round-trip:** reorder a molecule's atoms → honest `route_digest` must still match (order-preserving codec), i.e. **no false-reject**.
- **Edges int-coercion:** `[true, 1.9]` / `["1","2"]` edges → rejected before coercion.
- **Verifier mutation tests:** disable each of {bind, edge-projection, process-projection, equality, component-check, mandatory-presence} one at a time → the corresponding negative control must start failing.

---

## 5. Gating policy (Q5)

**Consumer-selected, not payload-selected.**
- **Legacy inspection:** an absent payload may parse; the historical verdict is **producer-declared, not replay-verified**; admission is **not** claimed.
- **Verified admission** (new consumer flag, parallel to `require_signature`): requires `schema_version ≥ item-2` **and** payload present **and** (bind + pinned re-derive + exact equality + component/projection checks) pass — else the route is `UNVERIFIED`/not-admitted; a *malformed-present* payload is always an error. *"Zero overhead when absent"* means **no reconstruction cost in legacy mode**, never a truthiness bypass in verified mode. Distinguish absent / present-null / present-empty / partial explicitly (a genuine no-synthesis outcome uses its existing separate response outcome, not an empty payload).

---

## 6. Build plan (the L round) + the one decision fork

**Build:** (1) Molecule/Bond serializers mirroring `_graph_payload`; (2) full 10-field `ConditionEnvelope` + `ProcessRequirements`/`SourceCitation` serializers (flat pattern); (3) per-step thick payload, `compare=False`, on both summaries; (4) conservation-certified route/DAG reconstruction; (5) the **bind** checks (`reconstruct.digest`, edge/process projection) + the **pinned re-derive + exact-equality** fold, for linear **and** DAG; (6) the `require_verified_admission` consumer flag + a **computed** verified-admissible property that excludes payload-less FITS routes; (7) `schema_version` bump + descriptor bump + golden regen (`response_schema.json` + populated-dossier goldens); (8) strict-parser hardening + the edges int-coercion fix; (9) the §4 test list + an evil-morty pass targeting the deletion door specifically.

**DECISION FORK — ranking-verdict authentication → RESOLVED: (A) INCLUDE** (user decision, 2026-09-06). Item 2 re-derives + equality-checks the displayed `selectivity/feasibility/equilibrium/kinetics` against the reconstructed route (§2 step 7), closing the adversary's MED "fabricate ranking → float a bad route to #1 recommendation" gap. This is step (5b) in the build above and widens the golden/test surface modestly (the four verdicts are re-derived by the same per-step providers already invoked, so it is near-free given the reconstruction).

Nothing here authorizes a merge of the held branch.
