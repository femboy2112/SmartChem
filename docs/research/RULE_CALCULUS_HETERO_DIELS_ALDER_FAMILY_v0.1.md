# Rule-calculus heteroatom-Diels-Alder families (aza + oxa) (v0.1)

The FIRST non-all-carbon reaction families compiled onto the `rule_calculus` kernel: the **aza**-Diels-Alder
(diene + imine → tetrahydropyridine) and the **oxa**-Diels-Alder (diene + carbonyl → dihydropyran), the two
heteroatom siblings of the all-carbon [4+2] families (#82 alkene + #85 alkyne). Opt-in, additive; production
behaviour byte-unchanged for non-opt-in users, and the two shipped all-carbon families are **byte-identical**
after this round (their frozen probe hashes are unchanged).

## 1. Why hetero-DA, and the one-line design insight

A diene + a **heteroatom** dienophile (an imine `C=N` or a carbonyl `C=O`) is a genuine, benign, thermal
[4+2] cycloaddition — the parent hetero-Diels-Alder. It is the natural ground the all-carbon families opened
onto: the same concerted 2-σ-bond-forming pericyclic mechanism, one ring atom now a heteroatom.

The design insight that makes it nearly free: **a hetero-DA is the all-carbon alkene rule with dienophile
vertex 5 RELABELED `C → heteroatom`.** The fixed-vertex kernel matches by vertex *label*, and a pericyclic
reaction conserves valence at every atom — an imine/carbonyl is a double bond exactly like an alkene — so:

- the **degree pattern is identical** to the alkene family, `(2,3,3,2,2,2)` both sides (verified on the kernel:
  the forward rule round-trips L→R and the retro round-trips R→L for both N and O);
- **every guard** in `_guarded_retro` (induced-subgraph exactness, guard 2b, the two-fragment split, the
  independent reconstruction) is element-agnostic and is reused **verbatim** — no new enforcement point;
- the **label lock** means an N-bearing rule matches only N-bearing rings (a negative control confirms the aza
  rule finds **0** disconnections on an all-carbon cyclohexene), so families never cross-poach at enumeration.

The product isomer was **verified computationally, not asserted** (the 1,4-CHD lesson from #85): under the rule,
the retro of a tetrahydropyridine (`C1C=CCCN1`) disconnects to butadiene + methanimine (`C4H6 + CH3N`), and the
retro of a dihydropyran (`C1C=CCCO1`) to butadiene + formaldehyde (`C4H6 + CH2O`). Conservation holds
(`C4H6 + CH3N = C5H9N`; `C4H6 + CH2O = C5H8O`).

## 2. The family factory + the shared guard core

`_HeteroDAFamily` is an immutable descriptor; `_hetero_family(label, …)` builds one by relabeling vertex 5 of the
alkene rule geometry and **deriving** the retro, the match signature, and the reaction centre from that rule (so a
family can never drift from its own rule). Two instances: `AZA_DA` (N) and `OXA_DA` (O).

`hetero_da_disconnections(family, target)` is a thin caller of the **shipped, unchanged** `_guarded_retro` — the
same one the alkene and alkyne families ride (dalembert's "one enforcement point" discipline, now paying off: a
third and fourth family reuse it with zero copy). `_reactant_hetero_da_disconnects_to(family, …)` re-derives
DA-ness from the reactant alone; its cheap pre-filter is the all-carbon one with the carbon floor dropped to
**5** (a hetero adduct ring is 5 C + 1 heteroatom, not 6 C) and a `hetero_label ∈ atoms` early-out added — all
four conditions identity-preserving.

Because the all-carbon families' rule/guard code is untouched, their frozen probes (`a0e61e51…` alkene,
`cbf19625…` alkyne) are **unchanged** — the byte-identity proof.

## 3. One generic edge + provider + two oracle recognizers

`HeteroDielsAlderEdge` is a single generic frozen dataclass serving **both** hetero families (they differ only by
the one relabeled vertex). It carries its `family` descriptor as a `field(compare=False, repr=False)`, so the
descriptor is **excluded from the content digest and from equality** (`contracts.canonical_payload` digests only
fields where `not name.startswith("_") and field.compare`). This is sound because an aza edge and an oxa edge are
already distinguished by their differing `schema_version` / `reaction_class` / `reactant` / `products` — the
digest stays a pure function of the chemistry (verified: aza and oxa edges have distinct, stable digests). The
same double certificate as the all-carbon edges runs at construction: (1) mass+charge conservation via a real
`Reaction`, (2) family-specific DA-ness re-derivation. `HeteroDielsAlderProvider` is generic (identity fields read
from the `family`); `AzaDielsAlderProvider` / `OxaDielsAlderProvider` are thin frozen-dataclass instances. Both
opt-in (absent from `DEFAULT_TRANSFORM_REGISTRY`).

The oracle recognizers `_aza_diels_alder` / `_oxa_diels_alder` (the **6th** and **7th** active classes, the first
heteroatom pericyclic recognizers) delegate to a shared `_hetero_diels_alder(step, family)` with the exact
three-layer discipline of `_diels_alder`: **Layer A** re-derives this family's guarded retro from the step's own
molecules (the soundness gate), **Layer B** pins `center == family.center`, **Layer C** fail-closes on an absent
centre.

## 4. The #83 valence precondition becomes LOAD-BEARING

Until now the charge-agnostic valence ceiling (`valence_sane`, #83) only ever caught pentavalent carbon — no
in-scope atom but C existed. With heteroatoms in scope it becomes **load-bearing**: a ring O at coordination 4 is
impossible in every charge state (ceiling 3) and is refused; a 3-coordinate ring N is legitimate (ceiling 5) and
admitted. The precondition the DA round surfaced and the #83 round closed is the exact gate the hetero families
now lean on (`test_the_valence_ceiling_now_gates_ring_heteroatoms`).

## 5. The four-family disjointness

The four DA families (alkene X=C, alkyne, aza X=N, oxa X=O) are **mutually disjoint**, on two independent grounds:

1. **Distinct reaction centres.** Each centre is `_synthesis_center(forward)` over labels `(C,C,C,C,C,X)`. The
   hetero centres carry `(C, N, ·)` (aza) / `(C, O, ·)` (oxa) bond pairs that no all-carbon centre carries, and
   the alkyne centre carries a `(C,C,3)` broken triple. All four are distinct multisets
   (`test_the_four_da_centres_are_all_distinct`), so the oracle's exact-equality Layer B separates them.
2. **The kernel label lock.** A family's rule embeds only into a target whose matched vertices carry its exact
   label multiset, so no family's rule matches another family's adduct (verified both directions, and against the
   all-carbon rings). Neither enumeration nor the oracle can cross-poach.

## 6. Boundaries (honest)

- **Structural type-validity only (Problem A)**: a vouch means "a structurally valid hetero-[4+2] disconnection
  exists", never that the forward reaction is feasible, selective, or endo/exo-resolved. Many hetero-DAs want a
  Lewis-acid catalyst — that is **Problem B**, deferred, exactly as the acyl recognizer vouches an
  activator-requiring esterification.
- **Scope**: an imine (`C=N`) or carbonyl (`C=O`) dienophile + an all-carbon diene → the parent tetrahydropyridine
  / dihydropyran. A 1-aza-/2-aza-**diene** (heteroatom in the 4π component), a nitroso/azo/thiocarbonyl
  dienophile, or a heteroatom embedded in a larger conjugated system is genuine [4+2] chemistry these families do
  **not** cover — honest coverage loss (false-UNRECOGNIZED, safe), never a false-vouch.
- **Opt-in**: `DEFAULT_TRANSFORM_REGISTRY` unchanged; production behaviour byte-identical for non-opt-in users,
  and the default single-cut grammar cannot even reach a ring-forming 2→1 step.

## 7. Evidence

- `tests/test_hetero_diels_alder.py` (family: rule round-trip, positives, seam control, guards, opt-in,
  cross-poach, the DA-ness certificate, centre derivation + four-family distinctness, the valence ceiling) +
  additions to `tests/test_diels_alder_oracle.py` (aza/oxa vouched, the 4×4 cross-poach matrix, hetero Layer A/C)
  + `experiments/hetero_diels_alder_family_probe.py` (frozen `content_hash` `de854e45…`) +
  `tests/test_hetero_diels_alder_family_probe.py`.
- Alkene + alkyne family byte-equivalence pinned by their **unchanged** frozen probe hashes.

## 8. Adversary gate (run SEPARATELY from acceptance — the meta-lesson, now 9 rounds)

Both adversaries — evil-morty (directed) and dalembert (structure-theorem) — ran on the hetero families + their
oracle recognizers, **separately from acceptance**, and **independently landed the same kill**. Acceptance's tests
(then 45 green) missed it. This is the meta-lesson holding a 9th straight round.

### 8.1 The kill — the oxocarbenium/iminium neutral-valence false-VOUCH (FIXED, guard 2c)

**The structure theorem (dalembert).** In the adduct the matched dienophile heteroatom `X5` carries two ring
single bonds plus `e` exocyclic single bonds → bond-order `2 + e`; the retro breaks one ring bond and lifts the
other to a double, so the emitted fragment's `X` is again bond-order `2 + e`. `valence_sane` (#83) admits it iff
`2 + e ≤ ceiling[X]` — the **charge-agnostic** ceiling. But the fragment is a real *neutral* dienophile only when
`2 + e ≤` its **neutral** valence. The gap `ceiling − neutral` is the leak:

| element | neutral valence | charge-agnostic ceiling | gap | leaks at |
|---|---|---|---|---|
| C | 4 | 4 | **0** | never (immune) |
| N | 3 | 5 | 2 | `e ≥ 2` (bond-order 4 = iminium) |
| O | 2 | 3 | 1 | `e ≥ 1` (bond-order 3 = oxocarbenium) |

So a dihydropyran with an exocyclic `O-CH3` (ring O at bond-order 3) retro'd to an **oxocarbenium** `C-O⁺=C`
drawn neutral, and the oracle **vouched** it as an oxa-DA — demonstrated end-to-end through the recognizer, the
opt-in provider, and the edge's double certificate (the aza analogue: an N,N-disubstituted ring N at bond-order 4
= an **iminium**). A **TYPE** false-vouch (the "carbonyl dienophile" is really a cation), the catastrophic
direction the arch forbids ("a verifier that cannot verify must fail closed"). **Guard 2b's justification silently
assumed carbon** — it bounds bond *order*, not the *count* of exocyclic single bonds, and for carbon the ceiling
equals the neutral valence so the distinction never mattered; the relabel to N/O made `valence_sane`'s
charge-blindness (a documented #83 boundary) load-bearing *and* leaky for the first time.

**Honest boundary of the kill.** The triggering input is a net-neutral graph whose heteroatom exceeds its neutral
valence but not its charge-agnostic ceiling — i.e. a charge-separated ion (oxonium/ammonium) missing its
counter-charge. It is **not reachable from the string parser** (which assigns per-atom formal charge; a charged
molecule is refused upstream by `_joined`), only from a hand-built `Molecule` graph or a hypothetical future
net-neutral charged-species provider. Both adversaries agreed on reachability; they diverged only on severity
(evil-morty: LOW/disclosed-boundary; dalembert: KILLED/close-it). **Disposition: FIXED**, because the recognizer
runs in the production hot path, the fix is cheap and zero-loss, and leaving a known false-vouch in a soundness
gate contradicts the whole fail-closed arch.

**The fix — guard 2c (`_NEUTRAL_VALENCE`).** Bound every matched centre atom by its NEUTRAL valence
(`{C:4, N:3, O:2}`), not the charge-agnostic ceiling. It is a **strict no-op for carbon** (4 == 4, so the
all-carbon families' frozen probes are byte-identical — verified `a0e61e51…`, `cbf19625…` unchanged), and for a
heteroatom it drops exactly the over-neutral-valence fiction while KEEPING every real neutral centre: an ether O
stays bond-order 2, and an **N-substituted** tetrahydropyridine N stays bond-order 3 (so an N-methyl aza-DA, from
`CH3-N=CH2` + butadiene, still vouches — verified). Regression-pinned in `tests/test_hetero_diels_alder.py`.

### 8.2 Survivals (attacked, bounded)

- **Cross-poach / disjointness** — SURVIVED. The four DA recognizers give a clean diagonal (verified matrix): each
  step vouches only its own class. Label lock + distinct heteroatom-bearing centres. Boundary: proven on the
  parent adducts + the label-lock argument, not an enumerative sweep of mixed N/O bicyclics.
- **Digest / identity (`family` = `compare=False`)** — SURVIVED, design confirmed correct. `schema_version` and
  `reaction_class` are read from the family and validated in `__post_init__`, so they pin the family; two edges
  can't share `(schema, class, reactant, products)` yet differ in `family`. Distinct chemistry → distinct digest;
  identical chemistry → identical digest (a pure function of the chemistry). Boundary: not fuzzed across
  serialization round-trips.
- **Pre-filter floor (`<5` C + `hetero_label ∈ atoms`)** — SURVIVED as a cheap identity-preserving filter (can
  only add enumeration work, never mint a vouch); it is not the false-vouch culprit (the guard layer was).
- **Provider shape** — SURVIVED. The frozen-dataclass provider over the non-dataclass `TransformProvider` base
  does not field-capture the base's bare annotations; `provider_id`/`witness_kind` properties read cleanly;
  instances hash; `registry.digest` / `search_algebra_digest` compute; duplicate-id detection fires. `DEFAULT`
  registry unmoved (both providers opt-in).
- **Regression** — none (65 shipped-suite pass at review time; 92 across the full DA set after the fix).

**Residual (non-actionable, disclosed).** The guard-2c fix closes the guard-level leak; the deeper information-
theoretic boundary — the graph carries only NET charge, not per-atom formal charge (#83) — is unchanged and
disclosed. Neither adversary fuzzed the neutral 5C+1X ring space exhaustively (a generative fuzzer would upgrade
"could not break" to "proven clean"), nor round-tripped a hetero step through the serialized replay payload (the
all-carbon path does; the hetero edge reuses it).
