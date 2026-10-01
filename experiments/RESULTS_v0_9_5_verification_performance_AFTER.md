# 0.9.5 verification performance -- AFTER

- tree commit: `037a9fa`; smartchem `0.9.5a1`; python 3.12.3
- layer (smartchem.verification): `{'present': True, 'load_response': True, 'enumeration_cache': True, 'budget': True}`
- declared runs: COLD n=3 (fresh subprocess each), WARM n=5 (one process, after 1 discarded cold load); p90 = nearest-rank; worst = max
- box: loadavg at start [1.6, 1.11, 1.58], at end [2.27, 2.49, 2.15] (timings on a shared box: +-30%)
- wall: 1023s; generated 2026-10-01T18:45:21Z

| payload | bytes | cold med | cold p90 | cold worst | warm med | warm p90 | warm worst | peak RSS MB | cold status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| a_tiny_linear | 12,415 | 0.41 | 0.41 | 0.41 | 0.12 | 0.13 | 0.13 | 32 | ok |
| b1_isopentyl_noprofile | 234,458 | 23.94 | 25.37 | 25.37 | 5.68 | 5.70 | 5.70 | 41 | ok |
| b2_isopentyl_fitbench | 663,144 | 27.48 | 27.59 | 27.59 | 8.82 | 8.92 | 8.92 | 46 | ok |
| c1_methyl_acetate_dag | 21,327 | 0.81 | 0.82 | 0.82 | 0.33 | 0.34 | 0.34 | 33 | ok |
| c2_isopentyl_dag | 1,140,575 | 45.85 | 46.92 | 46.92 | 27.18 | 31.64 | 31.64 | 66 | ok |
| d_diels_alder | 7,834 | 0.58 | 0.59 | 0.59 | 0.06 | 0.06 | 0.06 | 32 | ok |
| e_legacy_v08_isopentyl | 121,195 | 1.67 | 1.68 | 1.68 | 0.20 | 0.22 | 0.22 | 34 | ok |
| f_hostile2_45 | 14,278 | 0.19 | 0.19 | 0.19 | 0.06 | 0.07 | 0.07 | 32 | REFUSED(VerificationBudgetExceeded) |

## Samples (seconds) and 0.9.5-layer facts

- **a_tiny_linear** (smiles:CC(=O)OC linear, max_depth=2, water, stock CO/CC(=O)O): cold [0.407, 0.405, 0.406], warm [0.115, 0.121, 0.127, 0.118, 0.118]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=10, misses=2, entries=2, retained_transforms=20, retained_size=46); receipt work None; receipt facets None
- **b1_isopentyl_noprofile** (isopentyl acetate thick 27-route, no capability profile): cold [23.936, 23.901, 25.373], warm [5.696, 5.699, 5.67, 5.679, 5.672]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=90, misses=18, entries=18, retained_transforms=702, retained_size=851); receipt work None; receipt facets None
- **b2_isopentyl_fitbench** (isopentyl acetate thick 27-route + isopentyl_capability_fit_bench()): cold [27.587, 27.315, 27.479], warm [8.923, 8.861, 8.82, 8.803, 8.79]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=90, misses=18, entries=18, retained_transforms=702, retained_size=851); receipt work None; receipt facets None
- **c1_methyl_acetate_dag** (methyl acetate CAPPED_SCISSION_CONVERGENT DAG, max_total_minutes=30): cold [0.816, 0.812, 0.811], warm [0.33, 0.325, 0.328, 0.342, 0.328]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=25, misses=5, entries=5, retained_transforms=56, retained_size=144); receipt work None; receipt facets None
- **c2_isopentyl_dag** (isopentyl acetate CAPPED_SCISSION_CONVERGENT DAG, ProcessBounds.quick()): cold [45.385, 46.917, 45.846], warm [26.982, 27.062, 27.177, 29.229, 31.641]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=145, misses=29, entries=29, retained_transforms=832, retained_size=1230); receipt work None; receipt facets None
- **d_diels_alder** (Diels-Alder control C1CC=CCC1, certified-route-v07): cold [0.576, 0.586, 0.581], warm [0.055, 0.055, 0.056, 0.056, 0.055]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=5, misses=1, entries=1, retained_transforms=1, retained_size=62); receipt work None; receipt facets None
- **e_legacy_v08_isopentyl** (real v0.8 fixture response_isopentyl_acetate.json (legacy read leg)): cold [1.666, 1.675, 1.677], warm [0.202, 0.203, 0.218, 0.192, 0.186]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=0, misses=0, entries=0, retained_transforms=0, retained_size=0); receipt work None; receipt facets None
- **f_hostile2_45** (hostile large target: 45-heavy-atom wax ester, 6 helper reagents, default bounds (C7-1)): cold [0.191, 0.191, 0.181], warm [0.057, 0.07, 0.058, 0.057, 0.057]; entry `service.response_from_payload`; warm statuses ['REFUSED(VerificationBudgetExceeded)']; cache stats EnumerationCacheStats(hits=0, misses=0, entries=0, retained_transforms=0, retained_size=0); receipt work None; receipt facets None
