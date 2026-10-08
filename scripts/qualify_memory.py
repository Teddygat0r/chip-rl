import argparse,json
from pathlib import Path
from chip_rl.memory.spec import Config,NAMES
from chip_rl.memory.rtl import CATALOG,design
from chip_rl.memory.mutants import CATALOG as MUTANTS,bad
from chip_rl.memory.evaluate import Evaluator
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');p.add_argument('--tasks',nargs='+',choices=NAMES,default=NAMES);p.add_argument('--heldout',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows={};fail=[];q=Evaluator(a.cache)
for n in a.tasks:
 c=Config(n,entries=6 if a.heldout else 4);rows[n]={}
 cases=[(x,design(c,x),True) for x in CATALOG[n]]+([] if a.heldout else [('bad_'+x,bad(c,x),False) for x in MUTANTS[n]])
 for label,src,want in cases:
  d=a.output/n/label;r=q.evaluate(c,src,artifacts=d,heldout=a.heldout);compact(d);rows[n][label]=r
  if r['tested_correct']!=want:fail.append(n+'/'+label)
  print(n,label,r['tested_correct'],r['reward'],flush=True)
  (a.output/'summary.json').write_text(json.dumps({'tasks':rows,'failures':fail,'heldout':a.heldout},indent=2))
if fail:raise SystemExit(1)
