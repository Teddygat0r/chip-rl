import argparse,json
from .spec import Config,Choice
from .evaluate import Evaluator
p=argparse.ArgumentParser(description='Experimental digital CDC architecture qualification; no physical safety certification.')
p.add_argument('--architecture',choices=['binary_gray','gray_only'],default='binary_gray');p.add_argument('--sync-stages',type=int,choices=[2,3],default=2);p.add_argument('--width',type=int,default=16);p.add_argument('--depth',type=int,default=4);p.add_argument('--cache');p.add_argument('--artifacts');a=p.parse_args()
r=Evaluator(a.cache).evaluate(Config(width=a.width,depth=a.depth),Choice(a.architecture,a.sync_stages),artifacts=a.artifacts);print(json.dumps(r));raise SystemExit(0 if r['tested_correct'] else 1)
