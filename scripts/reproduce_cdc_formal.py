import argparse,json
from pathlib import Path
from chip_rl.cdc.spec import CHOICES,Choice
from chip_rl.cdc.formal import check
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows={}
for choice in CHOICES:
 key=f'{choice.architecture}-{choice.sync_stages}';rows[key]=check(choice,a.output/key);print(key,rows[key]['status'],flush=True)
 (a.output/'summary.json').write_text(json.dumps(rows,indent=2))
for mutation in ('corrupt','single_sync'):
 rows[mutation]=check(Choice(),a.output/mutation,mutation);print(mutation,rows[mutation]['status'],flush=True)
 (a.output/'summary.json').write_text(json.dumps(rows,indent=2))
# Timeouts remain unproven. A pass is never inferred from absent results.
if any(rows[f'{c.architecture}-{c.sync_stages}']['status']!='bounded_pass' for c in CHOICES):raise SystemExit(1)
assert rows['corrupt']['status']=='unproven' and (a.output/'corrupt'/'counterexample.vcd').exists()
