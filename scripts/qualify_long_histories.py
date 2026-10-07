import argparse,json,secrets,math
from pathlib import Path
from chip_rl.expansion.spec import Config
from chip_rl.expansion.rtl import design,CATALOG
from chip_rl.history.adversaries import NAMES
from chip_rl.history.evaluate import check
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');p.add_argument('--seed',type=int);p.add_argument('--tasks',nargs='+',default=['crc','retire']);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);a.output.chmod(0o700)
seed=secrets.randbits(128) if a.seed is None else a.seed;(a.output/'private-seed.json').write_text(json.dumps({'seed':seed}));rows={};fail=[]
for n in a.tasks:
 configs=[Config(n),Config(n,width=8),Config(n,width=24)] if n=='crc' else [Config(n),Config(n,width=12,depth=6),Config(n,width=8,depth=4)]
 rows[n]={}
 for ci,c in enumerate(configs):
  baseline=None
  candidates=[(alt,design(c,alt),True) for alt in CATALOG[n]]+[('bad_'+fault,design(c,mutant=fault),False) for fault in NAMES[n]+('semantic','order','no_reset','stall')+(('frame_reset_ports',) if n=='retire' else ())]
  for label,source,want in candidates:
   path=a.output/n/f'{ci}-{label}';r=check(c,source,seed+ci,path,a.cache);compact(path)
   if label=='baseline':baseline=r
   if r['tested_correct'] and baseline['tested_correct']:
    assert r['vectors_sha256']==baseline['vectors_sha256']
    r['measured_relative_to_baseline']={'cells':r['synthesis']['cells']/baseline['synthesis']['cells'],'cycles':r['cycles']/baseline['cycles'],'score_scope':'diagnostic long-history measurements; default reward unchanged'}
   rows[n][f'{ci}-{label}']=r
   if r['tested_correct']!=want:fail.append(n+'/'+str(ci)+'/'+label)
   print(n,ci,label,r['tested_correct'],r.get('error','')[:110],flush=True)
   (a.output/'summary.json').write_text(json.dumps({'tasks':rows,'failures':fail},indent=2)+'\n')
if fail:raise SystemExit(1)
