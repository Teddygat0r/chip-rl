"""Bounded host-side scheduling; no model subagents or candidate-selected commands."""
import argparse,json,subprocess,time,shutil,sys,hashlib
from pathlib import Path
from chip_rl.softmax.rtl import CATALOG
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);p.add_argument('--aggregate-summary',type=Path);p.add_argument('--max-jobs',type=int,choices=range(1,5),default=4);p.add_argument('--resume',action='store_true');a=p.parse_args();a.output.mkdir(exist_ok=a.resume)
worker=Path(__file__).with_name('softmax_review_worker_v23.py');jobs=[('faults','development',None)]
for label in CATALOG:
 for split in ('development','heldout','reserve','audit','review'):jobs.append((split+'-'+label,split,label))
if a.resume:
 pending=[]
 for job in jobs:
  folder=a.output/(job[0]+'-worker');result=folder/'results.json'
  if not result.exists():
   assert not folder.exists(), 'Preserve incomplete worker outside output before resuming'
   pending.append(job);continue
  previous=json.loads(result.read_text())
  assert len(previous)==(28 if job[0]=='faults' else 1)
  for row in previous:
   assert row['result']['tested_correct']==row['expected_correct'], 'Preserve failed attempt outside output before resuming'
   archive=folder/(row['case']+'.tar.gz');manifest=json.loads((folder/(row['case']+'.manifest.json')).read_text())
   assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
 jobs=pending
live=[];done=[];failed=False
while jobs or live:
 aggregate_done=not a.aggregate_summary
 if a.aggregate_summary:
  try:aggregate_done=len(json.loads(a.aggregate_summary.read_text())['families'])==22
  except (FileNotFoundError,json.JSONDecodeError):pass
 max_jobs=min(a.max_jobs,4 if aggregate_done else 3)
 while jobs and len(live)<max_jobs and not failed:
  if shutil.disk_usage(a.output).free<300*1024**2:failed=True;break
  name,split,label=jobs.pop(0);log=(a.output/(name+'.log')).open('w');cmd=[sys.executable,str(worker),split,'--root',str(a.output),'--cache',a.cache,'--worker-name',name+'-worker']
  cmd+=['--labels',label] if label else ['--faults-only']
  process=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT);live.append((name,process,log))
 for row in live[:]:
  name,process,log=row;rc=process.poll()
  if rc is not None:
   log.close();live.remove(row);done.append({'job':name,'returncode':rc});failed|=rc!=0;print(name,rc,flush=True);(a.output/'jobs.json').write_text(json.dumps(done,indent=2))
 if failed and not live:raise SystemExit('qualification failed; remaining jobs not launched; all started artifacts retained')
 time.sleep(.5)
rows=[]
for p in sorted(a.output.glob('*/results.json')):rows.extend(json.loads(p.read_text()))
assert len(rows)==63 and len({r['case'] for r in rows})==63
(a.output/'results.json').write_text(json.dumps(rows,indent=2));print('63 final cases complete',flush=True)
