# V10: long packet and retirement histories

## What these exercises teach

A CRC block computes a checksum as data arrives. Here the agent can trade a small
circuit that processes a few bits per clock against a larger circuit that processes
an entire word. The retirement queue keeps results in their original order even
when work finishes out of order. It resembles one small part of a processor; it
does not implement a processor's registers, instruction set or memory system.

An environment `step` submits a circuit edit. The evaluator then simulates many
hardware clock cycles; the agent is not manually issuing every data operation.
An environment `reset()` starts a new design episode, while the RTL's `rst` input
resets the simulated circuit during a test. These are different operations.

Both blocks use counters with a fixed number of bits. Like an odometer, a16-bit
counter goes from65,535 back to0. Short tests can accidentally reward a smaller,
incorrect counter because they never reach that boundary. This batch makes the
checker run long enough to expose that shortcut.

These are small component-level RTL exercises for future design agents. RTL is
code describing a digital circuit. A complete efficient accelerator also needs an
overall architecture, memory and communication systems, software/compiler support,
and physical implementation to determine real clock speed, power and layout.
This project has not trained an RL policy or demonstrated those complete-chip
results. Generic synthesized cell count is a cost proxy, not measured silicon area.

## Technical scope

This batch deepens CRC and retirement. It adds no task family. Six faults with
valid syntax were accepted by the frozen v9 evaluator: truncated CRC count,
saturating CRC count, CRC restart on count wrap, truncated retirement ticket,
saturating retirement ticket, and treating live ticket IDs as numerically ordered
across wrap. Their source hashes and old/new results are retained with evidence.

The CRC checker implements a bit recurrence independently of the primary model's
zlib call. It checks every response of a packet exceeding 65,536 bytes, followed
by invalid continuations, active-packet restarts and single-word packets. It checks
modulo byte count, checksum, final/error flags, tag and padding, output stability,
registered response latency, and complete draining. Private lengths/payloads/tags
and reserved bits vary. Structural width8/16/24 checks cover byte-count step sizes
including a width24 packet crossing wrap from65535 to2.

The retirement checker tracks unbounded allocation sequence IDs in an event
ledger, separate from the primary deque of mutable entries. Only interface IDs
are truncated to16 bits. More than66,000 allocations cross wrap with live work;
flushes bracket rollover without resetting tickets. A drain phase at exactly65,536 allocations makes high-ticket completions observable while the next ticket is zero. Generated frames include
out-of-order completion, duplicates, unknown tickets, full replacement, input-idle
completion, backpressure, final draining and reset after rollover. Timing phases,
lengths and payloads vary with a trusted seed. Callers do not retain stale
completions across reset or ticket reuse, as required by the existing contract.

## Explicit verification budgets

The default scored workload still has its host-specified `max_cycles` (at most
30,000). A separate mandatory long-history stage has a fixed host budget of900,000
CRC clocks or200,000 retirement frames. These are verification budgets, exposed
in task metadata; they are not agent actions or overrides of the ordinary workload
limit. Default workload checks run first. The long stage executes once for the
requested configuration, after the usual structural/default workload checks.
The separate structural long suite additionally exercises all three chosen
configurations per family. Every positive long check must pass actual synthesis,
RTL simulation and mapped-netlist simulation with identical vectors and metrics.
Tool timeout, unfinished history or divergence rejects qualification.

Long-history elapsed time and workload cycles do not enter the existing reward.
The finite workload area/latency objectives and fixed baselines are retained;
long-run cell/cycle ratios are separately reported as diagnostic measurements.
For retirement, `completed` counts retirements in the main long epoch; the trailing
reset probe is checked separately and excluded from that count.
This avoids rewarding a reset or truncation that merely shortens verification.
CRC baseline/nibble/serial and retirement baseline/shift/pruned remain distinct
valid architecture candidates. No routed timing, frequency or power is measured.

## Reproduction

Install the wheel and local pinned tools as in the README. Run installed checks
from outside the checkout with fresh result directories:

```sh
python -m chip_rl.expansion.suite --tasks crc retire --output /tmp/v10-q --cache /tmp/chip-cache
python /path/to/scripts/check_expansion_apis.py --tasks crc retire --output /tmp/v10-api --cache /tmp/chip-cache
python /path/to/scripts/qualify_long_histories.py --output /tmp/v10-long --cache /tmp/chip-cache
python /path/to/scripts/replay_long_history.py /private/v10-long/retire/0-baseline --output /tmp/replay --cache /tmp/chip-cache
```

Replay verifies source, checker recipe, tool identity and vector hashes, then
reproduces the verdict and cycle metrics. Private raw vectors and seeds remain
outside Git. All source and verification work in this batch is original; no
external RTL is incorporated.

## Qualification boundaries

This is finite simulation across one counter wrap, not an unbounded proof.
CRC long histories use uninterrupted packets; exhaustive cancellation at every
internal serial-engine phase is not claimed. Retirement has no rename map,
architectural exceptions or memory ordering. New formal results and physical
validation are both zero; existing historical formal timeouts remain unproven.
Dedicated candidate OS isolation and trained-policy results remain unavailable.


Retirement additionally requires its top frame ready/valid signals to equal
`!rst`, including during reset. The older evaluator accepted a constant-high
port mutant because it skipped port comparison on reset frames. Both the ordinary
and long retirement drivers now enforce that declared rule. This differs from
the latency-flexible transaction tasks' synchronous-reset convention; no shared
reset-output restriction is imposed on those tasks.

## Development failures retained

A preliminary retirement trace flushed too soon after wrap and could mask the
numeric-ticket-order mutant at depth6. The final generator drains live work at
rollover before continuing; the original escaped-mutant result is retained.
An initial API run also returned a generic CRC baseline-reset failure. Two direct
installed environment resets subsequently passed. The original API test did not
retain the underlying failure cause, so no cause is asserted. The repeat API run
uses trusted host-side artifact capture for diagnosis. This failure is not erased
or reclassified as a correctness pass.

For private API diagnostics, set `CHIP_RL_CAPTURE_ROOT` to a trusted directory and
add `/path/to/scripts/capture_api` to `PYTHONPATH`. The test-only wrapper supplies
an artifact path to the unchanged evaluator; it does not alter JSON requests,
constraints, seeds, candidate source, comparison logic or rewards. Every server,
CLI and library evaluation is retained with its raw vectors and private error
log. Keep that directory outside candidate-editable locations. This logging
mechanism is not an OS sandbox.


## Measured architecture tradeoffs

These paired long runs use identical vectors within each family. Cell counts are
from generic synthesis; cycle counts are from actual successful simulations.

| Implementation | Cells | Long clocks | Default reward |
|---|---:|---:|---:|
| CRC baseline |578|37,972|1.0000|
| CRC nibble |519|202,484|0.0000|
| CRC serial |485|607,420|0.0000|
| Retirement baseline |1,885|76,314|1.0000|
| Retirement shift queue |2,773|76,314|0.8398|
| Retirement pruned reset |1,760|76,314|1.0335|

The smaller CRC circuits are correct but too slow for the default balanced goal.
Under the area objective, nibble and serial are eligible and score0.8603 and0.7916;
the speed cost still outweighs their modest cell savings in that objective. The
retirement task has fixed physical-cycle behavior, so the reward measures area:
pruned reset reduces cells without changing the trace. These values apply to the
recorded configurations/workloads, not all dimensions or fabricated physical PPA.


## Final recorded results

79 unit tests pass, including a clean checkout. The selected default suites accept
6 valid implementations and reject28 mutants. The long structural suite accepts
18 implementation/configuration pairs and rejects45 adversarial cases. Selected
library/CLI/JSON checks accept18 valid cases and reject84 mutants; the other seven
expansion families accept60 valid API cases and reject246 mutants. All27 regular
schema attacks and4 attempts to bypass the new long-history budget are rejected.
Seven faulty sources accepted by v9 are rejected now. Counts overlap across
interfaces and configurations; they are not counts of unique architectures.

Every accepted HDL case includes synthesis and RTL/mapped-netlist checking. Two
fresh-tool long checks pass, both lowered ordinary workload budgets reject before
the long stage, and replay reproduces the retirement verdict and cycle metrics.
The sealed wheel matches64 runtime source files. CRC and other-family runs from
earlier frozen v10 builds are retained with an audit: relevant CRC/simulation
branches are AST-identical,342 generated non-retirement sources match, and the
subsequent code changes affect retirement only. Final retirement and fresh-tool
runs use the sealed build. Prior root-pilot/fixed-cycle hardware results are
inherited, not claimed as freshly rerun.

New formal checks:0. Physical validation:0. Historical formal timeouts remain
unproven. The initial generic CRC API reset failure remains undiagnosed; subsequent
diagnostic resets and the complete captured API matrix passed. It is retained as
a failed attempt and a remaining qualification caveat, not silently discarded.

See [evidence](../evidence/v10/summary.json) and [exact executed commands](../evidence/v10/executed-commands.txt).
All work remains local. The next genuinely distinct task assessed is a dual-clock
FIFO/CDC bridge; see [the architecture assessment](next-architecture-assessment.md).
It is not yet an implemented environment.
