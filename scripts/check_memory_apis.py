import argparse,json,sys,subprocess
from pathlib import Path
import chip_rl
from chip_rl.memory.spec import Config,NAMES
from chip_rl.memory.rtl import CATALOG,design
from chip_rl.memory.mutants import CATALOG as MUTANTS,bad
from chip_rl.memory.evaluate import Evaluator
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
assert 'site-packages' in chip_rl.__file__
rows={};fail=[];q=Evaluator(a.cache)
for n in NAMES:
 c=Config(n);cases=[(x,design(c,x),True) for x in CATALOG[n]]+[('bad_'+x,bad(c,x),False) for x in MUTANTS[n]]
 requests=[{'op':'reset','task':n,'seed':17}]+[{'op':'step','action':{'rtl':s}} for _,s,_ in cases[1:]]
 requests += [{'op':'reset','task':n,'entries':1},{'op':'reset','task':n,'replay_seed':1},{'op':'step','action':{'rtl':cases[0][1],'max_cycles':1}},{'op':'step','action':{'rtl':cases[0][1],'heldout':False}}]
 cp=subprocess.run([sys.executable,'-m','chip_rl.memory.server','--horizon','32','--cache',a.cache],input=''.join(json.dumps(x)+'\n' for x in requests),text=True,capture_output=True,timeout=2400)
 (a.output/(n+'-server.jsonl')).write_text(cp.stdout);(a.output/(n+'-stderr.txt')).write_text(cp.stderr);assert cp.returncode==0
 replies=[json.loads(x) for x in cp.stdout.splitlines()];assert len(replies)==len(requests) and all(not x['ok'] for x in replies[-4:]);rows[n]={}
 for (label,src,want),reply in zip(cases,replies):
  assert reply['ok'],reply
  path=a.output/(n+'-'+label+'.sv');path.write_text(src)
  cp=subprocess.run([sys.executable,'-m','chip_rl.memory',n,'--rtl',str(path),'--cache',a.cache],text=True,capture_output=True,timeout=600)
  cli=json.loads(cp.stdout);lib=q.evaluate(c,src);js=reply['observation']['evaluation'];rows[n][label]={'json':js,'cli':cli,'library':lib}
  assert cp.returncode==(0 if want else 1)
  for api,r in [('json',js),('cli',cli),('library',lib)]:
   if r['tested_correct']!=want:fail.append(n+'/'+label+'/'+api)
  print(n,label,[r['tested_correct'] for r in (js,cli,lib)],flush=True)
  (a.output/'summary.json').write_text(json.dumps({'tasks':rows,'failures':fail,'schema_rejections_per_family':4,'installed_module':chip_rl.__file__},indent=2))
if fail:raise SystemExit(1)
