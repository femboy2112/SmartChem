# Poor-man ingenuity — the etherification recognizer (R57)

> **Canonical record for ROUND 57 of the poor-man ingenuity arch.** The reaction-TYPE oracle grows its positive
> whitelist by a SECOND conservation-locked class — dehydrative etherification — under the same admission gate that
> shipped acyl condensation at R56. Sound at the production config, non-vacuous (serves dimethyl ether), and
> different-in-kind from the R49–R55 escape #7. Probe `experiments/poor_man_etherification_recognizer_probe.py`
> (FROZEN_HASH `83d71b0d4ca8aadca6c9658eabb8145265f6234669504dc6b1727ed59f0c98ab`); tests
> `tests/test_poor_man_etherification_recognizer.py`.

## The steer, and the honest answer

The live R57 steer: *"are we hard-coding chemistry, or hard-coding the RULES of chemistry and letting the chemistry
itself drop out? let the category theory do the heavy lifting."*

R56's acyl recognizer is a hand-coded census — one detector per class. Growing the whitelist that way is a lookup
table that scales with human labor and collides at boundaries. The steer asks whether the recognizer *set* can be
DERIVED from a small set of categorical/algebraic rules so soundness drops out of structure.

A recon + 5-adversary design gate (workflow `w9mbf48ua`), then reproduced against the filesystem by the author,
returned **SCOPED_BUILD** with a sharp finding:

- **The categorical-from-scratch route is a cathedral this round.** There is **no span/DPO rule-algebra** in the
  tree to derive recognizers from — only port-gluing pushouts (`open_core.py:276,343`, `open_chem_diagram.py:468`);
  `transform_registry.py` is a provenance *digest* over an *imperative* grammar, not an enumerable rule table. Per
  the gate (Birdperson), a "span registry" would merely RELOCATE the escape-#7 collision into "which predicate
  populates L" with zero new discriminating power. So the literal "recognizer set drops out of category theory" is
  not achievable without building new scaffolding that must earn a consumer.
- **But the categorical rewrite already exists per-step and is discarded.** The generator computes each step as a
  `CappedScission` — a valence-certified span with `cut` (bonds broken) and `caps` (bonds formed) in one joined
  index space (`structure_descent.py:552`). `ExperimentStep.from_transform` (`step.py:237`) rebuilds the step from
  only `reactant`/`reagents`/`products` and **throws the span away**. Reading it is the genuine structural fix.
- **That fix is a spine change, not a scoped add**, so it is its own round (**R58**, below): the step digest is
  derived from *all* dataclass fields (`contracts.py:152`), so a new field bumps `step-v1` and cascades into
  route/DAG/compilation-IR digests + every frozen fixture; and the replay payload has fixed fields
  (`service.py` `_STEP_PAYLOAD_FIELDS`), so a threaded span would not survive serialization — a recognizer that
  *required* it would vouch a route live but demote it on recompile.

**R57 therefore ships the etherification recognizer at the step level — sound at the production config (k=1) — at the
same bar the shipped acyl recognizer already meets.** The structural payoff is scoped and named (R58).

## The recognizer, and its conservation-lock (three clauses)

`smartchem/experiment/feasibility._is_intermolecular_etherification(step)` fires iff the **elementary intermolecular
shape** holds (exactly 2 non-water reactants → exactly 1 non-water product, water net-produced) **and** all three:

| clause | encodes | the fake it demotes |
|---|---|---|
| net dialkyl (sp3 C–O–C) ether-O **formed** | a real ether bond is created | aryl-ether fake `phenol + methanol → anisole + water` — anisole's ether-O has an **aromatic** neighbour (not a dialkyl ether) |
| net sp3 alcohol **consumed** | the ether is built *from alcohols* | peroxide-coupling fake `EtOOH + ethane → Et₂O + water` — a hydroperoxide O–O–H is **not** an alcohol, so none is consumed |
| **no** ether-O among the reactants | a dehydrative etherification does not reuse an ether | bundled non-local fiction `glycol + DME → dimethoxyethane + water` — REUSES a reactant ether (d'Alembert's demonstrated kill) |

The census is representation-robust (heavy-neighbour only, no explicit-H dependence, mirroring `_acyl_group_counts`).
An `sp3 non-aromatic carbon` is a carbon all of whose bonds are order 1 — which, on the codebase's **kekulized**
aromatics, excludes aromatic ring carbons (they carry an order-2 bond) and carbonyl carbons (their C=O) for free, so
an ester's `-O-` is never miscounted as an ether.

## Why this is NOT escape #7

Escape #7 (R49–R55, six defers) was a bounded-radius local decision function `valid = g(f(step))` CARRYING an
unbounded property; it collided at every polarity/alphabet. This recognizer is a **positive whitelist** entry whose
unbounded-ness surfaces as **coverage loss** (a real-but-unregistered etherification is demoted-as-unrecognized),
**never a false-VOUCH**. Within the elementary shape, the three clauses make a fired step FORCED onto a real
etherification — a formula-conserving fake cannot share the full signature (each adversarial fake fails a distinct
clause).

## The consumer, and the soundness numbers (author-verified against the filesystem)

- **Consumer served:** `dimethyl ether` (`2 methanol → dimethyl ether + water`) was demoted-as-unrecognized before
  R57; it is now VOUCHED as etherification and clears the `route_reaction_type_blockers → service._affordability_frontier`
  hard-blocker site. One live, non-vacuous consumer (honestly reported as exactly one — modest ROI, clears the
  zero-call-sites bar).
- **Sound:** 0 false-VOUCH across the whole production frontier; the isopentyl-acetate C-C fictions stay demoted.
- **Non-vacuous:** dimethyl ether joins the genuine reals (`reals_vouched` 4 → 5 in the whole-oracle measurement;
  the R56 probe is re-frozen `98cceeeb → fc8fea1e` to record this legitimate supersession).
- **Escape #7 stays shut:** caffeine (N-methylation) is still demoted; a general N-alkylation recognizer collides
  (Bucherer: aromatic C–OH + N–H → C–N + water is a real named reaction, so the sp3 restriction is not
  formula-forced) — the R45 caffeine win remains honest coverage loss, recoverable only behind a class-specific
  conservation-locked N-alkylation recognizer.

## Design-gate folds honored

1. The conservation-lock proof rests on its **true** hypotheses (the three clauses + the k=1 locality assumption),
   not the false "two-alcohol impossibility" lemma evil-morty refuted; proof landed before code (test-first).
2. The predicate is **two-sided** (net alcohol consumed AND net ether formed) — dropping the alcohol half would
   false-VOUCH the peroxide coupling.
3. The **k=1 locality** debt (shared with acyl) is documented, not faked-guarded; the reactant-ether clause demotes
   the specific glycol+DME bundle even at k≥2; general config-robustness is the R58 span-reading fix.
4. Adversarial MUST-DEMOTE cases pinned beyond the isopentyl case: peroxide, anisole, glycol+DME.
5. The non-aromatic-carbon clause is included so the anisole fake is demoted.
6. The consumer is reported honestly as exactly one live route (dimethyl ether).
7. Escape #7 stays shut — no N-alkylation / caffeine recovery this round.

## R58 — the span-reading root fix (precisely scoped, not this round)

Carry the generator's already-computed span (`CappedScission.cut`/`.caps`) onto `ExperimentStep` and re-target BOTH
recognizers to a boundary-LOCAL census over the reaction center. This:

- makes the k=1 locality a **checked** structural fact (a bundled multi-cut step has >1 cut bond → demoted), so
  BOTH acyl and etherification become config-robust;
- is the genuine "let the structure do the heavy lifting" — the reaction center (the local rewrite) drops out of
  the span the generator already built, instead of being reconstructed by a whole-molecule count.

Its blast radius (why it is its own round): bump `step-v1 → step-v2`; serialize the reaction center through the
replay payload; regenerate step/route/DAG/compilation-IR digests + golden fixtures; prove live == replay.
