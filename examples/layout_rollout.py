import argparse,json
from chip_rl.layout.env import LayoutEnv
from chip_rl.layout.rtl import design
p=argparse.ArgumentParser();p.add_argument('--cache');p.add_argument('--objective',choices=('transpose','diagonal'),default='transpose');a=p.parse_args();e=LayoutEnv(cache=a.cache,objective=a.objective,horizon=2);obs,_=e.reset(seed=19);print(json.dumps({'design':'row_major','reward':obs['evaluation']['reward']}))
for name in ('xor','add'):
 obs,reward,_,done,_=e.step({'rtl':design(name)});print(json.dumps({'design':name,'reward':reward,'correct':obs['evaluation']['tested_correct'],'done':done}))
