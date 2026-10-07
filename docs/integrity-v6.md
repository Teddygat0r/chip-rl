# Expansion batch 2: ECC, CRC and resource allocation

These three experimental environments extend the local v5 suite to 16 families:
six pilots and ten experimental tasks. V6 is local work; publishing is not authorized.
They add three distinct hardware problems, not aliases of earlier arithmetic or
memory tasks. Full bit layouts and semantics live in the installed
[contracts](../chip_rl/expansion/contracts.md).

- `ecc`: shortened extended Hamming SECDED encoding/decoding, with independent
  nearest-codeword reference checking. Width8/16 development; width12 structural.
  Baseline variable-index correction, static decoded correction, elastic pipeline.
- `crc`: stateful packet CRC-32/ISO-HDLC, checked against Python zlib. Start/restart,
  end, illegal continuation, running CRC, length and reset are observable. Parallel,
  four-bit and bit-serial RTL. Width8/16 development; width24 structural.
- `freelist`: simultaneous releases and up to K lowest-ID allocations, partial
  grants, invalid release atomicity, resource conservation and flush. Combinational
  and serial allocators. Depth8/32 development; depth16/24 and K3 structural.

Source-only actions cannot change host budgets, workload seeds or objective. Every
qualification checks identical candidate source at multiple configurations, paired
against a fixed baseline, in both Icarus RTL and Yosys/ABC mapped-netlist simulation.
These are latency-flexible transaction contracts, not fixed-latency equivalence.
The APIs expose immutable configuration, contract text, measured proxies and reasons
for reward ineligibility. Errors/timeouts cannot produce correctness success.

## Reference and reuse review (2026-10-07)

[OpenTitan primitive documentation](https://github.com/lowRISC/opentitan/blob/master/hw/ip/prim/README.md)
and its [SECDED generator](https://github.com/lowRISC/opentitan/blob/master/util/design/secded_gen.py)
provide public ECC design context. This implementation uses an original shortened
extended Hamming code, not an imported OpenTitan code or compatibility claim.
[Python zlib documentation](https://docs.python.org/3/library/zlib.html) specifies the
incremental CRC reference; zlib is a runtime standard-library dependency.
[BOOM rename documentation](https://docs.boom-core.org/en/latest/sections/rename-stage.html)
describes bit-vector free lists and allocation priority. This task omits rename maps,
speculative snapshots, branch rollback and architectural state.

No external RTL, source, vectors, benchmark datasets or document passages were copied.
All new project code uses the repository license. No OpenTitan/BOOM source dependency
is introduced. Existing Icarus/Yosys/ABC license and tool-installation notes apply;
Python/zlib retain their upstream licenses. No proprietary IP or paid service is used.

## Reproduction

Install the package and HDL tools as in the README. Run from outside the checkout
for installed-package API checks. Use fresh artifact paths:

```bash
python -m unittest discover -s tests -v
python -m chip_rl.expansion.suite --tasks ecc crc freelist --output /tmp/v6-q --cache /tmp/chip-cache
python scripts/check_expansion_apis.py --tasks ecc crc freelist --output /tmp/v6-api --cache /tmp/chip-cache
python scripts/check_expansion_holdouts.py --tasks ecc crc freelist --qualification /tmp/v6-q/summary.json --output /tmp/v6-held --cache /tmp/chip-cache
python scripts/reproduce_integrity_formal.py --output /tmp/v6-formal
python examples/expansion_rollout.py --task ecc --cache /tmp/chip-cache
python examples/expansion_rollout.py --task freelist --objective area --cache /tmp/chip-cache
```

The scripts can instead use absolute paths from an installed virtual environment.
Development qualification uses host replay seed99173; APIs and structural checks
use fresh private seeds. Raw vectors/logs remain in private host artifacts. Committed
evidence contains summaries and hashes, not private workloads.

## Limits

This is finite qualification, not silicon readiness. Generic cell area and gate depth
are synthesis proxies; workload cycles/latency include offered arrivals and consumer
backpressure. There is no clock-frequency, routed timing, power or SRAM-macro claim.
No RL policy is trained. Public structural stress parameters are not a secret test
set or proof of learned generalization. Dedicated evaluator OS isolation remains
unavailable; use an external VM/account boundary for untrusted candidates.

ECC guarantees correction of one bit and detection of two; arbitrary multi-bit
corruption is not recoverable. CRC is an integrity checksum, not authentication.
CRC byte count wraps at16 bits; tested packet lengths are much shorter. Resource
allocation is not a complete CPU rename/rollback system. Serial implementations can
pass correctness while receiving zero reward for a performance-ineligible goal.

Bounded ECC formal is separate from default qualification. At width8 over eight
clocks, baseline and decoded variants passed symbolic 8-bit data, handshake signals and
zero/one/two injected errors. The pipeline attempt timed out at the fixed45s solver
budget and remains **unproven**. A correction-disabled mutant produced a proof
counterexample. Liveness and unbounded equivalence were not proved. Physical checks
remain **not run** because no usable OpenROAD/PDK flow is installed.


## Measured tradeoffs

Default mapped counts (generic Yosys/ABC cells; not physical area):

| Task/design | Cells | Logic levels | Balanced reward |
|---|---:|---:|---:|
| ECC baseline | 514 | 41 | 1.000 |
| ECC decoded | 298 | 28 | 1.120 |
| ECC pipeline | 546 | 21 | about 0.983 |
| CRC parallel | 578 | 13 | 1.000 |
| CRC four-bit | 519 | 7 | 0 (performance gate) |
| CRC bit-serial | 485 | 7 | 0 (performance gate) |
| Free-list parallel | 2357 | 72 | 1.000 |
| Free-list serial | 1192 | 63 | 0 (performance gate) |

Area goals still account for workload cost: CRC serial variants save cells but
score below1 because service slows considerably. The serial free list has area
reward above1, while balanced/latency goals reject its performance. ECC decoded
improves area at unchanged transaction behavior. The ECC pipeline lowers generic
logic depth but uses more cells and adds latency; no clock-frequency improvement
is inferred. Correct, goal-ineligible candidates remain marked tested_correct=True.
Catalog qualification covers mandatory development configurations; not every
architecture is guaranteed to meet the cycle budget at every host parameter.

Replayed example policies evaluate these hand-written alternatives through reset/step
and report rewards. They demonstrate API use and reward sensitivity, not RL learning.


Replay a retained private case with the original installed wheel/toolchain:
`python scripts/replay_expansion.py /private/task/design/case-0-0/candidate --output /tmp/replayed-case --cache /tmp/chip-cache`.
This checks evaluator/tool/source hashes, regenerates the exact recorded case and
runs RTL plus mapped simulation. It never labels a single-case replay as full
qualification. Keep the original private artifacts and their parent result.json;
committed summary JSON alone is not sufficient to reproduce the private workload.


## Final executed results

All8 new designs passed paired RTL/netlist qualification; all32 mutants were
rejected. Installed library/CLI/JSON checks passed24 valid pairs, rejected96 mutant
pairs and rejected9 host-setting override attempts. All4 frozen-source structural
cases passed. All61 unit tests passed, including in a clean checkout. Fresh-cache
checks of all3 families passed using the independent HDL tool installation.
All48 installed runtime Python/contract files matched implementation commit
`9fb7ab64ac30dd761648696d3a422aa3b7d357fb` byte-for-byte.

Regression: six earlier pilots passed18 baseline API checks and rejected219 mutant
checks. Four earlier cycle controllers passed13 designs and rejected28 mutants.
The v5 expansion passed27 valid API checks and rejected90 mutant API checks. These
are real default-coverage HDL executions, not mock/reset-only checks. The larger
memory API matrix took about30 minutes; each tool subprocess still had its normal
fixed resource limits. No coverage was reduced to finish the run.

ECC replay passed through the saved evaluator/tool/source identity gate. Formal
scope is as stated above:2 ECC implementations bounded-pass, pipeline unproven,
corrupt mutant counterexample. Zero unbounded proofs, physical evaluations or
trained policies. See [evidence](../evidence/v6/summary.json), per-family summaries,
tradeoffs, source hashes and [exact commands](../evidence/v6/executed-commands.txt).
Private replay artifacts remain outside Git under the recorded host paths.
