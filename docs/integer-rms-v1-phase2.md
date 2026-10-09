# Integer RMS exact-integer family: Phase 2 qualification

The integer_rms family is an exact integer normalization microbenchmark inspired by RMS normalization. It is not equivalent to floating-point model RMSNorm. No model-quality, formal-verification, physical-timing, area-after-routing, or power claim follows from these proxy results. Source screening and tool timeouts are not OS isolation.

The source and evaluator/contract were frozen before evaluation. Source SHA256: serial `0a7241139699cbd77852761dc6969fade0ccaf1a71b9baef09590b5f581cb7a3`, chunked4 `6058b594e112a61539694a2b15afd05713d21fd0f4d0f77c1ac5b12eb67a823e`. Contract identity SHA256 is `57372ddabaf9db17b1e1662cdbbb11f8e6c24ca14dc0a1ce945b9526ed00ebc2`; evaluator recipe SHA256 reported by all four runs is `72c6234016a0d223b4ba59b3fe0b34db4f0b45f35fd64f00524ddb058bbcee09`. Individual file hashes and predeclared seed hashes are in `../../integer-rms-phase2-freeze.json`. Full private seeds remain in restricted local evidence only. The same predeclared split seed and workloads pair both architectures. No candidate or evaluator tuning followed results.

Four sequential public evaluator calls checked the two references on all N={1,2,4,8,16} under independent development and heldout traffic. Each run passed exact source/mapped arithmetic, mixed ready-valid traffic, saturation, 257-cycle blocked output, blocked-output reset/recovery, ordered consumption and progress. The serial baseline qualified at every N. Both references were tested correct and reward-qualified on both splits, with no gate failures. Both rewards were **0.0**, because the fixed balanced area×cycle proxy clamps negative benefit to zero. Chunked4's area costs outweigh its cycle improvement; correctness and qualification remain distinct from reward.

| Split | Reference | Correct | Qualified | Reward | Mean log(area ratio × cycle ratio) |
|---|---|---|---|---:|---:|
| Development | serial | yes | yes | 0.0 | 0.0000 |
| Development | chunked4 | yes | yes | 0.0 | 0.4079 |
| Heldout | serial | yes | yes | 0.0 | 0.0000 |
| Heldout | chunked4 | yes | yes | 0.0 | 0.4207 |

The fixed gates per N were generic-cell area ratio <=4, completion-cycle ratio <=1, and saturated acceptance II <=2*N+24. Chunked4's development (area ratio, completion ratio, II) were N1 (0.843, 1.000, 21), N2 (1.344, 0.942, 22), N4 (2.330, 0.900, 24), N8 (2.328, 0.821, 29), N16 (2.329, 0.772, 39). Heldout completion ratios were 1.000, 1.000, 0.946, 0.804, 0.753 respectively; area and II were unchanged. Serial II was 21,23,27,35,51 versus respective fixed limits 26,28,32,40,56. Full result JSON, artifacts and tool logs are in `../../integer-rms-phase2-results/{development,heldout}/{serial,chunked4}/`. The cache has verified paired records.

Three separate copied-source N=4 arithmetic mutants were screened, synthesized, and detected by both RTL and mapped simulation on specific numerical witnesses. Omitted +1 epsilon used (2,2,2,0); a narrowed -32768 magnitude used (-32768,0,0,0); removed ties-even increment used (1024,3,0,0). All six stage checks compiled and failed on arithmetic mismatch. See `../../integer-rms-phase2-negative-controls/summary.json` and `scripts/check_integer_rms_negative_controls_v1.py`. These are narrowly scoped functional arithmetic regression probes, not a security audit, formal proof, or mutation-coverage rate.

The new-family focused unit suite passed 5 tests; the full lightweight source unit suite passed 224 tests with the matching local HDL tools. A wheel built without network dependencies; the unpacked wheel import, contract read, oracle, RTL generator and JSONL error-boundary smoke passed. No software was installed or published. Local cache, Phase 1/2 evidence, mutants and package build total about 468 MB, below the 2 GB cap; workspace free space exceeds 29 GB.

Directed host witnesses cover zero, extrema, mixed signs, every single-nonzero position, ignored input fields, equal magnitude, floor division when N>=2, reachable exact/above/below-square radicands, and positive/negative even/odd half ties when N>=2. N=1 cannot witness a nonzero S%N or the labelled below-square case and has no directed half tie. The valid domain has no observed output-clipping witness; clipping coverage is not claimed.
