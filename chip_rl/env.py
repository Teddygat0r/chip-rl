"""Gym-style (dependency-free) edit/evaluate episodes."""
from copy import deepcopy
from importlib.resources import files
from .tasks import Config
from .rtl import design
from .evaluate import evaluate

class ChipEnv:
    def __init__(self, name, horizon=8, **config):
        if type(horizon) is not int or not 1<=horizon<=1024: raise ValueError('horizon must be positive')
        self.config=Config(name,**config); self.horizon=horizon; self.baseline=None
    def reset(self,seed=1):
        if type(seed) is not int or not 0<=seed<=0xffffffff: raise ValueError('seed must be an unsigned 32-bit integer')
        self.seed=seed; self.steps=0; self.source=design(self.config)
        self.baseline=evaluate(self.config,self.source,seed=seed)
        if not self.baseline['correct']: raise RuntimeError(self.baseline)
        self.last=self.baseline
        return self.observation(), {'baseline':deepcopy(self.baseline)}
    def observation(self):
        return {'task':self.config.name,'rtl':self.source,'evaluation':deepcopy(self.last),'remaining_steps':self.horizon-self.steps,
                'action_schema':{'rtl':'complete module source OR use stages','stages':[1,2,4,6]},
                'contract_text':files('chip_rl').joinpath('contracts.md').read_text(),'constraints':deepcopy(self.baseline['config'])}
    def step(self,action):
        if self.baseline is None: raise RuntimeError('reset first')
        if self.steps>=self.horizon: raise RuntimeError('episode finished')
        if set(action) not in ({'rtl'},{'stages'}): raise ValueError('action cannot change task/constraints/evaluator')
        self.source=action['rtl'] if 'rtl' in action else design(self.config,stages=action['stages'])
        self.last=evaluate(self.config,self.source,seed=self.seed,baseline=self.baseline)
        self.steps+=1
        return self.observation(),self.last['reward'],False,self.steps>=self.horizon,{'correct':self.last['correct']}
