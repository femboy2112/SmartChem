# Compiled synthetic survival recovery — Cycle 3 receipt

**Run date:** 2026-07-27
**Lifecycle status:** `COMPLETE`
**Scientific status:** `SYNTHETIC_RECOVERY_PASSED`
**Validation status:** `NOT_VALIDATED_FOR_BIOLOGY_OR_HUMAN_PREDICTION`

This is the D2b-S synthetic rung, not empirical D2b. The fitter received only a typed
`SurvivalFitInput`: nine TRAIN records plus the fixed protocol. It could not access the six
HOLDOUT records or generator truth. HOLDOUT scoring and truth comparison were separate
post-fit steps.

The records are independent cohort intervals drawn reproducibly from a declared binomial
generator with different retained TRAIN/HOLDOUT seeds. The fitted family was selected before
data generation:

`H(t|d) = (t/lambda)^k exp(beta*d/d_ref)`

and each interval used:

`q[t0,t1|d] = 1 - exp(-(H(t1|d)-H(t0|d)))`.

No repeated cumulative rows were treated as independent observations.

## Recorded result

- known generator: `lambda=100 days`, `k=2`, `beta=0.5`;
- fitted: `lambda=99.3525740368881 days`, `k=2.0174167822069715`,
  `beta=0.4979040450746142`;
- maximum normalized score-gradient norm: `8.337514710802028e-09`;
- approved numerical gradient gate: `1.4901161193847656e-08` (the larger of the
  declared `1e-08` tolerance and the binary64 square-root-epsilon floor);
- conditional likelihood-curvature rank: `3`;
- curvature condition number: `12.405485415529157`;
- HOLDOUT mean binomial negative log score per at-risk member:
  `0.5959545153916355`;
- HOLDOUT Brier score: `0.20434530864800635`.

The retained likelihood-curvature covariance and intervals are conditional diagnostics
under this fixed synthetic binomial model. They are **not** calibrated confidence coverage.
No cohort bootstrap or profile-likelihood coverage study was performed.

## Exact output inventory

1. `human_survival_synthetic_fit`
2. `human_survival_data_governance`
3. `human_survival_parameter_uncertainty`
4. `human_survival_training_predictions`
5. `human_survival_heldout_scoring`

All four pre/post obligations passed: exact synthetic records/split, exact proxy casualty
boundary, independent full-result recomputation, and exact output membership.

## Durable identities

| Artifact | SHA-256 / ID |
|---|---|
| run | `252db1381ffe4079839387af250cf236` |
| source | `0c8a7973b4986d304636443a076cd75716eed807055fab926aeb0d70ca1e6bdf` |
| resolved program | `bc0f2d02e0b732dc1c763dca33dd369bde8444c806063f0379d647b4fac68423` |
| Physical IR | `8de2c5098cc23e821929ba40f7dda3ce326e8b8cad39d46d474173e067226a7f` |
| request | `24de68435e45cfc0be5cfd2ed740dd351e5b629139456967f3093968a9db6c70` |
| plan | `329ed566d7223705f8e93105a8092e7ac4f48493f1b2ebf7d31be13c10675384` |
| approval | `d78d83df512d57c03ebf14a63f035062d17e9c4d905de75f4f364d98b8431c6a` |
| calculation | `e6c7fbde6890e83555d92d8976b377f622315890698ad477da7abe728b6d724e` |
| engine implementation | `39763682e88483e99874e3eae417d5ffef730c5bef8437ace96bd88a0a57870c` |
| compiler/runtime implementation | `d464e35334fab5293f0cf33db51c5af8e01924b27ae5f0414cb7cf121f156d0d` |
| dataset | `239a03c0d66791d48969c242e381d95855ff3e0d6b07986396223aa9f410c225` |
| synthetic fit observable | `b3605a3373b102522dd365eef0a9dd1ec3c886f4ccebfe9158ee1c5cc7cfa9a0` |
| governance observable | `003ab2983616cae53e0925457520e67e40a6d4aea95030dcc01d9299cfbc8683` |
| parameter/curvature observable | `80b51a484e7000867afaf2020b77e1074984f9034f989828e6f27f3f66c6d887` |
| TRAIN prediction observable | `fa106a1a0e2bea4f291bb3e9f6cd45abc66039297551ef27f5be06bce2088111` |
| HOLDOUT scoring observable | `b76c17019f0edac3de2438a5785f7543efcbc683e15e77eae93dae575b888041` |
| certificate | `69ceb1a207aff262130c66ac215c118e7cf48e3817871c2e4ed5e5eda5e75c11` |

The write-once local journal was created at
`/tmp/smartchem-cycle3-final-m5AbRT/run.json`, from
`2026-07-27T11:57:35.284485+00:00` to
`2026-07-27T11:57:35.501394+00:00`. The local JSON is intentionally not committed; this
receipt and the reproducible harness are.

## What this establishes

- the shepherd/compiler can bind content-addressed synthetic records and immutable split
  authority;
- the built-in fitter uses a conditional interval likelihood, not the repeated-cumulative
  binomial error;
- fixed starts agree, stationarity is gated, and singular/ill-conditioned curvature emits
  no fit;
- the runtime independently recomputes every retained output and quarantines forgeries;
- same-generator recovery works for this seeded finite fixture.

## What this does not establish

It does not establish human or animal calibration, a mortality prediction, toxicology,
causality, a biological assembly, environmental transport, LD50/LC50 as a rate or safety
threshold, individual risk, competing-risk incidence, external validation, confidence
coverage, or authority for experimentation. `COMPLETE` is only the artifact lifecycle
status. D2a remains underidentified, and empirical D2b remains open.

## Verification

- focused Cycle 3/registry suite: `36 passed`;
- full maintained suite before the receipt-only documentation change:
  `1231 passed, 14 skipped, 1 xfailed`;
- independent scientific re-review: `SHIP`;
- independent runtime review: runtime gates `SHIP`; its missing-receipt blocker is discharged
  by this file;
- `python -m compileall -q smartchem experiments tests`: passed;
- `git diff --check`: passed.
