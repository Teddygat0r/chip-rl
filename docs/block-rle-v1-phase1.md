# Block RLE v1: Phase 1

Status: New experimental exact block run-length environment implemented in an isolated source snapshot. No five-N scored evaluation has been run. The reference candidates' generated RTL was frozen before hardware evaluation.

## Frozen generated Verilog SHA256

- serial: `5768a73b8ad3e0b8cab1592f0227f94765cfde3ef55828eeca2049f63f3e87b9`
- chunked4: `35e4ff8f63b14f5679f4ddee44ca67a1f2865c571ef0f59ff3a3f56c25c75366`

Both candidates use IDLE, SCAN and RESPONSE states. An accepted block waits for ceil(N/stride) scan edges (stride 1 or 4), then one registered response edge and return to IDLE after consumption. Thus saturated acceptance II is N+2 for serial and ceil(N/4)+2 for chunked4. These expectations match N=1,4,16 smoke and meet the fixed N+6 gate. No FSM/gate contradiction was found.

## Focused evidence

The focused Python tests cover independent list-of-runs packing and decoding, directed and seeded roundtrip, ignored-bit metamorphic invariance, run-length sum, malformed output decoding, frozen source hashes, source screening, exact scoring-set cardinality and gate failure. `python -m unittest tests.test_block_rle -v` passed (4 tests).

Source RTL and mapped netlists passed exact directed and mixed protocol checks at N=1,4,16 on the local Yosys 0.52/Icarus 12 installation. These are phase-1 smokes, not a full scored five-N evaluation.

| RTL | N | Exact directed probes | Generic cells | Workload completion cycles | Saturated acceptance II | Blocked output / reset |
|---|---:|---:|---:|---:|---:|---|
| serial | 1 | 26 | 4080 | 271 | 3 | pass |
| chunked4 | 1 | 26 | 14741 | 271 | 3 | pass |
| serial | 4 | 32 | 4077 | 528 | 6 | pass |
| chunked4 | 4 | 32 | 14728 | 293 | 3 | pass |
| serial | 16 | 60 | 4073 | 1980 | 18 | pass |
| chunked4 | 16 | 60 | 14712 | 714 | 6 | pass |

The protocol check includes a 257-cycle blocked output with observed valid and stable data, reset while output is visibly blocked, fresh-block recovery, and ordered no-drop/no-duplicate completion. Each transaction has a 4*N+64 ready-high service-opportunity bound. The generated workload limit has request_count*(4*N+64)+1 ready-high opportunities after final release. Completion cycles and generic cell counts are proxies. Formal verification, physical PPA and model-quality evaluation were not run.

The fixed scoring definition requires all five N cases exactly once, including serial baseline verification, generic cell ratio <=4, workload completion cycles <=serial, saturated II <=N+6, and balanced reward max(0,1-exp(mean(log(area_ratio*cycle_ratio))/2)) only when every gate passes. Correct-but-unqualified remains distinct from incorrect.

Later work: review/integrate source, then run complete scored N={1,2,4,8,16} comparison. The proposed numerical negative controls for off-by-one run length, merging nonadjacent repeats and nonzero unused output are not part of Phase 1.
