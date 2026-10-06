"""Trusted-host replay of one retained private case; never expose to candidate agents."""
import argparse,json,gzip,tempfile
from pathlib import Path
from chip_rl.tasks import Config
from chip_rl.evaluate import TrustedEvaluator,Rejected
p=argparse.ArgumentParser();p.add_argument('artifact',type=Path);p.add_argument('--output',required=True);p.add_argument('--cache');a=p.parse_args()
r=json.loads((a.artifact/'private-replay.json').read_text());c=Config(**r['config']);src=(a.artifact/'candidate.sv').read_text();q=TrustedEvaluator(a.cache)
try:
 sd,sm,_=q._synth(c,src);result=q._simulate(c,src,sd,r['seed'],r['count'],a.output)
 print(json.dumps({'tested_correct':True,'metrics':result,'synthesis':sm},indent=2))
except Rejected as e:
 print(json.dumps({'tested_correct':False,'reason':str(e)}));raise SystemExit(1)
