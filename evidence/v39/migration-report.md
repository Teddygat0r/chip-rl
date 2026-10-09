# v39 block-quant migration run

Original saved-environment v39 plan: never executed. This run used a newly generated private 128-bit host seed on the dot cloud computer; it is not a replay of v38 seed_1. The original `predeclared.json` is unchanged. `migration-predeclared.json` records only the new seed hash and frozen candidate hashes. No RTL candidate or qualification gate was changed.

## Validation and accounting

- Matching toolchain: Yosys 0.52 (fee39a3284c90249e1d9684cf6944ffbbcbb8f90), Icarus/VVP 12.0, ABC; tool fingerprint matches v38 (`9f09818abb592bcd94083f044465209e067389983ec3f90f93ca78a8070e7ac8`).
- Focused block-quant tests: 9/9 passed. Full source unittest suite with authentic historical v34 summary restored: 219/219 passed. The first full-suite run failed only because that archival summary was absent from the transfer.
- Attempt 1 stopped safely at the original 1 GB operational artifact guard after 32/33 evaluations, before N=15/chunked4. Attempt 2 reused the same private seed, candidates, workload definitions, tools, and gates; its complete 33-call sweep passed.
- Total evaluator invocations: 65 (32 interrupted attempt + 33 complete rerun). Unique new-N/design combinations verified: 33. Fresh synthesis builds across both attempts: 48. Verified simulation cache hits: 450. Simulator log invocations: 792 (four RTL/mapped arithmetic/traffic simulation logs per fresh verified pairing).
- Total new allocated migration evidence: 978,522,112 bytes, below the 4 GB cap. Workspace free: 30,822,694,912 bytes; /tmp free: 5,215,318,016 bytes.
- All 33 requested cases passed exact-integer functional RTL and mapped-netlist validation. Formal and physical stages were not run.

## Per-N service gates

Every row below passed the functional RTL/mapped validation. `pass` means area ≤4× serial, completion ≤1× serial, and II ≤2N+3 on that N; the fixed reward remains scored only on N={1,2,4,8,16}.

| N | serial | parallel | chunked4 |
|---:|:---:|:---:|:---:|
| 3 | pass | pass | pass |
| 5 | pass | pass | pass |
| 6 | pass | pass | pass |
| 7 | pass | pass | pass |
| 9 | pass | pass | pass |
| 10 | pass | pass | pass |
| 11 | pass | pass | pass |
| 12 | pass | pass | pass |
| 13 | pass | pass | pass |
| 14 | pass | pass | pass |
| 15 | pass | FAIL: area >4× | pass |

Only new-N gate failure: parallel N=15 has 9080 cells versus 2222 serial cells (4.0864×); completion and II gates pass. This is a measured result, not a correctness failure.

Fixed five-point rewards and service qualification: serial 0.0 / yes; parallel 0.0 / no (historical N=16 area gate); chunked4 0.07705624926402332 / yes.

## Source change summary

- `META/dirty.patch` carries the pre-transfer changes in seven tracked block-quant contract, evaluator, oracle, scoring, spec, workload, and unit-test files. The measured N domain expands to all integers 1..16; the original five reward-scored Ns and hard gates remain fixed.
- The migration added `migration-predeclared.json`, amended the v39 runner to read it, and recorded `attempt1-resource-stop.json` plus `migration-summary.json`. The runner’s artifact guard now measures aggregate allocation across both attempts against the authorized 4 GB cap while preserving a 5 GB workspace and 750 MB /tmp free floor.
- Candidate RTL source hashes exactly match the frozen declarations. No code was published externally.
