# Expansion batch 1: vector routing, request coalescing, and retirement

Status: experimentally qualified on finite tests. These three families are not
included in the six-pilot count. The published v4 branch and
its commit remain unchanged. V5 work is local until publishing is authorized.

The suite previously covered ready/valid buffering, arithmetic, bank arbitration,
address/data movement, packet output queues, issue hazards, a cache, and memory gather.
The new batch targets three different gaps:

- `permute`: dynamic register-vector selection, including masks, duplicates and
  out-of-range indices. This is a crossbar/serialization problem, not memory gather.
- `coalesce`: compress active lane requests into unique aligned memory segments
  with exact source-lane masks and stable group order. It does not transfer data.
- `retire`: hold independently completed operations until they can retire in order,
  including backpressure, full-buffer replacement, flush and stale completions.

Source contracts are packaged in `chip_rl/expansion/contracts.md`. All three have
source-only reset/step APIs, CLI and JSON entry points. Permute/coalesce admit varied
latency under the existing explicit optimization goals. Retire fixes physical cycles
and permits internal area optimization; it is not scored as a latency optimization.
Shared changes add three entries to the synthesis depth-limit registry and enforce
explicitly lowered cycle budgets in the older physical-cycle simulator. Existing
default family contracts and workloads are unchanged.

## Reference and reuse review (2026-10-06)

- [BOOM ROB documentation](https://docs.boom-core.org/en/latest/sections/reorder-buffer.html)
  describes in-order commit after execution finishes out of order. This task omits
  rename maps, exception handling, ISA execution and speculative memory ordering.
- [NVIDIA CUDA best practices](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html)
  motivates grouping lane accesses by aligned memory segments. Our 4/6/8-lane,
  8/16/32-byte abstraction is not a model of a specific NVIDIA GPU transaction unit.
- [RISC-V vector specification](https://github.com/riscvarchive/riscv-v-spec/blob/master/v-spec.adoc)
  provides context for indexed register permutation. This block is not RVV compliant:
  it has no vtype, vstart, LMUL or mask-undisturbed architectural state.

Only public explanatory material was consulted. No source, RTL, test vectors,
benchmark datasets or document passages were incorporated. All implementation and
oracles are original project code under the repository's license. No CUDA binaries,
proprietary IP or paid services are dependencies. The existing external Icarus/Yosys
license audit continues to apply.

## Reproduce

```bash
python -m unittest discover -s tests -v
python -m chip_rl.expansion permute --cache /tmp/chip-cache
python -m chip_rl.expansion.suite --output /tmp/expansion-q --cache /tmp/chip-cache
PYTHONPATH=. python scripts/check_expansion_holdouts.py --qualification /tmp/expansion-q/summary.json --output /tmp/expansion-holdouts --cache /tmp/chip-cache
PYTHONPATH=. python scripts/reproduce_expansion_formal.py --output /tmp/expansion-formal
python -m chip_rl.expansion.server --cache /tmp/chip-cache
```

Install the wheel in a separate environment and run, from outside the source tree:

```bash
python /path/to/chip-rl/scripts/check_expansion_apis.py --output /tmp/expansion-api --cache /tmp/chip-cache
```

The API script checks every catalog design and adversarial source through JSON,
CLI and the library using default coverage, plus invalid requests attempting to
change seeds, budgets or goals. Development uses a fixed host seed; actual actions
and frozen structural checks use fresh private randomness. Raw replay vectors and
logs stay in host-private artifact directories. No quick-profile success is exposed.

## Scope and limitations

Generic mapped cells and logic depth are proxies. No routed timing, power, SRAM
macro, unbounded formal proof, policy training or production security claim is made.
The dedicated OS sandbox remains unavailable. Resource limits and source restrictions
do not replace an external VM/container/account boundary for untrusted agents.
Finite streams, public dimension choices and author-created mutants can be overfit;
prospective splits and private instances are evidence rather than exhaustive proofs.
Ticket identity is finite (16 bits), with the reset/wrap semantics stated in the contract.


## Executed batch-1 results

The final suite accepted **9 valid implementations** and rejected **30 RTL mutants**.
Every accepted source ran both RTL and mapped-netlist simulation on all mandatory
cases. Installed library/CLI/JSON checks accepted all **27 valid-design/API pairs**,
rejected all **90 mutant/API pairs**, and rejected **9 schema override attempts**.
Six frozen-source structural cases passed at six-lane, 12-bit, 32-byte-segment and
six-entry configurations. These dimensions are public stress cases; no secrecy or
learned generalization claim is made. Host goal selection was checked through the
real JSON server: a valid serial coalescer has area reward >1 but is ineligible for
balanced/latency goals. Agent requests cannot change that host choice.

All **54 unit tests** passed, including in a fresh checkout. Fresh-cache coalescer
and retirement checks passed with the independently installed HDL toolchain. All
44 installed runtime Python/contract files matched implementation commit
`97ebf6b0d8b329da704baf01c90fb86ab4121e04` byte-for-byte.

Regression: the existing six-pilot default API matrix passed **219 bad-source
rejections and 18 baselines**. The existing four-controller suite passed **13 valid
designs and 28 mutant rejections**. The earlier six-pilot architecture search was not
repeated; these are precisely the default-API and controller regressions stated.

Bounded symbolic permutation safety passed at four 8-bit lanes over eight clocks
for parallel, naïve serial and shift-serial implementations. A reversed-output
control failed. This is one new bounded-formal family, not unbounded liveness,
full-size proof or a default API formal stage. There are zero new physical results.

| Design | Default cells | Cell ratio | Cycle ratio | Area reward | Balanced reward |
|---|---:|---:|---:|---:|---:|
| permute baseline | 1,165 | 1 | 1 | 1 | 1 |
| permute decoded | 2,229 | 1.913 | 1 | .762 | .858 |
| permute naïve serial | 2,177 | 1.869 | 5.550 | .624 | 0 |
| permute shift-serial | 480 | .412 | 5.550 | 1.114 | 0 |
| coalesce baseline | 5,333 | 1 | 1 | 1 | 1 |
| coalesce serial | 1,004 | .188 | 5.550 | 1.347 | 0 |

The shift-serial permutation replaces variable-position extraction/writes with
shifting index/mask/result registers, creating an actual area/latency tradeoff.
The other two permutation alternatives are dominated in this workload; keeping them
makes the finite search comparison honest. Zero balanced reward means correct but
goal-ineligible. Serial offered latency increases about 83x for permutation and 84x
for coalescing under these mixed offered workloads; the area goal explicitly accepts
that tradeoff and must not be presented as general performance improvement.

Retirement preserves fixed cycles: circular baseline is 1,885 cells, shift queue
2,773, and pruning unobservable data resets yields 1,760 at the default configuration.
The pruned reward is 1.034 across mandatory dimensions, with prospective six-entry
scores around 1.054–1.057. None of these numbers imply physical clock frequency.

Warm-cache qualification cost per valid candidate was about 4.8–10.7s for permutation,
19.3–21.0s for coalescing and 1.8–2.3s for retirement, with concurrent work on four CPU
cores. These are observed costs, not controlled benchmarks. Full per-candidate
metrics, code hashes and results are in `evidence/v5`; raw private replay artifacts
remain under `/workspace/chip-rl-v5-final-*`. `scripts/summarize_v5.py` recreates the
compact report. No policy was trained or search advantage established.

The suite now contains 13 runnable families: six pilots and seven experimental
families. This batch and its evidence remain local; v4 is the latest approved push.
