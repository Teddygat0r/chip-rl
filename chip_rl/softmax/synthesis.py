from pathlib import Path
import json,tempfile,shutil,fcntl
from ..evaluate import TrustedEvaluator,sanitize,logical_depth,digest,run,tool,Rejected
from .spec import PORTS
class Synthesis:
 def __init__(self,cache=None):self.host=TrustedEvaluator(cache);self.root=self.host.root
 def compile(self,n,source):
  sanitize(source);key=digest(source+str(n)+self.host.tool_fingerprint+Path(__file__).read_text());dest=self.root/('softmax-'+key)
  with (self.root/('softmax-'+key+'.lock')).open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   if not (dest/'netlist.json').exists():
    with tempfile.TemporaryDirectory(dir=self.root,prefix='softmax-build-') as td:
     p=Path(td);(p/'candidate.sv').write_text(source)
     params=f'-set N {n}'
     (p/'synth.ys').write_text(f'read_verilog -sv candidate.sv; chparam {params} candidate; hierarchy -check -top candidate; synth -top candidate; check -assert; write_json netlist.json; write_verilog -noattr netlist.v')
     run([tool('yosys'),'-s','synth.ys'],p,'softmax-synthesis',60);self.inspect(p)
     if dest.exists():shutil.rmtree(dest)
     shutil.copytree(p,dest)
   return dest,self.inspect(dest)
 def inspect(self,p):
  m=json.loads((p/'netlist.json').read_text())['modules']['candidate']
  if {k:(v['direction'],len(v['bits'])) for k,v in m['ports'].items()}!=PORTS:raise Rejected('softmax interface changed')
  if any(not cell['type'].startswith('$_') for cell in m['cells'].values()):raise Rejected('unsupported synthesis cell')
  depth=logical_depth(m);cells=len(m['cells'])
  if not 1<=cells<=25000 or depth>160:raise Rejected('softmax resource budget')
  return {'cells':cells,'logic_depth':depth}
