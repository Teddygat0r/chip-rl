# V22 adversarial softmax audit

This checkpoint audits the existing softmax family and retains **24 runnable families: six pilots and eighteen experimental families**. V21 source, measurements and private artifacts remain preserved. No new family, training campaign, physical implementation or generalized formal claim is added.

## Exact contract and eligibility

| Item | Fixed rule |
|---|---|
| Input data | 128 bits, sixteen little-lane-order signed INT8 fields; lane i occupies bits8*i through8*i+7 |
| Logit interpretation | Q4, real value signed_integer/16, domain[-8,7.9375]; no clipping |
| Input mask | 16 bits, only lowN bits meaningful; inactive/unused data is ignored |
| Output data | 256 bits, sixteen unsigned16-bit fields; lane i occupies bits16*i through16*i+15 |
| Probability scale | 4096; each field in[0,4096]; inactive/unused outputs exactlyzero; all-masked output allzero |
| Numerical oracle | Direct exp(logit/16), normalized over active terms, with80-digit Decimal arithmetic; no candidate LUT reuse |
| Absolute error | Maximum lane probability error<=1/256, equivalent to16 output units |
| Total error | Sum of absolute probability errors<=1/64, equivalent to64 output units |
| Normalization | Active output sum differs from4096 by at mostN-1 integer units, using structural N, not active population |
| Ordering and ties | Larger logits cannot produce smaller outputs; equal logits differ by at most1 output unit |
| Common shifts | Legal common shifts of active logits may change any output by at most2 units |
| Clock/reset | Scalar clk/rst, synchronous reset cancels pending/stalled work on a single asserted clock edge; ready/valid suppressed during reset |
| Transaction ports | Scalar in_valid/in_ready and out_valid/out_ready; preserve order, exactly one response per accepted input, stable output under stalls |
| Response latency | At least one registered cycle; accepted-to-consumed deadline40*N+4 with the supplied bounded consumer stalls |
| Resource caps | <=25000 generic mapped cells, <=160 mapped logic levels; fixed interface, synthesis and source restrictions |
| Development structures | N=4,8 |
| Heldout structures | N=3,7,16 |
| Reserve structures | N=5,12 |
| Added audit structures | N=1,2,6,9,15; disjoint from the original splits |

Unused lanes and upper mask bits carry unrelated poison. Subtraction must represent max-minus-logit differences0..255; narrow signed arithmetic cannot change the specified numerical result. Internal rounding and underflow are allowed only within **all** gates. Requiring every small probability to be nonzero would contradict this approximation contract. Constant outputs are correct on particular degenerate rows (for example, uniform output for all-equal active logits, or zero for an all-masked row), but are not correct implementations across the task domain.

Agent actions contain only RTL source. N, interface widths, judge, numerical limits, workload seed/split, baseline, resource caps and artifacts are host-owned. Agent episode seeds do not select the private qualification seed. Reset evaluates the fixed `full_serial` baseline, and each step returns a measured evaluation and bounded episode status. Supported RTL is synthesizable and must pass the existing source filter, mapped interface/cell checks and both simulations. A source filter and subprocess limits are not an OS sandbox; candidate agents must not have write access to trusted code or private artifacts.

Correctness precedes reward. The unchanged loss is0.5*ln(cell ratio)+0.3*ln(cycle ratio)+0.2*ln(logic-depth ratio), measured against the fixed baseline on the same private workloads. Reward is1-0.5*tanh(loss); any failed, missing or timed-out stage earns zero. Generic cells and depth are synthesis proxies; simulation cycles describe the supplied workload, not routed frequency, physical area, power or GPU speed.

## Demonstrated gaps and fixes

Two same-author adversarial sources passed the complete v21 development evaluator with seed220022:

1. `mask_delta17` discards an exponential term only when the active mask is3 and the logit difference is17. The old random/directed mix missed that combination. The new deterministic sweep checks every difference0..255 under a two-active-lane mask and at both representable endpoints, with explicit shift-pair comparisons.
2. `single_edge_reset` qualifies reset with its previous-cycle value. Three-cycle reset pulses in v21 hide the failure to reset after one edge. The revised monitor issues a one-edge reset during normalization, then requires fresh work to complete without stale responses. Numerical constraints were not changed.

The preserved v21 commit is`7291b004dbccbb851a283cf61563b955c71cced8`. `scripts/reproduce_softmax_gaps_v22.py --old-python OLD_VENV/bin/python --new-python FINAL_VENV/bin/python --output NEW_DIR --cache CACHE` reruns both before/after cases; the private checkpoint includes the exact v21 wheel used.

Both old-checker acceptances retain exact sources, private seeds, tool logs, testbenches, netlists and results. The same sources are rejected by the revised evaluator. These are demonstrated finite workload/protocol coverage holes, not evidence that the Decimal arithmetic oracle was wrong. They also do not prove that the revised finite suite has no remaining blind spots.

The added workloads exercise tail differences around64,80,88,96,112,128,160,176,192 with one/many high logits, inactive extremes, rotating masks, ties and long boundary-heavy streams. This tests accumulated small-probability mass rather than checking each small term in isolation. Sequences exceed256 transactions on multi-lane structures, exposing counters or behavior that changes only late in a stream. Existing invalid-cycle poison, output stalls, canceled accepted work, canceled partial work, completed stalled work and duplicate-response drain checks remain active. RTL and mapped netlists must agree exactly on all scored output bits and cycles.

## Oracle and false-rejection audit

An independent120-digit Decimal calculation uses max-subtracted exponentials and compares all65536 possible signedINT8 two-lane pairs with the80-digit direct-absolute-exponential oracle. The maximum observed probability difference is5.2868035500310561617265482745520388189326e-80. This is a cross-check of two formulations and precisions, not a proof over arbitrary vectors.

Synthetic output controls distinguish the maximum-error, L1-error and normalization gates. They reject constant-zero, incorrect uniform probabilities, permuted dominance, inactive nonzero outputs and accumulated loss from dropping small terms. Equal uniform output, exact-floor output, all-masked zero and bounded tiny-tail underflow are accepted. An additional L1 control preserves total output sum and keeps each individual error below16units while exceeding64units of combined error. Another control violates maximum error while its total error is below64units.

The valid RTL catalog retains fine/interpolated exponential tables with one/two divider bits per cycle, and adds nearest-rounded radix-four division plus a deliberately bounded-underflow radix-four implementation. The latter zeros terms at delta>=160; this is meaningfully different from the fine table. A preliminary delta>=192 version was redundant with existing table zeros and was replaced before final qualification. Six implementations help test false rejections without forcing them to produce identical approximated probabilities.

## Reproduction

Use the packaged wheel with the existing Icarus12 and Yosys0.52/ABC toolchain. No new tools were installed. Run installed checks outside the source directory. Output directories must not already exist.

```bash
python -m pip wheel --no-deps --no-build-isolation . -w /tmp/v22-wheels
python -m venv /tmp/v22-venv
/tmp/v22-venv/bin/pip install --no-index /tmp/v22-wheels/chip_rl-0.22.0-py3-none-any.whl
python -m unittest discover -s tests
repo="$PWD"
cd /tmp
/tmp/v22-venv/bin/python -m unittest discover -s "$repo/tests"
/tmp/v22-venv/bin/python "$repo/scripts/audit_softmax_oracle_v22.py" --output /tmp/v22-oracle
/tmp/v22-venv/bin/python "$repo/scripts/qualify_softmax_v22.py" --output /tmp/v22-matrix --cache /tmp/v22-cache --archive-cases
/tmp/v22-venv/bin/python "$repo/scripts/check_softmax_api_v22.py" --output /tmp/v22-api --cache /tmp/v22-cache
/tmp/v22-venv/bin/python "$repo/examples/softmax_audit_rollout.py" --cache /tmp/v22-cache
/tmp/v22-venv/bin/python "$repo/scripts/check_quality_aggregate.py" --output /tmp/v22-aggregate --cache /tmp/v22-cache
/tmp/v22-venv/bin/python "$repo/scripts/check_layout_api_v20.py" --output /tmp/v22-layout --cache /tmp/v22-cache
# Extract a verified per-case archive before exact replay.
tar -xzf /tmp/v22-matrix/heldout-full_radix4.tar.gz -C /tmp/v22-matrix
/tmp/v22-venv/bin/python "$repo/scripts/replay_softmax.py" /tmp/v22-matrix/heldout-full_radix4 --output /tmp/v22-replay --cache /tmp/v22-cache
```

Two unbatched valid evaluations hit the45-second mapped-simulation timeout and were correctly rejected. The final simulator uses batches of at most448 transactions, retaining every workload row and keeping shift pairs together. Multi-lane batches remain longer than256 transactions. Each batch restarts the fixed bounded-stall schedule and rebases offered release times; scored cycles and latency sums add across batches. This changes workload scheduling, not numerical tolerance, resource caps or reward weights. All softmax matrix/API/example/replay checks were rerun on this final implementation.

The actual run uses at most four independent evaluation workers to keep the enlarged matrix practical, sharing only the locked synthesis cache. `scripts/softmax_audit_worker_v22.py SPLIT --root PATH --cache PATH` supports that layout; the development worker includes adversarial sources. `--labels` and `--worker-name` allow independent candidate jobs on the audit split. Completed results from the same final runtime can be retained in root/results.json; workers skip those cases. An interrupted case is preserved separately, not counted as a passing result. Each completed case is compressed and all content hashes are verified before raw duplicates are removed. Archive hashes and file manifests accompany each case. The scripts do not grant agent access to private data.

## Final results and measured tradeoffs

All177 source and177 installed unit tests pass. The final matrix accepts24 design/split evaluations across72 structural cases (six designs on twelve lane counts) and rejects22 bad designs. API qualification accepts its baseline, rejects its fault, and rejects16 invalid requests. The six-design rollout completes and both exact replays match numerical errors, measured metrics, recipe and tool fingerprints. This gives33 correct final softmax evaluations and23 rejected final bad evaluations including the API check. All23 inherited-family baseline regressions pass; their124 runtime files remain unchanged. Functional/synthesis evidence is retained for24 families; new formal/physical validations:0/0.

Ratios below are geometric means relative to the fixed fine-lookup serial baseline on each split. Maximum error is in probability units. The fixed maximum-error limit remains0.00390625; the L1 limit remains0.015625. Full absolute cell/depth/cycle measurements and per-shape numerical errors are in the machine-readable matrix.

| Split | Design | Cells ratio | Depth ratio | Cycles ratio | Max error | Reward |
|---|---|---:|---:|---:|---:|---:|
| development | full_serial | 1.0000 | 1.0000 | 1.0000 | 0.0002491 | 1.00000 |
| development | linear_serial | 1.0848 | 1.8891 | 1.0000 | 0.0021566 | 0.91682 |
| development | full_radix4 | 1.1103 | 1.2383 | 0.5757 | 0.0002491 | 1.03525 |
| development | linear_radix4 | 1.1977 | 1.8891 | 0.5757 | 0.0021566 | 0.97414 |
| development | full_radix4_round | 1.1297 | 1.2383 | 0.5757 | 0.0001268 | 1.03093 |
| development | full_radix4_tiny | 1.1059 | 1.2383 | 0.5757 | 0.0003177 | 1.03624 |
| heldout | full_serial | 1.0000 | 1.0000 | 1.0000 | 0.0002970 | 1.00000 |
| heldout | linear_serial | 1.0822 | 1.8844 | 1.0000 | 0.0021708 | 0.91765 |
| heldout | full_radix4 | 1.1067 | 1.2317 | 0.5669 | 0.0002970 | 1.03886 |
| heldout | linear_radix4 | 1.1915 | 1.8844 | 0.5669 | 0.0021708 | 0.97797 |
| heldout | full_radix4_round | 1.1255 | 1.2317 | 0.5669 | 0.0002039 | 1.03467 |
| heldout | full_radix4_tiny | 1.1024 | 1.2317 | 0.5669 | 0.0006805 | 1.03984 |
| reserve | full_serial | 1.0000 | 1.0000 | 1.0000 | 0.0002790 | 1.00000 |
| reserve | linear_serial | 1.0816 | 1.8750 | 1.0000 | 0.0021566 | 0.91827 |
| reserve | full_radix4 | 1.1066 | 1.2188 | 0.5682 | 0.0002790 | 1.03960 |
| reserve | linear_radix4 | 1.1906 | 1.8750 | 0.5682 | 0.0021566 | 0.97834 |
| reserve | full_radix4_round | 1.1253 | 1.2188 | 0.5682 | 0.0001774 | 1.03542 |
| reserve | full_radix4_tiny | 1.1030 | 1.2188 | 0.5682 | 0.0004991 | 1.04040 |
| audit | full_serial | 1.0000 | 1.0000 | 1.0000 | 0.0002668 | 1.00000 |
| audit | linear_serial | 1.0850 | 1.9044 | 1.0000 | 0.0021871 | 0.91599 |
| audit | full_radix4 | 1.1108 | 1.2591 | 0.5905 | 0.0002668 | 1.02967 |
| audit | linear_radix4 | 1.1984 | 1.9044 | 0.5905 | 0.0021871 | 0.96938 |
| audit | full_radix4_round | 1.1299 | 1.2591 | 0.5905 | 0.0001675 | 1.02541 |
| audit | full_radix4_tiny | 1.1061 | 1.2591 | 0.5905 | 0.0006352 | 1.03073 |

The faster-division result survives the stronger tests: fine radix-four division consumes56.7–59.1% of baseline workload cycles, with10.7–11.1% more generic cells and21.9–25.9% more logic depth. Reward improves2.97–3.96% across the four splits. Its numerical outputs match the serial fine-lookup design. This is a cycle/logic tradeoff, not a measured frequency or GPU-speed improvement.

Nearest rounding reduces peak error relative to floor division on every split, with a modest cell increase. Bounded underflow has higher error (worst observed0.0006806), but meets all gates and slightly reduces cells; its higher reward is legitimate under the prospectively fixed error contract. Interpolation continues to use more cells/depth and lose reward against the fixed baseline. No tolerance or scoring weight was retuned to favor any design.

Hardware campaign accounting:75 evaluator invocations,56 synthesis invocations and756 HDL simulation invocations, including failed and interrupted attempts, within80/160/800 caps. Four interrupted evaluations are retained and excluded from correctness totals. Two preliminary valid evaluations timed out and earned zero; no final valid evaluation timed out after batching. The existing-family aggregate consumed its separate43 evaluator calls and layout consumed2. There are no active evaluations at checkpoint completion.

See summary (private evaluation artifact retained locally), full matrix (private evaluation artifact retained locally), before/after gap reproductions (private evaluation artifact retained locally), oracle controls (private evaluation artifact retained locally) and inherited aggregate (private evaluation artifact retained locally). Raw private cases and journals are packaged separately from these summaries; compressed case manifests were verified before duplicate removal.

## Limits and next step

The tests, mutants and holdouts are same-author. There is no trained-agent study or independent adversarial evaluation. No new formal proof or physical validation is claimed; OpenROAD/STA and a PDK/platform are absent. The v18 exact K16 proof remains limited to that documented configuration. All v21 artifacts and source remain recoverable, and nothing was pushed or published.

The numerical sweep was inadvertently repeated when adding two synthetic gate controls:131072 pair checks exceeded the prospective100000-check cap. That excess is recorded, not hidden by counting unique inputs. Numerical tolerances and hardware resource limits were unchanged. Interrupted/preliminary HDL evaluations also remain in compute accounting and evidence.

A useful next step is independent, separately authored protocol and numerical adversarial evaluation against this frozen checkpoint, particularly reset timing and higher-dimensional error accumulation. That would address a stronger evidence gap than adding another same-author task family.
