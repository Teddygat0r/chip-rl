# Requantization reset repair (v26)

This experimental checkpoint repairs the specific reset false acceptance demonstrated in [v25](requant-audit-v25.md). The exact preserved bad source (private evaluation artifact retained locally) now fails the final evaluator and installed API with zero reward. Five valid architectures pass development and heldout splits (20 structural cases). No new family is added: 25 families remain, six pilot and nineteen experimental.

The unscored harness now poisons cold reset inputs and probes cancellation before and after scored work. It primes one accepted request, holds output backpressure and offers more requests for a bounded window, then applies a single-edge reset and drains. Acceptance is capacity-adaptive: it does not require a single-entry design to accept another request. All four shapes of the elastic pipeline accepted two pending requests before and after the workload; the other valid designs accepted one. Handshakes must be suppressed during reset regardless of inactive payload fields. Numerical input restrictions apply to accepted commands, not inactive reset payloads.

The cold-poison probes reject the preserved exploit immediately. A separate copied-testbench diagnostic disables only cold poisoning: the unchanged capacity gate still rejects the bad source in RTL and mapped simulation, while the good elastic control passes the entire workload. The original two-pending standalone test gives the same positive/negative outcomes. This establishes the specific repair; finite probes do not prove cancellation at every possible occupancy or lifetime.

## Executed checks

* Source and installed wheel: 188 unit tests each passed.
* Five valid architectures × two splits: 10 passed evaluations, 20 shape cases; all fourteen existing mutants plus the exact escaped reset source rejected.
* Installed API: existing three valid designs, one bad design and fourteen invalid requests checked; extra exact-exploit baseline/step/horizon check passed.
* Exact elastic replays: development and heldout passed.
* Independent 80-digit Decimal boundary model: 900 rows × four lanes × two designs = 7,200 comparisons; both RTL and mapped simulations passed.
* Inherited regression: 22-family aggregate plus layout/softmax APIs, 47 evaluator calls completed. Together with requant, all 25 families have current baseline functional/synthesis-backed checks.
* New formal checks: 0. Routed physical checks: 0. Cache reuse of validated mapped netlists is explicit; no new synthesis invocation was needed for requant.

Actual bounded usage is recorded in summary (private evaluation artifact retained locally) and ledger (private evaluation artifact retained locally): 33/48 requant evaluator calls, 0/120 fresh synthesis calls and 141/512 simulator invocations, plus the separately approved 47 aggregate calls. Expected bad-source failures count as rejected controls, not successful circuits.

## Frozen scoring and seed sensitivity

The oracle, accepted-input contract, workload generator, baseline/alternate RTL, synthesis, evaluator reward formula and all service thresholds are byte-identical to v25. All ten positive results at seed 250025 have identical scored fields to v25; only reset-probe coverage, recipe identity and wall time change. See comparison (private evaluation artifact retained locally) and matrix (private evaluation artifact retained locally).

Service eligibility remains seed-sensitive. With v24's recorded workload, heldout N3 serial offered-latency ratio was 17.38315 and old pipelined was 6.42360, exceeding the unchanged limit of 6. With seed 250025, serial is 8.09088 (still ineligible), while old pipelined is 3.33059 (eligible). The new elastic design is eligible on both splits, with rewards 1.1110156467 development and 1.0299673394 heldout. These are measured finite workload results, not universal service guarantees. No thresholds were relaxed.

## Reproduction and limits

Install the included 0.26.0 wheel in a clean virtual environment. Set `CHIP_RL_TOOLS=/path/to/extracted/usr` for the retained Icarus 12/Yosys 0.52 packages. From the checkout:

```sh
python -m unittest discover -s tests
python scripts/check_requant_api_v25.py --output /tmp/api --cache /tmp/cache
python scripts/check_requant_api_v26.py --output /tmp/exploit-api --cache /tmp/cache
python scripts/requant_reset_probe_v25.py --root /tmp/reset-controls --cache /tmp/cache
python scripts/replay_requant.py /path/to/retained/elastic_pipeline-development --output /tmp/replay --cache /tmp/cache
python scripts/check_quality_aggregate.py --output /tmp/aggregate --cache /tmp/cache
python scripts/check_layout_api_v20.py --output /tmp/layout --cache /tmp/cache
python scripts/check_softmax_api_v23.py --output /tmp/softmax --cache /tmp/cache
```

Exact executed matrix, boundary and warm-gate drivers, seeds, tool logs, RTL, mapped netlists and workloads are retained in the private artifact archive. Drivers contain the recorded executor paths; adjust paths for a new host. The numerical script requires a fresh explicit ledger reservation; do not overwrite historical ledgers. API and replay tests used the installed wheel. The source and installed runtime files were compared byte-for-byte.

Area and depth are generic synthesis proxies; cycles are workload simulation, not routed timing or power. Evaluation was authored and executed in the same environment, without a learned policy or an OS isolation claim. Private evaluator artifacts must remain outside candidate reach. This remains experimental and does not establish adversarial completeness, independent qualification or silicon readiness. The f9d7137 publication candidate and v24/v25 historical worktrees are unchanged. Nothing was pushed or uploaded.
