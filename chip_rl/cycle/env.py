"""Source-only experimental cycle episodes. Independent of the six pilot API."""
from copy import deepcopy
from importlib.resources import files
from ..tasks import Config
from .rtl import design
from .evaluate import CycleEvaluator
class CycleEnv:
 def __init__(self,name,horizon=4,cache=None):
  if name not in ('dma','router','scoreboard','accelerator'):raise ValueError('cycle family')
  if type(horizon) is not int or not 1<=horizon<=32:raise ValueError('horizon')
  self.c=Config(name,depth=16);self.q=CycleEvaluator(cache);self.horizon=horizon;self.steps=None
 def reset(self,seed=1):
  if type(seed) is not int or not 0<=seed<=0xffffffff:raise ValueError('seed must be an unsigned 32-bit integer')
  # Compatibility only: never selects evaluation randomness.
  self.steps=0;self.source=design(self.c);self.result=self.q.evaluate(self.c,self.source)
  if not self.result['tested_correct']:raise RuntimeError('experimental baseline failed')
  return self.observation(),{}
 def observation(self):return {'task':self.c.name,'rtl':self.source,'evaluation':deepcopy(self.result),'remaining_steps':self.horizon-self.steps,'action_schema':{'rtl':'complete parameterized module source'},'contract_text':files('chip_rl.cycle').joinpath('contracts.md').read_text()}
 def step(self,action):
  if self.steps is None or self.steps>=self.horizon:raise RuntimeError('reset/episode boundary')
  if not isinstance(action,dict) or set(action)!={'rtl'}:raise ValueError('source-only action')
  self.source=action['rtl'];self.result=self.q.evaluate(self.c,self.source);self.steps+=1
  return self.observation(),self.result['reward'],False,self.steps>=self.horizon,{'tested_correct':self.result['tested_correct']}
