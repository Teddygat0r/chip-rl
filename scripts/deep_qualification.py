import argparse,json,secrets
from pathlib import Path
from chip_rl.expansion.spec import Config
from chip_rl.expansion.rtl import design,CATALOG
from chip_rl.qualification.workloads import make
from chip_rl.qualification.harness import check
from chip_rl.suite import compact
from chip_rl.qualification.objectives import assess
p=argparse.ArgumentParser();p.add_argument('--tasks',nargs='+',default=['ecc','coalesce','histogram']);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');p.add_argument('--seed',type=int);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);a.output.chmod(0o700);rows={};fail=[];seed=secrets.randbits(128) if a.seed is None else a.seed
(a.output/'private-seed.json').write_text(json.dumps({'seed':seed}))
for name in a.tasks:
 configs=[Config(name,width=8)] if name=='ecc' else [Config(name),Config(name,width=64,k=1),Config(name,width=64,k=3)] if name=='coalesce' else [Config(name),Config(name,width=8,depth=24,k=3)]
 rows[name]={}
 for ci,c in enumerate(configs):
  epochs=make(c,seed+ci)
  candidates=[(alt,design(c,alt),True) for alt in CATALOG[name]]+ [('bad_'+bad,design(c,mutant=bad),False) for bad in ('semantic','order','no_reset','stall','reset_ready','reset_valid')]+[('bad_reset_priority',design(c).replace('if(rst)','if(rst && !in_valid)'),False)]
  if name=='histogram':candidates += [('bad_late1535',design(c,mutant='counter1023').replace('accepts<1023','accepts<1535'),False)]
  baseline_result=None
  for label,source,want in candidates:
   path=a.output/name/f'{ci}-{label}';r=check(c,source,epochs,path,a.cache);compact(path)
   if label=='baseline':baseline_result=r
   r['integration_objective']=assess(r,baseline_result);rows[name][f'{ci}-{label}']=r
   if r['tested_correct']!=want:fail.append(name+'/'+str(ci)+'/'+label)
   print(name,ci,label,r['tested_correct'],r.get('error','')[:100],flush=True)
   (a.output/'summary.json').write_text(json.dumps({'tasks':rows,'failures':fail},indent=2)+'\n')
if fail:raise SystemExit(1)
