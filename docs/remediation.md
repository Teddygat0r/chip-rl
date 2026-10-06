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

The final measured table and clean-checkout evidence are recorded after qualification
completes. Development qualification uses a trusted reproducibility seed; this seed
is not exposed by the agent API and is not a production heldout seed. Private replay
bundles must never be supplied to a training agent.
