# SmartChem: process accessibility audit and implementation

Date: 2026-09-05. Audited main: `2fc759542a2858605c25cd6bf660fdb56afe6975`.
Work branch: `audit/process-accessibility-2026-09-05`.

## Verdict

The requested direction is sound: accessible starting materials are insufficient when the operations
require equipment, attention, or workup that the operator cannot supply. This branch adds typed process
requirements and enforces operator limits across the synthesis frontends. It also repairs defects in
constraint precedence, selectivity, reagent identity, numeric validation, and response admission.

This is a working constraint and selection layer over a bounded formal search. It does not establish
arbitrary-formula-to-executable-synthesis capability. A reversed conserving cleavage is a candidate;
reaction applicability, material suitability, isolation, and analytical acceptance still need evidence.
The shipped catalog currently lacks the new whole-process metadata, so its process-constrained routes
honestly remain unknown-fit until suitable records are added.

## Repository and coverage

The GitHub connector supplied all 385 tracked files at the frozen commit. Every original file was
checked against its Git blob SHA, and the reconstructed full tree matched
`8162e124a07eb4b9715a2035447dac4210bd82a2`. Direct authenticated git cloning was unavailable in this
runtime; the local baseline is a verified tree snapshot, not a fetched historical git checkout. Published
commits on this branch descend from the actual remote main commit. No existing branch was overwritten.

Ten branches were returned by the branch census. Implementation starts from current main, which already
contains the recent compiler reorientation and subsequent work; older audits are historical context.
The code audit concentrated on identity/parsing, structural transformation and search, sourcing,
affordability and units, condition evidence, experiment grading, constraint fitting, service serialization,
CLI parity, and tests. The broader simulation/runtime domains are covered by repository regression tests,
not a new line-by-line physical validation of every executor. This report supersedes no unrelated roadmap.

Measured baseline catalog coverage:

| Surface | Observed scope |
|---|---|
| Commodity terminals | 15 structure-level source leads |
| Default synthesis transform grammar | One family: mediated capped scission |
| Condition seed | 3 records, 2 for assembly; 1 assembly envelope has an accepted typed source |
| Selectivity seed | 3 records |
| Kinetic seed | 2 records |
| New whole-process records | None in the shipped chemistry catalog |
| Formula-only target | Accepted for formula accounting; refused for a structural synthesis search |
| Charged transformation work | Opt-in decomposition capabilities; not a general charged synthesis planner |

## Round 1: reproduce and repair audit defects

| Finding | Baseline discriminator | Change |
|---|---|---|
| Evidence grade overrides a hard bench exclusion | Real ranking/classification with controlled enumeration preferred a cooler fitting candidate, but `compile_synthesis` selected a hotter excluded candidate with a stronger grade | Hard exclusions precede grade; no best dossier or shopping recommendation when nothing is admissible |
| Cash from different currencies compared directly | 5 USD dominated 10 EUR with the same unit and no exchange-rate evidence | Both currency and denomination must match for cash comparison |
| Invalid quantitative inputs contaminate ordering/conversions | Negative costs, infinities, fractional ordinal ranks, and conversion overflow were accepted | Validate finite nonnegative amounts and supported ranks; reject invalid mass/price conversions |
| Sparse registry masquerades as selectivity knowledge | A formal propanal-to-acetone control returned `NOT_APPLICABLE` because only one C3H6O isomer was registered | Missing applicable evidence remains `UNKNOWN`; exact sourced positive controls still work |
| Formula-only inventory masquerades as structural identity | Inventory containing C3H6O could satisfy a propanal reagent requirement | Formula-only matches produce an identity gap; exact names/aliases and missing identities retain distinct behavior |
| Impossible physical declarations accepted | Negative kelvin, pressure, and duration entered envelopes | Constructor validation rejects these values |
| Conserving identity steps crash rate grading | Spectator cancellation leaves an empty reaction evidence key | Arrhenius/Eyring consumers report an explicit unknown rate for no-net operations; the key constructor stays strict |

The formal isomerization controls test bookkeeping and evidence logic; they do not assert experimentally
available transformations. NIST lists [acetone](https://webbook.nist.gov/cgi/cbook.cgi?ID=67-64-1) and
[propanal](https://webbook.nist.gov/cgi/cbook.cgi?ID=C123386&Mask=10) with the same C3H6O formula but distinct
structures. Formula composition therefore cannot specify the user's unique intended chemical.

## Round 2: process requirements become load-bearing

`smartchem.process_constraints` separates operator limits (`ProcessBounds`) from supplied process facts
(`ProcessRequirements`). Requirements attach to each `ConditionEnvelope.process` and therefore contribute
to step and route identity. They have their own provenance; declaring process facts does not promote
unknown reaction conditions to sourced chemistry.

| Resource | Requirement | Operator limit |
|---|---|---|
| Elapsed time | Whole-step interval in minutes, including workup | Per-step ceiling and total route ceiling |
| Hands-on effort | Active minutes for all operations | Sum across the route |
| Attention | Continuous, periodic, or passive | Allowed attention modes |
| Check frequency | Maximum allowed minutes between operator checks | Shortest interval at which the operator can return |
| Agitation | None, manual, periodic, or continuous | Allowed modes |
| Equipment | Explicit exact identifiers, including workup apparatus | Explicit available identifiers |
| Workup scope | Explicit declaration that requirements include workup | Required for an affirmative process fit |
| Heat and pressure during workup | Whole-process temperature peak and pressure extrema | Existing physical bounds, applied together with process limits |

Missing is distinct from zero, an empty inventory, and unconstrained. A known violating dimension excludes
the route even if other dimensions are unknown. Any missing constrained dimension creates a gap. Route
totals conservatively sum step upper bounds; the implementation assumes no unproved overlap or parallel
labor saving. An already-known subtotal above the route limit excludes even if another step lacks data.

No duration, attention pattern, stirring tolerance, or apparatus is inferred from a low temperature,
a formula, a name, or a generic reaction class. A mild reaction envelope cannot clear an unknown or hotter
purification: when physical and process limits are combined, whole-process extrema must also be supplied.
An accepted citation is provenance, not experimental validation of the whole operation sequence.

The editable presets are software preference examples, not chemistry thresholds:

| Preset | Step elapsed | Total elapsed | Total active | Other defaults |
|---|---:|---:|---:|---|
| `quick` | 60 min | 120 min | 60 min | None/manual/periodic agitation |
| `low-touch` | 10,080 min | 20,160 min | 60 min | Passive/periodic attention; at least 60 min between required checks; none/periodic agitation |

Temperature and pressure remain explicit independent choices. Equipment is unconstrained unless supplied.
The user can override each preset dimension; `--equipment` with no values declares no equipment available.

### CLI examples

These commands exercise route selection and print evidence gaps, not laboratory instructions:

```bash
python -m smartchem recompile 'smiles:CC(=O)OC' --max-depth 2 \
  --process-profile quick --max-active-minutes 30

python -m smartchem recompile 'smiles:CC(=O)OC' --max-depth 2 \
  --process-profile low-touch --max-temp 333.15 \
  --max-pressure 1.1 --min-pressure 0.9 --min-check-interval 90 --json

python -m smartchem recompile --help
```

`compile`, `recompile`, and `synthesize` share the process flags and canonical request construction. The
current catalog example above finds formal routes but cannot admit them under process limits because its
whole-step requirements are absent. The machine response preserves those candidates and their reasons.

### Selection and protocol contract

Search completeness and process admission remain separate facts. `ROUTES_FOUND` describes the bounded
structural search; it does not claim the returned routes meet the operator's constraints.

| Process selection | Meaning |
|---|---|
| `NOT_REQUESTED` | No process bounds were supplied |
| `NOT_REQUIRED` | The target already matches active terminal stock; no synthesis was searched |
| `UNASSESSED` | No applicable route fitting ran, including the current DAG path |
| `NO_FIT_FOUND` | No returned route has a complete affirmative fit under the selected constraints |
| `FITS_FOUND` | At least one returned formal candidate fits the declared requirements and bounds |

`admissible_route_digests` contains only `FITS` candidates under active process constraints. Unknown and
excluded candidates remain inspectable, but are not selected for the best dossier, shopping recommendation,
or process-constrained affordability frontier. Candidate IDs must exist in the returned IR and ranked IDs
must be unique. A loaded response rechecks its derived admission fields, exit code, and result digest.
These are integrity checks on declared records, not authentication of the experimental evidence.

Exit codes keep their established precedence: invalid input 2, an empty complete structural search 3,
incomplete search 4, and refused admission 5 when a complete search has candidates but none can be admitted.
An incomplete search remains exit 4 even when a returned candidate fits. Successful stock matches remain 0.
Physical-only searches with every returned route excluded also return 5. A no-fit result is not a universal
claim that no workable synthesis exists.

Request schema advances to `compilation-request-v1alpha5`, response to `compilation-response-v1alpha9`,
descriptor to `compilation-response-schema-v1alpha10`. This is an intentional alpha protocol migration;
old request payloads are not silently upgraded by dropping their constraints. Golden fixtures were
regenerated for the new fields and changed identity/selectivity semantics.

## Round 3: adversarial integration

The acceptance probes include:

- Unknown process metadata versus complete synthetic declarations through the real search and service.
- A workup-scope mutation that kills a previously fitting software control.
- Hot workup, elevated-pressure workup, and vacuum-isolation counterexamples under mild reaction conditions.
- Whole-route labor/time limits, missing steps, known over-limit subtotals, and overflow.
- Continuous attention versus periodic operator availability, explicit contradictory declarations, and
  unavailable or unknown equipment.
- Malformed/extra/missing protocol fields and fabricated or duplicate admitted route identities.
- Imported affordability frontiers cannot recommend candidates that process admission did not accept.
- Null/spectator-only operations through fitting and grading, with genuine isomerization and rate controls retained.
- Exact CLI request/JSON parity, incomplete-search precedence, and quiet-mode blockers.
- Sourced/selectivity and numeric positive controls alongside the counterexamples that killed prior behavior.

Synthetic metadata validates the software comparisons only. It is not also used as experimental validation.
Agent reviews shared the same model family and code provenance; their agreement is not independent chemistry
evidence. Regression results and environment limits are recorded in
[the validation receipt](experiments/validation/process-accessibility-2026-09-05/receipt.json), alongside
the raw final test and benchmark output. The baseline-only heuristic benchmark ran successfully but reported
incomplete coverage (5 of 11 reference cases declined), with conditional MAE 80.60 kcal/mol on the six scored
cases. That result is not chemical accuracy and does not validate synthesis predictions.

## What remains open, in priority order

1. **Applicable whole-process evidence.** Populate a small reviewed record set with direction, exact molecular
   identity, material assumptions, scale, operations, workup, equipment, attention, and provenance. Start with
   benign covered chemistry and independent holdouts. There is no general process-data importer in this branch;
   the programmatic seam is `ConditionEnvelope(process=ProcessRequirements(...))` and reviewed provider records.
2. **Applicability of sourced selectivity and kinetics.** Structure/composition matches alone do not establish
   transport across temperature, solvent, catalyst, scale, or addition-order changes. Selectivity records still
   lack a full operational applicability envelope. Bind these contexts before claiming a source licenses the
   requested operating regime.
3. **Material identity and suitability.** Commodity presence is a source lead, not an assay, isolation yield,
   stock amount, grade, or price guarantee. Connect typed `StockMaterial` requirements to terminal matching and
   the entire workup/analytical chain. Exact equipment identifiers likewise do not certify equipment ratings.
4. **Useful chemistry coverage.** Expand independently tested transformation providers and cross-provider
   compositions, with negative controls. The active synthesis grammar remains narrower than the decomposition
   research modules. More formal balances alone do not solve source coverage.
5. **Search completeness under constraints.** Filtering occurs after bounded enumeration. Excluded/unknown
   candidates still consume the search result budget; a low result cap can miss a later fitting route. Preserve
   incomplete receipts, then implement admissibility-aware search only with a valid monotonic pruning proof.
6. **Convergent process plans.** DAG process admission remains explicitly `UNASSESSED`. Scheduling, shared
   apparatus, overlapping attention, preprocessing, and total batch effort require a separate resource model.
7. **Procedure readiness.** Retain `FORMAL_CANDIDATE` until scale, addition order, endpoint, isolation,
   purification, waste handling, material assays, and analytical acceptance are supported. Fitting selected
   resource bounds does not imply reaction success, unattended suitability, or an executable procedure.

The [Open Reaction Database schema](https://docs.open-reaction-database.org/en/latest/schema.html) is a useful
primary-source design reference: it separates inputs, setup, reaction conditions, observations, workups,
outcomes, and provenance. A future adapter should preserve those distinctions, with explicit unknowns for
operator-effort fields absent from a source. This branch neither imports ORD data nor claims ORD supplies all
attention or workup requirements automatically.

## Continuation contract

Keep this branch separate until reviewed. Reproduce the validation commands in the receipt. Add one
properly sourced process record through the existing typed condition seam, then demonstrate: the expected
profile fits; a stricter heat, attention, or apparatus limit excludes; deleting one constrained fact yields
unknown; changing a material/condition outside source scope removes the supporting claim; and a fresh held-out
example behaves as predicted. Do not loosen unknown handling to make the demo return a route.
