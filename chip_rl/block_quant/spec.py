"""Block-adaptive signed INT16 to INT8 experimental scored contract."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json

NS=(1,2,4,8,16)
SUPPORTED_NS=tuple(range(1,17))
PORTS={'clk':('input',1),'rst':('input',1),'in_valid':('input',1),'in_ready':('output',1),
       'in_data':('input',512),'out_valid':('output',1),'out_ready':('input',1),'out_data':('output',256)}
HEADER='module candidate #(parameter N=4)('+','.join(d+' '+(f'[{w-1}:0] ' if w>1 else '')+n for n,(d,w) in PORTS.items())+');\n'

@dataclass(frozen=True)
class Config:
 n:int=4
 def __post_init__(self):
  if type(self.n) is not int or self.n not in SUPPORTED_NS:raise ValueError('N must be an integer from 1 through 16')

def configurations(split,requested=None):
 if split in ('development','heldout'):
  if requested is None:return NS
  if type(requested) is not int or requested not in SUPPORTED_NS:raise ValueError('N')
  return tuple(sorted(set(NS)|{requested}))
 raise ValueError('split')

def specification(c):
 return {'task':'block_quant','version':'block-quant-v39-parameter-coverage','config':asdict(c),'ports':PORTS,
  'action_type':'complete_synthesizable_RTL_source','timing':'latency_flexible_ready_valid',
  'supported_active_lanes':SUPPORTED_NS,
  'scored_configurations':{'development':NS,'heldout':NS},
  'measured_configurations':configurations('development',c.n),
  'reward':'balanced_area_cycle_proxy','reward_qualified':'conditional',
  'formal':'not_run','physical':'not_run','independent_evaluation':False,
  'protocol':Path(__file__).with_name('contracts.md').read_text()}

def identity(c):return hashlib.sha256(json.dumps(specification(c),sort_keys=True).encode()).hexdigest()
