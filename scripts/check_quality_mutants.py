import argparse,json,secrets,shutil
from pathlib import Path
from chip_rl.quality.spec import Config
from chip_rl.quality.mutants import CATALOG,bad
from chip_rl.quality.evaluate import Evaluator
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.root.mkdir(parents=True,exist_ok=False);rows=[]
for n,labels in CATALOG.items():
 for label in labels:
  if shutil.disk_usage(a.root).free<300*1024**2:raise SystemExit('disk budget')
  c=Config(n);r=Evaluator(a.cache).evaluate(c,bad(c,label),artifacts=a.root/(n+'-'+label));rows.append({'task':n,'mutant':label,'result':r});compact(a.root/(n+'-'+label));(a.root/'results.json').write_text(json.dumps(rows,indent=2));print(n,label,r['tested_correct'],flush=True)
assert all(not x['result']['tested_correct'] for x in rows),'surviving mutant'
