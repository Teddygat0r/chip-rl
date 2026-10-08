import argparse,json
from pathlib import Path
from .spec import Config,NAMES
from .rtl import design,CATALOG
from .evaluate import Evaluator
p=argparse.ArgumentParser();p.add_argument('task',choices=NAMES);p.add_argument('--rtl',type=Path);p.add_argument('--architecture',default='baseline');p.add_argument('--cache');p.add_argument('--artifacts');p.add_argument('--objective',choices=['area','balanced','latency'],default='balanced');p.add_argument('--replay-seed',type=int);a=p.parse_args()
c=Config(a.task,objective=a.objective);src=a.rtl.read_text() if a.rtl else design(c,a.architecture)
r=Evaluator(a.cache).evaluate(c,src,replay_seed=a.replay_seed,artifacts=a.artifacts);print(json.dumps(r,indent=2));raise SystemExit(0 if r['tested_correct'] else 1)
