# chip-rl: constrained RTL design environments

`chip-rl` lets an agent submit synthesizable RTL for small circuit-design tasks, then checks behavior with independent models and HDL simulation, synthesizes the design, and reports cost proxies against fixed baselines. Reward-bearing families also score those proxies. It is a research benchmark for exploring ASIC/GPU building blocks. Its benchmark scores are generic proxies, not routed timing, power, silicon readiness or learned-agent gains.

The underlying published checkpoint on [`codex/verified-33-family-checkpoint`](https://github.com/Teddygat0r/chip-rl/tree/codex/verified-33-family-checkpoint) exposes **33 distinct family APIs**: six pilots and 27 experimental tasks. The [prior published 25-family checkpoint](https://github.com/Teddygat0r/chip-rl/tree/codex/verified-25-family-checkpoint) is a separate, earlier publication at root commit `4e3d4f07ebc3b84daedb0317e4801ae64b005b39`. This checkpoint also includes [fused INT8 dot-plus-requant](docs/current-status.md), [compressed 2-of-4 sparse dot-plus-requant](docs/current-status.md), [block quantization](docs/block-quant-reward-v37.md), [exact integer RMS](docs/integer-rms-v1-phase2.md), [block RLE](docs/block-rle-v1-phase2.md), [block frame-of-reference packing](docs/block-for-v1-phase2.md), and [exact BF16-to-INT8 quantization](docs/bf16-quant-v1-phase2.md), and [INT8 Hadamard transforms](docs/hadamard-int8-v1-phase2.md). All 27 experimental families have conditional, task-specific reward rules. Reference variants, quality profiles and long-history verification modes do not add families. The [current status](docs/current-status.md), [one-row-per-family inventory](docs/task-inventory.md) and [machine-readable inventory](evidence/current-inventory.json) separate current source APIs from version-scoped evidence. This 33-family checkpoint is published on its own branch; version-specific evidence limits below still apply.

A [bounded N=4 integer RMS physical reference comparison](docs/rms-physical-reference-v1.md) now records two completed Nangate45 GDS routes under one generous 100 ns constraint. Both reference-deck DRC checks timed out incomplete; there is no physical signoff or change to any benchmark reward.

The [v37 block quantization qualification](docs/block-quant-reward-v37.md) validates serial, fully parallel and chunked-four references at N={1,2,4,8,16} with the fixed proxy gates; [v36](docs/block-quant-v36.md) is the historical measurement-only result. A [three-seed sensitivity check](docs/block-quant-sensitivity-v38.md) records workload-dependent score and cycle margins without changing those gates. The historical v33 consolidated default check reported 27 baseline passes and two pipelined-reference passes. Its raw summary is not present in this source snapshot; see [current status](docs/current-status.md) for the evidence scope. Recent family qualifications and the [post-Hadamard 240/240 source unit run](evidence/hadamard-int8-v1/integration-verification.json) are separate results, not a fresh 33-family simulation sweep.

## Five-family pilot and local GPU entry point

This branch includes the [five-family reference checkpoint](docs/five-family-pilot-checkpoint.md) and an experimental [5090/uv GPU setup and launcher](docs/gpu-pilot-5090.md). Start with the GPU smoke command in that guide. The training launcher currently covers **Hadamard TRAIN parameters only**, with a fixed stronger reference and grouped REINFORCE LoRA updates; it does not yet run the full five-family training experiment or held-out evaluation. CPU integration and tiny-model autograd tests are distinct from a real CUDA/model run, which remains unverified here. A run with equal candidate rewards explicitly skips optimizer updates.

## Three-step quickstart

1. Provide Python 3.10+, Icarus Verilog 12 and Yosys with ABC on `PATH`, or set `CHIP_RL_TOOLS` to the prefix containing their `bin/` directory. No paid service or model API is needed.

2. From this repository root, run the normal source tests:

   ```sh
   python -m unittest discover -s tests
   ```

3. Run one source-only agent episode (the host keeps evaluation workloads and replay seeds private):

   ```sh
   python - <<'PY'
   from chip_rl.sparse24.env import Sparse24Env
   from chip_rl.sparse24.rtl import design
   env = Sparse24Env(g=1, horizon=1, cache='/tmp/chip-rl-demo-cache')
   observation, _ = env.reset(seed=1)
   observation, reward, _, _, info = env.step({'rtl': design('pipeline')})
   print(info['tested_correct'], info['reward_qualified'], reward)
   PY
   ```

The episode may take minutes because it runs real synthesis and RTL/mapped simulation. `reset(seed)` controls the episode, not the evaluator's private workload. Use a trusted cache and artifact location outside the candidate's reach.

To repeat the scored block quantization comparison, run `python scripts/qualify_block_quant_v37.py --cache /tmp/chip-rl-block-quant-cache --out /tmp/chip-rl-block-quant-v37-summary.json --private /tmp/chip-rl-block-quant-v37-private`. It draws a private seed; the [v37 report](docs/block-quant-reward-v37.md) lists scores, rejected gates and limits.

To repeat the sparse24 parameter comparison, run `python scripts/qualify_sparse24_v35.py --cache /tmp/chip-rl-sparse24-v35-cache --out /tmp/chip-rl-sparse24-v35-summary.json --private /tmp/chip-rl-sparse24-v35-private`. It draws one private root seed; the the historical v35 comparison is summarized in [current status](docs/current-status.md); its original report is not included in this snapshot.

Read [current status](docs/current-status.md) first for task and API selection, then the linked family contract before editing RTL. The [task inventory](docs/task-inventory.md), [machine-readable inventory](evidence/current-inventory.json), and [report index](docs/README.md) give source entry points and evidence by version. Older v32-v37 references in retained reports are historical and may point to artifacts absent from this local snapshot.
