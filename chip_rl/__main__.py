"""Trusted host CLI. Never expose replay/artifact flags through the agent server."""
import argparse,json
from pathlib import Path
from .tasks import Config,NAMES
from .rtl import design
from .evaluate import TrustedEvaluator
p=argparse.ArgumentParser();p.add_argument('task',choices=NAMES);p.add_argument('--rtl');p.add_argument('--replay-seed',type=int);p.add_argument('--artifacts');p.add_argument('--cache');p.add_argument('--allow-experimental',action='store_true');p.add_argument('--emit',action='store_true');a=p.parse_args()
c=Config(a.task);s=Path(a.rtl).read_text() if a.rtl else design(c)
if a.emit:print(s)
else:
 r=TrustedEvaluator(a.cache).evaluate(c,s,replay_seed=a.replay_seed,artifacts=a.artifacts,allow_experimental=a.allow_experimental)
 print(json.dumps(r,indent=2));raise SystemExit(0 if r['tested_correct'] else 1)
