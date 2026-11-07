# OPERATION XXII §7 — the categorical bridge: three layers, one honest claim

**Status:** research. **Claim:** `open_diagram_bridge.bridge_to_kernel` is a **faithful STRUCTURAL functor within
its tested domain** — it is **NOT** a universal dynamics functor. This dossier states what that means precisely, which
layer admits strict theorems, and where the claim stops.

## The three categories

| Category | Objects | Morphisms | Composition / tensor |
|---|---|---|---|
| **Chemical diagrams** | typed chemical interface ports (species tokens) | admitted open reaction diagrams (`OpenChemDiagram`) | `then` glues matching ports; `tensor` juxtaposes disjoint diagrams |
| **Physical system specs** | typed species, phases, conserved components, boundary identities | admitted reaction + transport specifications (require source data for a *physical* reading) | a declared `CoupledWorld` (compartments + interfaces + boundaries + bulk exchanges) |
| **Numerical trajectories** | state + observation spaces | approximate evolution maps where equations + admissible methods are defined | operator-split integration (Lie/Strang) + SNIA projection |

`bridge_to_kernel` carries a **saturated** chemical diagram to a kernel `ChemicalSystem` (a point in the physical-spec
category whose *structural* content is fixed and whose *physical* content — rate laws — is left `RATE_UNKNOWN` unless
supplied). The kernel system is advanced into the numerical-trajectory category only when kinetics are attached.

## The three property layers (separated, and tested as separate)

**Layer 1 — exact structural preservation.** Species identity (name, composition, charge, phase, substance),
stoichiometry, port matching, conservation `E N = 0`, hyperedge identity. This layer **admits strict theorems**, and
XXI §7 proved them on the exact-integer bridge: identity, associativity, tensor (commutative on the signature),
conservation under gluing, port correspondence, catalyst identity, and — crucially — that a glued internal species is
removed from the *net* but **retained as a species**, and that two mechanisms with the **same net equation** bridge to
**different** systems (the mechanism is part of `kernel_signature`, never reduced to its net column).

**Layer 2 — physical interpretability.** Kinetics, thermodynamics, boundary conditions, transport coefficients, phase
applicability. This layer is **PARTIAL**: the bridge does not supply it. A bridged reaction is `RATE_UNKNOWN` by
default, so its *dynamics* is **undefined** until a rate law is attached — and the attached law is a separate,
source-bearing premise that **caps the claim tier** (an `ASSUMED_PARAMETER` kinetic law caps the whole trajectory at
rank 1, no matter how exact Layer 1 is). Transport morphisms here enforce the same identity discipline as Layer 1: an
identity-changing passive transfer (ethanol → dimethyl ether, both C₂H₆O) is refused as a reaction mis-declared as
transport.

**Layer 3 — numerical approximation.** Integrator error, projection error, splitting error, positivity, solver
failure. This layer is **APPROXIMATE** and carries a **measured** error contract, never an exact one. The splitting
error is a property of the *operator structure*: it is zero when there is nothing to split (a single bridged reaction:
Lie ≡ Strang) and nonzero only when reaction and transport do not commute — where it is **measured** against a
monolithic reference (`splitting_convergence`), never assumed.

## Why this is not a dynamics functor (the executable boundary)

A functor into the numerical-trajectory category would have to send each structural object to a *determined*
trajectory. It cannot, and `test_xxii_s7_layer_separation.py` proves why:

- **One structure, many dynamics.** The same proton-transfer diagram bridged with `k = 0.5` and with `k = 5.0` has
  **one** structural signature but **different** trajectories. The structural functor underdetermines the dynamics.
- **Missing kinetics ⇒ undefined dynamics.** A pure structural bridge (no rate laws) cannot be integrated at all
  (`RATE_UNKNOWN` fails closed), so **no** dynamics claim is reachable from structure alone.
- **The layers are independent.** A registered mass-action law makes the *execution identity* certified (XXII-2) yet
  the *claim tier* stays `ASSUMED_PARAMETER` (the kinetic premise), and the integrator *scheme* changes the trajectory
  (where transport makes R, T non-commute) without touching the structural signature.

So a successful bridge is a **conservation + identity certificate** on the structural layer, within the domain the
tests exercise (saturated diagrams, balanced hyperedges, faithful Molecule→Species maps). It does not, and does not
claim to, determine physics or numerics. Extending the claim would require (Layer 2) sourced constitutive laws with a
functorial composition rule of their own, and (Layer 3) a proven — not measured — error contract. Neither is asserted.

## Evidence map

- Layer-1 composition laws: `experiments/sandbox_foundation/tests/test_xxi_s7_composition_laws.py` (22),
  `test_xxi_s7_exact_structural_arithmetic.py` (exact integer `E N` / net).
- Layer separation + the non-dynamics-functor boundary: `test_xxii_s7_layer_separation.py` (9).
- The measured splitting error (Layer 3 contract): `general_coupled.splitting_convergence`; the reactor's
  membrane-vs-bulk trajectories (`general_reactor_demo`) exercise it where transport is present.
