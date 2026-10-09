# Block FOR v1: Phase 2 qualification

Status: all fixed, paired five-N development and heldout evaluations passed functional source/mapped correctness and service gates. Reward is zero for both serial and chunked4 in both splits. This result was retained without tuning the frozen references, gates, or workload after scores were seen.

The two generated candidate hashes remain serial `6e070e3d9868b0f7139950359ca9ca6ecf0a79cea22755c7226ee988828dc2f6` and chunked4 `2303f60c81ed9dbdea4157612dcbe1f07409b3b1ed8be63e5b0e3559a8622dff`. All block-FOR Python and contract files were hashed before qualification with family tree SHA256 `8843f27e5a32e48fb1391d6994b7e7da3dc536990ab1607a6f1f81658356f3db`. Two distinct 128-bit host seeds were predeclared privately, one per split. Each split used the same paired workloads for serial and chunked4. No private seed is exposed in the source-action interface.

| Split | Reference | Correct | Qualified | Reward | Area ratios at N=1,2,4,8,16 | Completion ratios at N=1,2,4,8,16 | Saturated II at N=1,2,4,8,16 |
|---|---|---|---|---:|---|---|---|
| development | serial | yes | yes | 0 | 1, 1, 1, 1, 1 | 1, 1, 1, 1, 1 | 5, 7, 11, 19, 35 |
| development | chunked4 | yes | yes | 0 | 1.321, 1.956, 3.061, 3.061, 3.062 | 1, 0.899, 0.997, 0.626, 0.654 | 5, 6, 8, 13, 23 |
| heldout | serial | yes | yes | 0 | 1, 1, 1, 1, 1 | 1, 1, 1, 1, 1 | 5, 7, 11, 19, 35 |
| heldout | chunked4 | yes | yes | 0 | 1.321, 1.956, 3.061, 3.061, 3.062 | 1, 0.816, 0.995, 0.651, 0.667 | 5, 6, 8, 13, 23 |

All area ratios are at most 4, completion ratios at most 1, and IIs at most `2*N+6`. Chunked4's geometric mean area-cycle product remains above 1, so the fixed clipped reward is 0 despite qualification.

Three copied-source N=4 negative controls were predeclared with concrete witnesses before testing. Each passed screening, synthesis, source compilation, and mapped compilation, and then produced a wrong numerical output versus the independent oracle at both source and mapped levels: wrong bit width at `[0,2,0,2]`, signed extrema at `[128,255,0,127]`, and an offset starting one bit late at `[3,4,6,3]`. This is numerical detection, not a screening or compile rejection.

With an exact read-only copy of the missing historical `evidence/v34/summary.json` fixture from the local main snapshot, all 232 unit tests passed. An installed wheel was imported outside the source checkout and included the new package's contract and frozen-hash files. Its JSONL reset and source-only step API passed. The initial aggregate run without the historical fixture failed solely because that file was absent from the isolated stripped snapshot.

Yosys 0.52/Icarus 12 generic-cell counts and workload cycles are cost proxies. No physical timing/power, formal proof, or trained-RL result is claimed.
