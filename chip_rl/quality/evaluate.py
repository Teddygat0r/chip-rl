from pathlib import Path
from dataclasses import asdict
import json,math,time
from ..audit import journal
from ..evaluate import Rejected,digest
from .spec import specification,identity,configurations,validate_profile
from .synthesis import Synthesis
from .rtl import design
from .workloads import generate
from .stress import arithmetic_checks
from .simulation import simulate as arithmetic_simulate
from .tlb_simulation import simulate as tlb_simulate
class Evaluator:
 def __init__(self,cache=None):self.synth=Synthesis(cache)
 @journal
 def evaluate(self,c,source,*,replay_seed=None,artifacts=None,heldout=False):
  start=time.monotonic();root=Path(artifacts);seed=replay_seed
  r={**specification(c),'tested_correct':False,'reward':0.,'source_sha256':digest(source) if isinstance(source,str) else None,'contract_sha256':identity(c),'tool_fingerprint':self.synth.host.tool_fingerprint,'cases':[],'verification':[],'heldout':heldout}
  basepath=Path(__file__).parent.parent
  recipe=self.synth.host.recipe_fingerprint+''.join(p.read_text() for p in sorted(Path(__file__).parent.glob('*.py')))+Path(__file__).with_name('contracts.md').read_text()+''.join((basepath/p).read_text() for p in ['audit.py','memory/oracles.py','memory/rtl.py','memory/workloads.py'])
  r['recipe_sha256']=digest(recipe)
  try:
   validate_profile(c)
   if type(heldout) is not bool and not (heldout=='stress' or c.name=='tlb' and heldout=='reserve'):raise Rejected('invalid split')
   if type(seed) is not int or not 0<=seed<2**128:raise Rejected('private seed')
   (root/'private-seed.json').write_text(json.dumps({'seed':seed}))
   for i,cc in enumerate(configurations(c,heldout)):
    sd,sm=self.synth.compile(cc,source);base=design(cc);bd,bsm=(sd,sm) if source==base else self.synth.compile(cc,base)
    for mode in (('memory',) if c.name=='tlb' else ('stream','compact')):
     work=generate(cc,seed+i,heldout,mode);sim=tlb_simulate if c.name=='tlb' else arithmetic_simulate
     cm=sim(cc,source,sd/'netlist.v',work,root/f'case-{i}-{mode}'/'candidate')|sm
     bm=dict(cm) if base==source else sim(cc,base,bd/'netlist.v',work,root/f'case-{i}-{mode}'/'baseline')|bsm
     r['cases'].append({'config':asdict(cc),'mode':mode,'candidate':cm,'baseline':bm})
    if c.name!='tlb':
     vm=arithmetic_simulate(cc,source,sd/'netlist.v',arithmetic_checks(cc,seed+i,heldout),root/f'case-{i}-unscored')
     r['verification'].append({'config':asdict(cc),'metrics':vm,'included_in_reward':False})
   objectives={}
   for mode in (('memory',) if c.name=='tlb' else ('stream','compact')):
    cases=[x for x in r['cases'] if x['mode']==mode];keys=('cells','cycles','latency_sum','memory_reads') if mode=='memory' else ('cells','cycles','latency_sum')
    ratios={k:math.exp(sum(math.log(x['candidate'][k]/x['baseline'][k]) for x in cases)/len(cases)) for k in keys}
    if mode=='memory':
     eligible=all(x['candidate']['cycles']<=2*x['baseline']['cycles'] and x['candidate']['latency_sum']<=2*x['baseline']['latency_sum'] and x['candidate']['memory_reads']<=1.25*x['baseline']['memory_reads'] for x in cases)
     loss=sum(w*math.log(ratios[k]) for k,w in [('cells',.45),('cycles',.30),('latency_sum',.15),('memory_reads',.10)])
    else:
     eligible=all(x['candidate']['cycles']<=(1.10 if mode=='stream' else 1.25)*x['baseline']['cycles'] and x['candidate']['maximum_latency']<=64 for x in cases);loss=math.log(ratios['cells'])
    objectives[mode]={'eligible':eligible,'reward':1-.5*math.tanh(loss) if eligible else 0.,'ratios':ratios}
   r.update(tested_correct=True,validation='rtl_and_mapped_pass',objectives=objectives,reward=objectives['memory' if c.name=='tlb' else 'compact']['reward'])
  except (Rejected,ValueError,OSError,AssertionError) as e:r['validation']='rejected';(root/'private-error.txt').write_text(str(e))
  r['elapsed_s']=round(time.monotonic()-start,3);(root/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r
