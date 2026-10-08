from copy import deepcopy
from .spec import Config,specification
from .rtl import design
from .evaluate import Evaluator
class LayoutEnv:
 def __init__(self,name='layout',horizon=4,cache=None,objective='transpose'):
  if type(horizon) is not int or not 1<=horizon<=32:raise ValueError('horizon')
  self.c=Config(name,objective);self.horizon=horizon;self.steps=None;self.q=Evaluator(cache)
 def reset(self,seed=1):
  if type(seed) is not int or not 0<=seed<=0xffffffff:raise ValueError('episode seed')
  self.steps=0;self.source=design();self.last=self.q.evaluate(self.c,self.source)
  if not self.last['tested_correct']:raise RuntimeError('baseline qualification failed; private journal retained')
  return self.observation(),{}
 def observation(self):return {'task':'layout','rtl':self.source,'objective':self.c.objective,'constraints':specification(self.c),'evaluation':deepcopy(self.last),'remaining_steps':self.horizon-self.steps}
 def step(self,action):
  if self.steps is None or self.steps>=self.horizon:raise RuntimeError('episode boundary')
  if not isinstance(action,dict) or set(action)!={'rtl'}:raise ValueError('source-only action')
  self.source=action['rtl'];self.last=self.q.evaluate(self.c,self.source);self.steps+=1
  return self.observation(),self.last['reward'],False,self.steps>=self.horizon,{'tested_correct':self.last['tested_correct']}
