# Minimal local evaluation walkthrough

This uses the existing elastic baseline and `global4` alternative. It is a deterministic trusted-host evaluation, not trained RL. Run from the repository root with Python 3.10+ and existing Icarus/Yosys/ABC tools. No network or paid service is needed for these commands; the build interpreter must already have pip, setuptools and wheel. Choose a fresh `work` directory on every run.

```bash
repo="$PWD"
work=/tmp/chip-rl-doc-walkthrough
mkdir "$work"
python -m pip wheel --no-deps --no-build-isolation "$repo" -w "$work/wheels"
python -m venv "$work/venv"
"$work/venv/bin/pip" install --no-index "$work"/wheels/chip_rl-*.whl
# Existing extracted tool location on the verified executor; adjust for your host.
export CHIP_RL_TOOLS=/workspace/tools/root/usr
export PATH="$CHIP_RL_TOOLS/bin:$PATH"
export CHIP_RL_TRACE_ROOT="$work/private-traces"
cd "$work"
"$work/venv/bin/python" -m chip_rl elastic --emit > baseline.sv
"$work/venv/bin/python" - <<'PYCODE'
from pathlib import Path
from chip_rl.tasks import Config
from chip_rl.architectures import architecture
Path('alternate.sv').write_text(architecture(Config('elastic'), 'global4'))
PYCODE
"$work/venv/bin/python" -m chip_rl elastic --rtl baseline.sv --replay-seed 4242 --cache "$work/cache" --artifacts "$work/baseline" > baseline.json
"$work/venv/bin/python" -m chip_rl elastic --rtl alternate.sv --replay-seed 4242 --cache "$work/cache" --artifacts "$work/alternate" > alternate.json
"$work/venv/bin/python" - <<'PYCODE'
import json
for name in ('baseline', 'alternate'):
    result = json.load(open(name + '.json'))
    assert result['tested_correct']
    assert result['objective_eligible']
    if name == 'baseline':
        assert result['reward'] == 1
    print(name, result['reward'], result['metrics'])
PYCODE
```

These two CLI evaluations exercise installed-package source checking, RTL simulation, Yosys/ABC synthesis, mapped replay, mandatory structural/workload checks and paired scoring. A nonzero CLI exit signals functional qualification failure; **always inspect eligibility separately**, because correct but ineligible candidates can exit successfully with zero reward. Do not treat a successful tool exit alone as correctness.

`baseline.json` and `alternate.json` contain the results. Their artifact directories contain the exact source, private journal, workloads and logs for diagnosis/replay; keep the whole directory and its cache dependencies where present. The fixed replay seed is a host-only control; the [agent episode example](../examples/rollout.py) uses `reset`/`step` and private fresh evaluation seeds instead. The documentation walkthrough runs two evaluations, not the full 24-family suite, formal campaign or physical flow.

The absolute tool path is executor-specific. See [tool installer](../scripts/install_tools.sh) and [reproduction notes](reproduction-v12.md) for other hosts; downloads are a separate setup operation, not a silently skipped prerequisite. File modes and this source-only API do not isolate a shell-capable agent sharing the host UID. See [reading guide](README.md) for evidence boundaries.

## Recorded v23 clean-install check

The command block was executed verbatim from a clean clone, with a newly built wheel, fresh virtual environment and empty synthesis cache. Both evaluations passed and were eligible. Baseline: 81 generic cells, depth 5, 1550 mean completion cycles, reward 1.0. `global4`: 76 cells, depth 2, 1550 cycles, reward 1.0138724233888021; offered latency was slightly worse (43.2339 versus 43.0955 cycles), illustrating why the scalar alone is insufficient. All 138 installed wheel runtime files matched v23 source. See verification record (private evaluation artifact retained locally), exact commands (private evaluation artifact retained locally), and execution log (private evaluation artifact retained locally). These measurements belong to this seed and contract, not every workload.
