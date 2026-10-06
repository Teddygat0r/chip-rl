"""Re-evaluate a retained source against its recorded trusted configuration."""
import argparse,json
from pathlib import Path
from chip_rl.tasks import Config
from chip_rl.evaluate import evaluate
p=argparse.ArgumentParser();p.add_argument('artifact',type=Path);p.add_argument('--output',required=True);a=p.parse_args()
r=json.loads((a.artifact/'result.json').read_text())
count=r.get('workload_count')
if count is None:
    count=len((a.artifact/'inputs.hex').read_text().splitlines())
    if r['config']['name'] in ('accelerator','gather'):count-=r['config']['depth']
x=evaluate(Config(**r['config']),(a.artifact/'candidate.sv').read_text(),seed=r['seed'],split=r['split'],count=count,artifacts=a.output)
print(json.dumps(x,indent=2));raise SystemExit(0 if x['correct']==r['correct'] else 1)
