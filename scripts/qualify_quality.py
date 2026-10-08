#!/usr/bin/env python3
"""Trusted host runner. Private seeds never go through agent JSON actions."""
import argparse,json,secrets,shutil
from pathlib import Path
from chip_rl.quality.spec import Config
from chip_rl.quality.rtl import CATALOG,design
from chip_rl.quality.evaluate import Evaluator
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('task',choices=CATALOG);p.add_argument('--root',type=Path,required=True);p.add_argument('--cache',required=True);p.add_argument('--heldout',action='store_true');p.add_argument('--reserve',action='store_true');p.add_argument('--stress',action='store_true');p.add_argument('--architectures',nargs='+');a=p.parse_args()
a.root.mkdir(parents=True,exist_ok=False);seed=secrets.randbits(128);(a.root/'private-seed.json').write_text(json.dumps({'seed':seed}));results=[]
labels=a.architectures or CATALOG[a.task]
if len(labels)!=len(set(labels)) or any(x not in CATALOG[a.task] for x in labels):raise ValueError('unique supported architectures required')
for label in labels:
 if shutil.disk_usage(a.root).free<300*1024**2:raise SystemExit('disk budget')
 c=Config(a.task);src=design(c,label);r=Evaluator(a.cache).evaluate(c,src,replay_seed=seed,heldout='stress' if a.stress else 'reserve' if a.reserve else a.heldout,artifacts=a.root/label);results.append({'architecture':label,'result':r});compact(a.root/label)
 (a.root/'results.json').write_text(json.dumps(results,indent=2));print(label,r['tested_correct'],r.get('objectives'),r['elapsed_s'],flush=True)
if not all(x['result']['tested_correct'] for x in results):raise SystemExit(1)
