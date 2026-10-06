# chip-rl: constrained RTL research environments (0.4.0)

Six pilot families support latency-flexible RTL optimization: elastic pipelines,
INT8 dot products, banked scratchpads, INT8 tensor tiles, write-through caches, and
stable sparse gather. Four separate **experimental** families now implement physical
clock behavior: data-moving DMA, a queued router, a scoreboard with autonomous
completion, and concurrent load/compute. They remain excluded from pilot counts.

Version 0.4 adds explicit area/balanced/latency goals, Pareto measurements, additional
arithmetic architectures, stronger default workloads, new structural stress splits,
and independent cycle-controller monitors. See [iteration results](docs/iteration-v4.md)
for actual counts, costs, tradeoffs and exact reproduction commands.

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
