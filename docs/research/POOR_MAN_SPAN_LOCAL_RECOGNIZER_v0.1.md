# Poor-man ingenuity — the span-local recognizer (R58)

> **Canonical record for ROUND 58 of the poor-man ingenuity arch.** The reaction-TYPE oracle stops inferring a
> reaction from a whole-molecule count and starts reading the actual rewrite MORPHISM the generator already
> computes. The generator's `CappedScission` span (`cut` = bonds broken, `caps` = bonds formed) is distilled into a
> coordinate-free `ReactionCenter`, carried on the step, serialized through replay, and read by both recognizers to
> confirm the reaction centre is a single connected elementary condensation. This closes the R56/R57 k=1 locality
> debt with a CHECKED structural fact and retires a hand-enumerated blacklist clause. Probe
> `experiments/poor_man_span_local_recognizer_probe.py` (FROZEN_HASH
> `5f0be063224819d53547d8d9d0cecd4bd33eb80e34fe220fd47202b8d1e25c8f`); tests
> `tests/test_poor_man_span_local_recognizer.py`.

## The steer, and the answer with teeth

The standing steer: *"are we hard-coding chemistry, or hard-coding the RULES of chemistry and letting the chemistry
itself drop out? let the category theory do the heavy lifting."*

R57 named R58 as the genuine structural fix and shipped etherification at the step level with a documented k=1
locality debt. R58 pays that debt by reading the categorical rewrite. The concrete "chemistry drops out" win: R57's
etherification recognizer carried a **hand-enumerated whole-molecule blacklist clause** — *"no ether among the
reactants"* (clause iii) — to sink one bundled fiction. That clause is the R53 anti-pattern
([[a-fail-closed-guard-is-a-blacklist-of-an-unbounded-hazard-space]]) and it is non-local: it FALSE-DEMOTES a
genuine etherification whose reactant merely *contains* an unrelated ether. R58 **deletes clause (iii)** for
centre-carrying steps and lets the actual rewrite span decide.

## What the filesystem said (recon, reproduced by the author)

- **The span already exists and was discarded.** `CappedScission` (`structure_descent.py:552`) records `cut`/`caps`
  as `Bond`s in the joined reactant+reagents index space, valence-certified atom-by-atom; `products` are derived.
  `ExperimentStep.from_transform` (`step.py`) rebuilt the step from the multisets alone and threw the span away.
- **The anticipated `step-v1` bump was AVOIDABLE.** R57 predicted a schema bump + fixture cascade because the step
  digest is derived from *all* dataclass fields (`contracts.py:146`). But `canonical_payload` skips any field with
  `compare=False`. Declaring the new `reaction_center` field `compare=False` makes it **digest-invisible**: a step
  with a centre and its centre-less twin share one digest, one hash, one equality — so **no `step-v1` bump, no
  golden-fixture regen**. The digest machinery already carries non-identity provenance; R58 relocates onto that
  hatch rather than reinventing a schema version.
- **The join indices do not survive canonicalization**, so the raw span cannot be serialized. R58 distils it to a
  COORDINATE-FREE descriptor — the multiset of formed/broken bond element-kinds `(element, element, order)` plus the
  number of connected components of the changed-bond graph — which round-trips through the replay payload as element
  strings and small ints with no coordinate reconstruction. Live and replayed steps read identically.

## The reaction centre, from the generator's own spans (instrument-first)

Every elementary dehydrative condensation has one invariant reaction-centre signature, verified by dumping real
`CappedScission`s (synthesis direction; `formed` = the scission's `cut`, `broken` = its `caps`):

| class | FORMED | BROKEN | components |
|---|---|---|---|
| esterification / etherification (X=O) | `{C-O, O-H}` | `{C-O, O-H}` | 1 |
| amidation (X=N) | `{C-N, O-H}` | `{C-O, N-H}` | 1 |
| thioesterification (X=S) | `{C-S, O-H}` | `{C-O, S-H}` | 1 |

`ReactionCenter.is_elementary_condensation(nucleophiles)` returns true iff the centre is exactly this shape for some
`X` in `nucleophiles` **and** `n_components == 1`. Etherification passes `("O",)`; the acyl family passes
`("O","N","S")`. Ether and ester share a centre signature — the functional-group census (carbonyl vs sp3)
disambiguates the class, the span supplies the elementarity the census cannot see locally. A bundled multi-cut step
forms or breaks extra bonds, or splits into more than one component, and is rejected.

## Two measured consumers (this is not verdict-neutral hardening)

1. **Coverage (production, k=1).** `methanol + 2-methoxyethanol → 1,2-dimethoxyethane + water` is a genuine
   etherification the R57 clause (iii) sank because a spectator methoxy is present. R58 recovers it and its class:
   **48 reachable k=1 steps** over the probe library, every one a real single condensation by its span, **0 lost**.
2. **Soundness (config-robustness, k≥2).** A bundled multi-cut step forges the same net group signature as an
   elementary reaction (`THF + 2 water → ethane + a triol` for ether; **48 measured bundles** for acyl). The
   whole-molecule census FALSE-VOUCHES them; the span reads a non-elementary centre (extra bonds, or >1 component)
   and demotes them. The borrowed `max_reactant_cuts = 1` assumption becomes a CHECKED fact.

The acyl recognizer is **verdict-neutral at k=1** (measured 0 recovered / 0 lost; ester/amide/thioester all still
vouched) and gains the config-robust soundness above — the span gate accepts the whole acyl family and demotes only
bundles.

## Architecture (what changed, and what deliberately did not)

- **New** `smartchem/reaction_center.py` — the coordinate-free `ReactionCenter` (stdlib-only; no import cycles).
- `CappedScission.reaction_center()` builds it from `cut`/`caps` + the joined atom elements + a union-find component
  count.
- `ExperimentStep` gains a `reaction_center` field (`compare=False`, default `None`); `from_transform` carries it by
  duck-typing (`transform.reaction_center()` when present — a non-scission transform, e.g. redox, yields `None`).
- The feasibility predicates `_is_intermolecular_acyl_condensation` / `_is_intermolecular_etherification` are
  **UNCHANGED** (the acyl one is the feasibility DOMAIN GUARD; the ether one is the span-absent fallback and the R57
  pins). The R58 logic lives only in the fail-closed oracle: a centre-carrying step is additionally gated on
  `is_elementary_condensation`, and the ether path drops clause (iii); a centre-less step falls back to the R57
  whole-molecule predicate (sound at k=1).
- `service.py` serializes `reaction_center` as an OPTIONAL replay-payload field (absent → a centre-less step), so
  older envelopes still reconstruct and centre-less steps' payload bytes are unchanged.

## Boundaries carried as documented debt

- **Span-absent steps** (hand-built, or a non-scission transform family) fall back to the whole-molecule census —
  sound at k=1, and the only production steps lacking a centre are none (every generator-derived step carries one).
- **Class identity is still a whole-molecule census.** Given an elementary (single-centre) span the net count is
  local — only one centre exists to reflect — so this is sound; a future round could read the class from the
  centre's local environment (sp3 vs carbonyl) directly, but that needs a richer descriptor and has no consumer yet.
- **The whitelist is still two classes.** R58 hardens both; it does not add a class. Caffeine N-methylation still
  awaits a class-specific recognizer (a general N-alkylation collides — Bucherer); it stays demoted (escape #7 shut).

## Verdict

R58 makes the reaction-TYPE oracle read the actual rewrite morphism. It serves a production coverage consumer
(recovers spectator-ether etherifications, retires clause iii), stays sound on the frontier (0 false-VOUCH), demotes
reachable k≥2 bundled census-false-vouches (config-robust), round-trips identically through replay while never
changing step identity, and leaves acyl unregressed. The chemistry dropped out: a hand-enumerated blacklist is gone,
replaced by the categorical rewrite the generator was already computing.
