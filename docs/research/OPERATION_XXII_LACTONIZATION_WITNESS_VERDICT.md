# OPERATION XXII §8 — the lactonization witness dispute, resolved; the 1.6 release verdict

**Status:** 1.6 candidate (`feat/1.6-candidate-xxii`, off `main` = v1.5.0 research merge `9d04894`). This dossier
resolves the witness/recognizer disagreement by independent chemical graph reasoning (NOT by making them agree) and
renders the 1.6 go/no-go verdict against the directive's acceptance gates.

## The disagreement

`candidate/1.6-lactonization-witness` ships an **independent** structural witness (`smartchem.lactonization_witness`,
AST-audited to reference no production recognizer symbol). It agrees with the production 25th-class recognizer on
genuine hydroxy-acid → lactone pairs, and records ONE deliberate divergence:

- **Precursor** `OC(=O)CCC(O)O` = HOOC–CH₂–CH₂–**CH(OH)₂** — a carboxylic acid whose far carbon is a **gem-diol**
  (the hydrate of an aldehyde, i.e. a **masked carbonyl**; this is succinic-semialdehyde acid in its hydrated form).
- **Target** `O=C1CCC(O)O1` — a 5-membered ring with a C(=O)–O linkage whose **alkoxy carbon also bears an –OH**.
- **Witness:** `is_lactonization = True`. **Production recognizer (with the dalembert XV-P8 carbinol guard):** refuses,
  emits no edge.

## Resolution (independent graph reasoning + primary definition)

Both verdicts are correct **in their own domain**; they answer different questions, and the oracle's domain is the
binding one:

1. **Is the target a lactone?** By the primary definition (IUPAC: a lactone is a cyclic ester — a ring containing the
   –C(=O)–O– linkage), the target's ring **does** contain a genuine C(=O)–O linkage (C1 is the acyl carbon, bonded to
   the ring oxygen). So *structurally it is a lactone*, a 5-hydroxy (lactol-) lactone. **The witness is right** that
   the target is a lactone.

2. **Is the transformation a *carbinol lactonization* the reaction-type oracle should VOUCH?** No. Trace the atoms: the
   ring-closing oxygen that becomes the ester alkoxy sits on the **gem-diol (masked-carbonyl) carbon**. Mechanistically
   the carboxyl oxygen adds across that masked carbonyl — a **lactol / hemiorthoester formation** — which is the
   *opposite* nucleophile/electrophile assignment from a carbinol→carboxyl esterification (where a genuine alkyl
   carbinol oxygen attacks the carboxyl carbon). The product is a 1-acyloxy-1-hydroxy carbon (an acylated gem-diol
   hydroxyl), the kind of species in equilibrium with the open hydroxy-aldehyde-acid, not an isolable carbinol lactone.
   **The recognizer is right to refuse the VOUCH:** its carbinol guard (`_alkyl_carbinol_alcohol_count`) exists
   precisely because a hemiaminal / gem-diol / hemiacetal posed as an alcohol is a masked carbonyl, and vouching it
   would mis-class a lactol formation as a lactonization — the exact dalembert KILL 1 hazard.

**Verdict:** the production oracle's declared domain is **reaction-class recognition with fail-closed
positive-whitelist semantics** (coverage-loss-never-false-VOUCH). In that domain the recognizer's refusal is the
**correct** behaviour, and adopting the witness's structural "True" as the oracle verdict would be a **false-VOUCH** of
a lactol formation. The divergence is therefore a real, informative **domain boundary** — *structural lactone* (witness)
vs *carbinol-lactonization reaction* (oracle) — and it is recorded as such, **not** erased by forcing the two to agree.
The witness keeps its independent value: it genuinely cross-checks the oracle on bona-fide lactonizations and flags the
lactol-lactone boundary where a human should (and now can) look.

## 1.6 acceptance (directive §8) — status on this candidate

| Gate | Status |
|---|---|
| No demonstrated false-VOUCH in supported classes | the carbinol guard closes the masked-carbonyl false-VOUCH; lactonization corpus + guard tests pass (67) |
| Independent recognition route tested | witness cross-check runs **live** against the present recognizer (agrees on genuine pairs; diverges only at the resolved boundary) |
| Generator/recognizer common-mode repaired or demoted | witness imports only `Molecule`, AST-audited independent; divergence documented, not papered over |
| Registry count exactly 25 | **verified: `len(_RECOGNIZERS) == 25`** |
| No undeclared legacy-semantic change / frozen fingerprints valid | version-transition + public-contract tests pass (11); recognizer moves count/readiness, not the frozen semantic digest (MINOR boundary) |
| Correct `__version__` transition | **1.5.0 → 1.6.0** (MINOR: one new recognizer) |
| No unresolved P0 classification error | the witness dispute is resolved above in favour of the guard |
| Full core suite + hosted CI green | **gating** — full production suite + hosted CI on the exact head must be green job-level before any merge |
| Source + compatibility dossier; maintainer-ready changelog | this dossier + the 1.6 CHANGELOG entry |

**Rule honoured:** if any gate fails, the candidate stays on `feat/1.6-candidate-xxii` and production **retains 1.5.0**
(directive §8). The version bump + mainline merge happen only once every gate above is green; no tag or GitHub Release
is made (that needs separate authorization).
