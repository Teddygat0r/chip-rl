import argparse,json,shutil,tarfile,hashlib
from pathlib import Path
from chip_rl.softmax.rtl import design,CATALOG
from chip_rl.softmax.audit_cases import attack,OLD,NEW
from chip_rl.softmax.spec import Config
from chip_rl.softmax.evaluate import Evaluator
p=argparse.ArgumentParser();p.add_argument('split',choices=('development','heldout','reserve','audit'));p.add_argument('--root',type=Path,required=True);p.add_argument('--cache',required=True);p.add_argument('--labels',nargs='+',choices=CATALOG);p.add_argument('--worker-name');a=p.parse_args();root=a.root;out=root/(a.worker_name or a.split+'-worker');out.mkdir(exist_ok=False);rows=[];e=Evaluator(a.cache)
completed=json.loads((root/'results.json').read_text()) if (root/'results.json').exists() else [];done={x['case'] for x in completed}
jobs=[(f'{a.split}-{label}',design(label),True) for label in (a.labels or CATALOG)]
if a.split=='development' and not a.labels:jobs += [(f'bad-{label}',attack(label),False) for label in OLD+NEW]
for name,src,want in jobs:
 if name in done:continue
 if shutil.disk_usage(out).free<300*1024**2:raise SystemExit('disk budget')
 r=e.evaluate(Config(),src,replay_seed=220022,artifacts=out/name,split=a.split);rows.append({'case':name,'expected_correct':want,'result':r});(out/'results.json').write_text(json.dumps(rows,indent=2));print(name,r['tested_correct'],r['reward'],r['elapsed_s'],flush=True)
 assert r['tested_correct']==want,name
 d=out/name;files={str(p.relative_to(d)):hashlib.sha256(p.read_bytes()).hexdigest() for p in d.rglob('*') if p.is_file()};archive=d.with_suffix('.tar.gz')
 with tarfile.open(archive,'w:gz',dereference=True) as t:t.add(d,arcname=d.name)
 seen={}
 with tarfile.open(archive,'r|gz') as t:
  for m in t:
   if m.isfile():seen[str(Path(m.name).relative_to(d.name))]=hashlib.sha256(t.extractfile(m).read()).hexdigest()
 assert seen==files
 d.with_suffix('.manifest.json').write_text(json.dumps({'files':files,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}));shutil.rmtree(d)
