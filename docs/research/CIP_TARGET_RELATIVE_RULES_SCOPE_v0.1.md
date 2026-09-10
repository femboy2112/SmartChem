# CIP target-relative Rules 4b/4c — VERIFIED DEFER (item 1)

Status: **verified defer this round.** A sound target-relative Rules 4b/4c is a from-scratch build of the
hardest, most bug-prone stratum of CIP; it is NOT a bounded extension of the ROUND-35 auxiliary pass, and no
in-scope consumer forces it. This round ships the PROOF of the defer + a boundary demonstration, never a
fabricated comparator. Triangulated three ways: a direct code read + a design-recon bearing + a deep RDKit-source
research bearing (read `master` raw) — and confirmed empirically by an RDKit `rdCIPLabeler` existence sweep.

## Why it cannot be a bounded round (structure theorem — Verified)

The R35 second pass (`_cip_labels_by_atom`) draws `auxiliary` only from centres RESOLVED by the descriptor-free
Rules 1a–3, admits `len(auxiliary)==1` or exactly one opposed R/S pair, and never iterates. The canonical target
`O[C@H]1CC[C@@H](C)CC1` (RDKit → s,s; repo → ()) has BOTH stereocentres unresolved by Rules 1a–3, so both land in
`unresolved` and `auxiliary` is structurally **empty** `{}`. It fails the gate by CONSTRUCTION, not by a
threshold — there is no already-resolved descriptor to seed the bounded pass. Widening `len(auxiliary)` cannot
reach it. Closing it requires the architecture RDKit uses: a root-relative, distance-ordered recursive auxiliary
assignment (`labelAux` distance-batching) that re-roots each unresolved centre's digraph and resolves the mutual
dependency farthest-first.

The probe demonstrates this behaviourally, RDKit-free: the forcing target defers ALL centres (empty pool), a
symmetry-broken homolog of the same motif NAMES both centres, and a ring pseudoasymmetric centre with a **non-empty**
pool IS named by the bounded 4a/5 pass — so the wall is exactly the empty-pool mutual case the recursion exists for.

## Why a bounded hack would be UNSOUND (the missing Rule 4b — Verified from RDKit source)

The repo has NO genuine Rule 4b. `_cip_compare_rules45` is a faithful hand-port of RDKit's **Rule5New** (two
fixed references R & S; agree → ±1, opposed → ±2 pseudoasymmetry). Rule 4b is DIFFERENT: a like/unlike pass whose
REFERENCE is a per-branch nearest-non-empty-sphere MAJORITY VOTE of descriptors (IUPAC P-92.5.2.1; RDKit
`Rule4b::getReference`), held rigid for that branch's subtree and re-derived fresh per top-level comparison. A
special-case that names the target s,s WITHOUT genuine majority-vote 4b would silently diverge from RDKit wherever
the majority-vote reference matters and differs from the fixed-R/S trick — a MISLABEL, not mere incompleteness.
`[[a-sound-extension-guards-its-new-cross-comparisons]]`

## Why the honest scope is iterative, not closed-form (Verified from RDKit source)

RDKit treats auxiliary-descriptor assignment as an ITERATION-BUDGETED search (`maxRecursiveIterations`,
`MaxIterationsExceeded` → fail-closed UNKNOWN), NOT a closed-form bounded computation. `labelAux`
(`CIPLabeler.cpp`) scans every other Configuration, finds occurrences within the target's digraph, sorts
farthest-first, and resolves in distance-batches (each batch `setAux` before a nearer batch reads it). Termination
of farthest-first as a general well-founded order for depth > 1 mutual-dependency graphs is NOT proven in the
sources reached — a proof (or an oracle sweep standing in for it) is load-bearing and currently absent.

## No forcing consumer — the RDKit existence sweep (Observed, RDKit 2026.03.6)

A per-atom sweep against RDKit `rdCIPLabeler`, element-verified mapping:

- **North-star litmus targets are STEREOCENTER-FREE**: paracetamol, aspirin, Br₂/Cl₂/Br all give repo = RDKit =
  `{}` (no centres). 4b/4c is trivially irrelevant to both litmus tests.
- **Ten real chiral molecules** — menthol, camphor, glucopyranose, (2S,3S)- and meso-tartaric, threitol,
  ibuprofen, naproxen, nicotine, L-alanine, L-threonine — are named by the shipped rules on **every** centre,
  matching RDKit: **zero defers, zero mislabels**.
- **The forcing class is exactly the symmetric even-ring mutually-pseudoasymmetric case**: `O[C@H]1CC[C@@H](C)CC1`
  and `C[C@H]1CC[C@@H](C)CC1` → repo `{}`, RDKit `s,s` (lowercase pseudoasymmetric). Break the symmetry (5- or
  7-membered homolog) and the centres are resolved by Rules 1a–3, so the repo NAMES them (R,S), matching RDKit.
  The forcing class is synthetic, authored to probe the boundary.

The committed probe cross-checks 12 named centres against RDKit with **0 mismatches** and confirms both
forcing-class molecules are declined-yet-RDKit-named. This mirrors R32 (Rule 1b was a VERIFIED DEFER until IUPAC
P-9 supplied a consumer). `[[an-oracle-driven-existence-check-can-prove-a-defer]]`

## Phased build plan (when a real consumer appears)

1. Build genuine **Rule 4b**: the per-branch nearest-sphere majority-vote reference (`getReference`) + the
   like/unlike pairlist, as its own FIFO pass mirroring `_cip_compare_rule2/3`.
2. Build the **root-relative local-descriptor recursion** `_cip_local_descriptor(atom, parent, path, ...)` ranking
   ALL FOUR neighbours, memoized on **(atom_idx, parent_idx)** (atom_idx alone would alias a wrong-direction
   descriptor — a new-cross-comparison mislabel), distance-batched farthest-first + an iteration budget + a
   fail-closed cap.
3. Build **Rule 4c** (r < s) and settle Rule 5's interaction with 4b's tied-reference {R,S} fan-out.
4. **Oracle**: RDKit `rdCIPLabeler` (dev-venv-only) counterexample sweep — the mutual-pseudo ring class (5/6/7,
   substituent-swapped), same-handed auxiliary sets, nested depth > 1, a deliberate cache-aliasing case, and a
   non-transitivity fuzz through the new comparator.

## Boundary

- The s,s target result and the RDKit references are from RDKit 2026.03.6 (a dev-venv-only oracle, UNINSTALLED
  before the committed baseline). The `_rdkit_cross_check` is `importorskip`-gated; `validate()` and the frozen
  hash are RDKit-free.
- A live loose thread (source-only, unresolved): whether Rule 4b's tied-reference double-branch can produce a
  pseudoasymmetric ±2 signal that Rule5New does not capture — flagged for the oracle sweep when the build happens.

Evidence: `experiments/cip_target_relative_rules_probe.py`, `tests/test_cip_target_relative_rules.py`.
