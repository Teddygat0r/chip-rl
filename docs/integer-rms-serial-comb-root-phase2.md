# Exact integer RMS: serial combinational-root Phase 2 qualification

`serial_comb_root` substitutes an exact sixteen-iteration combinational restoring integer-square-root function for the serial reference's sixteen-cycle square-root state. It retains serial accumulation and normalization, the exact integer oracle, workloads, reset/ready-valid rules and fixed gates. This exact integer microbenchmark is not floating-point model RMSNorm.

Before running scored data, candidate and evaluator/contract hashes and two new 128-bit split seeds were frozen in `evidence/integer_rms/serial_comb_root_v1/source-evaluator-freeze.json`. The new heldout seed differs from the earlier v1 heldout seed. Raw seeds are excluded from this source tree; they are in restricted local private replay data for owner-controlled persistence. Generated source SHA256 remained `0a7241139699cbd77852761dc6969fade0ccaf1a71b9baef09590b5f581cb7a3` for serial and `6058b594e112a61539694a2b15afd05713d21fd0f4d0f77c1ac5b12eb67a823e` for chunked4. New `serial_comb_root` source SHA256 is `c7f72191ad6883f3543594544143517b88728883f32520f0b776a289d258d873`. Contract identity SHA256 is `57372ddabaf9db17b1e1662cdbbb11f8e6c24ca14dc0a1ce945b9526ed00ebc2`; public evaluator recipe SHA256 was `b329539388e75a30a82915ffa9a2dcb19e1d4eb5e066d0b03b518fdfeec36aca` in all four runs.

Four sequential public evaluator calls compared serial and serial_comb_root across all N={1,2,4,8,16} on separately predeclared development and heldout traffic. Both references passed exact RTL and mapped arithmetic/protocol checks at every N. Both passed the fixed per-N hard gates: generic-cell area ratio <=4, workload completion cycles <=serial, and saturated acceptance II <=2*N+24. There were no gate failures. Serial scored 0.0 by definition. serial_comb_root scored **0.3006514204 development** and **0.2857661278 heldout** under the fixed balanced area×cycle proxy.

| Split | N | Serial cells / cycles / II | Comb-root cells / cycles / II | Generic logic depth, both |
|---|---:|---:|---:|---:|
| Development | 1 | 8156 / 1929 / 21 | 9455 / 482 / 5 | 325 |
| Development | 2 | 8188 / 2503 / 23 | 9487 / 785 / 7 | 325 |
| Development | 4 | 8193 / 3161 / 27 | 9492 / 1265 / 11 | 325 |
| Development | 8 | 8202 / 4683 / 35 | 9498 / 2875 / 19 | 325 |
| Development | 16 | 8197 / 8419 / 51 | 9496 / 5862 / 35 | 325 |
| Heldout | 1 | 8156 / 2697 / 21 | 9455 / 734 / 5 | 325 |
| Heldout | 2 | 8188 / 3191 / 23 | 9487 / 1086 / 7 | 325 |
| Heldout | 4 | 8193 / 3649 / 27 | 9492 / 1696 / 11 | 325 |
| Heldout | 8 | 8202 / 5731 / 35 | 9498 / 2983 / 19 | 325 |
| Heldout | 16 | 8197 / 9496 / 51 | 9496 / 7013 / 35 | 325 |

These are generic-cell, generic-depth, and digital-cycle proxies, not measurements of clock period, routed timing, silicon area, energy or throughput at a real frequency. The combinational root may lengthen a critical path in another implementation even though the overall generic depth is 325 in this synthesis, likely dominated by the division datapath. Formal and physical verification were not run. No candidate, oracle, workload, gate or score tuning followed the results.

Compact freeze/summary and full result JSON are in `evidence/integer_rms/serial_comb_root_v1/`. Detailed local tool logs and artifacts are outside the source tree in `../integer-rms-comb-root-phase2-results/`. The fresh raw replay seeds remain only at the restricted local path `../integer-rms-comb-root-phase2-private/predeclared-seeds.json` pending combined persistence. The new qualification plus cache uses about 403 MB, below the 2 GB cap, with over 29 GB free.
