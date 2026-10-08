> Historical v1 evidence; superseded by [v2 remediation](remediation.md).

# Final v1 audit

This is an independent-style, adversarial **self-audit**, not third-party verification.
It inspected RTL, Python oracles, workload generation, action handling, tool execution,
packaging, and the original requested scope. The original v1 remains in Git history.

## Findings and fixes

1. The original alternates changed only shared buffer depth. They were valid and
   measured, but weak evidence for task-specific exploration. `alternates.py` now
   supplies a distinct implementation strategy for each kernel. Some strategies
   synthesize to similar logic; the reward includes buffering changes and does not
   claim kernel-only improvement.
2. Original heldout tests largely reused the training generator with a different
   seed. The new `challenge` split comes from the separately written `heldout.py`;
   it does not import/call the training generator. Original `heldout` behavior is
   retained for replay. Both generators still use the same task specification and
   Python oracle; there is no claim of independently authored specification or
   independent second oracle for every cycle.
3. External observations referred to a checkout-relative contract file. Contract
   text is now packaged and included directly in observations. A JSON-lines server
   exposes reset/step without permitting paths, tool commands or constraint changes.
   Installation and real rollouts were exercised outside the repository.
4. Added dirty-state reset probes before bulk initialization, including rejection of
   missing-memory-reset mutants. This prevents initialization writes from masking
   reset faults in accelerator/gather tests.
5. The seed was previously interpolated into trusted HDL without strict type
   validation. Exposing reset through JSON made string-seed injection a concrete
   API risk. Seeds now require exact unsigned-32-bit integers; numeric configuration
   and workload counts also have type/bound checks. Regression tests verify malformed
   seeds cannot reach an HDL tool, and the installed server rejects them. No exploit
   that writes a file was executed. Valid integer-seed qualification results are
   unaffected by this guard.
6. Expanded rejection of hierarchy access and bind/import/package/program/primitive/
   config/library/disable constructs. No direct file I/O path was found through the
   accepted RTL syntax. Compiler binaries still run under the evaluator's OS user;
   this is not a hardened compiler-exploit sandbox. Use a separate identity/container
   for adversarial deployments, and keep challenge logs private.

Additional cache address coverage walks all 256 default-size indices and isolates
each of the six tag bits: 10,752 commands pass on both baseline and alternate RTL.
Index-truncation and high-tag-truncation mutants are rejected. These are additional
RTL-level unit probes; the 40-case aggregate separately supplies synthesis/netlist
coverage.

## Scope assessment

All ten are distinct, runnable synthesizable block-level contracts with independently
written Python state transitions and hand-calculated oracle tests. The RTL generator
never executes the Python oracle to implement the candidate. A common transport shell
is shared; the task state/operations are distinct. “Independent” means independent
implementation of the specified transition function, not a separately authored spec.

- Elastic: real ready/valid word transport with backpressure. The alternate globally
  stalls its shift pipeline rather than using individual elastic enables.
- Dot: exact K signed INT8 products into signed 18 bits. No quantizer/saturation stage.
- Scratchpad: four proposals, four banks, 256 total 32-bit words; one RR grant per bank.
  The host retries losers. No buffered request fabric or SRAM macro integration.
- DMA: 1D/2D four-byte beat address/mask/final generation, explicit delayed acknowledgements,
  16-bit wrapping addresses. No bus master, outstanding-ID tracking or data mover.
- Router: five-input/five-output RR grant and payload selection with per-output readiness.
  No ingress queues, packet framing, credits or multi-hop network.
- Scoreboard: one issue decision across four context proposals, 16 register reservations,
  RAW/WAW checks and 1..8 logical-tick timers. No SIMD execution datapath or ISA decoder.
- Tensor: signed 2x2 output tile, K=4, four exact 18-bit reductions. No systolic array,
  local tiling controller or external operand stream.
- Accelerator: command-controlled shared scratchpad, single-word copy, read/write and dot
  operations. This is the narrowest match to the original integrated-subsystem ambition:
  it has no autonomous descriptor controller, concurrent DMA/compute or separate bus.
- Cache: direct-mapped 1KiB with four-byte lines, write-through/no-write-allocation,
  one pending miss and host-supplied refill. No coherent hierarchy or external bus engine.
- Gather: four irregular reads with all mask patterns, stable compaction and duplicates.
  No variable-length sparse stream or scatter engine.

Logical command ticks are intentionally distinct from physical clock cycles. Measured
latency is useful command-to-response latency, not complete-program or memory-system
latency. Generic cell counts are not physical area; none of these results establishes
clock frequency, routed timing, power, or silicon readiness.

## Measured matrix

Every row: **4/4 valid cases** (baseline, task-specific alternate, separate challenge, structural challenge) passed RTL simulation + synthesis + netlist replay; **3/3 mutants** rejected; **1/1 external installed-package rollout** passed. Reward baseline is 1.0000. The common three mutants comprise the listed semantic fault, dropped work, and stalled-output corruption.

| Family | Baseline → alternate cells | Measured alternate reward | Challenge transactions | Task-specific alternate | Semantic fault rejected |
|---|---:|---:|---:|---|---|
| elastic | 81 → 40 | 1.2346 | 128 | globally stalled shift pipeline instead of per-stage elastic enables | lost high data bit |
| dot | 2183 → 2139 | 1.1164 | 128 | explicit balanced product reduction instead of loop-carried accumulation | unsigned products |
| scratchpad | 104543 → 104010 | 1.1115 | 128 | reverse overwrite priority encoder instead of forward first-match encoder | unfair fixed priority |
| dma | 789 → 595 | 1.1711 | 6651 | incremental current/row-base addresses instead of row-times-stride multiplication | ignored row stride |
| router | 12805 → 12282 | 1.1216 | 128 | reverse overwrite destination arbitration instead of forward first-match | unfair fixed priority |
| scoreboard | 4698 → 4324 | 1.1286 | 128 | reverse overwrite ready-context selection instead of forward first-match | ignored RAW hazard |
| tensor | 8678 → 8526 | 1.1159 | 128 | four separately unrolled balanced reductions instead of nested accumulation loops | unsigned products |
| accelerator | 35998 → 35933 | 1.1310 | 640 | balanced scratchpad-product reduction instead of loop-carried accumulation | negated reduction |
| cache | 31576 → 33211 | 1.1183 | 1727 | one-hot decoded tag/data access instead of dynamic indexed read/write ports | lost hit-write update |
| gather | 44538 → 44284 | 1.1200 | 384 | parallel prefix-popcount destinations instead of a running compaction counter | reversed gather addresses |

Totals: **40 valid / 30 rejected mutants; 34 unit tests; 10 external rollouts**. Functional/synthesis/netlist families: **10/10**. Bounded formal: **1/10**, elastic width8 over 12 cycles (baseline and new alternative pass; corrupt control does not). Unbounded formal: **0/10**. Physical: **0/10**. OpenROAD/ORFS/PDK remain absent; optional integration is unvalidated.

The aggregate qualification command exited **0**. All 70 saved input streams, expected streams and candidate hashes were rechecked against current code after adding the numeric-input guards. The old 23-test/retiming-only qualification is preserved under `artifacts/release`; current evidence is under `artifacts/audit`. Full numeric-input and installed-JSON-server regressions passed after the fix.

## Reproduce and retrieve

```bash
python -m unittest discover -s tests -v
python -m chip_rl.suite --output /tmp/fresh-audit
python -m pip install --no-deps --no-build-isolation .
# From a different directory, using the installed package:
printf '%s\n' '{"op":"reset","task":"elastic","seed":17}' '{"op":"step","action":{"stages":2}}' | python -m chip_rl.server --horizon 1
```

The source repository is `/workspace/chip-rl` **in this cloud executor**. The portable
`/workspace/chip-rl.bundle` contains the full Git history and committed evidence. Retrieve
that file through this cloud task's file access, then on the destination machine:

```bash
git clone -b work /path/to/chip-rl.bundle chip-rl
cd chip-rl
./scripts/install_tools.sh "$PWD/.tools"
source .tools/env.sh
python -m unittest discover -s tests -v
```

The bundle has a SHA-256 sidecar at `/workspace/chip-rl.bundle.sha256`. These are cloud
executor paths, not files implicitly copied into a parent executor. No external repo,
service or public destination was used for delivery.
