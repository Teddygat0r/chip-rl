# V17: inductive folded-controller and prefix obligations

V17 adds source-bound inductive verification for selected **single-output** folded arithmetic instances. It changes no baseline RTL, reward, service gate, workload or ordinary evaluator. All106 pre-v17 runtime files are byte-identical. The suite remains22 families, six pilots and16 experimental. Physical validation remains blocked by missing OpenROAD/STA/PDK/platform; no permission workaround, external upload or push was used.

## V15 findings, concisely

The five reward exploits were (1) reading future input data while valid was low, (2) dropping work after128 commands, (3) delayed duplicate outputs, (4) expiring a response under prolonged stall, and (5) hiding narrow-accumulator overflow behind an exact uniform-vector shortcut. Repairs added randomized invalid-cycle inputs, longer histories/drains, long-stall checks and nonuniform extrema/tail terms.

The two overrestrictive checks rejected valid post-reset warmup and incorrectly tied TLB memory-tag capacity to translation-cache capacity. The repairs allow bounded warmup and use the actual16-tag interface. V15's five formal counterexamples were expected mutants—unsigned arithmetic, dropped work, duplicates, stale roots and wrong-context roots—not valid implementation failures. V15's missing `-set-assumes` error and v16's five insufficient-bound successes remain archived and are not upgraded by this work.

## Completed proof obligations

The checked RTL retains its controller, registers, input capture, shifts and arithmetic recurrence. The abstract model replaces exactly one typed signed8×8 multiply expression with a captured signed16 symbolic term. Accepted terms must lie in[-16256,16384]. The input snapshot and term vector remain fixed until the next accepted command. The invariant includes:

- One pending transaction exactly when busy or output-valid, with mutual exclusion.
- Aligned position and a bounded compute-step age; completion at the required final position.
- Correct reset establishment, ready/valid gating and captured command contents.
- Shifted operand bytes and actual multiplier operands equal the accepted-input snapshot.
- Accumulator equals the prefix sum; chunk equals its corresponding terms; completed data equals the total, with zero padding.

The predicate is combinational (`proof_ok`), avoiding sampled-assertion warmup. Reset is forced on the first edge; subsequent synchronous reset, input offers and output backpressure are arbitrary. No input-stability assumption is required by this model. Output consumption requires the consumer's readiness; no fairness assumption or unconditional retirement guarantee is claimed.

Yosys proved both the reset base case and temporal-induction step for five abstract instances: shiftadaptive K1/K4/K7 and fold2/shift2 K5, all M=N=1. These are inductive results for the stated **symbolic-product model**, not merely bounded passes.

For shiftadaptive K16, monolithic induction timed out. A partitioned proof subsequently completed:

| Obligation | Result |
|---|---|
| Reset establishes invariant, unrestricted candidate state before first reset | Pass |
| Invariant states fall into the enumerated cases | Pass |
| Unstarted transition | Pass |
| Idle transition | Pass |
| Completed/output-stalled transition | Pass |
| Busy positions0,4,8,12 | All four pass |

For each transition obligation, all initialization attributes are removed from the prepared model; the invariant and selected case are assumed only at time1, and the invariant is proved at time2. The unrestricted state-space coverage lemma prevents omitted cases. Thus these seven conditional transition lemmas plus the separate reset base establish inductiveness for this fixed abstract instance. They are not independently complete proofs on their own.

`induction_audit.audit_partition` requires identical source, parameters, invariant hash and case count, all cases exactly once, successful logs, and no remaining initialization attributes. It also requires a phase-covering witness and concrete replay. Parameter identity matters: the same parameterized RTL source hash can describe different K values. Unit tests reject mixed parameters, missing/duplicated cases, initialized transitions and contradictory controls.

## Reachability, linkage and vacuity

Eight existential SAT witnesses run24 cycles. They cover acceptance, compute progress, completion, output stall, resume, reset cancellation, a new command after cancellation and its completion. The K16 partition witness additionally visits all seven state cases. The witness is a finite existence check, not proof that every environment eventually supplies inputs/readiness.

Ten Icarus replays execute the original RTL and a concretized invariant monitor together. They check every recorded control sample, required events, output agreement, the concrete invariant, and results from two independent arithmetic oracles. Four replays replace the SAT data with signed extrema and deterministic varied data while preserving the control trace. These are finite linkage checks; they do not discharge an unbounded refinement theorem.

Product linkage has two separate results: a combinational SAT proof of the signed8×8 product range, and exhaustive testing of all65,536 operand pairs in both RTL and a Yosys-mapped netlist against Python integer arithmetic. An unsigned-product mutant fails the range proof. The checked typed expression is the multiplier cutpoint recognized in the source template. This establishes the primitive/range premise, not the entire stateful composition.

An intentionally contradictory host harness (`assume(0)`) produces apparent induction success but no reachable witness. That success is explicitly excluded. Candidate-supplied formal constraints, monitor-name collisions and hierarchy references are rejected before tools. This remains a trusted-host, recognized-template verifier, not an authenticated or OS-isolated proof service.

## Negative and unresolved evidence

Five deliberate mutants produce reachable **base-case** counterexamples in the abstract model: wrong operand, wrong shift amount, narrow accumulator, stuck position and reset-busy fault. The omitted-tail and stall-expiry mutants fail induction closure within the three-step limit but do not produce a reset-reachable base-case counterexample in that run. Their induction countermodels remain unproven as reachable traces. Both are separately rejected by concrete RTL/netlist evaluation.

The partitioned checker also rejects a reset mutant in the base obligation and a progress mutant in a transition obligation. These negative controls establish that the conditional checks are active; they are not failures of the valid implementation.

Three monolithic abstract runs (shiftadaptive K13/K16 and fold4 K16) and two direct **concrete** induction attempts (K1/K4) hit solver limits. The completed K16 partition does not erase the earlier timeout. No valid RTL defect was demonstrated. Regression additions cover verifier failure classification, parameter binding, case coverage, initialization, vacuity, waveform decoding and source-boundary rejection.

The unresolved obligation is an unbounded refinement/composition proof showing that the concrete captured products implement the symbolic-product transition model. The concrete attempts strengthen the invariant with each captured product's equality to its captured operand multiplication and remove symbolic product assumptions; both remain unproven. No full concrete-design, tensor-wide, all-parameter or silicon guarantee follows from the abstract proof. The earlier isolated CRC failure remains unexplained; another aggregate pass does not resolve that historical cause. Ordinary evaluator results continue to report `formal: not_run`; proof results never change reward.

## Costs, regressions and reproduction

The prospective budget used40 SAT commands and12 HDL linkage/witness simulations. SAT scripts enforce assumptions, use20s per SAT solve and35s per tool command, and retain the existing90s CPU/3GiB address-space/64MiB-file limits. Recorded command elapsed times sum246.626s, within the800s planned solver allowance even including preparation. Available CPU reports sum93.060s;15 early-exit reports are missing, so this is not total CPU consumption. Largest reported peak is681.23 tool-reported MB. Concurrent sums are not experiment wall time.

Final validation:138 source tests and138 installed-wheel tests pass. Ten affected valid designs pass; eight concrete mutants are rejected. All22 aggregate baselines pass, with21 behavioral faults, one invalid CDC action and22 artifact-path overrides rejected. Two replays preserve scored metrics and rewards. Twenty quality calls sum411.814s of reported elapsed time (median13.296s, maximum70.661s); aggregate uses43 evaluator calls.

The machine-readable summary (private evaluation artifact retained locally) records final source/installed tests, affected and aggregate regression, score neutrality, exact evaluator counts and costs. Formal evidence (private evaluation artifact retained locally) retains both recorded and audited statuses. The initial parser marked all failed commands unproven; the audit distinguishes the five logged base-case counterexamples from failed induction closure, and the final parser makes that distinction directly.

The runtime was frozen at the commit recorded in the completion manifest before installed integration. Existing hash-bound synthesis caches are reused; simulations run again. Source/seed replays confirm unchanged scored metrics and objectives. This author controls all fixtures: no independent hidden evaluation is claimed. The separate sealed-evaluator protocol and its limitations remain unchanged.

Install the supplied wheel and use the pinned tool packages on a trusted Linux host. Source scripts require the installed package or `PYTHONPATH=.`. Use fresh output paths. Exact historical reproduction uses the archived generated sources and `.ys` scripts; current generators include later audit/phase instrumentation and may produce a different model than preliminary runs.

```sh
python -m unittest discover -s tests
python scripts/check_induction.py --phase valid --output /tmp/new-valid
python scripts/check_induction.py --phase mutants --output /tmp/new-mutants
python scripts/check_induction.py --phase reach --output /tmp/new-reach
python scripts/check_induction.py --phase vacuity --output /tmp/new-vacuity
python scripts/check_induction.py --phase concrete --output /tmp/new-concrete
python scripts/check_induction_partition.py --output /tmp/new-partition
python scripts/check_product_link.py --output /tmp/new-product-link
python scripts/replay_induction_witnesses.py --artifacts /path/to/restored-private-parent --output /tmp/new-replays
python scripts/check_v17_regression.py --task dot --output /tmp/new-dot --cache /tmp/rl-cache
python scripts/check_v17_regression.py --task tensor --output /tmp/new-tensor --cache /tmp/rl-cache
python scripts/check_v17_regression.py --task dot --only-extra --output /tmp/new-extra --cache /tmp/rl-cache
python scripts/check_quality_aggregate.py --output /tmp/new-aggregate --cache /tmp/rl-cache
```

The local product-link runner clamps the reused v16 SAT wrapper to20/35s; recorded `.ys` files contain the actual20s solver option. A wrapper setup attempt used the wrong working directory and failed before evaluation; its log is retained and it consumes no SAT/evaluator call. The original v16 aggregate artifacts were fully byte-verified against their preserved archive before removing duplicate raw files to make room. All prior delivery archives, transport parts and assumptions/errors remain preserved.

Highest-value next task: discharge a one-step concrete-to-symbolic refinement relation for captured operands/products, then compose it with the completed abstract induction. Split the multiplier relation into smaller equivalence obligations to avoid the timed-out monolithic encoding. After that, extend from one output to tensor rows/columns. Independent evaluation requires a separate owner; physical validation still requires an appropriate approved flow and PDK.
