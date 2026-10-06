# chip-rl: a constrained RTL research pilot

**Validated: six families, thirteen valid designs, fifty-seven rejected bad regressions,
six fresh heldout winners, and thirty-two tests.**

V2 remediates an empirical viability audit that found reward hacking and insufficient
contracts in v1. Six families are pilot candidates: elastic buffering, exact INT8
dot products, banked scratchpad arbitration, 2x2 INT8 tensor computation,
write-through cache control, and stable sparse gather. Four additional models
(DMA, router, scoreboard, integrated accelerator) remain **experimental and excluded**
from pilot counts. Ten runnable v1 tasks did not establish ten viable RL environments.
Historical v1 results are retained under `artifacts/audit` and `legacy/v1-tests`.

This is an area-first block-level optimization benchmark, not an ASIC/GPU design
system. No RL policy has been trained. Cell counts and workload cycles are proxies;
there is no routed timing, frequency, power or silicon-readiness claim.

## Run locally

Requires Python 3.10+, Icarus Verilog 12 and Yosys with ABC. No paid services,
proprietary IP or model API is required. On a compatible Debian 13 host:

```bash
./scripts/install_tools.sh "$PWD/.tools"
source .tools/env.sh
python -m unittest discover -s tests -v
python -m chip_rl dot --artifacts /tmp/dot-private
PYTHONPATH=. python examples/rollout.py --task elastic
python -m chip_rl.suite --output /tmp/pilot-private --cache /tmp/pilot-cache
PYTHONPATH=. python scripts/replay.py /tmp/pilot-private/dot/serial1/case-0-0/candidate --output /tmp/replay
```

Tool installation is local, version-pinned, and requires Debian mirror access and
compatible shared libraries. `CHIP_RL_TOOLS` overrides the fallback tool prefix.
Artifacts and caches belong to the trusted host; use new artifact output paths.
Full qualification includes mapped 256-word memories and can take many minutes.
A `bad_* PASS` means rejection, never acceptance.

```python
from chip_rl import ChipEnv
from chip_rl.tasks import Config
from chip_rl.architectures import architecture

env = ChipEnv('dot', horizon=1)
observation, info = env.reset(seed=17)
observation, reward, terminated, truncated, info = env.step(
    {'rtl': architecture(Config('dot'), 'serial1')})
```

`reset(seed=...)` identifies an agent-side search only; it never selects evaluation
seeds. Every action receives fresh private 128-bit randomness. The trusted-host CLI
alone offers `--replay-seed` for reproduction. The JSON-lines server
(`python -m chip_rl.server`) accepts only reset(task, seed) and step({rtl: source}).
Candidate actions cannot change constraints, baseline, seeds, artifact locations,
commands or files. The Python API is trusted host code, **not an isolation boundary**.

Each candidate is simulated against an independent integer model, synthesized with
Yosys, then the mapped netlist is simulated on identical inputs. Unchanged source is
elaborated across every relevant supported WIDTH/DEPTH/K. Checks enforce registered
latency, storage capacity, in-order responses, stable stalls, completion, arbitration,
reset, arithmetic extremes, full cache tag-bit aliases, and resource budgets.
Missing tools, timeouts and unproven formal results never count as success.

Baselines are fixed independently of candidates. Paired offline release/consumer
schedules measure waiting before acceptance as well as execution time. The reward
is monotone in cell count, total completion cycles and useful offered-to-retired
latency, with explicit area-first weights. Serial alternatives may earn more while
being slower; read paired ratios rather than interpreting reward as throughput.
See [contracts](docs/contracts.md), [remediation evidence](docs/remediation.md),
[security boundary](docs/security.md), and [reference/license audit](docs/references.md).

## Limits

Tests are finite and publicly documented; private samples prevent simple fixed-ROM
replay but are not a proof against adaptive overfitting. Formal helpers provide
bounded evidence only when explicitly run. No family has an unbounded proof, and
no family has physical validation. The optional ORFS launcher remains unvalidated;
absent OpenROAD/PDK or unreviewed reports cannot produce verified physical results.

Compiler runs have wall/CPU/memory/file limits, isolated temporary working directories,
and source restrictions, but this executor cannot create a dedicated OS sandbox.
Do not give an untrusted agent filesystem/process access to evaluator code, caches,
private artifacts or host credentials. Production use needs an external container/VM
or separate account and source-only RPC. This limitation is returned in every result.
Memory currently maps to registers and muxes, not SRAM macros.
