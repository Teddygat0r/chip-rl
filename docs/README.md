# Read the current project

This guide describes local v27: **25 families, six pilots and nineteen experimental**. The added [requantization experiment](requant-v24.md) is separately qualified; the v23 publication candidate remains unchanged. “Pilot” is a repository category, not a claim of training readiness. The last published `codex/verified-20-family-checkpoint` (5f8890a) contains 20 families; newer local reports and these guides have not been pushed. Historical reports describe their own frozen versions.

Read these in order:

1. [Task inventory](task-inventory.md): choose a family and find its actual implementation, contract and evidence.
2. [Contracts](contracts.md): understand the six pilot interfaces, correctness gates, eligibility and paired rewards; use each inventory row's contract for other APIs.
3. [Verified walkthrough](walkthrough.md): install locally, evaluate existing elastic RTL and inspect the result and private replay journal.
4. [Viability assessment](viability-v12.md): understand measured tradeoffs and the missing evidence for a learning advantage; it is a v12 assessment, not a new v23 experiment.

Read the [cross-family reset audit](reset-audit-v27.md) for six repaired false acceptances in elastic, MSHR and router and the residual inventory. The [v26 requantization repair](requant-reset-v26.md) remains preserved and has a baseline/exploit regression.

## How an evaluation works

The trusted host selects the task, structural/workload coverage, objective and limits. An agent resets an episode, observes its contract and source, and submits complete RTL in `step({'rtl': source})`; CDC instead accepts constrained architecture parameters. The evaluator checks the candidate with independent reference models, real RTL simulation and synthesis/mapped replay where required, then compares feasible performance with a fixed paired baseline. See [pilot environment](../chip_rl/env.py), [evaluator](../chip_rl/evaluate.py), and the inventory for the other environment classes.

`reset(seed)` identifies the agent episode; it does not choose private evaluation seeds. Replay seeds and artifact paths belong to trusted-host tools. Typical reset returns `(observation, info)` and step returns `(observation, reward, terminated, truncated, info)`; the exact observation and action schema are API-specific. There is no single interchangeable CLI or universal hardware port layout for all families.

## Read results precisely

| Term | Meaning and limit |
|---|---|
| `tested_correct` | Passed the executed finite functional/structural checks; not a proof over every input or lifetime. |
| Eligibility | A correct design may violate the selected performance goal and earn zero; pilot `objective_eligible` and quality profile `objectives` are different schemas. |
| Reward | A task/profile-specific score against a paired baseline; inspect raw metrics and constraints, not just the scalar. Baseline is normally 1. No universal formula applies to every API. |
| Simulated cycles | Workload completion/latency in a digital model, not achieved clock frequency or routed timing. |
| Cells/depth | Generic mapped synthesis proxies, not SRAM-macro area, physical area, power or silicon readiness. |
| Bounded formal | A particular harness/configuration and finite horizon; absent or timed-out runs are not proofs. |
| Exact-instance proof | The [v18 K16 dot refinement](refinement-v18.md) applies to its pinned RTL, parameters and assumptions; it does not prove an entire family, mapped netlist or physical implementation. |

Current v23 evidence (private evaluation artifact retained locally) records final regression across the prior 24 families and detailed softmax qualification. Earlier alternate/mutant/formal evidence remains scoped to its historical report. There is **no routed physical validation, demonstrated OS isolation against a same-UID shell agent, independently executed v23 evaluation, or trained-policy learning advantage**. The sealed protocol is not itself an OS sandbox. Do not expose private artifacts or writable judge files to an untrusted agent.

Optional depth: [fixed-cycle controllers](cycle-contracts.md), [trust boundary](security.md), [sealed protocol](sealed-evaluator.md), [exact-instance proof](refinement-v18.md), and [latest softmax audit](softmax-review-v23.md). Start with these topics rather than reading every version report. [References and licenses](references.md) covers external sources; historical `validation.md` and `v1-viability-study.md` are not current qualification summaries.
