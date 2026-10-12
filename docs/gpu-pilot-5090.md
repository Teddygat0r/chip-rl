# RTX 5090 Hadamard GPU pilot

This is a finite, first-family training feasibility run. It trains an adapter for **hadamard_int8 only**, on structural configurations **N=1, 2, 4 only**. It does not evaluate N=8/16 or the other four pilot families. Neither formal verification nor held-out validation nor physical PPA is included. No actual GPU training run was performed while preparing this launcher.

## Requirements and setup

Use Linux or WSL2 for `train` (the HDL judge uses POSIX process controls). `smoke` only needs CUDA and the Python packages. Confirm your RTX 5090 and CUDA driver with `nvidia-smi`. Training additionally needs the exact executables used by the judge: `yosys`, `yosys-abc`, `iverilog`, and `vvp`. The launcher checks paths, executable hashes, and versions **before downloading the model**. Check `which yosys yosys-abc iverilog vvp` in the same terminal. Install these from your trusted package source if absent. A locally configured `CHIP_RL_TOOLS` toolchain is also supported by the judge.

Use an environment outside this source checkout, then activate it. For example:

```bash
uv venv "$HOME/.venvs/chip-rl-gpu" --python 3.11
source "$HOME/.venvs/chip-rl-gpu/bin/activate"
uv pip install torch --index-url https://download.pytorch.org/whl/cu128
uv pip install transformers peft accelerate bitsandbytes huggingface_hub
uv pip install -e .
```

The CUDA 12.8 wheel index is listed in [PyTorch's official install history](https://pytorch.org/get-started/previous-versions/); check its [current install selector](https://pytorch.org/get-started/locally/) for your host before installation. Use `uv run --active --no-sync` from the clone so uv does not replace packages in the activated environment. The first run downloads the default Qwen2.5-Coder-7B-Instruct base model; allow substantial disk space, system RAM, time, and network access. The launcher has not established that every RTX 5090 setup has sufficient VRAM. It records the immutable model revision and CUDA/package versions at runtime.

First do the independent GPU plumbing check:

```bash
uv run --active --no-sync python -m chip_rl.gpu_pilot smoke --output /absolute/private/path/smoke-001
```

Smoke checks generation and **a real supervised adapter optimizer update**, including a changed-weight measurement. It is not a reinforcement-learning result. Use a **new** output directory for training, which loads a fresh adapter:

```bash
uv run --active --no-sync python -m chip_rl.gpu_pilot train --output /absolute/private/path/train-001
```

A lightweight plan check needs no GPU dependencies or CPU tools:

```bash
uv run --active --no-sync python -m chip_rl.gpu_pilot train --dry-run --output /absolute/private/path/dry-001
```

All output directories must be absolute, new, outside the repository, and without symlink ancestors. The launcher sets private directory/file permissions (0700/0600) and refuses overwrites. Keep these artifacts private: they contain generated sources, private workload seeds, finite-test logs, and adapter weights. Same-UID processes remain able to read files; these permissions are **not a security sandbox**.

## What the train command does

Defaults: two groups of two candidates, sampling temperature 1 and top-p 1, 2,048 maximum new tokens, 4,096 prompt-token limit, learning rate 1e-5, LoRA rank 8, seed 42, and 1,800 seconds of training wall budget. The wall budget starts **after model download/load**. Model download itself has no hard timeout; token generation checks the deadline between tokens, so an in-flight GPU kernel is not hard-preempted. Each HDL evaluation has an independent 180-second outer timeout and descendant-process cleanup. Every run is finite; no automatic retry or background monitoring is started.

Before generation, the launcher freezes the repo SHA, hashes of source/judge recipes, the exact rendered chat prompt and starter source, resolved model commit, Python/GPU package versions, tool fingerprints, and hyperparameters. A fresh private workload seed is drawn per group and used for each candidate and the sized_serial_butterfly strong reference at all three training configurations. Seeds, vectors, and logs are never placed in model prompts or reward feedback.

Each generated response must end with EOS and contain exactly one complete synthesizable `candidate` module. Missing EOS, truncation, extra modules, and oversize sources get reward zero. The existing finite `chip_rl.pilot.runner.run_case` judge checks source and mapped behavior at N=1, 2, and 4. The launcher uses its **candidate metrics** from a separate sized_serial_butterfly run as the strong reference. The judge's built-in `baseline` metrics are for the older serial_butterfly and are *not* used for this training reward.

A candidate gets zero if any training configuration fails correctness, has invalid metrics, or misses any fixed gate: generic cells ≤ 4 × strong-reference cells; workload cycles ≤ strong-reference cycles; and saturated initiation interval ≤ B+6, with B=(N/2)log₂N (B=0 for N=1). A qualified candidate gets `0.5 + 0.5 × max(0, 1 − sqrt(geometric_mean((candidate_cells/reference_cells) × (candidate_cycles/reference_cycles))))`. The strong reference itself scores 0.5; qualified gains score below 1. This is a **generic-cell/cycle proxy**, not routed physical performance.

The optimizer uses one on-policy grouped REINFORCE adapter step per group. The advantage for each sample is its reward minus the mean of the other samples' rewards. Sequence log probabilities are **summed** and the group loss is averaged over candidates. All-equal reward groups skip the update and report zero updates. This is not GRPO and includes no KL constraint. An incomplete generation group is never judged or updated. Missing tools, failed strong-reference checks, and outer evaluator timeouts abort separately from a candidate's reward-zero failure.

Review `freeze.json`, `attempts.jsonl`, `summary.json`, `final-adapter/`, and the private per-group folders in the output directory. The final summary records group/sample/correct/qualified/update counts, CPU/wall time, device statistics, and checkpoint hash when saving succeeded. It makes no improvement claim. Even a positive training proxy reward is not evidence of generalization or deployable silicon quality.
