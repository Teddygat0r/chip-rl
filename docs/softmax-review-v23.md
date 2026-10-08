# V23 review-guided softmax validation

Final runtime b60b698 passed 182 source and 182 installed unit tests, 35 valid evaluations across 91 shape-workload cases, and rejection of 28 bad designs. Seven distinct valid designs passed all five splits. Final aggregate, API, example, replay and independent recorded-output checks also passed. Historical pre-readiness and budget checkpoints remain preserved separately.

This checkpoint strengthens the existing softmax environment and retains24 runnable families. The supplied adversarial specification was independently authored, then made visible to the implementer. Execution and fixes here are local and visible; this is not hidden or independently executed validation. [Frozen-v22 findings](softmax-review-v23-frozen.md) were committed before runtime changes.

## Contract resolution

Inputs are128 bits holding16 signedINT8 logits at scale1/16, domain[-8,7.9375], plus a16-bit mask. Outputs are256 bits holding16 unsigned16-bit fields at scale1/4096, each0..4096. Structural N controls the low active lane region; unused and masked lanes must output exactlyzero. Empty-mask rows require allzero output. Only candidate RTL is an action; ports, N, oracle, thresholds, resources, seeds and artifact locations remain trusted-host inputs.

Maximum absolute probability error is<=1/256 (16 output units), L1 error<=1/64 (64 units), and the active sum differs from4096 by at mostN-1 units. N is structural, not the number of active lanes. For example, a singleton4081 output is legal under N16's allowance15, but not N2's allowance1. The ideal is not rounded before threshold comparison.

Full correctness additionally requires nondecreasing outputs as logits increase, tied-logit output spread<=1 unit, and at most2 units of change under legal common shifts. Thus the review's equal-logit +16/-16, L1=64 and normalization=15 vectors pass their individual numerical bounds but fail the separate tie rule. +17/-17, L1=65 and normalization=16 fail their respective numerical gates. A clarification was requested; no instruction to remove the tie rule was received, so the fixed rule is retained and the arithmetic gate results are reported separately. Accepting all the requested equal-logit vectors would require an explicit contract revision.

Ordering follows acceptance edges, with exactly one ordered response per accepted request. Minimum registered latency is1. Accepted-to-consumed deadline is40*N+4 under the scored schedule's periodic consumer stalls (three blocked cycles per eleven). Longer unscored output-hold probes check retention without applying that scored consumption deadline while the consumer intentionally holds ready low. Reset cancels work on one asserted edge; ready and valid must be suppressed while reset is asserted. Resource caps remain25000 generic mapped cells and160 mapped logic levels.

Approximate candidates and transformed inputs are checked against their numerical contract, not forced to match the baseline's output bits. The <=2-unit shift rule is retained. Exact bit/cycle agreement remains required between RTL and mapped simulation of the same candidate on the same input trace.

## Demonstrated defects and fixes

* Frozen v22 falsely rejected a legal ready-gated design because a retention probe required input acceptance while consumer ready was low. The final probe offers consumer readiness through acceptance, rejects unsolicited pre-acceptance responses, then stalls to test retention. The identical source passes all five final splits; see [the backpressure finding](softmax-review-v23-backpressure.md).

* A `late449` mutant passed frozen v22 but corrupted outputs after448 accepted transactions. The same source fails a continuous1024-transaction N2 run while the baseline passes.448 was a campaign batch limit, not a legal hardware lifetime. Final qualification now includes uninterrupted histories beyond this limit.
* A reset qualified by `(!internal_valid || previous_reset)` passed frozen v22's three-edge stall reset. Final tests use single-edge resets at cold start, idle, busy and completed/stalled states, and after scored/profile transaction counts. Fresh-response and duplicate-drain checks follow resets.
* Packed output values with extra bits above256 or negative Python integers passed the old direct checker after masking. The checker now requires an actual integer in0,2^256), excluding booleans. Fixed-width HDL cannot emit those host encodings; this was a host-boundary defect.
* Duplicate or malformed OUT lines, mismatched transaction counts and embedded PASS substrings passed portions of the old parser. The final parser requires ordered unique fixed-width records, one count-consistent metrics record, cancellation/post-reset results and a final drain marker. A narrowly matched Icarus finish footer is allowed. Missing outputs, unknown values, malformed records, unsuccessful tools and timeouts fail closed. Candidate-mediated log forgery was not demonstrated: the RTL source filter forbids printing and file/system tasks.

The first strict-parser preflight rejected Icarus's legitimate `$finish` footer. That failed attempt is retained. Its fix permits only the known anchored footer after successful drain; arbitrary extra text remains rejected. Numerical tolerances, cell/depth budgets and per-tool timeouts were not relaxed.

## Coverage and stage boundaries

The original development N4,8; heldout N3,7,16; reserve N5,12; and audit N1,2,6,9,15 splits remain. A review workload at N16 adds3601 rows: three protocol-probe rows plus3598 numerical vectors. It covers all511 signed two-lane differences, representative legal offsets and lane pairs(0,1)/(7,15), every mask cardinality0..16 at16 rotations, ties and signed/masked extremes. This covers representative positions for each difference, not every possible mask/logit vector.

Scored simulation remains batched at448 transactions, preserving complete shift groups. New unscored uninterrupted1024-transaction histories are required at every qualified N; N2,4,16 also run449- and512-transaction histories. N<=4 histories are fully active. Larger mapped histories mix empty-mask rows with nonempty probes around127/128,255/256,447/448/449,510/511/512/513 and1022/1023, followed by one-edge reset and fresh-work checks. Larger N also runs a fully active1024-transaction **RTL-only** trace. That trace's mapped stage is explicitly absent; it is not reported as mapped verification. These histories do not alter scored cycle totals.

The acceptance-edge scoreboard, invalid-cycle poison, stable pending outputs, single-edge resets and response drains remain active. Shift groups now compare every pair within a group, rather than relying on chained adjacent comparisons. Lane-permuted workloads use numerical/orientation checks without imposing bit identity between distinct approximate designs.

An independent numerical implementation uses a140-digit Taylor exponential at argument/256, eight squarings and120-digit normalization. It calls neither Decimal.exp nor math.exp and shares no candidate approximation tables. The frozen3598-vector comparison differs from the production80-digit oracle by at most4.1808873286227738345875461835183671400187e-80. A final recorded-output cross-check of the fine baseline and nearest-rounded variant passed all gates on 7202 rows, under a durable 20000-row reservation ledger. No full65536-pair sweep is repeated.

## Exact-final measured results

All values below are generic mapped synthesis and workload-cycle proxies, not routed timing or measured power. Ratios compare each candidate with the fixed paired baseline; histories are unscored.

| Design | Split | Cells ratio | Depth ratio | Cycles ratio | Reward | Maximum scored absolute error |
|---|---|---:|---:|---:|---:|---:|
| full_radix4 | audit | 1.11077 | 1.25913 | 0.59056 | 1.029661 | 0.00026679 |
| full_radix4_ready_gated | audit | 1.11107 | 1.25913 | 0.59130 | 1.029409 | 0.00026679 |
| full_radix4_round | audit | 1.12994 | 1.25913 | 0.59056 | 1.025397 | 0.00016748 |
| full_radix4_tiny | audit | 1.10606 | 1.25913 | 0.59056 | 1.030720 | 0.00063520 |
| full_serial | audit | 1.00000 | 1.00000 | 1.00000 | 1.000000 | 0.00026679 |
| linear_radix4 | audit | 1.19843 | 1.90440 | 0.59056 | 0.969370 | 0.00218610 |
| linear_serial | audit | 1.08500 | 1.90440 | 1.00000 | 0.915993 | 0.00218610 |
| full_radix4 | development | 1.11028 | 1.23825 | 0.57540 | 1.035321 | 0.00024911 |
| full_radix4_ready_gated | development | 1.11057 | 1.23825 | 0.57540 | 1.035255 | 0.00024911 |
| full_radix4_round | development | 1.12971 | 1.23825 | 0.57540 | 1.031002 | 0.00012478 |
| full_radix4_tiny | development | 1.10587 | 1.23825 | 0.57540 | 1.036310 | 0.00031770 |
| full_serial | development | 1.00000 | 1.00000 | 1.00000 | 1.000000 | 0.00024911 |
| linear_radix4 | development | 1.19772 | 1.88906 | 0.57540 | 0.974213 | 0.00215664 |
| linear_serial | development | 1.08480 | 1.88906 | 1.00000 | 0.916823 | 0.00215664 |
| full_radix4 | heldout | 1.10672 | 1.23172 | 0.56685 | 1.038879 | 0.00029700 |
| full_radix4_ready_gated | heldout | 1.10700 | 1.23172 | 0.56825 | 1.038447 | 0.00029700 |
| full_radix4_round | heldout | 1.12551 | 1.23172 | 0.56685 | 1.034692 | 0.00020386 |
| full_radix4_tiny | heldout | 1.10237 | 1.23172 | 0.56685 | 1.039858 | 0.00068054 |
| full_serial | heldout | 1.00000 | 1.00000 | 1.00000 | 1.000000 | 0.00029700 |
| linear_radix4 | heldout | 1.19154 | 1.88436 | 0.56685 | 0.977991 | 0.00219183 |
| linear_serial | heldout | 1.08221 | 1.88436 | 1.00000 | 0.917647 | 0.00219183 |
| full_radix4 | reserve | 1.10659 | 1.21875 | 0.56821 | 1.039603 | 0.00027899 |
| full_radix4_ready_gated | reserve | 1.10687 | 1.21875 | 0.56821 | 1.039539 | 0.00027899 |
| full_radix4_round | reserve | 1.12535 | 1.21875 | 0.56821 | 1.035424 | 0.00017737 |
| full_radix4_tiny | reserve | 1.10303 | 1.21875 | 0.56821 | 1.040403 | 0.00049915 |
| full_serial | reserve | 1.00000 | 1.00000 | 1.00000 | 1.000000 | 0.00027899 |
| linear_radix4 | reserve | 1.19056 | 1.87500 | 0.56821 | 0.978335 | 0.00215664 |
| linear_serial | reserve | 1.08158 | 1.87500 | 1.00000 | 0.918274 | 0.00215664 |
| full_radix4 | review | 1.09620 | 1.21875 | 0.56411 | 1.043022 | 0.00024537 |
| full_radix4_ready_gated | review | 1.09646 | 1.21875 | 0.56411 | 1.042964 | 0.00024537 |
| full_radix4_round | review | 1.11313 | 1.21875 | 0.56411 | 1.039216 | 0.00012348 |
| full_radix4_tiny | review | 1.09210 | 1.21875 | 0.56411 | 1.043953 | 0.00024537 |
| full_serial | review | 1.00000 | 1.00000 | 1.00000 | 1.000000 | 0.00024537 |
| linear_radix4 | review | 1.17317 | 1.87500 | 0.56411 | 0.983094 | 0.00215664 |
| linear_serial | review | 1.07440 | 1.87500 | 1.00000 | 0.919895 | 0.00215664 |

The final run initially rejected one valid baseline on a mapped-simulation timeout. The failed artifact is retained and never counted as a pass. A retry at two concurrent matrix workers passed with unchanged per-tool limits. Previously completed, hash-verified cases were preserved rather than repeated.

Cumulative v23 work, including frozen/pre-fix investigations and this retry: {"evaluator_calls": 140, "completed": 140, "incomplete": 0, "synthesis_calls": 22, "HDL_simulations": 3267, "scope": "Includes direct HDL controls as well as evaluator journals; excludes separately capped legacy/layout aggregate; archived/restored log duplicates counted once."}. Numerical reservation: 10944/20000 rows. The additional inherited/layout aggregate used its separately authorized 45-call allowance. Source and installed tests covered the same final runtime; all 138 wheel runtime files match the source. The host scheduler alone gained verified resume and configurable concurrency.

Exact evidence: [summary (private evaluation artifact retained locally), matrix (private evaluation artifact retained locally), aggregate (private evaluation artifact retained locally), and independent cross-reference (private evaluation artifact retained locally). The preserved budget checkpoint at commit 06fd88ad50e6d8375ddb07e4e04d9b740415ddbb remains historical and incomplete; this report supersedes its qualification status without relabeling its earlier evidence.

## Actual isolation

Read-only inspection found that the evaluator and tool processes use uid1000. That identity can read and write the trusted oracle/specification, private seed/results files and synthesis cache. Repository tooling does not create a separate uid or filesystem namespace. Directory modes0700 do not separate same-uid processes.

The source-only API rejects constraint/seed/artifact overrides. The sanitizer rejects `$display`, file reads, include directives, synthesis attributes and testbench hierarchy access in explicit probes. Fixed tool invocations, a reduced child environment, CPU/address-space/file-size limits and process-group timeouts are present. These controls restrict the RTL interface; they do not make this workspace a secure environment for an agent with arbitrary shell access. No security settings were changed.

## Reproduction

Existing Python3.12, Icarus12 and Yosys0.52/ABC were used. Set `CHIP_RL_TOOLS` to the existing extracted `usr` directory if necessary. Output directories must be new. Run installed tests outside the checkout.

```bash
python -m pip wheel --no-deps --no-build-isolation . -w /tmp/v23-wheels
python -m venv /tmp/v23-venv
/tmp/v23-venv/bin/pip install --no-index /tmp/v23-wheels/chip_rl-0.23.0-py3-none-any.whl
python -m unittest discover -s tests
repo="$PWD"
cd /tmp
/tmp/v23-venv/bin/python -m unittest discover -s "$repo/tests"
/tmp/v23-venv/bin/python "$repo/scripts/run_softmax_review_v23.py" --output /tmp/v23-matrix --cache /tmp/v23-cache --max-jobs 2
/tmp/v23-venv/bin/python "$repo/scripts/check_quality_aggregate.py" --output /tmp/v23-aggregate --cache /tmp/v23-cache
/tmp/v23-venv/bin/python "$repo/scripts/check_layout_api_v20.py" --output /tmp/v23-layout --cache /tmp/v23-cache
/tmp/v23-venv/bin/python "$repo/scripts/check_softmax_api_v23.py" --output /tmp/v23-api --cache /tmp/v23-cache
/tmp/v23-venv/bin/python "$repo/examples/softmax_review_rollout_v23.py" --cache /tmp/v23-cache
# Verify the accompanying manifest before extracting a per-case archive.
tar -xzf /tmp/v23-matrix/heldout-full_radix4-worker/heldout-full_radix4.tar.gz -C /tmp
/tmp/v23-venv/bin/python "$repo/scripts/replay_softmax.py" /tmp/heldout-full_radix4 --output /tmp/v23-replay --cache /tmp/v23-cache
```

For independent-reference reproduction, initialize a fresh JSON budget file with `{"limit":20000,"reserved":0,"stages":{}}`. Run `scripts/softmax_reference_review_v23.py --output NEW_DIR --budget BUDGET --stage frozen-reference` with the preserved v22 wheel, then `scripts/crosscheck_softmax_outputs_v23.py --matrix MATRIX --output NEW_DIR --budget BUDGET` on the final matrix. Stage reservations reject accidental repeated sweeps. The private archive also includes the exact fixed-path probe drivers and v22 wheel used for frozen checker/parser/HDL reproductions; restore their recorded paths or adjust them explicitly when moving executors.

The scheduler runs at most four evaluation jobs, or three while the existing-family aggregate runs. Per-case archives are hash-verified before raw duplicates are removed. The private checkpoint retains frozen acceptances, failed preflights, exact seeds, sources, testbenches, mapped netlists, logs and replay journals. The report's pinned hashes identify the frozen and final implementations. Do not expose private artifacts to candidate agents.

## Limits and next action

This is visible, review-guided finite validation, not a proof over all vectors, traffic histories, transforms or candidate programs. Long mapped histories at larger N are partly empty-mask; fully active large-N histories have RTL-only coverage. No OS isolation guarantee is established. Physical validation remains blocked by absent OpenROAD/STA/PDK/platform, and no new generalized formal claim is made. The inherited exact K16 v18 proof retains its original scope. V22 is preserved; nothing is pushed or uploaded.

The next useful action is to resolve the tie-contract mismatch explicitly, then obtain separately executed, independently authored higher-dimensional and long-history tests against a frozen version. A future untrusted-agent deployment also needs an actual process/filesystem trust boundary; that requires separately authorized infrastructure work.
