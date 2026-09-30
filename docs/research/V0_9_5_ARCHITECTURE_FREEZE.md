# SmartChem 0.9.5 — Architecture Freeze (the parent barrier)

**Status:** FROZEN 2026-09-29 on `feat/v0.9.5-adversarial-rc` @ `8601734` (0.9 merged as `d26f0eb`; baseline behaviour
frozen in [`V0_9_5_BASELINE_BEHAVIOR_FREEZE.md`](V0_9_5_BASELINE_BEHAVIOR_FREEZE.md)). No Wave-B writer starts before
this document. Anything not listed in §1 as an allowed semantic change is a **refactor** and must pass
`experiments/v0_9_5_baseline_freeze.py --check` with NO DRIFT.

**Inputs (Wave A, eight read-only lanes):** A architecture census · B verifier performance · C StreamDisposition
theorem · D identity/resonance · E transport/trust · F release engineering · G independent structure theorem · H
evidence semantics (Parts 10–13). Their full reports lived in the session scratchpad; every load-bearing fact they
established is restated below with its evidence so this document stands alone. Parent-verified items are marked
**[parent-verified]**.

---

## 0. The five jobs, restated as gates

1. Shrink accidental complexity without semantic movement — §9 consolidation, judged by the baseline freeze.
2. Bound all verification work — §5 budget + §4 caches, never by skipping a check.
3. Close the smallest genuinely necessary representation gaps — §1 S-list only.
4. Attack the complete product — Wave C + the RC funnel/fuzz/stress gates (§12).
5. Freeze public semantics for 1.0 — `COMPATIBILITY.md` + `docs/ARCHITECTURE.md` + the final re-freeze.

---

## 1. The EXHAUSTIVE list of allowed semantic changes

Each item names what moves. Anything else that moves is a regression.

| id | change | accepted set | verdicts | digests / wire |
|---|---|---|---|---|
| **S1** | `require_canonical_transport` policy (opt-in): THIN_ADVISORY **and** legacy v0.8 payloads refused at dispatch, before key checks or decode | narrows only when opted in | none | none |
| **S2** | Verification work budget (default ON, conservative; §5): a payload whose deterministic work exceeds the budget is refused with `VerificationBudgetExceeded` | narrows (only payloads above the budget; every frozen honest payload is far below) | none | none |
| **S3** | **F1** result-count law: `len(IR candidates of the search kind) <= receipt.result_limit` and `len(dossiers) <= receipt.result_limit` (`result_limit` is already bound to the request's `max_results` by D27.6), checked before any replay reconstruction | narrows (forgeries only). Premise MEASURED [parent-verified]: every one of the 23 frozen honest cases satisfies it (max 27/100 routes, 16/100 DAG dossiers; `isopentyl_dag` saturates at exactly 100/100 IR candidates with 0 dossiers — the documented unconstrained-DAG case) | none | none |
| **S4** | **F3** one-chemistry-one-dossier: two dossiers whose per-step STRUCTURE shapes (`resonance_identity` multisets of reactants and products, in step order) coincide are refused as a respelled duplicate | narrows (forgeries only). Premise MEASURED [parent-verified]: 0 chemistry-key collisions across all dossiers of the 23 frozen honest cases (incl. isopentyl 27 routes, 16 + 4 DAGs) | none | none |
| **S5** | **F4** DAG HEIGHT (the longest target→leaf chain of steps) `<= max_depth` on the D26.1 leg. NOT the step count: honest convergent DAGs carry MORE steps than `max_depth` [parent-verified: 5 steps under max_depth 3 (isopentyl_dag_quick), 3 under max_depth 2 (methyl_acetate_dag)] — the implementation must measure honest heights on the frozen DAGs before landing | narrows (forgeries only) | none | none |
| **S6** | **F9** TARGET_FILE responses refused at load dispatch — the loader never performs I/O on a payload-supplied path [parent-verified: an IR-less TARGET_FILE answer under `require_reexecution=True` opened the payload path `/tmp/.../target.txt`] | narrows (IR-less TARGET_FILE answers; IR-bearing ones are already refused) | none | none |
| **S7** | Stock/requirement STRUCTURE key := `"struct:" + resonance_identity(m)` from ONE authority (`stock.structure_key`); every consumer (requirements, waste, `name_resolves_to`, assess prefix test, StreamDisposition subjects) imports it | widens matching only for alternate Kekulé spellings of the SAME resonance structure (C7-2, a **false-BLOCKED**, not false-UNKNOWN — Lane D) | false-BLOCKED → correct for Kekulé-split pairs only | `MATERIAL_COMPONENT_SCHEMA` v1alpha2 → **v1alpha3** (the `identity_key` meaning coarsened); 0/69 parse-origin keys move |
| **S8** | ONE name normaliser (strip + casefold + collapse internal whitespace) owned by `stock.py`, used by stock, requirements and waste | widens only for whitespace-variant spellings of the same name | false-BLOCKED → match for those only | none beyond S7 |
| **S9** | **B-narrow** (Part 10b): stock-side component `states` and `phase_evidence` refuse SOURCE_QUOTED / DERIVED / CLAMPED (a stock claim is the operator's declaration: USER_DECLARED, ASSUMED or UNKNOWN). Stock `IntervalEvidence` keeps its sourced kinds (structural locators; the CLAMPED pure-witness law depends on them) | narrows (0 existing uses: 225 component states + 576 phase claims observed, all USER_DECLARED/ASSUMED/UNKNOWN) | none | `STOCK_MATERIAL_SCHEMA` v1alpha3 → **v1alpha4** |
| **S10** | **StreamDisposition** (§6) — the ONE permitted vocabulary closure — plus the two latent waste defects it would otherwise make unsound (D-C1 same-name spent-stream collapse; D-C2 route-wide residual/catalyst dedup) and D-C4 envelope-catalyst attribution | widens the evidence vocabulary; with no dispositions `derive_waste` is byte-identical except on routes repeating a species across steps (a strict SUPERSET of obligations there — safe direction) | FIT becomes REPRESENTABLE (synthetic witness); zero production FIT expected | response v1alpha17 → **v1alpha18**, descriptor v1alpha20 → **v1alpha21**, route summary v1alpha5 → **v1alpha6**, DAG summary v1alpha5 → **v1alpha6** |
| **S11** | Transport-ledger truthfulness (**F2**): `outcome`, `exit_code`, `search_space_status`, `standard_status` are RE only against single-field forgery; against a CONSISTENT rewrite of the advisory IR search status they are advisory (`advisory_when` states it); the ledger sweep gains a multi-field forgery per advisory source and the DAG legs of D29.1 / D27.1 (C7-3) | none | none | none (ledger text) |
| **S12** | `_compiler_implementation_digest` hashes the package's own `.py` files + `__version__`, never an ambient sibling `pyproject.toml` (source and installed trees then agree for byte-identical code) | — | none | the implementation digest value moves once |
| **S13** | `python -m smartchem.cli` gains a `__main__` guard (today it silently exits 0 doing nothing) | — | — | — |
| **S14** | Pre-release wire generations: the 0.9.0a1 ids (request v1alpha7 stays CURRENT; response v1alpha17, route/DAG summary v1alpha5, descriptor v1alpha20, stock v1alpha3, material component v1alpha2) are **not** migrated. They are SemVer pre-release alphas; only the frozen v0.8 generation keeps its legacy read leg. They are refused as `unsupported schema version` with a recompile hint | narrows (0.9.0a1 payloads) | none | — |

**Not changed (explicitly):** the request schema id stays `compilation-request-v1alpha7` — it folds into every
`semantic_digest`, and no request-shape change is needed (capability-side changes live in nested profile/stock ids that
reach only `capability_question_digest`). Search identity, noninterference and the search receipt are untouched.

---

## 2. VerificationPolicy (frozen shape) — `smartchem/verification.py`

```python
@dataclass(frozen=True)
class VerificationPolicy:
    verification_key: bytes | None = field(default=None, repr=False)
    require_signature: bool = False
    require_verified_admission: bool = False
    expected_request_digest: str | None = None
    expected_capability_question_digest: str | None | Unpinned = UNPINNED   # None == pinned to NOT_REQUESTED
    require_reexecution: bool = False
    require_canonical_transport: bool = False     # S1
    budget: VerificationBudget = VerificationBudget.default()   # S2
```

* Defaults reproduce today's `response_from_payload` kwargs EXACTLY, plus S1 off and S2 at the conservative default.
* Construction refuses contradictions: `require_signature` without a key (today's exact message); a key shorter than
  `_PRODUCER_KEY_MIN_BYTES` (16) or not `bytes` (deliberate tightening — a 1-byte HMAC key is a footgun); a pin that
  is not 64 lowercase hex (it could never match); a non-bool flag.
* Named constructors are `dataclasses.replace` sugar over the ONE policy — `advisory()`, `canonical()`
  (= require_canonical_transport + require_verified_admission), `pinned(request, *, question=...)`,
  `authenticated(key)` (key + `require_signature=True`), `paranoid(request, key)` (canonical + pinned + authenticated
  + reexecution). A test asserts each equals the explicit field-for-field policy.
* ONE compat shim: `response_from_payload(payload, **legacy_kwargs)` and `deserialize_response` build a policy via
  `VerificationPolicy.from_legacy_kwargs(...)` and call `load_response(...).response`. Passing `policy=` together
  with a legacy kwarg is a `TypeError`. Behaviour of every existing call is unchanged except S2/S3–S6/S14.

## 3. VerifiedLoad / VerificationReceipt — out of band, loader-constructed only

`load_response(payload, policy=VerificationPolicy()) -> VerifiedLoad(response, receipt)`;
`load_response_text(text, policy)`. `CompilationResponse` gains NO field (its digests and every golden are untouched).

Receipt facets (no single "strength" scalar): `schema_generation` (CURRENT | LEGACY_V08), `transport_mode`,
`digest_rule` (WHOLE_BODY | FROZEN_V08), `request_pin` (CHECKED | NOT_PINNED), `capability_pin` (CHECKED |
NOT_PINNED), `signature` (VERIFIED | NOT_REQUIRED_ABSENT | NOT_CHECKED), `verified_admission` (bool),
`replay_rederived_routes` / `replay_rederived_dags` (counts of dossiers whose replay was actually re-derived — a
zero-dossier canonical payload is canonical in name only, Lane E), `reexecuted` (bool), `legacy_migrated` (bool),
`search_output` (ADVISORY unless `reexecuted` or signature VERIFIED — the D25.3 boundary, S11), `work` (the budget
meter's final counters), `policy` (the policy it was produced under). `receipt.satisfies(policy) -> bool`.

**Unforgeability:** the receipt takes a module-private token as an `InitVar` checked in `__post_init__`;
`__reduce__` raises; `__copy__`/`__deepcopy__` return self; there is no `from_payload`; `dataclasses.replace` fails
because the token is not a field (Lane E verified the naive token-as-field design is forgeable via `replace`). The
wire cannot carry a receipt (D28.5 exact keys). Boundary: in-process code that reaches the private token (or
`object.__new__`) can forge one — no weaker than today, where in-process code can build a `CompilationResponse`
directly.

## 4. VerificationContext + caches (ownership and the cache-key theorem)

**VerificationContext** — created ONCE by `load_response`, installed for the duration of that load via a
`contextvars` context manager, discarded after. Owns: the budget meter; a per-load memo of `_reconstruct_route` /
`_reconstruct_dag` keyed by the replay-payload OBJECT (the context holds a strong reference, so `id` reuse is
impossible; no check mutates a payload — Lane A); the per-load D29.1 `emitted` table (already per-load today).
Outside a load (producer paths, direct test calls of a `_check_*`) there is no context and every function computes
directly — no signature of any `_check_*` changes (mutant stubs such as M180 `lambda self: None` stay valid).
Measured: reconstructions per thick isopentyl load 136 → 27 (Lane B: 5× per route; 6–7× with a profile).

**Process-level enumeration cache (bounded).** Wraps ONLY `registry.enumerate(target, reagents, budget=...)` and
caches its RAW output (a tuple of frozen `EnumeratedTransform`s + the completeness flag). The shape/centre reduction
stays textually inside `_check_replay_step_transforms` so the source-level mutants M212 (`_ident` import) and M213
(`reaction_center` test) still act on live code (caching the reduced table would mask them — Lane B).

*Cache-key theorem.* `enumerate` is a pure function of exactly: the registry VALUE (its providers' content-bound
semantic descriptors + knobs such as `max_reactant_cuts`, `ring_aware` — captured by the registry's own digest), the
target Molecule VALUE (atoms, bonds, charge, state — the literal spelling, because emitted transforms embed literal
atom order and index-based reaction centres), the reagent tuple VALUE, and `budget`. Key =
`(registry.digest, target_molecule_value, reagent_tuple_value, budget)`. Lane B attacked each coordinate: algebra
profile, `max_reactant_cuts`, `ring_aware`, target structure, target charge, target state, reagent pool and budget each
CHANGE the output (necessary); reagent order, duplicate reagents, target atom permutation and `PYTHONHASHSEED`
0 vs 1234 did NOT (no hidden input); no env var or RDKit reaches the path (grep). No bad hit found (18/18). Because
the key is the full VALUE of every argument plus the registry's content digest, a provider rule/guard change moves
`registry.digest` and misses structurally.

*Bounds.* Weighted LRU: ≤ 65,536 retained transforms total (~35 MB at ~0.53 KB/transform), ≤ 512 entries, an entry of
more than 8,192 transforms is not retained; thread-safe (lock). `clear()` hook: in-process patching (the mutation
harness `_patch`, tests that monkeypatch providers) is invisible to any key, so the harness and a `conftest` autouse
fixture call `clear()`. Cache on/off must give byte-identical accepted results (a stress-gate invariant and a
mutant: M-C1 omitted coordinate, M-C2 stale-after-provider-change).

**Not cached:** `Molecule.canonical()` (the real cold cost — 2,349 misses = 172 s of the hostile profile — but it IS
the identity function; an identity-preserving speedup is post-1.0). A per-Molecule-value `resonance_identity` LRU is
permitted (−35 % warm on isopentyl) under the same bounded/cleared discipline, keyed on the full frozen Molecule value.

## 5. The verification-budget law

`VerificationBudget` = deterministic work counters, never clocks. Exhaustion raises `VerificationBudgetExceeded`
(a `ValueError` subclass that is NOT a `DAGError`/`CeilingError` — `service.py:3471` swallows those) with the counter
name, limit and consumed value and the hint "raise the budget explicitly if you trust this payload's size". It is
charged **before** the work it bounds and re-raised ahead of every broad `except Exception` on the path (D29.1 wraps
`enumerate` in one). **Exhaustion never skips, clamps or degrades a check** — clamping `cut_budget` would change the
enumerated set; a failed budget means verification did not complete. Charge points: payload node walk at load entry
(before decode); each reconstruction; each D29.1 enumeration MISS (its predicted work `W = E × |bonds(target)|`,
`E = |bonds(target)| × Σ|bonds(distinct reagent)|`, exact for capped scission — measured work = 3E on 40/40 target
classes, so it is computable before enumerating); the re-execution (count + W of the request target). Never inside the
reaction-type oracle (`readiness.py:178` swallows exceptions and demotes).

| counter | honest max (frozen corpus + Lane B payloads) | DEFAULT | hostile C7-1 |
|---|---|---|---|
| payload JSON nodes | measured at implementation | ≥ 8 × honest max | — |
| dossiers (routes + DAGs) | 100 | 256 | 1 |
| replay steps (total) | 542 | 4,096 | 1 |
| steps per dossier | 7 | 32 | 1 |
| distinct enumeration targets | 29 | 128 | 1 |
| W per target | 4,356 | 32,768 | **473,200 → refused** |
| Σ W | 41,328 | 131,072 | 473,200 |
| re-executions | 1 | 1 | — |

One default for every caller (conservative); a caller raises it explicitly (`VerificationBudget(...)` or the explicit
`VerificationBudget.unlimited()` — an explicit raise, never an implicit one). The budget bounds the ORDER of work, not
a wall-clock number (cold cost per E-unit varies 0.2–33 ms across honest targets). Request pins and the canonical
requirement are checked BEFORE any budgeted work.

## 6. StreamDisposition (the ONE semantic closure) — frozen design

* **Module:** new leaf `smartchem/stream_disposition.py` (step.py cannot import the capability package; `WasteCapability`
  is NOT moved — enums encode by class name, moving it shifts every profile digest).
* **Subject algebra (CLOSED, 4 kinds, structural keys, never free names):** `BYPRODUCT(core = structure_key(species))`;
  `RESIDUAL(core = species key; one per (step, species))`; `OP_STREAM(op ordinal + op core digest)`;
  `USE_STREAM((op ordinal, use index) + use core digest)`. Every subject carries `step_signature` = digest of the
  sorted `resonance_identity` reactant and product multisets. Subject keys are injective and deliberately NOT
  reorder-invariant: a prose edit never unbinds; reordering ops makes the subject vanish → construction refuses (never a
  silent rebind). **Excluded:** untyped op material and untyped step input — neither can ever reach FIT (their spec /
  quantity terms stay unresolved independently), so a disposition on them would be decorative.
* **Values:** `CONSUMED_COMPLETELY` (RESIDUAL only, and only if the step net-consumes the species); `RECOVERED`
  (RESIDUAL or USE_STREAM only, and it must name `via_op`, a DISTILL/FILTER/SEPARATE op in the same procedure — that
  op's own stream stays a separate obligation; never implies reagent purity); `ROUTED(WasteCapability)` (all four kinds;
  a species-level ROUTED needs a known hazard record; adds a category, so a bench lacking it → waste BLOCKED; an
  OFFGAS-vs-CONDENSED fate contradiction → UNKNOWN). Absence = UNKNOWN. RECOVERED on a byproduct is refused (byproduct
  recovery is a second-product question — `requirements.py:352`). The two REDUCING values need structural
  corroboration; ROUTED only adds a requirement.
* **Evidence:** SOURCE_QUOTED only (stricter than `CERTIFYING_REQUIREMENT_EVIDENCE`: no kernel backs DERIVED/CLAMPED
  on a disposition), an accepted `procedure.source`, a non-empty locator, and the exact subject. AUTHOR_INFERRED,
  ASSUMED, USER_DECLARED, UNKNOWN, DERIVED, CLAMPED are refused at construction.
* **Placement:** `ProcedureEvidence.stream_dispositions: tuple[StreamDisposition, ...] = ()` appended last,
  digest-covered, canonically sorted, duplicate subject refused. `ExperimentStep.__post_init__` refuses an unknown
  subject, a wrong `step_signature`, and CONSUMED_COMPLETELY on a species the step does not net-consume (loudness +
  wire-forgery refusal); SOUNDNESS lives in `derive_waste`'s exact-key lookup. Coverage ledger rows added
  (`missing_coverage()` must stay `()`).
* **Consumption:** `derive_waste` (the single producer of waste obligations) moves exactly ONE obligation from
  `unresolved` to `reasons` per matching disposition and ADDS the ROUTED category; it never deletes a derived category
  (monotone, law L1). `assess.py` needs no change.
* **Corpus:** NO cited page states disposal (Lane C checked the isopentyl page: zero disposal sentences) — no corpus
  envelope gains a disposition; zero production FIT is expected and acceptable.
* **Synthetic reachability witness (MODEL-LEVEL, benign, not a real procedure):** the DME fixture + 3 dispositions
  (ROUTED(AQUEOUS_NEUTRAL) on the water byproduct, ROUTED(AQUEOUS_NEUTRAL) on op #3, CONSUMED_COMPLETELY on methanol)
  reaches CAPABILITY_FIT under an exactly-sufficient Custom profile (equipment {CONTROLLED_HEATING, GRAVITY_FILTRATION,
  REACTION_VESSEL, REFLUX_CONDENSER}, containment {FUME_HOOD}, measurement {MASS}, waste {AQUEOUS_NEUTRAL}). Deleting
  any one disposition → UNKNOWN; a bench without AQUEOUS_NEUTRAL → BLOCKED; swapping A's disposition onto B does not
  discharge B; changing the ROUTED category moves only the waste axis.
* **Residual honesty boundary:** CONSUMED_COMPLETELY on an excess reagent is a SOURCE_QUOTED claim the model cannot
  cross-check without a unit engine (stated in COMPATIBILITY.md).

## 7. Resonance-key migration law (S7/S8)

One public memoised `stock.structure_key(m)` = `"struct:" + resonance_identity(m)`; an `asgiven:` fallback (molecules
above 64 heavy atoms / 128 placements) maps to `"struct-asgiven:" + …`, byte-identical to today. Delete
`requirements._struct_digest` and `waste._struct_digest`; `name_resolves_to` uses it on both sides; replace
`assess._STRUCTURE_KEY_PREFIXES` with a shared `is_structure_key`. KEEP the private symbol `stock._structure_key` as the
implementation M3 patches (or retarget M3 in the same commit). Controls: graph-surgery Kekulé alternates (NOT
SMILES-spelling pairs, which the parser already canonicalises — a vacuous control) of o-xylene, catechol, salicylic
acid, methyl salicylate, aspirin, o-cresol, phthalic acid, 2-aminophenol, naphthalene → one key; end-to-end parsed
bottle × flipped requirement (both directions) not BLOCKED; 13 constitutional-isomer pairs (+ o/m/p-xylene) distinct;
tautomers distinct; (R)/(S) and H2O/D2O share a key (the named boundary); salts are not one Molecule; a no-move sweep
over the 69 registered/commodity/library structures. Corrected `stock.py` doc (lines 14, 117–119, 136, 241).

**Declared identity boundary (1.0):** material identity is CONSTITUTION-level (resonance class); stereo and isotope
labels are not perceived by stock matching; the target's stereo/isotope features are disclosed as identity losses on the
request; a Molecule carries one global charge and one connected species (salts are name-keyed).

## 8. Source-subject scope (Part 10) and the deferred representation gaps

* **EvidenceSubject: NOT added.** Evidence records prove ARITHMETIC, not subject or source. A claim's subject is fixed by
  placement; requirement-side claims come only from the shipped corpus, which the canonical loader re-derives (D27.1);
  every stock-side claim is the operator's declaration and certifies exactly as USER_DECLARED (S9 removes the fake
  labels on states/phase; a pin test asserts stock SOURCE_QUOTED / DERIVED / USER_DECLARED intervals give identical
  edge verdicts). Transplanting a sourced number onto another material moves the component/stock digest (Lane H,
  Verified) — the minimum the brief demands. The one path that could strengthen toward FIT without the operator's word
  is StreamDisposition, whose subject binding is structural (§6). A locator is a provenance string, never a verification.
* **Part 11 (temperature domain): DEFER.** `TypedInput.temperature_k` is digest-covered and read by nothing; the only
  consumer of the derived NaCl interval is the temperature-invariant `interval[0] > 0` commensurability test
  (`assess.py:414–416`), so the domain is irrelevant to every frozen comparison; a blanket law would create false
  UNKNOWNs. No frozen verdict moves.
* **Part 12 (one-sided physical requirement): DEFER to post-1.0.** The physical axis is UNKNOWN in all 21 frozen cells;
  the distillation lower bound 416.15 K is ≤ every frozen bench ceiling (523.15 / 473.15 / 500 K), so no verdict moves.
* **Part 13 (endpoints): keep prose endpoints = measurement UNKNOWN.** Typing all 5 corpus endpoint slots changes no
  verdict in 21 cells; a `PH_INDICATOR` member would be auto-declared by `research_lab` / the fit bench via
  `frozenset(MeasurementMethod)` — decorative.

## 9. Consolidation plan (Lane A) — what moves, what stays

**Hard wall:** 13 of the 16 classes in `service.py` fold `__module__` into their digests (`contracts.py:104–105`;
`_V08_OMITTED_FIELDS` hard-codes `smartchem.service.*`) — moving any of them moves every digest. Only functions,
constants and non-digested classes may leave.

Incisions (safest first): **E1** per-load reconstruction memo (via §4 context). **I1** `smartchem/transport_integrity.py`
(body digest, transport-bound result digest, HMAC sign/verify, producer-key resolution, transport-mode constants — ~60
lines, zero service deps, zero mutant retargets). **E2** one shared assessment helper (`service.py:1506–1509` vs
`2835–2838`). **E3** one shared frontier-admission predicate (`3126` vs `3812`) and hard-blocker logic (`3561–3580` vs
`2959–2986`). **E4** the producer consumes `_rederive_request_context` (one request-context authority; today hand-mirrored
at `3846–3906` vs `3744–3793`). **I2** `smartchem/legacy_v08.py` — the ~140-line pure legacy kernel (`_v08_canonical_payload`,
`_v08_digest`, omitted-field tables, smuggling refusal helpers); retarget M108/M116. **I0** ~180 lines of schema-history
comments move to `docs/research/SCHEMA_HISTORY.md` (current-truth comments stay). **New authority:**
`smartchem/verification.py` (§2–§5).

**Recommended AGAINST (recorded so nobody re-walks them):** moving the `_check_*` methods (25 v0.9 mutants + v0.8
M10/M12 retarget, 62 ledger entries rewritten, no duplicate removed); moving any digest-covered class/enum; extracting
request-context / projection / wire-container modules (each needs the record classes → cycle); hoisting the lazy imports
(M212 anchors a lazy-import line; they are not cycle dodges — the docstrings claiming so get corrected); a strategy-object
"legacy boundary"; deleting the narrower readiness/capability/frontier checks; moving `_check_reexecution`; the optional
~910-line `replay_codec.py` move (no duplicate removed — deferred unless budget remains).

**Refusal order:** existing checks keep their order (the freeze records message heads). NEW checks (S1, S3, S6,
budget) are placed at the earliest point that has their inputs. The hidden safety order F9 is REPLACED by S6 (a structural
refusal), not preserved by accident.

## 10. Release engineering decisions (Lane F)

Wheel is byte-reproducible for a fixed builder (`c3668999…`, 3 builds); installed CLI output is byte-identical to the
source tree on 3.10/3.11/3.12/3.13 and on the declared dependency floors (numpy 1.24.0, scipy 1.10.0). Decisions:
`MANIFEST.in` prunes `tests/` from the sdist (it shipped 290 test files without fixtures/conftest/experiments — unrunnable);
a release script repacks the sdist canonically (sorted, fixed mtime, owner 0, `gzip -n`) and writes `SHA256SUMS`;
single-source version (`[tool.setuptools.dynamic] version = {attr = "smartchem.__version__"}`); S12; S13; the dev venv's
stale 0.4.0 editable install is reinstalled (`pip install -e . --no-deps`) and the ignored stale `smartchem.egg-info/`
removed; CI YAML gets the minimal repo-side corrections it needs even when runners return (use `scripts/run_suite.sh`,
`timeout-minutes`, pin `ubuntu-24.04`, a wheel-install smoke job) — labelled UNVERIFIED until a runner exists; the hosted
CI blocker (account billing — GitHub's own annotation) is recorded in `docs/CI_INFRASTRUCTURE_BLOCKER.md`.

## 11. File ownership (Wave B) — one writer per file, parent integrates one incision at a time

| writer | owns | may not touch |
|---|---|---|
| `rc-verification-core` | NEW `smartchem/verification.py`, NEW `tests/test_v0_9_5_verification_core.py` | `service.py` |
| `rc-service-adapter` (sequential incisions) | `smartchem/service.py`, NEW `smartchem/transport_integrity.py`, NEW `smartchem/legacy_v08.py`, `smartchem/transport_ledger.py`, `tests/test_transport_ledger.py`, NEW `tests/test_v0_9_5_loader_laws.py` | capability/*, stock |
| `rc-identity-material` | `smartchem/experiment/stock.py`, the key call sites in `capability/requirements.py`, `capability/waste.py`, `capability/assess.py`, `experiment/material_spec.py` (S9 only), NEW `tests/test_v0_9_5_material_identity.py` | service.py |
| `rc-stream-disposition` | NEW `smartchem/stream_disposition.py`, `smartchem/experiment/procedure_evidence.py`, `smartchem/experiment/step.py` (binding check only), `capability/coverage.py` rows, NEW `tests/test_v0_9_5_stream_disposition.py` | corpus sources |
| `rc-capability-integration` (after identity-material) | `capability/waste.py` (derive_waste consumption + D-C1/D-C2/D-C4), witness + zero-FIT theorem test rewrite | corpus sources |
| `rc-release-engineering` | `pyproject.toml`, NEW `MANIFEST.in`, NEW `scripts/build_release.py`, `smartchem/program.py` (S12 only), `smartchem/cli.py` (S13 only), `.github/workflows/ci.yml`, NEW `COMPATIBILITY.md`, NEW `docs/ARCHITECTURE.md`, NEW `docs/CI_INFRASTRUCTURE_BLOCKER.md`, NEW `experiments/v0_9_5_install_matrix.py` | semantics |
| `rc-gates` | NEW `experiments/v0_9_5_*` (RC funnel + frozen oracle, fuzzers, stress, verification performance), `experiments/v0_9_mutation_calibration.py` (mutant additions / retargets, successor harness if needed) | production code |

Integration order (each: baseline differential, focused tests, relevant mutants, ledger completeness, perf if applicable,
then commit): (1) verification-core; (2) adapter: policy/receipt/context/memo/budget/cache wiring + S1/S6/S14-refusal
plumbing (freeze: NO DRIFT); (3) adapter: S3/S4/S5/S11 (NO DRIFT); (4) adapter: I1/E2/E3/E4/I2/I0 (NO DRIFT);
(5) identity-material S7/S8/S9 (adjudicated drift: capability question digests of structure-keyed profiles only);
(6) stream-disposition + capability-integration + adapter wire bump S10 (adjudicated drift: digests + schema ids only,
verdicts unchanged); (7) release S12/S13 + packaging; (8) gates; (9) Wave C; (10) final re-freeze, full suite,
mutation gate, bump `0.9.5a1`, PR (not merged).

The RC funnel corpus + its blind expected-outcome oracle are written and committed by `rc-gates` BEFORE step (5) lands
(frozen before the feature-closure writers see the answers).

## 12. Mutation additions (minimum; every one must be KILLED, zero void retirements)

Omitted cache coordinate (each of registry digest / target value / reagent tuple / budget); stale cache after a provider
semantic change; cache on vs off byte-identical; budget exhaustion skips D29.1 (→ must refuse); budget charged after the
work; `VerificationBudgetExceeded` swallowed by the broad except; thin accepted under `require_canonical_transport`;
legacy accepted under `require_canonical_transport`; a forged/replaced `VerificationReceipt`; receipt says `reexecuted`
without re-execution; F1 count law dropped; F3 duplicate-chemistry law dropped; F4 DAG-height law dropped; F9
TARGET_FILE path opened on load; DAG leg dropped from D29.1 and from D27.1 (C7-3); disposition wrong-subject discharge;
non-certifying disposition discharges; CONSUMED_COMPLETELY on a byproduct; RECOVERED without `via_op`; disposition
deletes a derived category; resonance key merges constitutional isomers (o/m/p-xylene); resonance key splits alternate
Kekulé; a literal `_struct_digest` reintroduced on the requirement side; B-narrow guard dropped (states / phase); source
subject transplant not moving the component digest; wheel missing runtime package data; installed CLI diverging from the
source CLI; implementation digest reading an ambient file.

## 13. Exit (0.9.5 release gate — unchanged from the mission)

Baseline freeze: no unexplained drift (every drift key classified under §1). Verifier authority consolidated per §9.
Default verification work bounded (§5). Canonical/thin trust impossible to confuse under `canonical()`. Resonance material
identity correct (§7). StreamDisposition sound + synthetic witness (§6). Frozen RC funnel complete with every denominator.
All ACTIVE mutants killed. Fresh Wave C finds no release blocker. Deterministic stress passes. Package build/install passes
on every locally available supported Python (3.10–3.13). Source and installed behaviour agree. Full OOM-safe suite passes.
CI green OR the exact external blocker documented. `COMPATIBILITY.md` exists. `docs/ARCHITECTURE.md` reflects reality.
Only then: `0.9.0a1 → 0.9.5a1`, PR `feat/v0.9.5-adversarial-rc → main`, NOT merged.

---

## 14. Amendments (adjudicated after the barrier; each names its evidence)

| id | amendment | evidence |
|---|---|---|
| **A1 = S15** | **Front-door misparse fixes** (0.6 layer; exact regression fixes, allowed in 0.9.5): **F-2** interior whitespace may be removed only where removal cannot change tokenization (around separators; digit / `)` / `]` → capital or `(`/`[` boundaries such as `H2 O`, `CuSO4 . 5 H2O`); whitespace whose removal would attach a count across it (`CuSO4 5H2O` → `CuH2O46S`, `O4 2` → `O42`) or fuse letters into a different element symbol is a typed `FormulaSyntaxError` naming the explicit separator (`CuSO4·5H2O` / `CuSO4 . 5 H2O`; the ASCII-period spelling `CuSO4.5H2O` stays refused as a decimal-point ambiguity, FD-08). **F-3 REFUTED as a defect** (adjudicated after the writer stopped on an oracle conflict): the bare trailing-sign rule is a DECLARED convention pinned by test P0-B — a multi-element body reads a single trailing digit as a COUNT (the polyatomic-ion convention: `NH4+`, `NO3-`, `H3O+`, `VO2+`), a single-element body is refused as ambiguous (`Fe3+`); `HZn3+` = HZn₃⁺ under that convention; no change, the convention is stated in COMPATIBILITY.md. **F-4** (found by the S15 writer, same class as F-1): the SMILES ring-closure lexer accepted non-decimal digits (`isdigit()`), so `S²N²` was silently read as a ring in AUTO mode — ring labels are ASCII-decimal only. **F-1** a malformed bracket atom (`[³]`, `C[²H]`, `[¹²C]`) is a typed invalid input, never a bare `ValueError` (the CLI exited 70 INTERNAL). Accepted set: narrows for the misparsed spellings only; every change is listed in the fix's test file. | `experiments/RESULTS_v0_9_5_boundary_fuzz.md`, repros `experiments/fuzz_repros/frontdoor_0{1,2,3}_*.json` (seed 950; F-2 = a silent identity hallucination class → release-blocking) |
| A2 | S7 also retargets mutants **M55** (`requirements_mod._struct_digest(` → `stock_mod.structure_key(`) and **M179** (anchor → `if is_structure_key(key) or not name_resolves_to(key, requirement.identity):`) — §7 named only M3 | rc-identity-material report: both SURVIVED only as harness errors on the post-S7 tree; KILLED with the retarget |
| A3 | S3 is a CONSTRUCTION law (`CompilationResponse.__post_init__` → `_check_receipt_bounds`): even the keyless forger's digest-recompute path refuses | `tests/test_v0_9_5_loader_laws.py::test_s3_*` |
| A4 | Erratum: the baseline freeze carries **22** service cases (not 23) | `--check` output `NO DRIFT (22 service cases, ...)` |
| A5 | Erratum (§11 paths): `smartchem/procedure_evidence.py` and `smartchem/material_spec.py` live at the package root, not under `experiment/` | writer reports |
| A6 | The stale 0.4.0 editable install of the dev venv leaked main-checkout modules into worktree runs (a module absent from a worktree resolved from `/home/leah/SmartChem/smartchem/`); every integration gate runs in the main checkout on the integrated branch, so no committed result depends on it; the venv is reinstalled (`pip install -e . --no-deps`) once no writer is live | rc-gates part 2 report |
