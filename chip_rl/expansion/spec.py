from dataclasses import dataclass,asdict,replace
from ..objectives import PROFILES
from ..contracts import LOGIC_LEVEL_LIMIT
import hashlib,json
NAMES=('permute','coalesce','retire','ecc','crc','freelist','scan','topk','histogram')
@dataclass(frozen=True)
class Config:
 name:str
 width:int=16
 depth:int|None=None
 k:int=4
 objective:str='balanced'
 max_cells:int=50000
 max_cycles:int=30000
 def __post_init__(self):
  if self.depth is None:object.__setattr__(self,'depth',32 if self.name=='freelist' else 16 if self.name=='histogram' else 8)
  if self.name not in NAMES or self.objective not in PROFILES:raise ValueError('task/goal')
  if any(type(v) is not int for v in (self.width,self.depth,self.k,self.max_cells,self.max_cycles)):raise ValueError('integer configuration required')
  widths=(8,16,32,64) if self.name=='coalesce' else (8,16,24) if self.name=='crc' else (8,12,16)
  depths=(8,16,24,32) if self.name in ('freelist','histogram') else (4,6,8)
  if self.width not in widths or self.depth not in depths or self.k not in ((1,2,3,4) if self.name=='coalesce' else (2,3,4)):raise ValueError('unsupported dimension')
  if not 1<=self.max_cells<=50000 or not 128<=self.max_cycles<=30000:raise ValueError('budget')
 @property
 def lanes(self):return 2*self.k

def specification(c):
 return {'version':'long-history-v10.1' if c.name in ('crc','retire') else 'reset-qualified-v9.1' if c.name in ('ecc','coalesce','histogram') else 'collectives-v7.1' if c.name in ('scan','topk','histogram') else 'integrity-v6.1' if c.name in ('ecc','crc','freelist') else 'expansion-v5.1','config':asdict(c),'status':'experimental_expansion','pilot_eligible':False,
  'timing':'fixed_physical_cycles' if c.name=='retire' else 'latency_flexible_transactions',
  'objective':'fixed_cycle_area' if c.name=='retire' else c.objective,
  'source_only_actions':True,'mapped_logic_depth_limit':LOGIC_LEVEL_LIMIT[c.name],'formal':'not_run','physical':'not_run','os_isolation':'not_provided',
  'default_workload_units':{'target_short':[128,256],'target_long':[2048,2304] if c.name=='histogram' else [1024,1280],'structural':[512,768]},
  'long_history_verification':({'required':True,'cycle_budget':900000 if c.name=='crc' else 200000,'separate_from_scored_workload':True} if c.name in ('crc','retire') else None),
  'response_bound':64,'minimum_registered_latency':1 if c.name!='retire' else None}
def identity(c):return hashlib.sha256(json.dumps(specification(c),sort_keys=True).encode()).hexdigest()
def cases(c,seed):
 variants=[c]+([replace(c,depth=4),replace(c,width=8)] if c.name=='retire' else [replace(c,depth=8),replace(c,depth=32),replace(c,k=2)] if c.name=='freelist' else [replace(c,depth=8),replace(c,width=8),replace(c,k=2)] if c.name=='histogram' else [replace(c,width=8),replace(c,width=16)] if c.name in ('crc','ecc') else [replace(c,k=2),replace(c,width=8)])
 variants=list({(x.width,x.depth,x.k):x for x in variants}.values());out=[]
 for i,cc in enumerate(variants):
  for j in range(2 if i==0 else 1):
   secret=int.from_bytes(hashlib.sha256(f'{seed}:{i}:{j}'.encode()).digest()[:16],'big')
   lo,hi=(128,256) if i==0 and j==0 else ((2048,2304) if c.name=='histogram' else (1024,1280)) if i==0 else (512,768)
   out.append((i,j,cc,secret,lo+secret%(hi-lo+1)))
 return out
