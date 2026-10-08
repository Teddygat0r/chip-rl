# Requantization audit: viable architecture, incomplete reset gate

**A correct elastic architecture meets the fixed service limits on the executed splits, but the evaluator has a demonstrated false acceptance. Do not treat this checkpoint as ready for untrusted-agent training.** Numerical semantics and thresholds remain unchanged. The prior publication candidate f9d7137 and v24 checkpoint 728e24a remain in their original clean worktrees. No families are added in this audit.

## Numerical and service contract

The [exact contract](../chip_rl/requant/contracts.md) still computes a signed INT32 accumulator times an unsigned INT16 scale, rounds division by 2**shift to nearest with ties to even, adds the signed zero point, then saturates to INT8. For either sign, magnitude ties go to an even quotient: +0.5 and -0.5 map to 0; +1.5 maps to 2 and -1.5 to -2. The independent oracle uses signed floor quotient/remainder, while candidate RTL rounds magnitudes. The product range fits signed 48 bits: the largest magnitude is 2**31*(2**16-1), strictly below 2**47. The 49-bit signed rounding/addition intermediate accommodates zero-point addition without overflow. Truncating the product to 32 bits or treating scale as signed is wrong.

Clamp only after zero-point addition: round(200)+(-128)=72, not -1. Boundary tests cover shifts 0..47, most-negative and most-positive accumulators, high-bit and zero scales, positive/negative ties, near saturation transitions, all four zero-point categories, masks and reserved input bits. A new 900-row direct workload compares the baseline and elastic pipeline against an independent 80-digit Decimal reference: 7200 lane comparisons. Both also pass mapped simulation with bit/cycle equality. No numerical defect or tolerance change was identified in these tests; this finite set is not an exhaustive proof over the full input space.

## Why serialization wins development and fails heldout

The frozen release generator averages 1.4 cycles between development arrivals and 2.4 cycles between heldout arrivals, before finite-sample variation. The fixed parallel baseline has a one-entry output buffer and prohibits simultaneous dequeue/enqueue, so it introduces bubbles. The serial and old pipelined designs also prohibit overlap. Under saturated development traffic, both baseline and serial queues grow, and the serial cell reduction outweighs its cycle cost in the fixed weighted reward. Under sparser heldout traffic, the baseline's offered latency can be much smaller, while the slower alternative still accumulates a queue; their offered-latency **ratio** can grow sharply even though completion-cycle ratio stays below 4.

V24's heldout N3 latency ratios were 17.38315 for serial and 6.42360 for old pipelined RTL, above the unchanged limit of 6. On the fresh v25 seed they are 8.09088 and 3.33059 respectively: serial still fails eligibility; old pipelined RTL now passes, with reward below 1. Thus the earlier observations are real finite-workload failures, not universal impossibility results. No threshold was tuned to rescue a candidate. Correctness remains distinct from per-case eligibility; ineligibility gives zero reward.

The new `elastic_pipeline` retains a registered product stage and registered output stage, but allows simultaneous ingress and egress with ready propagation. It removes the old bubble bottleneck. It passes both structural splits and the independent boundary workload, with positive development and heldout rewards. Its gain is a canonical buffering/flow-control improvement against a simple starter baseline, not a discovered arithmetic breakthrough. The heldout workload was visible to this author before development; success is not unseen-policy generalization. A separate `ready_gated` candidate also passes both splits; no false rejection of that legal conservative ingress behavior was found.

## Demonstrated reset false acceptance

The mandatory checker resets empty state, one newly accepted request, and one completed stalled response; it does not deliberately fill both stages of an elastic design before cancellation, and cold startup uses zero input mask. A mutant replaces the elastic pipeline's reset assignment `pv<=0` with `pv<=pv && ov && in_mask[0]`. This illegally makes cancellation depend on pending occupancy and an input mask that should be irrelevant during reset.

The frozen evaluator accepts that exact source on development N2/N4 with nonzero reward. In a separate transaction-level probe, two requests are accepted while output ready is low, then a single reset edge occurs with the mask active. The correct design cancels both. The mutant produces a spurious response afterward. **Both RTL and mapped simulations reproduce the mutant's failure**, and both pass for the correct source. The same mutation can also mishandle cold reset with a nonzero mask; no universal cold-start guarantee is claimed. Artifact sources, testbenches, netlists and logs preserve the exact conditions.

An initial mutant depending only on old occupancy failed mapped cold startup before reaching the intended scenario. It was retained as a failed diagnostic and was not presented as a false acceptance. The second deterministic-start control above is the demonstrated counterexample. Existing ties-away, narrow-product, premature-saturation, repaired ignore-mask, reset and stalled-output controls are still rejected. Passing them does not close this new coverage gap.

## Status and next work

This is an **audit checkpoint with a known unfixed evaluator defect**. The evaluator was kept frozen so its acceptance, independent failure, API and replay results share one exact implementation. Corrective qualification would require a new bounded phase; only one requant evaluator call remains in this audit's 24-call allowance, insufficient for the full affected matrix/API/replay rerun. No caps were silently extended, and no untested gate patch is presented as complete.

The next most useful work is to add a capacity-adaptive reset probe that accepts as many pending requests as a design permits while output is stalled, then cancels and drains, and to poison mask/data during reset. It must continue to accept legitimate one-slot, ready-gated and two-stage designs. Freeze this counterexample as a regression, recheck all valid architectures and affected faults, then rerun final installed API/replay and aggregate checks under a fresh explicit budget. After that, independently executed arrival-rate/backpressure sweeps would test whether eligibility has adequate margin. Do not add another family first.

No new formal proof, physical timing/power, OS isolation or learning-advantage evidence is claimed. Tests are locally authored and visible. Generic cells/depth and simulated cycles remain proxies. The historical exact K16 dot proof does not cover requantization.

## Reproduction

Use the installed v0.25.0 wheel with existing Icarus/Yosys/ABC and `CHIP_RL_TOOLS`. Run outside the checkout. These are trusted-host controls; choose new private output paths and reserve calls before execution. The private checkpoint retains the exact executed campaign drivers, frozen seed 250025, sources, journals and tool logs.

```bash
repo=/workspace/chip-rl-requant-audit
py=/workspace/chip-rl-v25-venv/bin/python
export CHIP_RL_TOOLS=/workspace/tools/root/usr
# Each uses fresh output paths; do not rerun an already reserved numerical stage.
"$py" "$repo/scripts/requant_reset_probe_v25.py" --root /tmp/reset-probe-new --cache /tmp/requant-cache
"$py" "$repo/scripts/check_requant_api_v25.py" --output /tmp/requant-api-new --cache /tmp/requant-cache
# Replay a retained successful elastic-pipeline artifact from the private archive:
"$py" "$repo/scripts/replay_requant.py" /workspace/chip-rl-v25-runs/elastic_pipeline-heldout --output /tmp/requant-replay-new --cache /tmp/requant-cache
```

The reset probe runs RTL and mapped positive/negative controls. The frozen full evaluator's false acceptance is retained separately at `chip-rl-v25-runs/reset-counterexample`; its private journal contains the exact source and seed. The boundary script `scripts/requant_boundaries_v25.py` requires a ledger with `numerical` status `reserved` and reservation at least 7200, then changes the stage to `started` before work and `passed` after checking; use the preserved results unless intentionally funding a new audit.

## Exact recorded results

| Architecture | Split | Cells ratio | Depth ratio | Cycles ratio | Eligible | Reward |
|---|---|---:|---:|---:|---|---:|
| parallel | development | 1.00000 | 1.00000 | 1.00000 | yes | 1.000000 |
| parallel | heldout | 1.00000 | 1.00000 | 1.00000 | yes | 1.000000 |
| serial | development | 0.40311 | 1.08511 | 2.18928 | yes | 1.146517 |
| serial | heldout | 0.64153 | 1.07938 | 1.62662 | no | 0.000000 |
| pipelined | development | 1.02530 | 0.73404 | 1.33276 | yes | 0.964935 |
| pipelined | heldout | 1.03011 | 0.73017 | 1.32902 | yes | 0.964221 |
| elastic_pipeline | development | 1.01176 | 0.73404 | 0.51020 | yes | 1.111016 |
| elastic_pipeline | heldout | 1.02102 | 0.73017 | 0.87214 | yes | 1.029967 |
| ready_gated | development | 1.00007 | 1.00000 | 1.00000 | yes | 0.999979 |
| ready_gated | heldout | 1.00102 | 0.97872 | 1.00000 | yes | 1.000769 |

All ten architecture/split evaluations passed the frozen finite gate. The separately tested **known incorrect** reset mutant also passed that gate with reward 1.1109153567717769; it is excluded from the valid-design count. A correct architecture passing the tested constraints does not make the evaluator sound against adversarial proposals.

188 source and 188 installed unit tests passed; final-source API and exact development/heldout replays passed; all 22 inherited-family baselines/fault-or-invalid-action controls plus layout and softmax checks passed. Aggregate count is 47 evaluator calls. No full historical architecture/formal campaigns were rerun. Compute: {"requant_evaluator_calls": 23, "requant_synthesis_calls": 11, "requant_simulations": 135, "numerical_comparisons": 7200, "numerical_reserved_plus_units": 8000, "incomplete": 0, "separate_aggregate_calls": 47}. One requant evaluator call remains; full corrective qualification is the outstanding obligation.

See summary (private evaluation artifact retained locally), matrix (private evaluation artifact retained locally), reset controls (private evaluation artifact retained locally), escaped source (private evaluation artifact retained locally), accepted result (private evaluation artifact retained locally), numerical boundary results (private evaluation artifact retained locally), and ledger (private evaluation artifact retained locally).
