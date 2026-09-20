# Rule calculus course correction: witnesses before authority

**Base:** `main@8810a45cd508c250919e9d7f7127133a74ae0c2d` (R63).
**Branch:** `aletheia/rule-calculus-course-correction-2026-09-19`.
**Status:** executable structural research slice, with local finite tests and mutation controls;
production integration tests are supplied but not claimed as run in the sparse local workspace.
**Direction:** preserve the compiler, provider seam and open-diagram backbone. Add a checkable
rule-calculus layer without turning formal rewrites into laboratory authorization.

## 1. Executive verdict and corrections to the preceding audit

The audit identified a useful direction, but its strongest phrases need correction before they become
architecture. This document supersedes those phrases, not the project's honesty contract.

1. **A collection of failed local classifiers is not a universal impossibility theorem.** A collision
   refutes factorization through that particular observation map on those labelled cases. It does not
   refute every bounded-radius recognizer, every application-condition language or an enriched global
   representation. The exact theorem is in Section 3.1; `fibre_collisions` implements its finite probe.
2. **DPO validity is structural validity.** A checked span/application proves graph facts. It cannot,
   by itself, establish that the reaction class is chemically attested, that these substrates react,
   that the pathway is selective, or that the available apparatus can realize it.
3. **Free syntax and chemical equivalences are compatible.** One may construct free syntax and then
   impose a justified quotient. The existence of chemical relations does not disprove freeness of the
   syntax. Conversely, testing two examples does not prove faithfulness of a semantics functor.
4. **Do not assume chemically admissible graphs form an adhesive category.** Valence, bond uniqueness,
   charge localization and stereochemical constraints need a model and closure theorem. This build
   uses an explicit, guarded, all-vertices-preserved simple-graph fragment; it is not a general DPO
   engine or a proof about all chemically valid graphs.
5. **The current whitelist has three active entries, not four.** R63 replaces N-methylation with
   general N-alkylation. `reaction_type_oracle.py` still says “FOUR CLASSES” and carries stale
   disposition prose. Correct that documentation during integration; this additive branch leaves
   the existing module bytes and its authoritative behavior unchanged.
6. **The published completeness result has a formal scope.** Gale–Lobski–Zanasi describe a faithful,
   full-up-to-isomorphism translation between their disconnection syntax and formal reactions [1].
   That is not completeness of real-world synthetic chemistry or of SmartChem's current providers.
   The paper's theorem has not been ported or independently re-proved here.
7. **A condition/effect distributive law is not itself an adjunction.** The old withdrawn slogan
   should not be restored. Here the useful, fully specified adjunction is between image and universal
   preimage for a finite relation. It has actual operators, carriers and tests.

The prior answer's repository findings were primarily source inspection, not a fresh full-suite run.
This branch preserves that distinction. A snapshot's reported green suite is not a new measurement.

## 2. What this branch builds

| File | Executable contribution | Boundary |
|---|---|---|
| `smartchem/rule_calculus.py` | Typed fixed-vertex bond rules; local matches; replay witnesses; independent table verifier; budgeted match enumeration; bounded raw-state closure; sufficient read/write independence | Structural, not a reaction-type/feasibility oracle; no isomorphism quotient |
| `smartchem/rule_calculus_bridge.py` | Local span extraction from `CappedScission`; forward/backward replay; independent endpoint reconstruction; projection into the existing `OpenChemDiagram`; opt-in `AuditedCappedScissionProvider` | Neutral, empty-state species only; existing recognizer remains the class authority; production integration unrun locally |
| `smartchem/rule_semantics.py` | Finite context relations; existential/universal preimages; fibre collisions; exact interval grades; robust Pareto certificates; independent capability axes; symbolic state-potential cancellation | Declared finite models, not calibrated physical data |
| `tests/test_rule_calculus*.py`, `tests/test_rule_semantics.py` | Exhaustive finite, negative, mutation-sensitive and full-checkout bridge gates | Finite implementation evidence, not universal proof |
| `experiments/rule_calculus_probe.py` | Reproducible JSON receipt; explicit `--integration` mode | No silent substitution for a full checkout |
| `experiments/rule_calculus_mutations.py` | Isolated baseline and six actual mutants, with raw outputs | Same-author tests, not blind agent reports |

This is not a second compiler or an automatic default-provider migration. The opt-in provider is a real
consumer at the existing `TransformProviderRegistry.enumerate` seam. It returns the existing transforms
only after replay, preserving their original identities and the parent's completeness flag. Its own
provider identity/manifest changes, correctly changing the declared grammar identity. A failed replay
raises a scoped refusal rather than dropping a candidate and calling the search complete.

The three current class examples are methyl acetate, diethyl ether and ethylamine, used only as graph
integration fixtures. Their class labels come from the existing oracle. No procedure, conditions,
quantities, yield, purity or practical accessibility is inferred from these examples.

## 3. The mathematical package

These are scoped elementary derivations and engineering consequences; no priority or novelty claim is
made for the underlying category theory, graph rewriting, interval arithmetic or order theory.

### 3.1 The exact observation-fibre theorem

Let S be a set of cases, p:S -> O a declared observation, and v:S -> V the verdict being predicted.
There exists g:p(S) -> V with v = g o p **iff v is constant on each fibre of p**.

**Proof.** If v = g o p, equal observations give equal verdicts. Conversely, for an observation o,
define g(o) to be the common verdict of its nonempty fibre. Fibre constancy makes this well-defined.
For finite S this is an executable partition check. QED.

A collision therefore identifies a representation/probe defect, not the falsity of the underlying
chemical proposition. `fibre_collisions` returns the two cases and disagreeing labels. Changing the
observation map can remove the obstruction. Zero collisions on a finite corpus says nothing about
unseen cases or correctness of the supplied labels.

**New acceptance discipline:** every generalization claim names its observation map, label authority,
finite corpus and unresolved fibres. A further “locality is impossible” claim needs a quantified family
of counterexamples, not a longer list of failed heuristics.

### 3.2 The fixed-vertex rewrite lemma

A rule is L <- K -> R, with identical labelled vertex sets on all three graphs and
E(K) = E(L) intersect E(R). A match m:L -> G is injective on vertices, preserves labels and required
bond orders, and introduces no new edge whose endpoint pair already survives in the host context.
All vertices survive, so there is no vertex-deletion dangling condition in this fragment.

Write D = G minus m(E(L) minus E(K)). Define

    H = D union m(E(R) minus E(K)).

The checked collision condition makes H a simple labelled graph. Vertex labels are unchanged. For each
matched vertex, require the sum of incident bond orders in L to equal the sum in R. Then its degree in
H equals its degree in G; every unmatched vertex is untouched.

**Proof.** Only mapped deleted/added edges change. At a matched vertex the degree difference is
sum(added orders) minus sum(deleted orders), which is zero by the rule condition. No vertex or label is
added/deleted. Edge gluing is disjoint outside K. The two setwise edge unions supply the pushout squares
in the ambient labelled incidence-graph interpretation; rejecting duplicate pairs retains the simple
output fragment. No closure theorem for a chemical-validity subcategory is being assumed. QED.

This proves **preservation**, not that the initial valence was chemically admissible. Opaque labels,
formal charge distributions and stereochemistry are not reconstructed from an integer degree.

### 3.3 Equivariance and the frame law

For a vertex permutation sigma of G, transport both the host and the match. Then

    apply(r, sigma(G), sigma o m) = sigma(apply(r, G, m)).

For a disjoint spectator graph C, with m landing in G,

    apply(r, G disjoint-union C, m) = apply(r, G, m) disjoint-union C.

**Proof.** A bijection commutes with finite set difference and union. The modified edge set lies in
the mapped rule; a disjoint frame has no such edge. QED.

The tests inspect every permutation in a four-vertex example and a nonempty spectator frame. The raw
digests deliberately change under presentation changes; they are not canonical chemical identities.
The bridge compares reconstructed species using the existing repository canonicalization rather than
inventing another molecule-identity system.

**Quotient frontier:** atom mapping must be transported jointly with both endpoints. Canonicalizing the
two endpoints separately is not an atom-mapping witness. Before quotienting histories, prove congruence
under composition and tensor and retain occurrence identities for repeated equal reaction events.

### 3.4 A sufficient independence theorem, with its real limit

For an application a, let Q(a) contain the mapped left-edge queries and the required absences of newly
created bonds. Let W(a) contain the endpoint pairs whose order changes. If two verified applications
share a source and

    W(a) intersect Q(b) = empty,   W(b) intersect Q(a) = empty,

then each remains applicable after the other and the two results coincide.

**Proof.** Neither application changes an edge query on which the other's admission depends. Labels
never change. Their write sets are disjoint, since each write is also a read in this fragment. Thus the
two finite updates commute. QED.

This is sufficient, not necessary. It does not decide chemical competition, simultaneous feasibility,
or safety. Adding a global guard changes the read footprint; the theorem must be extended before
reusing it for that guarded grammar. General critical-pair analysis remains open.

### 3.5 Relative bounded completeness, now stated at the correct level

Fix a finite ordered rule registry, seed graph G, depth d, total vertex-extension budget B, and raw-state
budget N. The matcher enumerates injective label-preserving maps with iterative DFS. Breadth-first
closure expands every discovered state of shortest distance less than d.

**Conditional theorem.** If the receipt is `COMPLETE_TO_DEPTH`, its state set is exactly the raw labelled
states reachable from G by at most d applications of that registry.

**Proof.** Soundness follows from `apply`. For completeness, the matcher explores every prefix of each
possible injective map unless it reports a budget exit. Induct on shortest path length. At distance zero
G is present. If all states at distance k<d are present, every legal next application is enumerated when
its source is expanded, so every state at distance k+1 is present unless the state budget exits. BFS
state deduplication is harmless because future applicability depends on the full current graph, not
on the path used to reach it. Both exit kinds are explicitly incomplete. QED.

This is **not** completeness of all histories, paths, isomorphism classes, reaction mechanisms or real
chemistry. Context-sensitive history/resource search must include that context in its state before
reusing the Markov-state proof. Preprocessing/input-size costs are not hidden inside the match counter.
Cyclic/state-preserving rewrites no longer depend on a strictly decreasing molecule-size measure.

The production `SearchReceipt` is not replaced. This finite engine is a reference instrument for
calibrating future provider/search extensions, not a second claim that the old search is exhaustive.

### 3.6 Contextual realizability is relational, not a boolean per arrow

For a formal arrow f:X -> Y, let C_f be a declared relation between source contexts and output contexts.
For a composable pair,

    C_(g o f) = {(a,c) : exists b, (a,b) in C_f and (b,c) in C_g}.

Both C_f and C_g can be nonempty while their composite is empty. The probe uses an output context `wet`
for the first relation and a required context `dry` for the second; these are abstract labels, not a
chemical protocol. “Both steps work somewhere” does not prove one compatible route exists.

Relational composition is associative because the two parenthesizations assert the same existential
witness pair. Identity is the diagonal relation. Cartesian product gives an interchange-respecting
parallel semantics **when independence/product contexts are part of the model**.

The backward planner gets an exact operation:

    may_(g o f)(T) = may_f(may_g(T)).

It can therefore propagate acceptable target contexts backwards instead of discarding them after
reaction generation. The existing Conditions/Process machinery should eventually supply these typed
relations or conservative approximations, rather than be replaced by fictional categorical wrappers.

### 3.7 The useful adjunction is image versus universal preimage

For relation R, let image_R(A) be its direct image and must_R(B) the inputs all of whose successors lie
in B. Then

    image_R(A) subset B  iff  A subset must_R(B).

**Proof.** Both sides say that every edge whose source is in A ends in B. QED.

A state with no successors belongs to must_R(B) vacuously. Therefore universal safety-style preimages
must not be read as reachability: require a separate nonempty-successor witness when execution is
needed. The tests pin the empty-relation negative control as well as the adjunction and backward laws.

### 3.8 Symbolic cancellation can resolve the net while steps remain unknown

Fix explicit potential coordinates k = (species identity, phase, environment identity, model identity).
Environment identity must bind the temperature, standard state, activity convention and reservoirs
needed by that model. A reaction/route has a signed exact ledger n_k, so its formal state-potential
change is sum_k n_k G_k. Compose ledgers and cancel coefficients **before** partially evaluating G.

For A -> I -> B,

    (G_I - G_A) + (G_B - G_I) = G_B - G_A.

If G_I is unknown but G_A and G_B are known, the net is known while both steps remain unknown. With
G_A in [10,11] and G_B in [3,4] in one common declared unit, the net enclosure is [-8,-6]. These are
synthetic model values, not measured chemical constants.

**Proof.** Coefficients of the same symbolic coordinate sum to zero. No numerical value for that
coordinate is needed. Keys with different species, phase, environment or model do not cancel. For
known interval variables, cancelling shared coordinates before interval evaluation gives an enclosure
contained in the uncancelled Minkowski sum; the latter needlessly forgets shared-variable dependence.
QED.

The existing `route_net_delta_g` sums per-step values and returns unknown if any is unknown. This branch
adds an **auxiliary** symbolic instrument; it does not weaken that production gate. A known net drive
cannot certify rate, individual activation barriers, selectivity or any missing operation. A nonzero
cycle cost may represent omitted reservoirs or dissipation, not a contradiction of endpoint algebra.

### 3.9 Poor-man resources: partial orders and a scalar-decoration obstruction

Exact interval grades carry a unit. An unknown input is not a zero-price reagent. For minimizing cost
vectors with interval components, a sufficient robust strict dominance certificate is

    upper(a_i) <= lower(b_i) for every i,
    and upper(a_j) < lower(b_j) for at least one j.

It is irreflexive and transitive. An unknown coordinate prevents this certificate. No probability or
independence assumption is inferred from the intervals. Reusable equipment, simultaneous occupancy,
separation, product verification and waste handling must remain explicit capability/context axes.

There is also a concrete reason NOT to treat elapsed duration as just another scalar SMC decoration.
If sequential durations add and parallel durations take max, interchange would require

    max(a+c,b+d) = max(a,b) + max(c,d).

For (a,b,c,d)=(10,0,0,10), the two sides are 10 and 20. The operation is not a general scalar decoration.
Retain the causal/resource schedule and distinguish independent branches from a global synchronization
barrier. An event-graph/resource semantics can model the difference; relabelling a max/sum fold as a
functor cannot.

`capability_verdict` keeps substrate, conditions, kinetics/selectivity, equipment/containment,
separation, identity/purity and waste handling distinct. Its strongest output is only
`FITS_DECLARED_MODEL`; input declarations are not authenticated evidence. The kernel never fills a
missing capability with success. No outside/household substitution confers containment or safety.

## 4. What remains open, and the next verdict-changing probes

| Frontier | Next concrete build/probe | Pass / failure boundary |
|---|---|---|
| General rule calculus | Compile one new guarded structural family to the existing provider interface; start with a benign bond-order-change family | Same search shell, complete receipt propagation, independent replay; no chemical attestation inferred |
| Three recognizers -> class witnesses | Encode exact atom-mapped patterns/application guards for current acyl, ether and N-alkyl classes; compare on independent positives and hostile near-misses | Legacy agreement on the declared corpus plus externally supported class scope; disagreement is investigated, not relabelled “real” |
| Full DPO scope | Explicit atom/charge/state maps, node operations where meaningful, and ambient category with verified gluing hypotheses | Counterexamples for dangling/identification/collision; a molecular-valence subcategory is not assumed adhesive |
| Context/realizability | Connect one sourced whole-process example to context relations, including workup and product checks | Common intermediate-context witness; missing context remains unknown, not blanket infeasibility |
| Identity/quotient | Joint endpoint-plus-atom-map transport; occurrence-aware repeated events | Relabelling invariance, context congruence and a negative control separating distinct connectivity |
| Search scalability | Receipt-preserving pruning / symmetry reduction against the finite reference engine | Exact state-set agreement on finite holdouts; incomplete providers cannot become aggregate complete |
| Thermodynamics | Feed full state/model keys into auxiliary symbolic net-balance evaluation | Unknown intermediates cancel only as identical variables; phase/model mismatch stays unresolved; no admission promotion |
| Kinetics/selectivity | Context-indexed transition relations or kernels with independently supported parameters | Holdouts and competing-path regimes; product survival is conditional on the stated stochastic/kinetic model |
| Poor-man access | Resource-aware scheduling plus independent identity/purity and waste/containment evidence | Show a practical low-resource alternative only after all required controls are supported; prices dated/sourced or unknown |
| Provenance/transport | Bind rule body, match, context, all verdict-bearing evidence and scope into verified replay | Arbitrary supplied rule labels and payload hashes cannot mint trusted authority; preserve current thick/thin refusal discipline |
| Empirical coverage | Predeclare a benign target corpus spanning acyclic/ring/charged/state/stock boundaries | Report each funnel denominator: representable, enumerated, class-recognized, feasible, capability-fit; zero-step purchase is separate |

A frozen whitelist is not the endpoint. Neither is deleting it before its replacement has a sound
admission theorem and new external evidence. The next round should start by running the supplied real
bridge gates, then build one new family in a separate feature branch, not by replacing the entire core.

## 5. Verification and provenance

The committed receipt is `experiments/validation/rule-calculus-2026-09-19/receipt.json`,
with `tests.txt` and `probe.json` alongside it. Full mutation stdout/stderr and JUnit are retained
in the delivered validation archive; the script regenerates them without modifying original files.

The source snapshot was read through the authorized GitHub connector. The branch is based on the exact
commit above. No AGENTS.md or CLAUDE.md entry was found in the retrieved recursive tree. The container
could not resolve github.com for cloning; no complete local checkout, original-suite baseline or
mocked replacement for original modules is claimed.

Local source and tests were actually executed in a sparse workspace containing the new modules. The
bridge test module explicitly skips if `smartchem.category` is unavailable. This skip is an access gap,
not evidence that integration works. The separate `--integration` probe does NOT skip: it fails without
a full repository. Full-branch CI results, if subsequently obtained, must be recorded separately.

The local tests include 17,496 host/match comparisons against a matrix interpreter; 4,096 associative
relation triples; 65,536 relational interchange quadruples; exact adjunction/backward checks; 625
known-potential balance pairs; negative/malformed/budget/phase/mutation controls. These are finite
checks. The proofs above give their mathematical scope; neither proves physical chemistry.

The mutation runner records a green baseline, then kills six actual mutants through ordinary test
failures: lost context, a verifier trusting the target, budget laundering, false independence, unknown
as zero, and failed symbolic cancellation. Generator and verifier use different representations but
share the same author and graph data types. They are not blind agents or independent scientific sources.

Reproduce in a complete checkout:

```bash
python -m pytest -q tests/test_rule_calculus.py tests/test_rule_semantics.py tests/test_rule_calculus_bridge.py
python -m experiments.rule_calculus_probe --integration
python -m experiments.rule_calculus_mutations
# Then run the repository's original suite in its established OOM-safe partitions.
```

Do not promote this branch to a general synthesis engine or bench-ready release. A total *answering
contract* can be pursued: supported input -> witnessed candidates or precisely scoped unresolved,
incomplete, absent-in-grammar or unsupported outcomes. No returned route is guaranteed for every target.

## 6. Primary-source context

Sources were rechecked on 2026-09-19. The following descriptions stay within the authors' stated scope;
this round did not reproduce their full proofs or import their implementation.

[1] Ella Gale, Leo Lobski, Fabio Zanasi, *Disconnection Rules are Complete for Chemical Reactions*,
arXiv:2410.01421v1 (2024). https://arxiv.org/abs/2410.01421
Formal disconnection-to-reaction translation, faithful and full up to isomorphism; not universal wet-lab synthesis.

[2] Ella Gale, Leo Lobski, Fabio Zanasi, *A Categorical Model for Retrosynthetic Reaction Analysis*,
arXiv:2311.04085 (2023). https://arxiv.org/abs/2311.04085
Layered props model partial explanations including environment, chirality and protection/deprotection.

[3] John C. Baez, Blake S. Pollard, *A Compositional Framework for Reaction Networks*,
arXiv:1704.02051; Rev. Math. Phys. 29 (2017), 1750028. https://arxiv.org/abs/1704.02051
Open reaction networks, dynamical semantics and steady-state black-boxing; no microscopic synthesis oracle.

[4] Jakob L. Andersen et al., *Representing catalytic mechanisms with rule composition*,
arXiv:2201.04515v3 (2022). https://arxiv.org/abs/2201.04515
Rule composition records conditions and transient changes beyond endpoint differences; this motivates
preserving atom traces and occurrence/provenance rather than conflating net balance with mechanism.

[5] Jakob L. Andersen, Christoph Flamm, Daniel Merkle, Peter F. Stadler,
*A Software Package for Chemically Inspired Graph Transformation*, arXiv:1603.02481 (2016).
https://arxiv.org/abs/1603.02481
DPO rules, rule composition and graph-language generation over multisets; an implementation precedent,
not evidence that this new kernel is equivalent to that package.
