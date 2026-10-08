"""Scripted architecture selection, not a trained RL policy."""
import argparse,json
from chip_rl.requant.env import RequantEnv
from chip_rl.requant.rtl import design
p=argparse.ArgumentParser();p.add_argument('--cache');a=p.parse_args()
e=RequantEnv(horizon=2,cache=a.cache);obs,_=e.reset(seed=24)
print(json.dumps({'architecture':'parallel','evaluation':obs['evaluation']}))
for label in ('serial','pipelined'):
 obs,reward,terminated,truncated,info=e.step({'rtl':design(label)})
 print(json.dumps({'architecture':label,'reward':reward,'correct':info['tested_correct'],'truncated':truncated}))
