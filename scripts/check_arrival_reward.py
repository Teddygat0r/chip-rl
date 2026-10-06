"""Reproduce the previously exploitable delayed-acceptance reward regression."""
import argparse,json
from chip_rl.evaluate import TrustedEvaluator
from chip_rl.tasks import Config
from chip_rl.rtl import design
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--cache');a=p.parse_args()
q=TrustedEvaluator(a.cache);c=Config('dma');s=design(c)
s=s.replace('assign in_ready=ready[0] && !rst;','assign in_ready=ready[0] && out_ready && !rst;').replace('valid[0]<=in_valid; if(in_valid) data[0]<=y;', 'valid[0]<=fire; if(fire) data[0]<=y;')
r=q.evaluate(c,s,replay_seed=9134,count=80,allow_experimental=True,artifacts=a.output)
print(json.dumps(r,indent=2))
assert r['tested_correct'] and r['reward']<=1 and not r['pilot_eligible']
