from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json
@dataclass(frozen=True)
class Shape:
 rows:int
 cols:int
 banks:int
 lanes:int
 def __post_init__(self):
  if any(type(x) is not int for x in (self.rows,self.cols,self.banks,self.lanes)):raise ValueError('integer shape')
  if self.rows not in (4,8,16) or self.cols not in (8,16,32) or self.banks not in (4,8,16) or self.lanes not in (8,16) or self.cols<self.banks:raise ValueError('shape')
 @property
 def words(self):return self.rows*self.cols
@dataclass(frozen=True)
class Config:
 name:str='layout'
 objective:str='transpose'
 def __post_init__(self):
  if self.name!='layout' or self.objective not in ('transpose','diagonal'):raise ValueError('layout task/objective')
MAX_CELLS=64
MAX_DEPTH=12
PORTS={'row':('input',6),'col':('input',6),'addr':('output',10)}
HEADER='module candidate #(parameter ROWS=8,COLS=8,BANKS=8)(input [5:0] row,col,output [9:0] addr);\n'
def shapes(split='development'):
 table={'development':[(8,8,8,8),(8,16,8,8)],'heldout':[(16,8,4,8),(16,16,16,16)],'reserve':[(4,16,4,8),(16,32,8,16)]}
 if split not in table:raise ValueError('split')
 return [Shape(*x) for x in table[split]]
def specification(c):
 return {'version':'layout-v20.1','config':asdict(c),'status':'experimental','timing':'stateless_address_mapper_with_fixed_clocked_bank_engine','source_only_actions':True,'mapper_cells_limit':MAX_CELLS,'mapper_logic_depth_limit':MAX_DEPTH,'memory_capacity':'ROWS*COLS 32-bit words; no padding','ports':PORTS,'development_shapes':[asdict(s) for s in shapes()],'protocol':Path(__file__).with_name('contracts.md').read_text(),'formal':'not_run','physical':'not_run','independent_evaluation':False,'os_isolation':'not_provided'}
def identity(c):return hashlib.sha256(json.dumps(specification(c),sort_keys=True).encode()).hexdigest()
