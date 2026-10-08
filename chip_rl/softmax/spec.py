from dataclasses import dataclass,asdict
from pathlib import Path
import json,hashlib
@dataclass(frozen=True)
class Config:
 name:str='softmax'
 def __post_init__(self):
  if self.name!='softmax':raise ValueError('softmax task')
PORTS={'clk':('input',1),'rst':('input',1),'in_valid':('input',1),'in_ready':('output',1),'in_data':('input',128),'in_mask':('input',16),'out_valid':('output',1),'out_ready':('input',1),'out_data':('output',256)}
HEADER='module candidate #(parameter N=8)('+','.join(d+' '+(f'[{w-1}:0] ' if w>1 else '')+n for n,(d,w) in PORTS.items())+');\n'
def shapes(split):
 d={'development':[4,8],'heldout':[3,7,16],'reserve':[5,12],'audit':[1,2,6,9,15],'review':[16]}
 if split not in d:raise ValueError('split')
 return d[split]
def specification(c):return {'version':'softmax-v23.1','config':asdict(c),'status':'experimental','development_lanes':shapes('development'),'ports':PORTS,'max_cells':25000,'max_logic_depth':160,'accepted_deadline':'40*N+4','minimum_registered_latency':1,'oracle':'80-digit independent Decimal exp(x/16), normalized over active logits','output_scale':4096,'absolute_error_limit':1/256,'L1_error_limit':1/64,'sum_error_units':'N-1','shift_error_units':2,'formal':'not_run','physical':'not_run','independent_evaluation':False,'os_isolation':'not_provided','protocol':Path(__file__).with_name('contracts.md').read_text()}
def identity(c):return hashlib.sha256(json.dumps(specification(c),sort_keys=True).encode()).hexdigest()
