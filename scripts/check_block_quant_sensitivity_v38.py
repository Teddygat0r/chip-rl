"""Three new private seeds, unchanged v37 RTL/evaluator, fixed case gates."""
import argparse,hashlib,json,os,secrets,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from chip_rl.evaluate import digest
from chip_rl.block_quant.evaluate import Evaluator
from chip_rl.block_quant.rtl import design
from chip_rl.block_quant.scoring import score_cases
from chip_rl.block_quant.spec import Config,NS,identity

NAMES=('serial','parallel','chunked4')
MAX_CALLS=16
MAX_SIMULATIONS=384

def sha(data):return hashlib.sha256(data).hexdigest()

def verify_freeze(evaluator):
 record=json.loads((ROOT/'evidence/v38/source-evaluator-freeze.json').read_text())
 sources={name:design(name) for name in NAMES}
 for name,src in sources.items():
  assert {'sha256':sha(src.encode()),'bytes':len(src.encode())}==record['candidate_sources'][name],name
 for relative,expected in record['evaluator_and_contract_files_sha256'].items():
  assert sha((ROOT/relative).read_bytes())==expected,relative
 package=ROOT/'chip_rl/block_quant'
 recipe=digest(''.join(p.read_text() for p in sorted(package.glob('*')) if p.suffix in ('.py','.md'))+
               evaluator.synth.host.recipe_fingerprint)
 assert recipe==record['recipe_sha256']
 assert identity(Config(4))==record['contract_sha256']
 assert evaluator.synth.host.tool_fingerprint==record['tool_fingerprint']
 # All 15 exact-source/N/tool netlists already exist from v37. Never build a
 # new synthesis result in this sensitivity run.
 for name,src in sources.items():
  for n in NS:
   key=digest(src+str(n)+evaluator.synth.host.tool_fingerprint+
              (package/'synthesis.py').read_text())
   target=evaluator.synth.root/('block-quant-'+key)
   assert (target/'netlist.json').is_file() and (target/'netlist.v').is_file(),(name,n)
 return record,sources

def metrics_view(metrics):
 fields=('cells','workload_cycles','stream_ii_numerator','stream_ii_denominator',
         'ready_low_cycles','output_blocked_cycles','input_blocked_cycles',
         'accepted_to_first_sum','offered_to_consumption_sum',
         'accepted_count','consumed_count','workload_sha256','watchdog_sha256')
 return {key:metrics[key] for key in fields}

def analyze(by_seed):
 """Use the unchanged scorer for each seed and all 15 pooled cases."""
 result={'per_seed':{},'pooled':{},'failing_cases':[],'n4_chunked_margin':[]}
 for seed_id,designs in by_seed.items():
  public={}
  for name in NAMES:
   evaluated=designs[name]
   if not evaluated['tested_correct'] or len(evaluated['cases'])!=5:
    raise AssertionError('functional or progress validation failed: '+seed_id+'/'+name)
   recomputed=score_cases(evaluated['cases'])
   for key in ('reward','service_qualified','reward_qualified','hard_constraints_passed',
               'scored_cases','constraint_failures'):
    assert recomputed[key]==evaluated[key],(seed_id,name,key)
   public[name]={'tested_correct':evaluated['tested_correct'],'validation':evaluated['validation'],
    'reward':evaluated['reward'],'service_qualified':evaluated['service_qualified'],
    'reward_qualified':evaluated['reward_qualified'],'hard_constraints_passed':evaluated['hard_constraints_passed'],
    'scored_cases':evaluated['scored_cases'],'constraint_failures':evaluated['constraint_failures'],
    'cases':evaluated['cases'],'source_sha256':evaluated['source_sha256'],
    'candidate_simulation_cache_hits':evaluated['candidate_simulation_cache_hits'],
    'baseline_simulation_cache_hits':evaluated['baseline_simulation_cache_hits']}
   for case,row in zip(evaluated['cases'],evaluated['scored_cases']):
    if row['constraints_passed']:continue
    result['failing_cases'].append({'seed_id':seed_id,'design':name,'N':case['N'],
     'failed_gates':[k for k,v in row['constraints'].items() if not v],
     'area_ratio':row['area_ratio'],'completion_ratio':row['completion_ratio'],
     'stream_ii':row['stream_ii'],'candidate':metrics_view(case['candidate']),
     'baseline':metrics_view(case['baseline'])})
   if name=='chunked4':
    case=evaluated['cases'][2];row=evaluated['scored_cases'][2]
    assert case['N']==row['N']==4
    result['n4_chunked_margin'].append({'seed_id':seed_id,
     'candidate_cycles':case['candidate']['workload_cycles'],
     'baseline_cycles':case['baseline']['workload_cycles'],
     'cycle_margin_baseline_minus_candidate':case['baseline']['workload_cycles']-case['candidate']['workload_cycles'],
     'completion_ratio':row['completion_ratio'],'completion_gate_passed':row['constraints']['completion_ratio_at_most_1'],
     'input_blocked_candidate':case['candidate']['input_blocked_cycles'],
     'input_blocked_baseline':case['baseline']['input_blocked_cycles'],
     'output_blocked_candidate':case['candidate']['output_blocked_cycles'],
     'output_blocked_baseline':case['baseline']['output_blocked_cycles']})
  result['per_seed'][seed_id]=public
  # The same seed and N must mean the exact same paired operands and traffic.
  for n in NS:
   cases=[next(x for x in designs[name]['cases'] if x['N']==n) for name in NAMES]
   hashes={(x[label]['workload_sha256'],x[label]['watchdog_sha256'])
           for x in cases for label in ('candidate','baseline')}
   assert len(hashes)==1,(seed_id,n,'unpaired workload')
   reference=cases[0]['candidate']
   assert all(x['baseline']==reference for x in cases),(seed_id,n,'baseline mismatch')
  serial=designs['serial'];parallel=designs['parallel']
  assert serial['service_qualified'] and serial['reward']==0
  assert parallel['tested_correct'] and not parallel['service_qualified'] and parallel['reward']==0
  n16=parallel['scored_cases'][-1]
  assert n16['N']==16 and n16['area_ratio']>4 and not n16['constraints']['area_ratio_at_most_4']
 for name in NAMES:
  cases=[case for designs in by_seed.values() for case in designs[name]['cases']]
  pooled=score_cases(cases)
  rows=[row for designs in by_seed.values() for row in designs[name]['scored_cases']]
  scores=[designs[name]['reward'] for designs in by_seed.values()]
  result['pooled'][name]={**pooled,
   'area_ratio_range':[min(x['area_ratio'] for x in rows),max(x['area_ratio'] for x in rows)],
   'completion_ratio_range':[min(x['completion_ratio'] for x in rows),max(x['completion_ratio'] for x in rows)],
   'per_seed_scores':scores,'observed_score_range':[min(scores),max(scores)],
   'per_seed_service_qualified':[designs[name]['service_qualified'] for designs in by_seed.values()],
   'functional_case_count':len(cases),'failed_service_case_count':sum(not x['constraints_passed'] for x in rows)}
 return result

def run(cache,out,private):
 cache=Path(cache).resolve();out=Path(out).resolve();private=Path(private).resolve()
 assert not private.exists() and not out.exists(),'use fresh private and public output paths'
 evaluator=Evaluator(cache)
 record,sources=verify_freeze(evaluator)  # Must finish before drawing any seeds.
 private.mkdir(parents=True,mode=0o700)
 os.environ['CHIP_RL_TRACE_ROOT']=str(private)
 seeds=[secrets.randbits(128) for _ in range(3)]  # Exactly three new seeds.
 assert len(set(seeds))==3,'duplicate seed; stop without drawing another'
 for path in (Path('/tmp/chip-rl-v36-private/replay-seed.json'),Path('/tmp/chip-rl-v37-private/replay-seed.json')):
  if path.exists():assert all(x!=json.loads(path.read_text())['seed'] for x in seeds),'historical seed collision'
 (private/'replay-seeds.json').write_text(json.dumps({'seed_1':seeds[0],'seed_2':seeds[1],'seed_3':seeds[2]},indent=2)+'\n')
 (private/'replay-seeds.json').chmod(0o600)
 initial={p.name for p in cache.glob('block-quant-*') if p.is_dir()}
 by_seed={};calls=0
 for index,seed in enumerate(seeds,1):
  seed_id=f'seed_{index}';by_seed[seed_id]={}
  for name,source in sources.items():
   assert calls<MAX_CALLS and len(list(private.rglob('*-simulation-*.log')))<MAX_SIMULATIONS
   evaluated=evaluator.evaluate(Config(4),source,replay_seed=seed,split='heldout')
   calls+=1;by_seed[seed_id][name]=evaluated
   (private/'progress.json').write_text(json.dumps({'completed_evaluator_calls':calls,
    'latest_seed_id':seed_id,'latest_architecture':name,'latest_tested_correct':evaluated['tested_correct']})+'\n')
   if not evaluated['tested_correct']:
    raise RuntimeError('functional/harness discrepancy; stop before further evaluation: '+seed_id+'/'+name)
  # Detect pairing, scoring, and baseline discrepancies before the next seed.
  analyze({seed_id:by_seed[seed_id]})
 analyzed=analyze(by_seed)
 sims=list(private.rglob('*-simulation-*.log'))
 new_synth=[p.name for p in cache.glob('block-quant-*') if p.is_dir() and p.name not in initial]
 assert calls==9 and calls<=MAX_CALLS and len(sims)<=MAX_SIMULATIONS
 assert not new_synth,'unexpected synthesis cache miss'
 summary={'task':'block_quant','study':'v38-three-seed-fixed-gate-sensitivity',
  'seed_count':3,'seed_ids':list(by_seed),'Ns':list(NS),'architectures':list(NAMES),
  'freeze_record_sha256':sha((ROOT/'evidence/v38/source-evaluator-freeze.json').read_bytes()),
  'candidate_sources':record['candidate_sources'],'recipe_sha256':record['recipe_sha256'],
  'contract_sha256':record['contract_sha256'],'tool_fingerprint':record['tool_fingerprint'],
  'evaluation_calls':calls,'simulator_runs':len(sims),'new_synthesis_builds':0,
  'validation_counts':{'functional_rtl_mapped':45,'synthesis_from_exact_cache':45,'formal':0,'physical':0},
  **analyzed,'private_trace_path':str(private)}
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps({'summary':str(out),'evaluation_calls':calls,'simulator_runs':len(sims),
  'scores':{name:summary['pooled'][name]['reward'] for name in NAMES},
  'n4_chunked_margin':summary['n4_chunked_margin']},indent=2))

def main():
 p=argparse.ArgumentParser()
 for name in ('cache','out','private'):p.add_argument('--'+name,required=True)
 a=p.parse_args();run(a.cache,a.out,a.private)

if __name__=='__main__':main()
