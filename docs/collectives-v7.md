# Expansion batch 3: scan, selection and histogram updates

Status: experimentally qualified on finite RTL/netlist tests; not promoted to pilot. This
batch adds segmented all-prefix sums, stable signed top-K selection, and stateful
multi-lane histogram updates with exact collision ordering. These differ from
scalar reduction, memory gather, arbitration and the existing allocator tasks.

The installed [contracts](../chip_rl/expansion/contracts.md) define every bit,
ignored field, ordering rule and constraint. Sources use the established ready/valid
transaction API; host dimensions, goals and seeds remain outside candidate actions.
No trained policy, routed timing, physical power or complete GPU is claimed.

## Reference/reuse audit (2026-10-07)

[NVIDIA GPU Gems on scan](https://developer.nvidia.com/gpugems/gpugems3/part-vi-gpu-computing/chapter-39-parallel-prefix-sum-scan-cuda)
provides background on ordered prefixes and parallel scan. The hardware has an
explicit mask, segment-head and modulo32 contract; no CUDA source is reused.
[NVIDIA's histogram discussion](https://developer.nvidia.com/blog/gpu-pro-tip-fast-histograms-using-shared-atomics-maxwell/)
motivates testing both distributed and colliding bin updates. This small register
array returns exact lane-ordered previous values and post-update queries; it is not
a model of Maxwell atomics or a memory hierarchy.
[CUB's top-K interface](https://github.com/NVIDIA/cccl/blob/main/cub/cub/device/device_topk.cuh)
provides selection context. Our sorted signed integer results with stable index ties
are an original contract, not a compatibility or performance claim about CUB.

Only public explanations/interfaces were consulted. No external RTL, source, test
vectors, images, datasets or prose passages were incorporated. All code is original
under the repository license. CUDA/CUB/NVIDIA binaries are not dependencies. Existing
Python and open-source HDL tool license notes apply; no paid services are used.

## Reproduce

```bash
python -m unittest discover -s tests -v
python -m chip_rl.expansion.suite --tasks scan topk histogram --output /tmp/v7-q --cache /tmp/chip-cache
python scripts/check_expansion_apis.py --tasks scan topk histogram --output /tmp/v7-api --cache /tmp/chip-cache
python scripts/check_expansion_holdouts.py --tasks scan topk histogram --qualification /tmp/v7-q/summary.json --output /tmp/v7-held --cache /tmp/chip-cache
python scripts/reproduce_collective_formal.py --output /tmp/v7-formal
python examples/expansion_rollout.py --task scan --objective area --cache /tmp/chip-cache
```

Install the wheel first; use absolute script paths from outside the checkout for
installed API checks. The evaluator runs paired RTL and mapped-netlist workloads,
private arrivals/stalls, multiple dimensions and source-only schema tests. It never
accepts a timeout, incomplete drain, divergence, changed constraint or unproved
formal attempt as correctness success. Raw replay files are host-private; committed
evidence contains only summaries. Public structural dimensions do not establish
secret-test robustness or learned generalization.

## Scope of formal and physical checks

The scan check is width8/four lanes, one symbolic transaction immediately after
reset, always-ready output and nine clocks. It checks exact inclusive/exclusive
segmented values, acceptance, one response and completion by clock7. This is not
arbitrary streaming/backpressure or unbounded equivalence. Baseline and serial
passed; the tree attempt exhausted its45s SAT budget and remains unproven. A mutant
that ignores segment heads produced a proof counterexample. Private simulation
separately exercises streams, stalls and reset. No physical stage was run.

Dedicated OS isolation is still not provided. Process limits/source restrictions
are not a security boundary for arbitrary untrusted compilers or agents. Generic
cell count/depth and workload cycles are proxies, not physical PPA or silicon readiness.


## Measured tradeoffs

| Architecture | Generic cells | Logic levels | Balanced reward |
|---|---:|---:|---:|
| Scan ordered accumulator | 3292 | 94 | 1.000 |
| Scan tree | 8800 | 62 | 0.792 |
| Scan serial | 2383 | 26 | 0 (performance gate) |
| Top-K insertion | 4132 | 147 | 1.000 |
| Top-K parallel ranks | 22975 | 93 | 0.676 |
| Histogram parallel | 9195 | 74 | 1.000 |
| Histogram serial | 4178 | 17 | 0 (performance gate) |

A lower generic logic depth does not establish a higher physical clock rate.
Parallel ranks/tree implementations cost more cells despite shallower logic. The
serial histogram saves enough cells to score above1 under the area goal; scan
serial saves cells but loses enough workload service performance that even its
area-goal reward is below1. Defaults fix the baseline rather than replacing it
with the best result. Reward sensitivity includes worse valid alternatives.

Development accepted7 designs and rejected31 adversarial variants. Counts cover
both RTL and synthesized netlists at mandatory development dimensions. Workload
bands specify random portions; directed/initialization commands add to actual
transaction counts, and all commands contribute measured elapsed clocks.


Replay a retained private case with the original installed wheel/toolchain:
`python scripts/replay_expansion.py /private/task/design/case-0-0/candidate --output /tmp/replayed-case --cache /tmp/chip-cache`.
This checks evaluator/tool/source hashes, regenerates the exact recorded case and
runs RTL plus mapped simulation. It never labels a single-case replay as full
qualification. Keep the original private artifacts and their parent result.json;
committed summary JSON alone is not sufficient to reproduce the private workload.


## Final executed results

All7 new designs passed paired RTL/netlist qualification; all31 mutants were
rejected. Installed library/CLI/JSON passed21 valid pairs and rejected93 mutant
pairs, plus9 host-setting override attempts. All6 frozen-source structural cases
passed. All66 unit tests passed in both working and clean checkouts. Fresh-cache
checks of all3 families passed using the independently installed HDL toolchain.
All52 installed runtime Python/contract files matched implementation commit
`58e0d2269bc663cedda5060f8e9594b1eaf68cad` byte-for-byte.

The six earlier expansion families were rerun through the installed APIs:51 valid
checks passed and186 mutants were rejected. Pilot/controller HDL results are
inherited from the completed v6 batch, not claimed as newly rerun in v7. Their29
runtime Python files are byte-identical, and3000 legal parameter/goal contract
outputs match between installed versions. V6's18 pilot baseline checks,219 mutant
rejections,13 valid controllers and28 controller rejections remain in the repository.

Scan replay succeeded from retained private artifacts. A mismatched evaluator
version was rejected before replay. Formal:2 scan implementations bounded-pass,
tree unproven after timeout, corrupt mutant counterexample. Zero unbounded proofs,
physical evaluations or trained policies. See [summary](../evidence/v7/summary.json),
per-family evidence, source hashes, replay output and
[executed commands](../evidence/v7/executed-commands.txt).

Total runnable suite:19 families, six pilots and thirteen experimental. Each has
real reference RTL, distinct alternate RTL, adversarial sources and measured HDL
qualification. Counts do not imply production ASIC/GPU readiness. V5/v6/v7 remain
local; only the explicitly approved v4 branch was published.
