"""Freeze development selections, evaluate previously unused parameter values.
Dimensions are public stress splits, not a claim of permanent secrecy.
"""
import argparse,json,secrets
from pathlib import Path
from dataclasses import replace
from chip_rl.tasks import Config
from chip_rl.architectures import architecture,CATALOG
from chip_rl.evaluate import TrustedEvaluator
from chip_rl.objectives import frontier
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('--qualification',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');p.add_argument('--tasks',nargs='+',default=list(CATALOG));a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False);a.output.chmod(0o700);q=TrustedEvaluator(a.cache);prior={};rows={};fail=[]
for path in a.qualification.glob('*/summary.json'):prior.update(json.loads(path.read_text())['tasks'])
frozen={}
for name in a.tasks:
 choices={k:prior[name][k] for k in CATALOG[name]}
 assert all(r['tested_correct'] for r in choices.values())
 winner=max(choices,key=lambda k:choices[k]['reward'])
 frozen[name]={'winner':winner,'source':architecture(Config(name),winner),'development':choices,
               'pareto_frontier':frontier({k:r['pareto_point'] for k,r in choices.items()})}
(a.output/'frozen.json').write_text(json.dumps(frozen,indent=2)+'\n')
for name,item in frozen.items():
 c=Config(name)
 variants=([replace(c,width=w) for w in (12,20)] if name=='elastic' else
           [replace(c,k=k) for k in (1,3)] if name in ('dot','tensor') else
           [replace(c,depth=d) for d in (32,128)])
 rows[name]={'winner':item['winner'],'pareto_frontier':item['pareto_frontier'],'heldouts':[]}
 for cc in variants:
  path=a.output/name/f'w{cc.width}-d{cc.depth}-k{cc.k}'
  r=q.evaluate(cc,item['source'],replay_seed=secrets.randbits(128),artifacts=path);compact(path)
  rows[name]['heldouts'].append(r)
  if not r['tested_correct']:fail.append(str(cc))
  print(name,cc.width,cc.depth,cc.k,r['tested_correct'],r['reward'],flush=True)
  (a.output/'summary.json').write_text(json.dumps({'tasks':rows,'failures':fail,'scope':'frozen public structural stress split; private new workloads; not trained RL'},indent=2)+'\n')
if fail:raise SystemExit(1)
