"""Resume a disk-guard pause without changing frozen sources, seeds or completed data."""
import argparse,json,shutil
from pathlib import Path
from chip_rl.quality.spec import Config
from chip_rl.quality.rtl import design
from chip_rl.quality.evaluate import Evaluator
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('task');p.add_argument('--root',type=Path,required=True);p.add_argument('--cache',required=True);p.add_argument('--architectures',nargs='+',required=True);a=p.parse_args()
rows=json.loads((a.root/'results.json').read_text());seed=json.loads((a.root/'private-seed.json').read_text())['seed'];done={x['architecture'] for x in rows}
for label in a.architectures:
 if label in done:continue
 if shutil.disk_usage(a.root).free<300*1024**2:raise SystemExit('disk budget')
 path=a.root/label;assert not path.exists();c=Config(a.task);r=Evaluator(a.cache).evaluate(c,design(c,label),replay_seed=seed,heldout='stress',artifacts=path);rows.append({'architecture':label,'result':r});compact(path);(a.root/'results.json').write_text(json.dumps(rows,indent=2));print(label,r['tested_correct'],r.get('objectives'),flush=True)
assert all(x['result']['tested_correct'] for x in rows)
