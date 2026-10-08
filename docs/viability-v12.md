# A credible optimization demonstration

The suite is useful as an RTL-optimization research harness. It has not established
that RL finds better hardware than enumeration, random search or a competent human.
There is no trained policy in this checkpoint.

Start with two task tracks rather than maximizing family count:

* TLB/page walking has a measured architectural tradeoff: two walkers versus one
  give a paired aggregate cycle ratio 0.5333, latency ratio 0.7839 and generic-cell
  ratio 1.4209. The reward is 1.0321. This is concurrency/area variation under a custom
  small translation contract, not an ISA-compliant MMU or a chip-speed claim.
* INT8 dot/tensor arithmetic is inexpensive and exactly checkable. In the recorded
  v4 development workload a serial dot used 0.526 times baseline cells but 3.126 times
  cycles, with much worse offered latency. It earned area reward 1.075 and zero
  balanced reward because it missed the explicit performance limits. A pipeline's
  small development gain did not generalize uniformly to held-out K values.

MSHR merging is a useful third correctness/concurrency challenge. Its current
alternative has aggregate cell ratio 0.9832 and unchanged paired workload metrics,
for reward 1.0038. That is a modest measured change, not a strong optimization result.
The router's much larger historical cell reduction mostly exposes inefficient
starter RTL and compiler lowering, so it is a poor headline for agent capability.

The next experiment should use equal tool-evaluation and wall-time budgets for
catalog enumeration, random search and the proposed agent. Report all attempted
candidates, correctness yield, best feasible raw metrics, multi-seed uncertainty
and held-out structures/workloads. Freeze baselines and reward weights before the
comparison. A two-choice catalog alone cannot demonstrate a learning advantage.
Free RTL proposals need an isolated judge and retained failed attempts too.

Reward is an optimization objective, not independently established user value.
Generic-cell reduction can worsen service latency by orders of magnitude. Fewer
workload cycles with more walkers does not establish a higher routed clock rate,
lower power or a faster complete accelerator. Keep area, completion cycles, offered
latency, memory traffic and feasibility limits visible alongside reward.

Recorded warm-cache v12 wall times were 5.0/9.8 seconds for baseline/alternate MSHR
and 13.2/23.7 seconds for TLB. Earlier baseline measurements were about 1.6 seconds
for dot,5.6 for tensor,88 for cache and 179 for gather. These are shared-host samples,
not controlled cold-run comparisons or a throughput guarantee. For perspective,
1000 valid TLB evaluations at those measured rates would take roughly 3.7–6.6 hours
serially, before cold synthesis, agent inference, repeats and held-out qualification.
Memory-heavy families can be much more expensive. Parallelism is bounded by CPU,
memory and tool resource caps; hidden seeds and baseline pairing must stay intact.

Evidence gaps are no trained-agent comparison, limited statistical generalization (including a fixed custom page-table memory map),
no routed PPA, incomplete bounded formal coverage, no unbounded proof, and no
provided OS-level separation between agent and judge. The original CRC failure
remains unexplained because its seed/logs were lost. Subsequent passing replays
and improved logging do not resolve it. The project also currently has no top-level
LICENSE file; this work does not assign an owner-selected license.

Sources are the measured [v4 tradeoffs](iteration-v4.md), v4 elapsed costs (private evaluation artifact retained locally),
v12 memory results (private evaluation artifact retained locally), v12 API costs (private evaluation artifact retained locally) and [v12 reproduction notes](reproduction-v12.md).
No additional broad expansion is started while the parent reviews strategy.
