# Accelerator memory-system exercises

An accelerator often waits for data rather than arithmetic. V12 develops two
experimental RTL tasks that exercise that interaction. Neither is an ISA-compliant
MMU, a coherent cache, or a physical memory macro.

An **MSHR** (miss-status handling register) remembers a missing cache line and the
requests waiting for it. Here, requests arrive over time, different memory reads
can return out of order, and each completed line must supply every waiting word
and client tag. This differs from the earlier coalescer, which groups lanes inside
one command, and from the earlier blocking direct-mapped cache. The baseline uses
per-entry circular waiter queues; the alternative shifts waiter queues. Both retain
four waiters per line and support the configured number of concurrent misses.

A **TLB** caches virtual-to-physical page translations. On a miss, this task reads
a root PTE and then the leaf PTE addressed by that root. A PTE is a page-table entry.
The backing tables contain private randomized mappings, valid bits and permissions.
ASIDs distinguish address spaces. The baseline has one walker; the alternative has
two independent walkers sharing memory/output channels and a fully associative TLB.
Invalidation can arrive during a root read, leaf read or stalled output. A poisoned
walk must restart, while an already offered output remains stable.

The templates and monitors are original. Architectural background was checked
against [Rocket Chip's MSHR implementation](https://github.com/chipsalliance/rocket-chip/blob/master/src/main/scala/rocket/NBDcache.scala)
and the [RISC-V supervisor specification](https://docs.riscv.org/reference/isa/v20260120/priv/supervisor.html).
No source was copied. Rocket Chip identifies LICENSE.Berkeley and LICENSE.SiFive
in that source; their attribution/redistribution conditions would matter for reuse.
This exercise deliberately uses a small custom translation format, not Sv32,
SFENCE.VMA, accessed/dirty-bit updates, superpages or privilege/PMP enforcement.

## Protocol

Both tasks use `clk` with a synchronous active-high `rst`, a tagged client
ready/valid request stream and a tagged result stream. Tags are eight bits and
must be unique among outstanding client requests. Outputs may reorder and must
remain stable under backpressure. A reset cancels both client and memory work;
the environment coordinates the memory service reset. Unilateral controller reset
with uncanceled external responses is outside the contract.

The memory request stream carries a 16-bit address and four-bit transaction ID.
Responses carry the same ID and 128 data bits. An ID cannot be reused while its
response remains outstanding. Request and response channels have independent
backpressure. MSHR client addresses are word indices; TLB addresses are byte addresses.
MSHR memory addresses are aligned four-word line addresses, and a
response contains four 32-bit words. Only one fetch per outstanding line is allowed.
A full waiter queue stalls matching requests; it cannot drop or overwrite a waiter.
MSHR requests use zero auxiliary bits, produce fault code zero, and ignore the
translation-invalidation inputs.

The translation format has a 16-bit virtual address: eight VPN bits and eight
page-offset bits. Request auxiliary bits 1:0 are the ASID; bit 3 requests execute,
otherwise bit 2 requests write, otherwise the access is read. Bits 7:4 are reserved
and driven zero by this environment. There are four ASIDs.
The root address is `0x8000 + ASID*256 + VPN[7:4]*4`. Its valid bit is bit 0 and its
next-table address is bits 15:2 shifted left 2. The leaf address adds VPN[3:0]*4.
A leaf stores PPN in bits 15:8 and valid/read/write/execute in bits 0/1/2/3.
The concrete service owns root addresses in `0x8000..0x83ff` and leaf addresses
in `0x1000..0x4fff`. ASID a uses the leaf window beginning at `0x1000+a*0x1000`;
its sixteen 64-byte leaf-table blocks are privately permuted within the first
1KiB of that window for each generation. Arbitrary physical page-table placement
outside this memory map is not part of the tested contract.
A successful result is PPN concatenated with the page offset. Fault 1 is invalid,
fault 2 is permission denied; fault results have data zero.

For the TLB task, `inv_valid` invalidates `inv_asid` at the clock edge. The service changes that
ASID's page tables at the same edge. Results first offered before that edge are
committed and remain stable; other outstanding requests must reflect the updated
tables. Multiple invalidations are supported. The client is stalled on an
invalidation edge; memory requests already offered remain stable until accepted.

## Qualification and limits

The independent software oracle reads concrete memory dictionaries; it does not
simulate the DUT state machine. A separate flat page map cross-checks every VPN,
ASID and access mode in unit tests. A transaction scoreboard checks every output
against that oracle and accounts for memory tokens, responses, stable interfaces,
reset cancellation and completion deadlines. RTL and mapped-netlist metrics must
match exactly. No Python-model pass counts as hardware qualification.

Directed probes require the configured concurrent MSHR capacity and a TLB working
set of the configured size that subsequently hits without external reads. The
TLB cache probe is unscored; MSHR capacity is checked in the required mixed-miss
burst, which is part of the scored workload. Tests exercise all words of a line, merging, independently
delayed returns, cache hits, invalid/permission faults, ASID aliases, cancellation,
in-flight invalidations and more than 96 completions. Fresh private tables, traffic
and backpressure supplement the directed probes. Default entry counts are 4/2/8;
held-out qualification adds a six-entry target and longer workloads.

Correctness precedes reward. Area, completion cycles, offered-to-completed latency
and external memory reads are compared to a fixed baseline on paired workloads,
with weights 0.45/0.30/0.15/0.10. Every case must remain within twice baseline cycles
and latency and 1.25 times its reads. Limits are 30000 generic cells, 96 gate levels,
20000 cycles per epoch and 2048 cycles per accepted request. Generic cells and
workload cycles are proxies; no routed frequency, power or silicon claim is made.
Formal and physical stages are not silently inferred from simulation.

## Run

```sh
python -m pip install .
export CHIP_RL_TRACE_ROOT=/absolute/private/evaluation-journals
python -m chip_rl.memory mshr --architecture ring --artifacts /tmp/mshr-run
python -m chip_rl.memory tlb --architecture dual --artifacts /tmp/tlb-run
python examples/memory_rollout.py tlb --cache /tmp/memory-cache
python -m chip_rl.memory.server --cache /tmp/memory-cache
```

The JSON interface accepts `reset(task,seed)` and `step(action)` with exactly
`{"rtl":"...candidate module..."}` as the action. Entry counts, test controls,
replay seeds and budgets are host-only. `MemoryEnv` exposes reset/step observations
with generated RTL and constraints. The episode seed does not select hidden tests.
Default journals retain qualification artifacts outside agent observations; see
[delivery and evidence retention](reproduction-v12.md). A separate OS sandbox is
still the deployment host's responsibility.

## Recorded v12 release measurements

The release package contains 88 runtime files, identical between the source tree,
the validation installation and a clean offline wheel installation. The only
previously existing runtime file changed since the public twenty-family checkpoint
is the private journal wrapper; the twelve new memory files implement these tasks.

Default qualification accepts both designs per task and rejects 15 MSHR and 17 TLB
mutants. Held-out qualification accepts both designs again. Together these are
24 RTL-and-mapped configuration checks. The installed JSON, CLI and library matrix
accepts 12 design checks and rejects 96 mutant checks; eight schema attacks and
four host budget violations are also rejected. These are finite tests, not proofs.

| Family / design | Four-entry generic cells | Paired aggregate cycle ratio | Reward |
|---|---:|---:|---:|
| MSHR circular baseline | 2207 | 1.0000 | 1.0000 |
| MSHR shifting alternative | 2174 | 1.0000 | 1.0038 |
| TLB one-walker baseline | 654 | 1.0000 | 1.0000 |
| TLB two-walker alternative | 944 | 0.5333 | 1.0321 |

Ratios use the geometric mean across the three default configurations, pairing each
candidate with its fixed baseline on the same private workload. The MSHR alternative
uses fewer generic cells with identical paired completion metrics. The two-walker
TLB uses more cells but completes the workload in fewer cycles. Its aggregate
latency ratio is 0.7839 and memory-read ratio 1.0284. Different evaluations use
different private seeds; compare their paired ratios, not unrelated raw cycle totals.
No routed clock period, power measurement or physical implementation was produced.

Replays from a clean offline install and a second installation of the same pinned
HDL tools reproduce MSHR, TLB and a rejected TLB mutant, including source, recipe,
contract, tool hashes, private workload hashes and all metrics. Private replay
inputs are delivered separately from agent-visible results. No formal run was
performed for either new family; earlier bounded results apply only to their
recorded small models. No learned RL policy is included.

The final existing-family regression also passed: pilot APIs accepted 18 checks and
rejected 237 faults; cycle JSON and library each accepted 8 and rejected 4; expansion
APIs accepted 78 and rejected 330; CDC APIs accepted 12 and rejected 9 schema attacks.
Including the memory APIs, that is 136 accepted and 671 fault-rejection checks.
Per-family API counts are in `evidence/v12/api-regression-counts.json`. This repeats
the existing API matrices, with extra cycle library coverage; it is not a rerun of
every historical standalone formal, physical or specialized deep-validation job.
