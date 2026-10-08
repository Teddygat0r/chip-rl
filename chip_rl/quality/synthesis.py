from pathlib import Path
import json,tempfile,shutil,fcntl
from ..evaluate import TrustedEvaluator,sanitize,logical_depth,digest,run,tool,Rejected
from ..memory.spec import PORTS as TLB_PORTS
from .spec import PORTS,identity
class Synthesis:
 def __init__(self,cache=None):self.host=TrustedEvaluator(cache);self.root=self.host.root
 def compile(self,c,source):
  sanitize(source);key=digest(source+identity(c)+self.host.tool_fingerprint);dest=self.root/('quality-'+key)
  with (self.root/('quality-'+key+'.lock')).open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   if not (dest/'netlist.json').exists():
    with tempfile.TemporaryDirectory(dir=self.root,prefix='quality-build-') as td:
     p=Path(td);(p/'candidate.sv').write_text(source)
     params=f'-set ENTRIES {c.entries}' if c.name=='tlb' else f'-set M {c.m} -set N {c.n} -set K {c.k}'
     (p/'synth.ys').write_text(f'read_verilog -sv candidate.sv; chparam {params} candidate; hierarchy -check -top candidate; synth -top candidate; check -assert; write_json netlist.json; write_verilog -noattr netlist.v')
     run([tool('yosys'),'-s','synth.ys'],p,'synthesis');self.inspect(c,p)
     if dest.exists():shutil.rmtree(dest)
     shutil.copytree(p,dest)
   return dest,self.inspect(c,dest)
 def inspect(self,c,p):
  m=json.loads((p/'netlist.json').read_text())['modules']['candidate']
  if {k:(v['direction'],len(v['bits'])) for k,v in m['ports'].items()}!=(TLB_PORTS if c.name=='tlb' else PORTS):raise Rejected('quality interface changed')
  depth=logical_depth(m);cells=len(m['cells'])
  if not 1<=cells<=c.max_cells or depth>96:raise Rejected('quality resource budget')
  return {'cells':cells,'logic_depth':depth}
