"""A real edit/evaluate episode; scripted candidate selection, not trained RL."""
import argparse,json
from chip_rl.env import ChipEnv
from chip_rl.tasks import Config
from chip_rl.architectures import architecture,CATALOG
p=argparse.ArgumentParser();p.add_argument('--task',choices=CATALOG,default='elastic');a=p.parse_args()
e=ChipEnv(a.task,horizon=len(CATALOG[a.task])-1);obs,_=e.reset(seed=17)
print(json.dumps({'action':'baseline','evaluation':obs['evaluation']}))
for label in CATALOG[a.task][1:]:
 obs,reward,_,_,_=e.step({'rtl':architecture(Config(a.task),label)})
 print(json.dumps({'action':label,'evaluation':obs['evaluation']}))
