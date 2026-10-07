from copy import deepcopy
from importlib.resources import files
from .spec import Config,specification
from .rtl import design
from .evaluate import Evaluator
class ExpansionEnv:
 def __init__(self,name,horizon=4,cache=None,**config):
  if type(horizon) is not int or not 1<=horizon<=32:raise ValueError('horizon')
  self.c=Config(name,**config);self.q=Evaluator(cache);self.horizon=horizon;self.steps=None
 def reset(self,seed=1):
  if type(seed) is not int or not 0<=seed<=0xffffffff:raise ValueError('seed')
  self.steps=0;self.source=design(self.c);self.last=self.q.evaluate(self.c,self.source)
  if not self.last['tested_correct']:raise RuntimeError('baseline qualification failed')
  return self.observation(),{}
 def observation(self):return {'task':self.c.name,'rtl':self.source,'evaluation':deepcopy(self.last),'remaining_steps':self.horizon-self.steps,'constraints':specification(self.c),'contract_text':files('chip_rl.expansion').joinpath('contracts.md').read_text()}
 def step(self,action):
  if self.steps is None or self.steps>=self.horizon:raise RuntimeError('episode boundary')
  if not isinstance(action,dict) or set(action)!={'rtl'}:raise ValueError('source-only action')
  self.source=action['rtl'];self.last=self.q.evaluate(self.c,self.source);self.steps+=1
  return self.observation(),self.last['reward'],False,self.steps>=self.horizon,{'tested_correct':self.last['tested_correct']}
