"""Explicit parameter-holdout plan and candidate-source registration."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

# These are structural parameter splits under existing contracts, not unseen tasks.
SPLITS = {
    'gather': {'train': (16, 32), 'dev': (64,), 'test': (128, 256)},
    'mshr': {'train': (2, 4), 'dev': (6,), 'test': (8,)},
    'sparse24': {'train': (1, 2, 4), 'dev': (3, 5), 'test': (6, 7, 8)},
    'block_quant': {'train': (1, 2, 4, 8), 'dev': (3, 5, 6, 7), 'test': tuple(range(9, 17))},
    'hadamard_int8': {'train': (1, 2, 4), 'dev': (8,), 'test': (16,)},
}
PARAMETERS = {'gather': 'DEPTH', 'mshr': 'ENTRIES', 'sparse24': 'G',
              'block_quant': 'N', 'hadamard_int8': 'N'}
LEGAL = {'gather': frozenset((16, 32, 64, 128, 256)),
         'mshr': frozenset((2, 4, 6, 8)),
         'sparse24': frozenset(range(1, 9)),
         'block_quant': frozenset(range(1, 17)),
         'hadamard_int8': frozenset((1, 2, 4, 8, 16))}


def _check_plan() -> None:
    assert set(SPLITS) == set(PARAMETERS) == set(LEGAL)
    for family, splits in SPLITS.items():
        assert set(splits) == {'train', 'dev', 'test'}
        groups = [set(v) for v in splits.values()]
        assert all(all(type(x) is int for x in group) for group in groups)
        assert all(groups[i].isdisjoint(groups[j]) for i in range(3) for j in range(i))
        assert set.union(*groups) == LEGAL[family]


_check_plan()


def validate_request(family: str, config: int, split: str) -> None:
    if family not in SPLITS:
        raise ValueError('unknown pilot family')
    if split not in ('train', 'dev', 'test'):
        raise ValueError('invalid data split')
    if type(config) is not int or config not in SPLITS[family][split]:
        raise ValueError(f'{family} {PARAMETERS[family]}={config} is not in the {split} split')


def sha256_text(source: str) -> str:
    if not isinstance(source, str):
        raise TypeError('source must be text')
    return hashlib.sha256(source.encode()).hexdigest()


def canonical_sha256(value: object) -> str:
    return sha256_text(json.dumps(value, sort_keys=True, separators=(',', ':')))


def _valid_created_at(value: str) -> None:
    if type(value) is not str:
        raise ValueError('missing freeze creation time')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError('freeze creation time must be UTC')


def frozen_manifest(family: str, source: str, *, created_at_utc: str | None = None) -> dict:
    if family not in SPLITS:
        raise ValueError('unknown pilot family')
    created = created_at_utc or datetime.now(timezone.utc).isoformat()
    _valid_created_at(created)
    return {'schema': 'chip-rl-pilot-source-freeze-v1', 'family': family,
            'source_sha256': sha256_text(source), 'parameter': PARAMETERS[family],
            'plan': {name: list(values) for name, values in SPLITS[family].items()},
            'created_at_utc': created}


def verify_frozen_manifest(path: str | Path, family: str, config: int, split: str, source: str) -> str:
    validate_request(family, config, split)
    if split == 'train':
        raise ValueError('freeze verification applies to dev/test')
    value = json.loads(Path(path).read_text())
    if not isinstance(value, dict) or set(value) != {'schema', 'family', 'source_sha256', 'parameter', 'plan', 'created_at_utc'}:
        raise ValueError('invalid frozen manifest schema')
    if value['schema'] != 'chip-rl-pilot-source-freeze-v1' or value['family'] != family or value['parameter'] != PARAMETERS[family]:
        raise ValueError('frozen manifest identity mismatch')
    if value['source_sha256'] != sha256_text(source) or value['plan'] != {name: list(v) for name, v in SPLITS[family].items()}:
        raise ValueError('frozen source or split plan mismatch')
    _valid_created_at(value['created_at_utc'])
    return canonical_sha256(value)
