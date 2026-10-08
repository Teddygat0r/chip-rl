import argparse,json
from pathlib import Path
from .spec import Config,NAMES
from .rtl import CATALOG,design
from .evaluate import Evaluator
p=argparse.ArgumentParser();p.add_argument('task',choices=NAMES);p.add_argument('--rtl',type=Path);p.add_argument('--architecture');p.add_argument('--cache');p.add_argument('--artifacts');a=p.parse_args()
c=Config(a.task)
if a.architecture and a.architecture not in CATALOG[a.task]:p.error('architecture')
s=a.rtl.read_text() if a.rtl else design(c,a.architecture)
r=Evaluator(a.cache).evaluate(c,s,artifacts=a.artifacts);print(json.dumps(r));raise SystemExit(0 if r['tested_correct'] else 1)
