# Cross-family reset audit (v27)

This checkpoint extends the v26 reset lesson to three representative protocols, without adding a family. It demonstrates and repairs six false acceptances: two incorrect designs each for elastic storage, MSHR and router. The frozen v26 evaluators accepted all six; directed RTL and mapped checks exposed their contract violations. The repaired evaluator rejects the same sources and accepts two distinct valid architectures per family. This is finite same-author qualification, not an exhaustive reset proof.

The [bounded plan](reset-audit-v27-plan.md) was committed before evaluation. The publication candidate f9d7137 and v26 8bbee9e remain unchanged on separate worktrees, as do v24/v25. The new checkpoint is local; no tools, services, credentials, security settings, pushes or uploads were introduced.

## Contract inventory and prioritization

| Contracts | Outstanding state and existing coverage at v26 | Audit disposition |
|---|---|---|
| Elastic | At least four buffered responses; shared three-edge dirty reset, no occupied single-edge cancellation | Demonstrated and repaired |
| Dot, tensor, scratchpad, cache, gather pilots | Latency-flexible buffering allowed; memory/arbitration/cache state; shared three-edge dirty reset | Inspected; baseline regression only, no claim the new elastic gate covers them |
| Permute, CRC, free list, scan, top-K | Latency-flexible buffering/state; shared dirty reset | Inspected; deferred targeted controls |
| Coalesce, ECC, histogram | Shared dirty reset plus mandatory interrupted phase/control/payload sweeps | Different coverage; no assumed transfer of the defect |
| Router | Five independently queued outputs; fixed-cycle frames; multi-edge zero-input resets | Demonstrated and repaired |
| DMA, scoreboard, accelerator | One pending DMA read/job; multiple contexts; overlapping load/compute respectively; shared fixed-cycle harness | Inspected; router-only gate does not qualify these reset cases |
| Retire | Multiple tickets, independent completion, flush and reset semantics | Existing fixed-cycle/flush monitors; deferred targeted reset controls |
| MSHR | Multiple entries and up to four merged requesters per line; four-edge reset with request/response valid low | Demonstrated and repaired |
| TLB, including quality profile | Blocking or dual walkers plus cache; similar four-edge reset, distinct quality harness | Inspected; not changed by MSHR-only gate |
| Quality dot/tensor profiles | Buffered/iterative arithmetic, three-edge busy/stall probes | Separate APIs; inspected, deferred |
| Softmax | Buffering permitted; one-edge cancellation at several phases, but primarily one pending input | Residual coverage question; no demonstrated exploit in this audit |
| CDC FIFO | Multiple entries; coordinated local resets with skewed release; traffic prohibited until both domains release; parameter-only candidate actions | Different contract; no unsupported one-clock cross-domain requirement imposed |
| Layout | Candidate is stateless; trusted engine holds one warp; existing poisoned busy/stalled single-edge tests | No candidate-retained state; no transferred finding |
| Requant | v26 capacity-adaptive poisoned single-edge probes before/after work | Preserved baseline/exploit API regression |

## Reproductions and repair

`two_edge` delays the candidate's state reset until a second asserted edge. `retained` preserves occupied state only for particular reset-time control/input conditions. Neither source changes its interface or performs simulator-only behavior. [Control generator](../scripts/reset_controls_v27.py) and frozen candidate sources are retained with every run.

| Family | Escaped retained-state condition | Final probe | Valid controls |
|---|---|---|---|
| Elastic | All stages occupied, consumer blocked, reset payload bit0 set | Prime a request with consumer ready, offer further requests while blocked, apply one-edge poisoned reset with ready 0, drain 80 clocks, then alternate poison with ready 1; repeat after work | Four-stage elastic baseline and circular FIFO4 |
| MSHR | A merged line has more than one requester and request-valid is asserted during reset | Prime with downstream ready, offer extra requests under memory/client backpressure, cancel DUT and external source together with one edge and poisoned inactive inputs; drain 2048 clocks; repeat after work | Ring and shift waiter queues |
| Router | An occupied queue and input-valid/payload bit0 during reset | Independent fixed-cycle model creates five occupied queues, then one-edge zero-input or all-one-input reset, followed by empty frames; prefix and suffix outside scored stats | Search-loop baseline and decoded arbitration |

The elastic probe observes four accepted requests for both valid designs. MSHR accepts 8, 16, 32 requests for 2, 4, 8 entries respectively, before and after work. Only the existing elastic minimum capacity 4 is required; MSHR extra acceptance is adaptive and does not mandate a new ingress policy. Reset payloads are inactive commands; downstream memory responses are canceled together with the MSHR. No stale external response is injected after reset release.

The first delayed-reset router diagnostic used all-one receiver-ready bits. Its queues drained through normal operation, so that particular probe did not expose retained occupancy. Holding receiver-ready low exposed it. Both attempts are retained; the first is not counted as a successful rejection. The repaired router gate includes both reset payload cases. No new requirement is imposed on top-level frame outputs while reset is asserted; post-reset behavior is checked against the existing model.

Repairs are conditional on `elastic`, `mshr`, and `router`. Sharing a Python module does not imply other families received this cancellation coverage. Deferred families may deserve targeted follow-up, but source inspection alone does not prove a false acceptance.

## Executed qualification

See machine-readable summary (private evaluation artifact retained locally), discovery (private evaluation artifact retained locally), final matrix (private evaluation artifact retained locally) and budget (private evaluation artifact retained locally).

* Frozen discovery: three baselines and six bad sources accepted. All six bad sources subsequently fail a directed contract probe in both RTL and mapped simulation; good controls pass.
* Exact-final matrix: six valid evaluations passed, six preserved bad sources rejected with zero reward. Source and installed unit suites each passed 190 tests.
* Each affected installed API checks baseline, distinct valid source, preserved retained-state mutant, three invalid action shapes and the episode horizon. Each affected alternate has a full exact-seed evaluation replay.
* The initial elastic replay driver compared returned Python tuples with lists read from JSON and raised an assertion. Comparing serialized results passed without another HDL evaluation; this driver failure remains in the logs.
* Existing 47-call aggregate: 22-family default baseline/fault checks plus layout and softmax APIs. A separate two-call requant baseline/preserved-exploit regression covers the 25th family. This is baseline regression, not a repeat of every historical alternate/mutant matrix.

Final review caught a resource-accounting regression before handoff: router reset-only frames were initially included in the existing scored-cycle budget. The final code checks that limit before appending unscored probes. Two new unit checks preserve acceptance at the original exact limit and rejection one clock below it. Router's four-control matrix, three-call API, full replay and two-call aggregate row were repeated against the final wheel (ten additional calls within the 48-call cap). Earlier results are retained; the final router aggregate row supersedes the earlier row. Other protocol runtime files are byte-identical between the two wheels; the non-router cycle path and all generated router benches/vectors at the qualification settings are unchanged.

For all three baselines, the scored metrics, eligibility and reward at seed 270027 are identical before/after repair. The workload generators, contracts, baseline RTL, thresholds and reward formulas were not changed. Probes run outside scored streams and counters. The final valid alternatives earn 0.8084494701 (elastic FIFO4), 1.0038165520 (MSHR shift), 1.4915342899 (decoded router). These finite workload/proxy measurements are not generalized performance claims. This audit holds its comparison seed fixed; it does not establish seed-independent service eligibility.

Final usage: 45/48 evaluator calls, 26/120 fresh synthesis invocations, 469/512 simulations (including 21/48 direct diagnostics), plus the separately approved 47-call aggregate.

The simulator count uses canonical `tool-logs` records: pilot/cycle artifact copying can duplicate the same log under a case directory, and those copies are not new invocations. Direct diagnostic failures, including the unsuccessful first router probe, remain counted. No timeout or incomplete evaluation is a success. New formal 0; physical 0. Synthesis caches are reused where source, parameters and tool fingerprints match; RTL and mapped simulation are performed as recorded.

## Reproduce

Install the bundled 0.27.0 wheel in a clean virtual environment. Use the retained Icarus 12/Yosys 0.52 Debian packages and set `CHIP_RL_TOOLS=/path/to/extracted/usr`. These depend on host libraries; the bundle is not an OS image.

```sh
python -m unittest discover -s tests
python scripts/check_reset_api_v27.py elastic --output /tmp/elastic-api --cache /tmp/cache
python scripts/check_reset_api_v27.py mshr --output /tmp/mshr-api --cache /tmp/cache
python scripts/check_reset_api_v27.py router --output /tmp/router-api --cache /tmp/cache
python scripts/check_quality_aggregate.py --output /tmp/aggregate --cache /tmp/cache
python scripts/check_layout_api_v20.py --output /tmp/layout --cache /tmp/cache
python scripts/check_softmax_api_v23.py --output /tmp/softmax --cache /tmp/cache
python scripts/check_requant_api_v26.py --output /tmp/requant --cache /tmp/cache
```

The private archive includes exact executed discovery/final/direct/replay drivers, sources, workload vectors, mapped netlists, logs, seeds and the budget ledger. Drivers use recorded executor paths; adapt those paths on another host and create a new ledger instead of overwriting historical evidence. Discovery uses frozen v26 runtime; final checks use the installed v27 wheel. The wheel's runtime files were compared byte-for-byte with the committed source.

## Limits and next work

The three demonstrated judge gaps are repaired within tested scope. Other families' reset coverage remains an audit finding/question, not a claim of correctness or a fabricated exploit. Deep phase coverage, longer histories and adversarial designs can reveal further gaps. No independently executed campaign, trained-policy learning advantage, comprehensive OS isolation, unbounded formal proof, routed timing, power estimate or silicon readiness is established. Keep judge files, private seeds and artifacts outside candidate reach. Generic mapped cells/depth and simulated cycles remain proxies.
