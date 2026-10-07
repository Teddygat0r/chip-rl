"""All experimental expansion entry points, real default HDL qualification."""
import argparse,json,subprocess,sys,tempfile
from pathlib import Path
import chip_rl
from chip_rl.expansion.spec import Config,NAMES
from chip_rl.expansion.rtl import design,CATALOG,MUTANTS,mutants
from chip_rl.expansion.evaluate import Evaluator
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);p.add_argument('--tasks',nargs='+',choices=NAMES,default=NAMES);a=p.parse_args()
assert 'site-packages' in chip_rl.__file__
a.output.mkdir(parents=True,exist_ok=False);rows={};fail=[];q=Evaluator(a.cache)
for n in a.tasks:
 c=Config(n);cases=[(alt,design(c,alt),True) for alt in CATALOG[n]]+[('bad_'+m,design(c,mutant=m),False) for m in mutants(n)]
 requests=[{'op':'reset','task':n,'seed':17}]+[{'op':'step','action':{'rtl':src}} for _,src,_ in cases[1:]]
 requests += [{'op':'reset','task':n,'replay_seed':1},{'op':'reset','task':n,'max_cells':1},{'op':'step','action':{'rtl':cases[0][1],'objective':'area'}}]
 cp=subprocess.run([sys.executable,'-m','chip_rl.expansion.server','--horizon','32','--cache',a.cache],input=''.join(json.dumps(x)+'\n' for x in requests),capture_output=True,text=True,timeout=2400)
 assert cp.returncode==0,cp.stderr
 replies=[json.loads(x) for x in cp.stdout.splitlines()];assert len(replies)==len(requests)
 assert all(not r['ok'] for r in replies[-3:]);rows[n]={}
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/'candidate.sv'
  for (label,src,want),reply in zip(cases,replies):
   assert reply['ok'],reply;js=reply['observation']['evaluation'];path.write_text(src)
   cp=subprocess.run([sys.executable,'-m','chip_rl.expansion',n,'--rtl',str(path),'--cache',a.cache],capture_output=True,text=True,timeout=1200)
   cli=json.loads(cp.stdout);lib=q.evaluate(c,src);rows[n][label]={'expected':want,'json':js,'cli':cli,'library':lib}
   assert cp.returncode==(0 if want else 1)
   for api,r in [('json',js),('cli',cli),('library',lib)]:
    if r['tested_correct']!=want:fail.append(n+'/'+label+'/'+api)
    assert r['pilot_eligible'] is False
   print(n,label,[r['tested_correct'] for r in (js,cli,lib)],flush=True)
   (a.output/'summary.json').write_text(json.dumps({'tasks':rows,'failures':fail,'schema_attacks_rejected_per_family':3,'installed_module':chip_rl.__file__},indent=2)+'\n')
if fail:raise SystemExit(1)
