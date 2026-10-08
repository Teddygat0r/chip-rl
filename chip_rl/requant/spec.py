from dataclasses import dataclass,asdict
from pathlib import Path
import json,hashlib
@dataclass(frozen=True)
class Config:
 name:str='requant'
 def __post_init__(self):
  if self.name!='requant':raise ValueError('requant task')
PORTS={'clk':('input',1),'rst':('input',1),'in_valid':('input',1),'in_ready':('output',1),'in_data':('input',192),'in_mask':('input',4),'out_valid':('output',1),'out_ready':('input',1),'out_data':('output',32)}
HEADER='module candidate #(parameter N=4)('+','.join(d+' '+(f'[{w-1}:0] ' if w>1 else '')+n for n,(d,w) in PORTS.items())+');\n'
def shapes(split):
 if split not in ('development','heldout'):raise ValueError('split')
 return [2,4] if split=='development' else [1,3]
def specification(c):return {'version':'requant-v24.1','config':asdict(c),'status':'experimental','ports':PORTS,'development_lanes':[2,4],'max_cells':45000,'max_logic_depth':160,'numerical_tolerance':0,'formal':'not_run','physical':'not_run','os_isolation':'not_provided','independent_evaluation':False,'protocol':Path(__file__).with_name('contracts.md').read_text()}
def identity(c):return hashlib.sha256(json.dumps(specification(c),sort_keys=True).encode()).hexdigest()
