from dataclasses import dataclass,asdict,replace
import hashlib,json
NAMES=('mshr','tlb')
@dataclass(frozen=True)
class Config:
 name:str
 entries:int=4
 max_cells:int=30000
 max_cycles:int=20000
 def __post_init__(self):
  if self.name not in NAMES:raise ValueError('memory task')
  if any(type(v) is not int for v in (self.entries,self.max_cells,self.max_cycles)):raise ValueError('integer parameters')
  if self.entries not in (2,4,6,8) or not 1<=self.max_cells<=30000 or not 256<=self.max_cycles<=20000:raise ValueError('configuration budget')
def specification(c):return {'version':'memory-v12.1','config':asdict(c),'status':'experimental_memory_system','pilot_eligible':False,'timing':'latency_flexible_tagged_transactions','action_type':'source_only','formal':'not_run','physical':'not_run','os_isolation':'not_provided','reset':'synchronous coordinated cancellation of clients and external memory','logic_depth_limit':96,'minimum_latency':1,'maximum_response_cycles':2048}
def identity(c):return hashlib.sha256(json.dumps(specification(c),sort_keys=True).encode()).hexdigest()
def configurations(c):return list(dict.fromkeys((c,replace(c,entries=2),replace(c,entries=8))))
PORTS={'clk':('input',1),'rst':('input',1),'req_valid':('input',1),'req_ready':('output',1),'req_addr':('input',16),'req_tag':('input',8),'req_aux':('input',8),'inv_valid':('input',1),'inv_asid':('input',2),'out_valid':('output',1),'out_ready':('input',1),'out_tag':('output',8),'out_data':('output',32),'out_fault':('output',2),'mem_valid':('output',1),'mem_ready':('input',1),'mem_addr':('output',16),'mem_tag':('output',4),'resp_valid':('input',1),'resp_ready':('output',1),'resp_tag':('input',4),'resp_data':('input',128)}
HEADER='module candidate #(parameter ENTRIES=4)('+','.join(f'{d} '+(f'[{w-1}:0] ' if w>1 else '')+n for n,(d,w) in PORTS.items())+');\n'
