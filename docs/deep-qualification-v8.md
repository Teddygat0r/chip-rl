# V8: deeper qualification without adding families

The suite remains19 families. This iteration concentrates on ECC, request coalescing,
and histogram updates. None is automatically promoted from experimental to pilot.
The checks are independently implemented algorithms within this project, not an
independent third-party audit. Physical PPA and evaluator OS-isolation limits remain.

## Scope of the nine expansion families at the v7 checkpoint

All valid designs passed mandatory RTL and mapped-netlist simulation. All variants
were also checked through installed library/CLI/JSON APIs. Counts below describe
v7; v8 adds alternatives and adversaries rather than rewriting historical evidence.

| Family | Contract | Valid RTL | Mutants rejected | Main remaining gap |
|---|---|---:|---:|---|
| permute | Masked indexed register-vector selection with invalid indices zeroed | 4 | 10 | Larger structures and prolonged streaming |
| coalesce | Stable aligned-segment grouping with exact source lane masks | 2 | 10 | System-level memory benefit beyond the grouping block |
| retire | Fixed-cycle in-order retirement after independent completion, flush and tickets | 3 | 10 | Ticket wrap and wider control interleavings |
| ecc | Shortened extended-Hamming encode/decode with explicit error status | 3 | 10 | Full default-width exhaustive/formal coverage |
| crc | Stateful packet CRC, restart/end/error/reset and byte count | 3 | 11 | Long packet/count wrap and interrupted serial words |
| freelist | Atomic releases then lowest-ID allocation, invalid-free rejection and flush | 2 | 11 | Long histories and interrupted serial allocation |
| scan | Masked segmented inclusive/exclusive modulo32 signed prefixes | 3 | 10 | Broader arithmetic combinations; tree formal timeout |
| topk | Signed masked selection with descending values and stable index ties | 2 | 10 | Wider independent optimality checking |
| histogram | Ordered conflicting updates, old values and post-update queries | 2 | 11 | Wider arrays and memory-macro/physical behavior |

Why experimental: finite author-created tests, public stress dimensions, incomplete
formal coverage, no trained-policy evaluation, no physical flow, and no dedicated
OS sandbox. Bounded proof success covers its stated configuration/property only.

## Confirmed evaluator gaps and fixes

Using the frozen v7 wheel, three sources that ignore reset whenever input-valid is
asserted passed the old default evaluator: ECC, coalescing and histogram. They violate
the existing synchronous-reset contract. The shared transaction harness now applies
warm reset with input-valid asserted and a nonzero payload. The same source hashes
are rejected by the new evaluator, while all selected valid designs still pass.
Because this driver is shared, the pilot and other transaction-family regressions
must complete before the final v8 evidence is sealed.

A histogram source that silently stops producing outputs after1535 accepted commands
also passed v7's finite workload bounds. Histogram target-long bands now cover
2048..2304 random units, and a192-command sustained-collision prefix crosses16-bit
counter wrap even at K=2 before a clear. The unchanged30000-clock cap still applies.
The1535 cutoff is rejected, while baseline, serial and per-bin alternatives pass.
This closes a demonstrated hole; a still-later/adaptive backdoor remains possible
in finite testing and is not claimed eliminated.

## Independent deep checks

`chip_rl.qualification` does not import the primary task reference machines or
traffic generators. It uses:

- ECC: direct parity-equation codewords and a complete nearest-codeword table for
  the8-bit payload configuration. All8192 received words and256 encoding inputs are
  checked in actual RTL and mapped simulation, including ignored-bit noise.
- Coalescing: equivalence classes and earliest representatives, with all-to-one,
  distinct, boundary, hot-set, rotating-first and sparse traffic. New64-byte segments
  and two-lane configurations supplement the prior four/eight-lane development cases.
- Histogram: an event log that reconstructs counts rather than the primary mutable
  array. Long all-to-one collisions, counter wrap, invalid indices, clear storms and
  query/update ordering are checked.

The separate driver injects bounded consumer stalls and resets at different points
inside transactions, then checks post-reset responses/state. These deep tests assert reset with input-valid/output-ready high and alternating
zero/all-one payloads; they do not exhaust all reset-control combinations. It enforces exact in-order results, registered response bounds,
no extra output, completion deadlines, and RTL/netlist agreement. Cancelled work is
excluded from performance scoring. Every epoch retains the host cycle cap. Private
seeds/vectors stay outside Git; result summaries contain their hashes.

## New architecture comparisons and objectives

`representatives` coalescing computes first-lane representatives and membership masks
in parallel. Default generic cells fall from5333 to2004 and logic levels from101 to23,
with identical measured transaction cycles. Default balanced reward is about1.207.
This is measured logic mapping, not a frequency, routed area or power claim.

`parallel_bins` histogram accumulates per-bin deltas and reconstructs ordered old
values. It uses11874 cells versus9195, with41 generic levels versus74. It is a
shallower but larger alternative; it is not described as an area improvement.

Additional integration scenarios explicitly require coalescing service >=0.45
commands/clock at an offered period of2, and histogram service >=0.30 at period3,
with maximum offered-to-consumed latency64. The consumer waveform has approximately
0.62 available transfers/clock, so these offered rates are below its capacity. ECC
uses a saturated stream and requires >=0.50 commands/clock; no bounded offered
queue latency is asserted for that deliberately overloaded arrival schedule.
Existing cell/depth budgets remain. Ineligible correct designs score zero; feasible
ones receive a monotone measured area score relative to the paired fixed baseline.
These are explicit cycle-level scenarios, not physical timing constraints.

## Formal scope

A new ECC monitor tracks up to two outstanding responses and **asserts** that bound;
it does not assume a well-behaved DUT. This avoids the old16-entry monitor's state
explosion. Baseline, decoded and pipeline designs passed at8-bit payload width over
8 clocks with symbolic data, handshake signals, and zero/one/two injected errors.
A correction-disabled mutant produced a counterexample. A later baseline rerun
timed out at45s; a same-budget retry passed with byte-identical RTL, harness and
solver script. All attempts are retained, including the unproven timeout. Liveness and unbounded
correctness are not proved. The older pipeline timeout remains recorded as unproven
in v6; this new bounded result is separately identified. Scan's earlier tree timeout
is unchanged. No missing or timed-out stage is counted as verified.

## Reproduction

After installing the wheel and pinned tools, run from outside the checkout for
installed-package checks (use absolute script paths). Use fresh output directories:

```bash
python -m unittest discover -s tests -v
python -m chip_rl.expansion.suite --tasks ecc coalesce histogram --output /tmp/v8-q --cache /tmp/chip-cache
python scripts/check_expansion_apis.py --tasks ecc coalesce histogram --output /tmp/v8-api --cache /tmp/chip-cache
python scripts/deep_qualification.py --output /tmp/v8-deep --cache /tmp/chip-cache
python scripts/reproduce_deep_formal.py --output /tmp/v8-formal
python -m chip_rl.suite --output /tmp/v8-pilot-regression --cache /tmp/chip-cache
```

The deep command chooses a fresh host-private seed unless the trusted host supplies
`--seed`; agents cannot select it through environment actions. Retained hex inputs,
expected values, epoch metadata, both testbenches and tool logs make each run
replayable. A deep-test pass is not default qualification or pilot promotion.


## Next qualification gaps

Highest priority after this milestone: reset-control cross products and mid-transaction
reset for additional stateful families; long CRC packet/count wrap and retirement
ticket-wrap histories; broader independently authored structural distributions; and
formal coverage beyond the small bounded ECC configuration. The current deep harness
is another project-owned implementation, not a third-party audit. Dedicated OS
isolation and an installed physical design flow remain prerequisites for stronger
security and PPA claims. No new task family is needed to address these gaps.

To replay one retained deep configuration with the original driver and tools:
`python scripts/replay_deep_case.py /private/deep/coalesce/1-representatives --output /tmp/deep-replayed --cache /tmp/chip-cache`.
The command checks source/driver/tool/vector identities and verifies the recorded
verdict and cycle metrics. It does not label replay as full qualification.

## Final recorded results

The installed 0.8.0 wheel passed 71 unit tests, selected default qualification
(9 valid designs, 35 rejected mutants), selected library/CLI/JSON checks
(27 valid, 105 rejected, 9 constraint-override rejections), and independent deep
checks (18 valid design/configuration pairs, 32 rejected adversarial cases).
The other six expansion families passed 51 valid API checks, 186 mutant
rejections and 18 override rejections. The pilot regression accepted 16 designs
and rejected 71 mutants. These counts overlap across interfaces and are not
counts of independent designs. All positive HDL checks include simulation and
synthesis; the deep checks separately simulate mapped netlists.

A fresh clone passed the 71 unit tests and three selected HDL smoke checks using
an independent tool installation. A retained coalescer deep run replayed with
identical verdict and cycle metrics. The frozen wheel matches all 59 runtime
source files. Fixed-cycle controller results are inherited; no fresh v8 full
controller run is claimed.

All three selected ECC implementations have a successful small bounded-formal
attempt. The installed baseline attempt timed out and remains unproven; a
byte-identical retry at the same budget passed. Both attempts are retained.
There is no unbounded proof, physical validation, trained policy, or dedicated
candidate OS sandbox. No family is promoted by this milestone. Exact commands,
provenance, summaries and all formal attempts are in [v8 evidence](../evidence/v8/summary.json).
