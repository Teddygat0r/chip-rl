# v36 block-adaptive INT16-to-INT8 quantization

The local `block_quant` family is an **experimental measurement-only agent task**. Its [public contract](../chip_rl/block_quant/contracts.md) accepts compile-time N={1,2,4,8,16}; a fixed 512-bit input holds up to 16 signed INT16 lanes. The [integer oracle](../chip_rl/block_quant/oracle.py) computes a 17-bit-safe maximum magnitude, exponent `max(0,bit_length(A)-7)`, nearest ties-to-even INT8 results, and the specified zero-padded 256-bit output. The fixed references are a two-pass serial maximum/quantizer and a two-stage elastic parallel maximum/exponent followed by rounding/clamping. `BlockQuantEnv` and `python -m chip_rl.block_quant` expose source-only reset/step actions. The host controls N, split, cache and private replay seed. **`reward` is null; `reward_qualified` is false.** No optimization objective has been selected.

The historical freeze record (not included in this checkpoint) was committed at `921e3fa` before generated paired inputs. It fixes serial source SHA-256 `40b9fdc14f4d2e9e70da3c2eabdbaa891495218d6ae5f72d43419d058b6f1d32` and parallel source SHA-256 `dcfaeb768aa9688f8fa7ca5968c2d5771f0bc8d1fdb132c9c2a255ff96fc92f9`. The [qualification driver](../scripts/qualify_block_quant_v36.py) checks source and generator hashes before generating any workload. Neither candidate RTL source changed during the campaign.

One private heldout root seed supplied a separate deterministic traffic/operand set per N, shared between serial and parallel. Both source RTL and Yosys-mapped netlists matched the oracle on all five N values. Unscored arithmetic probes covered every exponent boundary, positive and negative ties, signed extrema including -32768, positive round-then-clamp, maximum at every active lane, ignored upper/inactive inputs and zero inactive outputs. Unscored protocol probes checked reset cancellation, reset with a blocked output, a 257-cycle consumer stall and recovery. Scored traffic checked bursts, backpressure, ordered outputs and a separate always-ready 32-command stream. The historical v36 summary (not included in this checkpoint) includes direct counters and hashes for every paired case. Its coverage record confirms exponents 0..9 and both sides of all nine exponent transitions at every N.

| N | Design | Generic cells | Logic depth | Workload cycles | Stream II | Commands | Accepted-to-first sum | Offered-to-consumption sum | Unscored vectors |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | serial | 2,223 | 42 | 1,085 | 5 | 154 | 616 | 60,359 | 90 |
| 1 | parallel | 657 | 34 | 311 | 1 | 154 | 432 | 1,561 | 90 |
| 2 | serial | 2,224 | 42 | 1,544 | 7 | 175 | 1,050 | 109,935 | 95 |
| 2 | parallel | 1,279 | 34 | 335 | 1 | 175 | 496 | 3,078 | 95 |
| 4 | serial | 2,223 | 42 | 2,297 | 11 | 177 | 1,770 | 176,351 | 97 |
| 4 | parallel | 2,478 | 60 | 357 | 1 | 177 | 496 | 5,206 | 97 |
| 8 | serial | 2,222 | 42 | 3,672 | 19 | 181 | 3,258 | 315,485 | 101 |
| 8 | parallel | 4,880 | 112 | 338 | 1 | 181 | 517 | 10,689 | 101 |
| 16 | serial | 2,220 | 42 | 7,377 | 35 | 189 | 6,426 | 669,975 | 109 |
| 16 | parallel | 9,680 | 216 | 385 | 1 | 189 | 548 | 5,712 | 109 |

All ten design/N cases passed functional RTL/mapped and synthesis checks. Two deliberately bad serial variants, one treating -32768 magnitude as zero and one rounding exact ties away from even, failed the unscored source-RTL arithmetic probe at N=1. Direct Python, `BlockQuantEnv`, and the JSON-lines CLI returned identical measurement results for both designs at N=4. Agent N overrides and invalid host N=0,3,17 were rejected before evaluation. The campaign used **10 evaluator calls and 82 simulator invocations**, below its 24/160 caps. Four exact synthesis builds were preflighted before workload generation; eight further builds comprised six remaining valid design/N netlists and two bad controls. Exact-match verified simulation cache hits avoided duplicate API replay. Validation counts for valid cases: **10 functional RTL/mapped, 10 synthesis, 0 formal, 0 physical**.

The first attempt exposed a verifier defect: its fixed 32-cycle reset-stall probe could finish before the N=16 serial response appeared, and freshly measured flags were not checked before marking that case verified. The evaluator now validates fresh and cached metrics with the same rules, and the unscored reset window is `2*N+16`. The pair was rerun with the **same private seed and unchanged candidate RTL**. Both attempts' journals remain in the private archive; the 82 simulator count includes them. This was a harness repair, not a candidate change.

Normal source tests, `python -m unittest discover -s tests`, passed **215/215** (historical log not included in this checkpoint). The local package was installed without dependencies or build isolation using `python -m pip install --no-deps --no-build-isolation --target /tmp/chip-rl-v36-installed /workspace/chip-rl-block-quant-v36`; from `/tmp`, `PYTHONPATH=/tmp/chip-rl-v36-installed:/workspace/chip-rl-block-quant-v36 python -m unittest discover -s /workspace/chip-rl-block-quant-v36/tests` also passed **215/215** (historical log not included in this checkpoint). The loaded package resolved from `/tmp/chip-rl-v36-installed`.

To repeat the paired check from the repository root with a newly drawn private seed:

```sh
python scripts/qualify_block_quant_v36.py \
  --cache /tmp/chip-rl-block-quant-cache \
  --out /tmp/chip-rl-block-quant-summary.json \
  --private /tmp/chip-rl-block-quant-private
```

The private seed, operands and raw tool logs remain outside Git. A dereferenced local archive at `/workspace/chip-rl-v36-private-artifacts.tar.gz` has SHA-256 `322b1c856b734274154dae941bedb16e5e1c27d18a17b34d55efa043298600b5`; its 808-file private manifest (not included in this checkpoint) was checked against extracted files. Generic mapped cells and depth and digital-simulation cycles/latencies are proxies, not routed area, Fmax, energy, power, optimal quantization accuracy or silicon readiness. No full formal or physical implementation, same-UID OS isolation, independent evaluation or trained-policy improvement is claimed. This checkpoint remains local and unpushed.
