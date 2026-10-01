# 0.9.5 verification performance -- AFTER

- tree commit: `74414eb`; smartchem `0.9.5a1`; python 3.12.3
- layer (smartchem.verification): `{'present': True, 'load_response': False, 'enumeration_cache': True, 'budget': True}`
- declared runs: COLD n=3 (fresh subprocess each), WARM n=5 (one process, after 1 discarded cold load); p90 = nearest-rank; worst = max
- box: loadavg at start [4.41, 4.89, 6.57], at end [4.85, 5.15, 5.72] (timings on a shared box: +-30%)
- wall: 790s; generated 2026-10-01T16:07:09Z

| payload | bytes | cold med | cold p90 | cold worst | warm med | warm p90 | warm worst | peak RSS MB | cold status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| a_tiny_linear | 12,415 | 0.48 | 0.48 | 0.48 | 0.14 | 0.14 | 0.14 | 32 | ok |
| b1_isopentyl_noprofile | 234,458 | 25.37 | 26.14 | 26.14 | 6.48 | 7.52 | 7.52 | 41 | ok |
| b2_isopentyl_fitbench | 663,144 | 34.07 | 38.26 | 38.26 | 10.73 | 11.01 | 11.01 | 46 | ok |
| c1_methyl_acetate_dag | 21,327 | 0.98 | 1.14 | 1.14 | 0.40 | 0.42 | 0.42 | 32 | ok |
| c2_isopentyl_dag | 1,140,575 | 58.15 | 58.23 | 58.23 | 37.35 | 39.33 | 39.33 | 65 | ok |
| d_diels_alder | 7,834 | 0.67 | 0.68 | 0.68 | 0.08 | 0.09 | 0.09 | 32 | ok |
| e_legacy_v08_isopentyl | 121,195 | 1.90 | 1.91 | 1.91 | 0.23 | 0.25 | 0.25 | 34 | ok |
| f_hostile2_45 | 14,278 | 0.21 | 0.21 | 0.21 | 0.07 | 0.08 | 0.08 | 32 | REFUSED(VerificationBudgetExceeded) |

## Samples (seconds) and 0.9.5-layer facts

- **a_tiny_linear** (smiles:CC(=O)OC linear, max_depth=2, water, stock CO/CC(=O)O): cold [0.476, 0.465, 0.481], warm [0.141, 0.142, 0.137, 0.136, 0.136]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=10, misses=2, entries=2, retained_transforms=20, retained_size=46); receipt work None; receipt facets None
- **b1_isopentyl_noprofile** (isopentyl acetate thick 27-route, no capability profile): cold [26.139, 24.716, 25.371], warm [6.481, 6.416, 7.522, 7.068, 6.23]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=90, misses=18, entries=18, retained_transforms=702, retained_size=851); receipt work None; receipt facets None
- **b2_isopentyl_fitbench** (isopentyl acetate thick 27-route + isopentyl_capability_fit_bench()): cold [31.78, 34.067, 38.26], warm [9.683, 10.732, 10.763, 9.861, 11.008]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=90, misses=18, entries=18, retained_transforms=702, retained_size=851); receipt work None; receipt facets None
- **c1_methyl_acetate_dag** (methyl acetate CAPPED_SCISSION_CONVERGENT DAG, max_total_minutes=30): cold [0.979, 0.965, 1.139], warm [0.409, 0.399, 0.394, 0.417, 0.401]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=25, misses=5, entries=5, retained_transforms=56, retained_size=144); receipt work None; receipt facets None
- **c2_isopentyl_dag** (isopentyl acetate CAPPED_SCISSION_CONVERGENT DAG, ProcessBounds.quick()): cold [58.146, 58.231, 53.24], warm [33.968, 37.68, 37.349, 39.327, 35.129]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=145, misses=29, entries=29, retained_transforms=832, retained_size=1230); receipt work None; receipt facets None
- **d_diels_alder** (Diels-Alder control C1CC=CCC1, certified-route-v07): cold [0.677, 0.665, 0.673], warm [0.079, 0.085, 0.077, 0.077, 0.085]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=5, misses=1, entries=1, retained_transforms=1, retained_size=62); receipt work None; receipt facets None
- **e_legacy_v08_isopentyl** (real v0.8 fixture response_isopentyl_acetate.json (legacy read leg)): cold [1.905, 1.904, 1.832], warm [0.228, 0.227, 0.252, 0.229, 0.232]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=0, misses=0, entries=0, retained_transforms=0, retained_size=0); receipt work None; receipt facets None
- **f_hostile2_45** (hostile large target: 45-heavy-atom wax ester, 6 helper reagents, default bounds (C7-1)): cold [0.214, 0.212, 0.213], warm [0.065, 0.082, 0.066, 0.065, 0.069]; entry `service.response_from_payload`; warm statuses ['REFUSED(VerificationBudgetExceeded)']; cache stats EnumerationCacheStats(hits=0, misses=0, entries=0, retained_transforms=0, retained_size=0); receipt work None; receipt facets None
