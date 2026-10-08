"""A scripted source-edit rollout, not a trained policy."""
import argparse,json
from chip_rl.quality.env import QualityEnv
from chip_rl.quality.rtl import design
p=argparse.ArgumentParser();p.add_argument('task',choices=('dot','tensor','tlb'));p.add_argument('--cache');p.add_argument('--objective',choices=('stream','compact','memory'));a=p.parse_args()
e=QualityEnv(a.task,horizon=2,cache=a.cache,objective=a.objective);obs,_=e.reset(seed=7)
for label in (('w2','w4r4') if a.task=='tlb' else ('tree','shiftadaptive')):
 obs,reward,_,done,info=e.step({'rtl':design(e.c,label)})
 print(json.dumps({'architecture':label,'reward':reward,'correct':info['tested_correct'],'objectives':obs['evaluation'].get('objectives'),'done':done}))
