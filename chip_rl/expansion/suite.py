import argparse,json
from pathlib import Path
from .spec import Config,NAMES
from .rtl import design,CATALOG,MUTANTS,mutants
from .evaluate import Evaluator
from ..suite import compact
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');p.add_argument('--tasks',nargs='+',choices=NAMES,default=NAMES);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);a.output.chmod(0o700);q=Evaluator(a.cache);rows={};fail=[]
for n in a.tasks:
 c=Config(n);rows[n]={}
 cases=[(alt,design(c,alt),True) for alt in CATALOG[n]]+ [('bad_'+m,design(c,mutant=m),False) for m in mutants(n)]
 for label,src,want in cases:
  path=a.output/n/label;r=q.evaluate(c,src,replay_seed=99173,artifacts=path);compact(path);rows[n][label]=r
  if r['tested_correct']!=want:fail.append(n+'/'+label)
  print(n,label,'PASS' if r['tested_correct']==want else 'FAIL',r['reward'],flush=True)
  (a.output/'summary.json').write_text(json.dumps({'tasks':rows,'failures':fail,'status':'experimental_expansion'},indent=2)+'\n')
if fail:raise SystemExit(1)
