import argparse,json
from pathlib import Path
from chip_rl.qualification.formal import check_ecc_capacity_two
from chip_rl.expansion.spec import Config
from chip_rl.expansion.rtl import design
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows={};c=Config('ecc')
for label,source in [(n,design(c,n)) for n in ('baseline','decoded','pipeline')]+[('corrupt',design(c,mutant='semantic'))]:
 rows[label]=check_ecc_capacity_two(source,a.output/label);compact(a.output/label);print(label,rows[label]['status'],flush=True)
(a.output/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
assert all(rows[n]['status']=='bounded_pass' for n in ('baseline','decoded','pipeline'))
assert rows['corrupt']['status']=='unproven' and 'proof did fail' in rows['corrupt'].get('error','')
