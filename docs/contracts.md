# Contracts and task scope

Every candidate is one synthesizable SystemVerilog module named `candidate`:

```verilog
module candidate(input clk, input rst, input in_valid, output in_ready,
 input [511:0] in_data, output out_valid, input out_ready,
 output [255:0] out_data);
```

Reset is synchronous, active high, and discards all outstanding work and task state.
A command is accepted on a rising edge with `in_valid && in_ready`.
Exactly one response must eventually retire per accepted command, in order.
The producer holds input valid/data until acceptance. The consumer may stall;
output valid/data must remain stable until retirement. Unused output bits are zero.
Memory resets to zero. All integer field numbering is little endian (bit 0 least
significant); addresses outside configured memory wrap modulo depth. No X/Z
outputs are allowed when valid. Four stages are the fixed reference baseline;
responses are **latency flexible**, so alternatives may change internal buffering.
All candidates face the same backpressure schedule, deadline, workload and budget.

The starter designs compute a task transition at command acceptance and buffer its
response. Task ticks (DMA acknowledgement or scoreboard progression) are **logical
command ticks**, not every physical clock. This separates variable implementation
latency from architecture semantics. These are bounded microarchitecture problems,
not full AXI implementations, coherent caches, GPU ISA implementations or complete
accelerator products. In particular, arbitration losers must be retried by the host;
input packets/instructions are proposals, not silently accepted internal queue entries.

Notation: `field L:W` means W bits starting at L. Memory depth defaults to 256 words.
The Python `Model.step` specifies each state transition; the RTL generator implements
it separately. Hand-calculated tests exercise those reference models independently.

| Family | Command | Response and semantics |
|---|---|---|
| `elastic` | data `0:16` (parameter width 8/16/24) | Zero-extended input. Baseline has four genuine elastic registers with ready propagation and backpressure. |
| `dot` | Four signed INT8 A values at `0:32`, four B at `32:32` | Exact signed sum of four products at `0:18`, two's-complement; K=2 structural variant uses the first two pairs. No rounding/saturation. |
| `scratchpad` | Four 48-bit slots: valid bit 0, write bit 1, word address `2:8`, write data `10:32` | Grant mask `0:4`; values at `8+32*i:32`. Four banks (`address % 4`), one winner per bank, round robin per bank; write-through returned value on a write. Non-granted slots return zero. 256 total 32-bit words. |
| `dma` | Start bit 0, acknowledge bit 1, base byte address `8:16`, columns-minus-one `24:3`, rows-minus-one `27:3`, byte row stride `32:16` | Valid bit 0, byte address `8:16`, eight byte-lane enables `24:8`, final-beat bit 32. Four bytes per beat. Low/high nibble masks represent two adjacent aligned words for misaligned beats. Address holds until acknowledgement. Row traversal is base + row*stride + 4*column, wrapping at 16 bits. A start while active is ignored; a start while idle may acknowledge its first beat immediately. There is one outstanding beat; the test host supplies delayed acknowledgements. This environment is the burst address/control engine, not an external bus implementation. |
| `router` | Five 32-bit input slots: valid bit 0, destination `1:3` (0..4), payload `4:16`; five output-ready bits at `160:5` | Input grant bits `0:5`, output valid bits `8:5`, output payloads `16+16*p:16`. Round robin per destination, one grant per ready output. No grant when destination blocked. Invalid destinations have no grant. |
| `scoreboard` | Four 24-bit context slots: valid bit 0, source register `1:4`, destination register `5:4`, execution-latency-minus-one `9:3` | Issue mask `0:4`, busy-register bitmap `8:16`. Sixteen registers. Busy timers decrement first, then one ready context issues via round robin, reserving destination for 1..8 logical ticks. RAW and WAW hazards block issue. Host retries proposals; this is a scalar issue decision across four SIMD contexts, not a vector ALU. |
| `tensor` | A 2x4 signed INT8 matrix in row-major order at `0:64`; B 4x2 at `64:64` | Four exact signed 18-bit C values, row-major at `0:72`. K=4 (or first two inner terms for K=2). A two-row dot-product array. |
| `accelerator` | Opcode `0:2`, destination/base A `8:8`, data or source/base B at `16:32` | Shared 256x32 scratchpad. Op0 host/DMA write, response zero. Op1 copies one word from B to A and returns it. Op2 sums K signed low-byte products from wrapping ranges A and B, returning 18 bits. Op3 reads A. Sequential commands compose host DMA loads/copies, local storage and compute. No autonomous descriptor queue or external bus. |
| `cache` | Opcode `0:2`, byte address `8:16`, memory/write data `24:32` | Direct-mapped 1KiB, 256 single-word lines, write-through, no write allocation. Flags: bit0 response, bit1 read hit, bit2 pending/miss, bit3 external write. Data `8:32`, external byte address `40:16`. Op0/3 read. Hit returns data; miss records one pending address. Commands while pending return busy and have no side effects, except op2 supplies delayed refill data and retires the pending read. Op1 writes through and updates a resident line. Address low two bits are ignored. The explicit external write flag/data are the write-through memory request. There is no dirty eviction or coherence. |
| `gather` | Write bit0: address `8:8`, data `16:32`. Otherwise four mask bits `4:4` and four irregular addresses at `16:32` | Writes return zero. Read response count at `0:3`; selected words packed at `8+32*j:32` in original lane order. Duplicates preserved. Sparse masks compact stably; empty mask yields zero. |

## Measurements and constraints

The default budget is 250,000 Yosys generic mapped cells and 30,000 cycles per
workload, plus 120 s wall/90 s CPU/3 GiB per tool process (30 s for simulation).
Candidates are limited to 100 kB and one module. No timing directives, attributes,
preprocessor, file access, simulation system tasks, blackboxes, latches or interface
changes are allowed. Bounds are trusted configuration, never action fields.

`useful_work` excludes control-only transactions: accepted DMA beats, granted
scratchpad/router/scoreboard operations, cache responses, accelerator MACs, gather
selected words, tensor/dot MACs, or elastic words. Initialization/control cycles
remain in total workload cycles. Useful latency is output-response latency weighted
by useful work; this is command-to-response latency, not end-to-end program runtime.
The cache miss/refill and DMA address protocol operate on explicit host commands.

Reward is zero for any correctness/budget/tool failure. Otherwise:

```
1 + .2*tanh(log(baseline_cells / candidate_cells))
  + .2*tanh(log(baseline_useful_latency / candidate_useful_latency))
  + .1*tanh(log(candidate_useful_throughput / baseline_useful_throughput))
```

Successful rewards are strictly positive and at most 1.5. Baseline, seed, input
hash, task configuration and workload size must match. Cells are a **logic-area
proxy**, not micrometers squared. Cycle measurements are not frequency, routed
critical path, timing closure, power, or silicon readiness. Reducing pipeline depth
can improve this reward while worsening achievable clock frequency; the present
reward cannot assess that tradeoff. Memory is mapped to flip-flops/muxes by this
flow, not characterized SRAM macros.

## Validation and splits

The post-audit qualification runs each baseline and a task-specific two-stage
alternative, a separately generated challenge workload (seed982451653), and a
challenge workload on a held-out structural configuration (width24/depth16/K2,
seed32452843). Only applicable parameters affect a given family. Training uses seed1.
`heldout.challenge` is separately written and never calls the training generator.
It covers walking bits, signed extremes, arbitration masks/contention, RAW/WAW
chains, 1..8 by 1..8 DMA shapes with misalignment/wrap and delayed acknowledgements,
cache writes/refills/conflicts, and all gather masks. Published challenge seeds remain
reproducibility examples, not secrets. The older `heldout` split remains available to
replay the initial release, which used seed separation within the training generator.

Task-specific alternatives use a globally stalled elastic pipeline, balanced dot and
tensor reductions, reverse-overwrite priority encoders for scratchpad/router/scoreboard,
incremental DMA address state, a balanced shared-memory dot kernel, decoded cache
read/write enables, and prefix-popcount gather placement. Yosys can canonicalize
some equivalent formulations. Their combined area/latency reward also includes the
four-to-two-stage buffering change; it does not isolate kernel-only improvement.

Every valid case runs Icarus RTL simulation, Yosys+ABC synthesis, then Icarus on the
synthesized netlist with identical vectors and cycle/latency checks. Directed and
random vectors include resets with work in flight, long output stalls, input bubbles,
full signed extremes, conflicts, pending memory responses, sparse masks and duplicates.
The suite requires task-specific semantic mutant, dropped-response mutant and
unstable-output mutant rejection for each family. Tests do not prove all possible
workloads; larger independent stress suites are appropriate before serious training.

`check_elastic` proves transaction-order/data/occupancy/stall safety for a small
pipeline over 12 cycles using Yosys SAT. It does not prove unbounded liveness or
other families. `check_cycle_equivalence` is a **separate** bounded all-port miter
for explicitly fixed-cycle specifications. The unit test confirms a 4-to-2-stage
change fails cycle equivalence while passing transaction safety. Timeout, error and
inconclusive results are always `unproven`, never correctness success.
