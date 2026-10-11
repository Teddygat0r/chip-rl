"""Finite, paired, single-configuration pilot adapter.

Only the requested structural parameter is compiled. Workload vectors, oracle
outputs, seeds, traces and build logs remain in an explicitly private directory.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import secrets
import resource
import time

from ..evaluate import Rejected, TrustedEvaluator, digest, sanitize
from .manifest import PARAMETERS, sha256_text, validate_request, verify_frozen_manifest

_REPO = Path(__file__).resolve().parents[2]


def _recipe_sha256(family: str) -> str:
    """Hash pilot adapter and all underlying Python/contract recipe inputs."""
    family_dir = _REPO / 'chip_rl' / ('memory' if family == 'mshr' else family)
    paths = (list((_REPO / 'chip_rl' / 'pilot').glob('*.py'))
             + list((_REPO / 'chip_rl').glob('*.py'))
             + list(family_dir.glob('*.py'))
             + list(family_dir.glob('contracts.md'))
             + list((_REPO / 'chip_rl').glob('contracts.md')))
    hasher = hashlib.sha256()
    for path in sorted(set(paths), key=lambda p: str(p.relative_to(_REPO))):
        hasher.update(str(path.relative_to(_REPO)).encode() + b'\0')
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def _cpu_seconds() -> float:
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime


def _legacy_reference_source(family: str, config: int) -> str:
    if family == 'gather':
        from ..rtl import design
        from ..tasks import Config
        return design(Config('gather', depth=config))
    if family == 'mshr':
        from ..memory.rtl import design
        from ..memory.spec import Config
        return design(Config('mshr', entries=config))
    if family == 'sparse24':
        from ..sparse24.rtl import design
        return design('serial')
    if family == 'block_quant':
        from ..block_quant.rtl import design
        return design('serial')
    from ..hadamard_int8.rtl import design
    return design('serial_butterfly')


def _private_path(path: str | Path, label: str) -> Path:
    p = Path(path).expanduser().resolve()
    if p == _REPO or p.is_relative_to(_REPO):
        raise ValueError(f'{label} must be outside the source repository')
    return p


def _seed_for(seed: int, family: str, config: int, split: str, replay: str) -> int:
    material = f'chip-rl-pilot-v1:{seed}:{family}:{config}:{split}:{replay}'
    return int.from_bytes(hashlib.sha256(material.encode()).digest()[:16], 'big')


def _positive_metrics(m: dict, fields: tuple[str, ...]) -> None:
    for name in fields:
        value = m.get(name)
        if type(value) not in (int, float) or value <= 0:
            raise Rejected('missing or nonpositive metric: ' + name)


def _new_family_case(family: str, config: int, source: str, seed: int, split: str,
                     private_root: Path, cache_root: Path) -> tuple[dict, str, int]:
    if family == 'sparse24':
        from ..sparse24 import decoder_check, rtl, scoring, simulation, synthesis, workloads
        from ..sparse24.spec import identity, Config
        synth = synthesis.Synthesis(cache_root)
        work = workloads.generate(config, seed, 'development' if split == 'train' else 'heldout')
        decoder_hash = digest(json.dumps(decoder_check.vectors(config)[0]))
        def measure(src: str, label: str) -> dict:
            began = time.monotonic()
            build, structural = synth.compile(config, src)
            synthesis_s = time.monotonic() - began
            d = private_root / label
            d.mkdir(parents=True, exist_ok=False)
            began = time.monotonic()
            probes = decoder_check.check(config, src, build / 'netlist.v', d / 'decoder')
            probe_s = time.monotonic() - began
            began = time.monotonic()
            traffic = simulation.simulate(config, src, build / 'netlist.v', work, d / 'simulation')
            simulation_s = time.monotonic() - began
            m = structural | probes | traffic
            for flag in ('rtl_mapped_checked', 'decoder_rtl_mapped_checked',
                         'reset_backpressure_checked', 'long_stall_checked',
                         'reset_during_stall_checked', 'long_stall_output_seen',
                         'reset_blocked_output_seen'):
                if m.get(flag) is not True:
                    raise Rejected('missing sparse24 probe evidence: ' + flag)
            if m.get('decoder_vectors_checked') != 24 * config or m.get('decoder_vector_sha256') != decoder_hash:
                raise Rejected('sparse24 decoder probe mismatch')
            if m.get('workload_sha256') != work['sha256'] or m.get('watchdog_sha256') != work['watchdog_sha256']:
                raise Rejected('sparse24 workload mismatch')
            if m.get('accepted_count') != m.get('consumed_count') or m.get('transactions') != m.get('accepted_count'):
                raise Rejected('sparse24 incomplete transaction record')
            if m.get('service_opportunity_bound') != config + 64 or m.get('stream_transactions') != 32:
                raise Rejected('sparse24 incomplete service evidence')
            scoring.validate_metrics(config, m, label)
            return m | {'stage_wall_time_s': {'synthesis': round(synthesis_s, 6),
                'decoder_check': round(probe_s, 6), 'source_mapped_simulation': round(simulation_s, 6)}}
        baseline = rtl.design('serial')
        contract = identity(Config(config))
    elif family in ('block_quant', 'hadamard_int8'):
        if family == 'block_quant':
            from ..block_quant import arithmetic_check as exact, evaluate, rtl, simulation, synthesis, workloads
            from ..block_quant.spec import identity, Config
            probe_name, vector_name = 'arithmetic', 'arithmetic_vector_sha256'
            base_name = 'serial'
        else:
            from ..hadamard_int8 import exact_check as exact, evaluate, rtl, simulation, synthesis, workloads
            from ..hadamard_int8.spec import identity, Config
            probe_name, vector_name = 'exact', 'exact_vector_sha256'
            base_name = 'serial_butterfly'
        synth = synthesis.Synthesis(cache_root)
        work = workloads.generate(config, seed, 'development' if split == 'train' else 'heldout')
        selected = exact.selected(work)
        key = {vector_name: digest(json.dumps(selected))}
        def measure(src: str, label: str) -> dict:
            began = time.monotonic()
            build, structural = synth.compile(config, src)
            synthesis_s = time.monotonic() - began
            d = private_root / label
            d.mkdir(parents=True, exist_ok=False)
            began = time.monotonic()
            probes = exact.check(config, src, build / 'netlist.v', work, d / probe_name)
            probe_s = time.monotonic() - began
            began = time.monotonic()
            traffic = simulation.simulate(config, src, build / 'netlist.v', work, d / 'simulation')
            simulation_s = time.monotonic() - began
            m = evaluate.validate_metrics(structural | probes | traffic, key, work, config)
            return m | {'stage_wall_time_s': {'synthesis': round(synthesis_s, 6),
                probe_name + '_check': round(probe_s, 6),
                'source_mapped_simulation': round(simulation_s, 6)}}
        baseline = rtl.design(base_name)
        contract = identity(Config(config))
    else:
        raise ValueError('unexpected family')
    candidate = measure(source, 'candidate')
    reference = dict(candidate) if source == baseline else measure(baseline, 'baseline')
    _positive_metrics(candidate, ('cells', 'workload_cycles', 'stream_ii_numerator', 'stream_ii_denominator'))
    _positive_metrics(reference, ('cells', 'workload_cycles', 'stream_ii_numerator', 'stream_ii_denominator'))
    return {'candidate': candidate, 'baseline': reference,
            'baseline_reused_candidate': source == baseline,
            'ratios': {k: candidate[k] / reference[k] for k in ('cells', 'workload_cycles', 'logic_depth')
                       if k in candidate and k in reference and reference[k] > 0}}, contract, 1


def _mshr_case(config: int, source: str, seed: int, split: str,
               private_root: Path, cache_root: Path) -> tuple[dict, str, int]:
    from ..memory import rtl, simulation, synthesis, workloads
    from ..memory.spec import Config, identity
    c = Config('mshr', entries=config)
    work = workloads.generate(c, seed, heldout=(split != 'train'))
    synth = synthesis.Synthesis(cache_root)
    def measure(src: str, label: str) -> dict:
        began = time.monotonic()
        build, structural = synth.compile(c, src)
        synthesis_s = time.monotonic() - began
        # The simulator requires source and mapped PASS records to agree and
        # rejects absent reset/cancellation probe markers for both levels.
        began = time.monotonic()
        traffic = simulation.simulate(c, src, build / 'netlist.v', work, private_root / label)
        simulation_s = time.monotonic() - began
        m = structural | traffic
        # Probe markers are validated by memory.simulation.simulate before it returns.
        _positive_metrics(m, ('cells', 'cycles', 'transactions', 'latency_sum', 'memory_reads'))
        if m['peak_pending'] < config or not m.get('vectors_sha256'):
            raise Rejected('missing MSHR concurrency/vector probe evidence')
        return m | {'stage_wall_time_s': {'synthesis': round(synthesis_s, 6),
                    'source_mapped_simulation': round(simulation_s, 6)}}
    candidate = measure(source, 'candidate')
    baseline = rtl.design(c)
    reference = dict(candidate) if source == baseline else measure(baseline, 'baseline')
    if candidate['vectors_sha256'] != reference['vectors_sha256']:
        raise Rejected('MSHR paired workload mismatch')
    return {'candidate': candidate, 'baseline': reference,
            'baseline_reused_candidate': source == baseline,
            'ratios': {k: candidate[k] / reference[k] for k in ('cells', 'cycles', 'latency_sum', 'memory_reads')}}, identity(c), 1


def _gather_case(config: int, source: str, seed: int, split: str,
                 private_root: Path, cache_root: Path) -> tuple[dict, str, int]:
    from ..coverage import BANDS
    from ..contracts import identity
    from ..rtl import design
    from ..tasks import Config
    c = Config('gather', depth=config)
    host = TrustedEvaluator(cache_root)
    began = time.monotonic()
    source_build, source_struct, _ = host._synth(c, source)
    candidate_synthesis_s = time.monotonic() - began
    baseline = design(c)
    if source == baseline:
        baseline_build, baseline_struct = source_build, source_struct
        baseline_synthesis_s = 0.0
    else:
        began = time.monotonic()
        baseline_build, baseline_struct, _ = host._synth(c, baseline)
        baseline_synthesis_s = time.monotonic() - began
    replays = []
    for label in ('target_short', 'target_long'):
        replay_start = time.monotonic()
        replay_seed = _seed_for(seed, 'gather', config, split, label)
        lo, hi = BANDS[label]
        span = hi - lo + 1
        count = lo + _seed_for(seed, 'gather', config, split, label + ':length') % span
        began = time.monotonic()
        candidate = host._simulate(c, source, source_build, replay_seed, count,
                                   private_root / label / 'candidate') | source_struct
        candidate_simulation_s = time.monotonic() - began
        if source == baseline:
            reference = dict(candidate)
            baseline_simulation_s = 0.0
        else:
            began = time.monotonic()
            reference = host._simulate(c, baseline, baseline_build, replay_seed, count,
                                       private_root / label / 'baseline') | baseline_struct
            baseline_simulation_s = time.monotonic() - began
        _positive_metrics(candidate, ('cells', 'cycles', 'commands', 'useful_units',
                                      'useful_throughput', 'maximum_response_cycles'))
        _positive_metrics(reference, ('cells', 'cycles', 'commands', 'useful_units',
                                      'useful_throughput', 'maximum_response_cycles'))
        if candidate['commands'] != reference['commands'] or candidate['useful_units'] != reference['useful_units']:
            raise Rejected('gather paired workload mismatch')
        replays.append({'band': label, 'random_count': count,
                        'wall_time_s': round(time.monotonic() - replay_start, 6),
                        'candidate_simulation_wall_time_s': round(candidate_simulation_s, 6),
                        'baseline_simulation_wall_time_s': round(baseline_simulation_s, 6),
                        'baseline_reused_candidate': source == baseline,
                        'candidate': candidate,
                        'baseline': reference,
                        'ratios': {k: candidate[k] / reference[k] for k in ('cells', 'cycles', 'offered_latency')
                                   if reference[k] > 0}})
    return {'candidate_synthesis_wall_time_s': round(candidate_synthesis_s, 6),
            'baseline_synthesis_wall_time_s': round(baseline_synthesis_s, 6),
            'replays': replays}, identity(c), len(replays)


def run_case(family: str, config: int, source: str, split: str, *, seed: int | None = None,
             private_artifacts: str | Path, cache_dir: str | Path | None = None,
             frozen_manifest_path: str | Path | None = None) -> dict:
    """Run a full finite check at exactly one structural configuration.

    Invalid requests and missing/mismatched source registration raise ValueError.
    Tool/check failures produce a visible unsuccessful result with an error.
    """
    validate_request(family, config, split)
    sanitize(source)
    if seed is None:
        seed = secrets.randbits(128)
    if type(seed) is not int or not 0 <= seed < 2**128:
        raise ValueError('seed must be a 128-bit unsigned integer')
    private_root = _private_path(private_artifacts, 'private artifacts')
    cache_root = _private_path(cache_dir or private_root / 'cache', 'cache')
    if frozen_manifest_path is None and split != 'train':
        raise ValueError('dev/test requires a pre-created frozen source manifest')
    manifest_sha = (verify_frozen_manifest(frozen_manifest_path, family, config, split, source)
                    if split != 'train' else None)
    private_root.mkdir(parents=True, exist_ok=False)
    cache_root.mkdir(parents=True, exist_ok=True)
    # Opaque run-local ID avoids leaking a low-entropy caller seed through a
    # public unsalted hash; the private replay record maps ID back to seed.
    seed_id = secrets.token_hex(16)
    (private_root / 'private-replay.json').write_text(json.dumps({'seed': seed, 'seed_id': seed_id,
        'family': family, 'config': config, 'split': split}, indent=2) + '\n')
    start = time.monotonic()
    cpu_start = _cpu_seconds()
    result = {'schema': 'chip-rl-pilot-case-v1', 'holdout_kind': 'parameter_holdout',
              'family': family, 'parameter': PARAMETERS[family], 'config': config,
              'split': split, 'seed_id': seed_id, 'frozen_manifest_sha256': manifest_sha,
              'source_sha256': sha256_text(source),
              'baseline_source_sha256': sha256_text(_legacy_reference_source(family, config)),
              'baseline_role': 'legacy_reference',
              'recipe_sha256': _recipe_sha256(family), 'tested_correct': False,
              'validation': 'rejected', 'measurement_scope': 'generic_cells_and_finite_simulation',
              'formal': 'not_run', 'physical': 'not_run', 'metrics': None,
              'workload_replays': 0, 'tool_fingerprint': None, 'contract_sha256': None,
              'error': None}
    try:
        if family == 'gather':
            metrics, contract, nreplays = _gather_case(config, source, seed, split, private_root, cache_root)
        elif family == 'mshr':
            metrics, contract, nreplays = _mshr_case(config, source, _seed_for(seed, family, config, split, 'work'),
                                                     split, private_root, cache_root)
        else:
            metrics, contract, nreplays = _new_family_case(family, config, source,
                _seed_for(seed, family, config, split, 'work'), split, private_root, cache_root)
        # Synthesis objects use this same cache root. The host fingerprint is
        # recomputed from executable bytes, never inferred from version text.
        result.update(metrics=metrics, contract_sha256=contract, workload_replays=nreplays,
                      tested_correct=True, validation='finite_source_and_mapped_pass')
    except Exception as exc:
        result['error'] = {'type': type(exc).__name__, 'stage': 'single_configuration_case',
                           'message': 'finite validation failed; details in private artifacts'}
        (private_root / 'private-error.txt').write_text(repr(exc) + '\n')
    finally:
        try:
            result['tool_fingerprint'] = TrustedEvaluator(cache_root).tool_fingerprint
        except Exception as fingerprint_exc:
            if result['error'] is None:
                result['error'] = {'type': type(fingerprint_exc).__name__, 'stage': 'tool_fingerprint',
                                   'message': 'tool fingerprint unavailable; details in private artifacts'}
                (private_root / 'private-fingerprint-error.txt').write_text(repr(fingerprint_exc) + '\n')
                result['tested_correct'] = False
                result['validation'] = 'rejected'
        result['wall_time_s'] = round(time.monotonic() - start, 6)
        result['cpu_time_s'] = round(_cpu_seconds() - cpu_start, 6)
        result['cpu_time_scope'] = 'runner_and_spawned_tools'
        (private_root / 'public-result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
