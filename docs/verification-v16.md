# V16 folded-arithmetic component verification

This checkpoint adds host-only component checks and a sealed batch-evaluation protocol. It adds no family and changes no reward, service gate, baseline RTL, workload or simulation evaluator. All104 pre-v16 runtime files remain byte-identical. The suite still has22 families, six pilots and16 experimental. Physical evaluation remains blocked by the absent OpenROAD/STA/PDK/platform; there are no routed timing, power or silicon-readiness claims.

## What v15 repaired

| Exposed reward exploit | Repair |
|---|---|
| Read future commands from input data while valid was low | Randomize invalid-cycle input data |
| Stop after128 accepted commands | Longer correctness-only histories |
| Emit delayed duplicate outputs | Longer post-work drain |
| Discard a response after prolonged output stall | Long stalls and stability checks |
| Hide narrow-accumulator overflow behind an exact uniform-vector shortcut | Nonuniform extrema, cancellation and tail-term cases |

Two overrestrictive checks were repaired: valid post-reset warmup now receives a bounded readiness wait; TLB memory tags use the16-tag interface capacity instead of translation-cache entry count. The five v15 formal counterexamples were all **expected mutants**: unsigned arithmetic, dropped work, delayed duplicate output, stale root cache, and wrong-context root lookup. They were not failures of valid implementations. Valid folded arithmetic was unproven.

All v15 assumptions/errors remain archived. In particular, its recorded SAT scripts omitted `-set-assumes`; two intended reduced-domain runs were broader-domain timeouts. Nothing in v16 retroactively upgrades those results.

## Component argument and limits

`chip_rl.quality.components` recognizes a folded-template cutpoint and fails closed if its required anchors/typed multiplier declaration are absent. It retains the exact original source, transformed source, harness, script, hashes, logs and counterexample traces. It replaces the signed8×8 multiply with symbolic signed16 products, constrained to[-16256,16384]. Each check records that transformation; no abstract result is reported as an unmodified end-to-end proof.

The supporting pieces are:

1. **Product:** enumerate all65,536 signed byte pairs against a Python integer oracle in both Icarus RTL simulation and a Yosys-mapped netlist. This verifies the typed multiplier cutpoint and its extrema. The initial Icarus launch failed before simulation because its local library path was missing; the corrected run uses the repository's existing `-B` setup. No tool installation was required.
2. **Accumulator range:** a combinational SAT harness checks every K1..16 and lane count1/2/4/ceil(K/4). Each instance has separate symbolic inputs. Assuming a legal aligned prefix and exact product-range bounds for prefix/chunk sums, AW=`15+ceil(log2(K+1))` addition matches signed32-bit addition. These are conditional arithmetic lemmas, not proofs that every implementation state satisfies those assumptions.
3. **Combined bounded checks:** actual folded control/register/routing/accumulation RTL, with only multiplication abstracted, is compared to an independent accepted-input/product snapshot. Assertions check prefix sums, output values, occupancy, aligned position, stall stability and exact progress age. Useful bounded passes cover shiftadaptive K1/K4 and fold2/shift2 K5. Larger combined cases timed out or exhausted the3GiB address-space limit.
4. **Routing/control split:** retain actual operand selection/shift registers and control; eliminate arithmetic-value assertions from this check. Snapshot assertions verify actual a/b at the multiplier cutpoint, including tail gating. Ghost occupancy/age checks reject dropped/duplicated work and stalled-output control changes. K7/13/16 shiftadaptive passed bound10. The2×2 K6 tensor instance remained memory-limited.
5. **Local datapath transition split:** start from arbitrary candidate state with legal position/product-range assumptions when initially busy. Check actual chunk reduction, accumulator reset/accept/update/hold, output completion/sign extension/reset/hold across sampled transitions. Shiftadaptive K4/K13 and fold4 K16 passed bound4. These checks do not assume the accumulator's contents equal a mathematical prefix; the separate range lemma states the required prefix-bound premise.

The mathematical composition is that correctly routed products plus correct chunk reduction and exact-width recurrence maintain a prefix sum, and correct control emits the completed sum. **That composition has not been discharged as an unbounded machine-checked implementation theorem.** Bounded control checks do not establish the invariant for arbitrary future time. Multi-output tensor verification also remains incomplete. No SAT result changes reward eligibility or the existing `formal: not_run` field of ordinary simulation evaluations.

## Mutation and verifier audit

Seven original component mutants produced expected counterexamples: wrong operand, wrong shift amount, narrow accumulator, omitted final term, stuck position, reset-busy fault and expiring stalled output. A split routing mutant also failed as expected.

Mutation testing found a verifier weakness: a two-step local transition harness ended before sampled assertions became active. Three valid checks and two broken-update mutants returned solver SUCCESS at this inadequate bound. All five raw results remain archived and are **excluded from meaningful verification success**. A minimum-four-step guard now rejects such calls. At bound4, the three valid designs pass and both accumulator/output update mutants produce counterexamples. This is a correction to the verifier, not a discovered failure of the valid RTL.

There were32 SAT launches total, within the prospective cap:12 meaningful component successes (one combinational lemma and11 bounded sequential checks, including one preliminary development probe),10 expected-mutant counterexamples, five unproven resource-limited cases, and five insufficient-bound results. Raw solver SUCCESS count is17; reporting17 useful proofs would be incorrect. All new SAT scripts enforce `-set-assumes`. The initial split metadata erroneously marked operand routing checked even for datapath-only cases; the archive is unchanged, and the evidence summary corrects that field according to scope. Final code records it correctly.

The checks use30s SAT and45s tool-wall limits, existing90s CPU/3GiB address-space/64MiB-file limits, and no proof-outcome cache. Exact elapsed/CPU/memory observations and regression counts appear in the results summary (private evaluation artifact retained locally). No experiment-wide wall-time or throughput benchmark is implied by sums of overlapping evaluations.

## Sealed evaluator mechanism

See [the owner/candidate protocol](sealed-evaluator.md). An owner commits a nonce-salted private plan; all candidate source hashes are committed before scoring; each slot is consumed once; detailed results stay private until batch release. The corrected commitment binds runtime Python, contract documents and the four HDL-tool executable contents. Tool helpers/data files and host shared libraries/OS remain external dependencies.

The first four-slot mechanism test used a preliminary commitment that omitted contract documents and tool contents. Review caught that omission; a documented prospective budget amendment allows two additional valid/bad HDL evaluations with the corrected binding. Both versions and all receipts are retained. The interface integration uses `ff33f83dc924c76dadbe2d72a377c382d51a7c86`. Final runtime freeze `6cbd1b8b3501adc68a5add3d86be2de24a55f991` additionally rejects candidate-supplied formal assertions/assumptions and monitor-name collisions before any tool invocation; those guards have unit tests and do not change archived checked sources.

The same author controls both sides here. This validates a protocol, **not independent hidden evaluation**, authentication, a secure sandbox, or resistance to a malicious evaluator owner. New random seeds alone would not establish independence. Timing and final scores can convey information. The practical independent procedure requires a different evaluator owner, separately controlled files/execution, witnessed commitments and a predeclared finite submission budget.

## Final regression and costs

Final source and installed-wheel suites each pass127 tests. All20 arithmetic catalog designs and four valid controls pass RTL/mapped-netlist qualification; ten arithmetic attacks are rejected. All22 aggregate baselines pass, with21 behavioral faults, one invalid CDC action and22 artifact-path overrides rejected. Two prior winner replays preserve identical scored metrics and objectives. Sealed mechanism runs accept three valid sources and reject three bad sources across the preliminary/final batches; the final two-slot CLI test also rejects changes, overrides, replay and premature release.

The amended budget used42 quality evaluator calls and43 aggregate calls. Quality calls accepted29 and rejected13; summed reported elapsed time1511.939s, median19.517s, maximum120.896s. Thirty-two SAT launches sum266.732s of elapsed time. Available formal CPU samples sum143.840s, but15 early-exit cases lack that report; do not present it as total CPU consumption. Largest reported formal peak is2604.54 tool-reported MB; memory-limited runs stopped under the3GiB address-space limit. These overlapping/cached evaluations are not an experiment-wide wall-time benchmark.

The environment-disconnect notification did not block execution: a harmless command succeeded at09:25 UTC and jobs continued normally. No environment recreation or access workaround was used. Inactive v15 caches were archived and all bytes verified before removing raw copies; the retention manifest is included, and all original v15 delivery/evidence archives remain intact.

## Reproduction and next work

Use the delivered wheel, pinned tool packages and trusted host instructions. Source scripts require the installed package or `PYTHONPATH=.`. Outputs must be fresh directories. Private artifacts contain every historical `.ys` and generated source, including obsolete two-step harnesses; replay those files to reproduce historical outcomes. Current runners enforce corrected guards and may differ from those historical runs.

```sh
python -m unittest discover -s tests
python scripts/check_components.py --phase lemmas --output /tmp/new-lemmas
python scripts/check_components.py --phase valid --output /tmp/new-combined
python scripts/check_components.py --phase mutants --output /tmp/new-mutants
python scripts/check_components_split.py --output /tmp/new-split
python scripts/check_verification_regression.py --task dot --output /tmp/new-dot --cache /tmp/rl-cache
python scripts/check_verification_regression.py --task tensor --output /tmp/new-tensor --cache /tmp/rl-cache
python scripts/check_sealed.py --dot-only --output /tmp/new-sealed --cache /tmp/rl-cache
python scripts/check_quality_aggregate.py --output /tmp/new-aggregate --cache /tmp/rl-cache
```

The complete arithmetic/aggregate regression used the preliminary v16 wheel. The final correction touches only the new sealed module; all104 pre-v16 evaluator/runtime files are identical across both wheels. Final source/installed tests use the last wheel. The corrected sealed CLI integration uses the preceding interface wheel; its sealed module is byte-identical in the final wheel. The last change only adds component-source guards and has no effect on the evaluated sources. Source hashes and wheel hashes distinguish these stages; do not attribute all runs to one wheel.

Highest-value next task: establish an inductive single-output folded-controller/prefix invariant, with explicit reset/accept/complete/stall reachability checks and mutation controls for assertion activation; then discharge the multiplier-abstraction composition and scale to tensor outputs. This addresses the remaining correctness gap before another architecture family or policy-training claim. A genuinely independent heldout run needs a separate owner. Physical validation still needs an approved reproducible flow and technology data. No push, external upload or security change was performed.
