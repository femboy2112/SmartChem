# Move 5 (domain-neutral pipeline parameterization) — scope decision

> **Status:** SCOPE DECISION — **DEFER, do NOT build now.** Recon verdict: building the pipeline lift today would be a
> **zero-call-sites abstraction** (`THE_DIFFERENCE.md`), the exact pattern this repo has already falsified and deleted.
> This records *why*, the evidence, the one adjacent slice that IS real, and precisely what would UNLOCK Move 5 — so the
> next session (or the user) can make the go/no-go from one page instead of re-running the recon.
>
> Bearings: a `citadel-rick` read-only recon (2026-09-07) + a direct `Molecule`-coupling grep. Not a build.

## What Move 5 asks for

Lift the PIPELINE types — `ExperimentStep` / `ExperimentRoute` / `SynthesisDAG` / composability / cost — off the concrete
`Molecule` and onto an abstract **"conserved-inventory transition + survival predicate"**, so chemistry, circuits and
radiation become functor images of ONE base SMC (`[[electromagnetic-scope]]` as a theorem). `smartchem/open_core.py` is
ALREADY domain-neutral (ROUND 24); Move 5 would lift the *pipeline* onto it.

## The recon verdict: PREMATURE (no second-domain consumer exists today)

The decisive test for any abstraction here is the **zero-call-sites** rule: it must serve a REAL consumer that already
exists, not a domain the code does not yet have. Move 5 fails that test today.

### 1. `Molecule` is nominal-typed into the pipeline, and the conservation certificate is chemistry-specific
Not a duck-typed "conserved token" — the types hard-check `Molecule` at construction and the certificate re-derives
atom/charge balance from `Molecule.formula` dicts:
- `smartchem/experiment/step.py:99-104` — `ExperimentStep.__post_init__` does `if type(self.target) is not Molecule: raise`
  and the same sweep over reactants/products/reagents; `:117-127` builds the certificate as
  `Reaction(Config.of(*reactants), Config.of(*products), ...)` — the actual correctness mechanism, atom-count based.
- The same strict `type(x) is Molecule` guard repeats at `meta_compile.py:150`, `routes.py:474/694`, `formation.py:76`,
  `handling.py:215`, `compile.py:351`. Identity/dedup keys on `resonance_identity(molecule)` (`step.py:58`), a
  chemistry-specific Kekulé-invariant canonicalization, not a generic hash.
- Coupling breadth (grep of `Molecule` in `smartchem/experiment/`): `step.py` 27 · `routes.py` 27 · `dag.py` 20 ·
  `compile.py` 15 · `ceiling.py` 14 · `stock.py` 12 · `handling.py` 10 · `composability.py` 9 · `assembly.py` 9 ·
  `meta_compile.py` 8 · (~10 more). A lift is not a signature relaxation — it replaces the `Reaction`/`Config`/atom-dict
  certificate with an abstract `open_core.Decoration`-style combine law AND relaxes every nominal guard. Genuinely Size **L**.

### 2. No second domain in the tree wants the route pipeline
- **Electrochemistry / cell** (`electrochemistry.py`, `cell.py`, `redox_displacement.py`) are `Molecule`-typed — redox is a
  `TransformProvider` that already rides `ExperimentStep.from_transform` as CHEMISTRY (`transform_provider.py:24-30`);
  `HalfReactionCouple`/`RedoxDisplacementEdge` carry `tuple[Molecule, ...]` with `type(m) is Molecule` guards. `cell.py`
  forces an electron through `Molecule.carrier` by convention (`cell.py:151-152`). Not a distinct domain type.
- **Circuits** (`resistive_dc.py`, `rlc_ac.py`, `circuit.py`, `circuit_model_ir.py`) ARE a real, live, tested non-chemistry
  domain — but built on the SEPARATE `open_diagram.py` core (two-terminal, no decoration slot), with **no route/step/DAG
  concept at all** (a one-shot MNA network solve, not a multi-step synthesis process). There is no slot for
  `ExperimentStep`/`ExperimentRoute`/`SynthesisDAG` to serve; a lifted pipeline would gain zero circuit call sites.
- The `smartchem/*_domain.py` files (`human_isotope`, `human_survival`, `ising_lattice_gas`, `water_wave*`) and
  `smartchem/domain.py` are the **oracle-coverage** `Domain` concept ("would this oracle even try to price the request?",
  `domain.py:1-30`) — a DIFFERENT axis (pricing/coverage), not pipeline consumers. They show the codebase reaches beyond
  chemistry at the *oracle* layer, but the *route pipeline* still serves only chemistry.

### 3. `open_core` is usable; the honest smallest real slice is NOT the Move-5 pipeline lift
`open_core.py` is genuinely domain-neutral (opaque `str` ports, an abstract `Decoration` ABC with interchange-invariance,
`:73-93`). Its OWN docstring names the deferred next step: *"The core is written so it could host the electrical layer
later (Rung C+); this Rung B does not migrate `open_diagram.py` onto it"* (`open_core.py:27-29`). Migrating the electrical
`open_diagram.py`/`circuit.py` stack onto `open_core.py` is the one place a genuine second domain sits next to the generic
core — but that is **core consolidation, not the pipeline lift**, and circuits still would not want `ExperimentRoute`/
`SynthesisDAG` afterward. It is a different, separately-scoped piece of work (and only *Conjectured*-buildable — the MNA
solver / `PortKind` call sites were not checked for a behaviour-preserving re-base).

## What would UNLOCK Move 5 (the trigger to revisit)

Build the pipeline lift only when ONE of these is real:
1. **A genuine second domain with a multi-step-process shape** — a sequence of conserved-inventory transitions with a
   survival predicate that is NOT chemistry (e.g. a multi-stage circuit *fabrication/assembly* process, a staged materials
   process) that today CANNOT ride the pipeline solely because it demands `Molecule`. Then the lift has real call sites.
2. **A concrete pain report** from bending a non-molecule through `Molecule` — the `cell.py:151` `Molecule.carrier` warning
   is a *tell* (electrons bent into a chemistry vehicle) but not yet a pain report; a second such forced-fit would be the
   evidence that the abstraction is earned, not speculative.

Absent either, folding `Molecule` *wider* (the `cell.py` precedent — one universal token type) is cheaper than lifting the
whole pipeline, and Move 5 solves a problem nobody has yet.

## Recommendation

**Defer Move 5.** For forward motion on the categorical arc, the better-earned next steps are:
- **Move 6** — the conditions⤳effects distributive law `λ` (`THE_ORBITAL §IX`); spec-as-contract first. A distinct
  categorical piece that does not depend on a second domain existing.
- **CIP Rung 2 (Rule 1b)** — when a real Rule-1a+2-tied / 1b-decisive molecule appears (ROADMAP queue).
- (optional, if the arc wants the core consolidated) the `open_diagram.py`→`open_core.py` electrical migration — its own
  scoped round, NOT Move 5.

This keeps the reorientation honest: every structure earns its call sites, and a domain-neutral pipeline waits for the
domain that will use it.
