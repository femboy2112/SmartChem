# Rule-calculus valence precondition (v0.1)

Closes the valence **fail-OPEN** dalembert surfaced during the Diels-Alder round: the domain-neutral
kernel and `Molecule` *deliberately* do not enforce chemical valence, so a valence-impossible neutral
species (e.g. a pentavalent carbon) was silently processed by the rule-calculus providers. Opt-in-neutral,
additive; it touches no default registry, no ranking, and no production oracle.

## 1. The fail-open (dalembert, from the DA round)

- `smartchem/category.py` `Molecule.__post_init__` enforces composition, total charge, connectivity, and
  one-bond-per-pair — **but no valence**. This is documented as intentional (the labels are domain-neutral,
  so valence belongs in a chemistry-specific validator).
- The kernel (`rule_calculus.py`) is likewise valence-agnostic: `Edge` and `Bond` cap bond order only at
  `order >= 1` (no upper bound), and the kernel's own tests use opaque labels (`"X"`/`"Y"`/`"H"`).
- Consequence: `Molecule(("C","F","F","F","F","F"), {C-F ×5})` — a pentavalent carbon — constructs and is
  processed. The SMILES parser has a partial valence check (`_fill_hydrogens`), but it is organic-implicit-H
  only and is bypassed by bracket atoms, and nothing re-checks at the Molecule / kernel layer.

## 2. Why the check belongs at the chemistry-aware seam, not the kernel

The kernel is contractually **valence-agnostic and opaque-label**: a valence gate there would be a category
error and would break the kernel's own opaque-label tests. The right home is the chemistry-aware adapter
`rule_calculus_bridge._joined` (Molecule → `BondGraph`), which every rule-calculus provider — the audited
capped-scission provider, the Diels-Alder provider, and any future family — already flows through, and whose
existing contract is exactly *"refuse a species we cannot soundly transport."* Valence-impossible is such a
species.

## 3. A charge-agnostic ceiling (why not the parser's neutral table) + source-side sufficiency

The first cut reused the parser's `smiles._VALENCES` (OpenSMILES implicit-H defaults) as the bound. The
adversary gate refuted that:

- It is the wrong table for a physical-impossibility bound (evil-morty): `_VALENCES` lists the halogens at
  valence 1, so it **false-rejects** real hypervalent-iodine oxidants (PhI(OAc)₂ / Dess-Martin / IBX), IF5,
  chloric acid, BrF3.
- A neutral-max rule is **charge-blind** (dalembert): the graph carries only *net* molecular charge, never
  per-atom formal charge, so a net-neutral *charge-separated* species is graph-identical to an impossible
  neutral. **Carbon monoxide** `[C-]#[O+]` (O at degree 3, in seven test files) and ozone are then
  false-rejected. And a *ceiling*, not membership, still admits the interior-gap neutrals (neutral NH4 at
  N=4) — but closing those needs the per-atom charge the graph does not carry.

So the bound is `_MAX_COORDINATION` — the maximum coordination each element reaches in **any** accessible
charge state (`O=3` as O⁺, `B=4` as borate, `Cl/Br/I=7` as perchlorate/periodate, `C=4`, `N=5`, `S=6`,
`P=6`). The gate refuses only a valence impossible in **every** charge state (pentavalent carbon, hexavalent
oxygen) — the actual fail-open — with **zero** false-rejects of real chemistry.

**Source-side sufficiency (certified by dalembert).** `BondRule.__post_init__` locks
`left.degrees == right.degrees` (`rule_calculus.py:133`): a rewrite can never change any atom's total bond
order, so a valence-insane *product* can only arise from a valence-insane *source*, and a single precondition
on the joined source graph is sufficient — the products need no separate check.

## 4. The gate

`valence_sane(graph: BondGraph) -> bool` (in `rule_calculus_bridge.py`): for each vertex, if the element is in
`_MAX_COORDINATION` and `degree` exceeds its ceiling, the graph is insane. Untabulated / opaque labels pass
(unconstrained — we impose no ceiling we cannot source). Wired fail-closed, each in its module's existing idiom:

- `_joined` **raises `RuleError`** on an insane join — so the audited capped-scission provider surfaces a
  `ScissionError` (its refuse-what-it-cannot-transport idiom) and the Diels-Alder provider, whose contract is
  never-raise, catches it and enumerates nothing (`((), True)`).
- `retro_da_disconnections` (the reusable DA core, also called directly on hand-built `BondGraph`s) returns
  `((), True)` for an insane target — a valence-impossible molecule has no valid chemistry, definitively.

Fail-closed throughout: an insane input is **dropped/refused** (coverage loss), never coerced into a witness.

## 5. Boundaries (honest — this is a ceiling, not a full valence validator)

- **Charge-blindness (the information-theoretic boundary).** The bound is charge-agnostic, so a species
  impossible only *as a neutral* but valid as an ion — a hand-built neutral ammonium (N=4), phosphonium (P=4),
  sulfonium (S=3) — is **admitted**. Distinguishing it from a real net-neutral charge-separated molecule (CO)
  needs per-atom formal charge, which neither `BondGraph` nor `Molecule` carries. These species do not arise
  from the parser (it assigns the charge, which is refused upstream), so this is a disclosed boundary, not a
  production hole. Pinned in the tests so any future "we close this too" must first supply the missing datum.
- **Organic subset + halogens only.** An untabulated element (a metal, Se, Si, …) carries no sourced ceiling
  and passes unconstrained. The finding dalembert raised — pentavalent **carbon** — is inside the bound and
  is closed.
- **Charged species are refused upstream**, before valence (`_joined` / the DA provider reject `charge != 0`).
- This is a valence-**ceiling** precondition, not a full cheminformatics valence model. It is a strict,
  regression-free improvement over the prior no-check baseline (it catches impossible-in-any-state valences
  that were silently processed); it is not a claim of complete valence validation.

## 6. Evidence

- `tests/test_valence_precondition.py` — the acceptance pins: table single-source-of-truth, opaque/untabulated
  pass, impossible rejected, real hypervalents accepted, the O-in-ring landmine not false-rejected, both seams
  fail-closed, and the parent DA unaffected.
- `experiments/valence_precondition_probe.py` (frozen `content_hash`) + `tests/test_valence_precondition_probe.py`.

## 7. Adversary gate (run SEPARATELY from acceptance — the meta-lesson)

Both adversaries ran on the first cut (the `_VALENCES`-based neutral-max rule) and forced the redesign above.

- **evil-morty — KILL 1 (false-reject, moderate, FIXED):** the OpenSMILES table lists Cl/Br/I at valence 1,
  so the neutral-max rule false-rejected hypervalent-iodine oxidants (PhI(OAc)₂ / Dess-Martin / IBX), IF5,
  chloric acid, BrF3 — real neutral chemistry central to the oxidation lane. Fixed by the charge-agnostic
  ceiling (halogens = 7). evil-morty also certified: the `-1` aromatic sentinel cannot reach `valence_sane`;
  charged hypervalents are refused upstream; degree-double-counting is impossible; **source-side sufficiency
  holds**; and there is **no false-VOUCH** through the production `_joined` seam.
- **dalembert — REFUTED the naive rule twice (FIXED / disclosed):** (a) *completeness* — a MAX is not
  membership, so interior-gap neutrals (neutral NH4/PH4/SH3/SH5) passed; and (b) *false-reject* — the rule
  was charge-blind, so net-neutral **carbon monoxide** and ozone were hard-refused (a real bite through the
  audited provider). The charge-agnostic ceiling closes (b) entirely (CO/ozone pass). (a) is
  information-theoretically unclosable without per-atom formal charge (which the graph lacks) and is now a
  disclosed, pinned boundary (§5), not a claimed close. dalembert **certified source-side sufficiency** sound.

Both kills are pinned as regressions in `tests/test_valence_precondition.py` and the frozen probe.
