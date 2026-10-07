# chip-rl: constrained RTL research environments (0.11.0)

This publication contains the verified 20-family checkpoint and automatic private
evaluation journals. All 76 runtime files match local checkpoint `09ce9bd`; 85
unit tests passed on this publication tree. MSHR/TLB development is excluded.
Only aggregate results are published; historical detailed replay evidence stays
private. See [publication scope](evidence/publication/scope.json).

An agent proposes RTL (code describing a digital circuit), and these environments
check its behavior and measure circuit-size and workload-speed proxies. The tasks
cover small building blocks. A complete accelerator also needs system architecture,
software support, physical layout, timing closure and power analysis.

Six pilot families support latency-flexible RTL optimization: elastic pipelines,
INT8 dot products, banked scratchpads, INT8 tensor tiles, write-through caches, and
stable sparse gather. Four separate **experimental** families now implement physical
clock behavior: data-moving DMA, a queued router, a scoreboard with autonomous
completion, and concurrent load/compute. They remain excluded from pilot counts.

Version 0.4 adds explicit area/balanced/latency goals, Pareto measurements, additional
arithmetic architectures, stronger default workloads, new structural stress splits,
and independent cycle-controller monitors. See [iteration results](docs/iteration-v4.md)
for actual counts, costs, tradeoffs and exact reproduction commands.

Recorded v4 validation: 16 pilot and 13 experimental controller designs; 65 pilot
and 28 controller mutants rejected; 219 installed pilot API rejection checks;
12 fresh structural cases and 45 unit tests passed.

Three additional experimental blocks—register permutation, memory request coalescing,
and reorder/retirement—passed finite qualification locally. See [the expansion work](docs/expansion-v5.md)
and `python -m chip_rl.expansion --help`. New evidence: 9 valid designs, 30 mutants,
90 API rejection checks, 6 structural cases, and 54 unit tests passed. There are now
13 runnable families at v5: six pilots and seven experimental families.

V6 adds experimental SECDED ECC, packet CRC and multi-allocation free-list tasks.
V6 reached **16 runnable families: six pilots and ten experimental**.
The new suite accepts 8 valid designs and rejects 32 mutants; installed APIs pass
24 valid checks and 96 mutant rejections; 4 structural cases and 61 unit tests pass. See [integrity/allocation results](docs/integrity-v6.md) for final installed
API, structural and regression evidence and the bounded-formal limitations.
Run `python -m chip_rl.expansion ecc` or
`python examples/expansion_rollout.py --task freelist --objective area`.

V7 adds segmented prefix scan, stable signed top-K, and collision-aware histogram
updates. The suite now has **19 runnable families: six pilots and thirteen experimental**.
All 7 new designs pass; 31 mutants are rejected; installed APIs pass 21 valid checks
and reject 93 mutant checks. Six structural cases and 66 unit tests pass. See
[collective-task results](docs/collectives-v7.md) and [evidence](evidence/v7/summary.json).
All v5/v6/v7 work remains local pending publishing approval.

V8 deepens ECC, coalescing and histogram qualification without adding families.
Independent RTL and mapped-netlist checks pass 18 design/configuration cases and
reject 32 adversarial cases. The selected default suite accepts 9 designs and
rejects 35 mutants; installed APIs pass 27 valid checks and 105 rejection checks.
All 71 unit tests pass. New workloads close demonstrated reset-priority and late
histogram-loss coverage holes. See [v8 scope and results](docs/deep-qualification-v8.md)
and [recorded evidence](evidence/v8/summary.json). All v8 work remains local.

V9 makes independent reset-control and interrupted-state probes mandatory for
ECC, coalescing and histogram. It closes a demonstrated readiness-gated reset
coverage hole while preserving scored workload measurements. See
[reset qualification](docs/reset-depth-v9.md) for the full 19-family inventory.
Recorded v9 checks: 73 unit tests; 9 accepted designs / 41 rejected mutants;
18 accepted deep configurations / 44 adversarial rejections; 78 accepted API
checks / 309 mutant rejections. See [v9 evidence](evidence/v9/summary.json).
V9 remains local, with no new formal or physical validation claim.

V10 adds mandatory long-history verification for packet CRC and retirement,
including counter rollover, with independent models and separate verification
budgets. See [the plain-language introduction and technical results](docs/long-history-v10.md)
and [the next architecture assessment](docs/next-architecture-assessment.md).
The inventory remains19 families; no new task or physical claim is added.
V10 results:79 unit tests;6 valid designs /28 rejected mutants;18 valid long
configurations /45 adversarial rejections;78 valid API checks /330 mutant rejections.
[Recorded evidence](evidence/v10/summary.json) also preserves an initial undiagnosed
CRC API reset failure; the complete captured rerun passed.

V11 adds an experimental two-clock FIFO with protected architecture-parameter actions.
There are now **20 runnable families: six pilots and fourteen experimental**.
See [the CDC contract, examples and limitations](docs/cdc-v11.md). Digital simulation
and bounded formal checks do not establish physical CDC safety or analog MTBF.
The historical CRC reset failure remains unexplained; captured replays are retained.
The FIFO suite accepts 8 default/held-out runs (32 configurations), rejects 12 RTL
faults and passes 12 installed API checks. All 83 repository unit tests pass.
Four 24-step digital formal models pass; physical validation remains zero. See [v11 evidence](evidence/v11/summary.json).

This is a block-level research benchmark. No RL policy has been trained. Generic
cell counts, gate levels and workload cycles are proxies; there is no routed timing,
frequency, power, or silicon-readiness claim. Ten runnable families are not ten
production-ready ASIC/GPU design environments.

## Run locally

Requires Python 3.10+, Icarus Verilog 12 and Yosys with ABC. No paid services,
proprietary IP or model API is required. On a compatible Debian 13 host:

```bash
./scripts/install_tools.sh "$PWD/.tools"
source .tools/env.sh
python -m pip install .
python -m unittest discover -s tests -v
python -m chip_rl dot --objective balanced --artifacts /tmp/dot-private
PYTHONPATH=. python examples/rollout.py --task elastic
python -m chip_rl.suite --output /tmp/pilot-private --cache /tmp/pilot-cache
python -m chip_rl.cycle.suite --output /tmp/cycle-private --cache /tmp/pilot-cache
PYTHONPATH=. python examples/cycle_rollout.py --task router --cache /tmp/pilot-cache
```

Tool installation is local, version-pinned and requires Debian mirror access and
compatible shared libraries. `CHIP_RL_TOOLS` overrides the fallback prefix. Artifacts
and caches belong to the trusted host; use new artifact output paths. Qualification
of register-mapped memories can take minutes per candidate. `bad_* PASS` means the
bad candidate was rejected.

```python
from chip_rl import ChipEnv
from chip_rl.tasks import Config
from chip_rl.architectures import architecture

env = ChipEnv('dot', horizon=1, objective='balanced')
observation, info = env.reset(seed=17)
observation, reward, terminated, truncated, info = env.step(
    {'rtl': architecture(Config('dot'), 'product_pipe')})
```

Pilot JSON boundary: `python -m chip_rl.server --objective balanced`.
Experimental controller boundary: `python -m chip_rl.cycle.server`.
Both accept reset(task, seed) and step({rtl: source}); their timing contracts differ.
Python controller episodes use `chip_rl.cycle.env.CycleEnv`. Observations include the
full packaged contract. Agent reset seeds never select private evaluation workloads.
Only trusted-host evaluation exposes replay controls. Candidate actions cannot alter
constraints, goals, baselines, tool commands, paths or seeds.

## Correctness and objectives

All public pilot paths use the same mandatory variable-length checks. Unchanged
source is elaborated across structural variants, compared against independent models,
synthesized, then checked again as a mapped netlist. Tests include reset after dirty
state, signed extremes, stable stalls, progress, fairness, cache aliases, post-init
memory updates, unused input bits and mixed arrival/operand distributions.

Correctness and resource failures score zero. A functionally qualified design can
also score zero when it violates the chosen goal's performance limits. The default
**balanced** goal allows at most 2x completion cycles and 4x offered latency in every
case. Area and latency goals have different explicit constraints. Raw paired ratios
and all goal scores expose tradeoffs; scalar reward is not universal superiority.
Read [pilot contracts](docs/contracts.md) and [controller contracts](docs/cycle-contracts.md).

The controller tasks have fixed physical-cycle protocols and an area-only reward.
Their independent transfer/order/fairness/progress monitors supplement cycle-by-cycle
oracles. They model small, scoped blocks, not full AXI, coherent cache or GPU systems.

## Limits and provenance

Finite workloads do not prove universal correctness or prevent all adaptive hacks.
Formal evidence is bounded and configuration-specific; no unbounded proof is claimed.
No family has physical validation. OpenROAD/PDK are absent, and the optional physical
launcher remains unvalidated. Missing tools/timeouts/unproven stages never silently pass.

Tools have wall/CPU/memory/file limits and private working directories, but this
executor does not provide a dedicated OS sandbox for arbitrary candidate compilers.
Use an external VM/container or separate account with source-only RPC before granting
an untrusted agent access. Keep evaluator code, caches and private artifacts protected.
Memory maps to flip-flops/muxes, not characterized SRAM macros.

Original project code; no benchmark RTL or datasets were copied. See the
[reference/license audit](docs/references.md), [security boundary](docs/security.md),
and [v3 default-coverage correction](docs/mandatory-coverage.md). Historical evidence
under `evidence/v2`, `evidence/v3`, `artifacts/audit` and `legacy` is not current proof.
