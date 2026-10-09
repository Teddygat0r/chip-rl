# v38 three-seed block quantization sensitivity check

This is a bounded workload check of the [v37 fixed scoring contract](block-quant-reward-v37.md), not a change to it. The [source/evaluator freeze](../evidence/v38/source-evaluator-freeze.json) was committed at `9c44e58` **before** three new trusted-host seeds were drawn. It records exact emitted hashes for serial, fully parallel and chunked-four RTL, plus every block-quant evaluator, scorer, oracle, workload, simulation and contract file; the evaluator recipe, contract and tool fingerprints were checked again before execution. No architecture, threshold, scoring or evaluator code changed. All 15 source/N netlists existed in the exact synthesis cache; the run made **zero new synthesis builds**.

Exactly three distinct new seeds were drawn once and retained privately. For each seed, every N={1,2,4,8,16} used identical candidate/baseline operands and traffic across the three designs. The unchanged evaluator ran separate unscored arithmetic and reset/backpressure probes, including the 257-cycle stall, then measured scored traffic and saturated-stream II. All **45 design/N cases** passed functional and progress validation on RTL and mapped netlists. After each seed, the runner checked workload hashes, serial-baseline metric identity, the frozen scorer result and the mandatory parallel N=16 area failure before continuing. The [public raw tables](../evidence/v38/summary.json) contain every candidate and baseline case, full-precision ratios, per-case gate outcomes and direct counters, without the seeds.

| Private seed ID | Serial qualification / score | Parallel qualification / score | Chunked-four qualification / score | N=4 chunked cycles versus serial |
|---|---|---|---|---:|
| `seed_1` | pass / 0 | fail N=16 area / 0 | pass / 0.07690443650142043 | 2,294 vs 2,308 (+14 margin) |
| `seed_2` | pass / 0 | fail N=16 area / 0 | pass / 0.07596263037991124 | 2,294 vs 2,297 (+3 margin) |
| `seed_3` | pass / 0 | fail N=16 area / 0 | pass / 0.07699693506740912 | 2,294 vs 2,308 (+14 margin) |

Pooling all **15 paired N/seed cases per design** with the unchanged scorer and equal case weights yields:

| Design | Pooled service-qualified | Pooled score | rA range | rC range | Three observed seed-score range | Failed service cases |
|---|---|---:|---:|---:|---:|---:|
| Serial | yes | 0 | 1–1 | 1–1 | 0–0 | 0 |
| Parallel | no | 0 | 0.29554655870445345–4.36036036036036 | 0.04766431287343835–0.28623853211009176 | 0–0 | 3 |
| Chunked-four | yes | 0.07662145220130123 | 0.6414754835807467–1.3202878992352676 | 0.6514161220043573–1 | 0.07596263037991124–0.07699693506740912 | 0 |

Every failed case was a **functionally correct** parallel N=16 block with 9,680 candidate cells versus 2,220 baseline cells: `rA=4.36036036036036` violates the fixed `<=4` cap. Its completion and II gates passed. Exact cycle and stall counters for all failures follow; each stall triple is `ready-low / output-blocked / input-blocked` cycles.

| Seed ID | Baseline cycles | Parallel cycles | Baseline stall triple | Parallel stall triple | Baseline II | Parallel II |
|---|---:|---:|---|---|---:|---:|
| `seed_1` | 7,377 | 361 | 3,362 / 757 / 7,145 | 167 / 161 / 158 | 35 | 1 |
| `seed_2` | 7,377 | 390 | 3,362 / 757 / 7,145 | 183 / 169 / 160 | 35 | 1 |
| `seed_3` | 7,364 | 351 | 3,353 / 749 / 7,137 | 162 / 160 / 160 | 35 | 1 |

No chunked-four case lost service qualification in these three samples, and its observed aggregate rewards were positive. The N=4 cycle margin was as small as **three cycles**; this bounded check does **not** establish robustness under other workloads or seeds. A future correct case that crosses `rC>1` would be service-unqualified and score zero under the same fixed rule. The parallel N=16 failure remained an area-gate result, not a logical-correctness failure. No gate was relaxed and no seed was chosen after observing a result.

The campaign used **9 evaluator calls and 180 simulator invocations**, below its 16/384 caps. Valid-case counts: **45 functional RTL/mapped, 45 synthesis checks using exact cached netlists, 0 formal, 0 physical**. The focused command `python -m unittest tests.test_block_quant -q` passed **8/8** (historical log not included in this checkpoint); `python -m py_compile scripts/check_block_quant_sensitivity_v38.py` and a read-only reanalysis of saved cases also passed. Full source and installed-package suites were **not rerun** for this metadata-only sensitivity study. No dependency was installed.

Private seeds, vectors and raw tool logs remain outside Git. The dereferenced local archive `/workspace/chip-rl-v38-private-artifacts.tar.gz` has SHA-256 `27a70d58e50def7a60801bf4806eb10fe09214a171b7337e66a9c16f0e7c9530`; its 1,694-file private manifest (not included in this checkpoint) was checked against extracted files. Generic cells, depth and simulated cycles/II remain proxies, not routed timing, area or power. This run makes no formal, physical, silicon-readiness or trained-policy claim and was not pushed.
