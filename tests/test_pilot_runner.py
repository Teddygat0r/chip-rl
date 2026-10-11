import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from chip_rl.pilot.manifest import frozen_manifest
from chip_rl.pilot.runner import run_case


class PilotRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    @patch('chip_rl.pilot.runner.TrustedEvaluator')
    @patch('chip_rl.pilot.runner._new_family_case')
    def test_one_explicit_config_and_no_private_seed_in_public_result(self, adapter, evaluator):
        evaluator.return_value.tool_fingerprint = 'fingerprint'
        adapter.return_value = ({'candidate': {'cells': 2}, 'baseline': {'cells': 4}}, 'contract', 1)
        result = run_case('block_quant', 1, 'module candidate(); endmodule', 'train', seed=123,
                          private_artifacts=self.root / 'artifacts')
        self.assertTrue(result['tested_correct'])
        self.assertEqual(result['config'], 1)
        self.assertEqual(result['workload_replays'], 1)
        self.assertEqual(result['tool_fingerprint'], 'fingerprint')
        self.assertNotIn('\"seed\": 123', json.dumps(result))
        adapter.assert_called_once()
        self.assertEqual(adapter.call_args.args[:3], ('block_quant', 1, 'module candidate(); endmodule'))
        self.assertEqual(json.loads((self.root / 'artifacts/private-replay.json').read_text())['seed'], 123)

    @patch('chip_rl.pilot.runner.TrustedEvaluator')
    @patch('chip_rl.pilot.runner._new_family_case')
    def test_failure_cannot_be_reported_as_success(self, adapter, evaluator):
        evaluator.return_value.tool_fingerprint = 'fingerprint'
        adapter.side_effect = RuntimeError('missing probe evidence')
        result = run_case('sparse24', 1, 'module candidate(); endmodule', 'train', seed=123,
                          private_artifacts=self.root / 'artifacts')
        self.assertFalse(result['tested_correct'])
        self.assertEqual(result['validation'], 'rejected')
        self.assertEqual(result['error']['stage'], 'single_configuration_case')
        self.assertNotIn('missing probe evidence', json.dumps(result))
        self.assertIn('missing probe evidence', (self.root / 'artifacts/private-error.txt').read_text())
        self.assertIsNone(result['metrics'])

    @patch('chip_rl.pilot.runner.TrustedEvaluator')
    @patch('chip_rl.pilot.runner._new_family_case')
    def test_dev_requires_matching_preregistered_manifest(self, adapter, evaluator):
        evaluator.return_value.tool_fingerprint = 'fingerprint'
        source = 'module candidate(); endmodule'
        with self.assertRaisesRegex(ValueError, 'requires'):
            run_case('block_quant', 3, source, 'dev', seed=123,
                     private_artifacts=self.root / 'missing')
        p = self.root / 'frozen.json'
        p.write_text(json.dumps(frozen_manifest('block_quant', source)))
        adapter.return_value = ({'candidate': {}, 'baseline': {}}, 'contract', 1)
        result = run_case('block_quant', 3, source, 'dev', seed=123,
                          private_artifacts=self.root / 'artifacts', frozen_manifest_path=p)
        self.assertTrue(result['tested_correct'])
        self.assertIsNotNone(result['frozen_manifest_sha256'])
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            run_case('block_quant', 5, source + '\n', 'dev', seed=123,
                     private_artifacts=self.root / 'other', frozen_manifest_path=p)
        self.assertEqual(adapter.call_count, 1)

    def test_private_artifacts_must_be_outside_repo(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            run_case('block_quant', 1, 'module candidate(); endmodule', 'train', seed=1,
                     private_artifacts=Path(__file__).resolve().parents[1] / 'private')

class PilotProbeTests(unittest.TestCase):
    def test_sparse24_rejects_missing_reset_evidence_before_success(self):
        from chip_rl.pilot.runner import _new_family_case
        from chip_rl.evaluate import Rejected, digest
        from chip_rl.sparse24 import decoder_check, rtl, scoring, simulation, synthesis, workloads
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp) / 'build'
            build.mkdir()
            source = 'module candidate(); endmodule'
            work = {'sha256': 'work', 'watchdog_sha256': 'watch'}
            vectors = [1] * 24
            structural = {'cells': 10, 'logic_depth': 3}
            probes = {'decoder_vectors_checked': 24,
                      'decoder_vector_sha256': digest(json.dumps(vectors)),
                      'decoder_rtl_mapped_checked': True}
            traffic = {'rtl_mapped_checked': True, 'reset_backpressure_checked': True,
                       'long_stall_checked': True, 'reset_during_stall_checked': True,
                       'long_stall_output_seen': True, 'reset_blocked_output_seen': False,
                       'workload_sha256': 'work', 'watchdog_sha256': 'watch',
                       'accepted_count': 200, 'consumed_count': 200, 'transactions': 200,
                       'service_opportunity_bound': 65, 'stream_transactions': 32,
                       'workload_cycles': 100, 'stream_ii_numerator': 31,
                       'stream_ii_denominator': 31}
            fake_synth = Mock()
            fake_synth.compile.return_value = (build, structural)
            with patch.object(synthesis, 'Synthesis', return_value=fake_synth), \
                 patch.object(workloads, 'generate', return_value=work) as generate, \
                 patch.object(decoder_check, 'vectors', return_value=(vectors, vectors)), \
                 patch.object(decoder_check, 'check', return_value=probes), \
                 patch.object(simulation, 'simulate', return_value=traffic), \
                 patch.object(rtl, 'design', return_value='baseline'), \
                 patch.object(scoring, 'validate_metrics'):
                with self.assertRaisesRegex(Rejected, 'reset_blocked_output_seen'):
                    _new_family_case('sparse24', 1, source, 1, 'train', Path(tmp) / 'private', Path(tmp) / 'cache')
            fake_synth.compile.assert_called_once_with(1, source)
            generate.assert_called_once_with(1, 1, 'development')


class PilotGatherAdapterTests(unittest.TestCase):
    def test_two_mandatory_bands_only_at_requested_depth(self):
        from chip_rl.pilot.runner import _gather_case
        from chip_rl import rtl
        with tempfile.TemporaryDirectory() as tmp:
            source = 'module candidate(); endmodule'
            host = Mock()
            host._synth.return_value = (Path(tmp) / 'build', {'cells': 10, 'logic_depth': 2}, False)
            host._simulate.return_value = {'commands': 200, 'cycles': 240,
                                           'useful_units': 100, 'useful_throughput': 0.4,
                                           'maximum_response_cycles': 3,
                                           'offered_latency': 2.0}
            with patch('chip_rl.pilot.runner.TrustedEvaluator', return_value=host), \
                 patch.object(rtl, 'design', return_value=source):
                metrics, _, count = _gather_case(16, source, 7, 'train',
                                                  Path(tmp) / 'private', Path(tmp) / 'cache')
            self.assertEqual(count, 2)
            self.assertEqual([x['band'] for x in metrics['replays']], ['target_short', 'target_long'])
            self.assertEqual(host._synth.call_count, 1)
            self.assertEqual(host._simulate.call_count, 2)
            self.assertTrue(all(call.args[0].depth == 16 for call in host._simulate.call_args_list))
            self.assertTrue(all(x['baseline_reused_candidate'] for x in metrics['replays']))


if __name__ == '__main__':
    unittest.main()
