import argparse,json
from pathlib import Path
from chip_rl.cdc.spec import Config,Choice,CHOICES
from chip_rl.cdc.rtl import MUTANTS,bad_source
from chip_rl.cdc.evaluate import Evaluator
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows={};fail=[];q=Evaluator(a.cache)
for heldout in (False,True):
 for choice in CHOICES:
  label=f'{choice.architecture}-{choice.sync_stages}-'+('heldout' if heldout else 'default')
  path=a.output/label;r=q.evaluate(Config(),choice,artifacts=path,heldout=heldout);compact(path);rows[label]=r
  if not r['tested_correct']:fail.append(label)
  print(label,r['tested_correct'],r['reward'],flush=True)
  (a.output/'summary.json').write_text(json.dumps({'cases':rows,'failures':fail},indent=2))
for fault in MUTANTS:
 label='bad_'+fault;path=a.output/label;r=q.evaluate(Config(),Choice(),trusted_source=bad_source(Choice(),fault),artifacts=path);compact(path);rows[label]=r
 if r['tested_correct'] or r['reward']!=0:fail.append(label)
 print(label,r['tested_correct'],flush=True)
 (a.output/'summary.json').write_text(json.dumps({'cases':rows,'failures':fail},indent=2))
if fail:raise SystemExit(1)
