import argparse,json
from pathlib import Path
from .tasks import Config,NAMES
from .rtl import design
from .evaluate import evaluate
p=argparse.ArgumentParser();p.add_argument('task',choices=NAMES);p.add_argument('--rtl');p.add_argument('--stages',type=int,default=4);p.add_argument('--seed',type=int,default=1);p.add_argument('--split',choices=['train','heldout','challenge'],default='train');p.add_argument('--artifacts');p.add_argument('--emit',action='store_true');a=p.parse_args()
c=Config(a.task);s=Path(a.rtl).read_text() if a.rtl else design(c,a.stages)
if a.emit: print(s)
else:
 r=evaluate(c,s,seed=a.seed,split=a.split,artifacts=a.artifacts);print(json.dumps(r,indent=2));raise SystemExit(0 if r['correct'] else 1)
