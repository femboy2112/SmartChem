# Rule-calculus alkyne-Diels-Alder family + the Cope isomerization defer (v0.1)

The second reaction family compiled onto the `rule_calculus` kernel: the **alkyne-dienophile** Diels-Alder
[4+2] (diene + alkyne → 1,4-cyclohexadiene), a sibling of the alkene-dienophile family (#82 + the oracle
promotion). It closes the exact coverage gap the alkene family's adversary gate surfaced (dalembert:
"alkyne dienophiles are uncovered"). Opt-in, additive; production behaviour byte-unchanged for non-opt-in
users. This round also records a **verified-defer** of Cope/Claisen [3,3].

## 1. Why alkyne-DA (and the chemistry, verified not asserted)

A diene + an **alkyne** dienophile is a genuine, benign, thermal all-carbon [4+2]: the alkyne donates one
π to the two new σ bonds and keeps its second π as a ring double bond, so the product has **two** ring
double bonds where the alkene family's product (cyclohexene) has one.

The product isomer was **verified computationally**, not asserted: the [4+2] of butadiene + acetylene is
**1,4-cyclohexadiene** (`C1=CCC=CC1`), the two double bonds *isolated* (across the ring), NOT the conjugated
1,3-cyclohexadiene. Proof: under the rule, the retro of 1,4-CHD disconnects to butadiene + acetylene (4
symmetric matches), while the retro of 1,3-CHD gives **zero** matches. (An earlier loose assertion of "1,3"
in the alkene round's adversary report was never rule-checked; the mechanism and the kernel agree on 1,4.)

Degree-preserving at every atom (`(2,3,3,2,3,3)` both sides): the alkyne carbons carry one more bond-order
unit than an alkene dienophile, spent on the surviving ring C=C — so it lives natively in the degree-locked
fixed-vertex kernel, no extension.

## 2. The rule + the shared guard core

`_FORWARD_ALKYNE`: LEFT `{0=1, 1-2, 2=3, 4#5}` (diene + alkyne) → RIGHT the 1,4-CHD ring
`{0-1, 1=2, 2-3, 3-4, 4=5, 0-5}`; `RETRO_ALKYNE_DA = _FORWARD_ALKYNE.reverse()`;
`ALKYNE_DA_CLASS = "diels-alder-[4+2]-alkyne-cyclohexadiene"`.

Both families now ride **one** guarded-retro enforcement point, `_guarded_retro(retro_rule, forward_rule,
retro_signature, class_label, target, *, budget)`, extracted from the alkene family's body (dalembert's ask:
one enforcement point, not a hand-copied second one that could drift out of guard-step). `retro_da_disconnections`
(alkene) and `retro_alkyne_da_disconnections` (alkyne) are both thin callers; `class_witness` and
`independently_reconstructs` are rule-parameterized (alkene defaults preserved). The alkene family is
**byte-identical** after the refactor — its frozen probe hash (`a0e61e51…`) is unchanged, the proof.

The guards are family-agnostic: induced-subgraph exactness (locality), guard 2b (no exocyclic multiple bond
on a matched carbon — the internal alkyne triple is *not* exocyclic, so it is kept, while a matched carbon's
exocyclic C=O/C≡N is still dropped), class-witness by the match's own signature, the independent replay
verifier, and the global two-fragment split.

## 3. The self-verifying edge + the oracle recognizer (5th class)

`AlkyneDielsAlderEdge` clones `DielsAlderRetroEdge` with its own schema/class/certificate/centre (so it can
never be confused with the alkene edge): two certificates at construction — mass+charge conservation via a
real `Reaction`, AND alkyne-[4+2]-ness re-derived from the reactant (`_reactant_alkyne_da_disconnects_to`).
`forget()` maps the adduct → two fragment formulae — a real rank **descent**, which is exactly why alkyne-DA
fits the transform seam and Cope does not (§5).

`AlkyneDielsAlderProvider` (opt-in, absent from `DEFAULT_TRANSFORM_REGISTRY`, `witness_kind="DIELS_ALDER_ALKYNE"`)
rides the unchanged route/DAG seam.

Oracle recognizer `_alkyne_diels_alder` (the **5th** conservation-locked class) is a straight clone of the
alkene `_diels_alder`'s three-layer discipline against the alkyne family's own centre and re-derivation:
Layer A re-derives [4+2]-ness from the step's molecules, Layer B pins `center == _ALKYNE_DA_CENTER` (derived
from `_FORWARD_ALKYNE`, distinct from the alkene `_DA_CENTER` — the alkyne centre carries a `(C,C,3)` broken
bond, the triple), Layer C fail-closes on an absent centre. The two DA classes cannot cross-poach: their
centres are distinct and each Layer A rejects the other family's adduct.

## 4. A known cosmetic behaviour

1,4-cyclohexadiene has a 2-fold ring symmetry, so the guarded enumerator finds two distinct vertex-role
matches that yield the identical product pair (butadiene + acetylene); the kernel dedups by exact target
digest (not isomorphism), so the provider returns 2 transforms with the same equation. This is benign —
`search_routes` collapses it to exactly 1 route, and the oracle recognizer vouches either — and the tests
assert the equation *set*, not a literal count. A future round could canonicalize by product-config.

## 5. Cope/Claisen [3,3] — a verified-defer (the structure theorem that kills it)

Cope/Claisen was the originally-proposed family #2. A feasibility spike proved it **structurally cannot ride
the transform seam**, and the reason is a clean structure theorem:

- Cope is a **1→1 isomerization** (formula-preserving: C₇H₁₂ → C₇H₁₂). It IS a valid rule-calculus rewrite —
  degree-preserving `(2,3,2,2,3,2)`, the kernel accepts it and the parent round-trips.
- But `forget()` must return a `DecompositionEdge`, which enforces invariant **W1**: *"every product must be
  strictly lower rank or the descent does not terminate."* An isomerization has **no descent** (product rank
  == reactant rank); the spike got `DecompilerError: non-descending product … (W1)`. The whole
  decompiler/route-search machinery is built on strict rank descent to guarantee termination, so an
  isomerization cannot be integrated through it.

This is not a bug to patch — forcing an isomerization in would break the termination guarantee (unsound).
Isomerization families (Cope/Claisen, electrocyclizations) need a **different** integration path (a lateral
"rewrite" seam, not the strict-descent decompiler) — deferred as future work. Proving this **is** the
deliverable (the R32 pattern: an oracle + structure theorem proving no sound consumer exists is a verified
defer). It is why alkyne-DA (a composition-reducing 2→1) was chosen instead.

## 6. Boundaries (honest)

- Scope: all-carbon diene + **alkyne** dienophile → 1,4-cyclohexadiene only. An allene dienophile, or an
  alkyne embedded in a larger conjugated system, is genuine [4+2] chemistry this family does NOT cover —
  honest coverage loss (false-UNRECOGNIZED), never a false-vouch.
- Structural type-validity only (Problem A): no feasibility, regiochemistry, or endo/exo.
- Opt-in: `DEFAULT_TRANSFORM_REGISTRY` unchanged; production behaviour byte-identical for non-opt-in users.

## 7. Evidence

- `tests/test_alkyne_diels_alder.py` (family) + additions to `tests/test_diels_alder_oracle.py` (recognizer +
  cross-poach both directions) + `experiments/alkyne_diels_alder_family_probe.py` (frozen `content_hash`) +
  `tests/test_alkyne_diels_alder_family_probe.py`.
- Alkene family byte-equivalence pinned by its unchanged frozen probe hash.

## 8. Adversary gate (run SEPARATELY from acceptance — the meta-lesson)

Both adversaries ran on the alkyne family + its oracle recognizer; both SURVIVED on the structural
(Problem-A) contract.

- **evil-morty — no false-VOUCH (earned clean bill):** ~94k fuzz trials (72,667 seeded + 21,963 unseeded)
  around the 1,4-CHD core produced 118k+ vouched transforms and, by independent forward-rule replay, **0**
  non-genuine. Guards 2/2b fire correctly on the alkyne path (guard 2b keeps the internal triple, kills
  exocyclic multiples); `_ALKYNE_DA_CENTER` independently re-derived as correct; fail-closed totality +
  hand-built forgery refusal confirmed. The 3 dual-provider molecules the fuzz surfaced are benign (two
  different rings → two different steps; no single step vouched by both families).
- **dalembert — SURVIVED (structural claim), one boundary carved:** no structural false-vouch, no cross-poach
  (the two centres are distinct multisets — the alkyne carries a `(C,C,3)` broken triple — and each family's
  Layer A rejects the other's adduct), no false-demote (the `_ALKYNE_DA_CENTER` invariant held across
  substituted / bridged / barrelene adducts).
- **The carved boundary (family-wide, fixed in prose):** the guarded retro can yield an **aromatic diene
  fragment** — barrelene → benzene + acetylene is vouched, and the shipped alkene family does the same
  (bicyclooctadiene → benzene + ethylene). This is IN-SCOPE for the module's "structural type-validity only,
  feasibility deferred" contract (benzene-as-diene is a valid [4+2] topology; whether it runs is Problem B).
  The prior guard-3 comment overclaimed "aromatic exclusion is automatic" — now scoped to the ADDUCT, not the
  retro fragments. A blanket aromatic-fragment drop was **rejected**: it would wrongly kill the genuine
  anthracene-type Diels-Alder. The boundary is pinned as a deliberate scope test.

Residual (non-actionable, noted): `Config` equality is the load-bearing infra Layer A reduces to (pre-existing,
outside this diff); Layer B's centre is not by itself a class certificate (Layer A is the gate, which held
everywhere); the "no-op in production for non-opt-in users" rests on the default single-cut's reachability,
not structure (even if reachable, a non-[4+2] fails Layer A — no false-vouch).
