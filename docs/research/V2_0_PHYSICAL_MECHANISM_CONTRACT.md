# V2.0 Physical-Mechanism Contract — the minimal, trustworthy representation SmartChem hands a future physical-simulation kernel

> *Mr. Meeseeks drafted the load-bearing claims against live source; every "establishes today" row was read, not
> remembered. A subtly-wrong contract is worse than none, so where source does not back a claim it is labelled
> UNVERIFIED or CONJECTURED, never asserted.*

## 0. Header — baselines & scope

| ref | SHA | note |
|---|---|---|
| `feat/chemical-graph-projections` (PR #101, draft) | `34e1891` | development branch; `__version__ = 1.1.0a1` (this doc authored here) |
| `origin/main` | `99fce34` | 5 commits past the tag, docs/launch only — semantically ≡ `v1.0.0` |
| released `v1.0.0` | `8345bbb` | the frozen 1.0 record; `git diff v1.0.0 -- smartchem/` vs `origin/main` empty |

**Scope statement.** This is a **branch-only research deliverable.** It proposes a representation for a *future,
external* physical-simulation kernel. It makes **no change to the frozen 1.x JSON wire** (today
`compilation-ir/chemical-compilation-ir-v1alpha8`, response `compilation-response-v1alpha18`; `compilation_ir.py:104`,
`COMPATIBILITY.md §3.1`), **no merge, no tag, no release**, and **no representational rewrite of the 1.5 branch**.
Every proposed schema name below is *provisional* and *not binding*. Nothing here is implemented; §11 marks each claim's
status. The 2.0 prerequisites this doc expands (`#105`, `#130`) are already recorded as DEFERRED in
`docs/research/V1_5_RELEASE_PROGRAM.md §5`.

---

## 1. HONEST INVENTORY — what each existing module genuinely establishes for physical simulation

Column 3 cites `file:line`. "Establishes today" = read in source this round. "Does NOT provide" = a capability a
physical kernel needs that this module deliberately does not supply.

| module | Genuinely establishes today | Does NOT provide | anchor |
|---|---|---|---|
| `smartchem/open_core.py` | Domain-neutral open symmetric-monoidal diagram core: multi-terminal `Hyperedge`, total `then`/`tensor`/`plug_all` composition, a monoidal `Decoration` slot with an **interchange-invariance obligation**, and a bounded fail-closed exact `canonicalize` (refuses, never approximates). | Any physics: ports/payloads are opaque strings; no rate, energy, geometry, or units. No numerical state. | `open_core.py:73,83-92,275,327,342,593` |
| `smartchem/open_chem_diagram.py` | Chemistry layer on the core: species-typed ports (resonance identity), one genuine additive **conservation decoration** (`products−reactants` element/charge vector, homomorphic SUM, gluing-independent), topology-derived provenance DAG, `conservation_status` tri-state (`CONSERVING/VIOLATED/UNDECIDED`), and `net_reaction` collapsing internal intermediates. | Rates, free energy, time evolution, cell/space. Charge is a **single global `+` key** (verified: `Na⁺→Na` nets `(('+',-1),)`) — NOT per-atom. | `open_chem_diagram.py:110-114,121,519,577` |
| `smartchem/category.py` (`Molecule`) | `Molecule` = a **pure connected graph**: `atoms` tuple, `bonds` frozenset, one integer `charge`, opaque `state` label. `formula` is a **property returning a `dict`** (verified). Bonded, canonicalised, isomerism-collapsing. `carrier`/`quantum` spell charge-only/atom-less tokens. | Per-atom charge, oxidation state, stereo/config, isotope, phase/material, concentration, geometry. `state` is opaque and not conserved. | `category.py:736,760-763,852-857,803` |
| `smartchem/experiment/step.py` (`ExperimentStep`) | One certified bench step (target/reactants/products/reagents/envelope/`reaction_center`). `__post_init__` **builds an independent `Reaction` conservation certificate and REFUSES non-conserving steps** (verified: `StepError`). **Recognition is a pure function of the conserved reactant/product multisets** for all 19 recognizers; `reaction_center` is `compare=False` advisory metadata, never recognition evidence. | Rate, yield, mechanism, elementary-step decomposition, executable dynamics. "Bookkeeping is exact; says nothing about whether/how fast it proceeds" (W3). | `step.py:77,99-106,115,140-146` |
| `smartchem/experiment/kinetics.py` | Arrhenius `k = A·exp(−Ea/RT)` and a rate **regime** (`FAST/MODERATE/SLOW/FROZEN`) **only where `(Ea,A)` are SOURCED** for the exact direction-specific reaction; otherwise a **LOUD `UNKNOWN` rate, never a fabricated k / never silent zero** (verified: regime+grade `UNKNOWN`, explicit reason). Rate is ORTHOGONAL to epistemic grade. **This is a foundation already present — the right fail-closed behaviour a kernel must inherit.** | Barrier prediction, cleavage selection, pathway ranking by rate (permanent W3 wall). No mechanism/rate-law *shape* beyond first/pseudo-first order half-life. | `kinetics.py:82-89,229-231,289-306` |
| `smartchem/experiment/equilibrium.py` | `K = exp(−ΔG/RT)` and an extent verdict; an **exactly-solvable** conversion only for Δn=0 ideal reference, else LOUD `UNKNOWN`. General `equilibrium_extent` bisection under a DECLARED ideal reference. | Rate / time-to-equilibrium; real activities; coupled equilibria; practical yield. **"Extent, never rate"; explicitly NOT a capability verdict** (DRIVE ≠ CAPABILITY). | `equilibrium.py:28-31,203,297-303` |
| `smartchem/experiment/feasibility.py` | Standard-state ΔG = ΔH(Hess) − TΔS over sourced (+Benson-derived) thermo; graded `DERIVED/PREDICTED`; a domain guard that **fails closed** on the free-acid dehydrative-acylation class it cannot judge. | **Measures thermodynamic DRIVE, not RATE and not an instantaneous reaction**; not a yield; standard-state only. | `feasibility.py:25-26,246-265,635-690` |
| `smartchem/experiment/phase.py` | Clausius–Clapeyron phase placement (`solid/liquid/gas`) at `(T,P)` from sourced normal bp + ΔHvap; **returns `None` (refuses)** when the needed sourced inputs are absent. | Mixtures, solubility, aqueous speciation, interfaces, partial pressures, non-ideal PVT. Melting treated P-independent (stated approximation). | `phase.py:44-63` |
| `smartchem/data/thermo.py` | Small SOURCED seed of ΔfH°/S° at 298.15 K with **phase-carrying key** and **fail-closed phase/isomer ambiguity** (`for_formula`/`for_named` return a hit IFF exactly one match); `uncertainty_*` and `grade` are `compare=False` (provenance, not identity). | Temperature-dependent Cp(T); aqueous ions; activity models; a non-seed compound without injection/derivation. | `thermo.py:40-73,142-167,189` |
| `smartchem/data/phase_change.py` | SOURCED ΔsubH/ΔsubS, ΔvapH/ΔvapS (gas−condensed, >0) and `to_condensed`, degrading to a loud absence (stays gas, phase-flagged). | Pressure/temperature dependence of the transition; fusion directly; any non-seed compound. | `phase_change.py:53-101,164-174` |
| `smartchem/conditions.py` | `ConditionEnvelope`: a **declared context, never a prediction** — optional T/P/duration intervals with **enforced units (K/atm/min)**, medium/catalysts/field, `EvidenceStatus` **capped at EXPERIMENTAL**; `unknown()` is the honest `UNSUPPORTED` default (verified). Env-comonad algebra. | Any computed chemistry/physics. A declared envelope is not a validated regime. | `conditions.py:101-124,146-159,178,210-217` |
| `smartchem/compilation_ir.py` | The **versioned JSON wire** both compiler directions speak; the rule that **"the serialized digest MUST change when any semantic input changes; display labels/ordering MUST NOT"**; candidate `readiness_tier` pinned `FORMAL_CANDIDATE`. | Any physical-state, rate-law, or mechanism payload. It certifies *search bookkeeping*, "asserts nothing about chemistry". | `compilation_ir.py:12-23,104,219` |
| `smartchem/transport_ledger.py` | Per-field transport trust status (`RE_DERIVED_ON_LOAD`/`BOUND_TO_REQUEST`/`DIGEST_ONLY_ADVISORY`/`LEGACY_FROZEN`), machine-checked: **a loader RE-DERIVES rather than trusting carried values**; advisory is named, not assumed. | A transport model for numerical physical state/fields; it governs the search/response wire only. | `transport_ledger.py:47-51,124-298` |
| `smartchem/contracts.py` | The **content-digest / `Digestible` pattern**: `canonical_digest` is a type-tagged SHA-256 that **excludes `compare=False` and non-public fields** (verified: `grade` moves no digest) — the clean identity-vs-provenance split a mechanism identity needs. | Not an authenticator; "identity and integrity aid, not an authentication boundary". | `contracts.py:146-155,183,244` |

**Four honest findings worth stating up front** (expanded in §11):
1. `kinetics.py` **already does the right thing**: no sourced `(Ea,A)` ⇒ a loud `UNKNOWN`, never a silent zero rate. The
   kernel contract inherits this, it does not invent it.
2. Charge today is **one integer per molecule / one global `+` key in the conservation vector** — not per-atom. General
   ionic chemistry MUST NOT be built on it (`#105`).
3. `ExperimentStep` is **already content-determined and conservation-fail-closed**; a mechanism loader can re-derive the
   same certificate rather than trust a carried one.
4. `feasibility`/`equilibrium` are **honestly scoped to DRIVE/EXTENT, never rate or capability** — the exact typed
   boundary §2 forbids collapsing.

---

## 2. THREE TYPED LEVELS that must not collapse

| level | what it is | SmartChem anchor today |
|---|---|---|
| **A — Chemical description** | *What transformation, conserving matter/charge.* Constitution, stoichiometry, a recognized family, a declared condition envelope. | `Molecule`, `Config`, `ExperimentStep` (`step.py:77`), `ConditionEnvelope` (`conditions.py:101`) |
| **B — Physical mechanism** | *A finite, verifiable set of elementary processes with rate laws + thermodynamic references + a declared applicability domain.* A model of dynamics, not of one world. | **does not exist today**; `kinetics.py`/`equilibrium.py`/`feasibility.py` supply only *per-reaction scalar* reads (k, K, ΔG) where sourced |
| **C — Physical world state** | *An instantaneous, numerical state of a concrete system:* amounts/concentrations, T, P, fields, geometry, time. Evolves under B. | **does not exist today**; `ConditionEnvelope` is a *declared* context, not a state |

**Forbidden collapses (each a hard law of this contract):**
- A valid `ExperimentStep` **MUST NOT** auto-become an executable rate model. (A→B is not free; `step.py:99-106` keeps
  recognition a pure multiset function with no dynamics.)
- A recognized reaction family **MUST NOT** auto-acquire a rate law. (Recognition ≠ parameterization; W3.)
- A favorable standard-state ΔG **MUST NOT** be read as an instantaneous (or any) reaction. (DRIVE ≠ event;
  `feasibility.py:25-26`, `equilibrium.py:28-31`.)
- A missing kinetic model is **`UNKNOWN`/`UNAVAILABLE`, never a silent zero rate.** (Inherited verbatim from
  `kinetics.py:289-306`.)
- An arbitrary formula **MUST NOT** become a fully specified material. (Formula-layer identity is never lifted to a
  structure/material/phase claim; `compilation_ir.py:26`, `IdentityLayer.FORMULA`.)

---

## 3. SCHEMA (provisional; names NOT binding)

Every field declares: **authority** (who may set it), **units**, **identity/digest contribution** (`id` = part of the
content digest; `prov` = `compare=False` provenance, moves no digest — the `contracts.py:146-155` pattern),
**uncertainty**, **domain of validity**, **failure behavior**. "Reuse" means an existing SmartChem type whose semantics
*genuinely* match; "NEW" means nothing fits.

### 3.1 `SpeciesIdentity` — reuse `Molecule` for constitution; EXTEND for the rest
| field | authority | units | id/digest | uncertainty | domain | failure |
|---|---|---|---|---|---|---|
| `constitution` (reuse `Molecule`, `category.py:736`) | parser/generator | — | **id** (canonical graph) | n/a | constitution-level only (`COMPATIBILITY.md §5`) | refuse >1024 atoms / budget (`CanonicalBoundExceeded`) |
| `net_charge` (reuse `Molecule.charge`) | parser | elementary charge `e` | **id** | n/a | one global charge | type-checked int |
| `per_atom_charge` (**NEW**; blocked by `#105`) | parser | `e` per atom index | **id** when claimed | n/a | **absent today** | MUST refuse to fabricate; absence ⇒ cannot represent ionic placement |
| `configuration` (**NEW**; blocked by `#130`) | parser | — | **id** when claimed | n/a | **absent today** | refuse (never terminate on wrong isomer) |
| `isotope` (**NEW**) | parser | — | **id** when claimed | n/a | absent (disclosed as identity loss today) | refuse to assume natural abundance silently |
| `phase_material` (**NEW**; cf. `thermo.ThermoRef.phase`) | caller/data | enum solid/liquid/gas/aqueous | **id** | n/a | phase-carrying lookup exists (`thermo.py:116`) | fail-closed on ambiguity |

### 3.2 `PhysicalSpeciesState` (Level C) — **NEW**
| field | authority | units | id/digest | uncertainty | domain | failure |
|---|---|---|---|---|---|---|
| `species` (ref `SpeciesIdentity`) | model | — | id | n/a | — | — |
| `amount` **or** `concentration` (**distinct** quantities) | world-state producer | mol / mol·L⁻¹ | state, not model id | measured/declared ± | per-cell volume must be declared for the pair to interconvert | refuse to convert without a declared volume |
| `phase_fraction` | producer | dimensionless | state | ± | — | `UNKNOWN` if unplaced |
| `activity`/`fugacity` (optional) | producer | dimensionless / bar | state | ± | needs an activity model | `UNKNOWN` (default ideal only if DECLARED) |

### 3.3 `ReactionStoichiometry` — reuse the conserved multisets
| field | authority | units | id/digest | uncertainty | domain | failure |
|---|---|---|---|---|---|---|
| `reactants`/`products` (reuse `ExperimentStep` multisets) | generator/caller | mol (ratios) | **id** | n/a | conservation enforced | **refuse non-conserving** (`step.py:140-146`, verified) |
| `conservation_vector` (reuse `ConservationDecoration`) | derived | element+`+` counts | **id** | n/a | global charge only | zero iff balanced |

### 3.4 `RateLawSpec` — **NEW** (no existing type; `kinetics.py` holds only sourced Arrhenius scalars)
| field | authority | units | id/digest | uncertainty | domain | failure |
|---|---|---|---|---|---|---|
| `form` | **sourced only** | enum (mass-action, Arrhenius, …) | **id** | n/a | declared mechanism form | no source ⇒ `UNAVAILABLE` |
| `orders` (per species) | sourced | dimensionless | **id** | ± | the fit's regime | missing ⇒ `UNKNOWN` |
| `A`, `Ea` (reuse `KineticRef` semantics) | sourced | A: form-dependent (`a_units`); Ea: kJ·mol⁻¹ | **id** | ± / fit window | **validity window `[T_lo,T_hi]`** | outside window ⇒ `PREDICTED` flag (`kinetics.py:316-318`) |
| `source` | sourced | — | **prov** | — | — | **never web-searched/guessed** |

### 3.5 `ThermodynamicModelRef` — reuse `ThermoRef`/`PhaseChangeRef`
| field | authority | units | id/digest | uncertainty | domain | failure |
|---|---|---|---|---|---|---|
| `dHf`, `S` (reuse `ThermoRef`, `thermo.py:40`) | sourced/derived | kJ·mol⁻¹, J·mol⁻¹·K⁻¹ | **id** (value); `grade`,`σ` **prov** | ± (`compare=False`) | standard state, 298.15 K reference, **declared phase** | ambiguous phase ⇒ `None`/`UNKNOWN` (`thermo.py:142-167`) |
| `standard_state` | data | enum/phase | **id** | — | phase-specific | mismatched phase fails closed |
| `phase_change` (reuse `PhaseChangeRef`) | sourced | kJ·mol⁻¹, J·mol⁻¹·K⁻¹ | **id**; `σ` prov | ± | gas↔condensed | absent ⇒ no correction (stays gas, flagged) |

### 3.6 `MechanismPack` (Level B) — **NEW**; a closed, explicitly-selected set
| field | authority | units | id/digest | uncertainty | domain | failure |
|---|---|---|---|---|---|---|
| `schema_version` | producer | — | **id** (own versioned artifact, NOT the 1.x wire) | — | — | unknown id refused, never guessed |
| `reactions` (tuple of `ReactionStoichiometry`) | explicit selection | — | **id** | n/a | closed set only | — |
| `rate_laws` (per reaction; `RateLawSpec`) | sourced | — | **id** | per law | per law | missing law ⇒ that reaction `UNAVAILABLE`, pack still valid but flagged |
| `thermo_refs` (`ThermodynamicModelRef`) | sourced/derived | — | **id**; σ prov | per ref | — | gap ⇒ `UNKNOWN` drive for that reaction |
| `domain` (`PhysicalApplicabilityDomain`) | producer | — | **id** | — | — | out-of-domain ⇒ refuse execution |

### 3.7 `MechanismValidationReceipt` — reuse the out-of-band receipt + ledger discipline
Semantics match `transport_ledger.py`/the load receipt (`COMPATIBILITY.md §4`): **issued only by the validating
loader, never on the wire, states facet-by-facet what was RE-DERIVED vs trusted.** Fields: `rederived_conservation`,
`rederived_structure`, `rate_laws_present`, `thermo_present`, `within_declared_domain`, `work_consumed`. Authority:
loader only. id/digest: out-of-band (cannot be constructed/copied into a stronger one). Failure: a carried value that
disagrees with re-derivation is **refused**, not accepted.

### 3.8 `PhysicalApplicabilityDomain` — **NEW** (partial analogue: `ConditionEnvelope`)
| field | authority | units | id/digest | uncertainty | domain | failure |
|---|---|---|---|---|---|---|
| `temperature`/`pressure` (reuse `Interval`, `conditions.py:80`) | producer | K / atm | **id** | — | the regime the pack was validated in | state outside ⇒ refuse (never extrapolate silently) |
| `media`/`phases` | producer | enum | **id** | — | declared | unlisted medium ⇒ `UNKNOWN` |
| `concentration_range` | producer | mol·L⁻¹ | **id** | — | — | outside ⇒ refuse |

**Reuse summary (said plainly):** `Molecule` for constitution; `ConditionEnvelope`/`Interval` for conditions;
`ThermoRef`/`PhaseChangeRef`/`KineticRef` for sourced parameters; `ConservationDecoration` for the balance vector; the
`Digestible`/`canonical_digest` pattern for every mechanism identity; the load-receipt + transport-ledger discipline for
validation. **NEW** only where nothing fits: per-atom charge, configuration, isotope, `PhysicalSpeciesState`,
`RateLawSpec`, `MechanismPack`, `PhysicalApplicabilityDomain`.

---

## 4. SPECIES IDENTITY obligations

A kernel-bound identity MUST be able to distinguish (independently — not one collapsed key):
1. molecular **constitution** (today: `Molecule` graph, resonance class; `COMPATIBILITY.md §5`);
2. **net formal charge** (today: `Molecule.charge`, one int);
3. **per-atom (local) charge state** (today: **absent**);
4. **isotope / configuration** identity *when claimed* (today: **absent**; disclosed as identity losses);
5. **phase & material state** (today: partial — phase-carrying thermo key, `thermo.py:116`);
6. **aqueous species vs bulk solid/gas** (today: **absent** as a first-class distinction);
7. **amount vs concentration** — *distinct quantities*, never interconvertible without a declared volume;
8. **actual model applicability vs an assumed initial condition** — a declared envelope (`conditions.py`) is an
   assumption, never a validated model domain.

### Precise representational OBSTRUCTIONS (each named & separated — do NOT conflate)

**`#105` — per-atom formal charge.** *What exactly breaks without it.* The conservation vector carries charge as a
**single global `+` key** (verified: `Na⁺→Na` ⇒ `(('+',-1),)`; `open_chem_diagram.py:110-114`). `Molecule.charge` is
one integer for the whole species (`category.py:762`). Therefore the representation **cannot say which atom bears the
charge**: a zwitterion (net 0, two local charges) and its neutral tautomer are indistinguishable at the charge layer; an
acid/conjugate-base pair cannot be placed; heterolytic/ionic mechanisms cannot be given a local driving charge.
`V1_5_RELEASE_PROGRAM.md §5` records this as blocking **all ionic/dipolar chemistry**. **Consequence for the contract:**
general ionic chemistry MUST NOT be built on an identity that silently loses charge placement — `per_atom_charge` is a
distinct, claim-gated field that **refuses to fabricate** when absent.

**`#130` — configuration-aware matching.** *What exactly breaks without it.* Material identity is constitution-level;
stereochemistry/configuration is explicitly **not perceived** and is disclosed as an identity loss
(`COMPATIBILITY.md §5`). A constitution-only match could **terminate on the wrong enantiomer/diastereomer** under a finer
requested identity layer. Today's fail-closed rule is *refuse*; 2.0's obligation is *honor when claimed*
(`V1_5_RELEASE_PROGRAM.md §5`). **Consequence:** `configuration` is a separate claim-gated field; a finer requested layer
must refuse rather than silently match a coarser identity.

**Separation check (demanded by the task).** `#105` (charge placement) and `#130` (configuration) are **independent**:
one can hold without the other. **Aromaticity representation is a THIRD, distinct obstruction** — I did *not* find a
source dependency making `#105` entail aromaticity. The aromaticity gap is documented separately: `#111`'s aryl-O
deferral is because *"a Kekulized aryl carbinol carbon is indistinguishable from an acyclic enol in the aromaticity-free
graph"* (`V1_5_RELEASE_PROGRAM.md §9`), a **bond-order/aromaticity** limitation, not a charge-placement one. The program
doc files the aromaticity model loosely under `#105`'s 2.0 bucket, but the *mechanism* is different; this contract keeps
them as three obstructions: **(a) per-atom charge `#105`, (b) configuration `#130`, (c) aromaticity/bond-order
perception.** Treat them separately; do not let one stand in for another. *(This separation is CONJECTURED from the two
docs' wording; see §11.)*

---

## 5. MECHANISM IDENTITY — content-bound + versioned, with INDEPENDENT TYPED FACETS

**Content binding.** A `MechanismPack` identity is its `canonical_digest` over the content fields (the `contracts.py:183`
pattern; `compare=False` provenance excluded, verified). This mirrors the wire rule that *"the serialized digest MUST
change when any semantic input changes… display labels/ordering MUST NOT"* (`compilation_ir.py:12-23`).

| MUST change the semantic identity | MUST NOT change it |
|---|---|
| any participating species (constitution/charge/config when claimed) | a displayed human label / name |
| stoichiometry / conservation vector | a visual colour or layout order |
| a rate-law form, orders, or parameters `(A, Ea, …)` | a diagnostics string / prose |
| a thermodynamic standard state or referenced model | a provenance citation string (`prov`, `compare=False`) |
| the declared validity range / applicability domain | a frame/tick index of a rendering |

### Readiness as INDEPENDENT TYPED FACETS (NOT one ordered ladder)

These are **NEW facets, distinct from — and never reusing or modifying — the existing 1.x readiness enum**
`FORMAL_CANDIDATE < REACTION_VOUCHED < CONDITIONS_SUPPORTED < PROCESS_SPECIFIED` (`smartchem/experiment/readiness.py:80-87`,
`COMPATIBILITY.md §2.1`). The 1.x ladder grades *bench/procedure readiness*; these grade *mechanism-model support* and
live on the `MechanismPack`, not the route.

| facet | means | satisfied today by |
|---|---|---|
| `FORMAL_ONLY` | conserving stoichiometry exists | `ExperimentStep` certificate |
| `STRUCTURALLY_RECOGNIZED` | an oracle family re-derivation recognizes it | `reaction_type_oracle` (internal-consistency witness only) |
| `THERMODYNAMICALLY_SUPPORTED` | a sourced/derived ΔG (DRIVE) is available | `feasibility.py` where thermo reaches |
| `KINETICALLY_PARAMETERIZED` | a sourced rate law `(form, A, Ea, window)` is available | `kinetics.py` where `(Ea,A)` sourced |
| `VALIDATED_WITHIN_DECLARED_REGIME` | reproduces a known measured outcome inside a declared domain | partially: feasibility/kinetics calibration cases |

**Why thermodynamic and kinetic support are NOT linearly ordered.** They are orthogonal physical facts, demonstrable both
ways in SmartChem today:
- **Thermo without kinetics:** diamond→graphite is thermodynamically favored yet kinetically frozen — the module
  docstrings cite exactly this (`feasibility.py:*`, `equilibrium.py:28-31`). A reaction can be
  `THERMODYNAMICALLY_SUPPORTED` with **no** sourced rate law (`KINETICALLY_PARAMETERIZED` absent).
- **Kinetics without thermo:** a sourced `(Ea,A)` yields k and a regime even when no ΔfH°/S° is tabulated for the species
  (kinetics keys on the sourced reaction record, not on the thermo table; `kinetics.py:214-226`), so
  `KINETICALLY_PARAMETERIZED` can hold with `THERMODYNAMICALLY_SUPPORTED` absent.

Therefore a single ordered ladder would be unsound: it would force one facet to imply the other. **A missing kinetic law
cannot be bypassed by labeling a reaction "known"** — `STRUCTURALLY_RECOGNIZED` (or any thermo/attestation footing) never
confers `KINETICALLY_PARAMETERIZED`; the rate stays `UNKNOWN` (`kinetics.py:25-30` states the orthogonality explicitly).

---

## 6. `compile_physical_mechanism(chemical_candidates, physical_context, source_policy)` — conceptual signature

```
compile_physical_mechanism(
    chemical_candidates : Sequence[ExperimentStep | OpenChemDiagram],   # Level-A input
    physical_context    : PhysicalApplicabilityDomain,                  # declared regime
    source_policy       : SourcePolicy,                                 # which sourced tables are admissible
) -> MechanismPack | MechanismAdmissionRefusal
```

**Behavioral contract (each clause is a hard law):**
- It produces **either** a VERIFIABLE finite `MechanismPack` **or** a `MechanismAdmissionRefusal` naming **exactly** what
  prevents admission (missing rate law / missing thermo / out-of-domain / unresolved identity). No partial silent pack.
- It **MUST NOT** web-search or guess rate constants (mirrors `kinetics.py:*` "a rate is NEVER guessed"; §11 CORROBORATED
  by the module's refusal path).
- It **MUST NOT** import every formally-possible reaction. The mechanism set is **closed and explicitly selected** first;
  reachability (a wider algebra) is a separate, opt-in concern (cf. `#114` reachability-vs-recognition in
  `V1_5_RELEASE_PROGRAM.md §2`).
- It **MUST NOT** auto-promote a named family into elementary steps. Recognition (`STRUCTURALLY_RECOGNIZED`) is not an
  elementary-step decomposition; the step stays an overall transformation unless an elementary mechanism is explicitly
  supplied and validated.
- The **loader RE-DERIVES** the structural + conservation obligations from the candidate molecules rather than trusting a
  supplied certificate — exactly the `ExperimentStep.__post_init__` discipline (`step.py:140-146`, verified) and the
  transport-ledger "re-derive, don't trust" rule (`transport_ledger.py`).
- **Prototype only in a SEPARATE experimental schema/module** with its own explicit `schema_version` — **never** an
  implicit extension of the frozen 1.x wire (`compilation_ir.py:104`, `COMPATIBILITY.md §3`).

---

## 7. CATEGORICAL BRIDGE (load-bearing, not decorative)

Let **N** be the species×reaction **stoichiometric matrix** (`N[s,j]` = net formation of species `s` by reaction `j`,
products +, reactants −) and **E** the **element-and-charge inventory matrix** (`E[e,s]` = count of element/charge
coordinate `e` in species `s`).

**Necessary conservation constraint:** `E·N = 0`. Each column `N[:,j]` is one reaction; `E·N[:,j] = 0` says reaction `j`
creates/destroys no element and no net charge. This **IS** the `ExperimentStep` certificate, column by column:
`__post_init__` enforces `dom.formula == cod.formula` and `dom.charge == cod.charge` for each generator
(`step.py:140-146`; `open_chem_diagram.py:519-532`), and the additive `ConservationDecoration` is the homomorphic column
sum (`open_chem_diagram.py:121-169`). **Load-bearing caveat:** today the charge *row* of **E** is the **single global
molecular charge** (the `+` key), not per-atom — so `E·N=0` certifies global element+charge balance but **cannot**
certify local charge placement (this is precisely `#105`, §4).

**Per-cell dynamics (Level C):** for a cell `c`,
```
dn_c/dt = N · r_c(state_c)  +  Σ_f  J_{f→c}
```
where `r_c` is the **state-dependent** reaction-rate vector (concentrations, T, …) and `J_{f→c}` the face flux into `c`.
**The rates are NOT inferable from N alone** — N is Level-A/B *stoichiometry*; `r_c` requires `RateLawSpec` + physical
state. This is the categorical restatement of the §2 forbidden collapse.

**Per shared interface (flux antisymmetry):** under a common orientation/convention/unit basis,
```
J_{A→B} + J_{B→A} = 0
```
so when cells are composed the internal face fluxes **cancel in the global elemental inventory** — the discrete-geometry
analogue of SmartChem's compositional cancellation: `plug_all` turns a glued producer/consumer node INTERNAL while leaf
inputs and byproducts stay EXTERNAL (`open_core.py:342`, `open_chem_diagram.py:467-474`), and `net_reaction` collapses
the internal intermediates so a conserving assembly yields a conserving net equation (`open_chem_diagram.py:577-600`).
**Open-system variant:** inlets/outlets are EXTERNAL ports (`PortState.EXTERNAL`) and reservoirs are unbalanced boundary
terminals — the open SMC already distinguishes `INTERNAL`/`EXTERNAL`/`OPEN` (`open_chem_diagram.py:80-86`), which is
exactly the open/closed-system distinction a flow reactor needs.

**Can `OpenChemDiagram` supply the compositional topology/identity while a separate layer supplies numerical source
terms?** *Assessment:* **Yes for topology + conservation identity; No for the numbers.** The diagram supplies: species
identity on ports, the hyperedge incidence (which reaction touches which species), the INTERNAL/EXTERNAL/OPEN port
classification, and the homomorphic conservation decoration — all node-relabel- and interchange-invariant under
`canonicalize`. A **separate** state-dependent layer must supply `r_c` and the fluxes; the diagram carries **no** numbers
and interprets **no** payload as physics (`open_core.py:14-18`). *(CONJECTURED-as-sufficient; the state layer does not
exist, so this is an architecture claim, not a demonstrated one — §11.)*

**The STRONGEST VALID categorical statement (and nothing broader).** The conservation decoration **is** a monoidal
functor from the diagram category to `(ℤ^(elements+charge), +, 0)` — composition maps to addition (`then`/`tensor` both
add; `open_chem_diagram.py:160-164`), the interchange law holds (`open_core.py:83-92`), and it is relabel-invariant. The
proven free-energy drive is the same shape (additive Hess-law sum, `feasibility.py:821-834`). *(The module
itself frames this decoration as a **demonstration** of the `open_core` decoration slot
(`open_chem_diagram.py:123-134`) and treats the separate direct boundary count `conservation_status` as the
AUTHORITATIVE conservation verdict, cross-checked to agree — so the functor is a sound structural witness, not
the sole verdict source.)* **What is NOT a functor:**
the **numerical time-evolution solver.** I do **not** claim it is one. To call the solver a functor one must define its
domain, codomain, composition law, approximation, and error law — none of which exists in source. Structure (N, the
diagram) implies the *conservation law* `E·N=0`; it does **not** imply the *rate law* or *energy conservation*. Where
structure does not imply a physical law, this contract says so plainly.

---

## 8. ENERGY as a SEPARATE obligation

A physical kernel's energy ledger is **independent of** and **additional to** the matter/charge ledger. Obligations:

| energy term | status today | note |
|---|---|---|
| species internal energy `U` | **absent** (no Level-C state) | the reference point convention must be DECLARED |
| enthalpy / chemical-energy convention | **partial**: ΔfH° referenced to elements (`thermo.py`) | — |
| reaction enthalpy ΔrH (Hess) | present as DRIVE (`feasibility.py:693`) | **standard-state, not transported energy** |
| heat transfer `Q` | **absent** | — |
| PV work (where admitted) | **absent** | only if a mechanical model is declared |
| enthalpy carried by flowing matter | **absent** | couples to the §7 face flux `J` |
| phase-change energy | **partial**: sourced ΔsubH/ΔvapH (`phase_change.py`) | add on a phase transition only |

**Double-counting flag (explicit).** When chemical energy is **already encoded in species internal energy** `U` (an
enthalpy-of-formation reference baked into `U`), a reaction's enthalpy change is the **difference of those `U` values** —
adding a *separate* reaction-enthalpy source term **double-counts**. The convention (is ΔrH implicit in `U`, or an
explicit extra term?) MUST be declared once in the `MechanismPack`/kernel and enforced.

**Stated plainly:** **a balanced atom ledger does NOT imply energy conservation.** `E·N=0` (§7) is a matter/charge fact;
it says nothing about `U`, `Q`, or work. Energy is its own conservation obligation with its own closure check.

---

## 9. LibGibson boundary (SKETCH ONLY this round)

A single provisional **data** boundary, producer→consumer, carrying a snapshot:

```
PhysicalWorldSnapshot  ──(serialized, immutable)──►  Presentation (LibGibson)
```

| snapshot field | content |
|---|---|
| `frame_id` / `model_tick` | identity of which simulation tick this is |
| `grid_dims` + `world_coords` | discretization + physical extent |
| `scalar_fields` | named fields **WITH UNITS** (T [K], P [atm], …) |
| `species_inventory` / `selected_observables` | amounts/concentrations + chosen readouts |
| `boundary_geometry` / `material_geometry` | cell/interface/material layout |
| `missing_mask` / `invalid_mask` | **explicit** missing/invalid data (never silent zero — mirrors the
  `UNKNOWN`/`None` fail-closed discipline throughout SmartChem) |
| `provenance` / `diagnostics` / `uncertainty_refs` | references, not inline authority |

**Constraints (hard):**
- The simulation runs **HEADLESS without LibGibson**; rendering is strictly downstream.
- LibGibson may render at **20/30/60 fps WITHOUT changing how many reactions occur** — frame rate is decoupled from
  model ticks (a snapshot may be rendered 0..N times; the mechanism count depends only on `model_tick`).
- **No per-pixel Python↔Rust FFI.** The boundary is **compact immutable snapshots** with **explicit producer/consumer
  ownership**, not a chatty call interface.
- **Ownership split:** `femboy2112/libgibson` issue **#125** (Interactive-Instrument Platform epic, #126–146) **OWNS the
  renderer/platform side.** **SmartChem MUST NOT implement renderer functionality; LibGibson MUST NOT learn reaction
  kinetics.** A documented serialization/protocol sketch is sufficient now. *(The libgibson issue numbers are quoted from
  the task brief; I could not verify them against that external repo from here — see §11, UNVERIFIED.)*

---

## 10. 2.0 → 3.0 DEPENDENCY ROADMAP (reconciled with the 1.5 plan)

| 3.0 capability | depends on |
|---|---|
| general ionic / electrochemical mechanisms | **`#105` per-atom formal charge** (§4) |
| time-resolved reactor simulation | **sourced kinetics** (`RateLawSpec`; today `UNKNOWN` without `(Ea,A)`) |
| aqueous / solution-phase chemistry | **thermo-speciation data** (aqueous ΔfG, activity models — absent today) |
| flow / gas-phase transport + fields | **fluid/gas physics** (the §7 flux layer + §8 energy — absent today) |
| configuration-correct products | **`#130` configuration-aware identity** (§4) |

**Framing.** `1.x` (coverage/recognition + honest fail-closed scalars) → **`2.0`** (this contract: the typed Level-A/B/C
separation, the mechanism schema, the `#105`/`#130` representational rails) → `2.x` (sourced kinetics/thermo-speciation
population; the external kernel prototype) → `3.0` (the running physical-simulation kernel + LibGibson platform).

**Explicit DEFERRED 2.0 items:** per-atom charge rail (`#105`); configuration identity (`#130`); aromaticity/bond-order
perception; organometallic elements (`#108`); the general reaction-event calculus / lateral-search fusion; atom-mapped
transformation witnessing (`V1_5_RELEASE_PROGRAM.md §5`).

**Hard rule (restated):** **no representational rewrite enters the 1.5 branch merely because 3.0 needs it.** The 1.5
branch ships recognition/reachability/hardening only; `#105`/`#130` and the mechanism schema are 2.0 work on a separate
line (`V1_5_RELEASE_PROGRAM.md §5`).

---

## 11. CLAIM LEDGER

Labels: **DISCLOSED** (within stated scope) / **CORROBORATED** (independent routes) / **OBSERVED** (one execution) /
**CONJECTURED** / **UNVERIFIED** / **REFUTED**.

| # | claim | label | basis |
|---|---|---|---|
| 1 | `Molecule.formula` is a property returning a `dict`; `Molecule` is a pure graph with a single `charge` int (no per-atom charge) | **OBSERVED** + **CORROBORATED** | probe + `category.py:736,760-763,852` |
| 2 | `ExperimentStep.__post_init__` refuses non-conserving steps via an independent `Reaction` certificate | **OBSERVED** + **CORROBORATED** | probe (`StepError`) + `step.py:140-146` |
| 3 | Recognition is a pure function of the conserved multisets for all 19 recognizers; `reaction_center` is `compare=False` advisory | **DISCLOSED** | `step.py:99-106,115` (not re-proven here) |
| 4 | No sourced `(Ea,A)` ⇒ a LOUD `UNKNOWN` rate, never a fabricated/silent-zero k | **OBSERVED** + **CORROBORATED** | probe + `kinetics.py:289-306` |
| 5 | ΔG (`feasibility`) measures thermodynamic DRIVE, not rate / not instantaneous; `equilibrium` is extent not rate, not a capability verdict | **DISCLOSED** | `feasibility.py:25-26`, `equilibrium.py:28-31,297-303` |
| 6 | Charge is carried as a single global `+` key (not per-atom) — the `#105` obstruction | **OBSERVED** + **CORROBORATED** | probe (`Na⁺→Na` ⇒ `(('+',-1),)`) + `open_chem_diagram.py:110-114` |
| 7 | `canonical_digest` excludes `compare=False`/non-public fields — the identity-vs-provenance split reused for mechanism identity | **OBSERVED** + **CORROBORATED** | probe (`grade` moves no digest) + `contracts.py:146-155` |
| 8 | Thermo/phase lookups fail closed on phase/isomer ambiguity; `estimate_phase` refuses (`None`) without sourced inputs | **DISCLOSED** | `thermo.py:142-167`, `phase.py:44-63` |
| 9 | The conservation decoration is a monoidal functor to `(ℤ^(elem+charge),+)`; `E·N=0` ≡ the per-generator certificate | **DISCLOSED** | `open_chem_diagram.py:121-169`, `step.py:140-146` |
| 10 | The numerical time-evolution solver is NOT claimed to be a functor (no domain/codomain/error law in source) | **DISCLOSED** (honest non-claim) | absence in source |
| 11 | Thermo-support and kinetic-support are not linearly ordered (each holds without the other in current modules) | **CORROBORATED** | `kinetics.py:214-226` vs `feasibility.py` + diamond/graphite docstring |
| 12 | `#105` (charge), `#130` (configuration), and aromaticity/bond-order are THREE separate obstructions | **CONJECTURED** | inferred from `V1_5_RELEASE_PROGRAM.md §5,§9` wording; no code proves the independence |
| 13 | `OpenChemDiagram` can supply topology/identity while a separate layer supplies numerical source terms | **CONJECTURED** | architecture read; the state layer does not exist |
| 14 | libgibson `#125` epic owns #126–146; renderer/kinetics ownership split | **UNVERIFIED** | quoted from the task brief; external repo not reachable from here |
| 15 | The 1.x wire is frozen; a 2.0 mechanism schema must be a separate versioned artifact | **DISCLOSED** | `compilation_ir.py:104`, `COMPATIBILITY.md §3` |

**Single next best FALSIFYING probe.** Build the smallest two-cell open flow model by hand — one reaction, a declared
`RateLawSpec`, an inlet and an outlet as `EXTERNAL` ports — and check two things at once: **(a)** that
`J_{A→B}+J_{B→A}=0` makes the composed two-cell elemental inventory equal the single-cell `net_reaction`
(`open_chem_diagram.py:577`), and **(b)** that `dn/dt` is **non-zero** while the conservation decoration stays the zero
vector. If (b) fails to separate — i.e. if any path lets the balanced ledger imply a rate — the §2/§7/§8 separation is
falsified and this contract is wrong where it matters most.
