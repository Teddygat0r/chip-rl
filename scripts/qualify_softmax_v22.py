"""Final-source numerical/structural acceptance and adversarial approximation matrix."""
import argparse,json,shutil,tarfile,hashlib
from pathlib import Path
from chip_rl.softmax.spec import Config
from chip_rl.softmax.rtl import design,CATALOG
from chip_rl.softmax.audit_cases import attack,OLD,NEW
from chip_rl.softmax.evaluate import Evaluator
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);p.add_argument('--archive-cases',action='store_true');a=p.parse_args();a.output.mkdir(exist_ok=False);rows=[];e=Evaluator(a.cache)
jobs=[(f'{split}-{label}',design(label),split,True) for split in ('development','heldout','reserve','audit') for label in CATALOG]
jobs += [(f'bad-{label}',attack(label),'development',False) for label in OLD+NEW]
def retain(root):
 files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
 archive=root.with_suffix('.tar.gz')
 with tarfile.open(archive,'w:gz',dereference=True) as t:t.add(root,arcname=root.name)
 seen={}
 with tarfile.open(archive,'r|gz') as t:
  for m in t:
   if m.isfile():seen[str(Path(m.name).relative_to(root.name))]=hashlib.sha256(t.extractfile(m).read()).hexdigest()
 assert seen==files
 root.with_suffix('.manifest.json').write_text(json.dumps({'files':files,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}))
 shutil.rmtree(root)
for name,source,split,want in jobs:
 if shutil.disk_usage(a.output).free<300*1024**2:raise SystemExit('disk budget')
 r=e.evaluate(Config(),source,replay_seed=220022,artifacts=a.output/name,split=split);rows.append({'case':name,'expected_correct':want,'result':r});(a.output/'results.json').write_text(json.dumps(rows,indent=2));print(name,r['tested_correct'],round(r['reward'],5),r.get('max_abs_error'),r['elapsed_s'],flush=True);assert r['tested_correct']==want,name
 if a.archive_cases:retain(a.output/name)
assert len(rows)==46
