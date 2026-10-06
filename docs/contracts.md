# Contracts and task scope

Every candidate is one synthesizable SystemVerilog module named `candidate`:

```verilog
module candidate #(parameter WIDTH=16, DEPTH=256, K=4)(input clk, input rst, input in_valid, output in_ready,
 input [511:0] in_data, output out_valid, input out_ready,
 output [255:0] out_data);
```

Reset is synchronous, active high, and discards all outstanding work and task state.
A command is accepted on a rising edge with `in_valid && in_ready`.
Exactly one response must eventually retire per accepted command, in order.
The producer holds input valid/data until acceptance. The consumer may stall;
output valid/data must remain stable until retirement. Unused output bits are zero.
Scratchpad/gather memory resets to zero; cache valid bits reset, and invalid cache data is unobservable. All integer field numbering is little endian (bit 0 least
significant); addresses outside configured memory wrap modulo depth. No X/Z
outputs are allowed when valid. The elastic baseline stores four words; other reference designs have one output register.
Responses are **latency flexible** within 1..64 cycles after acceptance; elastic designs must accept at least four commands while their consumer is blocked.
Candidates and the fixed baseline face identical offline command release times and consumer schedules. All designs use one positive-edge clock and synchronous state. Completion is bounded by min(max_cycles, 32*commands+128), useful throughput must be at least 1/16 of baseline, and generic combinational depth is bounded by the limits in contracts.py. These gate levels are a timing proxy, not clock closure.

Notation: `field L:W` means W bits starting at L. Memory depth defaults to 256 words.
The Python `Model.step` specifies each state transition; the RTL generator implements
it separately. Hand-calculated tests exercise those reference models independently.

| Family | Command | Response and semantics |
|---|---|---|
| `elastic` | data `0:16` (parameter WIDTH) | Zero-extended input. Baseline has four genuine elastic registers with ready propagation and backpressure. |
| `dot` | Four signed INT8 A values at `0:32`, four B at `32:32` | Exact signed sum of four products at `0:18`, two's-complement; K uses the first K pairs. No rounding/saturation. |
| `scratchpad` | Four 48-bit slots: valid bit 0, write bit 1, word address `2:8`, write data `10:32` | Grant mask `0:4`; values at `8+32*i:32`. Four banks (`address % 4`), one winner per bank, round robin per bank; write-through returned value on a write. Non-granted slots return zero. 256 total 32-bit words. |
| `tensor` | A 2x4 signed INT8 matrix in row-major order at `0:64`; B 4x2 at `64:64` | Four exact signed 18-bit C values, row-major at `0:72`. K uses the first K inner terms; physical input strides remain four for A and two for B. A two-row dot-product array. |
| `cache` | Opcode `0:2`, byte address `8:16`, memory/write data `24:32` | Direct-mapped 1KiB, 256 single-word lines, write-through, no write allocation. Flags: bit0 response, bit1 read hit, bit2 pending/miss, bit3 external write. Data `8:32`, external byte address `40:16`. Op0/3 read. Hit returns data; miss records one pending address. Commands while pending return busy and have no side effects, except op2 supplies delayed refill data and retires the pending read. Op1 writes through and updates a resident line. Address low two bits are ignored. The explicit external write flag/data are the write-through memory request. There is no dirty eviction or coherence. |
| `gather` | Write bit0: address `8:8`, data `16:32`. Otherwise four mask bits `4:4` and four irregular addresses at `16:32` | Writes return zero. Read response count at `0:3`; selected words packed at `8+32*j:32` in original lane order. Duplicates preserved. Sparse masks compact stably; empty mask yields zero. |


## Scope and parameters

These are six block-level pilot tasks. Four separate experimental physical-cycle
controllers have their own `chip_rl.cycle` API and contract; historical command-tick
models are retained for reproduction only. Arbitration losers in scratchpad commands
must be retried by the host. Cache refill is an explicit command, not an autonomous
external-memory interface. These are not complete ASIC/GPU products.

Each candidate's unchanged source is checked at the requested host configuration
and all development values applicable to its family: WIDTH 8/16/24, DEPTH 16/64/256,
or K 2/4. Extra supported stress configurations are WIDTH 12/20, DEPTH 32/128, K 1/3.
Only the relevant parameter affects a task. Sources cannot change between variants.
The structural stress script freezes development winners before evaluating those
extra public dimensions with fresh private workloads. This is a prospective split,
not a claim that authors cannot see the dimensions or that a policy was trained.

## Required checks and budgets

All qualifying paths share `coverage.cases`, including library, CLI, JSON episodes,
release qualification, heldout checks and the physical launcher's prerequisite.
There is no short-success mode. Target workloads draw 128..256 and 1024..1280 random
generator units; other dimensions draw 512..768. Directed prefixes and multi-command
operations add commands. Legacy host `count` can only increase coverage floors.
Private 128-bit seeds change each evaluation; agent reset seeds never control them.

Workloads cover reset after dirty state, stable stalls, progress, exact signed
extremes, dense/bursty/sparse arrivals, mixed operand distributions, cache tag aliases,
arbitration fairness, irregular masks, post-initialization memory writes and reads,
and randomized reserved high input bits. Useful units exclude control-only commands.
RTL preflight must pass, followed by paired baseline/candidate RTL and Yosys/ABC
mapped-netlist simulation. All transaction results and measured cycle statistics must
agree between RTL and netlist. Missing tools, divergence and timeouts reject.

Default limits: 250,000 generic cells, 30,000 clocks per case, 120 seconds wall per
compiler/simulation process, 90 CPU seconds, 3 GiB address space, 64 MiB output files,
and 100 kB source. One synthesizable module, exact ports and parameters, single
positive-edge clock. No preprocessor, simulation system tasks, timing directives,
attributes, file access, latches or blackboxes. Per-family logic-depth limits are in
contracts.py. Trusted host configuration can lower budgets; actions contain only RTL.

## Explicit objectives and Pareto measurements (0.4.0)

Correctness/resource/tool failures score zero. Correct candidates also score zero
when the selected goal's performance constraints fail on **any** tested case.
`tested_correct` records finite functional qualification; `objective_eligible` is
separate. Host selects the goal before the episode; actions cannot change it.

| Goal | cell/cycle/latency log weights | maximum cycle ratio | maximum latency ratio |
|---|---|---|---|
| area | .80/.15/.05 | 16 | 1024 |
| balanced (default) | .45/.30/.25 | 2 | 4 |
| latency | .20/.25/.55 | 1.1 | 1.1 |

Ratios compare each candidate against the fixed baseline on the identical workload.
Cell ratio = candidate/baseline; cycle ratio = candidate/baseline completion clocks;
latency ratio = (candidate offered latency + 1)/(baseline offered latency + 1).
Offered latency includes waiting before acceptance and is weighted by useful work.
The plus-one smooths sub-cycle weighted averages. Throughput is useful units divided
by completion clocks, so at fixed work its ratio is the inverse cycle ratio.

For eligible goals, score = mean over target cases of
`1 - .5*tanh(sum(weight * log(ratio)))`. Baseline scores 1. Structural cases gate
eligibility but do not dilute the target score. Raw paired metrics, all three goal
scores, geometric-mean target ratios and the candidate's Pareto relation are returned.
A scalar improvement can be an area/performance tradeoff. No single goal implies
universal superiority. The standalone older `reward()` helper is historical; public
evaluation uses `objectives.scores`.

Cells and generic logic depth are proxies, not physical area, frequency, routed
critical path, power or silicon readiness. Memory maps to registers/muxes, not SRAM.
There are no physical results. Compiler working directories and resource limits are
not an OS security boundary; protect evaluator/cache/artifacts with an external VM
or account and source-only RPC before exposing arbitrary agents.

## Verification limits

Finite public workload bands cannot exclude every adaptive hack or late cutoff.
64/127/257/777/1023 cutoff variants are regressions, not a universal liveness proof.
Single-case replay is diagnostic and cannot qualify a candidate. Bounded formal is
separate: elastic safety over 12 clocks and symbolic K=1 dot safety over 8 clocks.
A cycle-exact miter is used only for fixed-cycle comparisons; changing latency may
fail that miter while preserving the transaction contract. Errors/timeouts remain
unproven. No unbounded proof or K=4 arithmetic proof is claimed.
