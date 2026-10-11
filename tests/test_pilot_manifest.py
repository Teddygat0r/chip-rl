import json
import tempfile
import unittest
from pathlib import Path

from chip_rl.pilot.manifest import (LEGAL, SPLITS, canonical_sha256, frozen_manifest,
                                    validate_request, verify_frozen_manifest)


class PilotManifestTests(unittest.TestCase):
    def test_splits_are_disjoint_complete_and_legal(self):
        for family, split in SPLITS.items():
            train, dev, test = [set(split[k]) for k in ('train', 'dev', 'test')]
            self.assertFalse(train & dev or train & test or dev & test)
            self.assertEqual(train | dev | test, LEGAL[family])
            for name, values in split.items():
                for value in values:
                    validate_request(family, value, name)
                    for other in split:
                        if other != name:
                            with self.assertRaises(ValueError):
                                validate_request(family, value, other)

    def test_freeze_binds_source_and_full_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'freeze.json'
            value = frozen_manifest('block_quant', 'source a', created_at_utc='2026-10-11T00:00:00+00:00')
            p.write_text(json.dumps(value))
            self.assertEqual(verify_frozen_manifest(p, 'block_quant', 3, 'dev', 'source a'), canonical_sha256(value))
            with self.assertRaisesRegex(ValueError, 'source or split plan mismatch'):
                verify_frozen_manifest(p, 'block_quant', 3, 'dev', 'source b')
            value['plan']['train'] = [1]
            p.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, 'source or split plan mismatch'):
                verify_frozen_manifest(p, 'block_quant', 3, 'dev', 'source a')


if __name__ == '__main__':
    unittest.main()
