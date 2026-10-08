# Self-contained delivery and private failure evidence

The final v12 delivery includes a full-history Git bundle, a standalone source
archive, an offline Python wheel, checksums, and the three pinned Debian HDL
packages. The full-history bundle is a **private host delivery**: it includes
historical evidence and must not be published or exposed as an agent workspace.
The independently approved public branch remains the twenty-family checkpoint.
The delivery manifest records the exact v12 commit and SHA256 of every artifact.

On a compatible Debian13 amd64 host with Python3.10+ and the recorded system
libraries, the wheel installs without network access or Python runtime dependencies:

```sh
python3 -m venv .venv
.venv/bin/pip install --no-index --no-deps wheels/chip_rl-0.12.0-py3-none-any.whl
mkdir -p tools
for f in debs/*.deb; do dpkg-deb -x "$f" tools; done
export CHIP_RL_TOOLS="$PWD/tools/usr"
export PATH="$CHIP_RL_TOOLS/bin:$PATH"
export CHIP_RL_TRACE_ROOT=/absolute/private/evaluation-journals
.venv/bin/python -m chip_rl.memory mshr --architecture shift
.venv/bin/python -m chip_rl.memory tlb --architecture dual
```

The host's Debian runtime libraries are not a hermetic container image. Exact
versions used are recorded in `evidence/v12/delivery/host-runtime-packages.txt`;
other operating systems and architectures have not been validated. HDL packages
retain their upstream copyright/license files inside the Debian archives. Build
tools used for the wheel were setuptools84.0.0 and wheel0.48.0; neither is required
to install the delivered wheel. The clean offline wheel install passed all91 unit
tests. Positive MSHR/TLB and negative TLB replays also passed using that install,
a second pinned HDL installation and an initially empty synthesis cache.

Current commands are in `evidence/v12/commands.txt`; measured evidence is in
`evidence/v12/summary.json`. The private replay archive contains seeds, generated
workloads, candidate RTL and tool diagnostics, separately from public summaries.
Some completed-run logs are gzip-compressed; dangling original log symlinks can
point to their compressed replacement. Replay reads source, result and seed files,
then regenerates and checks the metrics and private workload hashes.

## Previous self-contained checkpoint

`/workspace/chip-rl-v11-full.bundle` contains the complete Git history through
218a816d8571d3739d264044991f818a129638f5. It has no prerequisite commit.
It was cloned into an empty directory, checked out at that revision, and checked
with `git fsck --full`. The original incremental bundle remains available; it is
no longer the only history delivery. The standalone source archive also remains
available. Checksums and verification are under `evidence/v12/delivery/`.

```sh
git clone chip-rl-v11-full.bundle chip-rl
cd chip-rl
git checkout 218a816d8571d3739d264044991f818a129638f5
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
in the delivery evidence. A complete old environment should retain those Debian
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

The final host process probe also kills an evaluator after its subprocess starts
streaming output. The journal remains `started` with the original source, config,
seed and partial log. A separate forced tool timeout raises rejection and retains
its evidence. These checks are reproducible with `scripts/check_journal_crash.py`;
they do not establish filesystem isolation or HDL correctness. A deployment
supervisor must clean up orphan tool processes if it kills the evaluator itself.
