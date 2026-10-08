"""Two real RTL evaluations, not a trained policy or a physical-design result."""
import argparse
from chip_rl.memory.env import MemoryEnv
from chip_rl.memory.rtl import CATALOG,design
p=argparse.ArgumentParser();p.add_argument('task',choices=CATALOG);p.add_argument('--cache');a=p.parse_args()
e=MemoryEnv(a.task,horizon=1,cache=a.cache);obs,_=e.reset(17)
print('baseline',obs['evaluation']['reward'])
obs,reward,_,done,info=e.step({'rtl':design(e.c,CATALOG[a.task][1])})
print('alternative',reward,'tested_correct',info['tested_correct'],'done',done)
