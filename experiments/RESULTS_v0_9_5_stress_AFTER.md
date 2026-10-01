# 0.9.5 stress -- AFTER

- tree `74414eb`, smartchem `0.9.5a1`, python 3.12.3
- config: seed 20260929, 40 cheap-family iterations (methyl-acetate family, DAG every 6th, profile noninterference every 6th), 3 fresh processes per cross-process spec, 1 isopentyl iteration(s); wall 243.9s
- generated 2026-10-01T17:38:02Z

| invariant | status | pass | fail | pending | vacuous |
|---|---|---:|---:|---:|---:|
| roundtrip_byte_identity | PASS | 41 | 0 | 0 | 0 |
| compile_replay_acceptance | PASS | 41 | 0 | 0 | 0 |
| cross_process_result_digest | PASS | 6 | 0 | 0 | 0 |
| profile_search_noninterference | PASS | 112 | 0 | 0 | 0 |
| kekule_identity_law | PASS | 10 | 0 | 0 | 0 |
| receipt_consistency | PASS | 158 | 0 | 0 | 0 |
| cache_on_off_identity | PASS | 41 | 0 | 0 | 0 |
| policy_only_promised_changes | PASS | 246 | 0 | 0 | 0 |


## Resources (long-lived process)

- RSS first/last/max: 33.8 / 34.6 / 34.6 MB
- **RSS slope (post-warmup 80%): 15.1 KB/iteration** (all points: 17.46 KB/iteration)
- RSS after each isopentyl iteration (KB): [49064]
- Molecule.canonical lru currsize first/last/max: [172, 199, 199] (maxsize 8192)
- enumeration cache stats first/last: ['EnumerationCacheStats(hits=32, misses=8, entries=4, retained_transforms=64, retained_size=128)', 'EnumerationCacheStats(hits=640, misses=80, entries=8, retained_transforms=120, retained_size=244)'] (null == layer absent)

Latency (seconds):

| op | n | p50 | p90 | p99 | max |
|---|---:|---:|---:|---:|---:|
| compile | 41 | 0.171 | 0.6888 | 71.6455 | 71.6455 |
| serialize | 41 | 0.002 | 0.0035 | 0.0104 | 0.0104 |
| load | 41 | 0.1099 | 0.418 | 7.2136 | 7.2136 |
| roundtrip | 41 | 0.1314 | 0.388 | 5.6465 | 5.6465 |
