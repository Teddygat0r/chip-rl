"""Predeclared one-seed RTL/mapped sweep of the eleven intermediate lane counts."""
import argparse,hashlib,json,os,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from chip_rl.block_quant.evaluate import Evaluator
from chip_rl.block_quant.rtl import CATALOG,design
from chip_rl.block_quant.scoring import score_cases
from chip_rl.block_quant.spec import Config,NS,SUPPORTED_NS

MAX_TOTAL_GROWTH=4_000_000_000
MIN_WORKSPACE_FREE=5_000_000_000
MIN_TMP_FREE=750_000_000
NEXT_CALL_RESERVE=80_000_000

def allocated(path):
 total=0
 for base,dirs,files in os.walk(path):
  total+=Path(base).stat().st_blocks*512
  for name in files:total+=(Path(base)/name).stat().st_blocks*512
 return total

def free(path):
 st=os.statvfs(path)
 return st.f_bavail*st.f_frsize

def metrics_view(m):
 fields=('cells','logic_depth','workload_cycles','stream_ii_numerator','stream_ii_denominator',
  'accepted_count','consumed_count','arithmetic_vectors_checked','ready_low_cycles',
  'output_blocked_cycles','input_blocked_cycles','maximum_service_opportunity_age',
  'service_opportunity_bound','workload_sha256','watchdog_sha256','rtl_mapped_checked',
  'arithmetic_rtl_mapped_checked','reset_backpressure_checked','long_stall_checked',
  'reset_during_stall_checked')
 return {key:m[key] for key in fields}

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--cache',required=True)
 p.add_argument('--private',required=True)
 p.add_argument('--out',required=True)
 a=p.parse_args()
 cache=Path(a.cache).resolve();private=Path(a.private).resolve();out=Path(a.out).resolve()
 assert cache.is_dir() and private.is_dir() and not out.exists()
 assert out.parent==ROOT/'evidence/v39'
 freeze=json.loads((ROOT/'evidence/v39/migration-predeclared.json').read_text())
 seed_record=json.loads((private/'seed-selection.json').read_text())
 seed=seed_record['seed']
 assert type(seed) is int and 0<=seed<2**128
 assert hashlib.sha256(str(seed).encode()).hexdigest()==freeze['seed_sha256']
 assert freeze['existing_scored_Ns']==list(NS) and freeze['new_Ns']==[n for n in SUPPORTED_NS if n not in NS]
 assert tuple(CATALOG)==('serial','parallel','chunked4')
 sources={name:design(name) for name in CATALOG}
 for name,source in sources.items():
  assert {'sha256':hashlib.sha256(source.encode()).hexdigest(),'bytes':len(source.encode())}==freeze['candidate_sources'][name]
 os.environ['CHIP_RL_TRACE_ROOT']=str(private/'traces')
 evaluator=Evaluator(cache)
 v38=json.loads((ROOT/'evidence/v38/source-evaluator-freeze.json').read_text())
 assert evaluator.synth.host.tool_fingerprint==v38['tool_fingerprint']==freeze['tool_fingerprint']
 previous=json.loads((ROOT/'evidence/v39/attempt1-resource-stop.json').read_text())
 assert previous['completed_evaluator_invocations']==32
 start_size=allocated(cache)+allocated(private)
 start_free={'workspace':free('/workspace'),'tmp':free('/tmp')}
 assert start_free['workspace']>=MIN_WORKSPACE_FREE+NEXT_CALL_RESERVE
 assert start_free['tmp']>=MIN_TMP_FREE+NEXT_CALL_RESERVE
 existing_builds={x.name for x in cache.glob('block-quant-*') if x.is_dir()}
 results=[];calls=0
 for n in freeze['new_Ns']:
  paired=[]
  for name in CATALOG:
   growth=previous['new_allocated_bytes']+allocated(cache)+allocated(private)-start_size
   if growth+NEXT_CALL_RESERVE>MAX_TOTAL_GROWTH or free('/workspace')<MIN_WORKSPACE_FREE+NEXT_CALL_RESERVE or free('/tmp')<MIN_TMP_FREE+NEXT_CALL_RESERVE:
    raise RuntimeError(f'resource guard before N={n}/{name}: growth={growth}')
   evaluated=evaluator.evaluate(Config(n),sources[name],replay_seed=seed,split='heldout')
   calls+=1
   if not evaluated['tested_correct'] or evaluated['validation']!='exact_integer_rtl_mapped_pass':
    raise RuntimeError(f'failed correctness or progress: N={n}/{name}; see private trace')
   cases=evaluated['cases']
   if [case['N'] for case in cases]!=list(sorted(set(NS)|{n})) or not all(
      case['candidate_verified'] and case['baseline_verified'] for case in cases):
    raise RuntimeError(f'incomplete case set: N={n}/{name}')
   scored=score_cases([case for case in cases if case['N'] in NS])
   for field in ('reward','service_qualified','reward_qualified','hard_constraints_passed','scored_cases','constraint_failures'):
    if scored[field]!=evaluated[field]:raise RuntimeError(f'fixed reward changed: N={n}/{name}/{field}')
   case=next(case for case in cases if case['N']==n)
   gates=score_cases([case])['scored_cases'][0]
   if evaluated['candidate']!=case['candidate'] or evaluated['baseline']!=case['baseline']:
    raise RuntimeError(f'requested metrics mismatch: N={n}/{name}')
   paired.append((name,case))
   results.append({'N':n,'design':name,'source_sha256':evaluated['source_sha256'],
    'tested_correct':True,'fixed_five_reward':evaluated['reward'],
    'fixed_five_service_qualified':evaluated['service_qualified'],
    'candidate':metrics_view(case['candidate']),'baseline':metrics_view(case['baseline']),
    'per_N_gates':gates,'candidate_simulation_cache_hits':evaluated['candidate_simulation_cache_hits'],
    'baseline_simulation_cache_hits':evaluated['baseline_simulation_cache_hits']})
   growth=previous['new_allocated_bytes']+allocated(cache)+allocated(private)-start_size
   if growth>MAX_TOTAL_GROWTH or free('/workspace')<MIN_WORKSPACE_FREE or free('/tmp')<MIN_TMP_FREE:
    raise RuntimeError(f'resource guard after N={n}/{name}: growth={growth}')
   (private/'progress.json').write_text(json.dumps({'completed_calls':calls,'latest_N':n,
    'latest_design':name,'new_allocated_bytes':growth})+'\n')
  hashes={(case[label]['workload_sha256'],case[label]['watchdog_sha256'])
   for _,case in paired for label in ('candidate','baseline')}
  if len(hashes)!=1 or not all(case['baseline']==paired[0][1]['candidate'] for _,case in paired):
   raise RuntimeError(f'unpaired workload or baseline: N={n}')
 new_builds=[x.name for x in cache.glob('block-quant-*') if x.is_dir() and x.name not in existing_builds]
 simulations=list((private/'traces').rglob('*-simulation-*.log'))
 end_growth=previous['new_allocated_bytes']+allocated(cache)+allocated(private)-start_size
 assert calls==33 and len(results)==33 and end_growth<=MAX_TOTAL_GROWTH
 summary={'task':'block_quant','study':'v39-one-new-host-seed-migrated-intermediate-N',
  'base_commit':freeze['base_commit'],'migration_predeclaration':'evidence/v39/migration-predeclared.json',
  'previous_plan_status':freeze['previous_plan_status'],
  'tool_fingerprint':freeze['tool_fingerprint'],'private_seed_file':str(private/'seed-selection.json'),
  'seed_sha256':freeze['seed_sha256'],'candidate_sources':freeze['candidate_sources'],
  'existing_scored_Ns':list(NS),'new_Ns':freeze['new_Ns'],'fixed_gates_unchanged':True,
  'evaluation_calls':calls,'total_evaluator_invocations':previous['completed_evaluator_invocations']+calls,
  'interrupted_attempt':'evidence/v39/attempt1-resource-stop.json',
  'new_synthesis_builds':len(new_builds),
  'total_new_synthesis_builds':previous['new_synthesis_builds']+len(new_builds),
  'simulation_cache_hits':previous['simulation_cache_hits']+sum(
    row['candidate_simulation_cache_hits']+row['baseline_simulation_cache_hits'] for row in results),
  'simulator_runs':len(simulations),'validation_counts':{'new_N_functional_rtl_mapped':33,
    'new_N_synthesis':33,'formal':0,'physical':0},
  'per_N_gate_failures':[{'N':row['N'],'design':row['design'],'failed':[
    key for key,value in row['per_N_gates']['constraints'].items() if not value]}
    for row in results if not row['per_N_gates']['constraints_passed']],
  'start_free_bytes':start_free,'new_allocated_bytes':end_growth,
  'end_free_bytes':{'workspace':free('/workspace'),'tmp':free('/tmp')},'cases':results}
 out.write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps({'summary':str(out),'evaluation_calls':calls,'total_evaluator_invocations':previous['completed_evaluator_invocations']+calls,
  'interrupted_attempt':'evidence/v39/attempt1-resource-stop.json',
  'new_synthesis_builds':len(new_builds),
  'total_new_synthesis_builds':previous['new_synthesis_builds']+len(new_builds),
  'simulation_cache_hits':previous['simulation_cache_hits']+sum(
    row['candidate_simulation_cache_hits']+row['baseline_simulation_cache_hits'] for row in results),
  'simulator_runs':len(simulations),'gate_failures':summary['per_N_gate_failures'],
  'new_allocated_bytes':end_growth,'end_free_bytes':summary['end_free_bytes']},indent=2))

if __name__=='__main__':main()
