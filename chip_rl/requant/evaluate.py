from pathlib import Path
import json,math,time
from ..audit import journal
from ..evaluate import Rejected,digest
from .spec import specification,identity,shapes
from .synthesis import Synthesis
from .rtl import design
from .workloads import generate
from .simulation import simulate
class Evaluator:
 def __init__(self,cache=None):self.synth=Synthesis(cache)
 @journal
 def evaluate(self,c,source,*,replay_seed=None,artifacts=None,split='development'):
  root=Path(artifacts);start=time.monotonic();r={'task':'requant','tested_correct':False,'reward':0.,'objective_eligible':False,'validation':'rejected','cases':[],'source_sha256':digest(source) if isinstance(source,str) else None,'contract_sha256':identity(c),'split':split,'tool_fingerprint':self.synth.host.tool_fingerprint,'formal':'not_run','physical':'not_run','independent_evaluation':False}
  r['recipe_sha256']=digest(''.join(p.read_text() for p in sorted(Path(__file__).parent.glob('*')) if p.suffix in ('.py','.md'))+self.synth.host.recipe_fingerprint)
  try:
   if type(replay_seed) is not int or not 0<=replay_seed<2**128:raise Rejected('private seed')
   baseline=design()
   for n in shapes(split):
    work=generate(n,replay_seed+n,split);case={'N':n}
    for who,src in [('candidate',source),('baseline',baseline)]:
     if who=='baseline' and source==baseline:case[who]=dict(case['candidate']);continue
     net,sm=self.synth.compile(n,src);p=root/f'n{n}'/who;p.mkdir(parents=True)
     for name in ('synth.ys','netlist.json'):(p/name).write_bytes((net/name).read_bytes())
     case[who]=simulate(n,src,net/'netlist.v',work,p/'simulation')|sm
    r['cases'].append(case)
   ratios={k:math.exp(sum(math.log(x['candidate'][k]/x['baseline'][k]) for x in r['cases'])/len(r['cases'])) for k in ('cells','logic_depth','cycles')}
   eligible=all(x['candidate']['cycles']<=4*x['baseline']['cycles'] and x['candidate']['latency_sum']<=6*x['baseline']['latency_sum'] for x in r['cases'])
   loss=.6*math.log(ratios['cells'])+.3*math.log(ratios['cycles'])+.1*math.log(ratios['logic_depth'])
   r.update(tested_correct=True,validation='exact_integer_rtl_mapped_pass',objective_eligible=eligible,reward=(1-.5*math.tanh(loss) if eligible else 0.),ratios=ratios)
  except (Rejected,ValueError,OSError,AssertionError) as e:(root/'private-error.txt').write_text(str(e))
  r['elapsed_s']=round(time.monotonic()-start,3);(root/'result.json').write_text(json.dumps(r,indent=2));return r
