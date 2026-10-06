"""Finite source-catalog rollout. No policy training or search superiority claim."""
import argparse,json
from chip_rl.cycle.env import CycleEnv
from chip_rl.cycle.rtl import design
p=argparse.ArgumentParser();p.add_argument('--task',choices=['dma','router','scoreboard','accelerator'],default='router');p.add_argument('--cache');a=p.parse_args()
env=CycleEnv(a.task,horizon=2,cache=a.cache);obs,_=env.reset()
print(json.dumps({'step':0,'evaluation':obs['evaluation']}))
for i,alt in enumerate([True,'decoded' if a.task=='router' else 'pruned'],1):
 obs,reward,_,done,_=env.step({'rtl':design(env.c,alternate=alt)})
 print(json.dumps({'step':i,'evaluation':obs['evaluation'],'reward':reward,'done':done}))
