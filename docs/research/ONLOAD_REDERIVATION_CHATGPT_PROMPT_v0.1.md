# On-load re-derivation (item 2) — the external design-review prompt sent to ChatGPT

> Status: **IN FLIGHT.** This is the *exact*, self-contained prompt handed to ChatGPT for an outside design
> review of ROADMAP queue **item 2** (on-load re-derivation of composability + physical). It is persisted here
> so that when the response returns in a fresh session, the answers can be mapped back to their five questions
> without reconstructing them. Sent during the ROUND 20 → compact handoff (2026-09-06).
>
> **Companion:** [`ONLOAD_REDERIVATION_SCOPE_DECISION_v0.1.md`](ONLOAD_REDERIVATION_SCOPE_DECISION_v0.1.md) — the
> in-repo decision (with the real file:line anchors) that this prompt abstracts into a codebase-free form. Read
> the two together. The prompt deliberately strips repo-specific identifiers so ChatGPT reasons from first
> principles; the scope doc is the ground truth those principles must land on.

## Why this exists

Item 2 closes a free-text trust boundary: on load, only the **process** component of each route's combined
`fit_status` is re-derived; **composability** (E1) and the **physical box** ride as free-text `exclusions`/`gaps`
and can be bare-relabeled to `FITS`. The decided design (digest-excluded thick re-derivation payload + a load-time
coherence check) is build-ready but big — its own round. Before building, we bought an outside adversarial read on
the design's protection-equivalence claim and its invariant. This is that prompt.

## How to use the response when it returns

1. Read ChatGPT's answers **against the scope doc**, not this prompt alone — the prompt hides the real
   constructors (`CompilationResponse.__post_init__`, `verify_composability`, `_step_box_check`,
   `ExperimentStep.__post_init__`). A recommendation only counts if it survives those actual constraints.
2. The load-bearing question is **Q1** (is digest-excluding the payload truly protection-equivalent to folding it
   in, for detecting a forged verdict?). If ChatGPT finds a hole there, the design changes before any code.
3. **Q2** (the monotonic sound-and-tight invariant) is the spec the build implements. Treat its answer as a
   proposal to verify, not gospel — re-derive the three-status → combined mapping against `service.py:1294`/`:1357`.
4. Then resume item 2 as a pure build per the scope doc. Nothing here authorizes a merge of the held branch.

## The prompt (verbatim, as sent)

```text
I'm hardening a load-time integrity check in a dependency-light Python "chemical compiler."
Pressure-test and refine the design below. Assume you have NO access to the codebase; reason
only from what's here.

BACKGROUND
- A compile emits a ranked list of synthesis routes. Each route carries a combined verdict
  ("fit_status") built from THREE components: composability (do adjacent steps' conditions and
  intermediates chain?), a physical box (are reagents available / equipment present / hazards
  cleared?), and a process axis.
- The serialized response is a THIN projection: each route/DAG summary carries only
  identity-relevant scalars plus a "process_requirements" field. It deliberately does NOT carry
  the full route object graph.
- On LOAD (deserialization) the response constructor re-derives ONLY the process component and
  enforces coherence against the claimed verdict. Composability and the physical box ride as
  free-text exclusions/gaps.
- THE HOLE: a route that is non-FITS for a composability or physical reason can be bare-relabeled
  to FITS in the serialized payload and admitted on load, unless a consumer opts into an HMAC
  signature. I want to close this STRUCTURALLY (no shared secret), the way the process axis is.

HARD CONSTRAINTS
1. Re-deriving composability needs each step's target intermediate (a molecular graph) and the
   FULL condition envelope (temperature/pressure/duration intervals, medium, catalysts, applied
   field, status, provenance, source, process) -- not just the process sub-field.
2. Re-deriving the physical box needs each step's reactants and products (reagent + hazard/
   equipment lookup).
3. Reconstructing a step is NOT partial-able: the step constructor builds a real mass+charge
   conservation certificate (Reaction(reactants -> products)) and REFUSES a non-conserving step.
   So any reconstruction must carry a COMPLETE, valid (reactants, products, reagents, target,
   envelope) per step.
4. Route identity is a digest over identity-relevant fields. A design rule says "dated data, not
   search identity" rides OUTSIDE the digest (compare-excluded); identity-relevant claims are
   digest-folded.

THE DECIDED DESIGN (review it)
- Carry a thick per-step re-derivation payload (reactants, products, reagents, target, full
  envelope) as an OPT-IN, digest-EXCLUDED (compare-excluded) field on both route and DAG summaries.
- Add a load-time coherence check that re-derives composability + the physical box from that
  payload and compares to the claimed verdicts (which ARE digest-folded), raising on mismatch.
- Rationale: a tamperer who edits the thick payload so it re-derives a DIFFERENT verdict than the
  claimed one is caught by the coherence check. A tamperer who edits BOTH the payload and the
  claimed verdict changes the digest -> that's the key-holding-forger residual only an HMAC closes,
  and it's unchanged by this work. So digest-EXCLUDING the payload is protection-equivalent for
  this purpose, while keeping every existing route digest byte-stable (folding it IN would change
  every route's identity -- a huge blast radius).

WHAT I NEED FROM YOU
1. Is "digest-excluded thick payload + coherence check" truly protection-equivalent to
   digest-folding it, FOR DETECTING A FORGED VERDICT? Find any hole: is there a tamper that changes
   the admitted verdict WITHOUT either being caught by the coherence check OR changing the digest?
2. Specify the coherence check's invariant precisely. The process axis already enforces a
   "one-direction lower bound": the honest combined status is AT LEAST AS SEVERE as any component
   (you can't relabel a route with a BLOCKED component to FITS). Give the exact monotonic rule for
   composability and physical, and the mapping from three component statuses to the combined one,
   so the check is SOUND (never rejects an honest verdict) and TIGHT (rejects every lenient forgery).
3. Recommend a serialization contract for (a) a molecular graph and (b) the 10-field condition
   envelope that must ROUND-TRIP LOSSLESSLY through the conservation-certified reconstruction. Flag
   the fields where a lossy round-trip would silently change a re-derived verdict.
4. Enumerate the adversarial tests: e.g. a payload that re-derives coherent-but-lenient; a
   reconstruction fed a non-conserving forged step; a payload present-but-empty; a mix of signed
   and unsigned routes; a payload whose re-derivation is coherent but whose CLAIMED verdict was
   edited to match (should fall through to the digest/HMAC residual, not the coherence check).
5. Should the check be GATED on the payload being present (zero overhead when absent) or MANDATORY?
   Argue the tradeoff.

Answer as a design review: a concrete invariant spec, a serialization contract, and a test list.
```
