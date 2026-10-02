# 0.9.5 stress -- BASELINE

- tree `d26f0eb`, smartchem `0.9.0a1`, python 3.12.3
- config: seed 20260929, 40 cheap-family iterations (methyl-acetate family, DAG every 6th, profile noninterference every 6th), 3 fresh processes per cross-process spec, 1 isopentyl iteration(s); wall 182.7s
- generated 2026-09-29T21:50:47Z

| invariant | status | pass | fail | pending | vacuous |
|---|---|---:|---:|---:|---:|
| roundtrip_byte_identity | PASS | 41 | 0 | 0 | 0 |
| compile_replay_acceptance | PASS | 41 | 0 | 0 | 0 |
| cross_process_result_digest | PASS | 6 | 0 | 0 | 0 |
| profile_search_noninterference | PASS | 112 | 0 | 0 | 0 |
| kekule_identity_law | PENDING | 0 | 0 | 1 | 0 |
| receipt_consistency | PASS | 158 | 0 | 0 | 0 |
| cache_on_off_identity | PENDING | 0 | 0 | 41 | 0 |
| policy_only_promised_changes | PASS (+pending) | 123 | 0 | 41 | 0 |

- **kekule_identity_law**: smartchem.experiment.stock.structure_key absent (S7 not landed): the law cannot be checked
- **cache_on_off_identity**: set_enumeration_cache_enabled absent on this tree (pre-0.9.5 layer)
- **policy_only_promised_changes**: smartchem.verification.VerificationPolicy/load_response absent: the 'thin under a canonical requirement is refused' and policy-object half is PENDING (legacy-kwarg half ran)

## Resources (long-lived process)

- RSS first/last/max: 32.9 / 33.7 / 33.7 MB
- **RSS slope (post-warmup 80%): 5.05 KB/iteration** (all points: 13.74 KB/iteration)
- RSS after each isopentyl iteration (KB): [43560]
- Molecule.canonical lru currsize first/last/max: [172, 199, 199] (maxsize 8192)
- enumeration cache stats first/last: [None, None] (null == layer absent)

Latency (seconds):

| op | n | p50 | p90 | p99 | max |
|---|---:|---:|---:|---:|---:|
| compile | 41 | 0.1143 | 0.6713 | 73.0573 | 73.0573 |
| serialize | 41 | 0.002 | 0.0025 | 0.0105 | 0.0105 |
| load | 41 | 0.1043 | 0.4805 | 7.6807 | 7.6807 |
| roundtrip | 41 | 0.1071 | 0.4828 | 8.0896 | 8.0896 |
