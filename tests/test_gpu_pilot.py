"""CPU-only tests of the finite Hadamard GPU launcher."""
import argparse
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chip_rl import gpu_pilot as pilot
from chip_rl.hadamard_int8.rtl import design


def case(n, *, cells=100, cycles=100, ii=2, correct=True):
    return {'tested_correct': correct, 'metrics': {'candidate': {
        'cells': cells, 'workload_cycles': cycles,
        'stream_ii_numerator': ii, 'stream_ii_denominator': 1,
        'workload_sha256': f'work-{n}', 'watchdog_sha256': f'watch-{n}'}}}


def args(output, **kw):
    data = dict(command='train', output=str(output), dry_run=False,
                model='fake-model', revision='fake-sha', groups=1,
                candidates=2, max_new_tokens=64, prompt_limit=4096,
                learning_rate=1e-5, lora_r=8, seed=42, max_wall_seconds=30)
    data.update(kw)
    return argparse.Namespace(**data)


class GPUPilotTests(unittest.TestCase):
    def test_train_only_and_baseline_reward(self):
        self.assertEqual(pilot.TRAIN_CONFIGS, (1, 2, 4))
        self.assertEqual(pilot.TRAIN_CONFIGS, pilot.SPLITS['hadamard_int8']['train'])
        refs = {n: case(n) for n in pilot.TRAIN_CONFIGS}
        self.assertEqual(pilot.train_reward(refs, refs), (0.5, True, True))
        faster = {n: case(n, cells=50, cycles=50) for n in refs}
        reward, correct, qualified = pilot.train_reward(faster, refs)
        self.assertAlmostEqual(reward, 0.75)
        self.assertTrue(correct and qualified)
        for bad in ({n: case(n, cycles=101) for n in refs},
                    {n: case(n, cells=401) for n in refs},
                    {n: case(n, ii=100) for n in refs}):
            self.assertEqual(pilot.train_reward(bad, refs), (0, True, False))
        bad = dict(refs)
        bad[2] = case(2, correct=False)
        self.assertEqual(pilot.train_reward(bad, refs), (0, False, False))

    def test_nonfinite_and_pairing_rejected(self):
        refs = {n: case(n) for n in pilot.TRAIN_CONFIGS}
        bad = dict(refs)
        bad[1] = case(1, cells=float('nan'))
        with self.assertRaisesRegex(ValueError, 'nonpositive or nonfinite'):
            pilot.train_reward(bad, refs)
        bad[1] = case(1)
        bad[1]['metrics']['candidate']['workload_sha256'] = 'unpaired'
        with self.assertRaisesRegex(pilot.InfrastructureError, 'paired workload'):
            pilot.train_reward(bad, refs)
        bad[1] = case(1, correct=False)
        with self.assertRaisesRegex(pilot.InfrastructureError, 'strong reference'):
            pilot.train_reward(refs, bad)

    def test_extract_strict_complete_module(self):
        src = design('sized_serial_butterfly')
        self.assertEqual(pilot.extract_candidate(src, eos=True), src.strip() + '\n')
        self.assertEqual(pilot.extract_candidate('```verilog\n' + src.strip() + '\n```', eos=True), src.strip() + '\n')
        for completion, eos, reason in [(src, False, 'length'),
                                        (src + '\nmodule candidate; endmodule', True, 'eos'),
                                        ('```verilog\n' + src, True, 'eos'),
                                        ('module candidate; ', True, 'eos'),
                                        (src + '\nexplanation', True, 'eos')]:
            with self.subTest(reason=reason, completion=completion[-30:]):
                with self.assertRaises(ValueError):
                    pilot.extract_candidate(completion, eos=eos, finish_reason=reason)

    def test_prompt_omits_legacy_reward_and_no_heldout_claim(self):
        prompt, starter = pilot.prompt_and_source()
        self.assertEqual(starter, design('sized_serial_butterfly'))
        self.assertNotIn('All five N values must pass fixed gates:', prompt)
        self.assertIn('N=1,2,4', prompt)
        self.assertIn('No held-out results are provided to you', prompt)

    def test_private_new_absolute_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = pilot._output_directory(str(root / 'new'))
            self.assertEqual(out.stat().st_mode & 0o777, 0o700)
            with self.assertRaises(FileExistsError):
                pilot._output_directory(str(out))
            with self.assertRaisesRegex(ValueError, 'absolute'):
                pilot._output_directory('relative')
            link = root / 'link'
            link.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                pilot._output_directory(str(link / 'new'))
            with self.assertRaisesRegex(ValueError, 'outside'):
                pilot._output_directory(str(pilot.REPO / 'private-run'))

    def test_dry_run_never_imports_gpu_or_cpu_tools(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(pilot, '_tool_preflight', side_effect=AssertionError('tool preflight called')):
                result = pilot.run(args(root / 'dry', dry_run=True))
            self.assertEqual(result['status'], 'dry_run')
            freeze = json.loads((root / 'dry' / 'freeze.json').read_text())
            self.assertEqual(freeze['train_configs'], [1, 2, 4])
            self.assertEqual(freeze['resolved_model_revision'], 'not_resolved_dry_run')

    def test_zero_advantage_skips_update(self):
        class Tokenizer:
            def apply_chat_template(self, messages, **kwargs):
                return 'templated:' + messages[0]['content']
        class Backend:
            tokenizer = Tokenizer()
            resolved_revision = 'resolved-sha'
            torch = type('Torch', (), {'version': type('Version', (), {'cuda': '12.8'})})()
            @classmethod
            def load(cls, *args, **kwargs):
                return cls()
            def device_info(self):
                return {'name': 'fake GPU'}
            def generate(self, prompt, **kwargs):
                assert prompt.startswith('templated:')
                return [dict(completion=design('sized_serial_butterfly'), eos=True,
                             finish_reason='eos', completion_tokens=10, prompt_tokens=300,
                             generation_seconds=0.01) for _ in range(2)]
            def update(self, *args):
                raise AssertionError('equal rewards should skip update')
            def save_adapter(self, directory):
                (Path(directory) / 'adapter_model.safetensors').write_bytes(b'fake')
                return {'model_id': 'fake-model'}
        import chip_rl.gpu_backend as backend_module
        def fake_judge(source, n, seed, private_dir, cache, deadline):
            self.assertIn(n, (1, 2, 4))
            private_dir.mkdir(mode=0o700, parents=True)
            return case(n)
        with tempfile.TemporaryDirectory() as temporary, \
             patch.object(backend_module, 'GPUPolicyBackend', Backend), \
             patch.object(pilot, '_tool_preflight', return_value={'fake': 'tools'}), \
             patch.object(pilot, '_judge', side_effect=fake_judge):
            root = Path(temporary)
            result = pilot.run(args(root / 'train'))
            self.assertEqual(result['status'], 'completed')
            self.assertEqual((result['groups_completed'], result['samples'], result['optimizer_updates']), (1, 2, 0))
            self.assertIn('equal_rewards_zero_advantage', (root / 'train' / 'group-0' / 'update.json').read_text())
            rows = (root / 'train' / 'attempts.jsonl').read_text().splitlines()
            self.assertEqual([json.loads(row)['reward'] for row in rows], [0.5, 0.5])
            self.assertEqual((root / 'train' / 'private-seeds.jsonl').stat().st_mode & 0o777, 0o600)

    def test_evaluator_outer_timeout_kills_tree(self):
        class Proc:
            pid = 1234
            returncode = None
            def wait(self, timeout=None):
                if timeout:
                    raise subprocess.TimeoutExpired('judge', timeout)
                self.returncode = -9
        with tempfile.TemporaryDirectory() as temporary, \
             patch.object(pilot.subprocess, 'Popen', return_value=Proc()), \
             patch.object(pilot, '_kill_process_tree') as kill:
            root = Path(temporary)
            with self.assertRaisesRegex(pilot.InfrastructureError, 'wall timeout'):
                pilot._evaluate_subprocess('module candidate; endmodule', 1, 1,
                                           root / 'evaluation', root / 'cache', 0.01)
            kill.assert_called_once_with(1234)

    def test_candidate_tool_timeout_vs_missing_tool(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            judge = root / 'judge'
            judge.mkdir()
            (judge / 'private-error.txt').write_text("Rejected('hadamard-int8-synthesis: timeout')")
            self.assertFalse(pilot._judge_error_is_infrastructure({'error': {'type': 'Rejected'}}, root))
            (judge / 'private-error.txt').write_text("Rejected('missing required tool: yosys')")
            self.assertTrue(pilot._judge_error_is_infrastructure({'error': {'type': 'Rejected'}}, root))


if __name__ == '__main__':
    unittest.main()
