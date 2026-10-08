# V15: adversarial audit and repaired judge

This local checkpoint contains22 runnable families (six pilots and16 experimental). No family was added. The original ten tasks and subsequent expansions remain runnable. All22 default baselines passed functional simulation and synthesis/netlist regression in this checkpoint. This is a finite research suite, not evidence of silicon readiness, a trained design policy, or secure execution of hostile candidates.

The runtime was frozen at `9dedf9d8948a9c16b0fc5c15b0e10ef6498ab433` before fresh structural evaluations. The installed wheel matches104 source runtime files byte for byte;88 non-quality runtime files match v14. See machine-readable results (private evaluation artifact retained locally), frozen service constraints (private evaluation artifact retained locally), and the [prospective plan](stress-v15-plan.md).

## Demonstrated flaws and repairs

The immutable v14 wheel accepted five invalid arithmetic strategies: using future inputs exposed during invalid cycles; dropping commands after128; producing delayed duplicate outputs; expiring stalled responses; and hiding an18-bit accumulator behind an exact uniform-vector shortcut. Recorded rewards were respectively0.968172,0.977296,0.995124,1.348320, and1.257114. The first narrow-accumulator adversary had a signed-expression simulation/synthesis discrepancy and was correctly rejected; the repaired adversary exposed the actual weakness. Both attempts are retained.

V15 randomizes invalid-cycle data, exercises256/320-command unscored histories, includes nonuniform signed extrema and tail terms, tests long stalls and idle gaps, drains256 cycles, and resets immediately after acceptance, during work, and during a stalled completed response. Two independent Python arithmetic models check expected results. Scored arrival schedules, gates, formula and budgets are unchanged. Correctness failure always suppresses reward.

A valid two-cycle post-reset warmup was falsely rejected by v14; readiness now has a bounded wait. A valid four-walker TLB at cache capacity2 was also falsely rejected because memory tags were incorrectly limited by translation-cache capacity. Tags now use the actual16-tag interface limit. TLB stress warms each target ASID alone, changes its root generation, invalidates it, and checks both changed and unchanged contexts. Three generation transitions cover all four ASIDs; stale and context-confused root caches are rejected.

An initially intended valid extra-state control had its own duplicate-output bug and was correctly rejected. The repaired control passes. Its active8-bit counter increases mapped sequential cells20→28 and total cells2160→2189: state is charged. No netlist memory cell hides that counter. The original failed control and all interrupted/failed runs remain in private evidence.

## Final measurements

Ratios below are geometric workload/configuration aggregates relative to the fixed baseline. Cells and logic depth are generic synthesis proxies; cycles and latency are simulated workload measurements, not clock frequency, routed delay, energy or power.

| Fresh structural candidate | Cell ratio | Compact cycle ratio | Compact reward | Stream cycle ratio | Stream eligible |
|---|---:|---:|---:|---:|---|
| Dot shiftadaptive, K7/13 |0.449614|1.004024|1.331841|5.114606|No|
| Tensor shiftadaptive,3×3 K6 /4×1 K10 |0.410270|1.003521|1.355929|4.828318|No|

Compact latency-sum ratios worsen to5.241227 and4.304919 even while service gates pass. These are area savings under the stated sparse workload, not universally faster designs. For TLB capacities12/15, w4 has cell/cycle/latency/read ratios1.567773/0.295828/0.715740/1.045368 and reward1.102898; w4r4 has1.951951/0.260211/0.621397/0.897901 and reward1.091480. Extra hardware improves concurrency at an explicit area cost.

Fresh structural evaluation accepted12 designs across40 paired scored cases and16 extra arithmetic stress cases. These dimensions were not previously HDL-evaluated, and candidates/recipes were frozen first. The author knows dimensions and generators; this is not an externally blinded audit. No tuning followed these results. All per-design measurements (private evaluation artifact retained locally) are retained.

Final verification:

- 116 source unit tests and116 installed-wheel unit tests passed.
- 14 new adversaries rejected; four valid controls accepted;20 inherited mutants rejected.
- Installed library, CLI and JSON APIs:18 valid evaluations accepted, nine bad evaluations rejected,12 schema overrides rejected.
- 14 direct configurations passed, including12 older folded arithmetic configurations and TLB walkers at capacities2/3.
- 22 family baselines passed;21 behavioral faults and one invalid CDC action rejected;22 artifact-path overrides rejected. This is a regression slice, not repetition of every historical mutant matrix.
- Three exact fresh-winner replays matched all qualification fields except elapsed time using a second extraction of the pinned tools. Three v14-source/seed replays retained identical scored metrics and objectives under v15.

Costs:142 quality evaluator attempts, including14 preliminary calls with one interrupted run;43 aggregate calls;16 direct cases including two old-monitor probes. Among128 completed quality evaluations outside the preliminary batch, reported elapsed time sums2031.977s, median9.910s, maximum98.961s. Runs overlap and use caches; these are not experiment wall time or standardized performance claims. Disk-guard pauses resumed identical candidates/seeds. The initial large artifacts and obsolete caches were compressed and byte-verified before duplicate raw copies were removed.

## Formal and physical evidence

Twelve actual Yosys SAT invocations produced three bounded passes, five counterexamples and four timeouts/unproven results. Ten earlier frontend setup failures occurred before SAT; all remain recorded as unproven. Actual SAT-attempt elapsed time totals230.512s with45s solver and60s tool-wall limits per attempt. No timeout counts as success.

Passing fixtures: parallel full signedINT8 M=N=1,K1 at bound8; K2 at bound8; and a TLB root-cache fixture at bound24 with ENTRIES2, one walker/root slot, two ASIDs, one VPN, two alternating page generations, no permission faults, one outstanding client and one-cycle memory response. Arithmetic supports arbitrary reset/launch/output backpressure; progress checks force ready high. Initial first-edge reset is explicit; other nonreset state is unconstrained except HDL initializers. There is no unbounded or full-family proof. Folded arithmetic remains unproven.

**Assumption audit:** archived SAT scripts omitted `-set-assumes`. Intended stable-input assumptions were not enforced, making passing checks broader in that respect. Two attempted signed4-bit-domain checks were actually broader-domain timeouts and establish no restricted-domain result. The final runner includes `-set-assumes`, covered by a static unit check, but was not rerun after the SAT budget was exhausted. Reproduce recorded proofs with their archived `.ys` scripts; do not attribute them to an execution of the corrected runner. Counterexample VCDs, timeouts and setup logs are preserved. See formal results and correction (private evaluation artifact retained locally).

Physical evaluation is blocked: no OpenROAD/STA executable, ORFS platform or technology LEF/liberty PDK is installed. Generic Yosys FF libraries are insufficient. The retained candidate and10ns target SDC are prospective inputs;10ns was not achieved or tested. Physical metrics are null and physical_verified is false. No tools were installed and no network provisioning was attempted. Concrete assessment (private evaluation artifact retained locally).

## Reproduction

Use the delivery's pinned wheel and tool debs on a trusted Linux host. Extract debs locally and set `CHIP_RL_TOOLS` to the extracted `usr` directory. Python>=3.10 is required. Host shared libraries remain dependencies; this is not a hermetic OS image. Candidate execution needs a separate host/container boundary: the package supplies time/resource limits and source checks, not OS isolation. Keep evaluator files, constraints, private seeds and artifacts inaccessible to agents. Do not expose the full-history trusted-host bundle as an agent checkout.

The following are the final command forms used (choose fresh output paths). The private archive includes actual seeds, sources, scripts/testbenches and logs. Fresh runs draw new seeds; use replay for exact reproduction.

```sh
python -m unittest discover -s tests
python scripts/check_stress_attacks.py --output /tmp/new-attacks --cache /tmp/rl-cache
python scripts/check_quality_mutants.py --root /tmp/new-mutants --cache /tmp/rl-cache
python scripts/check_stress_direct.py --output /tmp/new-direct --cache /tmp/rl-cache
python scripts/qualify_quality.py dot --root /tmp/new-dot --cache /tmp/rl-cache --stress --architectures parallel tree shift4 shiftadaptive
python scripts/qualify_quality.py tensor --root /tmp/new-tensor --cache /tmp/rl-cache --stress --architectures parallel tree shift4 shiftadaptive
python scripts/qualify_quality.py tlb --root /tmp/new-tlb --cache /tmp/rl-cache --stress --architectures w1 w2 w4 w4r4
python scripts/check_stress_apis.py --output /tmp/new-apis --cache /tmp/rl-cache
python scripts/check_quality_aggregate.py --output /tmp/new-aggregate --cache /tmp/rl-cache
python scripts/replay_quality.py /path/to/private/winner --output /tmp/new-replay --cache /tmp/new-replay-cache
```

Installed API tests were launched from `/tmp` with the installed venv interpreter, absolute script paths and private artifact directory configured on the trusted host. Current `check_stress_formal.py` runs the corrected runner and may differ from recorded experiments; exact historical formal replay uses the archived scripts. Sources/tool hashes and run journals bind each result to its recipe. Vector files compressed after completion must be decompressed before direct testbench replay; source/seed replay regenerates them.

Next useful work is compositional or inductive verification of folded MAC state, followed by a genuinely independent hidden evaluation and policy-training experiment. Physical claims require an approved, reproducible flow plus licensed open technology data. More families would not address these evidence gaps. The earlier historical CRC failure remains unexplained despite later passing runs. Repository licensing remains owner-unselected; third-party provenance/reuse restrictions are documented in existing license notes. No external publishing or push was performed.
