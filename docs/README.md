# Documentation and evidence index

Start with [current status](current-status.md) for qualification scope, [task inventory](task-inventory.md) for all 33 families, and the [machine-readable inventory](../evidence/current-inventory.json) for source/evidence paths. The [prior 25-family checkpoint](https://github.com/Teddygat0r/chip-rl/tree/codex/verified-25-family-checkpoint) remains on its separate branch. Historical report counts apply to their own versions.

## Recent family results

- Integer RMS: [v1 Phase 1](integer-rms-v1-phase1.md), [v1 qualification](integer-rms-v1-phase2.md), [combinational-root Phase 1](integer-rms-serial-comb-root-phase1.md), [combinational-root qualification](integer-rms-serial-comb-root-phase2.md), [compact evidence](../evidence/integer_rms/serial_comb_root_v1/summary.json)
- Block RLE: [Phase 1](block-rle-v1-phase1.md), [qualification](block-rle-v1-phase2.md), [compact evidence](../evidence/block-rle-v1/phase2-compact-summary.json)
- Block FOR: [Phase 1](block-for-v1-phase1.md), [qualification](block-for-v1-phase2.md), [shiftpack Phase 1](block-for-shiftpack-phase1.md), [shiftpack qualification](block-for-shiftpack-phase2.md), [v1 evidence](../evidence/block-for-v1/compact-summary.json), [shiftpack evidence](../evidence/block-for-shiftpack-v1/compact-summary.json)
- BF16-to-INT8 quantization: [contract](../chip_rl/bf16_quant/contracts.md), [Phase 2 report](bf16-quant-v1-phase2.md), [compact evidence](../evidence/bf16-quant-v1/summary.json), [MAIN integration check](../evidence/bf16-quant-v1/integration-verification.json)
- Hadamard INT8 transform: [contract](../chip_rl/hadamard_int8/contracts.md), [Phase 2 report](hadamard-int8-v1-phase2.md), [qualification](../evidence/hadamard-int8-v1/qualification.json), [arithmetic controls](../evidence/hadamard-int8-v1/control-results.json), [MAIN integration check](../evidence/hadamard-int8-v1/integration-verification.json)
- Block quantization: [v36 measurement-only](block-quant-v36.md), [v37 conditional reward](block-quant-reward-v37.md), [v38 sensitivity](block-quant-sensitivity-v38.md), [v38 evidence](../evidence/v38/summary.json)

Historical v33/v35/v37 raw paths referenced in [current status](current-status.md) are absent from this snapshot. They are retained as historical citations, not presented as current local raw evidence. The post-Hadamard [240/240 source unit result](../evidence/hadamard-int8-v1/integration-verification.json) is not a fresh 33-family simulation sweep. Physical integer RMS evaluation remains open.
