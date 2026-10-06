# chip-rl: ten runnable RTL optimization environments

This GitHub delivery contains the audited source and compact validation evidence.
[Publication provenance](docs/PUBLISHING.md) explains the original audit commit and
the generated artifacts intentionally omitted from Git history.

A local, dependency-light v1 for agents that edit synthesizable RTL or choose
constrained architecture parameters. It contains ten distinct functional contracts,
independent Python reference machines, parameterized workloads, elastic RTL
baselines/alternatives, task-specific bad mutants, reproducible evaluation artifacts,
and a `reset`/`step` interface. No model API, paid service or proprietary IP is needed.

The tasks are elastic pipelines, exact INT8 dot products, banked scratchpad arbitration,
burst DMA address generation, five-port packet routing, four-context scoreboarding,
2x2 INT8 tensor computation, a memory/copy/dot accelerator subsystem, a 1KiB
write-through cache controller, and sparse gather/stable compaction. See
[the exact contracts and scope](docs/contracts.md) before training.

## Run

Requires Python 3.10+, Icarus Verilog 12 and Yosys with ABC on `PATH`. The qualification
runs used Debian Icarus 12.0 and Yosys 0.52. For a Debian 13 host without those tools:

```bash
./scripts/install_tools.sh "$PWD/.tools"
source .tools/env.sh
```

This installs under the requested local prefix. It requires access to Debian's
public package mirror and compatible host shared libraries. Package versions are
pinned; if the mirror ages them out, use an appropriate Debian snapshot. In this
executor the prepared prefix is `/workspace/tools/root/usr` and is discovered by
fallback; `CHIP_RL_TOOLS` can override it.

From the repository root:

```bash
python -m unittest discover -s tests -v
python -m chip_rl dot --artifacts /tmp/dot-run
python -m chip_rl router --stages 2 --emit > /tmp/router.sv
python -m chip_rl router --rtl /tmp/router.sv --artifacts /tmp/router-run
PYTHONPATH=. python examples/rollout.py --task elastic
python -m chip_rl.suite --output /tmp/chip-rl-release
PYTHONPATH=. python scripts/replay.py /tmp/chip-rl-release/dot/alternate --output /tmp/dot-replay
```

Artifact destinations must not already exist. Full qualification includes mapped
memory designs and takes several minutes; scratchpad netlist elaboration is the
largest cost. Each bad-case `PASS` means the evaluator **rejected** that design.
Replay recomputes the trusted workload and checks the recorded acceptance outcome;
its standalone reward defaults to 1 for correct candidates without a loaded baseline.

```python
from chip_rl import ChipEnv

env = ChipEnv("tensor", horizon=3)
observation, info = env.reset(seed=17)
observation, reward, terminated, truncated, info = env.step({"stages": 2})
# Or: env.step({"rtl": complete_candidate_source})
```

For an external process, an installed package also supports a JSON-lines action API:

```bash
python -m pip install --no-deps --no-build-isolation .
printf '%s\n' '{"op":"reset","task":"elastic","seed":17}' '{"op":"step","action":{"stages":2}}' | python -m chip_rl.server --horizon 1
```

Every observation includes the full packaged contract text. The server accepts no
candidate paths, commands, baseline values or constraint overrides. It does not
provide an OS sandbox. `chip_rl.alternates.alternate(Config(task))` emits each
specific alternative for an RTL action.

`reset` really evaluates the baseline and fails if the tools or design fail.
`step` evaluates the action, returns metrics and correctness, and ends at the chosen
horizon. Correctness failures yield zero reward; valid designs are scored against
the fixed baseline's measured generic cell count and useful-work cycle metrics.
Agent actions cannot change task constraints, harness or baseline. The API is
Gym-style without a Gymnasium dependency or a fixed-size numeric observation space;
observations contain RTL text and structured metrics.

## Evidence and limitations

Post-audit qualification: **10/10 families, 40 valid cases passed, 30 bad RTL cases
rejected, 34 unit tests passed.** Bounded formal evidence covers one family; physical
validation covers zero. See [final audit, measured matrix and scope](docs/audit.md) (the [initial qualification history](docs/validation.md) is retained).

[Post-audit summary](artifacts/audit/summary.json) records every valid and negative
case. Published task/case directories retain result JSON. Full candidate RTL, testbenches,
vectors, logs and mapped netlists remain in the cloud task bundle and can be
regenerated with the suite command; they are intentionally omitted from this compact
GitHub snapshot. See
[unit-test output](artifacts/audit/unit-tests.txt), [ten installed-package rollouts](artifacts/audit/external-rollouts.jsonl),
and [tool provenance](artifacts/toolchain.json).

Correctness requires both RTL and synthesized-netlist simulation to agree on all
outputs, stall behavior and workload completion. Synthesized cell counts are an
area **proxy**; measured latency/throughput is in cycles. There are no routed timing,
frequency or power claims. These small tasks teach block-level transformations;
they do not constitute silicon-ready ASIC/GPU designs. Memory maps to registers/muxes,
not SRAM macros. Post-audit alternatives include task-specific implementation changes as well as
buffer-depth changes; their reward improvements do not isolate kernel-only gains or
claim global optimality. The initial release used buffering changes alone.

Formal evidence is limited to 12-cycle transaction safety for a small elastic
pipeline, with a failing mutant control. A separate bounded fixed-cycle equivalence
helper has tests showing why changed latency cannot be judged by that contract.
Other families have no formal proof. Every missing/timeout/unproven stage is explicit.

OpenROAD/ORFS and a PDK are absent here; **physical validation is zero**. The optional
launcher can use a separately installed trusted ORFS Nangate45 flow:

```bash
python -m chip_rl.physical elastic --flow-root /path/to/OpenROAD-flow-scripts/flow --output /tmp/physical-elastic
```

That integration is unvalidated in this executor. It first requires functional
qualification, preserves raw physical reports, and never marks setup or flow exit
alone as physically verified. Review timing/DRC/library assumptions explicitly.
Do not include its outputs in training rewards until the physical flow is qualified.

The [evaluator boundary](docs/security.md) protects against candidate-source edits
and resource abuse under a constrained RTL action interface. It is not a hardened
multi-tenant compiler sandbox. Published heldout seeds are replay examples; keep
fresh evaluation seeds private on the trusted host for real training.
[Reference and license audit](docs/references.md) explains the open-source research
and tools used; no external benchmark RTL/data was copied.
