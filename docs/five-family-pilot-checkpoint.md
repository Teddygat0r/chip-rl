# Five-family pilot checkpoint

**Checkpoint status (2026-10-11): a finitely validated reference scaffold, not yet a frontier-lab training environment.** The working package can run one specified structural configuration at a time with source/mapped checks and private replay artifacts. Frozen authored/legacy references passed 37/37 TRAIN and 65/65 reference-only DEV/TEST cases; a ten-design TRAIN physical area study reached post-route reporting. No model-difficulty trial, model call, token accounting, policy-weight update, model-based DEV/TEST evaluation, independent human RTL signoff, or general physical-proxy calibration is claimed.

## What was frozen and run

- Families: `gather`, `mshr`, `sparse24` (the `sparse24_dot_requant` contract), `block_quant`, and `hadamard_int8`.
- The corrected [canonical pre-measurement registry](../evidence/pilot-reference-panel/canonical-v2/registry.json) has canonical JSON SHA-256 `b428f5a19e16565e9e9a171f2eda78300f5b892867df524eed48f2ad5fb02c44`. It records 37 source/configuration cases, source and recipe hashes, a tool fingerprint, and same-workload pairing within each family/configuration. The [case report](../evidence/pilot-reference-panel/canonical-v2/report.json) links back to that digest and retains per-case records in [the case directory](../evidence/pilot-reference-panel/canonical-v2/cases/). All 37 returned `tested_correct=true` and `finite_source_and_mapped_pass`; the report records zero failed cases. This is finite validation of these authored references, not formal proof or independent review.
- Total panel elapsed wall time was **182.262248 s**; process and spawned-tool CPU time was **175.610124 s**. Dividing by 37 yields **4.926 s wall and 4.746 s CPU per registered case**, descriptive averages for this sequential, warm-cache-or-not panel only. Several cases rerun legacy paired checks and several use shared synthesis cache effects. These averages are not marginal evaluator cost, model rollout throughput, dollar cost, or a general RL training-cost estimate. Model tokens and cost are unavailable because there were no model calls.
- The first [panel attempt](../evidence/pilot-reference-panel/superseded.json) retained two attempted gather cases before it was stopped: emitted source text had parameter defaults that varied with configuration, violating the identical-source-bytes rule. Those cases are **superseded and excluded** from all totals and Pareto conclusions. The canonical registry corrects the source-bytes issue.
- The separate [sized-Hadamard study](pilot-hadamard-sized.md) and its [machine summary](../evidence/pilot-hadamard-sized/summary.json) checked N=1,2,4 only. At N=4, sizing the workspace and indices changed generic cells **4,717 → 1,379**, with workload cycles **666 → 666** and matched source/mapped traces for this finite campaign. N=2 was 4,668 → 365 cells at 312 → 312 cycles; N=1 was unchanged at 26 cells and 213 cycles. The summary calls this a development experiment; its measured parameter values are the proposed TRAIN values, not the protocol's DEV N=8 or TEST N=16.
- After the source freeze, the same 13 authored/legacy reference sources were qualified at the protocol’s DEV and TEST parameters without tuning. The [reference-only qualification summary](../evidence/pilot-reference-holdout-qualification/summary.json) and [registry](../evidence/pilot-reference-holdout-qualification/registry.json) record **65/65 finite source/mapped passes**: 24/24 DEV and 41/41 TEST, zero failed cases. Its canonical registry digest is `56e1c78c0fcf5e02f09310fcc437455ae755419d7313e5e1a055c749047c60db`. This establishes tested correctness of these frozen authored references across the legal dimensions. It is **not** a model test, unseen-specification test, or evidence of learned generalization. Keep these outcomes out of any future model feedback or candidate-selection path.
- The [ten-design physical manifest](../evidence/pilot-physical-calibration/manifest.json) is frozen under SHA-256 `0ec4b4ce9424d81494c743fa5c9726be20ea93d5a895dbede651c990cff57ebc`. All ten TRAIN designs passed finite pre-route checks and reached post-route reports with zero **reported detailed-route violations**. The [physical checkpoint](pilot-physical-calibration.md) separates the observations from general calibration or signoff claims.

## Paired TRAIN reference points

All cell counts and logic depths are Yosys generic-logic proxies; cycles and stream initiation intervals are finite Icarus workload observations. For gather, the first and second cycle columns are the paired `target_short` and `target_long` replays. For MSHR the first cycle column is its transaction workload. For the other three families it is the family workload; II is the measured stream interval. A dash is not measured or not comparable. Every row passed the finite checks described above; raw per-case evidence and hashes are in the linked case records.

| Family | Parameter | Reference | Cells | Depth | Cycles / short | Cycles / long | Stream II |
|---|---:|---|---:|---:|---:|---:|---:|
| gather | DEPTH=16 | legacy_baseline | 4,614 | 13 | 735 | 3,792 | — |
| gather | DEPTH=16 | time_mux | 3,113 | 12 | 2,157 | 10,795 | — |
| gather | DEPTH=16 | static_decoded | 4,863 | 11 | 735 | 3,792 | — |
| gather | DEPTH=32 | legacy_baseline | 7,233 | 14 | 604 | 3,654 | — |
| gather | DEPTH=32 | time_mux | 4,715 | 13 | 1,943 | 10,292 | — |
| gather | DEPTH=32 | static_decoded | 7,481 | 12 | 604 | 3,654 | — |
| mshr | ENTRIES=2 | ring | 1,097 | 19 | 5,007 | — | — |
| mshr | ENTRIES=2 | shift | 1,077 | 21 | 5,007 | — | — |
| mshr | ENTRIES=4 | ring | 2,207 | 24 | 3,026 | — | — |
| mshr | ENTRIES=4 | shift | 2,174 | 26 | 3,026 | — | — |
| sparse24 | G=1 | serial | 8,267 | 71 | 1,320 | — | 6 |
| sparse24 | G=1 | pipeline | 7,226 | 70 | 280 | — | 1 |
| sparse24 | G=2 | serial | 8,266 | 71 | 2,457 | — | 8 |
| sparse24 | G=2 | pipeline | 8,713 | 70 | 314 | — | 1 |
| sparse24 | G=4 | serial | 8,266 | 71 | 2,970 | — | 12 |
| sparse24 | G=4 | pipeline | 11,021 | 70 | 334 | — | 1 |
| block_quant | N=1 | serial | 2,223 | 42 | 757 | — | 5 |
| block_quant | N=1 | chunked4 | 1,426 | 36 | 757 | — | 5 |
| block_quant | N=1 | parallel | 657 | 34 | 192 | — | 1 |
| block_quant | N=2 | serial | 2,224 | 42 | 1,166 | — | 7 |
| block_quant | N=2 | chunked4 | 1,934 | 36 | 1,050 | — | 6 |
| block_quant | N=2 | parallel | 1,279 | 34 | 219 | — | 1 |
| block_quant | N=4 | serial | 2,223 | 42 | 1,771 | — | 11 |
| block_quant | N=4 | chunked4 | 2,935 | 36 | 1,764 | — | 8 |
| block_quant | N=4 | parallel | 2,478 | 60 | 224 | — | 1 |
| block_quant | N=8 | serial | 2,222 | 42 | 3,623 | — | 19 |
| block_quant | N=8 | chunked4 | 2,932 | 36 | 2,270 | — | 13 |
| block_quant | N=8 | parallel | 4,880 | 112 | 229 | — | 1 |
| hadamard_int8 | N=1 | serial_butterfly | 26 | 6 | 213 | — | 2 |
| hadamard_int8 | N=1 | stage_parallel | 26 | 6 | 213 | — | 2 |
| hadamard_int8 | N=1 | sized_serial_butterfly | 26 | 6 | 213 | — | 2 |
| hadamard_int8 | N=2 | serial_butterfly | 4,668 | 38 | 312 | — | 3 |
| hadamard_int8 | N=2 | stage_parallel | 2,952 | 28 | 312 | — | 3 |
| hadamard_int8 | N=2 | sized_serial_butterfly | 365 | 15 | 312 | — | 3 |
| hadamard_int8 | N=4 | serial_butterfly | 4,717 | 38 | 666 | — | 6 |
| hadamard_int8 | N=4 | stage_parallel | 6,489 | 37 | 554 | — | 4 |
| hadamard_int8 | N=4 | sized_serial_butterfly | 1,379 | 25 | 666 | — | 6 |

## Interpretation of the reference panel

These points are **architectural alternatives**, not a universal best reference or model-generated improvements. The [report's Pareto lists](../evidence/pilot-reference-panel/canonical-v2/report.json) compare only the two named axes within the same family, parameter, and replay; ties and depth remain visible in the raw rows. Do not pool unlike families or treat a cell/cycle frontier as silicon PPA.

- Gather `static_decoded` at DEPTH=16 uses 4,863 versus 4,614 baseline cells and has identical 735/3,792 replay cycles, while generic logic depth drops 13 → 11. At DEPTH=32 it similarly uses 7,481 versus 7,233 cells, has identical 604/3,654 cycles, and depth drops 14 → 12. On cells-versus-cycles it is dominated by the legacy baseline; the lower depth is a separate proxy that needs physical timing validation. `time_mux` saves cells but spends more cycles.
- MSHR `shift` saves a little area (ENTRIES=2: 1,097 → 1,077 cells; ENTRIES=4: 2,207 → 2,174) with identical workload cycles (5,007 and 3,026 respectively). Its logic depths increase by two (19 → 21 and 24 → 26). Near-area parity and unchanged cycles do not establish a broadly hard search problem.
- Sparse24 `pipeline` is substantially faster in cycles and II; at G=1 it also uses fewer cells, whereas at G=2 and 4 it uses more cells. This is a configuration-dependent area/throughput tradeoff.
- Block quant `chunked4` is not the best cells-versus-cycles point at N=4: `parallel` is 2,478 cells/224 cycles versus chunked4's 2,935/1,764. `parallel` has much greater generic depth at N=4 (60 versus 36), and its N=16 frozen area-gate caveat remains; do not extrapolate the N=4 point to a universal winner. At N=8 the three references form an area/cycles tradeoff in the measured pair of axes.
- Hadamard sizing removes an avoidable small-N fixed-workspace overhead. At N=4 `sized_serial_butterfly` saves cells with identical cycles; `stage_parallel` is faster (554 cycles) but larger (6,489 cells). The one physical N=4 pair below also favors the sized serial source in routed area; ranking stability across configurations and implementations remains open.

## Exploratory physical area study

The [full physical report](pilot-physical-calibration.md) links the frozen [manifest](../evidence/pilot-physical-calibration/manifest.json), [original results](../evidence/pilot-physical-calibration/results.json), [exact-source joined data](../evidence/pilot-physical-calibration/joined.json), [analysis](../evidence/pilot-physical-calibration/analysis.json), and [critical-path scope](../evidence/pilot-physical-calibration/critical-path-scope.json). It measures two frozen references at one TRAIN parameter per family, one implementation per source. Four of five paired generic-cell versus routed-area **directions** agree. Gather is the exception: generic cells increase 4,614 → 4,863 while routed standard-cell area is 8,996.92 → 8,988.14 μm², a −0.10% near-tie in one run. Hadamard N=4 has the clearest observed area change: generic cells 4,717 → 1,379 (−70.8%), final standard-cell area 5,210.94 → 2,042.88 μm² (−60.8%), and unchanged measured workload cycles. These are observed paired points, not a guaranteed design ranking.

The descriptive pooled Spearman correlation is **ρ=0.7818 across ten heterogeneous designs**. Circuit size and architecture confound the pool; two points per family at one parameter cannot establish within-family calibration, uncertainty, or ranking stability. Effective placement densities differ despite a common requested setting, and benchmark generic-cell synthesis differs from the physical technology-mapping recipe. All ten recorded maximum setup paths are **I/O-to-I/O** under a loose clock and external-delay constraint, so slack cannot validate core Fmax or cycles×routed-period latency. Zero reported detailed-route violations do not establish reference-deck DRC/LVS, post-route functional equivalence, GDS, power, or signoff. Three-or-more tradeoff points across multiple configurations, reruns, and a justified timing metric are still required by the [protocol](pilot-experiment-protocol.md) before a general proxy claim.

## Package and split-aware API readiness

A local full unit suite passed **278/278 in 13.570 s**. A `chip_rl` 0.37.0 wheel was built with SHA-256 `98a1906cc8f8651d83053a6d1a53c8f51b15cccfc07ec6155a0f10abdc28b850`, installed into a fresh virtual environment, and an installed Hadamard N=1 `run_case` smoke passed at 26 cells. This is a packaging/import and one-case execution check, **not** an installed-wheel campaign across families or configurations. The [machine-readable validation record](../evidence/pilot-validation.json) separates these checks. The wheel and local test log are working artifacts, not included as tracked evidence here.

The [`chip_rl.pilot` manifest](../chip_rl/pilot/manifest.py) encodes structural parameter partitions: gather TRAIN 16/32, DEV 64, TEST 128/256; MSHR TRAIN 2/4, DEV 6, TEST 8; sparse24 TRAIN 1/2/4, DEV 3/5, TEST 6/7/8; block quant TRAIN 1/2/4/8, DEV 3/5/6/7, TEST 9–16; Hadamard TRAIN 1/2/4, DEV 8, TEST 16. Its [single-case runner](../chip_rl/pilot/runner.py) validates one requested split/configuration, checks the source, pairs candidate against a fixed legacy reference, returns a public result, and writes private replay details outside the repository. The [CLI](../chip_rl/pilot/__main__.py) exposes `freeze` and `run`. DEV/TEST require a previously created exact-source freeze manifest. This implementation prevents an ordinary single-case call from silently running another split; a full model-facing test firewall and an independent leakage audit are still needed before any blind-test claim. Existing public family evaluators may expose proposed heldout dimensions and must not be used as an optimizer's sealed training interface.

For an authorized local TRAIN check, save the candidate RTL to a source file and call `python -m chip_rl.pilot run --family hadamard_int8 --config 4 --split train --source SOURCE --private-artifacts PRIVATE_OUTPUT`. Use a new private output directory **outside the repository** for each run; omit `--seed` unless the experiment's private controller sets it. For DEV/TEST, first use `python -m chip_rl.pilot freeze --family FAMILY --source SOURCE --output FROZEN_MANIFEST` **before** any heldout feedback, then pass that manifest to `run` with `--frozen-manifest`. These commands describe the interface; the DEV/TEST runs above were frozen **reference-only qualification**, not model-based holdout evaluation. Keep replay seeds, vectors, traces, logs, and raw cache material inaccessible to candidates and out of public artifacts.

## Decision and remaining gates

**Ready now:** a reproducible, split-aware CPU evaluator, finite frozen-reference checks across TRAIN/DEV/TEST structural parameters, and a ten-point exploratory TRAIN routed-area dataset, all subject to the recorded tool/recipe/source hashes. **Still pending:** named independent human RTL/evaluator review ([review packet](pilot-review-packet.md)); a frozen, feedback-isolated model experiment and measured generative difficulty; multi-point physical proxy validation across configurations; actual weight-updated policy training with matched frozen-policy and best-of-N controls; and any **model** DEV/TEST evaluation after a second-stage candidate/model freeze. The [experiment protocol](pilot-experiment-protocol.md) defines the planned denominators, budgets, leakage controls, controls, and claim boundaries. This preparation alone does **not** establish an RL-training environment suitable for a frontier lab, a learned-policy gain, a physical proxy correlation, or any result on unseen circuit families. All changes and measurements in this checkpoint are local; no new push or publication is claimed.
