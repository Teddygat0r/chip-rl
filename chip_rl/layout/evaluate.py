from dataclasses import asdict
from pathlib import Path
import json,math,time
from ..audit import journal
from ..evaluate import Rejected,digest
from .spec import Config,shapes,specification,identity,MAX_CELLS
from .synthesis import Synthesis
from .rtl import design
from .workloads import generate,oracle
from .simulation import mapping,workload,reset_cancellation
from .verification import probes

def score(cases):
 eligible=bool(cases) and all(x['candidate']['service_cycles']<=2*x['baseline']['service_cycles'] for x in cases)
 speed=math.exp(sum(math.log(x['baseline']['service_cycles']/x['candidate']['service_cycles']) for x in cases)/len(cases)) if cases else 0
 overhead=sum(x['candidate']['cells'] for x in cases)/len(cases) if cases else 0
 return {'eligible':eligible,'service_speedup_geomean':speed,'mean_mapper_cells':overhead,'reward':min(4.,max(0.,speed/(1+overhead/MAX_CELLS))) if eligible else 0.}
class Evaluator:
 def __init__(self,cache=None):self.synth=Synthesis(cache)
 @journal
 def evaluate(self,c,source,*,replay_seed=None,artifacts=None,split='development'):
  start=time.monotonic();root=Path(artifacts);r={'task':'layout','tested_correct':False,'reward':0.,'validation':'rejected','cases':[],'verification':[],'source_sha256':digest(source) if isinstance(source,str) else None,'contract_sha256':identity(c),'split':split,'formal':'not_run','physical':'not_run','independent_evaluation':False,'tool_fingerprint':self.synth.host.tool_fingerprint}
  r['recipe_sha256']=digest(''.join(p.read_text() for p in sorted(Path(__file__).parent.glob('*')) if p.suffix in ('.py','.sv','.md'))+self.synth.host.recipe_fingerprint)
  try:
   if not isinstance(c,Config):raise Rejected('configuration')
   if type(replay_seed) is not int or not 0<=replay_seed<2**128:raise Rejected('seed')
   base=design()
   for i,s in enumerate(shapes(split)):
    work=generate(s,replay_seed+i,c.objective,split);entry={'shape':asdict(s)}
    for who,src in [('candidate',source),('baseline',base)]:
     if who=='baseline' and source==base:entry[who]=dict(entry['candidate']);continue
     p=root/f'case-{i}'/who;p.mkdir(parents=True)
     net,sm=self.synth.compile(s,src)
     # Retain exact synthesis artifacts as well as command journal/cache identity.
     for name in ('candidate.sv','synth.ys','netlist.json','netlist.v'):(p/name).write_bytes((net/name).read_bytes())
     table=mapping(s,src,net/'netlist.v',p/'map');metrics=workload(s,src,net/'netlist.v',table,work,p/'workload');by_kind={}
     for q,v in zip(work,oracle(s,table,work)):by_kind[q['kind']]=by_kind.get(q['kind'],0)+v['service_cycles']
     entry[who]=metrics|sm|{'service_cycles_by_kind':by_kind}
     if who=='candidate':
      directed=workload(s,src,net/'netlist.v',table,probes(s,replay_seed+i),p/'verification')
      cancellation=reset_cancellation(s,src,net/'netlist.v',p/'reset-cancellation')
      r['verification'].append({'shape':asdict(s),'persistence':directed,'cancellation':cancellation,'included_in_reward':False})
    r['cases'].append(entry)
   sc=score(r['cases']);r.update(sc,tested_correct=True,validation='exhaustive_mapping_and_clocked_rtl_mapped_workload_pass')
  except (Rejected,ValueError,OSError,AssertionError) as e:(root/'private-error.txt').write_text(str(e))
  r['elapsed_s']=round(time.monotonic()-start,3);(root/'result.json').write_text(json.dumps(r,indent=2));return r
