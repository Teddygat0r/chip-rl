# Quality checkpoint v14

The suite still has 22 families. This checkpoint adds experimental optimization profiles to dot, tensor and TLB. Earlier runtime files and evidence are unchanged; it does not promote the profiles to silicon-ready tasks or demonstrate an RL policy.

## Audit and resulting contract

V13 exhausted tiny catalogs. The old arithmetic balanced objective rejected slower shared multipliers; merely adding more search methods could not fix that task-design limitation. The new profile separates two useful service requirements before measurement: one-command-per-cycle offered traffic and a period-eight workload with a four-command burst. It rewards lower generic cell count only after correctness, per-case completion ratio and offered-latency gates pass. Limits are in the [prospective plan](quality-v14-plan.md), committed at `b8401b2`. No historical objective is changed.

The arithmetic port now represents up to 4x4 outputs and K<=16. A fully parallel elastic baseline accepts on every cycle when the consumer permits. Candidates include a balanced width-aware reduction tree, indexed operand sharing, and constant-shift operand sharing. Development synthesis exposed the mux cost of indexed sharing; shifting was added before the candidate freeze. Adaptive shifting uses ceil(K/4) lanes, chosen analytically from the period-eight requirement. Both traffic classes are always checked for functional correctness, even when one objective is ineligible. A correct slow implementation gets zero for the unmet service objective; no timeout counts as correctness.

TLB candidates vary one/two/four walkers and cache valid root pointers with ASID tags and invalidation. Page-table shape, permission checks, stalled responses, in-flight invalidation, reset cancellation, minimum cache capacity and external memory accounting remain mandatory. The extended oracle maps all sixteen capacity-probe VPNs valid. It retains an independently checked flat translation representation. This remains a small custom format, not an ISA MMU.

All profiles check behavioral RTL and Yosys-mapped RTL against independently computed results and require identical measured metrics. Icarus and Yosys/ABC provide simulation and generic cell counts. Logical depth is capped but is not timing closure. Neither routed timing nor power was measured. No new formal proofs or physical runs were performed.

## Split and candidate freeze

Candidate sources and selection were frozen at `64361b6`, before any new holdout HDL evaluation. The source hashes are in freeze.json (private evaluation artifact retained locally). Arithmetic development covers K4/8/16; tensor shapes are 2x2 and 1x2. New holdouts are dot K5/11, tensor 3x2 K5 and 2x3 K11. TLB development capacities are4/8 and holdouts5/9. Twelve selected design/profile runs cover forty paired configuration/workload cases. No candidate or service gate was changed after observing holdouts. A later fresh-seed development API negative control exposed a monitor coverage gap, described below. After repairing it, reserved TLB capacities11/13 were used for four newly frozen design/profile checks at `129b0ea`. The original5/9 evidence is retained; arithmetic holdout metrics reproduced unchanged under the repaired recipe.

These are genuinely new *structural* tests relative to earlier chip-rl RTL evaluations. The author knew their dimensions and generator. Fresh private workload seeds do not make this independently blinded research. The finite 26 task/design catalog (16 unique generic RTL sources) supplies examples and negative controls, not evidence that the task is a compelling learning challenge. Agents may edit arbitrary synthesizable RTL through the source-only API; no policy was trained or paid model used.

## Measured tradeoffs

Ratios below are geometric means of per-case ratios to each fixed paired baseline, on arithmetic holdouts K5/11 and the final reserved TLB capacities11/13. A ratio below1 means less of that measured quantity.

| Candidate | Cells | Completion cycles | Offered latency sum | Service result |
|---|---:|---:|---:|---|
| Dot adaptive shift, compact |0.5350|1.0035|4.5103|eligible, reward1.2775|
| Tensor adaptive shift, compact |0.4290|1.0030|4.6599|eligible, reward1.3446|
| Dot adaptive shift, stream |0.5350|4.8627|21.8264|correct, ineligible, reward0|
| Tensor adaptive shift, stream |0.4290|4.7194|17.9587|correct, ineligible, reward0|
| TLB four walkers |1.6208|0.2936|0.7118|eligible, reward1.0968|
| TLB four walkers + four root entries |2.0357|0.2592|0.6207|eligible, reward1.0828|

Root caching reduced memory reads to0.9014 baseline, compared with1.0543 for four walkers alone. The extra area lowered its weighted reward despite faster completion and fewer reads. Parallel reduction trees had modest cell improvements (about1.7%) without changing transaction timing. Sharing provides a larger area opportunity at a substantial latency/throughput cost; it is not universally better.

## Running the profiles

Install locally with `python -m pip install .`; ensure Icarus and Yosys are available, or set `CHIP_RL_TOOLS` to the extracted tool prefix described in the root README. No external service is used.

```sh
python -m chip_rl.quality dot --architecture shiftadaptive --cache /tmp/chip-rl-cache
python -m chip_rl.quality tensor --architecture tree --cache /tmp/chip-rl-cache
python -m chip_rl.quality tlb --architecture w4r4 --cache /tmp/chip-rl-cache
python -m chip_rl.quality.server --objective compact --cache /tmp/chip-rl-cache
python examples/quality_rollout.py dot --objective stream --cache /tmp/chip-rl-cache
python scripts/qualify_quality.py tensor --root /tmp/new-quality-run --cache /tmp/chip-rl-cache
```

JSON lines accept `{"op":"reset","task":"dot","seed":7}` and `{"op":"step","action":{"rtl":"..."}}`. Host selects the service objective at server launch; candidate actions cannot change objective, resources, artifact path, private seed or dimensions. Episode seed does not reveal evaluation seeds. Library `QualityEnv` has reset/step and the same source-only action. Observations include the complete port/protocol contract and development matrix. This is a fixed-profile suite: the documented development or heldout matrix defines its dimensions. Host dimension overrides are rejected, including library calls; resource limits apply to every case. An inherited, ineffective CLI entries flag was removed during the final API audit.

Evaluation reports both arithmetic objectives. Its top-level summary reward is compact; the environment's step reward uses the host-selected objective. For TLB it uses the inherited four-term memory objective. Formal/physical absence and lack of OS judge isolation are explicit. The schema protects trusted configuration at the API boundary; deploy the evaluator separately from an untrusted editing workspace. This checkpoint does not create an OS sandbox.

Exact replay is host-only:

```sh
python scripts/replay_quality.py /private/original-run --output /private/new-replay --cache /tmp/fresh-cache
```

The private journal retains seed, source, configuration, tool logs and the result. Replay compares every qualification field except elapsed seconds, including source/contract/recipe/tool/vector hashes, gates and metrics. Never mount those private archives in the candidate workspace. Full-history bundles are trusted-host deliverables, not an approved public release.

## Scope and retained failures

A late API check initially **failed**: one fresh-seed `stale_roots` negative control was accepted. Random traffic could evict or fail to reuse the retained root pointer. The captured seed/source/logs were preserved, and an unscored directed probe now forces a concrete root-pointer reuse after ASID invalidation. It selects a moved pointer with a demonstrably different stale leaf result; an unavailable coverage precondition rejects evaluation. The captured survivor now fails on a result mismatch. All twenty negative controls and all TLB API paths were rerun. Candidate RTL, service gates and resource limits were unchanged. A paired valid-design replay verifies the probe adds four invalidation pulses but changes no scored metric, eligibility or reward. Reserved TLB capacities11/13 passed under the repaired recipe. This new failure is explicitly recorded; earlier negative-control success was insufficient.

The original180-call budget was exhausted at that finding. A prospective repair amendment allowed at most50 additional local calls, with unchanged per-tool caps. Actual total:230 new-profile evaluations, including five exact replays, twenty recipe-change requalifications, the captured-survivor recheck and one score-neutrality check. No experiment-wide wall-time limit was claimed. The old-family aggregate used43 evaluations plus schema checks. No paid service or new push occurred.

The first arithmetic smoke run failed because the reset driver sampled readiness before a combinational settle; the corrected run passed. The failed journal is retained. A first source-install attempt lacked setuptools in its clean venv; an offline wheel built with the already installed build backend resolved it. Development profiles were built incrementally; their early recipe hashes therefore differ. A final host-API audit rejected formerly ignored dimension overrides and removed the inherited CLI flag. This changed no candidate source, workload, gate or reward. The same heldouts and API checks were repeated under the final recipe; these repetitions are not independent blind tests. Both recipe versions and their exact replays are retained. The final installed evidence is the release reference. These are distinct from the historical v10 CRC reset anomaly, which remains unexplained and is not relabeled as resolved.

The new RTL and oracle code is original project work, with the TLB driver adapted from the repository's memory-v12 implementation. No third-party RTL was copied. Existing tool/reference license documentation remains applicable. The repository still has no owner-selected top-level license; this checkpoint does not invent one.

## Final validation counts

- 112 source and installed-wheel unit tests passed; all88 earlier runtime files remain identical.
- 26 development task/design pairs (16 generic RTL sources) accepted; final holdout selection covers12 pairs and40 paired configuration/workload cases. Original and reserve evidence are kept separately.
- 20 final mutants rejected; API checks accept18 valid runs and reject9 faults plus12 schema overrides. Arithmetic API checks used the host-guard recipe; TLB API checks used the repaired-coverage recipe. Eight arithmetic heldout results were requalified unchanged under the repaired recipe.
- All22 original-family JSON baselines passed, with21 behavioral faults, one invalid CDC action and22 artifact overrides rejected. This is a targeted aggregate regression, not a repetition of the older671-fault matrix.
- Five exact replays across recorded recipes passed using a separate extraction of the pinned tools. Final reserve TLB replay includes all qualification fields except elapsed seconds.
- New formal proofs:0. Physical runs:0. Trained policies:0. No OS judge sandbox is provided.

See the machine-readable summary (private evaluation artifact retained locally) and commands (private evaluation artifact retained locally). All230 attempts, including the initial false positive and driver failure, remain in the private evidence. Their counts must not be presented as230 independent valid designs.
