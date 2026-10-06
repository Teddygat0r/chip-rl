"""Small finite-catalog feedback experiment; not a trained policy or RL result.
Freeze the best previously qualified source, then check independent private instances.
"""
import argparse,json,secrets,time,resource
from pathlib import Path
from chip_rl.tasks import Config
from chip_rl.architectures import architecture,CATALOG
from chip_rl.evaluate import TrustedEvaluator
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('--qualification',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);p.add_argument('--tasks',nargs='+',default=list(CATALOG));a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False);a.output.chmod(0o700);q=TrustedEvaluator(a.cache);rows={};fail=[]
for name in a.tasks:
    part='compute' if name in ('elastic','dot','tensor') else name
    prior=json.loads((a.qualification/part/'summary.json').read_text())['tasks'][name]
    choices={label:prior[label] for label in CATALOG[name]}
    winner=max(choices,key=lambda label:choices[label]['reward'])
    # Fresh heldout seed never enters the source/agent feedback; retained only by host.
    seed=secrets.randbits(128);c=Config(name);src=architecture(c,winner)
    path=a.output/name/winner
    r=q.evaluate(c,src,replay_seed=seed,count=128,artifacts=path);compact(path)
    rows[name]={'search_kind':'finite catalog enumeration with measured feedback, not trained RL',
      'candidate_count':len(choices),'winner_frozen_before_heldout':winner,
      'development_rewards':{k:v['reward'] for k,v in choices.items()},'heldout':r,
      'comparator':'Enumerating the same finite catalog in random order with the same complete budget yields the same development winner; no search superiority claim.'}
    if not r['tested_correct']:fail.append(name)
    print(name,winner,r['tested_correct'],r['reward'],flush=True)
    (a.output/'summary.json').write_text(json.dumps({'tasks':rows,'failures':fail},indent=2)+'\n')
if fail:raise SystemExit(1)
