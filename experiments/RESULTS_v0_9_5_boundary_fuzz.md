# RESULTS -- v0.9.5 boundary fuzz (Part 18)

Harness: [`experiments/v0_9_5_boundary_fuzz.py`](v0_9_5_boundary_fuzz.py) -- seeded, five families, each with ONE declared
property and automatic shrinking (ddmin) of a failing input to a minimal repro.  It fuzzes the compiler's **representations**
(formula spellings, identity graphs, quantity vectors, wire payloads, search receipts) -- never synthesis instructions -- and
edits **no production code**.  A found failure is a FINDING (repro under [`fuzz_repros/`](fuzz_repros/)), not something fixed here.

Tree: `feat/v0.9.5-adversarial-rc` @ `115dd71` + the funnel/oracle commits (package `0.9.0a1`, base behaviour; no S-change landed).
Run: `.venv/bin/python experiments/v0_9_5_boundary_fuzz.py --write-repros` (seed 950, budget x1.0), plus seeds 951/952 at budget x3.

## Cases and findings

| family | property | cases (seed 950) | NEW findings | known-boundary hits | repro |
|---|---|---|---|---|---|
| `frontdoor` | only `IdentityParseError` escapes; bounded time; accepted meaning-preserving spellings equal the INTENDED composition; `render()`->parse is a fixed point; AUTO never silently picks a different-composition reading | 706 | **3** (F-1 crash, F-2 whitespace merge, F-3 bare-sign charge) | 0 | `fuzz_repros/frontdoor_0{1,2,3}_*.json` |
| `identity` | constitutional isomers stay DISTINCT (resonance key + stock layer); atom-permutation / Kekule-surgery respellings share the resonance key; every stereo/isotope feature is DISCLOSED as an identity loss; stock layer matches a Kekule respelling | 248 | 0 | 16 (**known:S7** -- Kekule stock-match, both directions x 8 benzenoids) | -- |
| `allocation` | material axis is NEVER FIT when demand exceeds supply (independent max-flow reference), never double-spends a package (multi-component / duplicate-id packages), never FITs an unquantified demand | 500 | 0 | 0 | -- |
| `wire` | key deletion/insertion, type mutation, nested-schema substitution, public-digest recomputation, transport downgrade, legacy-id smuggling: refused, or accepted only if semantically identical | 160 | 0 | 0 | -- |
| `receipts` | bound / count / stop-reason / completeness mutation (+ a deliberate consistent multi-field rewrite): refused | 111 | 0 | 0 | -- |

Seed 950 total: **1725 cases, 3 NEW findings, 16 known-boundary hits.**  Extra seeds (x3 budget; wire, receipts, identity, allocation):
seed 951 = 2564 cases (wire 480, receipts 331, identity 253, allocation 1500), 0 new, 17 known (16 x S7 + 1 x THIN-ADVISORY);
seed 952 = 2564 cases, 0 new, 16 known (x S7).

## The three findings (all front door; each is a REPRESENTATION defect, none touches a verdict)

**F-1 -- an untyped crash escapes the identity front door** (`P-crash`, `frontdoor_02_*`, minimal input `[³]`).
`resolve_identity("[³]")` (AUTO surface, also `smiles:[³]` and `C[²H]`, `[¹²C]`) raises a bare `ValueError: invalid literal for int()
with base 10: '³'` from `smiles._parse_bracket` (`int(iso)` on a superscript-digit isotope field: `str.isdigit()` is True for
superscripts, `int()` refuses them).  `plan` catches only `IdentityParseError`, so the CLI answers **exit 70 `ERROR_INTERNAL`**
(observed: `python -m smartchem plan "[³]"`), where the contract says a typed INVALID_INPUT.  The explicit-FORMULA surface refuses the
same text cleanly, so the bug is SMILES-parser-only.  Severity: low (robustness/contract; refusal is the right outcome, the wrong exception
class leaks).

**F-2 -- whitespace is silently deleted, so adjacent number tokens merge** (`P-silent-misparse[R1]`, `frontdoor_01_*`,
minimal input `O4 2` -> `O42`, from the human spelling `CuSO4 5H2O`).  The normaliser strips ASCII whitespace/tabs, so a
space-separated hydrate coefficient is glued onto the previous count: `CuSO4 5H2O` is accepted as **Cu S O46 H2 (composition
`CuH2O46S`, exit 0, "parse note: normalized 'CuSO4 5H2O' -> 'CuSO45H2O'")** -- a silently WRONG composition for a very common spelling
(`Na2SO4 10H2O`, `H2 2O`, `K2P4 (Mg2..)3 2Na4`, tab/NBSP variants likewise; 14 of 706 cases).  The ASCII-dot spelling is refused
(`CuSO4.5H2O`, decimal-point guard) and the middle-dot is understood, so the space form is the gap: the correct behaviours are refuse
(like `SO42-`) or read a following digit-led token as a hydrate coefficient; deleting the space is neither.  Severity: **medium** -- it is the
only place the front door hands a chemist a confident, wrong composition (the composition then drives `decompile`).
The shrunk text `O4 2` carries the merge; `shrunk_from` in the repro is the human spelling.

**F-3 -- the bare trailing-sign charge rule reads `X3+` as +1 with count 3, inconsistently with the ambiguity guard** (`P-silent-misparse[R2]`,
`frontdoor_03_*`, input `Fe１２Al４HZn3+`).  A single-ion `Fe3+`, `Cu2+`, `Zn2+`, `Al3+` (and `SO42-`) is REFUSED as an "ambiguous ASCII
ion", but the same charge tail after a multi-element body (`HZn3+`, `SiNBr2+`) is accepted as `+1` with the digit read as the last count
(the documented `NH4+` rule, recorded as a receipt note).  For a user meaning Zn(3+) the composition is `Zn3`/charge `+1` -- a
mis-parse with only a note.  Severity: low-medium (documented rule, but the guard's trigger is pattern-limited, so the refusal is
inconsistent across spellings of the same ambiguity).

## Known boundaries (recorded, not new findings)

* **known:S7** (16 hits per run): the stock layer does not match a Kekule respelling of the same molecule (bottle=parsed / requirement=flipped and
  reverse, 8 benzenoids: xylene, catechol, salicylic acid, methyl salicylate, aspirin, o-cresol, phthalic acid, 2-aminophenol).  The RESONANCE key
  itself is stable under graph-surgery flips and atom permutations (0 findings) -- the gap is exactly the literal `canonical()` stock key barrier
  S7 replaces.  The funnel members MK-01/MK-02 carry the same fact as PENDING(S7).
* **THIN-ADVISORY** (1 hit at seed 951): a THIN payload with an edited affordability-frontier `cost_vector.access_difficulty` and a
  recomputed public digest loads (semantic fields equal).  The thin wire is advisory by contract (D-T1) and `canonical()` refuses it at S1;
  classified known, not new.  Classifier: edits containing `downgrade_thin`.
* **S11** (consistent multi-field rewrite of the ADVISORY IR search status): NOT reproduced.  The deliberate rewrite in `fuzz_receipts` changes the
  IR-level `search_status`/`standard_status`, the receipt's `status`/`standard_status` and the top-level `standard_status` (digests recomputed) and the
  loader refused it.  It does NOT also rewrite `outcome` / `exit_code` / `search_space_status`, so it is not the FULL consistent rewrite barrier S11
  describes -- recorded as "this operator set did not reach the S11 hole", NOT as evidence the hole is closed.

## Is the harness able to fail? (controls)

* **allocation vacuity control**: 3/3 hand-built feasible controls reach material FIT, and 166/500 (seed 950), 542/1500, 514/1500 random cases do, so
  the never-FIT-over-supply property is exercised on real FITs, not vacuous.  (An earlier version reached 0/3 FITs because `assess` also caps the
  material axis at UNKNOWN for the base route's unrelated `material_unresolved` notes; the harness now replaces them with `()` -- the fix is in the
  fuzzer, and it was found by the control.)
* **`--self-test`**: the allocation family run against a deliberately broken flow (`_max_flow` returns the full demand) reports
  `P-fit-exceeds-supply` findings -> **self-test PASS** (the fuzzer is not blind to over-supply).
* **wire/receipts coverage** (seed 950): 132/159 and 101/110 valid mutations refused, the rest accepted-identical (no-op / honest thin); the refusal guards
  that fired include the whole-body digest, ranked-route re-derivation, schema-id dispatch, legacy-id smuggling refusal, exact-key checks and the
  IR-vs-receipt bound coherence check.  Zero untyped crashes from the loader (every refusal is a `ValueError`).

## Honest limits

* The wire/receipt families mutate ONE honest payload (methyl acetate @ poor-man, canonical THICK) with random single/double edits; they do not build
  multi-dossier (isopentyl) payloads, which is what the budget/S3 counting laws target -- that is the separate stress harness's job.
* `frontdoor` ground truth is the generator's own INTENDED composition for a spelling; genuinely ambiguous spellings (F-3) are findings about a
  documented rule, not about an undocumented bug.  Random malformed strings are only checked for crash / slowness / round-trip / positivity.
* Allocation is checked against an independent reference for SAFETY only (never-FIT-when-infeasible); over-conservative UNKNOWN/BLOCKED is not a failure.
* Shrinking is ddmin over characters / edit lists / requirement+bottle lists; the R2 and silent-misparse-by-intended-composition findings are not
  character-shrunk (their truth belongs to the whole string).
