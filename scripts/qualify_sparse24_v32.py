"""Run one host-owned sparse24 paired replay through all supported APIs."""
import argparse,json,os,secrets,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chip_rl.sparse24.evaluate import Evaluator
from chip_rl.sparse24.env import Sparse24Env
from chip_rl.sparse24.rtl import design
from chip_rl.sparse24.spec import Config

def controls():
 serial=design('serial')
 pair=serial.replace("3'd1:selected_activation=second ? slot[23:16] : slot[7:0];",
                     "3'd1:selected_activation=second ? slot[31:24] : slot[7:0];")
 reserved=serial.replace('if(slot[50:48]<6)accum<=','if(slot[50:48]<8)accum<=').replace(
  'default:selected_activation=0;','default:selected_activation=slot[7:0];')
 assert pair!=serial and reserved!=serial
 return {'serial':serial,'pipeline':design('pipeline'),'pair_swap':pair,'reserved_nonzero':reserved}

def public(result):
 keys=('tested_correct','validation','reward','reward_qualified','hard_constraints_passed','scored_cases','candidate','baseline','cases')
 return {key:result.get(key) for key in keys}

def run(seed,split,cache,root):
 root=Path(root);root.mkdir(parents=True,exist_ok=False)
 private=root/'private';private.mkdir(mode=0o700)
 os.environ['CHIP_RL_TRACE_ROOT']=str(private)
 (private/'replay-seed.json').write_text(json.dumps({'seed':seed,'split':split})+'\n')
 os.chmod(private/'replay-seed.json',0o600)
 sources=controls();q=Evaluator(cache)
 direct={key:q.evaluate(Config(4),source,replay_seed=seed,split=split) for key,source in sources.items()}
 env=Sparse24Env(4,4,cache,trusted_replay_seed=seed,split=split)
 obs,_=env.reset();python={'serial':obs['evaluation']}
 for key in ('pipeline','pair_swap','reserved_nonzero'):
  obs,reward,_,_,info=env.step({'rtl':sources[key]})
  assert reward==obs['evaluation']['reward'] and info['reward_qualified']==obs['evaluation']['reward_qualified']
  python[key]=obs['evaluation']
 requests=[{'op':'reset','seed':1}]+[{'op':'step','action':{'rtl':sources[key]}}
                                   for key in ('pipeline','pair_swap','reserved_nonzero')]
 cmd=[sys.executable,'-m','chip_rl.sparse24','--g','4','--horizon','4','--cache',str(cache),
      '--trusted-replay-seed',str(seed),'--split',split]
 completed=subprocess.run(cmd,input=''.join(json.dumps(req)+'\n' for req in requests),text=True,
                          capture_output=True,timeout=900,check=True)
 responses=[json.loads(line) for line in completed.stdout.splitlines()]
 assert len(responses)==4 and all(r['ok'] for r in responses),completed.stdout+completed.stderr
 cli={key:responses[i]['observation']['evaluation'] for i,key in enumerate(sources)}
 for i,key in enumerate(('pipeline','pair_swap','reserved_nonzero'),1):
  assert responses[i]['reward']==cli[key]['reward']
 parity={key:public(direct[key])==public(python[key])==public(cli[key]) for key in sources}
 assert all(parity.values()),parity
 assert direct['serial']['tested_correct'] and direct['serial']['reward_qualified'] and direct['serial']['reward']==0
 assert direct['pipeline']['tested_correct'] and direct['pipeline']['reward_qualified'] and direct['pipeline']['reward']>0
 for key in ('pair_swap','reserved_nonzero'):
  assert not direct[key]['tested_correct'] and not direct[key]['reward_qualified'] and direct[key]['reward']==0
 (private/'cli-responses.json').write_text(json.dumps(responses))
 logs=list(private.rglob('*-simulation-*.log'))
 summary={'split':split,'declared_Gs':list(direct['serial']['declared_scored_Gs']),
          'api_parity':parity,'evaluation_calls':12,'simulator_runs':len(logs),
          'results':{key:{'tested_correct':v['tested_correct'],'validation':v['validation'],
                          'reward':v['reward'],'reward_qualified':v['reward_qualified'],
                          'hard_constraints_passed':v['hard_constraints_passed'],
                          'scored_cases':v['scored_cases'],
                          'candidate_simulation_cache_hits':v['candidate_simulation_cache_hits'],
                          'baseline_simulation_cache_hits':v['baseline_simulation_cache_hits']}
                     for key,v in direct.items()},
          'cases':{key:direct[key]['cases'] for key in ('serial','pipeline')},
          'validation_counts':{'functional_rtl_mapped':8,'synthesis':8,'formal':0,'physical':0}}
 (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 return summary

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--seed',type=int)
 p.add_argument('--split',choices=('development','heldout'),default='heldout')
 p.add_argument('--cache',required=True)
 p.add_argument('--out',required=True)
 a=p.parse_args()
 seed=secrets.randbits(128) if a.seed is None else a.seed
 if not 0<=seed<2**128:p.error('seed must be a 128-bit nonnegative integer')
 summary=run(seed,a.split,a.cache,a.out)
 print(json.dumps({'out':a.out,'split':a.split,'api_parity':summary['api_parity'],
                   'evaluation_calls':summary['evaluation_calls'],'simulator_runs':summary['simulator_runs'],
                   'rewards':{k:v['reward'] for k,v in summary['results'].items()}},indent=2))
if __name__=='__main__':main()
