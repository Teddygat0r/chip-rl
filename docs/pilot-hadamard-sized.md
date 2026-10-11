# Sized serial Hadamard reference pilot

`sized_serial_butterfly` retains the serial butterfly's arithmetic, ready/valid
protocol, and pipeline state progression while sizing `work` and `next_work` to
`16*N` bits. Pair, lane, and stage indexes use widths derived from `N`, with
one-bit minima. The `N=1` path bypasses the butterfly datapath. Output remains
256 bits, with inactive lanes zero-extended.

This pilot measured only the development/train configurations `N=1,2,4`.
Each row paired the frozen `serial_butterfly` and sized source on the same
deterministic workload. Both passed source RTL and mapped exact-vector checks,
source RTL and mapped protocol/workload simulation, reset/backpressure, and
long-stall probes. Full source and mapped simulation traces matched between
the two references at each tested `N`.

| N | Frozen generic cells | Sized generic cells | Frozen cycles | Sized cycles |
|---:|---:|---:|---:|---:|
| 1 | 26 | 26 | 213 | 213 |
| 2 | 4,668 | 365 | 312 | 312 |
| 4 | 4,717 | 1,379 | 666 | 666 |

These are Yosys generic cell counts and Icarus workload cycles, not routed
area, timing, power, or a reward score. `N=8,16` were held out and were not
run in this pilot. Source, netlist, workload, watchdog, and tool hashes plus
per-case probe outcomes are in `evidence/pilot-hadamard-sized/summary.json`.
Raw workloads, netlists, and logs were kept outside the repository.
