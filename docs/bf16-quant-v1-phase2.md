# BF16 block quantization v1: Phase 2 evidence

The [family contract](../chip_rl/bf16_quant/contracts.md) defines exact BF16-to-INT8 block quantization with a custom NaN/Inf policy. The environment accepts complete synthesizable RTL source through a JSONL reset/step API. This report records fixed-reference local proxy evaluation; no trained agent was run.

## Verification setup

- Yosys 0.52 generic ABC cells; Icarus Verilog 12 source and mapped simulation
- Supported and scored N: 1, 2, 4, 8, 16
- Private development and heldout replay seeds were predeclared before scoring; only their SHA-256 digests are published
- Serial source SHA-256: 938202845b88fd0c1677e72ade2839b9fee1e6e02812ba80c4e537b836b9fff8
- Chunked-four source SHA-256: edbc44027e1d0a13b800938a50ce64a9eb8ccdbb06af60409ea95bd27aa82a9e
- Development seed SHA-256: 37bc2b623f3708f32f46ff48b8b67ee7e3c864ed799ac9fcadf94509dbefcf6f
- Heldout seed SHA-256: 17a3d9e7c089d6f5732e37a8c6f113d6295610cc067e8122e026817be0ef3764
- Frozen recipe manifest SHA-256: a95a54d90234200cf93409da0a45126d1612cb9b2bfe01c81c7e2d43569bda83

An independent host check compared exact integer arithmetic against BF16-as-binary32 unpacking, math.ldexp, and Python ties-even round. It checked all 65,536 BF16 patterns, all 32 scale exponents, and z in {-128, 0, 127}: **6,291,456 comparisons, zero mismatches**. This is host-oracle coverage, not exhaustive RTL verification.

## Fixed scoring results

Each of the four calls passed exact source/mapped replay, a 257-cycle blocked output, and reset while output was blocked. All five N gates passed in both splits: cells ≤4× serial, workload cycles ≤serial, and stream II ≤N+6. Reward was zero for both references on both splits. Serial is the baseline; chunked-four was correct and qualified but its geometric mean area×cycle product exceeded one. No gates or candidates were tuned after observing scored results.

| Split | Reference | N | Cells | Workload cycles | Stream II | Area ratio | Cycle ratio |
|---|---|---:|---:|---:|---:|---:|---:|
| development | serial | 1 | 3065 | 2908 | 3 | 1.000 | 1.000 |
| development | serial | 2 | 3066 | 3172 | 4 | 1.000 | 1.000 |
| development | serial | 4 | 3064 | 3174 | 6 | 1.000 | 1.000 |
| development | serial | 8 | 3062 | 4756 | 10 | 1.000 | 1.000 |
| development | serial | 16 | 3059 | 7498 | 18 | 1.000 | 1.000 |
| development | chunked4 | 1 | 10120 | 2908 | 3 | 3.302 | 1.000 |
| development | chunked4 | 2 | 10344 | 2116 | 3 | 3.374 | 0.667 |
| development | chunked4 | 4 | 10760 | 1764 | 3 | 3.512 | 0.556 |
| development | chunked4 | 8 | 10750 | 2380 | 4 | 3.511 | 0.500 |
| development | chunked4 | 16 | 10750 | 2700 | 6 | 3.514 | 0.360 |
| heldout | serial | 1 | 3065 | 3958 | 3 | 1.000 | 1.000 |
| heldout | serial | 2 | 3066 | 4194 | 4 | 1.000 | 1.000 |
| heldout | serial | 4 | 3064 | 3685 | 6 | 1.000 | 1.000 |
| heldout | serial | 8 | 3062 | 6038 | 10 | 1.000 | 1.000 |
| heldout | serial | 16 | 3059 | 8929 | 18 | 1.000 | 1.000 |
| heldout | chunked4 | 1 | 10120 | 3958 | 3 | 3.302 | 1.000 |
| heldout | chunked4 | 2 | 10344 | 2908 | 3 | 3.374 | 0.693 |
| heldout | chunked4 | 4 | 10760 | 2463 | 3 | 3.512 | 0.668 |
| heldout | chunked4 | 8 | 10750 | 3208 | 4 | 3.511 | 0.531 |
| heldout | chunked4 | 16 | 10750 | 3171 | 6 | 3.514 | 0.355 |

The three predeclared N=4 arithmetic negative controls (ties-away, clamp before adding z, NaN→0) each synthesized and compiled, then produced their expected wrong value at both source and mapped stages. The focused source unit test module passed all three tests. See [machine-readable evidence](../evidence/bf16-quant-v1/summary.json) for exact vectors, per-N metrics, tool and recipe hashes, and mutant witnesses.

## Main-tree integration checks

The full source suite passed 235/235 tests using Yosys 0.52 and Icarus 12. An isolated installed wheel imported the BF16 contract and frozen sources; direct reset/step and JSONL reset/step passed from qualified cache with zero fresh tool runs. The 266 pre-existing family and test source files compared byte-for-byte against the pre-integration snapshot were unchanged. Historical v34 evidence remains present. See [integration verification](../evidence/bf16-quant-v1/integration-verification.json).

## Limits

Generic-cell area and workload cycles are proxies. No exhaustive RTL proof, formal proof, routed PPA, BF16 ISA-conformance test, model-accuracy test, or trained-RL claim is made. The custom special-value policy is a task definition, not claimed hardware ISA behavior.
