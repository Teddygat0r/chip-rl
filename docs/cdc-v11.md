# Two-clock FIFO: an experimental digital exercise

A FIFO holds items in arrival order. This task connects a producer and consumer
whose clocks run independently, as often happens between accelerator components.
The agent chooses a pointer architecture and two or three synchronization stages.
It does not design a whole accelerator, and this task does not certify a safe
physical clock-domain crossing (CDC).

The inventory is now **20 runnable families: six pilots and fourteen experimental**.
The new `cdc_fifo` is experimental and accepts constrained architecture parameters,
not arbitrary source edits. The older nineteen families retain their RTL actions
and unchanged single-clock validators.

## Run and learn

Install the repository with `python -m pip install .`, and install the open-source
HDL tools using the README instructions. Then:

```sh
python -m chip_rl.cdc --architecture binary_gray --sync-stages 2 --artifacts /tmp/cdc-baseline
python -m chip_rl.cdc --architecture gray_only --sync-stages 2 --artifacts /tmp/cdc-alternative
python examples/cdc_rollout.py
python -m chip_rl.cdc.server --artifacts-root /tmp/cdc-api-private
```

The JSON-lines server accepts a reset followed by architecture actions:

```json
{"op":"reset","task":"cdc_fifo","seed":17}
{"op":"step","action":{"architecture":"gray_only","sync_stages":3}}
```

`CDCEnv.reset()` and `step()` return the same observation/reward/termination shape
as the other environments. The observation includes generated, read-only RTL.
The episode seed does not control private qualification vectors. Host replay tools
retain the private seed and exact artifacts. Candidate actions cannot alter clocks,
width, depth, limits, evaluator code, tests, or synchronizer requirements. Running
untrusted agents still requires a separate OS sandbox: file permissions and this
parameter API are not such a sandbox.

## Contract and checks

The baseline stores local binary pointers and registered Gray pointers. The
alternative stores only Gray pointers and decodes them for memory addressing.
Gray encoding changes one bit on each local increment. Both synchronize the peer
pointer through an untapped two- or three-register chain. The structural checker
requires these protected roles and checks domain ownership, reset ownership,
positive-edge clocks and combinational paths. This is a constrained template
validator, not a general-purpose CDC sign-off tool.

Writes and reads use separate positive-edge event clocks. Transfers occur only
on the corresponding edge and ready/valid handshake. Simultaneous edges sample
both handshakes before either state update. Reset cancels queued work: both local
synchronous resets must be asserted long enough to clock each domain; release
may be skewed, but traffic resumes only after both releases. Independent unilateral
reset while the other domain continues traffic is outside this contract.

Independent queue scoreboards check data, ordering, capacity, completion, stalled
output stability, empty/full flags and Gray transitions. Tests include varied
clock ratios and phases, simultaneous edges, bounded clock pauses, repeated wraps,
full/empty transitions, backpressure and reset with one item or a full queue.
Default structural cases use widths/depths 16/4, 8/2, 32/8 and 8/16. An additional
held-out 4/2 target passed with the three-stage Gray-only design and a fresh cache.
Held-out clock
profiles differ from default profiles. Every accepted case must pass both Icarus
RTL simulation and Yosys mapped-netlist simulation with identical metrics.

Correctness and structural acceptance precede reward. Reward compares measured
generic cell counts, event-tick completion and accepted-write-to-read latency to
the fixed binary/Gray, two-stage baseline on identical workloads. Weights are
0.65/0.25/0.10; any case exceeding twice baseline ticks or latency gets zero.
Host limits are 4096 generic cells, 64 gate levels and 30000 ticks per epoch.
Ticks are abstract scheduling units, not MHz or routed timing. Extra synchronizer
stages are not awarded an invented MTBF benefit.

The bounded formal check uses the same RTL generator transformed into a global
clock with independent event enables, width 4/depth 2 and a 24-step bound. It checks
queue safety and Gray transitions after initial coordinated reset. It does not
prove liveness, unbounded behavior, arbitrary repeated reset, metastability, analog
MTBF, placement/skew constraints or physical CDC safety. In particular, the
one-stage synchronizer diagnostic can pass digital formal checks while failing
the structural policy. Missing tools, timeout and absent success remain unproven.
There is no OpenROAD/PDK run, routed timing, power or silicon-readiness claim.

## CRC failure investigation

The preserved v10 CRC API reset failure had no retained private seed or tool logs.
Its root cause remains unknown. V11 captures the environment and replays two fixed diagnostic seeds, with one repeated, using a fixed episode seed. All three
passed; the repeated seed has identical deterministic metrics. These observations
do not retrospectively explain the failure or establish general reliability.
The diagnostic runner and evidence preserve this limitation explicitly.

## Reproduce qualification

Run scripts with an installed package from outside the source tree:

```sh
python /path/to/repo/scripts/qualify_cdc.py --output /tmp/cdc-suite --cache /tmp/cdc-cache
python /path/to/repo/scripts/check_cdc_apis.py --output /tmp/cdc-apis --cache /tmp/cdc-cache
python /path/to/repo/scripts/reproduce_cdc_formal.py --output /tmp/cdc-formal
python /path/to/repo/scripts/replay_cdc.py --help
python -m unittest discover -s /path/to/repo/tests
```

The generated RTL is original. The architecture assessment consulted the
[OpenTitan asynchronous FIFO](https://github.com/lowRISC/opentitan/blob/master/hw/ip/prim/rtl/prim_fifo_async.sv)
and its [Apache-2.0 license](https://github.com/lowRISC/opentitan/blob/master/LICENSE),
without copying its source. Existing Yosys, Icarus and benchmark reference license
notes remain in the repository. See `evidence/v11/summary.json` for recorded final
counts and `evidence/v11/commands.txt` for exact commands and paths.

## Recorded FIFO measurements

Default target: width 16, depth 4. Ratios aggregate the four structural cases
against a paired baseline; each design uses its own captured private workload.

| Architecture | Stages | Target generic cells | Tick ratio | Latency ratio | Reward |
|---|---:|---:|---:|---:|---:|
| binary_gray | 2 | 169 | 1.0000 | 1.0000 | 1.00000000 |
| binary_gray | 3 | 175 | 1.1122 | 1.0889 | 0.97089211 |
| gray_only | 2 | 165 | 1.0000 | 1.0000 | 1.00591387 |
| gray_only | 3 | 170 | 1.1145 | 1.0908 | 0.97678476 |

All eight default/held-out runs passed (32 configuration checks); twelve faulty
RTL variants were rejected. All twelve installed API checks passed; nine malformed
requests and two lowered host budgets were rejected. Four bounded formal models
passed, and the corrupted-data model produced a counterexample. These are digital
results only. The Gray-only area saving is small and not evidence of a better
physical implementation. No policy training was performed.

The restored full hardware suites accept 16 pilot and 13 cycle-controller designs
and reject 71 pilot and 28 controller mutants. The expansion API matrix accepts
78 checks and rejects 330 mutant checks across nine families. All 83 repository
unit tests pass. Pilot APIs accept 18 checks and reject 237 mutants; cycle APIs
accept 8 checks and reject 4 mutants. All final regression failure lists are empty.
Exact commands, captured metrics and retained development failures are in
`evidence/v11/`; full private FIFO/CRC diagnostic artifacts are listed in the
artifact manifest. The intermediate checkpoint files remain as historical evidence.
