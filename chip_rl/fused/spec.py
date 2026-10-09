"""Host-owned contract for one exact fused INT8 dot+bias+requant block."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json
KS=(1,2,4,8,16)
PORTS={'clk':('input',1),'rst':('input',1),'in_valid':('input',1),'in_ready':('output',1),'in_data':('input',512),'out_valid':('output',1),'out_ready':('input',1),'out_data':('output',32)}
HEADER='module candidate #(parameter K=4)('+','.join(d+' '+(f'[{w-1}:0] ' if w>1 else '')+n for n,(d,w) in PORTS.items())+');\n'
@dataclass(frozen=True)
class Config:
 k:int=4
 def __post_init__(self):
  if type(self.k) is not int or self.k not in KS:raise ValueError('K must be one of 1,2,4,8,16')
def configurations(split):
 if split=='development':return (2,4,8)
 if split=='heldout':return KS
 raise ValueError('split')
def specification(c):
 return {'task':'fused_dot_requant','version':'fused-v29-experimental','config':asdict(c),'ports':PORTS,'action_type':'complete_synthesizable_RTL_source','timing':'latency_flexible_ready_valid',
  'scored_configurations':{'development':tuple(sorted(set(configurations('development'))|{c.k})),
   'heldout':configurations('heldout')},
  'reward_policy':{'name':'experimental_balanced_proxy','formula':'max(0,1-exp(mean(log(area_ratio*completion_ratio))/2))',
   'hard_gates':{'area_ratio_at_most':4,'completion_ratio_at_most':1,'stream_ii_at_most':'K+4'},'correctness_required':True},
  'formal':'not_run','physical':'not_run','independent_evaluation':False,'protocol':Path(__file__).with_name('contracts.md').read_text()}
def identity(c):return hashlib.sha256(json.dumps(specification(c),sort_keys=True).encode()).hexdigest()
