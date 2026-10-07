"""Freeze development choices, then check prospective public dimensions privately."""
import argparse,json,secrets
from pathlib import Path
from dataclasses import replace
from chip_rl.expansion.spec import Config,NAMES
from chip_rl.expansion.rtl import design,CATALOG
from chip_rl.expansion.evaluate import Evaluator
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('--qualification',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');p.add_argument('--tasks',nargs='+',choices=NAMES,default=NAMES);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);a.output.chmod(0o700)
prior=json.loads(a.qualification.read_text())['tasks'];q=Evaluator(a.cache);frozen={};rows={};fail=[]
for n in a.tasks:
 assert all(prior[n][alt]['tested_correct'] for alt in CATALOG[n])
 winner=max(CATALOG[n],key=lambda alt:prior[n][alt]['reward']);frozen[n]={'winner':winner,'source':design(Config(n),winner)}
(a.output/'frozen.json').write_text(json.dumps(frozen,indent=2)+'\n')
for n,item in frozen.items():
 c=Config(n);variants=([replace(c,width=12,k=3),replace(c,k=3)] if n in ('permute','scan','topk') else [replace(c,width=32,k=3),replace(c,width=32)] if n=='coalesce' else [replace(c,depth=24,width=12,k=3),replace(c,depth=32,k=3)] if n=='histogram' else [replace(c,width=12)] if n=='ecc' else [replace(c,width=24)] if n=='crc' else [replace(c,depth=24,k=3),replace(c,depth=16,k=3)] if n=='freelist' else [replace(c,depth=6,width=12),replace(c,depth=6)])
 rows[n]={'winner':item['winner'],'cases':[]}
 for i,cc in enumerate(variants):
  path=a.output/n/str(i);r=q.evaluate(cc,item['source'],replay_seed=secrets.randbits(128),artifacts=path);compact(path);rows[n]['cases'].append(r)
  if not r['tested_correct']:fail.append(n+'/'+str(i))
  print(n,i,item['winner'],r['tested_correct'],r['reward'],flush=True)
  (a.output/'summary.json').write_text(json.dumps({'tasks':rows,'failures':fail,'scope':'public prospective structural split; new private workloads; no trained policy'},indent=2)+'\n')
if fail:raise SystemExit(1)
