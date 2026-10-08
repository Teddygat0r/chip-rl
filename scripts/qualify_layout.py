"""Bounded v19 matrix. Same-author qualification, not independent evaluation."""
import argparse,json,shutil
from pathlib import Path
from chip_rl.layout.spec import Config
from chip_rl.layout.rtl import design,mutant
from chip_rl.layout.evaluate import Evaluator
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(exist_ok=False);rows=[];q=Evaluator(a.cache)
jobs=[(f'{split}-{name}',Config(),design(name),split,True) for split in ('development','heldout','reserve') for name in ('row_major','xor','add')]
jobs += [(f'diagonal-{name}',Config(objective='diagonal'),design(name),'development',True) for name in ('xor','add')]
jobs += [(f'bad-{name}',Config(),mutant(name),'heldout' if name=='unmasked_row' else 'development',False) for name in ('alias','out_of_range','drop_high_col','unmasked_row','padding','latch','port','divergence')]
for i,(name,c,source,split,want) in enumerate(jobs):
 if shutil.disk_usage(a.output).free<300*1024**2:raise SystemExit('disk budget')
 r=q.evaluate(c,source,replay_seed=190190,artifacts=a.output/name,split=split);rows.append({'case':name,'expected_correct':want,'result':r});(a.output/'results.json').write_text(json.dumps(rows,indent=2));print(name,r['tested_correct'],round(r['reward'],5),r['elapsed_s'],flush=True)
 assert r['tested_correct']==want,name
assert len(rows)==19
