# Integer RMS exact-integer family: Phase 1

Status: source, contract, oracle, workloads, reference RTL, JSONL environment, synthesis, RTL/mapped arithmetic and protocol checks, conditional proxy scoring, focused unit tests, and N=1/N=4 reference smoke are implemented. No full five-N scored comparison has been run. The family is an exact integer normalization benchmark, not floating-point RMSNorm.

Frozen reference-source SHA256 (hash of complete generated Verilog):

- serial: `0a7241139699cbd77852761dc6969fade0ccaf1a71b9baef09590b5f581cb7a3`
- chunked4: `6058b594e112a61539694a2b15afd05713d21fd0f4d0f77c1ac5b12eb67a823e`

A unit test checks both hashes and source screening. The serial FSM takes one accept edge, N accumulation cycles, one M-preparation cycle, sixteen restoring-root cycles, N normalization cycles and one response/consume cycle. Its saturated input acceptance interval is 2*N+19 cycles as measured in the N=1 and N=4 smoke; the fixed qualification gate is 2*N+24. Chunked4 changes only the normalization width and masks final partial groups.

Phase 1 evidence, using the local matching Yosys/Icarus tools, is retained in `../integer-rms-phase1-final-evidence/` (per-architecture, per-N summaries and source/mapped logs). These are 32-request protocol smokes and directed arithmetic probes, not a scored five-N sweep:

| Reference | N | Directed probes | Generic cells | 32-request workload cycles | Saturated acceptance II | RTL/mapped and stall/reset |
|---|---:|---:|---:|---:|---:|---|
| serial | 1 | 40 | 8156 | 697 | 21 | pass |
| serial | 4 | 67 | 8193 | 878 | 27 | pass |
| chunked4 | 1 | 40 | 6874 | 697 | 21 | pass |
| chunked4 | 4 | 67 | 19088 | 791 | 24 | pass |

The 257-cycle blocked-output stall, reset while output was visibly blocked, recovery, order, and source/mapped arithmetic checks passed in each smoke. Logic depth and cells are generic synthesis proxies only. New evidence and cache artifacts use about 105 MB, with over 29 GB free, within the 2 GB artifact cap and 5 GB free-space floor.

Host-generated directed witnesses include all zero, signed extrema, single nonzero in every active position, ignored fields, mixed signs, equal-magnitude blocks, floor division (N>=2), exact/above/below-square radicands where reachable, and positive/negative half ties with even and odd quotient (N>=2). N=1 has no half-tie witness in the directed set and cannot have a nonzero S%N or a radicand immediately below a larger square with a one-lane input; these classes are not claimed. INT16 output clipping has no reachable witness under valid inputs and is not claimed exercised. Host-only unit negative controls show epsilon omission, narrow absolute value, and truncation disagree with the production oracle; RTL mutation-detection coverage has not been measured.

Next stage requires source/contract review before starting the five-N scored evaluations. The fixed gates are per N: area ratio <=4, completion cycles <=serial, and saturated acceptance II <=2*N+24. Correct-but-unqualified results remain separate from correctness failures.
