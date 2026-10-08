# Exact requantization experiment (v24)

This distinct task covers the accumulator-to-INT8 conversion after a dot/tensor operation: programmable integer scale, shift, nearest-even rounding, zero point and saturation. Existing exact accumulation and approximate softmax tasks do not test this contract. The prior 24-family publication candidate remains unchanged at f9d71379e85e73e8663aa41b3f703a41299b2158 in its original worktree; this work is on `codex/requant-v24`.

## Contract and implementation

Read the [fixed contract](../chip_rl/requant/contracts.md), [specification](../chip_rl/requant/spec.py), [integer oracle](../chip_rl/requant/oracle.py), [RTL architectures](../chip_rl/requant/rtl.py), [workload generator](../chip_rl/requant/workloads.py), [protocol checker](../chip_rl/requant/simulation.py), and [evaluator](../chip_rl/requant/evaluate.py). The arithmetic is exact: signed INT32 times unsigned INT16, divide by a power of two with ties to even, add signed INT8 zero point, then clamp to INT8. Saturating before adding the zero point is wrong. Masked and unused lanes must output zero. Inputs at shift 0 and 47, negative ties, most-negative accumulators, high-bit scales, saturation transitions, zero scales and all mask patterns are tested.

The parallel baseline computes each lane independently. Serial RTL shares one multiplier/rounding datapath across lanes. Pipelined RTL registers parallel products before rounding. All three source files are parameterized and unchanged across development N2/N4 and heldout N1/N3. Heldout traffic is sparser and emphasizes extremes and sparse masks; splits are visible, not a claim of secret or independent testing.

Each shape runs 1692 uninterrupted scored requests, with independent offered release times, periodic output stalls and invalid-cycle poison. Protocol probes cover cancellation, minimum registered latency, retention under long stalls, post-work reset and duplicate drains. The numerical oracle uses signed floor quotient/remainder; RTL rounds magnitudes and restores sign. A separate 80-digit Decimal implementation checked 6376 cases against the oracle, within a pre-reserved 7000-comparison allowance. Normal RTL reference checks are part of the separately capped HDL campaign, not additional independent numerical sweeps.

## Interpretation

A correct design can be ineligible and earn zero. Per-case cycle ratio must be at most 4 and offered-latency ratio at most 6; no gate was relaxed after measurement. The serial design materially reduces cells at the cost of throughput and queueing latency. The pipelined design reduces combinational depth while adding registers and a cycle. These are useful architecture tradeoffs, not claims that either alternative is universally better. In particular, both alternatives fail the heldout offered-latency gate at N3. The fixed parallel baseline remains feasible there.

Recommendation: include this as an **experimental research task**, not a promoted pilot or demonstrated RL success. It offers a real shared-versus-parallel datapath decision and exposes workload-sensitive eligibility. A useful next experiment is to find an architecture that preserves area benefits while meeting the heldout latency limits, then compare an agent with equally budgeted enumeration/random search. No policy was trained here.

## Reproduce with existing tools

Install the wheel from this checkpoint into a fresh virtual environment; use existing Icarus 12 and Yosys 0.52/ABC. Set `CHIP_RL_TOOLS` to their extracted `usr` directory. Run installed Python outside the source checkout. The following are trusted-host commands; source-only agents use [RequantEnv](../chip_rl/requant/env.py) or the [JSON server](../chip_rl/requant/server.py). Do not grant candidates access to seeds, constraints, artifacts or caches.

```bash
# Set these to your checkout, installed interpreter, and fresh private output paths.
repo=/workspace/chip-rl-requant
py=/workspace/chip-rl-v24-final-venv/bin/python
export CHIP_RL_TOOLS=/workspace/tools/root/usr
runroot=/tmp/requant-reproduction
mkdir "$runroot"
printf '{"calls":[]}' > "$runroot/budget.json"
cd /tmp
"$py" "$repo/scripts/evaluate_requant_v24.py" serial__development --split development --root "$runroot/runs" --cache "$runroot/cache" --ledger "$runroot/budget.json"
"$py" "$repo/scripts/replay_requant.py" "$runroot/runs/serial__development" --output "$runroot/replay" --cache "$runroot/cache"
"$py" "$repo/scripts/check_requant_api_v24.py" --output "$runroot/api" --cache "$runroot/cache"
"$py" "$repo/examples/requant_rollout.py" --cache "$runroot/cache"
```

The evaluation helper accounts its own calls in the ledger; API/replay/example invocations must additionally be reserved by the trusted campaign owner before running, as in the recorded campaign. Replay checks exact correctness, eligibility, reward, metrics, source, recipe and tool identity; it is a diagnostic, not an independent qualification split. The numerical audit script refuses to repeat an already reserved stage. Do not rerun it just to recreate a summary.

## Evidence boundaries

All tests were authored and executed locally with visible sources. Existing source screening, fixed commands, netlist inspection, resource limits and strict record parsing restrict the HDL interface; they do not isolate a shell-capable process with the same UID. There are no new formal proofs, routed area/timing/power results, physical implementation, independent evaluation or learning-advantage results. Cells and depth are generic synthesis proxies; latency and throughput are simulated workload metrics. The inherited exact K16 proof concerns its separate pinned dot instance, not requantization.

The initial ignore-mask control accidentally formed the Verilog literal `1'b1?`, which was rejected during parsing. That rejection is retained as malformed-source evidence, not semantic mask evidence. A space fixes the control; the corrected RTL must be rejected for an exact output mismatch. All valid designs are rerun on the final package. The other 13 mutant sources and evaluator implementation are byte-unchanged; their existing rejection evidence is retained with that provenance. No third-party RTL was added; this task reuses this repository's tool boundary, journals and strengthened transaction harness.

## Recorded results

| Architecture | Split | Cells ratio | Depth ratio | Cycle ratio | Correct | Eligible | Reward |
|---|---|---:|---:|---:|---|---|---:|
| parallel | development | 1.00000 | 1.00000 | 1.00000 | yes | yes | 1.000000 |
| parallel | heldout | 1.00000 | 1.00000 | 1.00000 | yes | yes | 1.000000 |
| serial | development | 0.40311 | 1.08511 | 2.19118 | yes | yes | 1.146398 |
| serial | heldout | 0.64153 | 1.07938 | 1.62980 | yes | no | 0.000000 |
| pipelined | development | 1.02530 | 0.73404 | 1.33340 | yes | yes | 0.964863 |
| pipelined | heldout | 1.03011 | 0.73017 | 1.33126 | yes | no | 0.000000 |

At heldout N3, serial offered-latency ratio is 17.38315 and pipelined ratio is 6.42360, exceeding the fixed 6 limit. At N1 the serial design uses more cells than the baseline (5989 versus 5554). The smaller geometric-mean cell ratio must not hide those per-case results. Development serial N4 uses 5990 versus 20873 cells and 2.40090 times the cycles.

Passed: 188 source and 188 installed tests; six positive split evaluations covering 12 shape cases; 14 meaningful faulty-source rejections; installed API with three correct designs, one faulty design and 14 invalid requests; exact development and heldout replays; three-design example. The initial malformed mask control is retained separately and excluded from the 14 semantic controls. All valid architectures and the corrected mask control were rerun after the fixture fix; the other 13 final mutant sources are byte-identical and the evaluator implementation unchanged.

Final cumulative usage: {"evaluator_calls": 46, "synthesis_calls": 27, "HDL_simulations": 212, "independent_numerical_comparisons": 6376, "numerical_reserved_including_units": 7256, "incomplete": 0}. Caps remained unchanged. No prior 24-family HDL aggregate or inherited formal campaign was rerun; inherited runtime files are byte-identical and all existing unit tests passed. See summary (private evaluation artifact retained locally), full positive results (private evaluation artifact retained locally), negative reasons and provenance (private evaluation artifact retained locally), and budget ledger (private evaluation artifact retained locally).
