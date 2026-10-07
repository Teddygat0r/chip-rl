# Self-contained delivery and private failure evidence

This public branch is a self-contained source snapshot of the verified twenty-family
checkpoint plus failure capture. Clone the branch directly; no unpublished base
commit or private artifact bundle is required. The private handoff also retains a
verified full-history bundle, but that history and its replay evidence are not
published here. Public runtime hashes are in `evidence/publication/scope.json`.

```sh
git clone --branch codex/verified-20-family-checkpoint https://github.com/Teddygat0r/chip-rl.git chip-rl
cd chip-rl
python3 -m venv .venv
.venv/bin/pip install .
bash scripts/install_tools.sh /absolute/private/tool-directory
source /absolute/private/tool-directory/env.sh
export PATH="$CHIP_RL_TOOLS/bin:$PATH"
.venv/bin/python -m unittest discover -s tests
```

The project has no third-party Python runtime dependencies. It requires Python
3.10+; the recorded runs use Python 3.12. HDL package versions are pinned in
`scripts/install_tools.sh` to Icarus12.0-2+b1, Yosys0.52-2 and
Yosys-ABC0.52-2 for Debian13 amd64. The actual package SHA256 values are retained
in the private delivery evidence. A complete old environment should retain those Debian
packages too; package archives may eventually stop serving a version. No PDK or
OpenROAD dependency is implied. Full v11 qualification commands are in
`evidence/v11/commands.txt`.

V12 adds an automatic host-only evaluation journal to each public evaluator.
Set `CHIP_RL_TRACE_ROOT` to a durable directory **outside the agent's accessible
filesystem**. If unset, traces use `/tmp/chip-rl-private-<uid>`; they survive an
evaluator process exit, but `/tmp` is not a reboot-persistence guarantee. The host
must manage disk capacity and retention; no automatic deletion policy is applied.
An unwritable journal fails the evaluation instead of silently discarding evidence.

Before qualification starts, the journal writes its seed, configuration, source
where supplied, Python/platform details and a `started` marker. Tool stdout/stderr
stream directly to retained files, including synthesis failures and timeouts.
Normal completion updates the status; an interrupted process can leave `started`
with its seed and tool logs intact. Explicit host artifact paths continue to work.
Neither paths, seeds nor logs are added to agent observations. File permissions
are not an OS sandbox; the training host must separate agent access itself.

The original v10 CRC reset anomaly remains unresolved. Its original seed and
private tool logs were not captured, so this change cannot retrospectively diagnose
it. V11 captured replays and the full CRC API matrix passed; those facts remain
separate from the unknown original cause.
