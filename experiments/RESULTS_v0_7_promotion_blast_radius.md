# v0.7 default-promotion blast-radius + performance (SS8/SS9)

Corpus n=22 targets x 2 profiles through the REAL run_compilation; only algebra_profile varies.

| target | kind | legacy exit/routes | certified exit/routes | new routes | algebra digest moved |
|---|---|---|---|---|---|
| da-alkene | da | 3/0 | 3/0 | 0 | yes |
| da-alkyne | da | 3/0 | 3/0 | 0 | yes |
| da-aza | da | 3/0 | 3/0 | 0 | yes |
| da-oxa | da | 3/0 | 3/0 | 0 | yes |
| da-thia | da | 3/0 | 3/0 | 0 | yes |
| da-aza-diene | da | 3/0 | 3/0 | 0 | yes |
| da-oxa-diene | da | 3/0 | 3/0 | 0 | yes |
| da-thia-diene | da | 3/0 | 3/0 | 0 | yes |
| da-holdout-methylcyclohexene | da | 3/0 | 3/0 | 0 | yes |
| da-holdout-substituted | da | 3/0 | 3/0 | 0 | yes |
| ctl-ethanol | nonda | 0/0 | 0/0 | 0 | yes |
| ctl-methyl-acetate | nonda | 0/2 | 0/2 | 0 | yes |
| ctl-acetic-acid | nonda | 0/0 | 0/0 | 0 | yes |
| ctl-butane | nonda | 4/0 | 4/0 | 0 | yes |
| ctl-cyclohexane | nonda | 3/0 | 3/0 | 0 | yes |
| ctl-cyclopentane | nonda | 3/0 | 3/0 | 0 | yes |
| ctl-benzene | nonda | 3/0 | 3/0 | 0 | yes |
| ctl-phenol | nonda | 3/0 | 3/0 | 0 | yes |
| hostile-enone | nonda | 3/0 | 3/0 | 0 | yes |
| lit-paracetamol | nonda | 4/2 | 4/2 | 0 | yes |
| lit-aspirin | nonda | 4/2 | 4/2 | 0 | yes |
| lit-caffeine | nonda | 4/1 | 4/1 | 0 | yes |

## Performance (SS9): wall-clock seconds, certified vs legacy, same corpus
- legacy  median=12.1ms p90=534.6ms p95=616.0ms max=1582.3ms
- certified median=18.0ms p90=532.8ms p95=633.4ms max=1653.9ms
- worst per-target slowdown factor: 3.95x
- transforms considered: legacy median=0 max=458; certified median=1 max=458

## Topology + budget samples
- DAG C1CC=CCC1: legacy exit 3/0 routes, certified exit 3/0 routes; digest moved: True
- starved budget=1 CC(=O)OC: legacy complete=False, certified complete=False (both must be False -- honest incompleteness)

## Stocked promotion demo (the intended benefit, an ALLOWED delta)
- cyclohexene + stock(butadiene, ethylene): legacy exit 3/0 routes, certified exit 0/1 routes; new certified routes oracle-vouched: True. (Certified turns a legacy NO_ROUTE into a class-vouched DA route -- exactly the promotion.)

## Co-ranking targets (Wave-C F1): legacy capped route + certified DA candidates co-exist, WITH stock
| target | legacy exit/routes | certified exit/routes | legacy routes ⊆ certified | new certified routes |
|---|---|---|---|---|
| corank-methyl-ester-cyclohexene | 0/1 | 4/1 | True | 0 |
| corank-acetate-cyclohexene | 4/0 | 4/4 | True | 4 |
| corank-amide-cyclohexene | 0/1 | 4/1 | True | 0 |
- eviction probe (COC(=O)C1CCC=CC1, max_routes=1): certified top-1 preserves legacy's top route: True. (No legacy route evicted from the top slot by a higher-ranked DA route.)

## Delta classification
- **No unacceptable deltas and nothing to inspect.** Every legacy route preserved -- including the CO-RANKING cases where a legacy capped route and certified DA candidates co-exist with stock present (Wave-C F1 non-vacuous); every non-DA target byte-identical; every new certified step oracle-vouched (all-steps guard); no false COMPLETE; no runtime explosion; no top-1 eviction. NOTABLE (allowed) deltas below are documented, not regressions.
- **NOTABLE** [corank-methyl-ester-cyclohexene]: certified honest-incomplete at default budget (wider enumeration); legacy route preserved -- higher bounded work, not a false complete
- **NOTABLE** [corank-amide-cyclohexene]: certified honest-incomplete at default budget (wider enumeration); legacy route preserved -- higher bounded work, not a false complete
