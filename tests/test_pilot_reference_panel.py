from contextlib import redirect_stdout
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chip_rl.pilot.manifest import canonical_sha256, sha256_text
from scripts import measure_pilot_reference_panel as panel


class ReferencePanelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.public = self.root / 'public'
        self.private = self.root / 'private'

    def test_exact_train_panel_and_legacy_roles(self):
        plan = panel.structural_plan()
        self.assertEqual(len(plan), 14)
        self.assertEqual(sum(len(row['references']) for row in plan), 37)
        self.assertEqual([(row['family'], row['config']) for row in plan],
                         [('gather', 16), ('gather', 32), ('mshr', 2), ('mshr', 4),
                          ('sparse24', 1), ('sparse24', 2), ('sparse24', 4),
                          ('block_quant', 1), ('block_quant', 2), ('block_quant', 4),
                          ('block_quant', 8), ('hadamard_int8', 1),
                          ('hadamard_int8', 2), ('hadamard_int8', 4)])
        for row in plan:
            self.assertEqual(sum(ref['role'] == 'legacy_reference' for ref in row['references']), 1)
            for ref in row['references']:
                self.assertEqual(ref['source_sha256'], sha256_text(panel.source_for(
                    row['family'], row['config'], ref['label'])))
        by_reference = {}
        for row in plan:
            for ref in row['references']:
                by_reference.setdefault((row['family'], ref['label']), set()).add(ref['source_sha256'])
        self.assertTrue(all(len(hashes) == 1 for hashes in by_reference.values()))
        with self.assertRaisesRegex(ValueError, 'outside'):
            panel.source_for('block_quant', 3, 'serial')

    @patch.object(panel, '_tool_fingerprint', return_value='tool')
    @patch.object(panel, '_recipe_sha256', return_value='recipe')
    def test_freeze_before_measurement_and_paired_private_seeds(self, recipe, tool):
        registry = panel.freeze(self.public, self.private)
        self.assertEqual(registry['stage'], 'pre_measurement_freeze')
        self.assertEqual(registry['tool_fingerprint'], 'tool')
        self.assertEqual(registry['plan_sha256'], canonical_sha256(registry['plan']))
        self.assertFalse((self.public / 'report.json').exists())
        self.assertFalse((self.public / 'cases').exists())
        self.assertEqual(len(registry['pairing_ids']), 14)
        replay = json.loads((self.private / 'replay.json').read_text())
        self.assertEqual(set(replay['seeds']), set(registry['pairing_ids']))
        self.assertNotIn(str(next(iter(replay['seeds'].values()))),
                         (self.public / 'registry.json').read_text())
        self.assertNotIn(str(self.private), (self.public / 'registry.json').read_text())
        with self.assertRaises(FileExistsError):
            panel.freeze(self.public, self.private)

        calls = []

        def fake_run_case(family, config, source, split, *, seed, private_artifacts, cache_dir):
            calls.append((family, config, seed, split, private_artifacts, cache_dir))
            private_artifacts.mkdir(parents=True)
            seed_id = f'{len(calls):032x}'
            (private_artifacts / 'private-replay.json').write_text(json.dumps({'seed': seed, 'seed_id': seed_id}))
            row = next(row for row in registry['plan']
                       if row['family'] == family and row['config'] == config)
            return {'schema': 'chip-rl-pilot-case-v1', 'family': family,
                    'parameter': row['parameter'], 'config': config, 'split': split,
                    'source_sha256': sha256_text(source),
                    'baseline_source_sha256': row['paired_runner_legacy_baseline_sha256'],
                    'baseline_role': 'legacy_reference',
                    'seed_id': seed_id,
                    'tool_fingerprint': 'tool', 'recipe_sha256': 'recipe',
                    'tested_correct': True, 'wall_time_s': 0.1, 'cpu_time_s': 0.05,
                    'metrics': {'candidate': {'cells': 10, 'cycles': 20,
                                              'workload_cycles': 20,
                                              'stream_ii_numerator': 31,
                                              'stream_ii_denominator': 31},
                                'replays': [{'band': 'target_short', 'candidate': {'cells': 10, 'cycles': 20}},
                                            {'band': 'target_long', 'candidate': {'cells': 10, 'cycles': 20}}]}}

        with patch.object(panel, 'run_case', side_effect=fake_run_case), redirect_stdout(io.StringIO()):
            report = panel.measure(self.public, self.private)
        self.assertEqual(len(calls), 37)
        self.assertTrue(all(split == 'train' for *_, split, private_artifacts, cache_dir in calls))
        self.assertEqual(report['registered_cases'], 37)
        self.assertEqual(report['completed_cases'], 37)
        self.assertEqual(report['tested_correct_cases'], 37)
        self.assertEqual(report['failed_cases'], 0)
        self.assertEqual(report['runner_cpu_time_sum_s'], 1.85)
        self.assertEqual(report['model_token_count'], 'unavailable_no_model_calls')
        self.assertEqual(report['model_cost_usd'], 'unavailable_no_model_calls')
        self.assertEqual(json.loads((self.public / 'progress.json').read_text())['status'], 'complete')
        by_config = {}
        for family, config, seed, *_ in calls:
            by_config.setdefault((family, config), set()).add(seed)
        self.assertTrue(all(len(seeds) == 1 for seeds in by_config.values()))
        first = report['records'][0]
        self.assertEqual(first['returned_result_sha256'], canonical_sha256(first['runner_result']))
        self.assertEqual(first['role'], 'legacy_reference')
        self.assertNotIn(str(self.private), (self.public / 'report.json').read_text())
        with self.assertRaises(FileExistsError):
            panel.measure(self.public, self.private)

    @patch.object(panel, '_tool_fingerprint', return_value='tool')
    @patch.object(panel, '_recipe_sha256', return_value='recipe')
    def test_invocation_errors_stay_in_denominator_without_private_details(self, recipe, tool):
        panel.freeze(self.public, self.private)
        with patch.object(panel, 'run_case', side_effect=RuntimeError('secret /private/path')), redirect_stdout(io.StringIO()):
            report = panel.measure(self.public, self.private)
        self.assertEqual(report['completed_cases'], 37)
        self.assertEqual(report['failed_cases'], 37)
        self.assertEqual(report['tested_correct_cases'], 0)
        self.assertEqual(report['pareto_frontiers'], [])
        self.assertTrue(all(r['runner_result']['error']['stage'] == 'panel_invocation'
                            for r in report['records']))
        self.assertNotIn('secret /private/path', (self.public / 'report.json').read_text())
        self.assertEqual(json.loads((self.public / 'progress.json').read_text())['attempted_cases'], 37)

    @patch.object(panel, '_tool_fingerprint', return_value='tool')
    @patch.object(panel, '_recipe_sha256', return_value='recipe')
    def test_changed_registry_is_rejected_before_runner(self, recipe, tool):
        panel.freeze(self.public, self.private)
        path = self.public / 'registry.json'
        registry = json.loads(path.read_text())
        registry['plan'][0]['references'][0]['source_sha256'] = '0' * 64
        path.write_text(json.dumps(registry))
        with patch.object(panel, 'run_case') as run:
            with self.assertRaisesRegex(ValueError, 'plan or sources changed'):
                panel.measure(self.public, self.private)
            run.assert_not_called()

    def test_pareto_only_correct_and_metric_specific(self):
        def record(label, cells, cycles, ii, correct=True):
            return {'family': 'block_quant', 'config': 4, 'label': label,
                    'tested_correct': correct,
                    'runner_result': {'metrics': {'candidate': {'cells': cells,
                        'workload_cycles': cycles, 'stream_ii_numerator': ii,
                        'stream_ii_denominator': 1}}}}
        rows = [record('a', 10, 10, 8), record('b', 8, 12, 10),
                record('c', 12, 12, 12), record('d', 1, 1, 1, False),
                record('e', 10, 10, 8)]
        fronts = panel.pareto_frontiers(rows)
        self.assertEqual(len(fronts), 2)
        self.assertTrue(all(front['tested_correct_count'] == 4 for front in fronts))
        self.assertTrue(all(front['members'] == ['a', 'b', 'e'] for front in fronts))
        self.assertTrue(all('d' not in front['members'] for front in fronts))


if __name__ == '__main__':
    unittest.main()
