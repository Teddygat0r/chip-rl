# Bounded search controls on the v12 runtime

The completed experiment does not establish a learned-agent advantage. It compares
fixed enumeration, seeded random search and a handwritten feedback rule over the
existing TLB, INT8 dot and INT8 tensor catalogs. No new RTL architecture was generated,
no policy was trained and no model or paid service was called.

The plan was committed at `93c225f64174a9bf2a857ec8105bdcfe145fb8b1` before
measurement. Each method gets two development queries for TLB or three for dot and
tensor, including the baseline. Three trials use public policy seeds 17, 29, 43 and
independently drawn private workload seeds. Methods share the same workload within
a task/trial. All winners are frozen before any held-out evaluation: TLB uses
six-entry targets and longer traffic; arithmetic uses K=1 and K=3. These structural values were already exercised in earlier iterations; only the
workload instances are newly drawn. This is not a blind unseen-structure benchmark.
The exact frozen
source bytes are reused rather than regenerated for the new dimensions.

The handwritten rule knows the previously authored templates and their historical
results. It tries the two-walker TLB, product pipeline or four-lane tensor first,
then uses observed reward when choosing the next remaining dot alternative.
It is a small search controller with prior knowledge, not an unbiased AI agent.

## Actual results

| Task / method | Mean best development reward | Mean held-out reward |
|---|---:|---:|
| TLB, all three methods | 1.032232 | 1.041465 |
| Dot, fixed enumeration | 1.000000 | 1.000000 |
| Dot, random search | 1.002089 | 0.995494 |
| Dot, handwritten feedback | 1.002089 | 0.995494 |
| Tensor, all three methods | 1.000000 | 1.000000 |

Every TLB search chose two walkers. Its held-out aggregate generic-cell ratio was
1.3833, cycle ratios were 0.5226–0.5297, latency ratios 0.7679–0.7790 and memory-read
ratios 1.0161–1.0203. These are paired digital workload results under the custom memory
map; they do not establish routed frequency, area or power.

Fixed-order dot enumeration did not reach the pipeline within its partial catalog
budget and retained the baseline. Random and handwritten search selected the
pipeline in two trials, with identical winners and scores. At held-out K=1 the
pipeline used 1.0405 times baseline generic cells and scored 0.9860–0.9864. At K=3 it
used 0.9772 times cells but had higher offered latency, scoring 1.0001–1.0005.
The tiny development gain therefore did not transfer across these dimensions.
Changing the enumeration order could remove the development difference; it is not
evidence of a learning advantage.

Every tensor search kept the baseline. Both serial alternatives were functionally
correct but failed the fixed balanced-performance eligibility limits. Across the
study,12 measured designs were correct yet objective-ineligible. This demonstrates
why correctness, useful performance and reward must be reported separately.

## Counts, cost and limits

There were 46 distinct real evaluations:9 TLB,22 dot and 15 tensor. All 46 passed RTL
and mapped-netlist qualification. The comparison charged 72 development queries and
45 held-out checks across methods. Identical source/config/private-seed queries
share one measured result, so 117 charged queries are **not**117 independent hardware
experiments. Three private trials per task support descriptive results only.

| Task | Distinct evaluations | Actual task elapsed time |
|---|---:|---:|
| TLB | 9 | 231.7s |
| Dot | 22 | 40.2s |
| Tensor | 15 | 101.0s |

Tasks ran concurrently on the shared host with existing compilation caches.
Within each task, method order rotates across trials. Per-method nominal time
charges reuse the first measurement's runtime. Query budgets match, but this is
not a controlled cold-run or equal-wall-time comparison and cannot establish a
wall-time search advantage. Baseline pairing and every mandatory qualification
stage remain enabled.

The predeclared physical-evaluation limits were 12/30/27 by task, at most 69 total.
The runner checks those limits before starting a new evaluation and stops if less
than 300MiB of disk space is available. Existing tool caps remain 90 CPU seconds,
3GiB address space,64MiB per output file and 120 seconds wall time for these tasks.
There is no separate hard experiment-wide wall deadline. All 99 final unit tests passed (97 before measurement),
including budget, feasibility, held-out freeze and shared-result isolation checks.
The 88 runtime files remain byte-identical to v12; this iteration adds study code,
tests and evidence only. It adds no environment, formal proof or physical result.

## Reproduce

Use the v12 offline wheel/tool delivery or install the unchanged runtime from this
source tree. Run outside the source directory to exercise the installed package:

```sh
python /path/to/chip-rl/scripts/compare_search.py tlb --output /private/new-tlb --cache /private/memory-cache
python /path/to/chip-rl/scripts/compare_search.py dot --output /private/new-dot --cache /private/pilot-cache
python /path/to/chip-rl/scripts/compare_search.py tensor --output /private/new-tensor --cache /private/pilot-cache
```

Each output directory must be new and host-private. The run preserves its private
seeds, immutable frozen selections, candidate sources, raw evaluation results,
generated inputs and compressed tool diagnostics. Public summaries omit workload
seeds. Reproduction with new random workloads need not yield identical rewards;
exact replay uses the retained per-evaluation inputs with the existing trusted
replay tools. No private judge files should be mounted into an agent workspace.

The strongest next evidence would compare actual candidate-generating agents
against strong search baselines, with meaningful search spaces, a separate judge,
new unreused hold-outs and routed validation where available. This small catalog
control does not justify adding more families or claiming RL capability.

Two selected measurements were replayed using the bundled HDL package installation
and a fresh cache: the dot pipeline at held-out K=1 and the two-walker TLB at six
entries. All public qualification fields reproduced exactly except elapsed time
and cache-hit counters. The first dot replay checker failed because saved JSON
weight arrays were lists while the live evaluator returned tuples. Its saved HDL
results already matched; canonical JSON comparison and two regression tests fixed
the checker, and the repeated dot check passed. That failed check and its artifacts
remain recorded in `evidence/v13/replay-check-correction.json`; no RTL, reward or
qualification rule was changed. These are three extra replay calls (one checker
failure and two successful checks), separate from the 46 distinct search evaluations.
The original CRC anomaly remains unrelated and unresolved.
