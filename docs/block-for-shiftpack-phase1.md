# Block FOR serial_shiftpack: Phase 1

Status: a third, frozen reference was added to the existing block-FOR family. This is a source and mapped N=1,4,16 smoke, not a full scored five-N qualification. The two earlier reference sources remain byte-identical. No gates, oracle, workloads, or protocol semantics changed.

Generated RTL SHA256:

- serial: `6e070e3d9868b0f7139950359ca9ca6ecf0a79cea22755c7226ee988828dc2f6`
- chunked4: `2303f60c81ed9dbdea4157612dcbe1f07409b3b1ed8be63e5b0e3559a8622dff`
- serial_shiftpack: `44257a380dd543c478981454a43a9b848ac6bbabae30f6d6e94576b7083322cb`

The new reference keeps the serial min/max scan and exact bit-width calculation. It clears a 128-bit accumulator at each block and consumes lanes in reverse order, from N−1 to 0. Each packing edge computes `acc_next = (acc << w) | (x_i−b)`. The output concatenates 116 zero bits, accumulator, 4-bit width, and 8-bit base. Thus lane zero occupies the low offset field, including when w=0. Packing remains one lane per cycle, with expected and observed saturated II `2*N+3`.

| N | Exact source/mapped vectors | Shiftpack generic cells | Earlier serial cells | Shiftpack workload cycles | Saturated II | Mapped logic depth | 257-cycle stall/reset |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 117 | 1352 | 2605 | 647 | 5 | 17 | pass |
| 4 | 182 | 1365 | 2602 | 2006 | 11 | 17 | pass |
| 16 | 218 | 1370 | 2598 | 7794 | 35 | 17 | pass |

The directed workload includes every reachable width, power-of-two range boundaries, unsigned edge cases, ignored input fields, and consecutive changing blocks. The mapped and source tests also check stable blocked output, reset while blocked, ordered responses, and recovery. Focused block-FOR tests pass with all three frozen hashes and canonical examples. These generic cell, depth, and cycle numbers are synthesis/simulation proxies; no physical PPA, formal proof, or learned-agent claim is made. The five-N scored sweep awaits review.
