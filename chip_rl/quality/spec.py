from dataclasses import dataclass,asdict,replace
from pathlib import Path
import hashlib,json
NAMES=('dot','tensor','tlb')
@dataclass(frozen=True)
class Config:
 name:str
 k:int=8
 m:int=1
 n:int=1
 entries:int=4
 max_cells:int=250000
 max_cycles:int=20000
 def __post_init__(self):
  if self.name not in ('dot','tensor','tlb'):raise ValueError('quality task')
  if any(type(x) is not int for x in (self.k,self.m,self.n,self.entries,self.max_cells,self.max_cycles)):raise ValueError('integer configuration')
  if not (1<=self.k<=16 and 1<=self.m<=4 and 1<=self.n<=4 and 2<=self.entries<=16 and 1<=self.max_cells<=250000 and 256<=self.max_cycles<=20000):raise ValueError('configuration bounds')
  if self.name=='dot' and (self.m,self.n)!=(1,1):raise ValueError('dot shape')
def specification(c):return {'version':'quality-v15.1','config':asdict(c),'status':'experimental','timing':'latency_flexible_transactions','action_type':'source_only','formal':'not_run','physical':'not_run','os_isolation':'not_provided','protocol':Path(__file__).with_name('contracts.md').read_text(),'logic_depth_limit':96,'development_dimensions':[asdict(x) for x in configurations(c)]}
def identity(c):return hashlib.sha256(json.dumps(specification(c),sort_keys=True).encode()).hexdigest()
def configurations(c,heldout=False):
 if c.name=='tlb':return [replace(c,entries=x) for x in ((12,15) if heldout=='stress' else (11,13) if heldout=='reserve' else (5,9) if heldout else (4,8))]
 if c.name=='dot':return [replace(c,k=x) for x in ((7,13) if heldout=='stress' else (5,11) if heldout else (4,8,16))]
 return [replace(c,m=m,n=n,k=k) for m,n,k in (((3,3,6),(4,1,10)) if heldout=='stress' else ((3,2,5),(2,3,11)) if heldout else ((2,2,4),(2,2,8),(1,2,16)))]
PORTS={'clk':('input',1),'rst':('input',1),'in_valid':('input',1),'in_ready':('output',1),'in_data':('input',1024),'out_valid':('output',1),'out_ready':('input',1),'out_data':('output',384)}
HEADER='module candidate #(parameter M=1,N=1,K=8)('+','.join(f'{d} '+(f'[{w-1}:0] ' if w>1 else '')+n for n,(d,w) in PORTS.items())+');\n'

def validate_profile(c):
 if (c.k,c.m,c.n,c.entries)!=(8,1,1,4):raise ValueError("quality profiles use a fixed dimension matrix; dimension overrides are not supported")
