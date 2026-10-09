"""Exact block frame-of-reference encoding over unsigned bytes."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json
NS=(1,2,4,8,16)
SUPPORTED_NS=NS
PORTS={'clk':('input',1),'rst':('input',1),'in_valid':('input',1),'in_ready':('output',1),
       'in_data':('input',512),'out_valid':('output',1),'out_ready':('input',1),'out_data':('output',256)}
HEADER='module candidate #(parameter N=4)('+','.join(d+' '+(f'[{w-1}:0] ' if w>1 else '')+n for n,(d,w) in PORTS.items())+');\n'
@dataclass(frozen=True)
class Config:
 n:int=4
 def __post_init__(self):
  if type(self.n) is not int or self.n not in NS:raise ValueError('N must be one of 1,2,4,8,16')
def configurations(split,requested=None):
 if split not in ('development','heldout'):raise ValueError('split')
 if requested is not None and (type(requested) is not int or requested not in NS):raise ValueError('N')
 return NS
def specification(c):
 return {'task':'block_for','version':'block-for-v1','config':asdict(c),'ports':PORTS,
  'action_type':'complete_synthesizable_RTL_source','timing':'latency_flexible_ready_valid',
  'supported_active_bytes':NS,'scored_configurations':{'development':NS,'heldout':NS},
  'measured_configurations':NS,'reward':'balanced_area_cycle_proxy','reward_qualified':'conditional',
  'formal':'not_run','physical':'not_run','independent_evaluation':False,
  'protocol':Path(__file__).with_name('contracts.md').read_text()}
def identity(c):return hashlib.sha256(json.dumps(specification(c),sort_keys=True).encode()).hexdigest()
