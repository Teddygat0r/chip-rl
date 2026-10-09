# Exact integer RMS: serial combinational-root reference, Phase 1

A third reference, `serial_comb_root`, keeps the existing exact-integer oracle, directed workloads, one-lane-per-cycle square accumulation, one-lane-per-cycle normalization, ready-valid protocol, reset behavior and fixed qualification gates. Its PREPARE state applies a synthesizable combinational unsigned restoring integer-square-root function with exactly sixteen fixed iterations to M=floor(S/N)+1, registering D and proceeding directly to NORMALIZE. It does not enter the 16-cycle SQRT state. This is still an exact integer microbenchmark, not floating-point model RMSNorm.

The existing serial and chunked4 generated source bytes remain unchanged at SHA256 `0a7241139699cbd77852761dc6969fade0ccaf1a71b9baef09590b5f581cb7a3` and `6058b594e112a61539694a2b15afd05713d21fd0f4d0f77c1ac5b12eb67a823e`, respectively. The new generated Verilog SHA256 is `c7f72191ad6883f3543594544143517b88728883f32520f0b776a289d258d873`.

Focused Python unit tests pass. Sequential local source and mapped synthesis/arithmetic/protocol smoke passed at N=1,4,16 using a 32-request traffic probe plus directed arithmetic vectors. All three checked exact oracle outputs, reset/recovery, stable 257-cycle blocked output, reset while output was visibly blocked, and source/mapped agreement. Logs and per-N `summary.json` records are in `../../integer-rms-comb-root-phase1-evidence/serial_comb_root/`.

| N | Directed vectors | Generic cells | Generic logic depth | 32-request completion cycles | Saturated acceptance II |
|---:|---:|---:|---:|---:|---:|
| 1 | 40 | 9455 | 325 | 174 | 5 |
| 4 | 67 | 9492 | 325 | 356 | 11 |
| 16 | 115 | 9496 | 325 | 1143 | 35 |

The corresponding serial Phase 1 generic cells were 8156 at N=1 and 8193 at N=4; all measured serial generic logic depths were 325. The new design uses more generic cells but fewer protocol cycles and acceptance intervals in these smokes. These are digital/synthesis proxies and do not establish clock frequency, physical timing, routed area or power. A fully combinational root can lengthen a critical path in another implementation even though the generic depth reported here remains 325, likely dominated by another datapath. Formal and physical verification were not run.

This is Phase 1 only. No five-N scored sweep or post-result tuning has been run for `serial_comb_root`. Candidate/evaluator review is required before any scored qualification. The new smoke evidence is about 20 MB; combined cache and new smoke evidence are about 153 MB, with over 29 GB workspace free.
