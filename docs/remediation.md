> Historical v2 profile results. The later default-path gap and mandatory-coverage correction are documented in [mandatory coverage](mandatory-coverage.md).

# V2 remediation and evidence

The [v1 viability study](v1-viability-study.md) found all ten fixed-workload ROMs
accepted, reward improvements from worse input waiting, insufficient dimension
shifts, and missing overflow/reset/cache-alias coverage. V1's runnable count was
not a viable-training count. V2 changes the evaluator and narrows the research scope.

Six constrained families have passed baseline, distinct-architecture and negative
qualification. DMA, router, scoreboard and accelerator are explicitly excluded from
the pilot because their command-tick contracts do not establish meaningful physical
scheduling/system behavior. Their original models remain for development/history.

The required path now includes fresh private workloads per action, same-source
parameter overrides, input release schedules independent of acceptance, strict
registered/storage/clock contracts, directed reset/arithmetic/tag tests, paired
baseline measurement, monotone area-first reward and explicit tool-stage status.
Raw evaluation inputs, seeds and logs remain host-only; observations expose coarse
outcomes. An external OS trust boundary is still required for adversarial agents.

Evidence is under [`evidence/v2`](../evidence/v2). The four qualification summaries
record all accepted baselines/alternatives and 52 original negative cases. Additional
regressions check finite ROMs small enough to pass the source-size limit, three
compute-family late-drop cases, cache reset after a populated line, stable gather
ordering, and the former delayed-acceptance reward exploit. A negative-case PASS
means rejection. Known v1 tests are retained under `legacy/v1-tests` rather than
silently repurposed; 32 current unit/reference/boundary tests pass.

Fresh heldout validation freezes a finite-catalog winner before generating new
private workloads, using larger random workloads and every supported structural
dimension with unchanged source. This is a deterministic catalog feedback experiment,
not trained RL, and complete enumeration in random order has the same search budget
and same development winner. It does not establish a learning advantage.

One small elastic family has 12-cycle transaction-safety BMC for baseline and alternate;
a corrupt design fails. Fixed-cycle equivalence separately passes identical RTL and
fails changed latency. There are zero unbounded proofs and zero physical validations.
The physical backend is optional and unvalidated; proxy gate depth is not routed timing.

Final counts: **6/6 pilot families**, **13 valid designs accepted**, **57 distinct bad
regression classes rejected**, **6/6 frozen winners accepted on fresh heldout workloads**,
**32 unit/reference/boundary tests passed**. Functional, synthesis, mapped-netlist and
same-source structural counts are each six. Bounded-formal count is one; unbounded
formal and physical counts are zero. The aggregate [summary](../evidence/v2/summary.json)
explains probe replacement/counting; raw development histories remain visible.

| Family / frozen design | Cells / baseline | Completion cycles / baseline | Offered latency / baseline | Reward |
|---|---:|---:|---:|---:|
| elastic / global4 | 0.938 | 1.000 | 1.000 | 1.0255 |
| dot / serial1 | 0.526 | 5.232 | 7.956 | 1.0808 |
| scratchpad / time_mux | 0.279 | 5.319 | 9.204 | 1.2887 |
| tensor / serial1 | 0.422 | 14.143 | 21.826 | 1.0696 |
| cache / lazy_cache | 0.984 | 1.000 | 1.000 | 1.0066 |
| gather / time_mux | 0.616 | 3.215 | 4.127 | 1.0707 |

Ratios below one mean less area/time. Tensor saves cells but takes roughly fourteen
times as many completion cycles and twenty-two times the offered latency. That is
an explicit area-first tradeoff, not performance improvement. Elastic and cache have
small measured headroom; the catalog does not establish broad optimization potential.

The final heldout evaluation walls were 0.44s elastic, 1.10s dot, 55.70s scratchpad,
3.77s tensor, 74.59s cache and 81.96s gather, with synthesis caches populated and
mixed simulator-program reuse. A separately measured dot run took 1.49s with a cold
cache, 0.42s for the same cached instance, and 0.62s for a fresh instance with cached
programs. These are observed costs on a four-CPU-quota executor, not throughput
promises. Mapped-memory compilation dominates some cases. Cache hits still execute
candidate RTL/netlist simulations; exact private baseline simulations may be reused.

Clean reproduction cloned code commit `013b1b9`, built/installed the 0.2.0 wheel in a
separate virtual environment, passed all 32 tests, accepted five compute designs and
rejected all 18 compute mutants. An external installed-package JSON API episode and
private artifact replay also passed. Tool packages were the independently installed
Debian Icarus 12.0/Yosys 0.52 prefix from the earlier clean-tool reproduction.

Reproduce broader evidence using:

```bash
python -m chip_rl.suite --output /tmp/pilot-private --cache /tmp/pilot-cache
PYTHONPATH=. python scripts/reproduce_formal.py --output /tmp/bounded-formal
PYTHONPATH=. python scripts/check_arrival_reward.py --output /tmp/arrival-private
```

`search_pilot.py` consumes partitioned qualification summaries (compute, scratchpad,
cache, gather) and freezes the finite-catalog winner before private heldout testing.
The development seed is a trusted replay fixture, not a production heldout seed.
Private replay vectors/seeds live outside Git and must never enter the agent workspace.

Verdict: suitable for a **limited, externally isolated, area-first RTL pilot**. This
is not evidence of ten viable environments, learned design ability, physical PPA,
or readiness for unrestricted autonomous training. Four families need architectural
redesign; OS isolation and real physical validation remain external prerequisites.
