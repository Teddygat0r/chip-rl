"""CPU-only contract tests; no model downloads or CUDA calls."""
import sys
import types
import unittest
from unittest.mock import patch

from chip_rl.gpu_backend import (GPUPolicyBackend, _disable_dropout,
                                 _generation_config_kwargs,
                                 _teacher_forcing_ids, _validate_group)


def records(**changes):
    base = dict(group_id="one", group_size=2, policy_version=0,
                prompt_ids=[11, 12], completion_ids=[21, 22],
                temperature=1.0, top_p=1.0, finish_reason="eos")
    return [dict(base, candidate_index=i, **changes) for i in range(2)]


class BackendContractTest(unittest.TestCase):
    def test_teacher_forcing_masks_prompt_and_retains_all_completion_targets(self):
        ids, first = _teacher_forcing_ids([11, 12, 13], [21, 22])
        self.assertEqual(ids, [11, 12, 13, 21])
        self.assertEqual(first, 2)
        self.assertEqual(len(ids) - first, 2)
        self.assertEqual(_teacher_forcing_ids([11], [22]), ([11], 0))
        with self.assertRaises(ValueError):
            _teacher_forcing_ids([11], [])

    def test_full_group_current_policy_and_finite_advantages_required(self):
        _validate_group(records(), [1.0, -1.0], 0)
        with self.assertRaisesRegex(ValueError, "current policy"):
            _validate_group(records(), [1, -1], 1)
        with self.assertRaisesRegex(ValueError, "finite"):
            _validate_group(records(), [float("nan"), 0], 0)
        with self.assertRaisesRegex(ValueError, "missing candidate"):
            pair = records()
            pair[1]["candidate_index"] = 0
            _validate_group(pair, [1, -1], 0)

    def test_update_rejects_warped_or_timed_out_samples(self):
        with self.assertRaisesRegex(ValueError, "unwarped"):
            _validate_group(records(top_p=0.9), [1, -1], 0)
        with self.assertRaisesRegex(ValueError, "timed-out"):
            _validate_group(records(finish_reason="timeout"), [1, -1], 0)

    def test_fresh_sampling_config_does_not_inherit_top_k_or_processors(self):
        stale_model_config = dict(top_k=50, repetition_penalty=1.2,
                                  suppress_tokens=[4], forced_eos_token_id=3)
        config = _generation_config_kwargs(max_new_tokens=8, pad_token_id=2,
                                            eos_token_id=2, temperature=1.0, top_p=1.0)
        self.assertEqual(config["top_k"], 0)
        self.assertEqual(config["repetition_penalty"], 1.0)
        self.assertIsNone(config["suppress_tokens"])
        self.assertIsNone(config["forced_eos_token_id"])
        self.assertEqual(config["temperature"], 1.0)
        self.assertEqual(config["top_p"], 1.0)
        self.assertEqual(config["num_beams"], 1)
        self.assertEqual(stale_model_config["top_k"], 50)

    def test_prompt_limit_rejects_without_truncation(self):
        backend = GPUPolicyBackend.__new__(GPUPolicyBackend)
        def encode(text, add_special_tokens):
            self.assertFalse(add_special_tokens, "rendered chat prompts must not gain duplicate BOS")
            return [1, 2, 3]
        backend.tokenizer = types.SimpleNamespace(encode=encode)
        with self.assertRaisesRegex(ValueError, "no truncation"):
            backend._encode_prompt("prompt", 2)
        self.assertEqual(backend._encode_prompt("prompt", 3), [1, 2, 3])

    def test_actual_logprob_method_scores_completion_positions_only(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("NumPy unavailable")

        class Tensor:
            def __init__(self, value):
                self.value = np.asarray(value)
            def __getitem__(self, key):
                return Tensor(self.value[key])
            def float(self):
                return Tensor(self.value.astype(float))
            def gather(self, dim, index):
                return Tensor(np.take_along_axis(self.value, index.value, axis=dim))
            def squeeze(self, dim):
                return Tensor(np.squeeze(self.value, axis=dim))
            def __sub__(self, other):
                return Tensor(self.value - other.value)
            def sum(self):
                return Tensor(self.value.sum())

        fake_torch = types.SimpleNamespace(
            long="long", tensor=lambda values, dtype, device: Tensor(values),
            logsumexp=lambda values, dim: Tensor(np.logaddexp.reduce(values.value, axis=dim)))

        class Model:
            def __call__(self, input_ids, use_cache):
                self.seen = input_ids.value.tolist()
                self.use_cache = use_cache
                return types.SimpleNamespace(logits=Tensor([[
                    [100, 0, 0],  # prompt prediction: must be ignored
                    [0, 1, 2],    # predicts completion token 2
                    [2, 0, 1],    # predicts completion token 0
                ]]))

        backend = GPUPolicyBackend.__new__(GPUPolicyBackend)
        backend.torch = fake_torch
        backend.device = "cpu"
        backend.model = Model()
        value = backend._completion_logprob([0, 1], [2, 0]).value.item()
        expected = (2 - np.logaddexp.reduce([0, 1, 2])
                    + 2 - np.logaddexp.reduce([2, 0, 1]))
        self.assertAlmostEqual(value, expected)
        self.assertEqual(backend.model.seen, [[0, 1, 2]])
        self.assertFalse(backend.model.use_cache)

    def test_cuda_failure_precedes_hf_model_lookup(self):
        fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
        hf_api = unittest.mock.Mock()
        fake_hf = types.SimpleNamespace(HfApi=hf_api)
        fake_transformers = types.SimpleNamespace(AutoModelForCausalLM=object,
                                                  AutoTokenizer=object, BitsAndBytesConfig=object)
        fake_peft = types.SimpleNamespace(LoraConfig=object, get_peft_model=lambda *a: None,
                                          prepare_model_for_kbit_training=lambda *a: None)
        with patch.dict(sys.modules, {"torch": fake_torch, "huggingface_hub": fake_hf,
                                      "transformers": fake_transformers, "peft": fake_peft}):
            with self.assertRaisesRegex(RuntimeError, "available CUDA"):
                GPUPolicyBackend.load()
        hf_api.assert_not_called()

    def test_real_cpu_autograd_scoring_and_adapter_only_step_if_torch_available(self):
        try:
            import torch
            import torch.nn.functional as F
        except ImportError:
            self.skipTest("PyTorch unavailable")

        class TinyModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.base = torch.nn.Embedding(6, 6)
                self.base.requires_grad_(False)
                self.lora_delta = torch.nn.Parameter(torch.zeros(6, 6))
                self.dropout = torch.nn.Dropout(0.25)
                self.attention_dropout = 0.2

            def forward(self, input_ids, use_cache=False):
                logits = self.base(input_ids) + F.one_hot(input_ids, 6).float() @ self.lora_delta
                logits = self.dropout(logits)
                logits = F.dropout(logits, p=self.attention_dropout, training=self.training)
                return types.SimpleNamespace(logits=logits)

        torch.manual_seed(19)
        model = TinyModel()
        _disable_dropout(model, torch)
        self.assertEqual(model.dropout.p, 0)
        self.assertEqual(model.attention_dropout, 0)
        model.eval()
        eval_logits = model(torch.tensor([[1, 2, 3]])).logits
        model.train()
        train_logits = model(torch.tensor([[1, 2, 3]])).logits
        self.assertTrue(torch.equal(eval_logits, train_logits))
        backend = GPUPolicyBackend(model, None, torch, model_id="tiny",
                                   resolved_revision="0" * 40, device="cpu", seed=19,
                                   learning_rate=1e-2, lora_config={})
        prompt, completion = [1, 2], [3, 4]
        actual = backend._completion_logprob(prompt, completion)
        with torch.no_grad():
            logits = model(torch.tensor([[1, 2, 3]])).logits[0]
            expected = (F.log_softmax(logits[1], -1)[3]
                        + F.log_softmax(logits[2], -1)[4])
        self.assertTrue(torch.allclose(actual, expected))
        base_before = model.base.weight.detach().clone()
        group = records()
        for record in group:
            record["prompt_ids"] = prompt
            record["completion_ids"] = completion
        result = backend.update(group, [1.0, -0.25])
        self.assertEqual(result["policy_version"], 1)
        self.assertGreater(result["changed_parameter_tensors"], 0)
        self.assertTrue(torch.equal(model.base.weight, base_before))
        self.assertFalse(torch.equal(model.lora_delta, torch.zeros_like(model.lora_delta)))

        zero_model = TinyModel()
        _disable_dropout(zero_model, torch)
        zero_backend = GPUPolicyBackend(zero_model, None, torch, model_id="tiny",
                                        resolved_revision="0" * 40, device="cpu", seed=19,
                                        learning_rate=1e-2, lora_config={})
        with self.assertRaisesRegex(FloatingPointError, "did not change adapter"):
            zero_backend.update(group, [0.0, 0.0])
        self.assertEqual(zero_backend.policy_version, 0)
        self.assertTrue(torch.equal(zero_model.lora_delta,
                                    torch.zeros_like(zero_model.lora_delta)))


if __name__ == "__main__":
    unittest.main()
