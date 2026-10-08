import argparse,json,time
from pathlib import Path
from chip_rl.audit import journal
from chip_rl.quality.spec import Config,identity
from chip_rl.quality.rtl import design
from chip_rl.quality.synthesis import Synthesis
from chip_rl.quality.stress import arithmetic_checks
from chip_rl.quality.workloads import generate
from chip_rl.quality.simulation import simulate
from chip_rl.quality.tlb_simulation import simulate as tlb_simulate
from chip_rl.evaluate import Rejected,digest
from chip_rl.suite import compact
class Direct:
 def __init__(self,cache):self.s=Synthesis(cache)
 @journal
 def evaluate(self,c,source,*,replay_seed=None,artifacts=None):
  p=Path(artifacts);start=time.monotonic();r={'tested_correct':False,'scope':'unscored_direct_configuration','config':c.__dict__,'source_sha256':digest(source),'contract_sha256':identity(c),'tool_fingerprint':self.s.host.tool_fingerprint}
  try:
   d,sm=self.s.compile(c,source);f=tlb_simulate if c.name=='tlb' else simulate;w=generate(c,replay_seed) if c.name=='tlb' else arithmetic_checks(c,replay_seed)
   r.update(metrics=f(c,source,d/'netlist.v',w,p/'simulation')|sm,tested_correct=True)
  except (Rejected,ValueError,OSError,AssertionError) as e:(p/'private-error.txt').write_text(str(e))
  r['elapsed_s']=time.monotonic()-start;(p/'result.json').write_text(json.dumps(r,indent=2));return r
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(exist_ok=False);rows=[]
cases=[(Config(n,k=16,m=1,n=1 if n=='dot' else 2),label) for n in ('dot','tensor') for label in ('fold1','fold2','fold4','adaptive','shift1','shift2')]+[(Config('tlb',entries=e),'w4r4') for e in (2,3)]
for c,label in cases:
 dest=a.output/(c.name+'-'+label+'-'+str(c.entries));r=Direct(a.cache).evaluate(c,design(c,label),artifacts=dest);rows.append({'label':label,'result':r});compact(dest);(a.output/'results.json').write_text(json.dumps(rows,indent=2));print(c.name,label,c.entries,r['tested_correct'],flush=True)
assert all(x['result']['tested_correct'] for x in rows)
