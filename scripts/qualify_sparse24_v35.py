"""One frozen-source, private-seed parameter comparison for sparse24 v35."""
import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chip_rl.sparse24.env import Sparse24Env
from chip_rl.sparse24.evaluate import Evaluator
from chip_rl.sparse24.rtl import HEADER, ROUND, SELECT, design
from chip_rl.sparse24.spec import Config, configurations


def sha(data):
 return hashlib.sha256(data).hexdigest()


def frozen_sources():
 freeze=json.loads((ROOT/'evidence/v35/frozen-source.json').read_text())
 for name in ('serial','pipeline'):
  source=design(name)
  assert {'sha256':sha(source.encode()),'bytes':len(source.encode())}==freeze['emitted_sources'][name],name
 for name,value in (('HEADER',HEADER),('ROUND',ROUND),('SELECT',SELECT)):
  assert sha(value.encode())==freeze['generator_fragments_sha256'][name],name
 for name in ('rtl.py','oracle.py','workloads.py'):
  path=ROOT/'chip_rl/sparse24'/name
  assert sha(path.read_bytes())==freeze['generator_files_sha256']['chip_rl/sparse24/'+name],name
 return {'serial':design('serial'),'pipeline':design('pipeline')}


def comparable(result):
 return {key:result[key] for key in ('tested_correct','validation','reward','reward_qualified',
  'hard_constraints_passed','scored_cases','candidate','baseline','cases')}


def checked(result,source,gs):
 assert result['source_sha256']==sha(source.encode())
 assert result['tested_correct'] and result['reward_qualified'] and result['hard_constraints_passed'],result
 assert tuple(result['declared_scored_Gs'])==tuple(gs)
 assert [case['G'] for case in result['cases']]==list(gs)
 for case in result['cases']:
  assert case['candidate_verified'] and case['baseline_verified']
  for label in ('candidate','baseline'):
   m=case[label]
   assert m['decoder_vectors_checked']==24*case['G']
   assert all(m[k] is True for k in ('decoder_rtl_mapped_checked','rtl_mapped_checked',
    'reset_backpressure_checked','long_stall_checked','reset_during_stall_checked',
    'long_stall_output_seen','reset_blocked_output_seen'))
   assert m['accepted_count']==m['consumed_count']==m['transactions']
   assert m['stream_transactions']==32
 assert all(row['constraints_passed'] and row['stream_ii_limit']==2*row['G']+4
            for row in result['scored_cases'])


def cli(g,seed,split,cache,sources):
 requests=[{'op':'reset','seed':1},{'op':'step','action':{'rtl':sources['pipeline']}},
           {'op':'step','action':{'rtl':sources['serial'],'G':g}}]
 cmd=[sys.executable,'-m','chip_rl.sparse24','--g',str(g),'--horizon','3',
      '--cache',str(cache),'--trusted-replay-seed',str(seed),'--split',split]
 proc=subprocess.run(cmd,input=''.join(json.dumps(x)+'\n' for x in requests),text=True,
                     capture_output=True,timeout=900,check=True,cwd=ROOT)
 responses=[json.loads(x) for x in proc.stdout.splitlines()]
 assert len(responses)==3 and responses[0]['ok'] and responses[1]['ok']
 assert not responses[2]['ok'] and 'source-only' in responses[2]['error']
 return {'serial':responses[0]['observation']['evaluation'],
         'pipeline':responses[1]['observation']['evaluation']},responses


def api_pair(g,seed,split,cache,sources,evaluator):
 gs=tuple(sorted(set(configurations(split))|{g}))
 direct={name:evaluator.evaluate(Config(g),source,replay_seed=seed,split=split)
         for name,source in sources.items()}
 for name,source in sources.items():checked(direct[name],source,gs)
 env=Sparse24Env(g,3,cache,trusted_replay_seed=seed,split=split)
 obs,_=env.reset();python={'serial':obs['evaluation']}
 before=env.steps
 try:env.step({'rtl':sources['pipeline'],'G':g})
 except ValueError:pass
 else:raise AssertionError('agent G override accepted')
 assert env.steps==before
 obs,reward,_,_,info=env.step({'rtl':sources['pipeline']})
 assert reward==obs['evaluation']['reward'] and info['reward_qualified']
 python['pipeline']=obs['evaluation']
 server,responses=cli(g,seed,split,cache,sources)
 parity={name:comparable(direct[name])==comparable(python[name])==comparable(server[name])
         for name in sources}
 assert all(parity.values()),parity
 assert direct['serial']['reward']==0 and direct['pipeline']['reward']>0
 return direct,parity,responses


def invalid_g(cache,seed,trace):
 before=len(list(trace.glob('eval-*/private-run.json')))
 outcome={}
 for g in (0,9):
  try:Config(g)
  except ValueError:pass
  else:raise AssertionError('invalid Config G accepted')
  cmd=[sys.executable,'-m','chip_rl.sparse24','--g',str(g),'--cache',str(cache),
       '--trusted-replay-seed',str(seed)]
  proc=subprocess.run(cmd,input='{"op":"reset","seed":1}\n',text=True,
                      capture_output=True,timeout=30,cwd=ROOT)
  response=json.loads(proc.stdout)
  assert not response['ok'] and 'G must be' in response['error']
  outcome[str(g)]=response['error']
 assert len(list(trace.glob('eval-*/private-run.json')))==before
 return outcome


def run(cache,out,private,seed,resume=False):
 sources=frozen_sources()  # No workload generation before this assertion.
 cache=Path(cache).resolve();out=Path(out).resolve();private=Path(private).resolve()
 if resume:
  assert private.is_dir() and not out.exists(),'no incomplete private run to resume'
  assert json.loads((private/'replay-seed.json').read_text())['seed']==seed
 else:
  assert not private.exists(),'private run directory already exists'
  private.mkdir(parents=True,mode=0o700)
  (private/'initial-synthesis-cache.json').write_text(json.dumps(sorted(p.name for p in cache.glob('sparse24-*') if p.is_dir()))+'\n')
  (private/'replay-seed.json').write_text(json.dumps({'seed':seed,'comparison_split':'heldout',
    'historical_seed':320041,'historical_split':'development'})+'\n')
  (private/'replay-seed.json').chmod(0o600)
 os.environ['CHIP_RL_TRACE_ROOT']=str(private)
 initial_dirs=set(json.loads((private/'initial-synthesis-cache.json').read_text()))
 q=Evaluator(cache)
 # Same root seed and heldout split give one paired workload per G=3,5,6,7.
 fresh,parity,responses=api_pair(5,seed,'heldout',cache,sources,q)
 assert tuple(fresh['serial']['declared_scored_Gs'])==(3,5,6,7)
 (private/'heldout-cli-responses.json').write_text(json.dumps(responses))
 # A public historical replay exercises an original G through all three APIs.
 old,old_parity,old_responses=api_pair(4,320041,'development',cache,sources,q)
 (private/'historical-cli-responses.json').write_text(json.dumps(old_responses))
 invalid=invalid_g(cache,seed,private)
 journals=list(private.glob('eval-*/private-run.json'))
 simlogs=list(private.rglob('*-simulation-*.log'))
 synth_dirs=[p for p in cache.glob('sparse24-*') if p.is_dir() and p.name not in initial_dirs]
 assert len(journals)<=24 and len(simlogs)<=160,(len(journals),len(simlogs))
 assert len(simlogs)<=56 and len(simlogs)%4==0,len(simlogs)
 assert len(synth_dirs)<=14,len(synth_dirs)
 summary={'comparison':'sparse24-v35-parameter-admission','split':'heldout',
  'declared_Gs':list(fresh['serial']['declared_scored_Gs']),
  'historical_development_Gs':list(old['serial']['declared_scored_Gs']),
  'frozen_sources':{name:sha(source.encode()) for name,source in sources.items()},
  'tool_fingerprint':q.synth.host.tool_fingerprint,
  'recipe_sha256':fresh['serial']['recipe_sha256'],
  'api_parity_new_G5':parity,'api_parity_old_G4':old_parity,
  'invalid_G_pre_evaluation':invalid,'evaluation_calls':len(journals),
  'simulator_runs':len(simlogs),'new_synthesis_builds':len(synth_dirs),
  'validation_counts':{'functional_rtl_mapped':8,'synthesis':8,'formal':0,'physical':0},
  'results':{name:{key:result[key] for key in ('tested_correct','validation','reward',
   'reward_qualified','hard_constraints_passed','scored_cases','candidate_simulation_cache_hits',
   'baseline_simulation_cache_hits')} for name,result in fresh.items()},
  'new_G_cases':{name:result['cases'] for name,result in fresh.items()},
  'historical_G4_results':{name:{key:result[key] for key in ('tested_correct','validation','reward',
   'reward_qualified','scored_cases')} for name,result in old.items()},
  'historical_G4_cases':{name:next(case for case in result['cases'] if case['G']==4)
   for name,result in old.items()},
  'private_trace_path':str(private)}
 out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps({'summary':str(out),'evaluation_calls':len(journals),
  'simulator_runs':len(simlogs),'new_synthesis_builds':len(synth_dirs),
  'heldout_rewards':{name:v['reward'] for name,v in fresh.items()}},indent=2))


def main():
 p=argparse.ArgumentParser()
 p.add_argument('--cache',required=True)
 p.add_argument('--out',required=True)
 p.add_argument('--private',required=True)
 p.add_argument('--seed',type=int)
 p.add_argument('--resume',action='store_true')
 a=p.parse_args()
 if a.resume:
  seed=json.loads((Path(a.private)/'replay-seed.json').read_text())['seed']
  if a.seed is not None and a.seed!=seed:p.error('resume seed mismatch')
 else:seed=secrets.randbits(128) if a.seed is None else a.seed
 if not 0<=seed<2**128:p.error('seed must be a 128-bit nonnegative integer')
 run(a.cache,a.out,a.private,seed,a.resume)


if __name__=='__main__':main()
