import argparse,json
from pathlib import Path
from chip_rl.expansion.spec import Config
from chip_rl.expansion.rtl import design
from chip_rl.expansion.formal import check_permute
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows={};c=Config('permute')
for name,s in [('baseline',design(c)),('serial',design(c,'serial')),('shift_serial',design(c,'shift_serial')),('corrupt',design(c,mutant='order'))]:
 r=check_permute(s,a.output/name);compact(a.output/name);rows[name]=r;print(name,r['status'],flush=True)
(a.output/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
assert rows['baseline']['status']==rows['serial']['status']==rows['shift_serial']['status']=='bounded_pass' and rows['corrupt']['status']=='unproven'
