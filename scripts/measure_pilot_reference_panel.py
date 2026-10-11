"""Freeze and measure the fixed, authored TRAIN reference panel.

``freeze`` must finish before ``measure`` is invoked.  There is deliberately no
resume path: changing any registered source, recipe, tool, plan, or private seed
requires a new directory and a new study.  This is an authored-reference census,
not model sampling, policy training, reward search, or physical measurement.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import secrets
import sys
import time

from chip_rl.pilot.manifest import PARAMETERS, SPLITS, canonical_sha256, sha256_text
from chip_rl.pilot.runner import _legacy_reference_source, _recipe_sha256, run_case


REPO = Path(__file__).resolve().parents[1]
SCHEMA = 'chip-rl-pilot-reference-panel-v1'
REFERENCES = {
    'gather': ('legacy_baseline', 'time_mux', 'static_decoded'),
    'mshr': ('ring', 'shift'),
    'sparse24': ('serial', 'pipeline'),
    'block_quant': ('serial', 'chunked4', 'parallel'),
    'hadamard_int8': ('serial_butterfly', 'stage_parallel', 'sized_serial_butterfly'),
}
LEGACY = {'gather': 'legacy_baseline', 'mshr': 'ring', 'sparse24': 'serial',
          'block_quant': 'serial', 'hadamard_int8': 'serial_butterfly'}


def source_for(family: str, config: int, label: str) -> str:
    """Generate a reference without measuring or modifying its source."""
    if label not in REFERENCES[family] or config not in SPLITS[family]['train']:
        raise ValueError('reference is outside the fixed TRAIN panel')
    if family == 'gather':
        from chip_rl.tasks import Config
        # Emit the same RTL bytes for every structural configuration.  The
        # trusted runner sets DEPTH at elaboration, never through source edits.
        c = Config('gather')
        if label == 'legacy_baseline':
            from chip_rl.rtl import design
            return design(c)
        if label == 'time_mux':
            from chip_rl.architectures import architecture
            return architecture(c, 'time_mux')
        from chip_rl.gather_reference import design
        return design(c)
    if family == 'mshr':
        from chip_rl.memory.rtl import design
        from chip_rl.memory.spec import Config
        return design(Config('mshr'), label)
    if family == 'sparse24':
        from chip_rl.sparse24.rtl import design
    elif family == 'block_quant':
        from chip_rl.block_quant.rtl import design
    else:
        from chip_rl.hadamard_int8.rtl import design
    return design(label)


def structural_plan() -> list[dict]:
    """Exact case order, including every reference at every TRAIN value."""
    plan = [
        {'family': family, 'parameter': PARAMETERS[family], 'config': config,
         'paired_runner_legacy_baseline_sha256': sha256_text(_legacy_reference_source(family, config)),
         'references': [
             {'label': label, 'role': 'legacy_reference' if label == LEGACY[family]
              else 'authored_reference', 'source_sha256': sha256_text(source_for(family, config, label))}
             for label in REFERENCES[family]]}
        for family in REFERENCES for config in SPLITS[family]['train']
    ]
    seen = {}
    for row in plan:
        for ref in row['references']:
            key = (row['family'], ref['label'])
            if key in seen and seen[key] != ref['source_sha256']:
                raise ValueError('reference source bytes vary across TRAIN configurations')
            seen[key] = ref['source_sha256']
    return plan


def _private_root(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path == REPO or path.is_relative_to(REPO):
        raise ValueError('private directory must be outside the source repository')
    return path


def _cpu_seconds() -> float:
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime


def _write_json_new(path: Path, value: object) -> None:
    with path.open('x') as handle:
        json.dump(value, handle, sort_keys=True, indent=2)
        handle.write('\n')


def _tool_fingerprint(cache: Path) -> str:
    from chip_rl.evaluate import TrustedEvaluator
    return TrustedEvaluator(cache).tool_fingerprint


def _study_inputs_sha256() -> str:
    """Guard panel code and qualification tests against mid-study edits."""
    paths = [Path(__file__)] + list((REPO / 'tests').glob('*.py'))
    h = hashlib.sha256()
    for path in sorted(paths):
        h.update(str(path.relative_to(REPO)).encode() + b'\0')
        h.update(path.read_bytes())
    return h.hexdigest()


def freeze(public_dir: Path, private_dir: Path) -> dict:
    """Create the immutable public registration and private replay secret."""
    public_dir = public_dir.resolve()
    private_dir = _private_root(private_dir)
    if public_dir == private_dir or public_dir.is_relative_to(private_dir):
        raise ValueError('public directory cannot be inside private artifacts')
    if public_dir.exists() or private_dir.exists():
        raise FileExistsError('panel directories must be new; no overwrite or resume')
    plan = structural_plan()
    seeds = {f"{row['family']}:{row['config']}": secrets.randbits(128) for row in plan}
    # Public pairing IDs are random labels, never hashes of replay seeds.
    pairing_ids = {key: secrets.token_hex(16) for key in seeds}
    # Fingerprint before creating the public freeze.  The private cache belongs to
    # the study and is never exposed to candidates or included as a public path.
    private_dir.mkdir(parents=True)
    private_dir.chmod(0o700)
    try:
        fingerprint = _tool_fingerprint(private_dir / 'cache')
        registry = {
            'schema': SCHEMA, 'stage': 'pre_measurement_freeze',
            'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'split': 'train', 'plan': plan, 'plan_sha256': canonical_sha256(plan),
            'tool_fingerprint': fingerprint,
            'recipe_sha256_by_family': {family: _recipe_sha256(family) for family in REFERENCES},
            'measurement_script_sha256': sha256_text(Path(__file__).read_text()),
            'study_inputs_sha256': _study_inputs_sha256(),
            'pairing_ids': pairing_ids,
            'pairing': 'same private seed for all references within one family/config',
            'execution': 'one case at a time; no source tuning; no resume',
            'measurement_scope': 'generic cells, finite cycles and stream II where defined',
            'model_token_count': 'unavailable_no_model_calls',
            'model_cost_usd': 'unavailable_no_model_calls',
        }
        _write_json_new(private_dir / 'replay.json', {'schema': SCHEMA, 'seeds': seeds,
                                                     'pairing_ids': pairing_ids})
        (private_dir / 'replay.json').chmod(0o600)
        public_dir.mkdir(parents=True)
        _write_json_new(public_dir / 'registry.json', registry)
    except Exception:
        # Keep any partially created private data private; fail before measuring.
        raise
    return registry


def _valid_result(result: dict, row: dict, ref: dict, registry: dict) -> str | None:
    family, config = row['family'], row['config']
    checks = {
        'schema': 'chip-rl-pilot-case-v1', 'family': family,
        'parameter': row['parameter'], 'config': config, 'split': 'train',
        'source_sha256': ref['source_sha256'],
        'tool_fingerprint': registry['tool_fingerprint'],
        'recipe_sha256': registry['recipe_sha256_by_family'][family],
    }
    for field, expected in checks.items():
        if result.get(field) != expected:
            return f'runner {field} did not match preregistration'
    seed_id = result.get('seed_id')
    if type(seed_id) is not str or len(seed_id) != 32 or any(c not in '0123456789abcdef' for c in seed_id):
        return 'runner did not report an opaque seed identifier'
    if type(result.get('tested_correct')) is not bool:
        return 'runner did not report a Boolean correctness result'
    if result.get('baseline_role') != 'legacy_reference':
        return 'runner baseline role did not match preregistration'
    if result.get('baseline_source_sha256') != row['paired_runner_legacy_baseline_sha256']:
        return 'runner legacy baseline source did not match preregistration'
    return None


def _candidate_metrics(result: dict) -> dict | None:
    m = result.get('metrics')
    if not isinstance(m, dict):
        return None
    candidate = m.get('candidate')
    return candidate if isinstance(candidate, dict) else None


def _points(result: dict, family: str) -> list[tuple[str, str, float, float]]:
    """(comparison, replay, cells, second metric), with no cross-family pooling."""
    m = result.get('metrics') or {}
    if family == 'gather':
        points = []
        for replay in m.get('replays', []):
            c = replay.get('candidate', {})
            points.append(('cells_vs_cycles', replay.get('band'), c.get('cells'), c.get('cycles')))
        return points
    c = _candidate_metrics(result) or {}
    if family == 'mshr':
        return [('cells_vs_cycles', 'workload', c.get('cells'), c.get('cycles'))]
    numerator, denominator = c.get('stream_ii_numerator'), c.get('stream_ii_denominator')
    ii = numerator / denominator if isinstance(numerator, (int, float)) and isinstance(denominator, (int, float)) and denominator > 0 else None
    return [('cells_vs_workload_cycles', 'workload', c.get('cells'), c.get('workload_cycles')),
            ('cells_vs_stream_ii', 'stream', c.get('cells'), ii)]


def pareto_frontiers(records: list[dict]) -> list[dict]:
    """Minimize both axes, retaining ties; only tested-correct references enter."""
    groups: dict[tuple, list[dict]] = {}
    for record in records:
        if not record['tested_correct']:
            continue
        for comparison, replay, cells, other in _points(record['runner_result'], record['family']):
            if not all(type(x) in (int, float) and x > 0 for x in (cells, other)):
                continue
            key = (record['family'], record['config'], comparison, replay)
            groups.setdefault(key, []).append({'label': record['label'], 'cells': cells, 'other': other})
    answer = []
    for key, points in groups.items():
        members = [p['label'] for p in points if not any(
            q['cells'] <= p['cells'] and q['other'] <= p['other'] and
            (q['cells'] < p['cells'] or q['other'] < p['other']) for q in points)]
        answer.append({'family': key[0], 'config': key[1], 'comparison': key[2],
                       'replay': key[3], 'tested_correct_count': len(points),
                       'members': members, 'points': points})
    return answer


def _error_record(row: dict, ref: dict, exc: Exception) -> dict:
    # Never publish exception strings, which might contain a private path.
    return {'schema': 'chip-rl-pilot-case-v1', 'family': row['family'],
            'parameter': row['parameter'], 'config': row['config'], 'split': 'train',
            'source_sha256': ref['source_sha256'], 'tested_correct': False,
            'metrics': None, 'wall_time_s': 0, 'cpu_time_s': 0,
            'error': {'type': type(exc).__name__, 'stage': 'panel_invocation',
                      'message': 'runner invocation failed; details in private artifacts'}}


def measure(public_dir: Path, private_dir: Path) -> dict:
    """Run exactly the registered cases sequentially; reject any resume attempt."""
    public_dir = public_dir.resolve()
    private_dir = _private_root(private_dir)
    registry = json.loads((public_dir / 'registry.json').read_text())
    replay = json.loads((private_dir / 'replay.json').read_text())
    if registry.get('schema') != SCHEMA or replay.get('schema') != SCHEMA:
        raise ValueError('invalid panel registry or private replay')
    if registry.get('plan') != structural_plan() or registry.get('plan_sha256') != canonical_sha256(registry['plan']):
        raise ValueError('registered structural plan or sources changed')
    if registry.get('measurement_script_sha256') != sha256_text(Path(__file__).read_text()):
        raise ValueError('measurement script changed since freeze')
    if registry.get('study_inputs_sha256') != _study_inputs_sha256():
        raise ValueError('panel tests or script changed since freeze')
    if registry.get('recipe_sha256_by_family') != {family: _recipe_sha256(family) for family in REFERENCES}:
        raise ValueError('runner recipe changed since freeze')
    if registry.get('tool_fingerprint') != _tool_fingerprint(private_dir / 'cache'):
        raise ValueError('tool fingerprint changed since freeze')
    seeds = replay['seeds']
    expected_keys = {f"{row['family']}:{row['config']}" for row in registry['plan']}
    if set(seeds) != expected_keys or registry.get('pairing_ids') != replay.get('pairing_ids') or set(registry['pairing_ids']) != expected_keys:
        raise ValueError('private seed identities do not match registry')
    for key, seed in seeds.items():
        pairing_id = registry['pairing_ids'][key]
        if type(seed) is not int or not 0 <= seed < 2**128 or type(pairing_id) is not str or len(pairing_id) != 32 or any(c not in '0123456789abcdef' for c in pairing_id):
            raise ValueError('private seed identity mismatch')
    cases_dir = public_dir / 'cases'
    if cases_dir.exists() or (public_dir / 'report.json').exists() or (private_dir / 'runs').exists():
        raise FileExistsError('measurement already started; no resume or overwrite')
    cases_dir.mkdir()
    (private_dir / 'runs').mkdir()
    began, cpu_began = time.monotonic(), _cpu_seconds()
    records = []
    planned = sum(len(row['references']) for row in registry['plan'])
    def progress(status: str) -> None:
        value = {'schema': SCHEMA, 'status': status, 'registered_cases': planned,
                 'attempted_cases': len(records),
                 'tested_correct_cases': sum(r['tested_correct'] for r in records),
                 'failed_cases': sum(not r['tested_correct'] for r in records),
                 'case_files': [r['case_file'] for r in records]}
        tmp = public_dir / 'progress.json.tmp'
        tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
        tmp.replace(public_dir / 'progress.json')
    progress('incomplete')
    for row in registry['plan']:
        family, config = row['family'], row['config']
        seed = seeds[f'{family}:{config}']
        for ref in row['references']:
            label = ref['label']
            if (registry['study_inputs_sha256'] != _study_inputs_sha256() or
                    registry['recipe_sha256_by_family'][family] != _recipe_sha256(family) or
                    registry['tool_fingerprint'] != _tool_fingerprint(private_dir / 'cache')):
                raise ValueError('study inputs, runner recipe or tools changed during measurement; use a new registry')
            source = source_for(family, config, label)
            # Recheck emitted bytes immediately before a single case.  No source
            # edits are made, including after a failed reference.
            if sha256_text(source) != ref['source_sha256']:
                raise ValueError('generated source changed during measurement')
            path = private_dir / 'runs' / f'{family}-{config}-{label}'
            case_began, cpu_case_began = time.monotonic(), _cpu_seconds()
            try:
                result = run_case(family, config, source, 'train', seed=seed,
                                  private_artifacts=path, cache_dir=private_dir / 'cache')
                mismatch = _valid_result(result, row, ref, registry)
            except Exception as exc:
                path.mkdir(parents=True, exist_ok=True)
                (path / 'private-panel-error.txt').write_text(repr(exc) + '\n')
                result, mismatch = _error_record(row, ref, exc), None
                result['wall_time_s'] = round(time.monotonic() - case_began, 6)
                result['cpu_time_s'] = round(_cpu_seconds() - cpu_case_began, 6)
            else:
                try:
                    private_replay = json.loads((path / 'private-replay.json').read_text())
                    if private_replay.get('seed') != seed or private_replay.get('seed_id') != result.get('seed_id'):
                        mismatch = 'runner private replay did not match the registered pairing'
                except Exception as exc:
                    (path / 'private-panel-error.txt').write_text(repr(exc) + '\n')
                    mismatch = 'runner private replay could not be verified'
            # Public result object is retained even on rejection.  A mismatch
            # disqualifies a run from the finite-correct Pareto denominator.
            public_result = {'family': family, 'parameter': row['parameter'],
                             'config': config, 'label': label, 'role': ref['role'],
                             'pairing_id': registry['pairing_ids'][f'{family}:{config}'],
                             'runner_result': result, 'preregistration_error': mismatch,
                             'returned_result_sha256': canonical_sha256(result),
                             'tested_correct': bool(result.get('tested_correct')) and mismatch is None}
            filename = f'{family}-{config}-{label}.json'
            _write_json_new(cases_dir / filename, public_result)
            records.append(public_result | {'case_file': f'cases/{filename}'})
            progress('incomplete')
            print(f'{family} {config} {label}: {"PASS" if public_result["tested_correct"] else "FAIL"}', flush=True)
    if (registry['study_inputs_sha256'] != _study_inputs_sha256() or
            registry['plan'] != structural_plan() or
            registry['recipe_sha256_by_family'] != {family: _recipe_sha256(family) for family in REFERENCES} or
            registry['tool_fingerprint'] != _tool_fingerprint(private_dir / 'cache')):
        raise ValueError('study inputs, sources, runner recipe or tools changed before report; use a new registry')
    report = {
        'schema': SCHEMA, 'registry_sha256': canonical_sha256(registry),
        'split': 'train', 'registered_cases': sum(len(row['references']) for row in registry['plan']),
        'completed_cases': len(records),
        'tested_correct_cases': sum(r['tested_correct'] for r in records),
        'failed_cases': sum(not r['tested_correct'] for r in records),
        'total_wall_time_s': round(time.monotonic() - began, 6),
        'total_cpu_time_s': round(_cpu_seconds() - cpu_began, 6),
        'runner_wall_time_sum_s': round(sum(r['runner_result'].get('wall_time_s', 0) for r in records), 6),
        'runner_cpu_time_sum_s': round(sum(r['runner_result'].get('cpu_time_s', 0) for r in records), 6),
        'model_token_count': 'unavailable_no_model_calls',
        'model_cost_usd': 'unavailable_no_model_calls',
        'physical': 'not_run', 'formal': 'not_run',
        'records': records, 'pareto_frontiers': pareto_frontiers(records),
    }
    _write_json_new(public_dir / 'report.json', report)
    progress('complete')
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('freeze', 'measure'))
    parser.add_argument('--public-dir', type=Path, default=REPO / 'evidence' / 'pilot-reference-panel')
    parser.add_argument('--private-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        value = freeze(args.public_dir, args.private_dir) if args.command == 'freeze' else measure(args.public_dir, args.private_dir)
        print(json.dumps({'command': args.command, 'registry_sha256': canonical_sha256(value) if args.command == 'freeze' else value['registry_sha256'],
                          'registered_cases': sum(len(row['references']) for row in value['plan']) if args.command == 'freeze' else value['registered_cases'],
                          'failed_cases': None if args.command == 'freeze' else value['failed_cases']}))
        return 0
    except (OSError, TypeError, ValueError, KeyError) as exc:
        print(json.dumps({'error': type(exc).__name__, 'message': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
