# Current task inventory

**25 families: six pilots, nineteen experimental.** API links point to the implementation, not a universal wrapper. “Current finite F/S” means the final v23 baseline regression has functional simulation and synthesis/mapped evidence: 22-family aggregate (private evaluation artifact retained locally), plus layout and softmax summary (private evaluation artifact retained locally). The [v27 reset audit](reset-audit-v27.md) adds targeted qualification for elastic/MSHR/router and current baseline regression across all 25 families, including the preserved requant exploit check. Other rows retain their historical alternate/mutant qualification evidence. The report in each row supplies design alternatives, faults and limitations from its own recorded version; those older campaigns were not all repeated in v23.

| Family | Purpose | Maturity | Agent API code | Contract/specification | Evidence |
|---|---|---|---|---|---|
| `elastic` | Elastic ready/valid storage | Pilot | [env.py](../chip_rl/env.py) | [contracts.md](contracts.md) | Current finite F/S; [iteration-v4.md](iteration-v4.md) |
| `dot` | Exact signed INT8 reduction | Pilot | [env.py](../chip_rl/env.py) | [contracts.md](contracts.md) | Current finite F/S; [iteration-v4.md](iteration-v4.md) |
| `scratchpad` | Banked arbitration and memory | Pilot | [env.py](../chip_rl/env.py) | [contracts.md](contracts.md) | Current finite F/S; [iteration-v4.md](iteration-v4.md) |
| `tensor` | Small exact INT8 matrix tile | Pilot | [env.py](../chip_rl/env.py) | [contracts.md](contracts.md) | Current finite F/S; [iteration-v4.md](iteration-v4.md) |
| `cache` | Direct-mapped write-through cache | Pilot | [env.py](../chip_rl/env.py) | [contracts.md](contracts.md) | Current finite F/S; [iteration-v4.md](iteration-v4.md) |
| `gather` | Irregular reads and stable compaction | Pilot | [env.py](../chip_rl/env.py) | [contracts.md](contracts.md) | Current finite F/S; [iteration-v4.md](iteration-v4.md) |
| `dma` | Contiguous word transfer with delayed responses | Experimental | [cycle/env.py](../chip_rl/cycle/env.py) | [cycle-contracts.md](cycle-contracts.md) | Current finite F/S; [iteration-v4.md](iteration-v4.md) |
| `router` | Five-port queued arbitration | Experimental | [cycle/env.py](../chip_rl/cycle/env.py) | [cycle-contracts.md](cycle-contracts.md) | Current finite F/S; [iteration-v4.md](iteration-v4.md) |
| `scoreboard` | Issue, dependencies and autonomous completion | Experimental | [cycle/env.py](../chip_rl/cycle/env.py) | [cycle-contracts.md](cycle-contracts.md) | Current finite F/S; [iteration-v4.md](iteration-v4.md) |
| `accelerator` | Concurrent DMA/load and MAC | Experimental | [cycle/env.py](../chip_rl/cycle/env.py) | [cycle-contracts.md](cycle-contracts.md) | Current finite F/S; [iteration-v4.md](iteration-v4.md) |
| `permute` | Register permutation | Experimental | [expansion/env.py](../chip_rl/expansion/env.py) | [../chip_rl/expansion/contracts.md](../chip_rl/expansion/contracts.md) | Current finite F/S; [expansion-v5.md](expansion-v5.md) |
| `coalesce` | Memory request coalescing | Experimental | [expansion/env.py](../chip_rl/expansion/env.py) | [../chip_rl/expansion/contracts.md](../chip_rl/expansion/contracts.md) | Current finite F/S; [expansion-v5.md](expansion-v5.md) |
| `retire` | Ordered retirement | Experimental | [expansion/env.py](../chip_rl/expansion/env.py) | [../chip_rl/expansion/contracts.md](../chip_rl/expansion/contracts.md) | Current finite F/S; [expansion-v5.md](expansion-v5.md) |
| `ecc` | SECDED encoding/decoding | Experimental | [expansion/env.py](../chip_rl/expansion/env.py) | [../chip_rl/expansion/contracts.md](../chip_rl/expansion/contracts.md) | Current finite F/S; [integrity-v6.md](integrity-v6.md) |
| `crc` | Packet CRC | Experimental | [expansion/env.py](../chip_rl/expansion/env.py) | [../chip_rl/expansion/contracts.md](../chip_rl/expansion/contracts.md) | Current finite F/S; [integrity-v6.md](integrity-v6.md) |
| `freelist` | Multi-allocation free list | Experimental | [expansion/env.py](../chip_rl/expansion/env.py) | [../chip_rl/expansion/contracts.md](../chip_rl/expansion/contracts.md) | Current finite F/S; [integrity-v6.md](integrity-v6.md) |
| `scan` | Segmented prefix scan | Experimental | [expansion/env.py](../chip_rl/expansion/env.py) | [../chip_rl/expansion/contracts.md](../chip_rl/expansion/contracts.md) | Current finite F/S; [collectives-v7.md](collectives-v7.md) |
| `topk` | Stable signed top-K | Experimental | [expansion/env.py](../chip_rl/expansion/env.py) | [../chip_rl/expansion/contracts.md](../chip_rl/expansion/contracts.md) | Current finite F/S; [collectives-v7.md](collectives-v7.md) |
| `histogram` | Collision-aware histogram | Experimental | [expansion/env.py](../chip_rl/expansion/env.py) | [../chip_rl/expansion/contracts.md](../chip_rl/expansion/contracts.md) | Current finite F/S; [collectives-v7.md](collectives-v7.md) |
| `cdc_fifo` | Independent-clock FIFO; constrained architecture actions | Experimental | [cdc/env.py](../chip_rl/cdc/env.py) | [../chip_rl/cdc/spec.py](../chip_rl/cdc/spec.py) | Current finite F/S; [cdc-v11.md](cdc-v11.md) |
| `mshr` | Miss merging and waiting requesters | Experimental | [memory/env.py](../chip_rl/memory/env.py) | [../chip_rl/memory/spec.py](../chip_rl/memory/spec.py) | Current finite F/S; [memory-v12.md](memory-v12.md) |
| `tlb` | Translation caching/page walking | Experimental | [memory/env.py](../chip_rl/memory/env.py) | [../chip_rl/memory/spec.py](../chip_rl/memory/spec.py) | Current finite F/S; [memory-v12.md](memory-v12.md) |
| `layout` | Bank-layout mapping around a fixed engine | Experimental | [layout/env.py](../chip_rl/layout/env.py) | [../chip_rl/layout/contracts.md](../chip_rl/layout/contracts.md) | Current finite F/S; [layout-audit-v20.md](layout-audit-v20.md) |
| `softmax` | Masked quantized approximate normalization | Experimental | [softmax/env.py](../chip_rl/softmax/env.py) | [../chip_rl/softmax/contracts.md](../chip_rl/softmax/contracts.md) | Current finite F/S; [softmax-review-v23.md](softmax-review-v23.md) |
| `requant` | Exact scale/round/zero-point/saturate datapath | Experimental | [requant/env.py](../chip_rl/requant/env.py) | [requant contract](../chip_rl/requant/contracts.md) | Finite F/S; [v26 reset repair](requant-reset-v26.md) |

## Entry points and scope

* Six pilots: `ChipEnv` in [env.py](../chip_rl/env.py), trusted CLI `python -m chip_rl TASK`, source-only server [server.py](../chip_rl/server.py), and [architectures](../chip_rl/architectures.py).
* Four fixed-cycle controllers: [cycle environment](../chip_rl/cycle/env.py), [server](../chip_rl/cycle/server.py), [reference models](../chip_rl/cycle/models.py), and [RTL](../chip_rl/cycle/rtl.py). They are not interchangeable with the older command-tick implementations in `tasks.py`.
* Nine expansion tasks: [environment](../chip_rl/expansion/env.py), [RTL catalog](../chip_rl/expansion/rtl.py), and trusted CLI `python -m chip_rl.expansion TASK`.
* CDC: [environment](../chip_rl/cdc/env.py), [RTL](../chip_rl/cdc/rtl.py), and `python -m chip_rl.cdc`; digital checks do not establish metastability/MTBF or physical CDC safety.
* MSHR/TLB: [environment](../chip_rl/memory/env.py), [oracles](../chip_rl/memory/oracles.py), [RTL](../chip_rl/memory/rtl.py), and `python -m chip_rl.memory TASK`.
* Requantization: [environment](../chip_rl/requant/env.py), [exact oracle](../chip_rl/requant/oracle.py), [catalog](../chip_rl/requant/rtl.py), and `python -m chip_rl.requant` JSON-lines server; [report and reproduction](requant-v24.md).
* Layout and softmax: their [layout](../chip_rl/layout/server.py) and [softmax](../chip_rl/softmax/server.py) module entry points run JSON-lines servers, not the pilot task CLI; see their contracts and reports before submitting actions.

The [quality environment](../chip_rl/quality/env.py) adds larger dot/tensor/TLB optimization profiles and its own [contract](../chip_rl/quality/contracts.md). These are **not three additional families**, and their interface, objectives and limits differ from the pilot/memory APIs. The [exact K16 proof](refinement-v18.md) concerns one quality dot instance, not every `dot` task. Historical bounded formal controls are documented in the linked version reports; the current aggregate did not rerun them. No row has family-wide formal proof, routed physical evidence or an independently demonstrated RL learning advantage.

The DMA here is contiguous word transfer, not a full misaligned 2D AXI implementation; the router is not a full NoC, the scoreboard has no execution datapath, and the accelerator is a small load/compute exercise. Consult contracts before treating task names as production component specifications.
