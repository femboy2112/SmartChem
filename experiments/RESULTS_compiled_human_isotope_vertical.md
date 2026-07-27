# Compiled human–isotope identifiability result — 2026-07-27

## Verdict

`COMPLETE` as an approved source-to-certificate **structural identifiability**
calculation.

The scientific result is negative and precise:

```text
UNDERIDENTIFIED_DYNAMIC_MODEL
ValidationStatus = UNVALIDATED
ClaimScope = EXPERIMENTAL_PROXY
EvidenceStatus = STRUCTURAL_TOY
```

A single hypothetical oral `LD50 = 100 mg/kg`, administered under the declared one-day
synthetic protocol and observed through day 14, contributes only the constraint

```text
P(declared event by the observation window | declared endpoint protocol) = 0.5
```

It is not a rate. It does not identify the time shape, dose-response curve, background versus
exposure hazard, toxicokinetic link, competing risks, assembly, or any individual outcome.
No observed human or animal record was used.

`COMPLETE` means the requested artifact lifecycle completed and every declared compiler/runtime
obligation passed. It does not mean the proxy is calibrated, validated, clinically meaningful,
or true.

## The constructive non-identifiability result

The executor retained two explicit normalized survival-family witnesses:

| Family | Cumulative mortality at half-window | Cumulative mortality at endpoint |
|---|---:|---:|
| Exponential | `0.2928932188134524` | `0.5` |
| Weibull, shape 2 | `0.1591035847462855` | `0.5` |

The independent formulas are:

```text
F_exp(1/2) = 1 - 2^(-1/2) = 0.2928932188134524
F_w2(1/2)  = 1 - 2^(-1/4) = 0.1591035847462855
F_exp(1) = F_w2(1) = 0.5
```

The endpoint cannot distinguish these two families, yet a time-resolved observation away from
the endpoint can. This is a witness of non-uniqueness, not a fit and not a human mortality
prediction. The two families are not advertised as an exhaustive list of possible models.

## Frozen scientist interpretation

The preserved source asked for a generic human represented as a scientist-chosen
differentiated bundle, using a modified radioactive-decay analogy affected by environmental
constraints and the LD50 concept.

The typed interpretation selected for this compiler acceptance run was:

- target: synthetic cohort all-cause survival identifiability;
- population: one declared synthetic generic-human proxy cohort;
- granularity: two lumped functional classes, `repair reserve` and
  `background failure channel`;
- assembly: a redundancy/quorum and repair hypothesis;
- environmental mechanism: exposure changes redundancy or repair state, not a nuclear decay
  constant;
- exposure: a synthetic oral administered-dose protocol;
- toxicokinetics: one declared placeholder source-to-internal-burden link, with no fitted
  parameters or validation;
- endpoint: hypothetical `LD50`, `100 mg/kg`, one-day exposure, 14-day observation window;
- calibration inventory: one synthetic endpoint record, one dose, one observation time, no
  dynamic uncertainty model, and no held-out data.

Every choice is in the plan digest. Changing target, population, event, component
differentiation, assembly, exposure, route, endpoint, toxicokinetic link, data digest,
uncertainty, validation split, or output contract invalidates approval.

## Exact retained output

The executor emitted all three requested structured observables:

1. `human_isotope_identifiability` — status, validation state, constraint, free parameters,
   missing evidence, transport, casualties, witnesses, and discriminating experiments;
2. `human_isotope_constraint_inventory` — the complete typed endpoint plus environmental,
   population, toxicokinetic, and calibration identities;
3. `human_isotope_family_witnesses` — both complete normalized witnesses and their parameters.

The current executor refuses any change to observable membership, support, resolution,
precision, coverage, diagnostics, or retention. It also blocks individual-lifetime output,
cause-specific cumulative incidence without all competing hazards, functional-threshold
targets without nonlethal target-specific endpoint semantics, observational or cross-species
evidence without data-governance/applicability adapters, and richer calibration evidence
without a data-bound validation executor.

## Free parameters and missing evidence

The diagnostic leaves at least these model axes free:

- state dynamics `F`;
- cause-specific hazards `G_k`;
- assembly map `A`;
- background hazard;
- exposure-response parameters;
- repair and interaction parameters;
- toxicokinetic parameters;
- dependence among competing risks.

The certificate carries these missing-evidence boundaries:

- a single median endpoint does not identify a dynamic family;
- assembly and hazard mechanisms lack independent calibration;
- no evidence separates part-hazard change from redundancy or repair change;
- no multiple exposure levels or observation times;
- no quantified dynamic calibration uncertainty;
- no held-out validation.

The next discriminating work would require multi-time and multi-exposure observations,
mechanism-specific state or repair measurements, and held-out validation on ethically and
legally obtained data. Those are proposed evidence gates, not authorization to collect or
experiment on humans.

## Casualty boundary

The result explicitly excludes:

- literal human/isotope identity;
- nuclear memorylessness or a constant nuclear rate at organism scale;
- a material human half-life;
- daughter-nuclide or radioactive-chain biological semantics;
- LD50/LC50 as a rate or hazard;
- a universal human LD50/LC50;
- unique identification of dynamics, dose response, toxicokinetics, or assembly;
- mortality prediction for any actual person or population;
- causal, clinical, regulatory, or toxicological safety claims;
- authority for direct human experimentation;
- validation or vindication of the original metaphor.

Successful refinement therefore does not promote the metaphor to truth.

## Run and lineage

The ignored JSON journal is a mutable local run artifact; this durable receipt records the
particular final reviewed run cited here.

| Record | Value |
|---|---|
| status | `COMPLETE` |
| run ID | `e1990973884d4bb0883a94c916875033` |
| started | `2026-07-27T08:18:39.901817+00:00` |
| updated | `2026-07-27T08:18:39.967627+00:00` |
| source digest | `8135494f3da6d6f30a926aa5e030b3ab0dcddaccc0e592a85558a54f164dc7bc` |
| shepherd session digest | `845eab443bbc55039e5bc43f2c2a99b163c00df8bcd574a5e1724db7f3c14963` |
| resolved-program digest | `ef6ee1c045f85a04fc01043d3ce07146d4e159fff9867ad7d1a377edaa1cdf2f` |
| Physical IR digest | `cab821c602cd354e04885cf5f28d699a0f5e8c65bca5451bac559da2d0774525` |
| request digest | `558f2d6fd7a35e728b1d0824afa4327ebebca697041dd8cf4ae798c66fb099c5` |
| plan digest | `532e0a3f43f166d9ab7a585358afc98d036d54e32e39b6a2f2cc46803232a65e` |
| approval digest | `62db7d405882c63bca560d78e67eac37e39f0a5a531bdc53fbe3a6e078ebb541` |
| calculation digest | `7103025e54bf045b3ce909872561db08bba418ad29495e938da080de47ab25fd` |
| engine implementation digest | `77bc20589c6a3d132ab7ca76b614147d25a35b63247124beffe09817cda98727` |
| compiler implementation digest | `3d39b06b52bc88ce7a7ae5c08824d33e2667a6a6745f042d9a420659f75bafab` |
| identifiability observable digest | `52bddf580439ff49bd263b45be0460ed988149ad429f2d78ca68a952da80d5c1` |
| constraint-inventory observable digest | `70f2da2a121371bd1f038b2d70c8d4e14ce7ac0347187b6c8ca2289731233cf3` |
| family-witness observable digest | `4706f79dc8131183fd04e930780db09377cf04052d668ff9e64d9e604f50942d` |
| certificate artifact content digest | `86d164a82106230cde91ebe62ec7346bd0c110352127ddfd99a8e1f2491ef991` |
| retained checkpoints | `1` |
| retained artifacts | `7` |

## Obligation results

All five required obligations passed:

1. the complete typed scientist-owned subject is present and supported;
2. exact structural-toy experimental-proxy scope and every casualty remain intact;
3. the LD50 remains a dose/window endpoint and cannot become a rate;
4. an independent recomputation equals the retained underidentified/`UNVALIDATED` diagnostic
   and both witnesses;
5. emitted observable identities exactly equal the frozen output contract.

An independent receipt checker also recomputes both half-window values directly from the
closed forms and compares the current source/request/plan/calculation/compiler identities
against the journal.

The final repository verification was:

```text
.venv/bin/python -m pytest -q -rs
1169 passed, 14 skipped, 1 xfailed in 19.72s

focused human/reaction/water compatibility gate
112 passed in 1.15s

independent final journal and witness recomputation
INDEPENDENT_RECEIPT_CHECK=PASS
```

## Scientific boundary

The endpoint semantics follow OECD Test Guideline 425, which defines LD50 as a statistically
derived oral dose tied to a tested population and protocol and treats uncertainty intervals as
part of a meaningful estimate:

- [OECD Test Guideline 425 (2022)](https://www.oecd.org/content/dam/oecd/en/publications/reports/2022/06/test-no-425-acute-oral-toxicity-up-and-down-procedure_g1gh2953/9789264071049-en.pdf).

The assembly vocabulary is motivated by reliability theory, while the certificate keeps that
theory at hypothesis status:

- [Gavrilov and Gavrilova, *The reliability theory of aging and longevity*
  (2001)](https://doi.org/10.1006/jtbi.2001.2430).

For a cause-specific target, cumulative incidence depends on the competing hazards as well as
the cause-specific hazard. That is why the present all-cause witness executor blocks
cause-specific output:

- [Andersen et al., *Competing risks in epidemiology: possibilities and pitfalls*
  (2012)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3396320/).

These sources establish vocabulary and statistical boundaries. They do not validate this
synthetic proxy or any human mortality model.
