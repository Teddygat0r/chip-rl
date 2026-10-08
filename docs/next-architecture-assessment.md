# Next architecture assessment after V10

Recommend a **dual-clock asynchronous FIFO / clock-domain crossing bridge** next.
This is an architectural coverage gap: every existing task exposes one positive-edge
clock. The elastic pipeline task does not exercise unrelated clocks, synchronized
pointer visibility, clock stoppage, or domain reset coordination. A small CDC
bridge is a distinct ASIC/GPU integration component, not another vector operation.

OpenTitan's primary asynchronous FIFO exposes separate read/write clocks and resets,
uses synchronized Gray-coded pointers and constrains its depth accordingly. Its
source carries Apache-2.0 licensing. These are reference facts, not a claim that
chip-rl incorporates or verifies OpenTitan IP. No source was copied. See the
[primary source](https://raw.githubusercontent.com/lowRISC/opentitan/master/hw/ip/prim/rtl/prim_fifo_async.sv)
and [license](https://raw.githubusercontent.com/lowRISC/opentitan/master/LICENSE),
reviewed2026-10-07. The older Sunburst paper URL redirected to an inaccessible page;
this assessment does not rely on unverified contents of that document.

Proposed first contract:16-bit words, power-of-two depth4/8/16, independent write
and read ready/valid interfaces and clocks, coordinated reset epochs with explicit
release rules. Exactly-once in-order delivery, no overflow/underflow, stable stalled
read output, and bounded recovery after both clocks resume. Do not initially claim
arbitrary one-sided reset preserves outstanding data; define cancellation or a
reset handshake explicitly before implementation.

The search space would include two- versus three-stage synchronization with a
minimum safe structural policy, registered flag versus registered output choices,
and dual-port storage versus small flop arrays. Independent tests need rational
and non-repeating clock ratios, relative phases, pauses, simultaneous edges, bursts,
full/empty transitions and reset skew. A checker must resolve simultaneous events
without racing the DUT. Small bounded formal checks should model nondeterministic
clock enables and synchronization delay, with explicit fairness assumptions.

The existing single-clock port validator and harness cannot certify this task.
A new protected interface/clock-domain validator is required. Generic simulation
cannot measure analog metastability, MTBF, synchronizer placement or routing skew;
it also cannot establish that simply removing a synchronization stage is safe.
Structural CDC checks and constrained formal assumptions are necessary before
rewarding area or latency. Physical/analog claims must remain unavailable without
the corresponding tools and constraints.

Compare alternatives: a page-table walker/TLB would add translation semantics but
requires substantial address-space and invalidation contracts; a DRAM scheduler
would add row/timing constraints but overlaps existing arbitration/scheduling work.
The CDC bridge is the smallest well-defined next expansion with genuinely new
clock behavior. This recommendation is engineering judgment from the repository
inventory and the cited primary reference, not a measured environment result.
