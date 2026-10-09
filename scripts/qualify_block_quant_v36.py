"""Frozen-source paired block quantization qualification, with private replay."""
import argparse,hashlib,json,os,secrets,subprocess,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from chip_rl.block_quant.env import BlockQuantEnv
from chip_rl.block_quant.evaluate import Evaluator
from chip_rl.block_quant.rtl import design
from chip_rl.block_quant.spec import Config,HEADER,NS
from chip_rl.block_quant.workloads import generate
from chip_rl.block_quant.oracle import decode

def sha(data):return hashlib.sha256(data).hexdigest()

def frozen():
 record=json.loads((ROOT/'evidence/v36/frozen-source.json').read_text())
 sources={name:design(name) for name in ('serial','parallel')}
 for name,source in sources.items():
  assert {'sha256':sha(source.encode()),'bytes':len(source.encode())}==record['candidate_sources'][name]
 assert sha(HEADER.encode())==record['header_sha256']
 for relative,expected in record['files_at_freeze_sha256'].items():
  assert sha((ROOT/relative).read_bytes())==expected,relative
 return sources

def checked(result,source):
 assert result['source_sha256']==sha(source.encode())
 assert result['tested_correct'] and result['validation']=='exact_integer_rtl_mapped_pass',result
 assert result['reward'] is None and result['reward_qualified'] is False and result['measurement_only'] is True
 assert [case['N'] for case in result['cases']]==list(NS)
 for case in result['cases']:
  assert case['candidate_verified'] and case['baseline_verified']
  for label in ('candidate','baseline'):
   m=case[label]
   assert m['arithmetic_vectors_checked']>60
   assert all(m[k] is True for k in ('arithmetic_rtl_mapped_checked','rtl_mapped_checked',
    'reset_backpressure_checked','long_stall_checked','reset_during_stall_checked',
    'long_stall_output_seen','reset_blocked_output_seen'))
   assert m['accepted_count']==m['consumed_count']==m['transactions']
   assert m['service_opportunity_bound']==2*case['N']+64 and m['stream_transactions']==32

def comparable(r):
 return {k:r[k] for k in ('tested_correct','validation','reward','reward_qualified',
  'measurement_only','candidate','baseline','cases')}

def controls(source):
 magnitude=source.replace('magnitude16=sx[16] ? -sx : sx;',
  "magnitude16=(x==16'h8000) ? 17'd0 : (sx[16] ? -sx : sx);")
 ties=source.replace('(rem==half && q[0])','(rem==half)')
 assert magnitude!=source and ties!=source and magnitude!=ties
 return {'wrong_min_magnitude':magnitude,'ties_away':ties}

def coverage(seed):
 rows={}
 for n in NS:
  work=generate(n,(seed+n)%(1<<128),'heldout')
  groups={}
  for label,word,output in zip(work['labels'],work['inputs'],work['expected']):
   groups.setdefault(label,[]).append((word,output))
  boundaries={max(abs(x) for x in decode(word,n)) for word,_ in groups['exponent_boundary']}
  assert all({(1<<(s+6))-1,1<<(s+6)}<=boundaries for s in range(1,10))
  exponents=sorted({(output>>128)&15 for output in work['expected']})
  assert exponents==list(range(10))
  signs={label:{sign:sum((decode(word,n)[-1]<0)==sign for word,_ in groups[label])
                for sign in (False,True)} for label in ('tie_even','tie_odd')}
  assert all(all(count>=8 for count in signs[label].values()) for label in signs)
  positions={next(i for i,x in enumerate(decode(word,n)) if abs(x)>=32767)
             for word,_ in groups['maximum_lane']}
  assert positions==set(range(n))
  assert groups['ignored_fields_a'][0][1]==groups['ignored_fields_b'][0][1]
  assert all(output>>132==0 and
             ((output>>(8*n))&((1<<(8*(16-n)))-1))==0 for output in work['expected'])
  assert all(word>>256 for word in work['inputs'])
  if n<16:assert any((word>>(16*n))&((1<<(16*(16-n)))-1) for word in work['inputs'])
  rows[str(n)]={'transactions':len(work['inputs']),'labels':dict(Counter(work['labels'])),
   'exponents_observed':exponents,'boundary_magnitudes_covered':sorted(boundaries),
   'ties_by_label_and_negative':{label:{'positive':v[False],'negative':v[True]} for label,v in signs.items()},
   'maximum_lane_positions':sorted(positions),'inactive_outputs_zero':True,'upper_output_bits_zero':True,
   'ignored_fields_pair_equal':True,'workload_sha256':work['sha256'],
   'watchdog_sha256':work['watchdog_sha256']}
 return rows

def cli(seed,cache,sources):
 requests=[{'op':'reset','seed':1},{'op':'step','action':{'rtl':sources['parallel']}},
           {'op':'step','action':{'rtl':sources['serial'],'N':16}}]
 cmd=[sys.executable,'-m','chip_rl.block_quant','--n','4','--horizon','3',
      '--cache',str(cache),'--trusted-replay-seed',str(seed),'--split','heldout']
 proc=subprocess.run(cmd,input=''.join(json.dumps(x)+'\n' for x in requests),text=True,
                     capture_output=True,check=True,timeout=900,cwd=ROOT)
 responses=[json.loads(x) for x in proc.stdout.splitlines()]
 assert len(responses)==3 and responses[0]['ok'] and responses[1]['ok']
 assert not responses[2]['ok'] and 'source-only' in responses[2]['error']
 return {'serial':responses[0]['observation']['evaluation'],
         'parallel':responses[1]['observation']['evaluation']},responses

def invalid_n(seed,cache,private):
 before=len(list(private.glob('eval-*/private-run.json')))
 result={}
 for n in (0,3,17):
  try:Config(n)
  except ValueError:pass
  else:raise AssertionError('invalid N accepted')
  cmd=[sys.executable,'-m','chip_rl.block_quant','--n',str(n),'--cache',str(cache),
       '--trusted-replay-seed',str(seed)]
  proc=subprocess.run(cmd,input='{"op":"reset","seed":1}\n',text=True,
                      capture_output=True,timeout=30,cwd=ROOT)
  response=json.loads(proc.stdout)
  assert not response['ok'] and 'N must be' in response['error']
  result[str(n)]=response['error']
 assert len(list(private.glob('eval-*/private-run.json')))==before
 return result

def run(cache,out,private,seed,resume=False):
 sources=frozen()  # This assertion precedes generated paired inputs.
 cache=Path(cache).resolve();out=Path(out).resolve();private=Path(private).resolve()
 if resume:
  assert private.is_dir() and not out.exists(),'no incomplete private run to resume'
  assert json.loads((private/'replay-seed.json').read_text())['seed']==seed
 else:
  assert not private.exists(),'private run directory already exists'
  private.mkdir(parents=True,mode=0o700)
  (private/'initial-synthesis-cache.json').write_text(json.dumps(sorted(p.name for p in cache.glob('block-quant-*') if p.is_dir()))+'\n')
  (private/'replay-seed.json').write_text(json.dumps({'seed':seed,'split':'heldout'})+'\n')
  (private/'replay-seed.json').chmod(0o600)
 os.environ['CHIP_RL_TRACE_ROOT']=str(private)
 initial=set(json.loads((private/'initial-synthesis-cache.json').read_text()))
 q=Evaluator(cache)
 direct={name:q.evaluate(Config(4),src,replay_seed=seed,split='heldout') for name,src in sources.items()}
 for name,src in sources.items():checked(direct[name],src)
 env=BlockQuantEnv(4,3,cache,trusted_replay_seed=seed,split='heldout')
 obs,_=env.reset();python={'serial':obs['evaluation']}
 try:env.step({'rtl':sources['parallel'],'N':16})
 except ValueError:pass
 else:raise AssertionError('agent N override accepted')
 obs,reward,_,_,info=env.step({'rtl':sources['parallel']})
 assert reward is None and info['measurement_only'] and not info['reward_qualified']
 python['parallel']=obs['evaluation']
 server,responses=cli(seed,cache,sources)
 parity={name:comparable(direct[name])==comparable(python[name])==comparable(server[name]) for name in sources}
 assert all(parity.values()),parity
 (private/'cli-responses.json').write_text(json.dumps(responses))
 mutants={name:q.evaluate(Config(4),src,replay_seed=seed,split='heldout') for name,src in controls(sources['serial']).items()}
 for result in mutants.values():
  assert not result['tested_correct'] and result['reward'] is None and not result['reward_qualified']
 invalid=invalid_n(seed,cache,private)
 journals=list(private.glob('eval-*/private-run.json'))
 sims=list(private.rglob('*-simulation-*.log'))
 new_synth=[p for p in cache.glob('block-quant-*') if p.is_dir() and p.name not in initial]
 assert len(journals)<=24 and len(sims)<=160,(len(journals),len(sims))
 summary={'task':'block_quant','version':'v36-experimental','split':'heldout','Ns':list(NS),
  'frozen_sources':{name:sha(src.encode()) for name,src in sources.items()},
  'tool_fingerprint':q.synth.host.tool_fingerprint,'recipe_sha256':direct['serial']['recipe_sha256'],
  'api_parity':parity,'invalid_N_pre_evaluation':invalid,
  'evaluation_calls':len(journals),'simulator_runs':len(sims),
  'preflight_synthesis_cache_directories':len(initial),'new_synthesis_builds':len(new_synth),
  'validation_counts':{'functional_rtl_mapped':10,'synthesis':10,'formal':0,'physical':0},
  'results':{name:{k:v[k] for k in ('tested_correct','validation','reward','reward_qualified',
   'measurement_only','candidate_simulation_cache_hits','baseline_simulation_cache_hits')}
   for name,v in direct.items()},
  'cases':{name:result['cases'] for name,result in direct.items()},
  'controls':{name:{k:result[k] for k in ('tested_correct','validation','reward','reward_qualified',
   'cases','source_sha256')} for name,result in mutants.items()},
  'coverage':coverage(seed),
  'private_trace_path':str(private)}
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps({'summary':str(out),'evaluation_calls':len(journals),'simulator_runs':len(sims),
  'new_synthesis_builds':len(new_synth),'api_parity':parity},indent=2))

def main():
 p=argparse.ArgumentParser()
 for option in ('cache','out','private'):p.add_argument('--'+option,required=True)
 p.add_argument('--seed',type=int);p.add_argument('--resume',action='store_true')
 a=p.parse_args()
 if a.resume:
  seed=json.loads((Path(a.private)/'replay-seed.json').read_text())['seed']
  if a.seed is not None and a.seed!=seed:p.error('resume seed mismatch')
 else:seed=secrets.randbits(128) if a.seed is None else a.seed
 if not 0<=seed<2**128:p.error('seed must be a 128-bit nonnegative integer')
 run(a.cache,a.out,a.private,seed,a.resume)

if __name__=='__main__':main()
