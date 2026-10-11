"""CLI for one structural case or explicit candidate-source freeze."""
import argparse
import json
from pathlib import Path
import sys

from .manifest import SPLITS, frozen_manifest
from ..evaluate import Rejected
from .runner import run_case


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Finite chip-rl parameter-holdout pilot')
    subs = parser.add_subparsers(dest='command', required=True)
    run = subs.add_parser('run', help='evaluate exactly one requested structural config')
    run.add_argument('--family', required=True, choices=SPLITS)
    run.add_argument('--config', type=int, required=True)
    run.add_argument('--split', required=True, choices=('train', 'dev', 'test'))
    run.add_argument('--source', type=Path, required=True)
    run.add_argument('--private-artifacts', type=Path, required=True)
    run.add_argument('--cache-dir', type=Path)
    run.add_argument('--seed', type=int, help='private local 128-bit replay seed; omitted chooses a random seed')
    run.add_argument('--frozen-manifest', type=Path, help='required for dev/test')
    freeze = subs.add_parser('freeze', help='register a source hash and the complete dev/test plan')
    freeze.add_argument('--family', required=True, choices=SPLITS)
    freeze.add_argument('--source', type=Path, required=True)
    freeze.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        source = args.source.read_text()
        if args.command == 'freeze':
            value = frozen_manifest(args.family, source)
            # Exclusive creation prevents a new candidate from replacing an old
            # preregistration without an explicit separate file.
            with args.output.open('x') as handle:
                json.dump(value, handle, indent=2)
                handle.write('\n')
            print(json.dumps({'manifest': str(args.output), 'source_sha256': value['source_sha256']}))
            return 0
        value = run_case(args.family, args.config, source, args.split, seed=args.seed,
                         private_artifacts=args.private_artifacts, cache_dir=args.cache_dir,
                         frozen_manifest_path=args.frozen_manifest)
        print(json.dumps(value, indent=2))
        return 0 if value['tested_correct'] else 1
    except (ValueError, OSError, TypeError, Rejected) as exc:
        print(json.dumps({'tested_correct': False, 'error': {'type': type(exc).__name__, 'message': str(exc)}}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
