from dataclasses import dataclass,asdict,replace
import hashlib,json
@dataclass(frozen=True)
class Config:
 width:int=16
 depth:int=4
 max_cells:int=4096
 max_ticks:int=30000
 def __post_init__(self):
  if any(type(x) is not int for x in (self.width,self.depth,self.max_cells,self.max_ticks)):raise ValueError('integer configuration')
  if self.width not in (4,8,16,32) or self.depth not in (2,4,8,16):raise ValueError('unsupported dimensions')
  if not 1<=self.max_cells<=4096 or not 128<=self.max_ticks<=30000:raise ValueError('host budgets')
@dataclass(frozen=True)
class Choice:
 architecture:str='binary_gray'
 sync_stages:int=2
 def __post_init__(self):
  if self.architecture not in ('binary_gray','gray_only') or type(self.sync_stages) is not int or self.sync_stages not in (2,3):raise ValueError('architecture choices')
CHOICES=tuple(Choice(a,s) for a in ('binary_gray','gray_only') for s in (2,3))
def specification(c):return {'task':'cdc_fifo','version':'digital-cdc-v11.1','config':asdict(c),'status':'experimental_digital_model','pilot_eligible':False,'action_type':'architecture_parameters_only','architectures':['binary_gray','gray_only'],'sync_stages':[2,3],'clocks':'independent positive write/read event clocks','reset':'coordinated cancellation; synchronous local resets; skewed release; no traffic until both domains released','capacity':c.depth,'logic_depth_limit':64,'formal':'not_run','physical':'not_run','metastability_modeled':False,'physical_cdc_safety_verified':False,'os_isolation':'not_provided'}
def identity(c):return hashlib.sha256(json.dumps(specification(c),sort_keys=True).encode()).hexdigest()
def configurations(c):return list(dict.fromkeys((c,replace(c,width=8,depth=2),replace(c,width=32,depth=8),replace(c,width=8,depth=16))))
