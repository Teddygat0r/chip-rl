# Experimental fixed-cycle controllers

These four tasks are separate from the six latency-flexible pilot tasks and the
historical command-tick models. They test synthesizable controller behavior, not
a complete AXI/NoC/GPU implementation. No promotion or formal/physical proof is implied.

All use `candidate #(WIDTH=16, DEPTH=16, K=4)` with the pilot port widths. Inputs
are applied before each rising edge; outputs describe that edge's transfers.
Synchronous active-high reset cancels outstanding work and clears observable state.
On non-reset clocks `in_ready=out_valid=1` identify a cycle frame. `in_valid`
gates new host requests only. Autonomous work continues during input-idle clocks.
Top-level `out_ready` is unused; each actual receiver's ready is encoded below.
All unused output bits are zero. Data fields are zero when their validity is false.
This is an explicit fixed-cycle contract: changing queue/issue/response latency is
not a permitted optimization. Source-only actions cannot alter the evaluator or goal.

Bit ranges below use low-bit plus width notation. Addresses wrap modulo DEPTH.

## DMA

Input: descriptor start bit 0, source 8:8, destination 16:8, length-minus-one 24:4,
read-request ready 32, read-response valid 33, destination-write ready 34,
read-response data 64:32. Output: descriptor-ready 0, read-request-valid 1,
response-ready 2, write-valid 3, done 4, busy 5, read address 8:8,
write destination 16:8, write data 32:32.

One outstanding read; phases are idle, request, response, write. Hold address/data
under stalls. Increment addresses only after a write transfer. Done is one clock
after the final write edge. Source and destination are distinct external memories.
This is contiguous word movement, not byte-misaligned/2D/AXI burst DMA.

## Queued router

Five input slots, each 24 bits: valid at +0, destination +1:3, payload +4:16.
Per-output ready is 160:5. Output: queue-valid 0:5, payloads 8+16*p:16,
accepted-input mask 96:5. WIDTH is 8 or 16; payload high bits are ignored at WIDTH=8.
Invalid destinations 5..7 are not accepted.

Each output has a one-entry queue. An empty queue or simultaneous dequeue permits
one enqueue. Per-destination round robin starts at input 0 and advances past each
winner. Output data stays stable while stalled; new data appears after its enqueue
edge. Independent ports can transfer concurrently. No virtual channels or routing network.

## Scoreboard

K=2 or 4 context slots, each 24 bits: valid +0, source-register +1:4,
destination-register +5:4, latency-minus-one +9:3, tag +12:8.
Output: issue mask 0:4, post-completion-and-issue busy-register mask 8:16,
issued tag 24:8, input-accepted mask 32:4.

Each context has one queue entry. Every physical clock completes pending register
writes, then issues at most one eligible queued instruction (RAW and WAW safe),
then enqueues new inputs. The issued instruction cannot be a same-edge new input.
Round robin advances after an issue; completion proceeds without new inputs.
No execution datapath, bypass network, or out-of-order retirement is modeled.

## Concurrent accelerator

DMA input fields match DMA above, except response data is signed INT8 at 64:8.
MAC start is bit 1, A base 40:8, B base 48:8, result-ready 34.
Output: DMA-ready 0, read-valid 1, response-ready 2, DMA-done 3, MAC-ready 4,
result-valid 5, MAC-busy 6, DMA-busy 7, read address 8:8, signed result 32:18.

DMA request/response loads a reset-zero scratchpad while an independent engine
accumulates K signed INT8 products over K physical clocks. Simultaneous MAC reads
and DMA writes observe the pre-edge memory value (read-before-write). Result holds
until accepted. MAC accepts a new command only when neither computing nor holding
a result. This is a small concurrent load/compute block, not a full accelerator.

## Evaluation and limits

Two private workloads per structural configuration run both RTL and Yosys/ABC
mapped netlists. Drivers inject delayed memory responses, bounded receiver stalls,
input-idle clocks, reset during work, saturation and drain. Independent transfer
monitors check FIFO ordering, memory values, fairness, progress and MAC results
from versioned memory history. Reset-aborted jobs are excluded from drain obligations.

Reward compares generic-cell area against a fixed paired baseline while all
physical-cycle outputs must match. It does not optimize latency or claim frequency,
routed timing or power. Runs have the same compiler/time/resource restrictions as
the pilot, but no OS sandbox. Finite tests are not exhaustive. Formal and physical
stages are explicitly not run. Use a trusted host with source-only RPC for agents.
