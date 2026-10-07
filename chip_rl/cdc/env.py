from dataclasses import asdict
from copy import deepcopy
from pathlib import Path
import tempfile
from .spec import Config,Choice,specification
from .rtl import design
from .evaluate import Evaluator
class CDCEnv:
 def __init__(self,horizon=4,cache=None,trace_root=None,**config):
  if type(horizon) is not int or not 1<=horizon<=32:raise ValueError('horizon')
  self.c=Config(**config);self.q=Evaluator(cache);self.horizon=horizon;self.steps=None;self.trace_root=Path(trace_root) if trace_root else None
 def _evaluate(self):
  path=None
  if self.trace_root:
   self.trace_root.mkdir(parents=True,exist_ok=True);self.trace_root.chmod(0o700);path=tempfile.mkdtemp(dir=self.trace_root,prefix='eval-')
  return self.q.evaluate(self.c,self.choice,artifacts=path)
 def reset(self,seed=1):
  if type(seed) is not int or not 0<=seed<=0xffffffff:raise ValueError('episode seed')
  self.steps=0;self.choice=Choice();self.last=self._evaluate()
  if not self.last['tested_correct']:raise RuntimeError('CDC baseline qualification failed')
  return self.observation(),{}
 def observation(self):return {'task':'cdc_fifo','architecture':asdict(self.choice),'rtl_read_only':design(self.choice),'constraints':specification(self.c),'evaluation':deepcopy(self.last),'remaining_steps':self.horizon-self.steps}
 def step(self,action):
  if self.steps is None or self.steps>=self.horizon:raise RuntimeError('episode boundary')
  if not isinstance(action,dict) or set(action)!={'architecture','sync_stages'}:raise ValueError('architecture-only action')
  self.choice=Choice(**action);self.last=self._evaluate();self.steps+=1
  return self.observation(),self.last['reward'],False,self.steps>=self.horizon,{'tested_correct':self.last['tested_correct']}
