from pathlib import Path
from dataclasses import asdict
import json,math,hashlib,secrets,time
from ..audit import journal
from ..evaluate import Rejected,digest
from .spec import specification,identity,configurations
from .synthesis import Synthesis
from .rtl import design
from .workloads import generate
from .simulation import simulate
class Evaluator:
 def __init__(self,cache=None):self.synth=Synthesis(cache)
 @journal
 def evaluate(self,c,source,*,replay_seed=None,artifacts=None,heldout=False):
  start=time.monotonic();root=Path(artifacts)
  seed=secrets.randbits(128) if replay_seed is None else replay_seed
  r={**specification(c),'tested_correct':False,'reward':0.,'source_sha256':digest(source) if isinstance(source,str) else None,'contract_sha256':identity(c),'tool_fingerprint':self.synth.host.tool_fingerprint,'cases':[],'heldout':heldout}
  r['recipe_sha256']=digest(self.synth.host.recipe_fingerprint+Path(__file__).parent.parent.joinpath('audit.py').read_text()+''.join(p.read_text() for p in sorted(Path(__file__).parent.glob('*.py'))))
  try:
   if type(seed) is not int or not 0<=seed<2**128:raise Rejected('private seed')
   (root/'private-seed.json').write_text(json.dumps({'seed':seed}))
   for i,cc in enumerate(configurations(c)):
    sd,sm=self.synth.compile(cc,source);base=design(cc);work=generate(cc,seed+i,heldout)
    cm=simulate(cc,source,sd/'netlist.v',work,root/f'case-{i}'/'candidate')|sm
    if base==source:bm=dict(cm)
    else:
     bd,bsm=self.synth.compile(cc,base);bm=simulate(cc,base,bd/'netlist.v',work,root/f'case-{i}'/'baseline')|bsm
    r['cases'].append({'config':asdict(cc),'candidate':cm,'baseline':bm})
   ratios={k:math.exp(sum(math.log(x['candidate'][k]/x['baseline'][k]) for x in r['cases'])/len(r['cases'])) for k in ('cells','cycles','latency_sum','memory_reads')}
   eligible=all(x['candidate']['cycles']<=2*x['baseline']['cycles'] and x['candidate']['latency_sum']<=2*x['baseline']['latency_sum'] and x['candidate']['memory_reads']<=1.25*x['baseline']['memory_reads'] for x in r['cases'])
   loss=sum(w*math.log(ratios[k]) for k,w in [('cells',.45),('cycles',.30),('latency_sum',.15),('memory_reads',.10)])
   r.update(tested_correct=True,validation='rtl_and_mapped_pass',objective_eligible=eligible,reward=1-.5*math.tanh(loss) if eligible else 0.,ratios=ratios,objective={'weights':{'cells':.45,'cycles':.30,'latency_sum':.15,'memory_reads':.10},'max_cycle_ratio':2,'max_latency_ratio':2,'max_memory_read_ratio':1.25,'frequency_or_power_claim':False})
  except (Rejected,ValueError,OSError,AssertionError) as e:
   r['validation']='rejected';(root/'private-error.txt').write_text(str(e))
  r['elapsed_s']=round(time.monotonic()-start,3);(root/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r
