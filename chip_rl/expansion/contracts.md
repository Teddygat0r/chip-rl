# Experimental expansion contracts

These are additional block tasks, not qualified pilots. All candidate RTL is original
project code. No ISA implementation, full GPU/CPU, physical PPA or trained policy is
claimed. Host constraints and private workload seeds are outside source-only actions.

All modules have parameters WIDTH, DEPTH, K and the existing 512-bit input/256-bit
output ready/valid ports. All state uses one positive-edge clock and synchronous
active-high reset. Unused input bits must be ignored; unused output bits must be zero.
Generated observations include the concrete host configuration and objective.

## Vector permutation (`permute`)

There are N=2*K lanes (development: 4 or 8; structural stress: 6). Input values occupy
16-bit slots at 16*i; only their low WIDTH bits are significant. WIDTH is 8 or 16,
with 12-bit stress cases. Indices are three bits at 128+3*i. Destination enables are
bits 152+i. Output lane i at 16*i receives input lane index[i] when enabled and
index[i]<N, otherwise zero. Each output is zero-extended to 16 bits. Duplicated input
selection is legal. This is a register-vector routing operation, not memory gather or
stable compaction. Reverse, broadcast, transpose-style index vectors and arbitrary
selection use the same contract. DEPTH does not affect this task.

## Request coalescing (`coalesce`)

N=2*K byte addresses occupy 16-bit slots at 16*i. Active-lane bits are 128+i.
WIDTH is the segment size in bytes: 8 or 16, with 32/64-byte structural stress cases. Coalescing also permits K=1 (two lanes); other lane tasks retain K>=2.
Group active addresses by floor(address/WIDTH)*WIDTH. Emit groups in order of the
first active lane belonging to each segment; never sort by address. Output count is
at 0:4. Each of N record slots has aligned base address at 8+24*j:16 and source lane
mask at 24+24*j:8. Inactive slots are zero. Duplicate addresses must preserve all
source mask bits. Addresses span all 16 bits; there is no memory data transfer or
cache-hit policy in this task. DEPTH has no effect.

Both tasks above use latency-flexible transactions: rising-edge acceptance on
in_valid&&in_ready, one in-order result per input, stable output while stalled,
minimum one registered clock, maximum 64 response clocks after acceptance. Reset
cancels buffered work. Dense/bursty/sparse arrivals and consumer backpressure are
paired with a fixed baseline. Baseline is parallel combinational logic plus one
elastic output register. Serial implementations process one lane per clock and may
save area while violating a selected performance goal. Permutation also has a
static decoded crossbar alternative.

## Reorder/retirement buffer (`retire`)

DEPTH is the number of outstanding entries (4 or 8; structural stress: 6).
WIDTH is result payload width (8 or 16; stress: 12). K is unused. This is a
fixed-physical-cycle frame protocol like `chip_rl.cycle`: top in_ready and out_valid
are !rst on every frame; top out_ready is unused. in_valid gates allocations only;
completion and retirement progress even on input-idle clocks.

Input allocation request bit 0; retirement-ready bit 1; flush bit 2; completion-valid
bit 3; completion ticket at 16:16; completion payload at 32:16 (low WIDTH used);
allocation program tag at 64:16. Outputs: allocation-ready bit 0; retirement-valid
bit 1; newly allocated ticket at 8:16 (zero if no allocation this edge); retirement
ticket at 24:16; zero-extended result at 40:16; program tag at 56:16; current occupancy
at 72:4. Retirement fields are zero when retirement-valid is false.

A ticket counter starts at zero on reset, increments modulo 65536 on allocation,
and survives flush. Entries retire strictly in allocation order, only once completed,
and hold all retirement fields while stalled. Completed younger entries cannot pass
an unfinished head. First completion wins; duplicate completions cannot overwrite it.
Unknown tickets are ignored. A completion on the allocation edge cannot complete
that new entry. Full plus simultaneous retirement permits replacement allocation.
Completions affect retirement starting next clock. Reset clears entries/counter;
flush suppresses retirement/allocation that frame and cancels all entries while
preserving the next ticket. Completion identity is the 16-bit ticket; a source must
not retain stale completions across reset or ticket wrap and assume extra identity.
No rename map, architectural register file, exceptions, branch PC, or speculative
memory ordering is modeled. Alternatives use circular storage versus a shift queue.

## Required evaluation and limits

Every API uses two private target workloads (128..256 and 1024..1280 units) and one
512..768-unit workload at each other development dimension. Sources are unchanged
across variants. Every accepted result passes RTL AND Yosys/ABC mapped simulation;
errors/timeouts reject. Retirement adds a 128-clock drain and mid-work reset; event
monitors separately check allocation sequence, completion data and in-order retirement.
Workloads include mixed duplicate/strided/unaligned/high-address coalescing, invalid
indices, masks, random reserved bits, full queues, delayed/out-of-order completion,
flush, stale and duplicate completion, and retirement stalls. Finite coverage is not
an exhaustive proof, and very late/adaptive corruption can evade sampled tests.

Limits: <=50,000 generic cells, per-family generic logic depth, <=30,000 transaction
clocks, 120s wall/90s CPU/3GiB per tool and 64MiB output. Missing tools never silently
pass. Generic cells and depth are proxies, not routed area/timing or power. Compiler
processes are resource-limited but not protected by a dedicated OS sandbox; use an
external VM/account boundary and protect evaluator/cache/artifacts for arbitrary agents.

Permutation/coalescing use the v4 explicit area/balanced/latency objectives, including
all-case feasibility gates. Useful work counts enabled lanes; empty requests still
consume workload cycles. Retirement fixes all externally visible cycles and rewards
only cell area relative to the fixed baseline; it cannot claim a speedup. Formal and
physical stages are not part of default qualification and must be separately reported.


## SECDED codec (`ecc`)

WIDTH data bits (8/16; structural 12) use shortened extended Hamming encoding.
Number positions from one. Power-of-two positions hold even Hamming parity;
remaining positions in increasing order hold payload bits low to high. P is the
minimum parity count satisfying 2**P >= WIDTH+P+1. The overall even parity bit is
at position WIDTH+P+1 (zero-based bit WIDTH+P). Input bit32 selects decoding;
encoding reads low WIDTH input bits, decoding reads low WIDTH+P+1 bits.
Output canonical codeword at 0:32, zero-extended data at 32:16, status at48:2:
0 clean, 1 corrected one-bit error, 2 uncorrectable (codeword/data zero).
Decode selects a valid codeword within Hamming distance one, otherwise status2.
This guarantees correction of one error and detection of two, not arbitrary
multi-bit error recovery. All remaining bits are ignored/zero. DEPTH/K unused.
Baseline uses syndrome correction, decoded uses a static correction mask, and
pipeline separates syndrome generation from correction with elastic registers.
Python checks nearest legal codewords independently of syndrome computation.

## Packet CRC (`crc`)

Reflected CRC-32/ISO-HDLC polynomial 0xedb88320, initial raw state 0xffffffff,
final complement; compatible with zlib.crc32. Input low WIDTH bits are one word
(WIDTH8/16; structural24), low byte first and low bit first per byte. Start bit32
resets packet CRC and byte count before incorporating this word, including when
restarting an active packet. End bit33 closes the packet after this word.
Tag at48:16 echoes unchanged. Continuation without active packet/start rejects
without state mutation. Output finalized running CRC at0:32, final flag32,
error33, tag48:16, packet byte count modulo65536 at64:16. Error responses have
only error/tag fields nonzero. Reset cancels packet and pending responses.
Baseline processes a word per accepted input; alternatives process four or one
bits per internal clock. DEPTH/K unused. Independent oracle uses Python zlib.

## Multi-allocation free list (`freelist`)

DEPTH resources numbered0..DEPTH-1 (development8/32, structural16/24), all
initially free. K=2/4 maximum grants per operation (structural3). Request count
at0:3, flush3, release mask16:32, tag48:16. Flush ignores other operation fields
and makes every resource free. Otherwise request>K, out-of-range release bits,
or releasing an already-free resource rejects the entire operation atomically.
Valid releases happen before allocation; select the lowest available IDs,
returning a partial grant when insufficient resources remain.
Output count0:3, error3, remaining free count8:6, grant mask16:32, up to four
8-bit IDs at64+8*i, tag96:16. Unused IDs zero. Error changes no allocation state;
flush returns no grants. WIDTH unused. Baseline allocates combinationally;
serial allocates at most one ID per clock. This is a resource allocator, not a
complete speculative rename map or rollback mechanism. Python uses a set model
plus a separate ownership/conservation monitor.

These three tasks use the same latency-flexible transaction contract, including
reset cancellation and stable stalled responses. Useful units are ECC data bits,
CRC accepted bytes (invalid commands zero), and successful free-list grants plus
releases (flush/errors zero). Empty/error work still consumes clocks. Reserved
input bits cannot change behavior. Default qualification includes dirty-state
reset and private variable-length/backpressure streams. Generic depth limits are
ECC96, CRC128, free-list160. All three remain experimental, with no physical or
trained-policy result implied by functional qualification.


## Segmented prefix scan (`scan`)

N=2*K signed WIDTH-bit values occupy low WIDTH bits of16-bit slots at16*i.
Active mask128:8; segment heads136:8; exclusive flag144; initial prefix160:32.
Process lanes in ascending order. Inactive lanes output zero, contribute nothing,
and ignore their segment-head flags. An active head resets the prefix to zero before
its value. Other active lanes continue the prefix. Output each inclusive/exclusive
prefix at32*i:32, modulo2^32; initial prefix is the input seed. Unused output lanes
zero. WIDTH8/16 and K2/4 development, WIDTH12 and K3 structural; DEPTH unused.
Baseline uses a combinational ordered accumulator, tree uses a segmented parallel
prefix, serial advances one lane per clock. This produces all ordered prefixes,
not a scalar reduction. Useful work counts active output lanes.

## Stable top-K selection (`topk`)

N=2*K signed WIDTH-bit values occupy low WIDTH bits of16-bit slots at16*i.
Active mask128:8; requested count136:3. Select min(requested,K,active count)
largest values, ordered decreasing by signed value, then increasing source index
for ties. Output count0:4; records at8+24*j contain sign-extended value16 then
index8. Unused records/bits zero. WIDTH8/16,K2/4 development, WIDTH12/K3 structural;
DEPTH unused. Baseline uses insertion comparators; alternative computes pairwise
stable ranks. Reference uses Python sorting plus membership/order checks. Useful
work counts active input lanes only when requested count is nonzero. This is a
small hardware selection contract, not a claim of CUB API compatibility.

## Collision-aware histogram (`histogram`)

DEPTH unsigned WIDTH-bit bins start zero. Input K update indices at8*i:8, enables
32+i, clear40, unsigned8-bit deltas at48+8*i, K query indices at128+8*i:8, tag192:16.
Clear happens before updates. Enabled in-range updates occur logically in ascending
lane order, wrapping modulo2^WIDTH, including repeated indices. Invalid updates
are ignored and flagged; inactive updates are ignored. Queries observe all updates
and return zero for invalid indices.

Output previous value per valid update at16*i:16, post-update query values at
64+16*i:16, valid-update mask128:4, invalid-update mask132:4, echoed tag144:16.
Inactive/invalid update values and all unused output bits are zero. K2/4, depth8/16,
width8/16 are development settings; depth24/32,width12,K3 are structural stress.
Baseline combines updates combinationally; serial performs one update per clock
then reads query values. Reset cancels pending output and clears all bins. A
counter model and independent per-bin conservation assertion check state changes.
Useful work counts valid updates and in-range query reads, excluding clear itself.

All three use the established latency-flexible ready/valid contract with synchronous
reset, registered responses, exact in-order completion and stalled-output stability.
Sources cannot change dimensions or budgets: max50000 generic cells, generic depth160,
max30000 workload clocks and response deadline64. Zero-work commands still consume
clocks. Reserved input bits are randomized and must be ignored. These tasks remain
experimental, and no physical, unbounded formal or trained-policy result is implied.


## V8 qualification changes

Synchronous reset has priority regardless of input-valid, payload, and output-ready.
The shared transaction evaluator now exercises warm reset with valid asserted and
nonzero input data. Histogram mandatory long workloads use2048..2304 random units,
plus existing initialization and192 sustained-collision commands. They cross16-bit
counter wrap before a clear even at K=2. The30000-clock cap is unchanged.

Additional valid architectures are coalescing `representatives` (parallel first-lane
representatives and membership masks) and histogram `parallel_bins` (per-bin sums
with ordered previous-value reconstruction). Their acceptance and reward are measured;
neither is presumed superior. Trusted deep qualification separately exercises an
independent oracle, new distributions and interrupted transactions. Passing that
layer does not automatically promote an experimental family to pilot status.
