import argparse,json
from chip_rl.softmax.env import SoftmaxEnv
from chip_rl.softmax.rtl import design
p=argparse.ArgumentParser();p.add_argument('--cache');a=p.parse_args();env=SoftmaxEnv(horizon=5,cache=a.cache);obs,_=env.reset(21);print(json.dumps({'design':'full_serial','result':obs['evaluation']}))
for name in ('linear_serial','full_radix4','linear_radix4','full_radix4_round','full_radix4_tiny'):
 obs,reward,_,done,_=env.step({'rtl':design(name)});print(json.dumps({'design':name,'reward':reward,'correct':obs['evaluation']['tested_correct'],'max_abs_error':obs['evaluation'].get('max_abs_error'),'done':done}))
