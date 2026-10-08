# V19: persistent bank-aware tile layouts

V19 adds one substantive experimental environment, `layout`, bringing the suite to **23 families: six pilots and 17 experimental families**. It targets the physical placement of logical tile words used by both producers and consumers. Existing scratchpad tasks choose arbitration with a fixed bank mapping; the permutation task moves register values. This task instead chooses a persistent, capacity-preserving address mapping whose effect is measured across stores, later reads, masks, repeated addresses and multiple access patterns.

This is a scoped accelerator component, not a CUDA emulator or a full GPU. The architecture is motivated by bank-conflict serialization and read broadcast described in [NVIDIA's CUDA Best Practices Guide, shared memory banks](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html#shared-memory-and-memory-banks). We authored the implementation and tests; no NVIDIA code, benchmark data or proprietary IP was copied. Existing Icarus/Yosys packages and their recorded license notes are unchanged. The repository still needs an owner-selected license before public reuse.

## Contract and implementation

An agent supplies synthesizable `candidate` RTL mapping `(row,col)` to a physical word address, parameterized by `ROWS,COLS,BANKS`. It must be a pure combinational bijection over all logical tile words into exactly the same number of physical words. Bank=`addr%BANKS`, slot=`addr/BANKS`. There is no extra padding, replication, variable capacity, extra bank port, input lane ID, request type, mask or data available to the mapper. Inputs outside the declared tile are unspecified. Netlist state, latches, unknown outputs, combinational cycles and changed ports are rejected. The shared source sanitizer remains active; use continuous assignments, `always @*` or `always_comb`. Manually enumerated sensitivities are rejected; the shared sanitizer also rejects the `(*` sequence in `always @(*)` as an attribute opener.

The immutable [HDL bank engine](../chip_rl/layout/engine.sv) captures one warp at a time and services one 32-bit word per bank per clock. It chooses the oldest pending lane in each bank. Same-address reads broadcast; stores serialize even when their address repeats, so the highest active lane's write wins. Masked lanes and store acknowledgments return zero. Empty masks still receive an acknowledgment. Responses remain stable while stalled, every submitted warp completes, and input changes after capture cannot change pending work. Reset clears memory and engine state. Warp-level overlap, multiple bank ports and scheduling-policy optimization are outside this task.

The host oracle keeps a logical memory independent of physical mapping and updates duplicate stores in lane order. A separate occupancy model predicts request latency from each bank's distinct reads or individual stores. It is cross-checked against an explicit queue scheduler in tests. RTL and mapped-mapper simulations execute the same fixed engine, compare every response and every request's cycle count, check output stalls and look for trailing duplicates. Before workloads, RTL and mapped logic enumerate every in-domain address forward and backward and must produce the same bijection. This is exhaustive finite mapping validation for the six configurations, not a formal-tool proof or universal parameter proof.

Mapper area is **actual generic mapped-cell count for one mapper**, with a 64-cell and 12-level limit. The row-major wiring mapper has zero cells; no artificial area floor is added. The engine instantiates one mapper per lane, but the reported count excludes replication, memory, arbitration and system wiring. Service cycles are measured from request capture to response production in HDL, excluding external consumer stalls. Wall cycles and active lane operations are also recorded. Neither metric is routed timing, power, SRAM area or measured GPU performance.

Correctness is required before reward. Every structural case must take at most 2x row-major's total service cycles. Eligible reward is:

```
clamp(geomean(row_major_service_cycles / candidate_service_cycles)
      / (1 + mean_mapper_cells / 64), 0, 4)
```

This is an explicitly priced mapper-overhead research objective. It does not estimate system PPA. The baseline is regenerated, synthesized and simulated under identical capacities and the exact same workload as each candidate. The controlled matrix uses one common replay seed across designs. Initial fill stores, overwrites, masked operations and final readback are included in score. Consumer stalls are identical within every paired comparison.

## Search space and observed tradeoffs

Three qualified designs are supplied: row-major, XOR bank swizzle and modular-add bank swizzle. The latter two preserve each row's bank-slot group while changing its bank. A fourth `rotate_xor` generator helper is available for exploration but is outside the qualified catalog; no validation claim is made for it.

The transpose objective emphasizes rows and columns but includes diagonals, small blocks, random gathers and broadcasts. The diagonal objective changes that fixed mix. A layout that spreads a column can collapse a diagonal into one bank. The following results use the controlled matrix; reward 1.0 is the paired row-major baseline.

| Split / objective | XOR reward | Add reward | XOR service speedup | Add service speedup |
|---|---:|---:|---:|---:|
| Development / transpose | 1.6160 | 1.7251 | 1.6917x | 1.9677x |
| Heldout / transpose | 1.6486 | 1.6036 | 1.7258x | 1.8291x |
| Reserve / transpose | 1.3751 | 1.3588 | 1.4288x | 1.4968x |
| Development / diagonal | 0.6700 | 0.9581 | 0.7014x | 1.0929x |

Development XOR uses three mapped cells at one logic level; modular-add uses nine cells at four levels. On heldout geometries XOR uses two/four cells, while add uses four/fourteen. Thus add wins the development transpose objective, but XOR wins after the heldout area penalty. Row-major wins the tested diagonal objective. These reversals establish a nontrivial optimization tradeoff; there is no claim that any supplied design is optimal.

Geometries `(rows,columns,banks,lanes)` are:

- Development: `(8,8,8,8)`, `(8,16,8,8)`.
- Heldout: `(16,8,4,8)`, `(16,16,16,16)`.
- Reserve: `(4,16,4,8)`, `(16,32,8,16)`.

Heldout/reserve include changed diagonal slopes as well as unseen shapes. They are **same-author qualification**, not independently owned or guaranteed-secret tests. No agent-training or independently owned study was run. Only the example reset/step rollout was exercised.

## Validation, hardening and bounded costs

The controlled matrix accepts 11 valid design/profile/split evaluations covering 22 shape cases, including all three catalog designs on all six shapes. Eight faulty sources are rejected: aliasing, out-of-range addresses, dropped high column bits, unmasked row XOR, padding, a latch, changed port width and a synthesis-divergence directive. The dropped-column design passes the narrow geometry before failing the wider one, demonstrating why a single default shape would be insufficient.

The installed JSON API passes its baseline, rejects an alias fault and seven invalid/boundary requests, and enforces the horizon. The executable example accepts XOR and add via `step`. An exact private-seed replay reproduces baseline metrics. A further manually incomplete sensitivity-list fault is rejected by the final source gate before any compiler call.

The initial runtime freeze is 58298fa; final runtime freeze is 20eda48. After the matrix, review identified the manual-sensitivity issue. The only changed runtime file is `layout/synthesis.py`, adding a restrictive source gate. The final audit verifies all 121 other runtime files byte-identical between wheels, the synthesis implementation and netlist inspector AST-identical after the entry gate, and all 11 previously valid sources accepted by the final gate. A final installed baseline run exactly reproduces every paired metric. The full matrix was **not rerun** after this gate addition, respecting the fixed simulation cap; initial and final recipe hashes are retained. Both wheels are preserved for exact historical reproduction. All 110 v18 runtime files remain byte-identical.

Final source and installed unit suites each pass 157 tests. A test initially assumed `always @(*)` was accepted, but the unchanged common sanitizer already rejects that spelling. The corrected test records this compatibility limit; the failed log remains. A script launch from the wrong working directory also failed before evaluation and is preserved. No failed correctness result or missing tool is counted as success.

Exact actual invocation totals, timings and aggregate results are in the summary (private evaluation artifact retained locally). The prospective caps were 40 new-task evaluator calls, 100 mapper synthesis calls, 240 simulation calls, 30s per new-task tool invocation, and 43 existing-family aggregate evaluator calls. Existing 90s CPU/3GiB address-space/64MiB file limits remain. No SAT campaign or tool installation was performed. No physical stage was available. The prior v18 proof remains unchanged and its exact-instance scope is not broadened by this new task.

## Reproduce

Install the final local wheel with the previously pinned Icarus/Yosys tools. Run from outside the checkout to verify installed behavior:

```bash
python -m chip_rl.layout.server --cache /tmp/layout-cache --objective transpose
# JSON lines:
# {"op":"reset","task":"layout","seed":19}
# {"op":"step","action":{"rtl":"module candidate ... endmodule"}}

python examples/layout_rollout.py --cache /tmp/layout-cache
python scripts/qualify_layout.py --output /tmp/layout-matrix --cache /tmp/layout-cache
python scripts/check_layout_api.py --output /tmp/layout-api --cache /tmp/layout-cache
python scripts/replay_layout.py PRIVATE_RUN_DIRECTORY \
  --output /tmp/layout-replay --cache /tmp/layout-cache
python -m unittest discover -s tests
```

Use a fresh output directory. `Evaluator(cache).evaluate(Config(), source, replay_seed=..., split=...)` is a trusted-host API; seed, split, output path, objective and constraints are not candidate action fields. Replay of the initial matrix's exact recipe uses the preserved pre-gate wheel. Final-gate comparison uses `scripts/check_layout_final_gate.py`; it explicitly permits the audited recipe change while requiring identical baseline metrics. `scripts/check_quality_aggregate.py` ran the 43 original-family calls separately.

Private artifacts retain exact candidates, Yosys scripts/netlists, complete mapping tables, logical requests, expected responses, cycle vectors, both-stage testbenches, streamed command logs and replay journals. Source/constraints/judge/workloads/artifacts must remain outside the candidate's editable workspace. Time limits and source gates do not constitute an OS sandbox for untrusted compilers. Previously archived raw duplicates were removed only after streaming/hash verification against retained archives; preservation manifests describe restoration.

Physical evaluation remains blocked by missing OpenROAD/STA/PDK/platform. No paid service, external upload, new credential, security configuration change, publishing or push occurred. This checkpoint establishes a small runnable search space and measured architectural tradeoffs, not silicon readiness or demonstrated agent generalization.
