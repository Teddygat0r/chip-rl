"""Source-only reset/step environment with conditional paired proxy reward."""
from copy import deepcopy
from .spec import Config,specification
from .rtl import design
from .evaluate import Evaluator

class BlockQuantEnv:
 def __init__(self,n=4,horizon=4,cache=None,*,trusted_replay_seed=None,split='development'):
  if type(horizon) is not int or not 1<=horizon<=32:raise ValueError('horizon')
  if split not in ('development','heldout'):raise ValueError('split')
  if trusted_replay_seed is not None and (type(trusted_replay_seed) is not int or not 0<=trusted_replay_seed<2**128):
   raise ValueError('trusted replay seed')
  self.c=Config(n);self.horizon=horizon;self.steps=None;self.q=Evaluator(cache)
  self.trusted_replay_seed=trusted_replay_seed;self.split=split
 def reset(self,seed=1):
  if type(seed) is not int or not 0<=seed<=0xffffffff:raise ValueError('episode seed')
  self.steps=0;self.source=design('serial')
  self.last=self.q.evaluate(self.c,self.source,replay_seed=self.trusted_replay_seed,split=self.split)
  if not self.last['tested_correct'] or not self.last['service_qualified'] or self.last['reward']!=0:
   raise RuntimeError('baseline validation failed; private journal retained')
  return self.observation(),{}
 def observation(self):
  return {'task':'block_quant','rtl':self.source,'constraints':specification(self.c),
   'evaluation':deepcopy(self.last),'remaining_steps':self.horizon-self.steps}
 def step(self,action):
  if self.steps is None or self.steps>=self.horizon:raise RuntimeError('episode boundary')
  if not isinstance(action,dict) or set(action)!={'rtl'}:raise ValueError('source-only action')
  self.source=action['rtl'];self.last=self.q.evaluate(self.c,self.source,replay_seed=self.trusted_replay_seed,split=self.split)
  self.steps+=1
  return (self.observation(),self.last['reward'],False,self.steps>=self.horizon,
   {'tested_correct':self.last['tested_correct'],'reward_qualified':self.last['reward_qualified'],
    'service_qualified':self.last['service_qualified'],'hard_constraints_passed':self.last['hard_constraints_passed']})
