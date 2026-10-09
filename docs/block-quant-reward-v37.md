# v37 block quantization: fixed gates and chunked-four reference

## Verifier carry-forward

The first [v36 attempt](block-quant-v36.md) had a reset-probe defect: a fixed 32-cycle wait ended before the N=16 serial output became blocked, so `reset_blocked_output_seen` was false. Fresh metrics were also marked verified without applying the cache-validation gate. v36 changed the **unscored** reset wait to `2*N+16` and applied the same `validate_metrics` checks to fresh and cached results, requiring the blocked output to be seen. It reran with the same private seed and unchanged candidate RTL, retaining the failed-attempt journal in its archive. Those corrections remain in v37; the watchdog remains `2*N+64` ready-high opportunities and the 257-cycle stall probe remains unscored.

## Contract and sources

The [contract](../chip_rl/block_quant/contracts.md) now uses the fixed balanced generic-cell/completion proxy. For each scored N={1,2,4,8,16}, the candidate and fixed serial baseline use **identical operands and traffic**. A functionally and progress-verified pair must satisfy cell ratio `rA<=4`, workload-cycle ratio `rC<=1`, and independent saturated-stream II `<=2*N+3`. Equality passes. If every case passes, aggregate score is `max(0,1-exp(mean(log(rA*rC))/2))` with equal N weights. A hard-gate failure leaves `tested_correct=true` when the RTL is correct, while `service_qualified=false`, `reward_qualified=false` and score 0. Missing or mismatched baseline verification fails closed. The fixed serial baseline qualifies at score 0.

The historical v37 freeze (not included in this checkpoint), committed at `67d7fb5` before new shared workloads, records all three candidate bytes. Serial (`40b9fdc14f4d2e9e70da3c2eabdbaa891495218d6ae5f72d43419d058b6f1d32`) and fully parallel (`dcfaeb768aa9688f8fa7ca5968c2d5771f0bc8d1fdb132c9c2a255ff96fc92f9`) exactly match v36. New chunked-four (`8fda0e3d643b5fcb9909ef89615459cac08cf792d6b5aab795cca84b2c5a0ed8`) accepts one block, scans active lanes one per cycle for the exact maximum, derives the exponent, then rounds/clamps up to four active lanes per cycle. It holds its packed output until consumed, never overlaps blocks, and reset cancels pending work. It uses the same 17-bit-safe magnitude and ties-to-even arithmetic. The [qualification driver](../scripts/qualify_block_quant_v37.py) asserts these hashes before generating the private workload.

## Paired heldout result

One fresh private root seed generated a separate deterministic operand/traffic set per N, shared by all three references. Source RTL and Yosys-mapped netlists passed exact oracle outputs, arithmetic probes, ordered scored traffic, readiness-normalized progress, reset cancellation, reset while an output was blocked, a 257-cycle output stall and recovery. The historical v37 case file (not included in this checkpoint) retains direct acceptance, consumption, latency, backpressure and workload-hash counters. Unscored arithmetic probes numbered 90/95/97/101/109 for N=1/2/4/8/16. Exponents 0..9, both sides of all nine exponent transitions, positive and negative ties, −32768, round-then-clamp, each maximum-lane position and ignored fields were covered at every applicable N.

| N | Design | Cells | Cycles | II | Accepted-to-first sum | Offered-to-consumption sum | rA | rC | N gate | Single-case proxy* |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| 1 | serial | 2,223 | 1,085 | 5 | 616 | 66,546 | 1.000000 | 1.000000 | pass | 0 |
| 1 | parallel | 657 | 285 | 1 | 434 | 4,303 | 0.295547 | 0.262673 | pass | 0.721375 |
| 1 | chunked4 | 1,426 | 1,085 | 5 | 616 | 66,546 | 0.641475 | 1.000000 | pass | 0.199078 |
| 2 | serial | 2,224 | 1,544 | 7 | 1,050 | 113,065 | 1.000000 | 1.000000 | pass | 0 |
| 2 | parallel | 1,279 | 338 | 1 | 497 | 7,341 | 0.575090 | 0.218912 | pass | 0.645185 |
| 2 | chunked4 | 1,934 | 1,260 | 6 | 875 | 88,131 | 0.869604 | 0.816062 | pass | 0.157592 |
| 4 | serial | 2,223 | 2,297 | 11 | 1,770 | 179,363 | 1.000000 | 1.000000 | pass | 0 |
| 4 | parallel | 2,478 | 334 | 1 | 509 | 4,382 | 1.114710 | 0.145407 | pass | 0.597400 |
| 4 | chunked4 | 2,935 | 2,294 | 8 | 1,239 | 179,314 | 1.320288 | 0.998694 | pass | 0 |
| 8 | serial | 2,222 | 3,672 | 19 | 3,258 | 311,619 | 1.000000 | 1.000000 | pass | 0 |
| 8 | parallel | 4,880 | 338 | 1 | 517 | 6,823 | 2.196220 | 0.092048 | pass | 0.550381 |
| 8 | chunked4 | 2,932 | 2,392 | 13 | 2,172 | 194,083 | 1.319532 | 0.651416 | pass | 0.072873 |
| 16 | serial | 2,220 | 7,364 | 35 | 6,426 | 671,962 | 1.000000 | 1.000000 | pass | 0 |
| 16 | parallel | 9,680 | 351 | 1 | 533 | 5,775 | 4.360360 | 0.047664 | **area fail** | 0 |
| 16 | chunked4 | 2,896 | 4,907 | 23 | 4,158 | 438,545 | 1.304505 | 0.666350 | pass | 0.067661 |

*The single-case proxy is the formula applied to that N alone for diagnosis; **it is not averaged to obtain the aggregate reward**. Aggregate logs are averaged before the final clipping. Exact ratios, gate booleans and full-precision diagnostics are in the public case file.

Serial is qualified at aggregate **0**. Fully parallel is functionally correct at all five N, but N=16 has `rA=9680/2220=4.360360360…`, so its **service qualification fails and aggregate reward is 0**; the area limit was not raised. Chunked-four passes every hard gate and scores **0.07705624926402332** on this workload. The narrow N=4 cycle margin (2294 versus 2297) makes that result workload-dependent, not a guaranteed reward across seeds.

Direct Python, `BlockQuantEnv`, and JSON-lines CLI results matched for all three sources at N=4. Agent N overrides and invalid host N=0,3,17 failed before evaluation. Wrong −32768-magnitude and ties-away mutants failed the unscored source-RTL arithmetic probe at N=1. The run used **11 evaluator calls and 62 simulator invocations**, below the 24/160 caps; the exact netlist cache supplied prior builds and only three chunked N netlists required new synthesis. Valid-case counts are **15 functional RTL/mapped, 15 synthesis, 0 formal, 0 physical**. Normal source tests and locally installed tests (logs not included in this checkpoint) each passed **218/218**. The installed package was created without new dependencies using `python -m pip install --no-deps --no-build-isolation --target /tmp/chip-rl-v37-installed /workspace/chip-rl-block-quant-v37` and loaded from that target.

To replay with a new private seed from the repository root:

```sh
python scripts/qualify_block_quant_v37.py \
  --cache /tmp/chip-rl-block-quant-cache \
  --out /tmp/chip-rl-block-quant-v37-summary.json \
  --private /tmp/chip-rl-block-quant-v37-private
```

Private seed, vectors and raw tool traces stay outside Git. The local dereferenced archive `/workspace/chip-rl-v37-private-artifacts.tar.gz` has SHA-256 `8e68ad79588daa3bb4db667c65e0e6caf138e186e023842b52e83b93f6d42fad`; its 620-file private manifest (not included in this checkpoint) was checked against extracted files. Cells and logic depth are generic Yosys/ABC proxies; simulated cycles and II are digital-workload measurements. There is no routed area, timing, power, physical or full formal result, same-UID OS isolation, independent evaluation or trained-policy gain. This branch remains local and unpushed.
