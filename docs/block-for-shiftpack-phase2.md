# Block FOR serial_shiftpack: Phase 2

Status: the third reference passed fixed, paired, full five-N development and heldout qualification. The older serial source is the unchanged baseline; chunked4 was not rescored. No candidate, oracle, workload, scoring gate, or score formula was tuned after results.

Before evaluation, the block-FOR Python/contract tree was frozen at SHA256 `0ec97947ea9ea1c664642c0633b416e5c5df4e79b05d42748c0281d9ecddbd12`, including evaluator `f017dabd51aa0bf86ab27c6447d70b970f819bd00ef1a809b0f8a7c0cc68ef06` and contract `6528033f246a8ba7c85e65c7d4ffac0aaa9aa0386d3726178232a7caa41adfd4`. Frozen generated source SHA256: serial `6e070e3d9868b0f7139950359ca9ca6ecf0a79cea22755c7226ee988828dc2f6`, chunked4 `2303f60c81ed9dbdea4157612dcbe1f07409b3b1ed8be63e5b0e3559a8622dff`, serial_shiftpack `44257a380dd543c478981454a43a9b848ac6bbabae30f6d6e94576b7083322cb`. Distinct fresh private 128-bit seeds were predeclared for the two splits, with paired serial and shiftpack workloads within each split.

All entries below passed source/mapped exact checks, reset/backpressure checks, the 257-cycle output stall, and the per-request ready-high opportunity bound. Correctness, qualification, and reward are separate results: serial was correct/qualified with reward 0 in both splits; serial_shiftpack was correct/qualified with reward `0.275663803501057` in both splits.

| N | Serial cells | Shiftpack cells | Serial depth | Shiftpack depth | Development cycles, both | Heldout cycles, both | II, both | Area ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2605 | 1352 | 30 | 17 | 642 | 1046 | 5 | 0.5190 |
| 2 | 2606 | 1371 | 30 | 17 | 1291 | 1839 | 7 | 0.5261 |
| 4 | 2602 | 1365 | 30 | 17 | 2002 | 2775 | 11 | 0.5246 |
| 8 | 2601 | 1369 | 30 | 17 | 4261 | 4588 | 19 | 0.5263 |
| 16 | 2598 | 1370 | 30 | 17 | 7794 | 9743 | 35 | 0.5273 |

Completion ratio is exactly 1 at every N on both splits. The fixed area limit is 4x serial, completion limit is serial, and saturated II limit is `2*N+6`; all pass. The balanced reward is positive because the geometric mean area-cycle product is below one. This is a generic-cell/cycle proxy reward, not physical PPA.

Compared with the earlier N=1/4/16 Phase 1 smoke, cell counts, mapped depth, and IIs are unchanged. Development workload cycles changed from `647/2006/7794` to `642/2002/7794` because the predeclared Phase 2 seed differs; serial and shiftpack matched exactly in each run. The full N=2/8 cases were added only in Phase 2.

The four complete public-evaluator invocations used a fresh cache. Both serial invocations performed fresh candidate simulations at all five N; both shiftpack invocations also performed fresh candidate simulations, while their paired serial baselines reused the preceding same-split verified serial results. Private seed values and replay artifacts remain in a separate private directory. Formal proof, routed timing, physical power, model quality, and trained-RL outcomes were not measured.
