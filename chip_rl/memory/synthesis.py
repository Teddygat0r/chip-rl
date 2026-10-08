from pathlib import Path
import json,tempfile,shutil,fcntl
from ..evaluate import TrustedEvaluator,sanitize,logical_depth,digest,run,tool,Rejected
from .spec import PORTS,identity
class Synthesis:
 def __init__(self,cache=None):self.host=TrustedEvaluator(cache);self.root=self.host.root
 def compile(self,c,source):
  sanitize(source);key=digest(source+identity(c)+self.host.tool_fingerprint+'memory-v12');dest=self.root/('memory-'+key)
  with (self.root/('memory-'+key+'.lock')).open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   if not (dest/'netlist.json').exists():
    with tempfile.TemporaryDirectory(dir=self.root,prefix='memory-build-') as td:
     p=Path(td);(p/'candidate.sv').write_text(source);(p/'synth.ys').write_text(f'read_verilog -sv candidate.sv; chparam -set ENTRIES {c.entries} candidate; hierarchy -check -top candidate; synth -top candidate; check -assert; write_json netlist.json; write_verilog -noattr netlist.v')
     run([tool('yosys'),'-s','synth.ys'],p,'synthesis');self.inspect(c,p)
     if dest.exists():shutil.rmtree(dest)
     shutil.copytree(p,dest)
   return dest,self.inspect(c,dest)
 def inspect(self,c,p):
  m=json.loads((p/'netlist.json').read_text())['modules']['candidate']
  if {k:(v['direction'],len(v['bits'])) for k,v in m['ports'].items()}!=PORTS:raise Rejected('memory interface changed')
  depth=logical_depth(m);cells=len(m['cells'])
  if not 1<=cells<=c.max_cells or depth>96:raise Rejected('memory resource budget')
  return {'cells':cells,'logic_depth':depth}
