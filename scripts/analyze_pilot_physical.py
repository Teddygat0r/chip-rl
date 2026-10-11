"""Analyze a manually joined physical pilot JSON table without running tools.

Usage: python -m scripts.analyze_pilot_physical INPUT.json --output analysis.json
Input may be an array of attempt rows or an object containing a ``rows`` array.
This script never reads the runner's artifacts or fills in missing measurements.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chip_rl.pilot_analysis import analyze_pilot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", type=Path, help="explicitly joined attempt rows")
    parser.add_argument("--output", type=Path, help="analysis JSON (default: stdout)")
    args = parser.parse_args(argv)
    source = json.loads(args.input_json.read_text())
    rows = source.get("rows") if isinstance(source, dict) else source
    report = analyze_pilot(rows)
    encoded = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.write_text(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
