"""Bounded, train-only Hadamard INT8 adapter pilot for a local GPU.

The judge runs in a separate process. GPU dependencies are imported only after
CPU/tool preflight, and never by ``--dry-run``.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone

from .hadamard_int8.rtl import design
from .pilot.manifest import SPLITS

REPO = Path(__file__).resolve().parents[1]
TRAIN_CONFIGS = (1, 2, 4)
from .gpu_backend import DEFAULT_MODEL
MAX_SOURCE_BYTES = 100_000
EVALUATOR_TIMEOUT_S = 180.0


class InfrastructureError(RuntimeError):
    """Judge/tool failure; distinct from a generated candidate's failure."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)


def _write_private_exception(path: Path, exc: BaseException) -> None:
    path.write_text(''.join(traceback.format_exception(exc)))
    path.chmod(0o600)


def _output_directory(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("--output must be an absolute path")
    # Checking every ancestor prevents an attacker-controlled symlink from
    # redirecting private files into a repository or a shared location.
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink():
            raise ValueError("--output cannot contain a symlink")
    resolved = path.resolve()
    if resolved == REPO or resolved.is_relative_to(REPO):
        raise ValueError("--output must be outside the source repository")
    if path.exists():
        raise FileExistsError("--output must name a new directory")
    path.mkdir(mode=0o700, parents=True, exist_ok=False)
    path.chmod(0o700)
    return path


def prompt_and_source() -> tuple[str, str]:
    contract = (REPO / "chip_rl/hadamard_int8/contracts.md").read_text()
    paragraphs = contract.rstrip().split("\n\n")
    if not paragraphs[-1].startswith("All five N values must pass fixed gates:"):
        raise ValueError("Hadamard contract reward paragraph changed; review prompt")
    contract = "\n\n".join(paragraphs[:-1])
    starter = design("sized_serial_butterfly")
    prompt = (
        "Improve the following clocked Hadamard RTL. Return exactly one complete "
        "synthesizable candidate module, with the same parameterized interface, "
        "and no explanation. The legal parameter values remain N=1,2,4,8,16. "
        "This first-family pilot trains and evaluates only N=1,2,4. No held-out "
        "results are provided to you; do not evaluate them. Preserve correctness, ready/valid and reset "
        "behavior, including inactive output bits.\n\n"
        "Normative functional and protocol contract (the final legacy reward "
        "paragraph has been omitted because this run uses a separate train-only "
        "reward):\n" + contract + "\n\n"
        "Starter reference, sized_serial_butterfly. Preserve the parameterized "
        "candidate module interface:\n```verilog\n" + starter + "\n```\n\n"
        "Reply with one complete candidate module only."
    )
    return prompt, starter


def extract_candidate(completion: str, *, eos: bool, finish_reason: str | None = None) -> str:
    if not eos or finish_reason in {"length", "timeout", "error"}:
        raise ValueError("generation incomplete or missing EOS")
    if not isinstance(completion, str) or not completion.strip():
        raise ValueError("empty completion")
    text = completion.strip()
    if text.startswith("```"):
        match = re.fullmatch(r"```(?:verilog|systemverilog|sv)?[ \t]*\n(.*?)\n```", text,
                             flags=re.I | re.S)
        if not match:
            raise ValueError("expected exactly one complete fenced module")
        text = match.group(1).strip()
    elif "```" in text:
        raise ValueError("extra or partial code fence")
    if len(text.encode()) > MAX_SOURCE_BYTES:
        raise ValueError("candidate source exceeds size limit")
    if len(re.findall(r"\bmodule\s+candidate\b", text)) != 1 or len(re.findall(r"\bendmodule\b", text)) != 1:
        raise ValueError("expected exactly one candidate module")
    if not re.search(r"\bendmodule\s*$", text):
        raise ValueError("candidate module is truncated or has trailing text")
    from .evaluate import sanitize
    sanitize(text)
    return text + "\n"


def _positive(metric: dict, name: str) -> float:
    value = metric.get(name)
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError("nonpositive or nonfinite " + name)
    return float(value)


def train_reward(candidate_cases: dict[int, dict], reference_cases: dict[int, dict]) -> tuple[float, bool, bool]:
    """Return reward, all-tested-correct, gate-qualified. No held-out data."""
    if set(candidate_cases) != set(TRAIN_CONFIGS) or set(reference_cases) != set(TRAIN_CONFIGS):
        raise ValueError("reward requires exactly the three train configurations")
    if not all(reference_cases[n].get("tested_correct") is True for n in TRAIN_CONFIGS):
        raise InfrastructureError("strong reference failed finite validation")
    all_correct = all(candidate_cases[n].get("tested_correct") is True for n in TRAIN_CONFIGS)
    if not all_correct:
        return 0.0, False, False
    logs = []
    gates = []
    for n in TRAIN_CONFIGS:
        ca = candidate_cases[n]["metrics"]["candidate"]
        ref = reference_cases[n]["metrics"]["candidate"]
        for field in ("workload_sha256", "watchdog_sha256"):
            if not ca.get(field) or ca[field] != ref.get(field):
                raise InfrastructureError("candidate/reference paired workload mismatch")
        cells = _positive(ca, "cells")
        cycles = _positive(ca, "workload_cycles")
        ref_cells = _positive(ref, "cells")
        ref_cycles = _positive(ref, "workload_cycles")
        numerator = _positive(ca, "stream_ii_numerator")
        denominator = _positive(ca, "stream_ii_denominator")
        _positive(ref, "stream_ii_numerator")
        _positive(ref, "stream_ii_denominator")
        b = (n // 2) * (n.bit_length() - 1)
        gates.append(cells <= 4 * ref_cells and cycles <= ref_cycles
                     and numerator <= (b + 6) * denominator)
        logs.append((math.log(cells) - math.log(ref_cells))
                    + (math.log(cycles) - math.log(ref_cycles)))
    if not all(gates):
        return 0.0, True, False
    improvement = max(0.0, 1.0 - math.exp(sum(logs) / (2 * len(logs))))
    return 0.5 + 0.5 * improvement, True, True


def leave_one_out(rewards: list[float]) -> list[float]:
    if len(rewards) < 2:
        raise ValueError("at least two candidates required")
    total = sum(rewards)
    return [r - (total - r) / (len(rewards) - 1) for r in rewards]


def _tool_preflight() -> dict:
    # _tools.tool may resolve a repository-provided toolchain even if PATH does
    # not. The executable actually used by run_case is the one fingerprinted.
    from .evaluate import TrustedEvaluator
    from ._tools import tool
    tools = {}
    for name in ("yosys", "yosys-abc", "iverilog", "vvp"):
        path = Path(tool(name)).resolve()
        if not path.is_file() or not os.access(path, os.X_OK):
            raise InfrastructureError(f"required CPU tool unavailable: {name}")
        version_command = ([str(path), "-c", "version"] if name == "yosys-abc"
                           else [str(path), "-V"])
        version = subprocess.run(version_command,
                                 capture_output=True, text=True, timeout=15)
        tools[name] = {"path": str(path), "sha256": sha256_file(path),
                       "version": (version.stdout + version.stderr).splitlines()[:4],
                       "version_exit_code": version.returncode}
    # Verify judge's own tool fingerprint resolution before model download.
    # Constructor creates cache, so use a temporary location outside the repo.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="chip-rl-preflight-") as temp:
        tools["judge_tool_fingerprint"] = TrustedEvaluator(temp).tool_fingerprint
    return tools


def _git_sha() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                            text=True, check=True)
    return result.stdout.strip()


def _recipe_files() -> dict[str, str]:
    paths = [REPO / "chip_rl/gpu_pilot.py", REPO / "chip_rl/gpu_backend.py"]
    paths += sorted((REPO / "chip_rl").glob("*.py"))
    paths += sorted((REPO / "chip_rl/pilot").glob("*.py"))
    paths += sorted((REPO / "chip_rl/hadamard_int8").glob("*.py"))
    paths += [REPO / "chip_rl/hadamard_int8/contracts.md", REPO / "chip_rl/evaluate.py",
              REPO / "chip_rl/_tools.py"]
    return {str(path.relative_to(REPO)): sha256_file(path) for path in paths if path.exists()}


def _gpu_versions(backend) -> dict[str, str | None]:
    versions = {}
    for package in ("torch", "transformers", "peft", "bitsandbytes", "huggingface_hub"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    versions["torch_cuda"] = backend.torch.version.cuda
    return versions


def _cpu_seconds() -> float:
    if sys.platform != "linux":
        return 0.0
    import resource
    self_usage = resource.getrusage(resource.RUSAGE_SELF)
    child_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return (self_usage.ru_utime + self_usage.ru_stime + child_usage.ru_utime + child_usage.ru_stime)


def _evaluate_subprocess(source: str, n: int, seed: int, private_dir: Path,
                         cache_dir: Path, timeout_s: float) -> dict:
    """Run an independent judge process with wall timeout and process-group kill."""
    if n not in TRAIN_CONFIGS:
        raise ValueError("launcher may evaluate only train configurations")
    private_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    request = private_dir / "request.json"
    _write_json(request, {"source": source, "n": n, "seed": seed,
                          "artifacts": str(private_dir / "judge"), "cache": str(cache_dir)})
    result_file = private_dir / "result.json"
    log_file = private_dir / "evaluator.log"
    with log_file.open("w") as log:
        os.chmod(log_file, 0o600)
        proc = subprocess.Popen([sys.executable, "-m", "chip_rl.gpu_pilot", "_eval",
                                 str(request), str(result_file)], cwd=REPO, stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True)
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired as exc:
            # HDL tools start their own sessions in _tools.run. Kill the whole
            # descendant tree, rather than just this outer judge's process group.
            _kill_process_tree(proc.pid)
            proc.wait()
            raise InfrastructureError("evaluator wall timeout") from exc
    if proc.returncode or not result_file.is_file():
        raise InfrastructureError("evaluator process failed; see private evaluator log")
    return json.loads(result_file.read_text())


def _kill_process_tree(pid: int) -> None:
    """Best-effort Linux /proc descendant cleanup, including child sessions."""
    try:
        os.kill(pid, signal.SIGSTOP)  # stop the judge spawning new HDL children
    except ProcessLookupError:
        pass
    descendants: set[int] = set()
    for _ in range(3):
        parents: dict[int, list[int]] = {}
        for path in Path("/proc").iterdir():
            if not path.name.isdigit():
                continue
            try:
                stat = (path / "stat").read_text()
                ppid = int(stat[stat.rfind(")") + 2:].split()[1])
                parents.setdefault(ppid, []).append(int(path.name))
            except (OSError, ValueError, IndexError):
                continue
        frontier = [pid]
        while frontier:
            children = parents.get(frontier.pop(), [])
            descendants.update(children)
            frontier.extend(children)
        for child in sorted(descendants, reverse=True):
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _eval_child(request_path: Path, result_path: Path) -> None:
    from .pilot.runner import run_case
    request = json.loads(request_path.read_text())
    result = run_case("hadamard_int8", request["n"], request["source"], "train",
                      seed=request["seed"], private_artifacts=request["artifacts"],
                      cache_dir=request["cache"])
    _write_json(result_path, result)


def _judge_error_is_infrastructure(result: dict, private_dir: Path) -> bool:
    error = result.get("error") or {}
    if error.get("stage") == "tool_fingerprint":
        return True
    if not error:
        return False
    if error.get("type") not in {"Rejected"}:
        return True  # Unexpected judge exceptions are not evidence of model failure.
    detail = private_dir / "judge" / "private-error.txt"
    try:
        message = detail.read_text().lower()
    except OSError:
        return True
    return any(term in message for term in
               ("missing required tool", "no such file", "permission denied",
                "resource temporarily unavailable"))


def _remaining(deadline: float) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise InfrastructureError("run wall-clock budget exhausted")
    return left


def _judge(source: str, n: int, seed: int, private_dir: Path, cache: Path,
           deadline: float) -> dict:
    return _evaluate_subprocess(source, n, seed, private_dir, cache,
                                min(EVALUATOR_TIMEOUT_S, _remaining(deadline)))


def run(args: argparse.Namespace) -> dict:
    if tuple(SPLITS["hadamard_int8"]["train"]) != TRAIN_CONFIGS:
        raise InfrastructureError("train split changed; review launcher")
    if (args.groups < 1 or args.candidates < 2 or args.max_new_tokens < 1
            or args.prompt_limit < 1 or not 0 <= args.seed < 2**63):
        raise ValueError("invalid bounded generation settings")
    if (not math.isfinite(args.max_wall_seconds) or args.max_wall_seconds <= 0
            or args.lora_r <= 0 or not math.isfinite(args.learning_rate)
            or args.learning_rate <= 0):
        raise ValueError("invalid training limits")
    if args.command == "train" and not args.dry_run and sys.platform != "linux":
        raise InfrastructureError("training requires Linux or WSL2")
    os.umask(0o077)
    output = _output_directory(args.output)
    started = time.monotonic()
    cpu_start = _cpu_seconds()
    prompt, starter = prompt_and_source()
    if args.command == "smoke":
        prompt = "Write a one-line Verilog AND gate."
    tools = (_tool_preflight() if args.command == "train" and not args.dry_run
             else {"status": "not checked in smoke/dry-run"})
    common = {"schema": "chip-rl-gpu-pilot-freeze-v1", "mode": args.command,
              "scope": "first_family_train_only", "family": "hadamard_int8",
              "train_configs": list(TRAIN_CONFIGS), "formal": "not_run", "physical": "not_run",
              "heldout": "not_run", "reward_scope": "generic_cell_cycle_proxy",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "repo_sha": _git_sha(), "recipe_files_sha256": _recipe_files(),
              "contract_sha256": sha256_file(REPO / "chip_rl/hadamard_int8/contracts.md"),
              "prompt_sha256": sha256_bytes(prompt.encode()),
              "starter_sha256": sha256_bytes(starter.encode()),
              "model_id": args.model, "requested_model_revision": args.revision,
              "hyperparameters": {"seed": args.seed, "groups": args.groups,
                                   "candidates_per_group": args.candidates,
                                   "temperature": 1.0, "top_p": 1.0,
                                   "top_k": 0, "repetition_penalty": 1.0,
                                   "max_new_tokens": args.max_new_tokens,
                                   "prompt_token_limit": args.prompt_limit,
                                   "learning_rate": args.learning_rate,
                                   "lora_r": args.lora_r, "lora_alpha": 16,
                                   "lora_dropout": 0.0, "optimizer": "AdamW",
                                   "max_wall_seconds": args.max_wall_seconds},
              "tools": tools}
    if args.dry_run:
        common["resolved_model_revision"] = "not_resolved_dry_run"
        _write_json(output / "freeze.json", common)
        _write_json(output / "summary.json", {"status": "dry_run", "generation": "not_run",
                                               "optimizer_update": "not_run",
                                               "train_configs": list(TRAIN_CONFIGS)})
        return {"status": "dry_run", "output": str(output), "train_configs": list(TRAIN_CONFIGS)}

    # The backend import is deliberately after CPU tool preflight. This may
    # download the model, but no expensive download occurs with missing HDL tools.
    from .gpu_backend import GPUPolicyBackend
    try:
        backend = GPUPolicyBackend.load(args.model, revision=args.revision, seed=args.seed,
                                        lora_r=args.lora_r, learning_rate=args.learning_rate)
    except Exception as exc:
        _write_private_exception(output / "model-load-error.txt", exc)
        _write_json(output / "summary.json", {"status": "model_load_failed",
                                               "error_type": type(exc).__name__,
                                               "private_error": "model-load-error.txt",
                                               "generation": "not_run",
                                               "optimizer_update": "not_run"})
        raise InfrastructureError("model/CUDA load failed; see output summary") from exc
    model_load_seconds = time.monotonic() - started
    # Model download/load cannot safely be preempted within this process. The
    # finite wall budget begins after load; report startup duration separately.
    deadline = time.monotonic() + args.max_wall_seconds
    # Render the instruct-model chat template exactly once; the backend encodes
    # the supplied string verbatim and does not add another template.
    prompt = backend.tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}], tokenize=False,
        add_generation_prompt=True)
    common["prompt_sha256"] = sha256_bytes(prompt.encode())
    common["resolved_model_revision"] = backend.resolved_revision
    common["model_load_seconds"] = round(model_load_seconds, 3)
    common["wall_budget_scope"] = "after_model_load"
    common["device"] = backend.device_info()
    common["gpu_packages"] = _gpu_versions(backend)
    _write_json(output / "freeze.json", common)  # before any generation
    (output / "prompt.txt").write_text(prompt)
    (output / "prompt.txt").chmod(0o600)
    if args.command == "smoke":
        try:
            smoke = backend.smoke(prompt=prompt, prompt_token_limit=64,
                                  max_time_s=_remaining(deadline))
        except Exception as exc:
            _write_private_exception(output / "smoke-error.txt", exc)
            summary = {"status": "smoke_failed", "error_type": type(exc).__name__,
                       "private_error": "smoke-error.txt", "rl_result": "not_run"}
            _write_json(output / "summary.json", summary)
            return summary | {"output": str(output)}
        if smoke.get("changed_parameter_tensors", 0) <= 0:
            raise InfrastructureError("smoke optimizer did not change adapter weights")
        _write_json(output / "smoke.json", smoke)
        summary = {"status": "smoke_only", "generation": smoke.get("generation"),
                   "optimizer_update": {"policy_version": smoke.get("policy_version"),
                                        "changed_parameter_tensors": smoke.get("changed_parameter_tensors"),
                                        "supervised_loss": smoke.get("supervised_loss"),
                                        "peak_step_vram_bytes": smoke.get("peak_step_vram_bytes")},
                   "rl_result": "not_run", "wall_time_s": round(time.monotonic() - started, 3)}
        _write_json(output / "summary.json", summary)
        return summary | {"output": str(output)}

    cache = output / "cache"
    cache.mkdir(mode=0o700)
    ledger = output / "private-seeds.jsonl"
    attempts = output / "attempts.jsonl"
    groups_done = samples = correct = qualified = updates = 0
    status = "completed"
    try:
        for group in range(args.groups):
            _remaining(deadline)
            seed = secrets.randbits(128)
            with ledger.open("a") as file:
                file.write(json.dumps({"group": group, "seed": seed}) + "\n")
            ledger.chmod(0o600)
            reference = {}
            for n in TRAIN_CONFIGS:
                result = _judge(starter, n, seed, output / f"group-{group}" / f"reference-{n}", cache, deadline)
                if not result.get("tested_correct") or result.get("error"):
                    raise InfrastructureError(f"strong reference failed at N={n}; see private artifacts")
                try:
                    ref_metrics = result["metrics"]["candidate"]
                    for metric in ("cells", "workload_cycles", "stream_ii_numerator",
                                   "stream_ii_denominator"):
                        _positive(ref_metrics, metric)
                except (KeyError, TypeError, ValueError) as exc:
                    raise InfrastructureError(f"strong reference metrics invalid at N={n}") from exc
                reference[n] = result
            generated = backend.generate(prompt, num_candidates=args.candidates,
                                         max_new_tokens=args.max_new_tokens,
                                         temperature=1.0, top_p=1.0,
                                         prompt_token_limit=args.prompt_limit,
                                         max_time_s=_remaining(deadline))
            if len(generated) != args.candidates or any(r.get("finish_reason") == "timeout" for r in generated):
                # Never update an incomplete on-policy group. Retain completions
                # privately so the finite-budget stop is auditable.
                _write_json(output / f"group-{group}" / "incomplete-generation.json",
                            {"returned": len(generated), "requested": args.candidates,
                             "reason": "generation_budget_or_timeout", "records": generated})
                for record in generated:
                    samples += 1
                    with attempts.open("a") as file:
                        file.write(json.dumps({"group": group, "candidate": record.get("candidate_index"),
                                               "reward": None, "failure": "incomplete_generation",
                                               "completion_tokens": record.get("completion_tokens"),
                                               "generation_seconds": record.get("generation_seconds")}) + "\n")
                attempts.chmod(0o600)
                status = "generation_budget_exhausted"
                break
            rewards = []
            for i, record in enumerate(generated):
                attempt_started = time.monotonic()
                attempt_cpu_started = _cpu_seconds()
                samples += 1
                row = {"group": group, "candidate": i, "reward": 0.0,
                       "tested_correct": False, "qualified": False,
                       "completion_tokens": record.get("completion_tokens"),
                       "prompt_tokens": record.get("prompt_tokens"),
                       "generation_seconds": record.get("generation_seconds"),
                       "peak_generation_vram_bytes": record.get("peak_generation_vram_bytes"),
                       "eos": record.get("eos"), "finish_reason": record.get("finish_reason")}
                candidate_root = output / f"group-{group}" / f"candidate-{i}"
                candidate_root.mkdir(mode=0o700, parents=True)
                completion = record.get("completion", "")
                (candidate_root / "completion.txt").write_text(completion)
                (candidate_root / "completion.txt").chmod(0o600)
                try:
                    source = extract_candidate(completion, eos=record.get("eos") is True,
                                               finish_reason=record.get("finish_reason"))
                    row["source_sha256"] = sha256_bytes(source.encode())
                    (candidate_root / "candidate.sv").write_text(source)
                    (candidate_root / "candidate.sv").chmod(0o600)
                    cases = {}
                    for n in TRAIN_CONFIGS:
                        case_dir = candidate_root / f"train-{n}"
                        result = _judge(source, n, seed, case_dir, cache, deadline)
                        if _judge_error_is_infrastructure(result, case_dir):
                            raise InfrastructureError("candidate judge infrastructure failed")
                        cases[n] = result
                    reward, passed, gated = train_reward(cases, reference)
                    row.update(reward=reward, tested_correct=passed, qualified=gated)
                    if passed:
                        row["train_metrics"] = {}
                        for n in TRAIN_CONFIGS:
                            ca = cases[n]["metrics"]["candidate"]
                            ref = reference[n]["metrics"]["candidate"]
                            b = (n // 2) * (n.bit_length() - 1)
                            row["train_metrics"][str(n)] = {
                                "area_ratio": ca["cells"] / ref["cells"],
                                "completion_ratio": ca["workload_cycles"] / ref["workload_cycles"],
                                "stream_ii": ca["stream_ii_numerator"] / ca["stream_ii_denominator"],
                                "gates": {"cells": ca["cells"] <= 4 * ref["cells"],
                                          "cycles": ca["workload_cycles"] <= ref["workload_cycles"],
                                          "ii": ca["stream_ii_numerator"] <= (b + 6) * ca["stream_ii_denominator"]},
                                "workload_sha256": ca["workload_sha256"]}
                except InfrastructureError:
                    row["failure"] = "infrastructure_failure"
                    row["wall_time_s"] = round(time.monotonic() - attempt_started, 3)
                    row["cpu_time_s"] = round(_cpu_seconds() - attempt_cpu_started, 3)
                    with attempts.open("a") as file:
                        file.write(json.dumps(row, sort_keys=True) + "\n")
                    raise
                except (ValueError, TypeError) as exc:
                    row["failure"] = type(exc).__name__
                row["wall_time_s"] = round(time.monotonic() - attempt_started, 3)
                row["cpu_time_s"] = round(_cpu_seconds() - attempt_cpu_started, 3)
                with attempts.open("a") as file:
                    file.write(json.dumps(row, sort_keys=True) + "\n")
                attempts.chmod(0o600)
                rewards.append(row["reward"])
                correct += int(row["tested_correct"])
                qualified += int(row["qualified"])
            advantages = leave_one_out(rewards)
            if any(abs(a) > 1e-12 for a in advantages):
                update = backend.update(generated, advantages)
                updates += 1
            else:
                update = {"skipped": "equal_rewards_zero_advantage"}
            _write_json(output / f"group-{group}" / "update.json", update)
            groups_done += 1
    except (InfrastructureError, KeyboardInterrupt) as exc:
        status = "aborted_infrastructure" if isinstance(exc, InfrastructureError) else "interrupted"
        _write_json(output / "abort.json", {"status": status, "reason": str(exc)})
    except Exception as exc:
        status = "aborted_runtime"
        _write_private_exception(output / "runtime-error.txt", exc)
        _write_json(output / "abort.json", {"status": status, "error_type": type(exc).__name__,
                                            "private_error": "runtime-error.txt"})
    adapter = output / "final-adapter"
    adapter.mkdir(mode=0o700)
    adapter_metadata = None
    checkpoint_hash = None
    try:
        adapter_metadata = backend.save_adapter(str(adapter))
        checkpoint_hash = sha256_bytes(b"".join(
            sha256_file(path).encode() for path in sorted(adapter.rglob("*")) if path.is_file()))
    except Exception as exc:
        status = "checkpoint_failed"
        _write_private_exception(output / "checkpoint-error.txt", exc)
    summary = {"status": status, "groups_completed": groups_done, "samples": samples,
               "correct": correct, "qualified": qualified, "optimizer_updates": updates,
               "checkpoint_sha256": checkpoint_hash, "adapter_metadata": adapter_metadata,
               "model_revision": backend.resolved_revision,
               "model_load_seconds": round(model_load_seconds, 3),
               "prompt_sha256": common["prompt_sha256"],
               "config_sha256": sha256_file(output / "freeze.json"),
               "wall_time_s": round(time.monotonic() - started, 3),
               "cpu_time_s": round(_cpu_seconds() - cpu_start, 3),
               "device": backend.device_info(), "claim": "train-only pilot attempt"}
    _write_json(output / "summary.json", summary)
    return summary | {"output": str(output)}


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "_eval":
        _eval_child(Path(argv[1]), Path(argv[2]))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("smoke", "train"))
    parser.add_argument("--output", required=True, help="absolute, new directory outside repository")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--revision")
    parser.add_argument("--groups", type=int, default=2)
    parser.add_argument("--candidates", type=int, default=2)
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument("--prompt-limit", type=int, default=4096)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--lora-r", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-wall-seconds", type=float, default=1800)
    args = parser.parse_args(argv)
    try:
        result = run(args)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] in ("dry_run", "smoke_only", "completed") else 1
    except (ValueError, FileExistsError, InfrastructureError) as exc:
        parser.exit(2, f"gpu pilot: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
