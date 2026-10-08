# V18: concrete refinement of the K16 dot-product proof

This checkpoint closes the previously identified captured-product gap by a locally checked compositional RTL proof for **one exact instance**: `shiftadaptive`, signed INT8 dot product, K=16, M=N=1. Source SHA256 is `52ca6c8f59d1912ce918a468ef3e98fd11b0ea7b6813eb9fddec36e0d1fb1d93`. Parameters are part of the identity: the generator's source hash alone does not identify K. The first clock edge must apply synchronous reset; subsequent synchronous resets, input data, input valid and output backpressure are arbitrary. Reset cancels pending work. No input-stability assumption is introduced.

The result is a composition of local SAT lemmas and the completed v17 abstract induction, not a single monolithic concrete induction run. The trusted boundary includes Yosys elaboration/SAT, the Python D/Q extraction, structural substitutions, the artifact audit and the composition argument below. It has not received independent proof review or certificate checking. It does not prove all parameterizations or all dot-product designs, tensor tiles, mapped-gate equivalence, or physical implementation. Consequently the count of fully proved *families* remains zero. The existing suite still has 22 runnable families, six pilots and 16 experimental families.

## Proof argument

1. The v17 abstract model's reset base, seven transition cases and case-coverage lemma establish its controller, exact accumulated prefix, operand routing, result and backpressure invariants. Its seven phases have a reachable witness; that witness was replayed on concrete RTL with an independent arithmetic oracle. The abstract input products are constrained only to the signed INT8 product range. V17's one-step combinational range proof and exhaustive 65,536-pair RTL/mapped check discharge this restriction for real signed products.
2. The new extractor elaborates the actual original, instrumented concrete and abstract sources with K=16. It replaces each plain positive-edge DFF Q with a symbolic current-state input and exposes its D as next state. Unsupported state cells, clocks and inconsistent state aliases are rejected. The audit checks every extracted D/Q bit against raw Yosys JSON, unchanged combinational cells, named aliases, model/source/configuration hashes and absence of remaining sequential or assumption cells. The concrete and abstract models each contain 2,661 state bits; the original contains 335.
3. An unconditional reset lemma establishes `saved_product[j] = signed(snapshot_A[j]) * signed(snapshot_B[j])` from arbitrary pre-reset state. It leaves all current state bits free, including the started flag, and checks the consequence whenever the actual effective reset is active. Four non-reset capture/hold cases preserve this relation. Their boolean coverage is exhaustively checked under the already proved exclusion of simultaneous busy and completed states. Snapshot B uses the actual stride 32 layout, at bit 512+32*j; A uses bit 8*j.
4. Seven equivalence checks compare **every next-state bit**, ready/valid and valid output data between concrete and abstract transitions. The initial case leaves non-start state arbitrary and relies on mandatory first reset. Later cases substitute only established invariant relations: matching command/snapshot, saved products as the signed product function, idle/completed/busy control, and the busy phase's shifted operand registers. All remaining state is shared but arbitrary. The incoming abstract products are the concrete product function of current inputs. Structural substitution makes equal nonlinear expressions identical before SAT. No `assume` cells are used in these miters.
5. The abstract and concrete initial restrictions match. Induction on time now combines the preserved product relation with abstract/concrete next-state equality and the existing abstract invariant. A separate noninterference lemma compares all 335 original next-state bits and interface outputs against the concrete instrumented model, with ghost state unconstrained. This links the composed property back to the original RTL.

The exact v17 abstract source and harness match the newly extracted abstract model. The audit checks that `started` and the monitor's started bit alias the same state in the elaborated models. All elaborated multipliers have signed 8-bit operands and signed 16-bit results. The generator and audit are trusted-host tools, not agent-editable evaluator inputs, and these proof results never affect reward.

## Fixed budget and retained unsuccessful work

Exactly 16 SAT commands ran, at 20s solver/35s tool wall limits, with 90s CPU,3GiB address-space and64MiB per-file limits. There were 14 successful local checks, of which one weaker reset-preservation check is superseded and excluded from composition; 13 obligations qualify. Two deliberate negative controls produced counterexamples: corrupting a captured product and corrupting a captured operand. No timeout or unknown was counted as success. Sum of measured SAT-command elapsed time: 57.465s; longest 7.604s. There was no budget increase.

Seven preprocessing calls were used: five model extractions and two Verilog exports for linkage simulation. The first extraction-replay harness failed compilation because it indexed scalar `busy`/`ov` signals. Its files/logs are retained; the corrected run matched all 335 state bits for 1,200 cycles and 113 responses. Two additional concrete witness replays passed, including varied arithmetic inputs and all required phases/events. That is three successful HDL linkage simulations, one failed compile attempt, within the eight-attempt cap.

The earlier v17 monolithic concrete timeouts remain timeouts. The weaker v18 reset success is retained at `chip-rl-v18-cases/capture-0`; initialization instead uses `chip-rl-v18-reset` with zero bound state bits. Negative models and counterexamples are retained separately. No historical result has been upgraded retroactively.

## Integration validation

The final source and installed-wheel unit suites each pass 144 tests. All 109 previous runtime files are byte-identical to v17; the only added runtime module is `quality/refinement.py`. The frozen wheel is 0.18.0.

Final affected and aggregate counts, command timings and statuses are recorded in the machine-readable summary (private evaluation artifact retained locally). The fixed integration budget is 20 affected evaluator calls and at most 44 aggregate calls. The aggregate checks one default baseline and a meaningful fault (or invalid CDC action) for each of 22 families, plus artifact-override rejection. These targeted checks supplement the existing multi-design, structural-split and adversarial matrices; they are not a rerun of every historical experiment.

## Reproduction

Use the delivery's wheel and pinned local Icarus/Yosys packages; no new package or external service is required. The private evidence contains generated HDL, exact Yosys scripts, raw/extracted JSON, vectors, logs, counterexamples and the wheel. Keep it on the trusted host, outside candidate access. The prior v17 private archive is also required for auditing the full composition chain; it remains unchanged and separately checksummed. Exact historical replay uses the archived scripts, since the initial weaker reset harness intentionally differs from the final generator.

```bash
python -m unittest discover -s tests
python scripts/audit_refinement.py --artifacts /workspace --output /tmp/refinement-audit.json
python scripts/check_refinement_extraction.py \
  --model /workspace/chip-rl-v18-models/original --output /tmp/extraction-replay
# Replay a retained SAT obligation from its own directory:
cd /workspace/chip-rl-v18-reset
/workspace/tools/root/usr/bin/yosys -s proof.ys
```

Integration commands were run from `/tmp` with `/workspace/chip-rl-v18-venv/bin/python` to ensure the installed wheel was imported:

```bash
python /workspace/chip-rl-refinement/scripts/check_v17_regression.py \
  --task dot --output /workspace/chip-rl-v18-regression-dot --cache /workspace/chip-rl-v16-cache
python /workspace/chip-rl-refinement/scripts/check_v17_regression.py \
  --task tensor --output /workspace/chip-rl-v18-regression-tensor --cache /workspace/chip-rl-v16-cache
python /workspace/chip-rl-refinement/scripts/check_v17_regression.py \
  --task dot --only-extra --output /workspace/chip-rl-v18-regression-extra --cache /workspace/chip-rl-v16-cache
# check_stress_neutrality.py was run once each against v17-neutrality-dot/tensor.
CHIP_RL_TRACE_ROOT=/workspace/chip-rl-v18-aggregate-private \
python /workspace/chip-rl-refinement/scripts/check_quality_aggregate.py \
  --output /workspace/chip-rl-v18-aggregate --cache /workspace/chip-rl-v12-cache
```

Outputs must be fresh directories. Private replay journals record seeds; fresh evaluator runs generate fresh heldout workloads. Synthesis caches are keyed by source, parameters, recipes and tools, and each new evaluation still runs its workload checks. Area remains a mapped-cell proxy; service latency/throughput are workload measurements, not routed frequency or power.

## Remaining limitations and next work

Physical validation remains blocked: no OpenROAD, STA, PDK or platform is installed/configured. No physical verification is claimed and no workaround or installation was attempted. This checkpoint adds no new paid dependency, credential, external upload or push. Repository licensing still needs owner selection before public reuse; prior third-party license notes remain applicable. The historical isolated CRC failure remains unexplained despite later passing aggregate checks.

The next useful benchmark-development step is an **independently owned sealed agent-optimization study**: freeze task splits and service constraints, run a fixed-budget optimization policy on the strongest pilot families, compare against fixed baselines and alternate valid designs, and report heldout correctness, actual area/service improvement and evaluation/agent cost. Keep evaluator code, seeds and oracle artifacts outside the candidate's editable workspace. This requires independent ownership of sealed evaluation; the same developer cannot label another local replay independent. Further proof expansion should be driven by a concrete study failure or deployment requirement rather than another abstract-only campaign.
