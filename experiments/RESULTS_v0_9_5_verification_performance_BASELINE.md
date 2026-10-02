# 0.9.5 verification performance -- BASELINE

- tree commit: `d26f0eb`; smartchem `0.9.0a1`; python 3.12.3
- layer (smartchem.verification): `{'present': False}`
- declared runs: COLD n=3 (fresh subprocess each), WARM n=5 (one process, after 1 discarded cold load); p90 = nearest-rank; worst = max
- box: loadavg at start [2.89, 3.35, 3.03], at end [4.94, 4.03, 3.29] (timings on a shared box: +-30%)
- wall: 5379s; generated 2026-09-29T23:12:56Z

| payload | bytes | cold med | cold p90 | cold worst | warm med | warm p90 | warm worst | peak RSS MB | cold status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| a_tiny_linear | 12,415 | 0.42 | 0.43 | 0.43 | 0.14 | 0.15 | 0.15 | 31 | ok |
| b1_isopentyl_noprofile | 234,431 | 26.14 | 27.10 | 27.10 | 7.66 | 8.17 | 8.17 | 38 | ok |
| b2_isopentyl_fitbench | 662,408 | 30.08 | 30.64 | 30.64 | 10.91 | 12.63 | 12.63 | 42 | ok |
| c1_methyl_acetate_dag | 21,327 | 0.89 | 0.91 | 0.91 | 0.50 | 0.58 | 0.58 | 32 | ok |
| c2_isopentyl_dag | 1,140,575 | 49.93 | 52.27 | 52.27 | 31.92 | 33.09 | 33.09 | 59 | ok |
| d_diels_alder | 7,834 | 0.62 | 0.63 | 0.63 | 0.06 | 0.06 | 0.06 | 31 | ok |
| e_legacy_v08_isopentyl | 121,195 | 1.87 | 1.89 | 1.89 | 0.27 | 0.30 | 0.30 | 33 | ok |
| f_hostile2_45 | 14,278 | 129.85 | 141.07 | 141.07 | 31.70 | 32.37 | 32.37 | 88 | ok |

## Samples (seconds) and 0.9.5-layer facts

- **a_tiny_linear** (smiles:CC(=O)OC linear, max_depth=2, water, stock CO/CC(=O)O): cold [0.404, 0.42, 0.43], warm [0.143, 0.146, 0.147, 0.143, 0.145]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats absent; receipt work None; receipt facets None
- **b1_isopentyl_noprofile** (isopentyl acetate thick 27-route, no capability profile): cold [25.157, 26.138, 27.104], warm [7.811, 7.629, 8.169, 7.66, 6.917]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats absent; receipt work None; receipt facets None
- **b2_isopentyl_fitbench** (isopentyl acetate thick 27-route + isopentyl_capability_fit_bench()): cold [30.643, 28.945, 30.08], warm [10.702, 10.906, 10.797, 11.023, 12.626]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats absent; receipt work None; receipt facets None
- **c1_methyl_acetate_dag** (methyl acetate CAPPED_SCISSION_CONVERGENT DAG, max_total_minutes=30): cold [0.888, 0.855, 0.913], warm [0.522, 0.468, 0.466, 0.58, 0.503]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats absent; receipt work None; receipt facets None
- **c2_isopentyl_dag** (isopentyl acetate CAPPED_SCISSION_CONVERGENT DAG, ProcessBounds.quick()): cold [52.27, 49.927, 47.034], warm [31.216, 31.92, 31.962, 33.087, 31.882]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=0, misses=0, entries=0, retained_transforms=0); receipt work None; receipt facets None
- **d_diels_alder** (Diels-Alder control C1CC=CCC1, certified-route-v07): cold [0.577, 0.634, 0.619], warm [0.059, 0.058, 0.059, 0.059, 0.058]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=0, misses=0, entries=0, retained_transforms=0); receipt work None; receipt facets None
- **e_legacy_v08_isopentyl** (real v0.8 fixture response_isopentyl_acetate.json (legacy read leg)): cold [1.894, 1.868, 1.718], warm [0.3, 0.272, 0.29, 0.259, 0.264]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=0, misses=0, entries=0, retained_transforms=0); receipt work None; receipt facets None
- **f_hostile2_45** (hostile large target: 45-heavy-atom wax ester, 6 helper reagents, default bounds (C7-1)): cold [122.052, 129.852, 141.07], warm [31.702, 30.062, 30.028, 32.368, 32.06]; entry `service.response_from_payload`; warm statuses ['ok']; cache stats EnumerationCacheStats(hits=0, misses=0, entries=0, retained_transforms=0); receipt work None; receipt facets None
