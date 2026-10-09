# Signed INT8 Hadamard transform v1: Phase 2 evidence

The [family contract](../chip_rl/hadamard_int8/contracts.md) defines an exact unnormalized Sylvester Hadamard transform from N signed INT8 input lanes to N signed INT16 output lanes for N={1,2,4,8,16}. The environment accepts complete synthesizable RTL through a reset/step JSONL API. This report records fixed-reference proxy evaluation; no trained agent was run.

## Frozen setup

- Yosys 0.52 generic ABC cells and Icarus Verilog 12 source/mapped simulation
- The direct parity-matrix sum is the primary oracle. Independent iterative butterflies agreed on every generated directed/random block in both splits, plus 1,000 additional full-range random blocks per N. This is finite host verification, not exhaustive RTL proof.
- The serial reference uses one signed16 sum/sub butterfly pair per work cycle. The stage-parallel reference uses N/2 pairs per stage cycle, reading pre-stage workspace. N=1 bypasses WORK.
- Two fresh private 128-bit replay seeds were frozen before the four public calls; the same split seed was used for both references. Only their SHA-256 digests are shown.

- Serial source SHA-256: f5a78eb0f073af7fb514b2f35e8e42e121f57e1b5ed2c588acbded40809bbb80
- Stage-parallel source SHA-256: d8e58b4b8a9837099f2d86ab62a9fa8c96717a42906c316138ce6655ba7dd74b
- Development seed SHA-256: 3bb14b8edbaab5e6ec311c436698a904bfb7b66966ef2bb42805f070086ee90e
- Heldout seed SHA-256: 2b726b6ad330dc485e6d2a8e7557486949afc49acd01cd9a5d4d949e406fd9ce
- Contract identity SHA-256: 27b00401a2052b2bbf4bb97024bb631257fecdbeabd42b514f97ce1740159459

## Fixed scoring results

All four calls passed exact source/mapped arithmetic and protocol replay across all five Ns, including 257-cycle blocked-output and reset-while-blocked checks. The fixed gates were area <=4× serial, workload cycles <=serial, and always-ready stream II <=B+6, where B=(N/2)log2(N). Serial qualified in both splits and earned zero reward as baseline. Stage-parallel was correct in both splits but unqualified: at N=16 its generic-cell area was 27,766 versus 5,000 for serial, a 5.5532× ratio. It met the completion and II gates at every N, but the failed area gate sets its reward to zero. The gate failure is preserved; the RTL and gates were not tuned after observing either split.

| Split | Reference | N | Cells | Workload cycles | Stream II | Area ratio | Cycle ratio | Gates |
|---|---|---:|---:|---:|---:|---:|---:|---|
| development | serial_butterfly | 1 | 26 | 213 | 2 | 1.000 | 1.000 | pass |
| development | serial_butterfly | 2 | 4668 | 312 | 3 | 1.000 | 1.000 | pass |
| development | serial_butterfly | 4 | 4717 | 666 | 6 | 1.000 | 1.000 | pass |
| development | serial_butterfly | 8 | 4811 | 1951 | 14 | 1.000 | 1.000 | pass |
| development | serial_butterfly | 16 | 5000 | 6773 | 34 | 1.000 | 1.000 | pass |
| development | stage_parallel | 1 | 26 | 213 | 2 | 1.000 | 1.000 | pass |
| development | stage_parallel | 2 | 2952 | 312 | 3 | 0.632 | 1.000 | pass |
| development | stage_parallel | 4 | 6489 | 554 | 4 | 1.376 | 0.832 | pass |
| development | stage_parallel | 8 | 13571 | 735 | 5 | 2.821 | 0.377 | pass |
| development | stage_parallel | 16 | 27766 | 1302 | 6 | 5.553 | 0.192 | fail: area |
| heldout | serial_butterfly | 1 | 26 | 337 | 2 | 1.000 | 1.000 | pass |
| heldout | serial_butterfly | 2 | 4668 | 493 | 3 | 1.000 | 1.000 | pass |
| heldout | serial_butterfly | 4 | 4717 | 844 | 6 | 1.000 | 1.000 | pass |
| heldout | serial_butterfly | 8 | 4811 | 2314 | 14 | 1.000 | 1.000 | pass |
| heldout | serial_butterfly | 16 | 5000 | 8300 | 34 | 1.000 | 1.000 | pass |
| heldout | stage_parallel | 1 | 26 | 337 | 2 | 1.000 | 1.000 | pass |
| heldout | stage_parallel | 2 | 2952 | 493 | 3 | 0.632 | 1.000 | pass |
| heldout | stage_parallel | 4 | 6489 | 802 | 4 | 1.376 | 0.950 | pass |
| heldout | stage_parallel | 8 | 13571 | 1046 | 5 | 2.821 | 0.452 | pass |
| heldout | stage_parallel | 16 | 27766 | 1527 | 6 | 5.553 | 0.184 | fail: area |

Three predeclared N=4 copied-serial arithmetic controls were checked on mathematical witnesses before synthesis. Each compiled and synthesized, then produced the expected wrong numerical value in both source and mapped simulation: wrong butterfly sign gave (1,1,1,1) instead of (1,-1,1,-1); swapping output lanes 1 and 2 gave (1,1,-1,-1); signed8 truncation after each butterfly gave (-4,0,0,0) instead of (508,0,0,0). These are narrow arithmetic regression controls, not formal mutation coverage. See [compact machine-readable evidence](../evidence/hadamard-int8-v1/qualification.json), [freeze manifest](../evidence/hadamard-int8-v1/freeze-manifest.json), and [control results](../evidence/hadamard-int8-v1/control-results.json).

## Historical Phase 1 note

An earlier stage-unrolled Phase 1 architecture passed limited N=1,4 smokes, then was superseded before qualification by explicit shared datapaths. Its hashes and status are retained only as [historical evidence](../evidence/hadamard-int8-v1/phase1-historical.json). None of its area or timing measurements are used here.

## MAIN integration checks

The full MAIN source suite passed 240/240 tests using Yosys 0.52 and Icarus 12. An isolated installed wheel imported the contract and frozen sources; direct reset/step and JSONL reset/step both passed using five verified cache hits per call and zero fresh tool logs. All 283 pre-existing family/test source and historical-v34 files compared byte-for-byte against the pre-integration snapshot were unchanged. See [integration verification](../evidence/hadamard-int8-v1/integration-verification.json).

## Limits

Area is generic synthesis cell count and completion is workload cycle count, not routed physical PPA. There was no formal proof, exhaustive RTL proof, physical run, model-quality evaluation, or trained-RL run. Correctness and reward qualification are separate claims. Both frozen references retain a fixed 16-lane workspace and dynamic indexing even when compile-time N is smaller. They are straightforward reference architectures, not best-known or minimum-area baselines; score interpretation is relative only to these exact frozen sources.
