"""Bounded finite-catalog search controls using real HDL measurements.
No learned policy, LLM, open-ended RTL generation or paid service is involved.
"""
import argparse,copy,hashlib,json,random,secrets,shutil,time
from pathlib import Path
from dataclasses import replace
from chip_rl.tasks import Config
from chip_rl.architectures import CATALOG,architecture
from chip_rl.evaluate import TrustedEvaluator
from chip_rl.memory.spec import Config as MemoryConfig
from chip_rl.memory.rtl import CATALOG as MEMORY_CATALOG,design
from chip_rl.memory.evaluate import Evaluator as MemoryEvaluator
from chip_rl.suite import compact
METHODS=('enumeration','random','handwritten_feedback')
POLICY_SEEDS=(17,29,43)
CATALOGS={n:tuple(CATALOG[n]) for n in ('dot','tensor')}|{'tlb':MEMORY_CATALOG['tlb']}
BUDGETS={'tlb':2,'dot':3,'tensor':3}
UNIQUE_LIMITS={'tlb':12,'dot':30,'tensor':27}
def plan():
 return {'version':'search-control-v13.1','tasks':list(CATALOGS),'methods':list(METHODS),'policy_seeds':list(POLICY_SEEDS),'catalogs':CATALOGS,'development_query_budget_including_baseline':BUDGETS,'maximum_actual_unique_evaluations':UNIQUE_LIMITS,'maximum_total_actual_evaluations':69,'development_queries_charged':72,'heldout_queries_charged':45,'objective':'existing fixed balanced objective for arithmetic; existing fixed memory objective for TLB','pairing':'same private workload seed for all development candidates/methods within a task/trial; independent held-out seeds','heldout_structures':{'tlb':[6],'dot':[1,3],'tensor':[1,3]},'selection':'freeze all development winners before any held-out evaluation; no held-out adaptation','memoization':'identical source/config/seed queries share one measured result and count against every querying method budget','timing':'record actual physical-evaluation wall time and nominal shared-query charges; query-budget matched, not a controlled cold-run or equal-wall-time experiment','tool_caps':'unchanged evaluator caps: 90 CPU seconds, 3GiB address space, 64MiB output file; 120-second tool wall timeout for these tasks','trained_policy':False,'llm_calls':0,'paid_services':False,'prior_knowledge':'handwritten heuristic knows these previously authored templates and historical results; not a blind or learned agent','scope':'finite catalog controls, not autonomous RTL design'}
def choose_next(task,method,history,rng):
 labels=CATALOGS[task];seen={x['label'] for x in history};remaining=[x for x in labels if x not in seen]
 if not history:return labels[0]
 if not remaining:raise ValueError('catalog exhausted')
 if method=='enumeration':return remaining[0]
 if method=='random':return rng.choice(remaining)
 if method!='handwritten_feedback':raise ValueError('unknown method')
 preferred={'tlb':'dual','dot':'product_pipe','tensor':'tensor4'}[task]
 if preferred in remaining:return preferred
 if task=='dot':
  choice='serial2' if history[-1]['reward']>history[0]['reward'] else 'serial1'
  if choice in remaining:return choice
 return remaining[0]
def choose_winner(history):
 valid=[x for x in history if x['tested_correct'] and x['objective_eligible']]
 if not valid:raise ValueError('no qualified feasible candidate')
 return max(valid,key=lambda x:x['reward'])['label']
def transact(task,method,oracle,seed):
 history=[];rng=random.Random(seed)
 for _ in range(BUDGETS[task]):
  label=choose_next(task,method,history,rng)
  if label in {r['label'] for r in history}:raise ValueError('duplicate query')
  r=oracle(label)
  history.append({'label':label,'reward':r['result']['reward'],'tested_correct':r['result']['tested_correct'],'objective_eligible':r['result'].get('objective_eligible',False),'measured_seconds_charged':r['measured_seconds'],'shared_measurement':r['shared_measurement']})
 return {'queries':history,'winner':choose_winner(history),'query_count':len(history),'nominal_seconds_charged':sum(x['measured_seconds_charged'] for x in history)}
class Study:
 def __init__(self,task,output,cache):
  self.task=task;self.output=output;output.mkdir(parents=True,exist_ok=False);output.chmod(0o700)
  self.c=MemoryConfig(task) if task=='tlb' else Config(task)
  self.q=MemoryEvaluator(cache) if task=='tlb' else TrustedEvaluator(cache)
  self.sources={n:design(self.c,n) if task=='tlb' else architecture(self.c,n) for n in CATALOGS[task]}
  self.seeds=[{'development':secrets.randbits(128),'heldout':secrets.randbits(128)} for _ in POLICY_SEEDS]
  assert len({v for x in self.seeds for v in x.values()})==6
  (output/'private-seeds.json').write_text(json.dumps(self.seeds,indent=2)+'\n')
  (output/'plan.json').write_text(json.dumps(plan(),indent=2)+'\n')
  self.samples={};self.actual_calls=0;self.started=time.monotonic();self.frozen=False
 def measure(self,trial,stage,dimension,label):
  if stage=='heldout' and not self.frozen:raise ValueError('holdout before freeze')
  key=f'{trial}/{stage}/{dimension}/{label}';shared=key in self.samples
  if not shared:
   if self.actual_calls>=UNIQUE_LIMITS[self.task]:raise ValueError('physical evaluation budget exceeded')
   if shutil.disk_usage(self.output).free<300*1024**2:raise OSError('less than 300MiB free; stop before starting another evaluation')
   c=self.c
   if stage=='heldout':c=replace(c,entries=dimension) if self.task=='tlb' else replace(c,k=dimension)
   kwargs={'replay_seed':self.seeds[trial][stage],'artifacts':self.output/'private-evaluations'/key}
   if self.task=='tlb':kwargs['heldout']=stage=='heldout'
   self.actual_calls+=1;start=time.monotonic();r=self.q.evaluate(c,self.sources[label],**kwargs);elapsed=time.monotonic()-start
   assert r['source_sha256']==hashlib.sha256(self.sources[label].encode()).hexdigest()
   self.samples[key]={'result':r,'measured_seconds':elapsed}
   compact(kwargs['artifacts'])
   (self.output/'measurements.json').write_text(json.dumps(self.samples,indent=2)+'\n')
   print(self.task,key,r['tested_correct'],r['reward'],round(elapsed,3),flush=True)
  return copy.deepcopy(self.samples[key])|{'shared_measurement':shared}
 def run(self):
  trials=[]
  for i,seed in enumerate(POLICY_SEEDS):
   methods={};order=METHODS[i:]+METHODS[:i]
   for method in order:methods[method]=transact(self.task,method,lambda label:self.measure(i,'development',0,label),seed)
   trials.append({'policy_seed':seed,'method_order':list(order),'methods':methods})
  # Persist immutable choices before consulting any new structure/workload.
  frozen=[{m:{'winner':r['winner'],'source_sha256':hashlib.sha256(self.sources[r['winner']].encode()).hexdigest()} for m,r in t['methods'].items()} for t in trials]
  (self.output/'frozen.json').write_text(json.dumps(frozen,indent=2)+'\n');self.frozen=True
  dims=(6,) if self.task=='tlb' else (1,3)
  for i,t in enumerate(trials):
   for method,r in t['methods'].items():
    r['heldout']=[]
    for dimension in dims:
     h=self.measure(i,'heldout',dimension,r['winner']);assert h['result']['source_sha256']==frozen[i][method]['source_sha256']
     r['heldout'].append({'dimension':dimension,**h})
  assert self.actual_calls<=UNIQUE_LIMITS[self.task]
  report={'task':self.task,'plan':plan(),'trials':trials,'actual_evaluations':self.actual_calls,'development_queries_charged':sum(r['query_count'] for t in trials for r in t['methods'].values()),'heldout_queries_charged':sum(len(r['heldout']) for t in trials for r in t['methods'].values()),'actual_wall_seconds':time.monotonic()-self.started,'measurements':self.samples,'all_measured_sources_correct':all(r['result']['tested_correct'] for r in self.samples.values()),'trained_policy':False}
  (self.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
  if not report['all_measured_sources_correct']:raise RuntimeError('previously valid catalog source failed; investigate retained evidence')
  return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('task',choices=CATALOGS);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args();Study(a.task,a.output,a.cache).run()
