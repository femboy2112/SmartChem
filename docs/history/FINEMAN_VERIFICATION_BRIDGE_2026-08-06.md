# SmartChem → Fine-Man verification bridge: audit + build spec

**Author:** Claude (Opus), working in the `fine-man` research repo, at Leah's request.
**Date:** 2026-08-06.
**Status of this doc:** a *build specification* for a future SmartChem session to implement.
Nothing here has been built. No SmartChem code was modified to write it. The audit in
Part I is grounded in a three-bearing read of this repo (architecture, trajectory, and a
full test run) done on 2026-08-06; every load-bearing architectural claim carries a
`file:line` so the implementer can re-verify rather than trust this doc.

**One-line intent:** SmartChem already enforces, on its own executors, the exact discipline
whose *absence* caused a retraction in the fine-man program last session. This doc audits
SmartChem, then specifies a small, decoupled tool — a **probe-evidence contract auditor** —
that lets SmartChem's discipline check fine-man's numerical "probes" for epistemic hygiene
(teeth, provenance-independence, source-locks, tier boundary), **without** touching
SmartChem's closed executor registry and **without** claiming to verify the physics.

---

## Part I — Audit of SmartChem (as of 2026-08-06)

### I.1 What SmartChem is

A **research compiler for scientific simulation programs** (`README.md:3`). It takes an
incomplete or metaphorical scientific request, forces every consequential modeling choice
into an explicit typed structure, compiles it to a narrowly-scoped executable plan, requires
human `Approval`, executes through a **closed, hand-registered set of nine executors**, and
returns a result bundled with its evidence status, exclusions, casualties, and a digest
audit trail (`README.md:36-61`). Under the compiler sits an older chemistry core
(`Molecule`/`Config`/`Reaction`, `smartchem/category.py`) whose `Reaction.__post_init__`
enforces conservation exactly once, at construction (`category.py:679-699`).

### I.2 Health — verified, not asserted

- **Test suite:** `.venv/bin/python -m pytest -q` → **`1476 passed, 14 skipped, 1 xfailed`**,
  exit `0`, run twice (the second run confirmed after a `tee`-pipeline exit-code hazard was
  caught and corrected). Zero failures. `ruff` is not present in `.venv` (system ruff exists
  at `/home/leah/.local/bin/ruff`); no `[tool.ruff]` section in `pyproject.toml`.
- **Git:** `main...origin/main`, clean, HEAD `2e405f7 feat: add bounded StructureIR adapter`.
- **Docs discipline:** the planning docs *self-supersede in place* (explicit "State
  supersession" banners, e.g. `DIRECTION_AUDIT_2026-07-27.md:14-19`) rather than silently
  rewriting history. Rejected work keeps its tombstone (a remote E1 verifier was `NO-SHIP`'d
  for calling the same production path it was meant to check —
  `RESEARCH_ROUND_OPEN_SYNTAX_2026-07-27.md:21-25`). This is a project that already treats
  common-mode verification as a firing offense.

### I.3 The five disciplines worth reusing (this is the whole reason the bridge is cheap)

These are SmartChem's, already built and tested. The fine-man program needs exactly these,
and currently enforces them only in prose (docstrings), not in code.

1. **Independent verifier, no shared code.** Every executor carries a second verifier that
   imports *neither* the production engine *nor* the executor (`rlc_ac_verifier.py:1-7`
   imports neither `rlc_ac.py` nor `rlc_ac_circuit.py`; it re-derives the RLC boundary
   relation, MNA rank, and every residual from scratch in exact rational arithmetic). The
   governing maxim, stated verbatim ≥3× in `THE_COMPILER.md:317,488-489,653`:
   **"a check derived from its own subject checks nothing."**
2. **`ClaimKind` ⊥ `EvidenceStatus`** (`contracts.py:46-101`, `README.md:59-60`). Two
   independent axes: *what kind of claim* (literal / analogue / experimental-proxy / other)
   vs *what evidence backs it* (established / calibrated / experimental / structural-toy /
   unsupported). "An analogue can have established algebra without becoming literal; a
   literal target can remain unsupported."
3. **Refusal over a plausible-but-unearned answer.** `carries_unmodelled_physics` → return
   `None`, never a wrong number (`THE_COMPILER.md:61-88`); the **DERIVED-MENU LAW** — every
   option offered must be the image of a *declared invariant* under a *declared operation*
   (`THE_COMPILER.md:100-105`).
4. **Canonical digest.** `canonical_payload`/`canonical_digest` (`contracts.py:108-191`): a
   strict, type-tagged, no-`repr`-fallback canonicalization that is the tamper-evident
   identity substrate for every plan/approval/certificate.
5. **Casualty/omission lists on every certificate** (`Certificate`, `program.py:1462-1511`)
   — a result is never shipped without the explicit list of what it *did not* cover.

### I.4 The central data structure and the extension cost

- **`PhysicalIR`** (`program.py:806-953`) is what flows through the compiler; its
  `__post_init__` cross-validates every reference rather than trusting the caller.
- **The closed registry:** `ExecutorDescriptor` (`runtime_registry.py:129-216`) and the
  hard-coded `_DESCRIPTORS` tuple of nine (`runtime_registry.py:232-505`). "No third-party
  executor can inherit authority by registration" (`README.md:53-54`).
- **Adding an executor is multi-file hand-wiring**, not plugin registration: a subject
  module + `compile_*()` + `_preflight_*` + `_execute_*` + a from-scratch independent
  verifier + one `_DESCRIPTORS` entry + a branch in `_observable_payload_error`
  (`program.py:1583-1930`) + optionally a branch in `structure_attachment_for_subject`
  (`structure_ir.py:509-539`). No ABC; conformance is duck-typed. **Implication for the
  bridge: do not try to make fine-man probes into executors.** That fights the architecture.

### I.5 The one smell, and the one nag (honest, because that is the standing rule)

- **Smell (independently flagged by two separate reads):** `_observable_payload_error`
  (`program.py:1583-1930`) and `structure_attachment_for_subject` (`structure_ir.py:509-539`)
  are hand-maintained `if executor_id == …` chains that duplicate the registry's own
  enumeration, with no shared enforcement that they stay in sync. This is precisely the
  "a check derived by hand-copying its subject" pattern the project's own doctrine distrusts.
  A tenth executor could pass registry validation while silently lacking a payload-error
  branch; the fallback behavior on an unmatched `executor_id` past `program.py:1930` was
  **not** verified in the audit and is worth checking before any extension. *Not a
  correctness bug found; a maintenance-hazard flagged.*
- **Nag (structural, out of my lane):** `ROADMAP_2026-07-27.md:7` and
  `DIRECTION_AUDIT_2026-07-27.md:7-12` both hedge, near-verbatim, that the milestone sequence
  "began as a proposal, not evidence of an earlier ratification." That is an unusual amount
  of protective language about *authorization* of the campaign itself. It may be ordinary
  diligence; it may mark a real disagreement about whether the campaign was sanctioned. I
  can't resolve it from prose and I'm not trying to — Leah will know if it matters.

### I.6 Audit verdict

SmartChem is **healthy, heavily tested (1476 green), and disciplined** — genuinely stronger
on epistemic hygiene than most research code. It is **not** pre-built to audit an external
repo's numeric results (its verifier/contract vocabulary is bound to its own closed
executor registry; importing outside results is not a designed capability). What transplants
is **the discipline**, and the bridge below carries it across as a small decoupled tool
rather than by bending SmartChem's registry.

---

## Part II — The need on the fine-man side

### II.1 What fine-man's verification looks like today

The `fine-man` repo (a GR-quantum legitimization program) verifies its physics through ~25
numerical **probes** (`research/probes/*.py`). Each is a plain Python file, run by a
`make research-check` gate, with a hand-rolled convention:

- check functions return a `dict`; a `TESTS` tuple names them; `main()` prints `PASS <name>`
  per check and `PASS all N` at the end.
- Every check is *supposed* to carry one of four **roles**, but only in its name/docstring:
  - **CALIBRATION** — the instrument recovers a *known* result before any novel reading counts;
  - **CLAIM** — the actual new assertion;
  - **MUTATION** — a deliberately-broken variant that *must* fail (the "teeth");
  - **SCOPE** — the explicit boundary of what the green check does and does not earn.
- Standing rules, enforced only by human vigilance: **never fabricate an empirical number**
  (every cited value must be source-locked to an arXiv id / textbook / closed form); label
  every claim on a **proved / observed / conjectured / unverified** ledger; and the program's
  one governing boundary — *no green check outside a passed "Milestone 4" discriminator may
  be reported as "the framing is legitimized."*

### II.2 The motivating failure — why this tool is worth building

Last session a probe shipped claiming a key gate ("§8 non-circularity") was **cleared**. An
adversarial re-derivation showed the CLAIM was a **generic identity**: two quantities that
were *both* proven identities of the *same single input* were compared and "agreed" — the
agreement **could not fail** for any consistent input. It was a check derived from its own
subject. The claim was **retracted**.

That is, word for word, the failure SmartChem's doctrine names: *"a check derived from its
own subject checks nothing"* (`THE_COMPILER.md:317`), and a "menu option" (the claimed
agreement) that was **not the image of a declared invariant under a declared operation** —
the DERIVED-MENU LAW violated. SmartChem already refuses to ship this shape on its own
executors. **The tool below lets it refuse it for fine-man's probes too.**

### II.3 The honest scope of what the tool can and cannot do

The tool audits **epistemic hygiene**, not physics. It cannot know whether `q_HDA = q_corr`
is *physically* right. It **can** mechanically detect that the probe asserting it has no
paired failing mutation (no teeth) and that its two compared quantities share provenance
(common-mode) — which is exactly what would have blocked the §8 retraction. Stated in
SmartChem's own axes: the tool checks that a `CLAIM` is *falsifiable and independently
sourced*; it never upgrades `EvidenceStatus` from `structural-toy` to `established`. That
boundary must be printed on the tool's own certificate so no one reads "probe certified" as
"physics verified."

---

## Part III — The tool: a probe-evidence contract auditor

**Name (suggestion):** `smartchem.evidence` (a new subpackage) + a thin CLI
`smartchem verify-probes`. It reuses `contracts.py` primitives; it does **not** enter the
executor registry.

### III.1 The data model — `EvidenceRecord` (built on `contracts.py`)

One record per probe *check*, a frozen `Digestible` dataclass so it gets a `canonical_digest`
for free:

```
EvidenceRecord:
  probe:            str                 # file/module the check lives in
  check:            str                 # the check function name
  role:             Role                # CALIBRATION | CLAIM | MUTATION | SCOPE   (new enum)
  claim_kind:       ClaimKind           # reuse contracts.py: literal | analogue | proxy | other
  evidence_status:  EvidenceStatus      # reuse contracts.py: established | calibrated |
                                        #   experimental | structural-toy | unsupported
  inputs:           tuple[ProvenanceTag, ...]   # declared input sources (see III.3)
  empirical_values: tuple[SourceLockedValue, ...]  # each cited number + its source token
  numeric_result:   Digestible          # the check's returned dict, canonicalized
  scope_boundary:   str                 # required non-empty for role == CLAIM
  pairs_with:       tuple[str, ...]      # for a CLAIM: the MUTATION check(s) that give it teeth
  passed:           bool
```

Two new small enums (`Role`, and `ProvenanceTag`/`SourceLockedValue` value types) added to
`contracts.py`; everything else is existing machinery. A **probe manifest** is just a list of
`EvidenceRecord`s plus a top-level program-tier field (below), canonicalized and digested.

### III.2 How fine-man emits the manifest — integration modes

**Mode B (primary, decoupled — recommended).** fine-man keeps its probes as-is and adds a
tiny in-repo shim that, per check, records `(role, claim_kind, evidence_status, inputs,
empirical_values, scope_boundary, pairs_with)` alongside the existing returned dict, and
writes a JSON manifest per probe run. `smartchem verify-probes manifest.json` (or a whole
directory) audits it and emits a `Certificate`. **fine-man does not import SmartChem
internals; SmartChem does not import fine-man.** The contract is the JSON schema. This
respects the closed-registry boundary (I.4) and keeps both repos independently releasable.

**Mode A (optional, tighter).** fine-man `from smartchem.evidence import calibration, claim,
mutation, scope, certify` and decorates its check functions; running a probe emits records
directly. Only worth it if fine-man is willing to take SmartChem as a dependency. Start with
Mode B; graduate to A only if the coupling earns itself.

### III.3 The five auditor rules (each a transplant of a Part-I.3 discipline)

The auditor consumes a manifest and either **certifies** it or **refuses** (SmartChem-style:
a refusal is a success of the tool, never an error). Each rule maps to a named SmartChem
discipline so the implementer knows the precedent to copy.

1. **Teeth rule (⇐ DERIVED-MENU LAW; the §8 defense).** Every `CLAIM` must name ≥1
   `MUTATION` in `pairs_with`, and the auditor must **run that mutation and confirm it
   genuinely fails/raises when the claimed structure is broken.** A "mutation" that passes
   (does not break) means the CLAIM has no teeth → **REFUSE**. A CLAIM with no paired
   mutation → **REFUSE**. *This rule alone would have blocked the §8 retraction.*
2. **Provenance-independence rule (⇐ independent-verifier / no shared code).** For a `CLAIM`
   whose assertion is an *agreement / equality* between two computed quantities, the auditor
   checks that the two quantities' `inputs` provenance tags are **disjoint** (not the same
   single source). Shared provenance on an "agreement" CLAIM → **flag as possible common-mode
   / generic identity**, downgrade `evidence_status` to at most `structural-toy`, and require
   an explicit `scope_boundary` acknowledging it. (This is the Aletheia "factor shared
   provenance before counting independent bearings" discipline; SmartChem's E1 `NO-SHIP` is
   the precedent.)
3. **Source-lock rule (⇐ refusal over unearned answer; `carries_unmodelled_physics`).** Every
   entry in `empirical_values` must carry a non-empty source token. Any asserted
   empirical/cited number without one → **REFUSE**. (Directly enforces fine-man's "never
   fabricate an empirical number.")
4. **Scope rule (⇐ casualty/omission lists).** Every `CLAIM` must carry a non-empty
   `scope_boundary`; every probe must contain ≥1 `SCOPE` record. Missing → **REFUSE**. The
   certificate reproduces the union of scope boundaries as the run's casualty list.
5. **Tier-boundary rule (⇐ ClaimKind ⊥ EvidenceStatus; the governing invariant).** The
   manifest's top-level `tier` may be reported as `legitimized` **only if** a
   `role == CLAIM, claim_kind == literal` record tagged as the Milestone-4 *discriminator*
   is present and `passed`. Absent that, any manifest-level "legitimized" claim → **REFUSE**;
   the highest honest label is `floor`. This turns fine-man's one governing boundary
   (roadmap: "no green check outside a passed Milestone 4 = legitimized") into a machine rule.

### III.4 Output — a `Certificate` fine-man can trust

Reuse `Certificate` (`program.py:1462-1511`) shape: bind the manifest digest, per-rule
verdicts, the aggregated proved/observed/conjectured/unverified ledger (derived from the
records' `evidence_status`), the casualty list (union of scope boundaries), and a **loud
banner**: *"Certifies epistemic hygiene of the probe suite, NOT the correctness of the
physics."* On any REFUSE, emit the refusal with the exact rule and record that tripped it —
never a partial green.

---

## Part IV — Build plan & acceptance criteria

Build it the way SmartChem builds everything: **the auditor's own tests must not share code
with the auditor** (I.3 rule 1 applied reflexively).

- **B0.** Add `Role`, `ProvenanceTag`, `SourceLockedValue` to `contracts.py`; add
  `EvidenceRecord` as a `Digestible`. *Accept:* round-trips through `canonical_digest`;
  digest is stable across runs, changes when any field changes.
- **B1.** The five auditor rules as pure functions over a manifest. *Accept:* each rule has a
  from-scratch test fixture — a **hand-authored** passing manifest and a **hand-authored**
  failing manifest — that does **not** import the rule's own construction helpers.
- **B2.** `smartchem verify-probes <path>` CLI → `Certificate` or refusal, exit code 0 on a
  clean certificate, non-zero on refuse. *Accept:* deterministic; same manifest → same digest.
- **B3.** The two **golden fixtures** from Part V appendix: the retracted §8 manifest must
  **REFUSE** (teeth rule + provenance rule), and a healthy probe manifest must **CERTIFY**.
  *Accept:* both, by digest, in CI.
- **B4 (Mode B shim, lives in the fine-man repo, not here):** a ~30-line emitter that writes
  the manifest from a probe's existing `TESTS` tuple + a small per-check annotation table.
  *Accept:* `make research-check` optionally also writes `manifest.json`; `smartchem
  verify-probes` on it certifies the current (honest) suite and would refuse a re-introduced
  §8-style claim.

---

## Part V — Non-goals, boundaries, and the two golden fixtures

### V.1 Non-goals (state them so nobody over-reads a green certificate)

- **Not a physics checker.** It cannot know if the physics is right; it checks that claims are
  falsifiable, independently sourced, and correctly tiered. Print this on every certificate.
- **Not an executor.** Do not enter `_DESCRIPTORS` (I.4). It is a sibling capability reusing
  `contracts.py`, not a tenth vertical.
- **Not a replacement for `make research-check`.** It audits the *epistemic contract* around
  the probes; the probes still have to *run and pass* on their own.

### V.2 The two golden fixtures (the acceptance heart)

- **REFUSE fixture — the §8 retraction, reconstructed:** a manifest with a `CLAIM` "q_HDA =
  q_corr agree" whose two quantities carry the **same single** `ProvenanceTag` (the conformal
  factor Ω) and whose `pairs_with` mutation, when run, **does not break** the agreement
  (because it is a generic identity). Expected: **REFUSE** on rule 1 (no teeth) and rule 2
  (common-mode provenance). This is the regression test that the tool earns its existence.
- **CERTIFY fixture — a healthy probe:** e.g. the fine-man `refoliation_shale` or
  `modular_hda_froeb_continuum_toy` probe, whose CLAIMs each pair with a mutation that
  genuinely fails (a fixed-cutoff / UV-sensitive reading that provably does *not* converge),
  whose empirical numbers are source-locked (arXiv ids), and whose tier is honestly `floor`,
  not `legitimized`. Expected: **CERTIFY** with `tier = floor`.

### V.3 Why this is a good fit rather than a forced marriage

The fine-man program and SmartChem independently converged on the **same core rule** — *a
check derived from its own subject checks nothing* — one in prose, one in code. The bridge
just lets the one that already made it mechanical enforce it for the one that hasn't. That is
the whole tool: SmartChem's discipline, pointed at fine-man's probes, refusing the exact
shape of last session's retraction, and honest to the bone about checking hygiene rather than
truth.

---

*If the SmartChem session picks this up: start with B0–B3 (self-contained, no fine-man
dependency) and the two golden fixtures. Mode-B shim (B4) is a fine-man-side change and can
land independently. Ping the fine-man side (Leah) if the `ProvenanceTag` model needs to
carry more than a source token — the honest independence check in rule 2 is the part most
likely to want iteration.*
