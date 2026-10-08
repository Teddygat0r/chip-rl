"""Replay a deterministic candidate policy; this is not trained RL."""
import argparse,json
from chip_rl.expansion.env import ExpansionEnv
from chip_rl.expansion.rtl import CATALOG,design
from chip_rl.expansion.spec import NAMES
p=argparse.ArgumentParser();p.add_argument('--task',choices=NAMES,default='ecc');p.add_argument('--objective',choices=['area','balanced','latency'],default='balanced');p.add_argument('--cache');a=p.parse_args()
alts=CATALOG[a.task][1:];env=ExpansionEnv(a.task,horizon=len(alts),cache=a.cache,objective=a.objective)
obs,_=env.reset(seed=17);print(json.dumps({'architecture':'baseline','reward':obs['evaluation']['reward'],'correct':obs['evaluation']['tested_correct']}))
for alt in alts:
 obs,reward,terminated,truncated,info=env.step({'rtl':design(env.c,alt)})
 print(json.dumps({'architecture':alt,'reward':reward,'correct':info['tested_correct'],'episode_done':terminated or truncated}))
