"""Optional, single-GPU QLoRA backend for a bounded pilot.

Imports of GPU packages are deliberately deferred until ``load``.  A call to
``update`` is one on-policy group update using a sequence-level REINFORCE
surrogate, not a GRPO implementation.  No evaluator or reward is called here.
"""
from __future__ import annotations

import json
import hashlib
import math
from pathlib import Path
import time
import uuid


DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"


def _teacher_forcing_ids(prompt_ids: list[int], completion_ids: list[int]) -> tuple[list[int], int]:
    """Return model input IDs and first logits index predicting completion."""
    if not prompt_ids or not completion_ids:
        raise ValueError("prompt and completion must each contain at least one token")
    if any(type(token) is not int or token < 0 for token in prompt_ids + completion_ids):
        raise ValueError("token IDs must be nonnegative integers")
    return prompt_ids + completion_ids[:-1], len(prompt_ids) - 1


def _generation_config_kwargs(*, max_new_tokens: int, pad_token_id: int,
                              eos_token_id: int, temperature: float, top_p: float) -> dict:
    """Build a fresh config rather than inheriting non-neutral model warpers."""
    return dict(max_new_tokens=max_new_tokens, pad_token_id=pad_token_id,
                eos_token_id=eos_token_id, use_cache=True, do_sample=temperature > 0,
                temperature=temperature if temperature > 0 else 1.0,
                top_p=top_p if temperature > 0 else 1.0,
                top_k=0, repetition_penalty=1.0, no_repeat_ngram_size=0,
                typical_p=1.0, min_p=None, epsilon_cutoff=0.0, eta_cutoff=0.0,
                bad_words_ids=None, forced_bos_token_id=None,
                forced_eos_token_id=None, suppress_tokens=None,
                begin_suppress_tokens=None, min_length=0, min_new_tokens=None,
                sequence_bias=None, guidance_scale=None, token_healing=False,
                num_beams=1, diversity_penalty=0.0, constraints=None)


def _disable_dropout(model, torch) -> None:
    """Ensure train-mode checkpointed scoring has eval-mode probabilities."""
    for module in model.modules():
        if isinstance(module, torch.nn.modules.dropout._DropoutNd):
            module.p = 0.0
        for name, value in vars(module).items():
            if name.endswith("dropout") and isinstance(value, (float, int)):
                setattr(module, name, 0.0)
        config = getattr(module, "config", None)
        if config is not None:
            for name, value in vars(config).items():
                if name.endswith("dropout") and isinstance(value, (float, int)):
                    setattr(config, name, 0.0)


def _validate_group(records: list[dict], advantages: list[float], version: int) -> None:
    if not records or len(records) != len(advantages):
        raise ValueError("one finite advantage is required per candidate")
    group_id = records[0].get("group_id")
    if not group_id or any(r.get("group_id") != group_id for r in records):
        raise ValueError("update requires one complete generation group")
    if any(r.get("policy_version") != version for r in records):
        raise ValueError("candidates were not sampled from the current policy")
    if any(r.get("group_size") != len(records) for r in records):
        raise ValueError("update requires every candidate in the group")
    if {r.get("candidate_index") for r in records} != set(range(len(records))):
        raise ValueError("duplicate or missing candidate index")
    prompts = {tuple(r.get("prompt_ids", ())) for r in records}
    if len(prompts) != 1:
        raise ValueError("candidates must share one prompt")
    for record, advantage in zip(records, advantages):
        _teacher_forcing_ids(record["prompt_ids"], record["completion_ids"])
        if record.get("temperature") != 1.0 or record.get("top_p") != 1.0:
            raise ValueError("policy update requires unwarped temperature=1, top_p=1 sampling")
        if record.get("finish_reason") == "timeout":
            raise ValueError("timed-out completion cannot be used for update")
        if not isinstance(advantage, (float, int)) or not math.isfinite(advantage):
            raise ValueError("advantages must be finite numbers")


class GPUPolicyBackend:
    """One CUDA device, one frozen base, and trainable LoRA adapters.

    Use ``GPUPolicyBackend.load(...)``, then ``generate(prompt, ...)`` and
    ``update(records, advantages)``.  An update consumes one complete group
    before another policy version is sampled.  ``smoke`` exercises a separate
    supervised example; it does not claim any reward improvement.
    """

    def __init__(self, model, tokenizer, torch, *, model_id: str, resolved_revision: str,
                 device: str, seed: int, learning_rate: float, lora_config: dict):
        self.model = model
        self.tokenizer = tokenizer
        self.torch = torch
        self.model_id = model_id
        self.resolved_revision = resolved_revision
        self.device = device
        self.seed = seed
        self.learning_rate = learning_rate
        self.lora_config = lora_config
        self.policy_version = 0
        self._consumed_groups: set[str] = set()
        trainable = [p for p in model.parameters() if p.requires_grad]
        if not trainable:
            raise RuntimeError("PEFT exposed no trainable adapter parameters")
        non_adapter = [name for name, p in model.named_parameters()
                       if p.requires_grad and "lora_" not in name]
        if non_adapter:
            raise RuntimeError(f"non-LoRA trainable parameters found: {non_adapter[:3]}")
        self.optimizer = torch.optim.AdamW(trainable, lr=learning_rate)
        self.trainable_parameter_count = sum(p.numel() for p in trainable)
        self.total_parameter_count = sum(p.numel() for p in model.parameters())

    @classmethod
    def load(cls, model_id: str = DEFAULT_MODEL, revision: str | None = None,
             seed: int = 0, *, lora_r: int = 8, lora_alpha: int = 16,
             learning_rate: float = 1e-5) -> "GPUPolicyBackend":
        if not model_id or not isinstance(model_id, str):
            raise ValueError("model_id must be a nonempty Hugging Face model ID")
        if lora_r <= 0 or lora_alpha <= 0 or learning_rate <= 0:
            raise ValueError("LoRA settings and learning rate must be positive")
        try:
            import torch
            from huggingface_hub import HfApi
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        except ImportError as exc:
            raise RuntimeError("GPU backend needs torch, transformers, bitsandbytes, peft, and huggingface_hub") from exc
        if not torch.cuda.is_available():
            raise RuntimeError("GPU backend requires an available CUDA device")
        if not torch.cuda.is_bf16_supported():
            raise RuntimeError("GPU backend requires CUDA BF16 support")
        if torch.cuda.device_count() < 1:
            raise RuntimeError("CUDA reports no devices")
        # Resolve branch/tag once: all model and tokenizer files use this SHA.
        sha = HfApi().model_info(model_id, revision=revision).sha
        if not sha or len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha.lower()):
            raise RuntimeError("Hugging Face did not resolve an immutable model commit")
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        quantization = BitsAndBytesConfig(load_in_4bit=True,
                                         bnb_4bit_quant_type="nf4",
                                         bnb_4bit_use_double_quant=True,
                                         bnb_4bit_compute_dtype=torch.bfloat16)
        kwargs = dict(revision=sha, trust_remote_code=False,
                      quantization_config=quantization, device_map={"": 0},
                      torch_dtype=torch.bfloat16)
        try:
            model = AutoModelForCausalLM.from_pretrained(model_id, attn_implementation="sdpa", **kwargs)
        except (ValueError, ImportError, NotImplementedError):
            model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
        tokenizer = AutoTokenizer.from_pretrained(model_id, revision=sha, trust_remote_code=False)
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        model.config.use_cache = False
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
        model.gradient_checkpointing_enable()
        config = LoraConfig(r=lora_r, lora_alpha=lora_alpha, target_modules="all-linear",
                            lora_dropout=0.0, bias="none", task_type="CAUSAL_LM")
        model = get_peft_model(model, config)
        model.config.use_cache = False
        _disable_dropout(model, torch)
        model.gradient_checkpointing_enable()
        model.train()
        if not getattr(model, "is_gradient_checkpointing", False):
            raise RuntimeError("gradient checkpointing did not activate")
        device = "cuda:0"
        if any(p.requires_grad and not p.is_cuda for p in model.parameters()):
            raise RuntimeError("trainable adapters are not on CUDA")
        return cls(model, tokenizer, torch, model_id=model_id, resolved_revision=sha,
                   device=device, seed=seed, learning_rate=learning_rate,
                   lora_config=dict(r=lora_r, alpha=lora_alpha, dropout=0.0,
                                    target_modules="all-linear"))

    def device_info(self) -> dict:
        props = self.torch.cuda.get_device_properties(0)
        return dict(device=self.device, name=props.name,
                    total_memory_bytes=props.total_memory,
                    capability=list(self.torch.cuda.get_device_capability(0)),
                    bf16_supported=self.torch.cuda.is_bf16_supported(),
                    gradient_checkpointing=bool(getattr(self.model, "is_gradient_checkpointing", False)),
                    trainable_parameters=self.trainable_parameter_count,
                    total_parameters=self.total_parameter_count)

    def _encode_prompt(self, prompt: str, prompt_token_limit: int) -> list[int]:
        if not isinstance(prompt, str) or not prompt:
            raise ValueError("prompt must be nonempty text")
        if prompt_token_limit < 1:
            raise ValueError("prompt_token_limit must be positive")
        # Caller supplies the rendered chat template. Never insert another BOS.
        ids = self.tokenizer.encode(prompt, add_special_tokens=False)
        if not ids or len(ids) > prompt_token_limit:
            raise ValueError(f"prompt has {len(ids)} tokens; limit is {prompt_token_limit}; no truncation performed")
        return list(ids)

    def generate(self, prompt: str, *, num_candidates: int = 2,
                 max_new_tokens: int = 64, temperature: float = 1.0,
                 top_p: float = 1.0, prompt_token_limit: int = 1024,
                 max_time_s: float = 60.0) -> list[dict]:
        """Generate sequentially within one group wall budget.

        Returns a partial group if the deadline expires. Such records cannot
        be updated, and any record ending at the deadline says ``timeout``.
        """
        if num_candidates < 1 or max_new_tokens < 1:
            raise ValueError("num_candidates and max_new_tokens must be positive")
        if temperature < 0 or not 0 < top_p <= 1:
            raise ValueError("temperature must be nonnegative and top_p in (0, 1]")
        if not math.isfinite(max_time_s) or max_time_s <= 0:
            raise ValueError("max_time_s must be finite and positive")
        prompt_ids = self._encode_prompt(prompt, prompt_token_limit)
        torch = self.torch
        self.model.eval()
        group_id = uuid.uuid4().hex
        records = []
        torch.cuda.reset_peak_memory_stats(0)
        from transformers import GenerationConfig, StoppingCriteria, StoppingCriteriaList
        class Deadline(StoppingCriteria):
            def __init__(self, deadline):
                self.deadline = deadline
                self.expired = False

            def __call__(self, input_ids, scores, **kwargs):
                self.expired = time.monotonic() >= self.deadline
                return self.expired

        group_deadline = time.monotonic() + max_time_s
        for index in range(num_candidates):
            if time.monotonic() >= group_deadline:
                break
            inputs = torch.tensor([prompt_ids], dtype=torch.long, device=self.device)
            started = time.monotonic()
            deadline = Deadline(group_deadline)
            generation_config = GenerationConfig(**_generation_config_kwargs(
                max_new_tokens=max_new_tokens, pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id, temperature=temperature, top_p=top_p))
            with torch.no_grad():
                output = self.model.generate(input_ids=inputs,
                                             generation_config=generation_config,
                                             stopping_criteria=StoppingCriteriaList([deadline]))
            torch.cuda.synchronize(0)
            elapsed = time.monotonic() - started
            completion_ids = output[0, len(prompt_ids):].detach().cpu().tolist()
            timed_out = deadline.expired or time.monotonic() >= group_deadline
            finish_reason = ("timeout" if timed_out else
                             "eos" if completion_ids and completion_ids[-1] == self.tokenizer.eos_token_id
                             else "length" if len(completion_ids) >= max_new_tokens else "unknown")
            records.append(dict(group_id=group_id, group_size=num_candidates,
                                candidate_index=index, policy_version=self.policy_version,
                                model_id=self.model_id, resolved_revision=self.resolved_revision,
                                prompt_ids=prompt_ids.copy(), completion_ids=completion_ids,
                                completion=self.tokenizer.decode(completion_ids, skip_special_tokens=True),
                                prompt_tokens=len(prompt_ids), completion_tokens=len(completion_ids),
                                eos=bool(completion_ids and completion_ids[-1] == self.tokenizer.eos_token_id),
                                finish_reason=finish_reason, temperature=temperature, top_p=top_p,
                                sampling_config=_generation_config_kwargs(
                                    max_new_tokens=max_new_tokens,
                                    pad_token_id=self.tokenizer.pad_token_id,
                                    eos_token_id=self.tokenizer.eos_token_id,
                                    temperature=temperature, top_p=top_p),
                                generation_seconds=elapsed,
                                peak_generation_vram_bytes=torch.cuda.max_memory_allocated(0)))
            del inputs, output
            if timed_out:
                break
        return records

    def _completion_logprob(self, prompt_ids: list[int], completion_ids: list[int]):
        torch = self.torch
        input_ids, first_logit = _teacher_forcing_ids(prompt_ids, completion_ids)
        inputs = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        outputs = self.model(input_ids=inputs, use_cache=False)
        logits = outputs.logits[0, first_logit:first_logit + len(completion_ids)].float()
        targets = torch.tensor(completion_ids, dtype=torch.long, device=self.device)
        selected = logits.gather(-1, targets[:, None]).squeeze(-1)
        logprobs = selected - torch.logsumexp(logits, dim=-1)
        return logprobs.sum()

    def _adapter_snapshot(self) -> dict:
        return {name: p.detach().cpu().clone() for name, p in self.model.named_parameters()
                if p.requires_grad}

    def _adapter_diff(self, before: dict) -> dict:
        changed = 0
        max_abs = 0.0
        for name, p in self.model.named_parameters():
            if name in before:
                delta = (p.detach().cpu() - before[name]).abs()
                if bool((delta != 0).any().item()):
                    changed += 1
                max_abs = max(max_abs, float(delta.max().item()))
        return dict(changed_parameter_tensors=changed, max_abs_adapter_weight_change=max_abs)

    def update(self, records: list[dict], advantages: list[float]) -> dict:
        """One grouped, sequence-level policy-gradient surrogate optimizer step.

        Caller supplies reward-derived, detached advantages. No baseline, ratio,
        KL penalty, clipping, or reward computation is implied here.
        """
        _validate_group(records, advantages, self.policy_version)
        group_id = records[0]["group_id"]
        if group_id in self._consumed_groups:
            raise ValueError("generation group already consumed")
        torch = self.torch
        self.model.train()  # Needed for checkpointing; all dropout rates are zero.
        self.optimizer.zero_grad(set_to_none=True)
        before = self._adapter_snapshot()
        losses = []
        try:
            for record, advantage in zip(records, advantages):
                mean_logprob = self._completion_logprob(record["prompt_ids"],
                                                        record["completion_ids"])
                loss = -float(advantage) * mean_logprob / len(records)
                if not bool(torch.isfinite(loss).item()):
                    raise FloatingPointError("nonfinite policy-gradient loss")
                losses.append(float(loss.detach().item()))
                loss.backward()
            parameters = [p for p in self.model.parameters() if p.requires_grad]
            grad_norm = torch.nn.utils.clip_grad_norm_(parameters, max_norm=1.0,
                                                       error_if_nonfinite=True)
            self.optimizer.step()
        except Exception:
            self.optimizer.zero_grad(set_to_none=True)
            raise
        diff = self._adapter_diff(before)
        if diff["changed_parameter_tensors"] <= 0:
            raise FloatingPointError("optimizer step did not change adapter weights")
        self.policy_version += 1
        self._consumed_groups.add(group_id)
        return dict(loss=sum(losses), grad_norm=float(grad_norm.item()),
                    policy_version=self.policy_version, **diff)

    def smoke(self, prompt: str = "Write a one-line Verilog AND gate.",
              completion: str = "assign y = a & b;", *, prompt_token_limit: int = 64,
              max_new_tokens: int = 8, max_time_s: float = 60.0) -> dict:
        """Generate briefly, then run an independent fixed-label supervised step."""
        if not 1 <= max_new_tokens <= 64:
            raise ValueError("smoke max_new_tokens must be 1 to 64")
        prompt_ids = self._encode_prompt(prompt, prompt_token_limit)
        completion_ids = self.tokenizer.encode(completion, add_special_tokens=False)
        if not completion_ids or len(completion_ids) > 64:
            raise ValueError("smoke completion must contain 1 to 64 tokens")
        generated = self.generate(prompt, num_candidates=1,
                                  max_new_tokens=max_new_tokens,
                                  prompt_token_limit=prompt_token_limit,
                                  max_time_s=max_time_s)
        if not generated or generated[0]["finish_reason"] == "timeout":
            raise TimeoutError("smoke generation exceeded its deadline")
        torch = self.torch
        torch.cuda.reset_peak_memory_stats(0)
        before = self._adapter_snapshot()
        self.optimizer.zero_grad(set_to_none=True)
        started = time.monotonic()
        try:
            self.model.train()
            loss = -self._completion_logprob(prompt_ids, completion_ids)
            if not bool(torch.isfinite(loss).item()):
                raise FloatingPointError("nonfinite supervised smoke loss")
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_([p for p in self.model.parameters() if p.requires_grad],
                                                  max_norm=1.0, error_if_nonfinite=True)
            self.optimizer.step()
        except Exception:
            self.optimizer.zero_grad(set_to_none=True)
            raise
        torch.cuda.synchronize(0)
        self.policy_version += 1
        diff = self._adapter_diff(before)
        if diff["changed_parameter_tensors"] == 0:
            raise RuntimeError("supervised smoke step did not change adapter weights")
        return dict(device=self.device_info(), generation=generated[0],
                    supervised_loss=float(loss.detach().item()), grad_norm=float(norm.item()),
                    step_seconds=time.monotonic() - started,
                    peak_step_vram_bytes=torch.cuda.max_memory_allocated(0),
                    policy_version=self.policy_version, **diff)

    def save_adapter(self, directory: str | Path) -> dict:
        """Save PEFT adapter and tokenizer with immutable base identity metadata."""
        path = Path(directory)
        if path.exists() and any(path.iterdir()):
            raise FileExistsError(f"refusing to overwrite existing adapter directory: {path}")
        path.mkdir(parents=True, mode=0o700, exist_ok=True)
        self.model.save_pretrained(path, safe_serialization=True)
        self.tokenizer.save_pretrained(path)
        adapter_files = sorted(path.glob("adapter_model*.safetensors"))
        if not adapter_files:
            raise RuntimeError("adapter weights were not saved as safetensors")
        hashes = {file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in adapter_files}
        metadata = dict(model_id=self.model_id, resolved_revision=self.resolved_revision,
                        lora=self.lora_config, seed=self.seed,
                        learning_rate=self.learning_rate, policy_version=self.policy_version,
                        adapter_sha256=hashes)
        (path / "base_model_identity.json").write_text(json.dumps(metadata, indent=2) + "\n")
        return metadata
