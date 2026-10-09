"""Host-owned compressed 2-of-4 INT8 sparse dot contract."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json
GS=tuple(range(1,9))
PORTS={'clk':('input',1),'rst':('input',1),'in_valid':('input',1),'in_ready':('output',1),'in_data':('input',512),'out_valid':('output',1),'out_ready':('input',1),'out_data':('output',32)}
HEADER='module candidate #(parameter G=4)('+','.join(d+' '+(f'[{w-1}:0] ' if w>1 else '')+n for n,(d,w) in PORTS.items())+');\n'
PAIRS=((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
@dataclass(frozen=True)
class Config:
 g:int=4
 def __post_init__(self):
  if type(self.g) is not int or self.g not in GS:raise ValueError('G must be an integer in 1..8')
def configurations(split):
 if split=='development':return (1,2,4)
 if split=='heldout':return (3,5,6,7)
 raise ValueError('split')
def specification(c):
 return {'task':'sparse24_dot_requant','version':'sparse24-v35-experimental','config':asdict(c),'ports':PORTS,
  'action_type':'complete_synthesizable_RTL_source','timing':'latency_flexible_ready_valid',
  'scored_configurations':{'development':tuple(sorted(set(configurations('development'))|{c.g})),
   'heldout':tuple(sorted(set(configurations('heldout'))|{c.g}))},'reward':'balanced_area_cycle_proxy','reward_qualified':'conditional',
  'formal':'not_run','physical':'not_run','independent_evaluation':False,
  'protocol':Path(__file__).with_name('contracts.md').read_text()}
def identity(c):return hashlib.sha256(json.dumps(specification(c),sort_keys=True).encode()).hexdigest()
