# Validation results

Final qualification: **10/10 families; 40 valid cases pass; 30/30 bad RTL cases rejected.**

All valid cases passed Icarus RTL simulation, Yosys/ABC synthesis and Icarus mapped-netlist replay. Twenty-three unit tests passed. A real three-action elastic agent rollout completed with rewards 1.0000, 1.2339 and 1.3478.

| Task | Baseline cells | Alternate cells | Baseline useful latency | Alternate useful latency | Alternate reward |
|---|---:|---:|---:|---:|---:|
| elastic | 81 | 41 | 6.258 | 3.305 | 1.2308 |
| dot | 2183 | 2139 | 6.258 | 3.305 | 1.1164 |
| scratchpad | 104543 | 104024 | 6.095 | 3.262 | 1.1115 |
| dma | 789 | 735 | 7.143 | 3.667 | 1.1303 |
| router | 12805 | 12274 | 6.194 | 3.249 | 1.1217 |
| scoreboard | 4698 | 4178 | 6.304 | 3.336 | 1.1354 |
| tensor | 8678 | 8526 | 6.258 | 3.305 | 1.1159 |
| accelerator | 35998 | 35926 | 6.000 | 2.662 | 1.1311 |
| cache | 31576 | 31468 | 6.510 | 3.020 | 1.1290 |
| gather | 44538 | 44028 | 6.179 | 3.033 | 1.1211 |

Cells are generic mapped logic counts, **not physical area**. Latency is weighted useful command-response latency in cycles; no clock frequency or power was measured.

| Evidence category | Families | Scope |
|---|---:|---|
| Functional simulation | 10/10 | Baseline, alternate, heldout seed, structural variant |
| Synthesis + mapped-netlist replay | 10/10 | Same 40 valid cases |
| Bounded formal | 1/10 | Elastic width8, 12 cycles; baseline and alternate pass, corrupted mutant does not |
| Unbounded formal | 0/10 | Not run |
| Routed physical | 0/10 | OpenROAD/ORFS/PDK absent |

Exact commands executed:

```bash
python -m unittest discover -s tests -v
python -m chip_rl.suite --output artifacts/release
python -m chip_rl.suite --tasks cache --output artifacts/cache-requalification
PYTHONPATH=. python examples/rollout.py
PYTHONPATH=. python scripts/replay.py artifacts/release/dot/alternate --output /tmp/chip-dot-replay
python -m chip_rl.physical elastic --flow-root /workspace/no-orfs-installed --output /tmp/chip-physical-missing
```

The first full qualification exited 1: one cache write-update mutant survived. This exposed a missing readback test. A directed prefix now observes hit writes before eviction and checks no-write-allocation. All seven cache cases were rerun and passed, and their artifacts replaced the initial cache cases. The initial summary and logs remain in `artifacts/release/initial-summary.json` and `initial-run.log`; the requalification log and final `summary.json` record the correction. Other families were unaffected. This is a targeted requalification, not a claim that the initial full command exited successfully.

The missing-physical-flow command correctly exited 1 with `not_run`, `physical_verified=false`, and no metrics. It is a tested unavailable-stage path, not a completed physical run. The ORFS adapter is unvalidated with a real installation.

Unit tests additionally check missing tools, timeouts, unsafe HDL, hard area budget, interface changes, action constraints, observation-copy integrity, mismatched baseline workloads, cache regression, unfair scoreboarding, and fixed-cycle versus latency-flexible proof behavior. Fixed-cycle miter artifacts show identical designs pass and retimed designs do not, while the retimed transaction proof passes.

See `artifacts/release/summary.json`, per-case source/vector/tool artifacts, `artifacts/unit-tests.txt`, and `artifacts/toolchain.json` for replayable evidence.
