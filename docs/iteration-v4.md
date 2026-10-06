# Version 0.4: objectives and physical-cycle controllers

This is a bounded continuation of published commit
`c5766ce31d556f9cde07ef0a118113438bd477ea`. Source and evidence are local; this iteration
has not been pushed. The six pilot families remain six. Four separately qualified
experimental controllers improve the earlier command-tick models without promoting
them to broad ASIC/GPU design benchmarks.

## Executed validation

| Scope | Functional + synthesis | Bounded formal | Unbounded formal | Physical |
|---|---:|---:|---:|---:|
| Pilot families | 6 | 2 small configurations | 0 | 0 |
| Experimental fixed-cycle controllers | 4 | 0 | 0 | 0 |

The development suites accepted 16 pilot designs and rejected 65 faulty variants;
controller suites accepted 13 designs and rejected 28 mutants. All 12 fresh
structural cases passed with frozen development selections. Every accepted
candidate ran both RTL and mapped-netlist simulation. All 45 unit tests passed,
including in a clean checkout. Elastic bounded safety passed at width 8 for 12
clocks, and symbolic pipelined-dot safety passed at K=1 for 8 clocks. Three negative
formal controls failed (corrupt elastic, changed-latency equivalence, corrupt dot).
These results do not establish unbounded liveness or full-size formal correctness.

The installed pilot library, CLI and JSON defaults rejected all 73 bad classes per
interface: **219 rejection checks**, with all **18 baseline checks** passing. That
includes the prior cutoff lengths and the new padding/late-write attacks.

The final installed controller API passed baseline and alternate actions for all
four families, rejected four late-loss candidates, and rejected eight attempts to
change host settings. Pilot goal tests through installed CLI and JSON confirmed
that a valid serial dot design receives an area reward but zero balanced/latency
reward, with `tested_correct=true` and `objective_eligible=false` where appropriate.

A fresh local clone of implementation commit
`c2040fddbf95d251613c8a1bf20279aaaaf28992` passed 45 tests and fresh-cache dot/DMA
HDL smoke checks using the independently installed toolchain. All 32 installed
runtime Python/contract files match that source byte-for-byte. Raw results and
hashes are retained in the public evidence directory; private vectors stay outside Git.

## Changes

- Host-selected area, balanced (default), and latency objectives have explicit
  per-case performance limits, paired raw metrics and Pareto comparisons. Correct
  but goal-ineligible RTL receives zero reward and retains `tested_correct=true`.
- Dot adds a two-multiplier serial design and a registered-product/reduction pipeline.
  Tensor adds four parallel accumulators with four multipliers, sharing across K.
- Every default pilot API now sees dense, bursty and sparse arrival phases; mixed
  arithmetic distributions; random reserved high bits; and interleaved post-init
  scratchpad/gather writes. New padding-dependent and late-write-loss attacks are
  in the default regression set, alongside prior late-drop/reset/fairness attacks.
- Frozen development selections face fresh private workloads at WIDTH 12/20,
  DEPTH 32/128, and K 1/3, absent the original development dimensions. These are
  author-visible prospective stress splits, not permanent secret test dimensions.
- Experimental DMA moves actual data through delayed reads and stalled writes.
  Router has one output queue per port and round-robin admission. Scoreboard owns
  context queues and completes writes on physical clocks even with no new inputs.
  Accelerator loads scratchpad concurrently with MAC execution, with specified
  read-before-write collisions and result backpressure.
- Controller reference models use queues/absolute completion times. Additional
  transfer/FIFO/fairness/drain monitors and versioned memory histories check results
  independently of the cycle oracle. Mid-work reset cancels pending jobs; accepted
  totals may exceed retired totals because reset-aborted work is not a loss.

## Measured tradeoffs

Development seed 20261006, same source across dimensions. Ratios below are geometric
means of target cases; latency uses the documented plus-one smoothing. These are
workload costs, not clock frequency. Full points/frontiers are in
[`evidence/v4/pareto.json`](../evidence/v4/pareto.json).

| Pilot design | Cells / baseline | Cycles / baseline | Offered latency / baseline | Balanced reward | Area reward |
|---|---:|---:|---:|---:|---:|
| elastic global4 | .938 | 1.000 | 1.008 | 1.013 | 1.025 |
| elastic fifo4 | 2.519 | .996 | .949 | .810 | .687 |
| dot serial1 | .526 | 3.126 | 59.862 | 0 (ineligible) | 1.075 |
| dot serial2 | .805 | 2.160 | 33.320 | 0 (ineligible) | .948 |
| dot product_pipe | .975 | 1.001 | 1.023 | 1.003 | 1.010 |
| tensor tensor4 | .342 | 3.126 | 59.862 | 0 (ineligible) | 1.229 |
| scratchpad time_mux | .279 | 3.181 | 149.419 | 0 (ineligible) | 1.269 |
| cache lazy_cache | .984 | 1.000 | 1.000 | 1.004 | 1.007 |
| gather time_mux | .616 | 2.315 | 68.743 | 0 (ineligible) | 1.031 |

Baseline reward is 1. Tensor's smallest implementation is not the best balanced
choice. The dot pipeline's small development gain did not generalize uniformly:
fresh K=1 scored .988 and K=3 scored 1.003. No statistically established improvement
or learned-policy advantage is claimed. Finite catalog enumeration in any order with
the same full budget can find the same development selection.

All controllers must preserve exact protocol cycles; their reward measures generic
cell area alone. At WIDTH=16 the static decoded router uses 1,315 cells versus
25,420 in the dynamic-index baseline (about 94.8% fewer); WIDTH=8 uses 1,079 versus
21,515. Generic logic depth drops from 54 to 42. This large result exposes an
inefficient starter baseline and dynamic-index lowering, not state-of-the-art router
superiority. DMA and scoreboard alternatives have small or negative area changes;
accelerator reset pruning reduces 1,417 to 1,386 cells at DEPTH=16/K=4. Equal or worse
valid alternatives remain valid; reward sensitivity does not require every change
to improve the baseline.

## Reproduction

Install the local wheel and execute API checks from outside the source directory so
Python resolves `site-packages`. The suite checks that explicitly. Tool versions:
Icarus 12.0, Yosys 0.52 with ABC. No external synthesis service is used.

```bash
python -m unittest discover -s tests -v
python -m chip_rl.suite --tasks elastic dot tensor --output /tmp/q/compute --cache /tmp/chip-cache
python -m chip_rl.suite --tasks scratchpad cache gather --output /tmp/q/memory --cache /tmp/chip-cache
PYTHONPATH=. python scripts/check_structural_holdouts.py --qualification /tmp/q --output /tmp/holdouts --cache /tmp/chip-cache
python -m chip_rl.cycle.suite --output /tmp/cycle-q --cache /tmp/chip-cache
PYTHONPATH=. python scripts/reproduce_formal.py --output /tmp/formal-elastic
PYTHONPATH=. python scripts/reproduce_dot_formal.py --output /tmp/formal-dot
PYTHONPATH=. python scripts/check_arrival_reward.py --output /tmp/arrival --cache /tmp/chip-cache
```

From `/tmp`, using an installed environment (substitute the repository path):

```bash
python /path/to/chip-rl/scripts/check_public_apis.py --output /tmp/api-q --cache /tmp/chip-cache
python /path/to/chip-rl/scripts/check_cycle_api.py --output /tmp/cycle-api --cache /tmp/chip-cache
python /path/to/chip-rl/scripts/check_objective_api.py --output /tmp/objective-api.json --cache /tmp/chip-cache
```

The actual run split public API checks into compute, scratchpad/cache, and gather jobs, and structural
checks into compute/scratchpad/cache+gather jobs. Raw replay artifacts are private
under `/workspace/chip-rl-v4-qualification-final`, `/workspace/chip-rl-v4-holdouts`,
`/workspace/chip-rl-v4-cycle-release`, and the corresponding formal directories.
Public summaries preserve source/contract/tool hashes and results, without seeds or
vectors. `scripts/summarize_v4.py` reconstructs the evidence summary from those paths.
Controller artifacts include `vectors.hex`, the exact testbench, RTL and logs for
both RTL/mapped simulation; compressed logs can be expanded locally for inspection.

## Scope, difficulty and cost

This is candidate evaluation plus finite catalog search, not policy training.
Architecture choices and compiler lowering provide real optimization variation,
but tiny arithmetic and inefficient starter RTL can be easy; memory mapping can
make each evaluation expensive without making the design task more representative
of a real GPU. Sparse/bursty workloads exercise behavior, not a calibrated GPU trace.
Raw evaluation elapsed seconds are in [`cost.json`](../evidence/v4/cost.json).
Development baseline evaluations took about 1.2s (elastic), 1.6s (dot), 5.6s
(tensor), 125.9s (scratchpad), 88.0s (cache), and 179.0s (gather). The full
compute qualification took 36s and memory qualification 870s; these exclude the
separate API, structural and controller runs. This cost is material for RL training.
Measurements used four shared CPU cores and warm synthesis/compiled-program caches,
with overlapping jobs; they are not cold-run cost comparisons or a throughput SLA.
Default API tests use new private workloads, so their timings differ from fixed-seed
qualification. Resource limits remain enforced; no timeout is a passing result.

Remaining boundaries: no OS sandbox for untrusted compiler exploits, no SRAM macros,
no OpenROAD/PDK/routed timing/power, no unbounded formal, no full-K dot formal proof,
no trained agents, and finite tests can miss sufficiently late/adaptive corruption.
DMA is contiguous word movement, not the old 2D/misaligned address task or AXI.
Router has no virtual channels/network; scoreboard has no execution datapath;
accelerator has a small load/MAC protocol. The cache retains explicit refill commands.
