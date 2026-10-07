"""A real HDL-evaluated parameter search; no trained policy or physical claim."""
from chip_rl.cdc.env import CDCEnv

env=CDCEnv(horizon=3)
obs,_=env.reset(seed=17)
print('baseline',obs['evaluation']['reward'])
for action in ({'architecture':'gray_only','sync_stages':2},
               {'architecture':'binary_gray','sync_stages':3},
               {'architecture':'gray_only','sync_stages':3}):
 obs,reward,_,done,info=env.step(action)
 print(action,'reward',reward,'digitally qualified',info['tested_correct'],'done',done)
