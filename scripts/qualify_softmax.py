"""Final-source numerical/structural acceptance and adversarial approximation matrix."""
import argparse,json,shutil
from pathlib import Path
from chip_rl.softmax.spec import Config
from chip_rl.softmax.rtl import design,bad,CATALOG
from chip_rl.softmax.evaluate import Evaluator
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(exist_ok=False);rows=[];e=Evaluator(a.cache)
jobs=[(f'{split}-{label}',design(label),split,True) for split in ('development','heldout','reserve') for label in CATALOG]
jobs += [(f'bad-{label}',bad(label),'development',False) for label in ('uniform','ignore_mask','unsigned','narrow_sum','coarse','stalled_expiry','live_input','wrong_scale','stuck','reverse','absolute','reset_during_division')]
for name,source,split,want in jobs:
 if shutil.disk_usage(a.output).free<300*1024**2:raise SystemExit('disk budget')
 r=e.evaluate(Config(),source,replay_seed=210021,artifacts=a.output/name,split=split);rows.append({'case':name,'expected_correct':want,'result':r});(a.output/'results.json').write_text(json.dumps(rows,indent=2));print(name,r['tested_correct'],round(r['reward'],5),r.get('max_abs_error'),r['elapsed_s'],flush=True);assert r['tested_correct']==want,name
assert len(rows)==24
