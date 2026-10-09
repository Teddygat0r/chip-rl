"""Cached generic-cell synthesis; cost figures are not routed PPA."""
from pathlib import Path
import json,tempfile,shutil,fcntl
from ..evaluate import TrustedEvaluator,sanitize,logical_depth,digest,run,tool,Rejected
from .spec import PORTS
class Synthesis:
 def __init__(self,cache=None):self.host=TrustedEvaluator(cache);self.root=self.host.root
 def compile(self,n,source):
  sanitize(source);key=digest(source+str(n)+self.host.tool_fingerprint+Path(__file__).read_text());dest=self.root/('integer-rms-'+key)
  with (self.root/('integer-rms-'+key+'.lock')).open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   if not (dest/'netlist.json').exists():
    with tempfile.TemporaryDirectory(dir=self.root,prefix='integer-rms-build-') as td:
     p=Path(td);(p/'candidate.sv').write_text(source)
     (p/'synth.ys').write_text(f'read_verilog -sv candidate.sv; chparam -set N {n} candidate; hierarchy -check -top candidate; synth -top candidate; check -assert; write_json netlist.json; write_verilog -noattr netlist.v')
     run([tool('yosys'),'-s','synth.ys'],p,'integer-rms-synthesis',120);self.inspect(p)
     if dest.exists():shutil.rmtree(dest)
     shutil.copytree(p,dest)
   return dest,self.inspect(dest)
 def inspect(self,p):
  m=json.loads((p/'netlist.json').read_text())['modules']['candidate']
  if {n:(v['direction'],len(v['bits'])) for n,v in m['ports'].items()}!=PORTS:raise Rejected('integer RMS interface changed')
  if any(not c['type'].startswith('$_') for c in m['cells'].values()):raise Rejected('unsupported synthesis cell')
  depth=logical_depth(m);cells=len(m['cells'])
  if cells<1:raise Rejected('missing synthesized logic')
  return {'cells':cells,'logic_depth':depth,'timing_scope':'generic_ABC_logic_depth_proxy','physical':'not_run'}
