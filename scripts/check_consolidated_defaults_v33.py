"""Normal public baseline and reference smoke for families outside the 22-task aggregate."""
import argparse,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chip_rl.fused.rtl import design as fused_design
from chip_rl.sparse24.rtl import design as sparse_design

def run(module,requests,cache,output,extra_args=()):
 cmd=[sys.executable,'-m',module,'--cache',str(cache),*extra_args]
 cp=subprocess.run(cmd,input=''.join(json.dumps(x)+'\n' for x in requests),text=True,
                   capture_output=True,timeout=1200)
 output.with_suffix('.jsonl').write_text(cp.stdout)
 output.with_suffix('.stderr.txt').write_text(cp.stderr)
 if cp.returncode:raise RuntimeError(f'{module} exited {cp.returncode}; see {output}.stderr.txt')
 rows=[json.loads(x) for x in cp.stdout.splitlines()]
 if len(rows)!=len(requests) or not all(x.get('ok') is True for x in rows):
  raise RuntimeError(f'{module} API response failure; see {output}.jsonl')
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
 p.add_argument('--cache',type=Path,required=True);p.add_argument('--new-cache',type=Path,required=True)
 p.add_argument('--sparse-replay-seed',type=int)
 a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 results={}
 for name in ('layout','softmax','requant'):
  rows=run('chip_rl.'+name,[{'op':'reset','task':name,'seed':33}],a.cache,a.output/name)
  r=rows[0]['observation']['evaluation']
  results[name]={'baseline':{'tested_correct':r['tested_correct'],'reward':r['reward'],
                             'validation':r.get('validation'),'objective_eligible':r.get('objective_eligible')}}
  (a.output/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
  if not r['tested_correct']:raise RuntimeError(f'{name} default baseline failed')
  print(name,'baseline passed',flush=True)
 for name,design in (('fused',fused_design),('sparse24',sparse_design)):
  extra=('--trusted-replay-seed',str(a.sparse_replay_seed),'--split','heldout') if name=='sparse24' and a.sparse_replay_seed is not None else ()
  rows=run('chip_rl.'+name,[{'op':'reset','seed':33},
    {'op':'step','action':{'rtl':design('pipeline')}}],a.new_cache,a.output/name,extra)
  result={}
  for label,row in zip(('baseline','pipeline'),rows):
   r=row['observation']['evaluation']
   result[label]={'tested_correct':r['tested_correct'],'reward':r['reward'],
                  'reward_qualified':r['reward_qualified'],'validation':r['validation'],
                  'candidate_simulation_cache_hits':r.get('candidate_simulation_cache_hits',0),
                  'baseline_simulation_cache_hits':r.get('baseline_simulation_cache_hits',0),
                  'declared_scored_cases':r.get('declared_scored_Gs',r.get('declared_scored_Ks')),
                  'cases':r.get('cases')}
   results[name]=result
   (a.output/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
   if not r['tested_correct'] or not r['reward_qualified'] or (label=='baseline' and r['reward']!=0) or (label=='pipeline' and r['reward']<=0):
    raise RuntimeError(f'{name} {label} public API check failed')
   print(name,label,'passed',flush=True)
 print(json.dumps({'families':list(results),'evaluation_calls':7,'all_passed':True}))
if __name__=='__main__':main()
