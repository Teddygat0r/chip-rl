# V20: full final-source audit of persistent tile layout

Execution remained available throughout this audit, including after the disconnect notification at 12:15 UTC. No environment recreation or access workaround was used. V18's proof checkpoint and V19's evidence remain unchanged. The suite remains **23 runnable families**, six pilots and 17 experimental families; this release hardens `layout` rather than adding a family.

## Reproduced issues and fixes

**Legal source syntax was falsely rejected.** V19's shared attribute guard treated `(*` inside `always @(*)` as an attribute opener. The layout-specific entry check now normalizes only wildcard event-control spelling before invoking the unchanged shared sanitizer. Real attributes, directives, strings, incomplete manual sensitivity lists and sequential mapper state remain forbidden. Continuous assignments, `always @*`, `always @(*)`, `always_comb` and automatic functions are exercised. This is a declared synthesizable subset, not support for every SystemVerilog construct; explicit manual sensitivity lists remain outside it.

**The testbench could falsely reject legal combinational logic at startup.** Once wildcard syntax passed the gate, a procedural mapper failed the first warp because a lane's row/column input stayed at its time-zero value and the procedural output had not evaluated. Mapping truth-table checks already passed. The bank-engine harness now leaves data coordinates unspecified during reset and drives valid coordinates before the first capture, providing the required input event without changing scored clock counts. The initial failure and the corrected run are preserved.

**Reset clearing was unobserved by the old workload.** Removing the fixed engine's memory-clear loop passed V19's RTL and mapped workload checks: each reset was followed by a full refill before reads. This was a trusted-engine coverage hole, not a permitted candidate action—the candidate cannot replace the engine. New directed reads observe zero immediately after reset, before any refill. Additional directed checks cover masked-word overwrite preservation, empty stores, oldest-lane duplicate-write ordering, later readback after intervening writes, and resets during an unfinished transaction or a stalled response. Partial writes here mean the task's per-lane 32-bit word mask; byte-write enables are not part of the contract.

These checks are unscored. They use the same independent logical-memory oracle but a separate, deterministic probe generator. Reset-cancellation checks use a dedicated clocked harness. No candidate can disable them, choose their seed, replace the engine or change storage/port/resource budgets through the action API.

## Full matrix on one final runtime

The runtime was frozen at `e97ec728838d9ef1a027269d95aa2b1b27a9945f`, packaged as 0.20.0, and imported from the installed wheel outside the checkout. All 124 runtime files match that wheel, and all 110 prior v18 runtime files are byte-identical. Unlike v19's final gate-only audit, **the complete acceptance, fault, API, example and replay matrix ran on the final runtime**. No correctness acceptance depends on carry-forward auditing. Later edits are reports and stricter checks in host scripts, not runtime changes.

The controlled matrix uses replay seed 190190 and identical fixed capacity, 64-cell/12-level mapper limits, service engine and workload for each competing architecture:

- Row-major, XOR and modular-add: both objectives on development, heldout and reserve splits—18 evaluations, 36 shape cases.
- Column-major: all three structural splits under the transpose objective—three evaluations, six shape cases.
- Legal wildcard procedural row-major, `always_comb` XOR, and automatic-function modular-add: three evaluations, six shape cases.

All 24 evaluations pass functional checks across 48 shape cases. All three core designs remain reward-eligible. Column-major is functionally correct on reserve but one geometry violates the fixed 2x service envelope, so its reward is zero; that is an explicit performance constraint, not a source-shape rejection.

Thirteen source-only attacks are rejected: aliasing, out-of-range addressing, dropped high column bits, unmasked row XOR, extra padding, latches, changed port width, synthesis-divergence directives, incomplete sensitivity, an additional read port, hidden sequential state, file-initialized uncounted storage and attributes. A bijection must cover exactly the declared physical capacity; extra storage or ports cannot appear merely by changing mapper outputs. Synthesized cells must be supported combinational gates, with complete driven outputs and no hidden state.

Nine additional **trusted-host engine mutations** are separately rejected: missing memory reset clearing, ignored write masks, read-data fabrication, aliased storage, reversed duplicate-store order, extra writes per bank per cycle, response expiry under stall, retained responses across reset and retained busy state across reset. All mutations compile successfully and fail simulation assertions, rather than being counted as rejected merely because of syntax errors. The extra-port engine completes a seven-write bank conflict in one cycle; the independent expected-cycle check catches it. Positive controls pass both engine harnesses in RTL and mapped-mapper simulation. These controls validate the judge's assumptions; they are not exposed candidate actions.

The final installed API passes its baseline, rejects an alias source and 16 invalid/boundary requests, enforces the horizon, and returns no private artifact paths. The example executes two valid optimization steps. Exact replay passes for both the development baseline and the heldout modular-add implementation, including scored metrics, unscored verification, recipe and tool fingerprints. Source and installed unit suites each pass 162 tests. The existing 22-family aggregate regression also ran on this exact installed wheel; final counts are in the summary (private evaluation artifact retained locally).

## Measured tradeoffs and reward checks

All 11 matching V19 controlled cases reproduce **exactly** the same scored metrics, workload hashes, mapped costs and rewards with the new unscored probes present. The fairness comparison fixes source, configuration, seed and tool fingerprint. Reward excludes all verification/cancellation cycles. No permitted-action reward exploit was found in this audit; this is not a claim that all future judge exploits are impossible.

| Objective / split | Row-major reward | XOR reward | Add reward |
|---|---:|---:|---:|
| Transpose / development | 1.0000 | 1.6160 | 1.7251 |
| Transpose / heldout | 1.0000 | 1.6486 | 1.6036 |
| Transpose / reserve | 1.0000 | 1.3751 | 1.3588 |
| Diagonal / development | 1.0000 | 0.6700 | 0.9581 |
| Diagonal / heldout | 1.0000 | 0.8279 | 0.8763 |
| Diagonal / reserve | 1.0000 | 0.7417 | 0.8084 |

The development XOR mapper uses three generic cells at one level; add uses nine at four levels. Add's higher service speedup wins development transpose reward, while XOR's smaller mapper wins heldout/reserve reward after the fixed overhead penalty. Row-major wins every tested diagonal profile among these three.

Column-major also has zero mapper cells, yet scores 0.6976/0.6012/0 on development/heldout/reserve transpose splits. It changes bank placement substantially and makes the row-oriented fill/readback cost visible. These costs are included for every design; examining only a favorable column-read phase would give a misleading result. Its zero area cannot bypass the service constraint.

All service metrics are clocked architectural-model measurements. Mapped cell/depth counts measure one mapper only, excluding the fixed bank engine, memories and lane replication. They are not routed timing, physical area, power or measured GPU performance. Same-author heldout/reserve tests remain labeled; no independent or agent-training study was performed.

## Budget, preservation and reproduction

The prospective caps were 80 layout evaluator calls, 180 mapper synthesis calls and 720 HDL simulations, including development failures and direct engine controls. Each new tool invocation has a 30s wall limit; existing 90s CPU/3GiB address-space/64MiB tool-file limits remain. The existing-family aggregate is separately limited to 43 evaluator calls. No SAT campaign was launched, and missing/unproven stages are never treated as verified. Exact actual counts and elapsed times are recorded in the summary. No new tools, paid services, credentials, security configuration changes, uploads or push were used.

Prior raw evidence remains in its verified archives. An older derived synthesis cache was archived and checked entry-by-entry before reclaiming disk space; its restoration manifest is retained. V18/V19 source commits, deliveries, private archives and transport parts were not changed.

With the final wheel installed and the existing pinned Icarus/Yosys tools available:

```bash
python -m unittest discover -s tests
python scripts/qualify_layout_v20.py --output /tmp/layout-v20-matrix --cache /tmp/layout-cache
python scripts/check_layout_engine.py --output /tmp/layout-v20-engine --cache /tmp/layout-cache
python scripts/check_layout_api_v20.py --output /tmp/layout-v20-api --cache /tmp/layout-cache
python examples/layout_rollout.py --cache /tmp/layout-cache
python scripts/replay_layout.py PRIVATE_RUN_DIRECTORY --output /tmp/layout-v20-replay --cache /tmp/layout-cache
python scripts/check_layout_score_neutrality.py --prior V19_MATRIX --current V20_MATRIX --output /tmp/neutrality.json
CHIP_RL_TRACE_ROOT=/tmp/aggregate-private python scripts/check_quality_aggregate.py \
  --output /tmp/aggregate --cache /tmp/existing-cache
```

Outputs must be fresh directories. Private artifacts include exact source, tables, engine variants, stimulus/oracle vectors, scripts, per-stage logs and journals; keep them outside candidate access. The old missed-reset control and the initial legal-source failures remain replayable from their archived testbenches. The final matrix and both replays use only the final wheel.

Physical evaluation remains blocked by absent OpenROAD/STA/PDK/platform. The prior exact K16 proof is preserved, but no new formal-tool proof or physical verification is claimed. The historical isolated CRC failure is not retroactively explained by a later aggregate pass. Source gates and tool limits are not an OS sandbox or an independent security audit. The repository still needs an owner-selected license before public reuse.

## Next distinct task opportunity

A small **fixed-point softmax/normalization datapath** would add nonlinear approximation and numerical-error contracts missing from the current exact arithmetic and memory-layout tasks. A useful first scope would use bounded signed logits, row-max subtraction, explicit output quantization, masks/all-masked behavior, and a high-precision host oracle with declared absolute/L1 error limits. Competing LUT/polynomial exponent and reciprocal implementations could trade actual mapped logic against measured service latency while keeping error and overflow constraints immutable.

This is a proposed next task, not implemented or authorized as a study here. Numerical stability must be part of its contract; NVIDIA's [cuDNN softmax algorithm documentation](https://docs.nvidia.com/deeplearning/cudnn/backend/latest/api/cudnn-ops-library.html#cudnnsoftmaxalgorithm-t) similarly distinguishes an overflow-avoiding algorithm using the input maximum. No cuDNN software or code was installed or reused.
