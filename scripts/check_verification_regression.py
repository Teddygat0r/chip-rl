"""All twenty arithmetic catalog designs plus ten attacks/four valid controls."""
import argparse,json,shutil
from pathlib import Path
from chip_rl.quality.spec import Config
from chip_rl.quality.rtl import CATALOG,design
from chip_rl.quality.evaluate import Evaluator
from chip_rl.suite import compact
from stress_candidates import make
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);p.add_argument('--task',choices=('dot','tensor'),required=True);a=p.parse_args();a.output.mkdir(exist_ok=False);rows=[];c=Config(a.task)
cases=[(label,design(c,label),True) for label in CATALOG[c.name]]+[(label,make(c,label),label in ('warmup2','active_state')) for label in ('uniform_narrow','idle_lookahead','drop_after128','late_duplicate','stall_expiry','warmup2','active_state')]
for label,source,want in cases:
 if shutil.disk_usage(a.output).free<300*1024**2:raise SystemExit('disk budget')
 r=Evaluator(a.cache).evaluate(c,source,artifacts=a.output/label);rows.append({'candidate':label,'expected_valid':want,'result':r});compact(a.output/label);(a.output/'results.json').write_text(json.dumps(rows,indent=2));print(label,want,r['tested_correct'],r['elapsed_s'],flush=True)
 assert r['tested_correct']==want,label
