# Block FOR v1: Phase 1

Status: experimental exact unsigned-byte frame-of-reference environment implemented in an isolated source snapshot. This is an unscored phase-1 smoke, not a five-N qualification. Reference RTL was frozen before hardware simulation. No gate was tuned after observing results.

## Fixed source hashes

- serial: `6e070e3d9868b0f7139950359ca9ca6ecf0a79cea22755c7226ee988828dc2f6`
- chunked4: `2303f60c81ed9dbdea4157612dcbe1f07409b3b1ed8be63e5b0e3559a8622dff`

The FSM scans N bytes serially to find min and max, prepares the base and exact bit width, then packs one or up to four offsets per cycle. The expected saturated acceptance II is `2*N+3` for serial and `N+ceil(N/4)+3` for chunked4. Both fit the fixed `2*N+6` gate. References hold output stable under backpressure and clear block state on reset.

The Python oracle independently computes min, max, bit length, and packed output. Its separate decoder checks width, offset overflow, unused bits, canonical range, and exact byte roundtrip. Directed work covers constants, unsigned edges, every reachable width (only width zero at N=1), ranges just below/at/above powers of two, min/max at every lane, alternating endpoints, leading/trailing zero offsets, ignored input bits, sharply changing consecutive blocks, and seeded full/narrow random values. The phase-1 tests assert the claimed endpoint and range-span coverage. Per-request timeout is `6*N+80` ready-high opportunities, with a whole-run bound of `requests*(6*N+80)+1` opportunities after last release. Consumer stalls do not age work.

Focused Python tests: `PYTHONPATH=chip-rl-for-work python -m unittest discover -s chip-rl-for-work/tests -p test_block_for.py` passed (4 tests). Source and Yosys-mapped checks used local Yosys 0.52 and Icarus 12, including exact directed probes, ordered/no-loss mixed traffic, a 257-cycle output stall, reset with output observed blocked, and fresh-block recovery.

| Reference | N | Exact probes | Generic cells | Workload cycles | Saturated II | Stall/reset |
|---|---:|---:|---:|---:|---:|---|
| serial | 1 | 117 | 2605 | 647 | 5 | pass |
| serial | 4 | 182 | 2602 | 2006 | 11 | pass |
| serial | 16 | 218 | 2598 | 7794 | 35 | pass |
| chunked4 | 1 | 117 | 3440 | 647 | 5 | pass |
| chunked4 | 4 | 182 | 7965 | 1995 | 8 | pass |
| chunked4 | 16 | 218 | 7955 | 5098 | 23 | pass |

The fixed all-five-N score requires each N in `{1,2,4,8,16}` exactly once, with verified source and mapped replay against serial. At every N, area must be at most 4x serial, workload cycles at most serial, and saturated II at most `2*N+6`. A correct gate failure is unqualified with zero reward. Qualified reward is `max(0,1-exp(mean(log(area_ratio*cycle_ratio))/2))`. Costs are generic-cell and completion-cycle proxies only; there is no routed timing, physical PPA, model quality, or trained-RL claim. Numerical mutation sweeps and the full scored sweep are deferred until review.
