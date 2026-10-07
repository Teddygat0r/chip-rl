# V9: reset independence and interrupted state

This batch keeps 19 families: six pilots and thirteen experimental tasks. It adds
no family and promotes none. The nine added families are permutation, coalescing,
retirement, ECC, CRC, free list, scan, top-K, and histogram. Their contracts and
remaining gaps are recorded in [v8](deep-qualification-v8.md).

## Full inventory

| Family | Contract / useful search dimension | Status |
|---|---|---|
| Elastic pipeline | Ready/valid buffering, storage capacity, pipeline structure | Pilot |
| INT8 dot product | Exact signed arithmetic, reduction architecture | Pilot |
| Banked scratchpad | Bank conflict arbitration and response ordering | Pilot |
| Burst DMA | Address generation and response scheduling | Experimental |
| Packet router | Five-port queues and fair arbitration | Experimental |
| SIMD scoreboard | Four-context dependencies and autonomous completion | Experimental |
| INT8 tensor tile | Exact 2x2 K4 matrix product architecture | Pilot |
| Accelerator subsystem | Concurrent DMA/load/compute coordination | Experimental |
| Cache controller | Direct-mapped write-through cache | Pilot |
| Sparse gather | Irregular reads and stable masked ordering | Pilot |
| Register permutation | Masked indexed vector selection | Experimental |
| Memory coalescing | Stable unique segments and exact membership masks | Experimental |
| Reorder/retirement | In-order completion, tickets and flush | Experimental |
| SECDED ECC | Exact shortened extended-Hamming encode/decode | Experimental |
| Packet CRC | Stateful reflected CRC32 packet processing | Experimental |
| Free list | Release/allocate conservation and lowest-ID priority | Experimental |
| Segmented scan | Masked signed segmented prefix sums | Experimental |
| Stable top-K | Exact signed ranking with stable index ties | Experimental |
| Histogram | Ordered atomic collisions, previous values and wrap | Experimental |

## Demonstrated coverage hole

The frozen v8 default and independent deep evaluators accepted all three selected
baseline designs with `if(rst)` changed to `if(rst && out_ready)`. Reset incorrectly
depended on consumer readiness. Saved source hashes establish that v9 rejects the
same candidates. This is an evaluator coverage improvement, not a contract change
or a claim that finite simulation proves arbitrary RTL.

V9 adds 80 dirty/observe pairs per configuration: all four valid/ready reset
combinations, one or two accepted commands before cancellation, and ten hold
lengths. Reset payloads vary with the trusted private seed. Histogram observation
reads every bin with all update lanes disabled, using an independently implemented
event-log oracle. ECC reset probes use independent parity equations and encode
requests at every supported width; exhaustive eight-bit decode checks remain in
the separate deep workload. The two-request interruptions exercise multi-entry
implementations; single-entry implementations may complete the first before the
second is accepted. This does not claim both entries are occupied in every design.

Review also removed an inherited overly strict deep-check assumption: the driver
now checks cancellation after the reset clock edge, without requiring combinational
masking of valid or forcing ready low during reset. Additional positive variants
remove both reset-output gates while retaining synchronous state reset. Their
acceptance is tested explicitly; the registered response and cancellation contract
is unchanged.

These probes are mandatory once per distinct selected configuration through
library, CLI and JSON evaluation. RTL and synthesized netlist both run against the
same independent expected values. The evaluation recipe fingerprint now includes
the qualification package. Reset probes are separate from uninterrupted long
workloads, preserving the late-loss tests added in v8.

## Objective fidelity and search

Reset probes contribute no responses, cycles or latency to scored workloads.
A retained v8 coalescer run with 160 new reset epochs reproduced all four scored
metrics exactly: 6,224 responses, 12,530 active cycles, latency sum 34,984 and maximum
offered latency 16. This verifies neutrality for that run; it is not a universal
performance theorem. The existing distinct architectures remain the search space:
ECC baseline/decoded/pipeline, coalescer baseline/serial/representatives, histogram
baseline/serial/parallel bins. V8's explicit offered-load constraints still apply.
The installed default balanced objective remains sensitive to architecture:
ECC rewards are baseline 1.0000, decoded 1.1203 and pipeline 0.9827; coalescing
baseline 1.0000, serial 0.0000 and representatives 1.2070; histogram baseline
1.0000, serial 0.0000 and parallel bins 0.9427. Zero here means a functionally
correct design failed the objective's eligibility constraints, not that it was
rejected as incorrect. Cell count and gate depth remain synthesis proxies; workload clocks do not imply
frequency, power or routed timing.

## Reproduction

Install the package and pinned local Icarus/Yosys tools as described in the README.
Run installed checks from outside the source checkout, with fresh output paths:

```sh
python -m unittest discover -s tests -v
python -m chip_rl.expansion.suite --tasks ecc coalesce histogram --output /tmp/v9-q --cache /tmp/chip-cache
python /path/to/scripts/check_expansion_apis.py --tasks ecc coalesce histogram --output /tmp/v9-api --cache /tmp/chip-cache
python /path/to/scripts/deep_qualification.py --output /tmp/v9-deep --cache /tmp/chip-cache
python /path/to/scripts/check_reset_score_neutrality.py /private/v8/coalesce/1-representatives --output /tmp/v9-neutral --cache /tmp/chip-cache
```

## Remaining status

Reset pulses currently last three clocks and hold lengths stop at nine clocks.
The probes are finite, project-authored checks with independently implemented
oracles, not a third-party audit. Other stateful families still need corresponding
interruption coverage, notably CRC packet/count wrap and retirement ticket wrap.
No new formal result is claimed: v8 successful bounded attempts and its timeout
remain separate historical evidence. Physical validation remains zero, dedicated
candidate OS isolation is unavailable, and no policy has been trained. No new
remote push or paid service was used.

Next useful batch: CRC's current generator starts packets of at most 23 words
(and can restart earlier), so it never reaches the 16-bit byte-count wrap.
Retirement's short trace resets the ticket counter halfway through; it cannot
exercise 65,536 allocations. A supplemental long-history checker should state its
own execution budget explicitly, retain the existing default 30,000-clock limit,
and test wrap plus cancellation/flush semantics with independent state tracking.
These are concrete missing mechanics in existing families, not justification for
adding more family names.


## Recorded milestone results

All final affected checks pass: 73 unit tests; 9 catalog designs accepted and
41 mutants rejected by default qualification; 18 valid design/configuration pairs
and 44 adversarial rejections in independent deep checks; 27 valid selected API
checks and 123 mutant rejections across library, CLI and JSON. The other six
expansion families pass 51 valid API checks and 186 mutant rejections. All 27
schema-override attacks are rejected. Three additional synchronous-only handshake
variants pass both default and deep evaluation. Counts overlap across interfaces;
they are not counts of unique designs or independent audits.

Every accepted HDL check includes actual synthesis and RTL/mapped-netlist
simulation. Three reset checks using an independent tool installation pass.
Replay reproduces verdict and cycle metrics. A clean checkout passes 73 tests.
The final installed wheel matches all 59 runtime files. Other-six API checks used
the initial v9 wheel: the only subsequent runtime difference is the unused deep
driver; their exercised evaluator/model/RTL/simulator code is byte-identical.
The provenance report records this rather than claiming a second full rerun.
Root pilot and fixed-cycle code is unchanged; previous results are inherited.

No new formal check was run (historical bounded successes and unproven timeouts
remain unchanged). Physical validation count is zero. All raw private vectors and
logs remain outside Git; [public evidence](../evidence/v9/summary.json) includes
exact commands, provenance, source-identity comparisons, API results, objective
measurements and replay results. This milestone is local only. It does not end
the ongoing development goal; the long-history gaps above are the next priority.
