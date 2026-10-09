# Block RLE v1: Phase 2 qualification

The new experimental block-RLE family was evaluated in an isolated local snapshot, without modifying the original source tree or publishing it. Reference RTL and evaluator/contract file hashes were frozen before scored runs in `phase2-freeze.json`. A fresh 128-bit host replay seed was predeclared for each of development and heldout, kept separately in a private mode-0600 file. Each split used the same seed and workload schedule for both candidate references. The public evaluator ran serial and chunked4 once each per split over N={1,2,4,8,16}. Both references were correct in source and mapped exact and protocol checks, qualified under every fixed gate, and earned zero balanced proxy reward. No tuning was made after measuring.

| Split | RTL | N=1 area/cycles/II | N=2 | N=4 | N=8 | N=16 | Mean log(area×cycles) | Reward |
|---|---|---|---|---|---|---|---:|---:|
| Development | serial | 1.000 / 1.000 / 3 | 1.000 / 1.000 / 4 | 1.000 / 1.000 / 6 | 1.000 / 1.000 / 10 | 1.000 / 1.000 / 18 | 0.000 | 0.000 |
| Development | chunked4 | 3.613 / 1.000 / 3 | 3.612 / 0.672 / 3 | 3.612 / 0.555 / 3 | 3.613 / 0.496 / 4 | 3.612 / 0.360 / 6 | 0.743 | 0.000 |
| Heldout | serial | 1.000 / 1.000 / 3 | 1.000 / 1.000 / 4 | 1.000 / 1.000 / 6 | 1.000 / 1.000 / 10 | 1.000 / 1.000 / 18 | 0.000 | 0.000 |
| Heldout | chunked4 | 3.613 / 1.000 / 3 | 3.612 / 0.711 / 3 | 3.612 / 0.681 / 3 | 3.613 / 0.531 / 4 | 3.612 / 0.357 / 6 | 0.807 | 0.000 |

Area and cycles are ratios against the serial reference. Every area ratio is <=4, cycle ratio <=1, and saturated acceptance II <=N+6. All five N values were required exactly once by the top-level scoring function. Serial's zero reward follows from its unit ratios. Chunked4's zero reward follows from positive mean log(area×cycles), despite faster cycles at most widths. The fixed formula clamps its negative raw reward to zero.

Three copied-source N=4 numerical/format negative controls were defined and frozen before execution: off-by-one run length on [65,65,66,67], merging nonadjacent 65 on [65,66,65,67], and a nonzero unused output bit on [0,0,255,0]. All three synthesized and compiled, then failed exact output comparison at both source RTL and mapped netlist levels. This is mutation detection evidence only, not a broad security audit.

The public results are in the four split-and-RTL JSON summaries. Detailed build and simulation records and replay seeds remain private. These measurements are generic area/cycle proxies; formal verification, physical PPA, model-quality work, and learned-agent gains are not claimed.

The repository unit discovery run with the confirmed local Yosys/Icarus prefix executed 228 tests: 227 passed and one unrelated historical sparse24 manifest test errored because this deliberately source-only snapshot excluded `evidence/v34/summary.json`. The new block-RLE focused tests passed separately (4 tests). A wheel built successfully, and importing the packaged family plus running `BlockRleEnv.reset`/`step` and a JSONL server validation probe passed.
