from copy import deepcopy
from .spec import Config,specification,validate_profile
from .rtl import design
from .evaluate import Evaluator
class QualityEnv:
 def __init__(self,name,horizon=4,cache=None,objective=None,**config):
  if type(horizon) is not int or not 1<=horizon<=32:raise ValueError('horizon')
  self.objective=objective or ('memory' if name=='tlb' else 'compact')
  if self.objective not in (('memory',) if name=='tlb' else ('stream','compact')):raise ValueError('objective')
  self.c=Config(name,**config);validate_profile(self.c);self.q=Evaluator(cache);self.horizon=horizon;self.steps=None
 def reset(self,seed=1):
  if type(seed) is not int or not 0<=seed<=0xffffffff:raise ValueError('episode seed')
  self.steps=0;self.source=design(self.c);self.last=self.q.evaluate(self.c,self.source)
  if not self.last['tested_correct']:raise RuntimeError('quality baseline qualification failed; private journal retained')
  return self.observation(),{}
 def observation(self):return {'task':self.c.name,'rtl':self.source,'objective':self.objective,'constraints':specification(self.c),'evaluation':deepcopy(self.last),'remaining_steps':self.horizon-self.steps}
 def step(self,action):
  if self.steps is None or self.steps>=self.horizon:raise RuntimeError('episode boundary')
  if not isinstance(action,dict) or set(action)!={'rtl'}:raise ValueError('source-only action')
  self.source=action['rtl'];self.last=self.q.evaluate(self.c,self.source);self.steps+=1
  return self.observation(),self.last.get('objectives',{}).get(self.objective,{}).get('reward',0.),False,self.steps>=self.horizon,{'tested_correct':self.last['tested_correct']}
