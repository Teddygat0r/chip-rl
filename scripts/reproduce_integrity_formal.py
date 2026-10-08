import argparse,json
from pathlib import Path
from chip_rl.expansion.spec import Config
from chip_rl.expansion.rtl import design,CATALOG
from chip_rl.expansion.integrity_formal import check_ecc
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows={};c=Config('ecc')
for name,s in [(alt,design(c,alt)) for alt in CATALOG['ecc']]+[('corrupt',design(c,mutant='semantic'))]:
 r=check_ecc(s,a.output/name);compact(a.output/name);rows[name]=r;print(name,r['status'],flush=True)
(a.output/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
assert all(rows[n]['status']=='bounded_pass' for n in ('baseline','decoded'))
assert rows['corrupt']['status']=='unproven' and 'proof did fail' in rows['corrupt'].get('error','')
# Pipeline may exhaust the fixed proof budget; preserve unproven, never count it as verified.
