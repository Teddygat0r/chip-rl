"""Source-only agent boundary. Host replay controls never enter actions."""
from copy import deepcopy
from importlib.resources import files
from .tasks import Config
from .rtl import design
from .evaluate import TrustedEvaluator
from .contracts import PILOT,specification

class ChipEnv:
    def __init__(self,name,horizon=8,**config):
        if type(horizon) is not int or not 1<=horizon<=1024:raise ValueError('horizon must be in 1..1024')
        if name not in PILOT:raise ValueError('experimental family excluded from pilot')
        self.config=Config(name,**config);self.horizon=horizon;self.baseline=None
        self._evaluator=TrustedEvaluator()
    def reset(self,seed=1):
        # Compatibility: this seed can identify agent search, never evaluation instances.
        if type(seed) is not int or not 0<=seed<=0xffffffff:raise ValueError('seed must be an unsigned 32-bit integer')
        self.steps=0;self.source=design(self.config)
        self.baseline=self._evaluator.evaluate(self.config,self.source)
        if not self.baseline['tested_correct']:raise RuntimeError('baseline qualification failed')
        self.last=self.baseline
        return self.observation(),{'baseline':deepcopy(self.baseline)}
    def observation(self):
        return {'task':self.config.name,'rtl':self.source,'evaluation':deepcopy(self.last),
                'remaining_steps':self.horizon-self.steps,'action_schema':{'rtl':'complete parameterized module source'},
                'contract_text':files('chip_rl').joinpath('contracts.md').read_text(),'constraints':specification(self.config)}
    def step(self,action):
        if self.baseline is None:raise RuntimeError('reset first')
        if self.steps>=self.horizon:raise RuntimeError('episode finished')
        if not isinstance(action,dict) or set(action)!={'rtl'}:raise ValueError('action must contain only rtl')
        self.source=action['rtl'];self.last=self._evaluator.evaluate(self.config,self.source);self.steps+=1
        return self.observation(),self.last['reward'],False,self.steps>=self.horizon,{'tested_correct':self.last['tested_correct']}
