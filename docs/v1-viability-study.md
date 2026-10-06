# chip-rl empirical viability evaluation

## Verdict
NO-GO for autonomous RL training toward ASIC/GPU design using the released reward.
The software is a useful engineering starting point, not a scientifically validated
RL environment suite. No model was trained and no paid model/service was used.
Published commit dbf986de789b928171f61d29f9ebac7ef0e4b2aa remains unchanged.

The study completed before the parent requested stopping duplicate evaluation.
No additional experiments were started after that instruction. All files are in
/workspace/chip-rl-viability on the original cloud executor.

## Method and totals
364 instrumented evaluator calls, 81 candidate configurations across ten families,
four-query scripted feedback policy versus four-query seeded random search, then a
finite catalog sweep. The scripted policy is not trained RL. Candidate design code
was written by the assistant; new designs include ring FIFOs, shared multipliers,
serial bank/port/context/gather engines and lazy cache reset.

120/120 baseline-and-valid-candidate generalization cases passed simulation,
synthesis/netlist validation: unseen seed, separate workload generator, changed
structure, and default-size conditions. Structural transfer regenerates RTL from
an architecture template; it is not unchanged-RTL or learned-policy generalization.
Each family used one random-search draw and one scripted run, so no statistical
algorithm-superiority claim is warranted. Scripted search tied random in six and
won in four families. Every catalog selected the zero-buffer combinational bypass.

293 evaluator calls were accepted and 71 rejected. Accepted includes known-incorrect
adversaries; it is NOT a count of genuinely correct designs. One deliberate infinite
HDL loop timed out at 30.01 s. Two prototype-generator syntax errors were corrected
before search. No unexpected valid-generalization failures or orchestration failures.

## Critical findings
- Input-independent answer ROMs passed the training evaluator in all 10 families;
  9/10 scored above the baseline. All failed an unseen seed. Counterexample source,
  vectors and logs are in runs/<family>/attack-rom*.
- Seven families accepted a design that drops responses after the first 64 accepted
  commands, then rejected it on longer workloads.
- Dot and accelerator 16-bit accumulators passed training and a second random seed;
  signed-overflow directed tests and the challenge generator rejected them.
- Accelerator/gather missing-memory-reset designs passed normal initialized workloads
  and a second seed, then failed cold reads. Relevant standalone unit tests are not
  integrated into the reward gate.
- A default-size cache with truncated high tag bits passed training (reward 1.1911)
  and the published challenge, but failed an address-alias test with a passing golden
  control. Private random seeds alone cannot fix missing workload dimensions.
- Constant-zero, duplicate-output and deliberate RTL/synthesis-divergence candidates
  were rejected in all 10 families. Last-lane starvation was rejected in scratchpad,
  router and scoreboard. The evaluator is useful but incompletely covering contracts.
- Elastic bypass: 2 cells vs baseline 81, score 1.398, but 113 workload cycles vs 111.
  It satisfies the current stream contract without providing elastic storage.
- DMA gating example: ungated one-stage uses 709 cells, 113 cycles, offered-to-retired
  useful latency 5.4167; gated uses 710 cells, 114 cycles, latency 5.75. Reward rises
  from 1.1555 to 1.1871 because accepted-to-retired latency excludes deferred acceptance.
  This is a demonstrated dominated design receiving a higher score.
- Four shared output-delay stages are largely removable padding, not arithmetic
  retiming. Zero-cycle combinational responses earn maximum latency credit without
  a clock-period, combinational-path or minimum-buffer constraint.

## Per-family measured matrix
All ratios below compare a meaningful alternative against the paired baseline on
an unseen challenge workload. Values are actual generic cell-count and useful
throughput ratios, not routed area/frequency/power. Area reductions with throughput
losses are real tradeoffs, not across-the-board performance gains.

| Family | Classification as released | Alternative | Cells ratio | Throughput ratio | Fresh baseline-source wall s* |
|---|---|---|---:|---:|---:|
| elastic | unsuitable current form | fifo2 | 1.444 | 0.979 | 0.22 |
| dot | needs work | serial1 | 0.510 | 0.240 | 0.70 |
| scratchpad | needs work | time_mux | 0.211 | 0.240 | 54.99 |
| dma | needs work | kernel1 | 0.721 | 0.972 | 0.41 |
| router | needs work | time_mux | 0.237 | 0.219 | 26.26 |
| scoreboard | unsuitable current form | time_mux | 0.318 | 0.286 | 4.97 |
| tensor | needs work | serial1 | 0.409 | 0.083 | 2.16 |
| accelerator | unsuitable current form | time_mux | 0.526 | 0.418 | 26.91 |
| cache | needs work | lazy_cache | 0.925 | 0.977 | 19.73 |
| gather | needs work | time_mux | 0.580 | 0.254 | 54.55 |

*Fresh same-source timing samples use different workload lengths and are not a
controlled cross-family speed ranking. Hardware parameters match the default baseline.

Scope limitations: elastic lacks a storage/capacity requirement; dot/tensor are exact
arithmetic kernels; scratchpad maps storage into registers/muxes; DMA emits addresses
and masks with supplied acknowledgements rather than moving data; router has no packet
queues; scoreboard advances execution timers on logical commands rather than physical
completion events; accelerator is a copy/read/write/dot opcode machine, not an autonomous
DMA+compute subsystem; cache uses host-supplied refill data; gather handles four lanes.
The scoreboard and accelerator need contract redesign for the stated GPU/system goal.
No family is ready for unrestricted autonomous training on the stock reward. Dot,
tensor, scratchpad and gather are reasonable first candidates for a repaired pilot.

## Cost and reproducibility
152 accepted fresh-synthesis calls: median 1.7845 s, p95 25.666 s, max 54.987 s;
median child CPU 1.6693 s. 141 accepted exact-source synthesis-cache calls: median
0.268 s, p95 1.149 s, max 13.613 s. The study cache is external instrumentation,
not a feature of the published evaluator. Cached calls still simulate RTL and gates.
Toolchain was fixed; caches must not be reused across changed tools/constraints.
Total instrumented child CPU 1115.55 s; summed evaluation wall 1143.993 s (parallel
work overlaps). Main study used two workers, with some auxiliary probes concurrently,
under a 4-CPU quota. Cost distributions include malicious accepted candidates.
10,000 fresh trials at the observed median is about 5 CPU-worker wall hours; at
55 s for a large memory candidate it is about 153 worker-hours. These are workload-
dependent extrapolations, not measured training runs.

A fresh GitHub clone at the pinned commit, documented Debian local dependency
installation, all 34 unit tests, dot's seven-case qualification with existing elastic
formal smoke, and omitted-artifact regeneration/replay succeeded. Logs are included.
The original dependency versions were Icarus 12.0 and Yosys 0.52 with ABC.
No new formal proof of these architectures was performed; no physical flow was run.
No routed timing, frequency, physical area or power was measured. No unsafe
filesystem exploit was executed. Compiler processes still lack a hardened OS sandbox.
Seeds/counterexamples are exposed on the training interface; same-user shell access
cannot protect evaluator code or private tests.

## Minimal next fixes, in order
1. Before positive reward, use private randomized validation plus deterministic cold
   reset, all address/tag bits, overflow, wrap, fairness and long-stream tests. Move
   applicable standalone unit coverage into candidate qualification. Add small formal
   proofs where practical; missing/unproven proof must remain explicit.
2. Repair the objective: offered-to-retired/end-to-end work metrics, fixed traffic
   traces, throughput constraints, meaningful clock/critical-path constraints and
   minimum storage where required. Separate area/latency tradeoffs instead of relying
   on the current arbitrary weighted score; remove gratuitous baseline delay padding.
3. Redesign physical-time completion contracts and independent producer/consumer
   traffic for scoreboard, DMA, router and integrated accelerator. Add actual DMA/
   compute concurrency before claiming integrated-accelerator training viability.
4. Isolate the trusted evaluator and private tests in a separate identity/container
   with no network and resource limits. Use a constrained action API; a source linter
   is not a compiler-exploit sandbox.
5. Cache synthesis by complete source/tool/constraint identity and batch workloads.
   Keep validation provenance clear. Then run multiple policies/seeds with equivalent
   budgets and genuinely withheld tasks before making any RL-learning claim.

## Evidence
metrics.json and family-metrics.csv give machine-readable aggregates. Each
<family>-summary.json includes trial-by-trial search, paired generalization and
adversarial outcomes. Arrival accounting is in *-arrival.json; cache aliasing in
cache-alias.json; boundary/timeout probes in edge-checks.json. All sources and logs
remain in runs/. The compact evidence archive includes scripts, reports, summaries,
per-run result JSON and candidate RTL; bulk netlists/tool caches are omitted.
The published checkout is unchanged; no push was made during this evaluation.
