"""A local search agent, no model credentials or paid services needed."""
import argparse,json
from chip_rl import ChipEnv,NAMES
p=argparse.ArgumentParser();p.add_argument('--task',choices=NAMES,default='elastic');a=p.parse_args()
e=ChipEnv(a.task,horizon=3);observation,info=e.reset(seed=17)
for stages in (4,2,1):
    observation,reward,terminated,truncated,info=e.step({'stages':stages})
    print(json.dumps({'task':a.task,'stages':stages,'reward':reward,'correct':info['correct'],'metrics':observation['evaluation'].get('metrics')}))
