# V21 masked fixed-point softmax

This checkpoint adds one experimental numerical approximation task, bringing the suite to **24 runnable families: six pilots and eighteen experimental families**. The existing v18 K16 proof and v20 layout audit are preserved. This is a small row-normalization circuit, not a GPU softmax implementation or evidence of silicon readiness.

The [prospective plan](softmax-v21-plan.md) fixed the numerical contract and compute budget before candidate evaluation. Inputs are up to sixteen signed INT8 Q4 logits with a lane mask. Outputs are sixteen unsigned probability slots scaled by 4096. Inactive and unused slots, including all-masked rows, must be zero. The [full contract](../chip_rl/softmax/contracts.md) specifies rounding tolerance, shift invariance, ordering, normalization, ready/valid behavior and resource limits. The reference computes absolute exponentials with 80-digit Decimal arithmetic and normalizes them independently of candidate lookup tables. Unit tests cross-check that calculation at 120-digit precision.

Four generated synthesizable candidates separate approximation choice from division schedule: `full_serial`, `linear_serial`, `full_radix4`, and `linear_radix4`. The full lookup has 256 exponential values; interpolation uses 64 quarter-step intervals. Serial division advances one quotient bit per cycle; radix-four advances two. The fixed baseline is `full_serial`. The evaluator checks both candidate and baseline under identical private workloads, then scores measured generic cell count, mapped logic depth and workload cycles. Accuracy remains a hard gate and is reported separately.

Qualification covers development N=4,8; heldout N=3,7,16; and reserve N=5,12. These same-author structural splits are disjoint but are not an independent study. Directed workloads include signed extremes, equal and dominant logits, near ties, every dominant/single-active position, masks, common shifts and random rows. Protocol tests poison invalid input cycles, stall outputs, cancel immediately accepted work, cancel during maximum scanning and normalization, cancel completed stalled work, and drain for duplicate responses. RTL and mapped simulation must agree exactly on output bits and scored cycles. Errors, missing tools and timeouts cannot earn correctness credit.

The API accepts only candidate RTL; it cannot change N, ports, oracle, errors, resource caps, hidden workload seed or artifact destination. Candidate code is copied into private evaluation directories and passed through the existing source restrictions and bounded subprocess runner. These controls are not an operating-system sandbox: do not grant an untrusted agent write access to evaluator code or private artifacts. Seeded replay is a trusted-host capability, not an action exposed to the agent.

## Reproduction

Use Python 3.10 or newer, Icarus Verilog and Yosys/ABC. The recorded local runs used Python 3.12, Icarus 12 and Yosys 0.52. Existing tools were reused; no services or new installations were required. `CHIP_RL_TOOLS` may point to a locally extracted `usr` directory. Run from outside the checkout when testing an installed wheel, so imports resolve to that wheel.

```bash
python -m pip wheel --no-deps --no-build-isolation . -w /tmp/wheels
python -m venv /tmp/softmax-venv
/tmp/softmax-venv/bin/pip install --no-index /tmp/wheels/chip_rl-0.21.0-py3-none-any.whl
python -m unittest discover -s tests
repo="$PWD"
cd /tmp
/tmp/softmax-venv/bin/python -m unittest discover -s "$repo/tests"
# Run each output command with a new, nonexistent directory.
/tmp/softmax-venv/bin/python "$repo/scripts/qualify_softmax.py" --output /tmp/softmax-matrix --cache /tmp/softmax-cache
/tmp/softmax-venv/bin/python "$repo/scripts/check_softmax_api_v21.py" --output /tmp/softmax-api --cache /tmp/softmax-cache
/tmp/softmax-venv/bin/python "$repo/examples/softmax_rollout.py" --cache /tmp/softmax-cache
/tmp/softmax-venv/bin/python "$repo/scripts/replay_softmax.py" /tmp/softmax-matrix/heldout-full_radix4 --output /tmp/softmax-replay --cache /tmp/softmax-cache
/tmp/softmax-venv/bin/python "$repo/scripts/check_quality_aggregate.py" --output /tmp/legacy-aggregate --cache /tmp/legacy-cache
/tmp/softmax-venv/bin/python "$repo/scripts/check_layout_api_v20.py" --output /tmp/layout-aggregate --cache /tmp/layout-cache
/tmp/softmax-venv/bin/python -m chip_rl.softmax.server --cache /tmp/softmax-cache
```

A server episode begins with `{"op":"reset","task":"softmax","seed":21}` and accepts `{"op":"step","action":{"rtl":"..."}}`. Reset evaluates the fixed baseline; each step returns the observation, reward and horizon status. The episode seed does not choose the private qualification seed. Private journals retain the actual seed, source, command logs, testbenches, inputs, mapped netlists and results for exact replay.

## Recorded final results

All 172 source and 172 installed unit tests pass. The final matrix accepts 12 design/split evaluations across 28 shape cases and rejects 12 bad designs. The installed API accepts its baseline, rejects its bad candidate and rejects 16 invalid requests. The four-evaluation example completes and two exact replays reproduce metrics, numerical errors, recipe and tools. In total, the final softmax campaign has 19 correct evaluations and 13 rejected bad evaluations. The existing 22-family aggregate and layout baseline also pass, retaining functional and synthesis evidence for all 24 families. No new formal proof or physical validation is claimed.

Ratios below are geometric means relative to the fixed baseline on each split. Maximum absolute error is in probability units; its fixed limit is 0.00390625.

| Split | Design | Cells ratio | Logic-depth ratio | Cycles ratio | Max absolute error | Reward |
|---|---|---:|---:|---:|---:|---:|
| development | full_serial | 1.0000 | 1.0000 | 1.0000 | 0.0002437 | 1.00000 |
| development | linear_serial | 1.0848 | 1.8891 | 1.0000 | 0.0020823 | 0.91682 |
| development | full_radix4 | 1.1103 | 1.2383 | 0.5773 | 0.0002437 | 1.03483 |
| development | linear_radix4 | 1.1977 | 1.8891 | 0.5773 | 0.0020823 | 0.97372 |
| heldout | full_serial | 1.0000 | 1.0000 | 1.0000 | 0.0002443 | 1.00000 |
| heldout | linear_serial | 1.0822 | 1.8844 | 1.0000 | 0.0019168 | 0.91765 |
| heldout | full_radix4 | 1.1067 | 1.2317 | 0.5679 | 0.0002443 | 1.03860 |
| heldout | linear_radix4 | 1.1915 | 1.8844 | 0.5679 | 0.0019168 | 0.97771 |
| reserve | full_serial | 1.0000 | 1.0000 | 1.0000 | 0.0002457 | 1.00000 |
| reserve | linear_serial | 1.0816 | 1.8750 | 1.0000 | 0.0019416 | 0.91827 |
| reserve | full_radix4 | 1.1066 | 1.2188 | 0.5693 | 0.0002457 | 1.03931 |
| reserve | linear_radix4 | 1.1906 | 1.8750 | 0.5693 | 0.0019416 | 0.97804 |

The fine lookup with radix-four division is a useful measured tradeoff: workload cycles fall to about 57–58% of baseline at roughly 11% more cells and 22–24% more logic depth. Its numerical error is unchanged and reward improves by 3.5–3.9%. These are workload-cycle improvements, not measured clock-speed or GPU-speed improvements. Interpolation is a negative result here: it increases mapped cells and depth and worsens error by roughly eightfold. Both interpolated designs lose reward against the fixed baseline despite meeting the fixed numerical limits. No tolerance or reward weight was relaxed after observing results.

Bad designs cover uniform approximations, mask omission, unsigned logits, denominator overflow, coarse exponential steps, disappearing stalled responses, live-input dependence, wrong probability scaling, nonterminating division, reversed lanes, absolute-logit underflow, and broken reset. The precise private failure logs are retained. A malformed or timed-out candidate always earns zero; synthesis alone never certifies numerical correctness.

The complete new-task work consumed 59 evaluator calls, 46 synthesis invocations and 289 HDL simulation invocations, including preliminary attempts and rejected candidates, within the predeclared 60/120/400 caps. The aggregate was separately bounded at 43 existing-family evaluator calls and two layout calls. The first matrix and completed legacy aggregate were compressed, hash-verified and retained before raw duplicates were removed to stay within disk limits. See machine-readable summary (private evaluation artifact retained locally), per-case metrics (private evaluation artifact retained locally), and aggregate evidence (private evaluation artifact retained locally).

## Scope and limitations

Finite workload checks are not proofs over every input or architecture. No new formal campaign or physical validation was performed. Generic cells, combinational logic levels and architectural cycles are proxies, not routed area, clock frequency, power or total GPU throughput. OpenROAD/STA and a PDK/platform are absent. The inherited v18 proof applies only to its documented exact K16 configuration, not this softmax task. There was no agent training, independent author or external evaluation. Existing third-party tool license notes remain applicable; no external implementation code or proprietary IP was copied for softmax. No push or publication was performed.

Review added a divider-phase reset probe after the first full matrix. The entire softmax matrix, API, example and replays were rerun from the final installed wheel. A targeted reset mutant also failed the older checker at initialization; that attempt is preserved, but is not evidence of an old false acceptance or an isolated test of the new probe. The earlier matrix is retained as preliminary evidence, not counted as final qualification. All 124 inherited runtime files remain byte-identical, so their aggregate runs apply to the final source without another expensive repeat.
