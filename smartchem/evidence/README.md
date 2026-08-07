# `smartchem.evidence` — probe-evidence contract auditor

A **decoupled sibling** of the SmartChem compiler. It points SmartChem's already-coded
epistemic discipline — *"a check derived from its own subject checks nothing"* — at any
external project's numerical **probes**, auditing the *contract* around them and either
**certifying** or **refusing** it.

It is **not** a physics checker, **not** a tenth executor, and makes **no** claim of
SmartChem scientific authority. It reuses `smartchem.contracts` primitives (`ClaimKind`,
`EvidenceStatus`, `Digestible`, `canonical_digest`) but never enters the closed executor
registry and **never raises a declared evidence status**. Every certificate carries a loud
hygiene-not-physics banner.

## Who can use it

Any project — fine-man or otherwise. The integration contract is the JSON manifest schema
(`manifest.schema.json`, id `smartchem.evidence/probe-manifest-v1`). Your project emits a
conformant manifest; you run the CLI. **Your repo imports nothing from SmartChem, and
SmartChem imports nothing from yours.** The tier vocabulary is caller-declared
(`floor_tier` / `promoted_tier`), so nothing here is fine-man-specific.

## Usage

```bash
# Start from a known-good, CERTIFYING template, then edit the strings:
smartchem-verify-probes --example > my-probes.json
smartchem-verify-probes my-probes.json

# Verify a file, a directory of manifests, or emit canonical JSON:
smartchem-verify-probes path/to/manifest.json
smartchem-verify-probes path/to/manifests_dir/
smartchem-verify-probes manifest.json --json
```

`smartchem-verify-probes` is put on your PATH by `pip install smartchem`; the exact
equivalent is `python -m smartchem.evidence …`. The older `… verify-probes <path>`
subcommand word still works as an optional alias — it is no longer required, so the
command no longer stutters.

Exit codes (the CI-gate contract):

| code | meaning |
|------|---------|
| `0`  | every audited manifest **CERTIFIED** |
| `1`  | at least one manifest **REFUSED** (a working refusal, not an error) |
| `2`  | a manifest could not be loaded (malformed / missing / not JSON) |

> A **`flag`** (rule 2's honestly-scoped common-mode) still **CERTIFIES and exits `0`** — it is a
> note, not a refusal. If your CI gate must catch flagged claims, grep the text output for `flag`
> or read each rule's `outcome` in `--json`; the exit code alone will not show it.

## The five rules (each transplants one SmartChem discipline)

> **Precondition — `nonvacuous`.** Before the five, a manifest must carry **at least one
> record**. An empty `records` list trips none of the five rules and would otherwise *certify
> vacuously* — a green certificate over nothing, which a `$?`-only gate reads as "passed." It is
> **REFUSED** (exit `1`) instead: the guard against the likeliest adoption footgun, a
> dropped-records emitter bug (`{"records": []}`) shipping a green gate.
>
> Two deliberate boundaries: (1) a manifest that carries records but **no `CLAIM`** — a
> calibration-only baseline, e.g. one file of a directory-audited suite whose `CLAIM` lives in a
> sibling file — is *not* refused; it is a legitimate independent unit. (2) The exit code
> certifies **hygiene, not substance**: a single *hollow* `CLAIM` (no inputs, no values, a
> rubber-stamp mutation) still certifies at exit `0`, honestly held at toy tier — a record count
> cannot police content. Read the evidence ledger / `--json` for strength, not just `$?`.

1. **teeth** ⇐ the DERIVED-MENU LAW — every `CLAIM` must be paired (`pairs_with`) with a
   `MUTATION` recorded as demonstrating a break (`passed=true`). A claim with no mutation, or
   whose mutation did not break it (`passed=false`), has no teeth → **REFUSE**.
2. **provenance-independence** ⇐ independent-verifier / no-shared-code — an `agreement` CLAIM
   must draw on ≥2 **distinct** provenance `source`s. Common-mode over-reported → **REFUSE**;
   common-mode honestly held at `structural-toy` with a scope note → **FLAG** (still certifiable).
3. **source-lock** ⇐ refusal over an unearned answer — every `empirical_values` entry needs a
   non-empty `source`. Missing → **REFUSE**.
4. **scope** ⇐ casualty/omission lists — every `CLAIM` needs a non-empty `scope_boundary`, and
   every probe needs ≥1 `SCOPE` record. Missing → **REFUSE**. The union of boundaries becomes the
   certificate's casualty list.
5. **tier-boundary** ⇐ `ClaimKind` ⊥ `EvidenceStatus` — `claimed_tier` may be the `promoted_tier`
   only if a `role=CLAIM, claim_kind=LITERAL, discriminator=true, passed=true` record exists.
   Otherwise the honest tier is `floor_tier` → **REFUSE** the promotion.

**Any REFUSE ⇒ the whole manifest is refused. No partial green.**

## Field semantics (the ones emitters get wrong)

- **`role: CALIBRATION`** — the instrument recovers a *known* result before its novel readings are
  trusted. It is the one role **enforced by none of the five rules** — a manifest certifies without
  one — so the `--example` template includes it as good practice, not obligation. Include one per
  probe when you can: put the recovered-vs-known comparison in `numeric_result` and the cited known
  value in `empirical_values` (so the source-lock rule sees it). The other three roles carry
  weight: `CLAIM` is audited by teeth/provenance/scope/tier, `MUTATION` gives a claim its teeth, and
  every probe needs ≥1 `SCOPE`.
- **`claim_kind`** (reused from `smartchem.contracts.ClaimKind`, independent of `evidence_status`):
  - `LITERAL` — the claim is *about the real target itself* (this circuit, this spacetime).
  - `ANALOGUE` — the claim is about a *structural analogue / toy model* standing in for the target;
    it never becomes literal by gaining evidence.
  - `EXPERIMENTAL_PROXY` — the claim is about a measured proxy standing in for the quantity of interest.
- **`passed` on a `MUTATION`** — `true` means the deliberately-broken variant was **correctly
  rejected** (the break was caught → teeth confirmed). This is the *opposite* polarity from classical
  "mutant survived" scoring; read it as "the mutation check passed its own assertion."
- **`agreement`** — set `true` on a `CLAIM` that asserts an equality/agreement between two computed
  quantities. Note: rule 2 fires on *any* `CLAIM` that rests on <2 distinct provenance sources and
  declares evidence above `structural-toy` — so you cannot dodge the common-mode check by leaving
  `agreement` unset. The flag only *adds* scrutiny (an explicit agreement at toy strength must scope
  its common mode).
- **`numeric_result`** — an **opaque** JSON object folded into the record digest and **audited by no
  rule**. It is the check's returned data, for tamper-evidence only. **Cited empirical/reference
  numbers must go in `empirical_values`, not here** — a number hidden in `numeric_result` escapes the
  source-lock rule (see boundary below).
- **`discriminator`** — `true` on the single `role=CLAIM, claim_kind=LITERAL` record that gates the
  `promoted_tier`. It must also be `passed=true` **and** declare evidence above `structural-toy`
  (a toy cannot legitimize). Any project may use a promoted tier; it is not physics-specific.

The published `manifest.schema.json` is a **structural** contract (it validates shapes). The five
rules above are the **acceptance** contract and are stricter — a manifest can be schema-valid and
still be refused. Validate against the schema *and* run `verify-probes`.

## Honest boundary — what a declarative auditor cannot catch

The auditor consumes a *declared* manifest and audits the **recorded** outcomes; it does not
re-execute your probes. Three things are therefore the **emitter's honesty obligation**, stated on
every certificate's banner rather than silently assumed away:

1. **Source aliasing.** Rule 2 counts distinct `source` *tokens*. Two tokens that denote the same
   underlying root (`Omega` and `Omega_relabeled`) read as independent. The auditor cannot know they
   alias; declare provenance honestly.
2. **`numeric_result` smuggling.** A cited number placed in `numeric_result` instead of
   `empirical_values` escapes the source-lock rule. Put cited numbers in `empirical_values`.
3. **Rubber-stamp mutations (Mode B).** The teeth verdict trusts the recorded mutation outcome; it
   does not re-run the mutation. A coupled (in-process, Mode A) emitter that actually re-ran it would
   strengthen this. The certificate attests the epistemic *contract*, not that the probes ran, and
   never that the physics is right.

## Minimal manifest

```json
{
  "schema": "smartchem.evidence/probe-manifest-v1",
  "program": "my-project",
  "claimed_tier": "floor",
  "floor_tier": "floor",
  "promoted_tier": "legitimized",
  "records": [
    {"probe": "p", "check": "the_claim", "role": "CLAIM", "claim_kind": "ANALOGUE",
     "evidence_status": "STRUCTURAL_TOY", "passed": true, "agreement": true,
     "inputs": [{"source": "A"}, {"source": "B"}],
     "scope_boundary": "toy limit only", "pairs_with": ["break_it"]},
    {"probe": "p", "check": "break_it", "role": "MUTATION", "claim_kind": "ANALOGUE",
     "evidence_status": "STRUCTURAL_TOY", "passed": true},
    {"probe": "p", "check": "the_scope", "role": "SCOPE", "claim_kind": "ANALOGUE",
     "evidence_status": "STRUCTURAL_TOY", "passed": true,
     "scope_boundary": "no claim outside the toy limit"}
  ]
}
```

## Two ways to author a manifest

1. **Emit JSON, import nothing** (the decoupled default). Run
   `smartchem-verify-probes --example` to print a complete **certifying** manifest that
   exercises all four roles, redirect it to a file, and edit the placeholder strings. This
   is the whole integration surface — your repo never imports SmartChem.

2. **Build typed records, then serialize** (for a project that is happy to import SmartChem,
   e.g. its own test suite). Construct `EvidenceRecord` / `ProbeManifest` values — they are
   validated *at construction* — then `manifest_to_mapping(manifest)` returns a JSON-ready
   dict you can `json.dumps`. The round-trip is exact
   (`manifest_from_mapping(manifest_to_mapping(m)).digest == m.digest`), so what you emit is
   guaranteed conformant. `example_manifest()` is the worked reference the `--example`
   command itself serializes.

Either way, validate against `manifest.schema.json` *and* run `verify-probes`: the schema
checks shape, the rules check hygiene (the `nonvacuous` precondition plus the five
disciplines), and the rules are stricter.
