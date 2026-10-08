"""Host-only abrupt-death and timeout evidence checks; not HDL qualification."""
import argparse,json,os,signal,subprocess,sys,time
from dataclasses import dataclass
from pathlib import Path
from chip_rl.audit import journal
from chip_rl._tools import run,Rejected
@dataclass(frozen=True)
class Config:
 name:str='journal_process_probe'
class Probe:
 @journal
 def evaluate(self,c,source,*,replay_seed=None,artifacts=None,timeout=60):
  run([sys.executable,'-c','import os,time; print(os.getpid(),flush=True); time.sleep(120)'],artifacts,'probe',timeout)
  raise AssertionError('a stopped probe must never return success')
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--child',action='store_true');a=p.parse_args()
if a.child:
 Probe().evaluate(c=Config(),source='process-probe-source',replay_seed=71,artifacts=a.output)
 raise SystemExit('unexpected success')
a.output.mkdir(parents=True,exist_ok=False);childdir=a.output/'killed';toolpid=None
proc=subprocess.Popen([sys.executable,__file__,'--child','--output',str(childdir)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
 deadline=time.monotonic()+20
 while time.monotonic()<deadline:
  logs=list((childdir/'tool-logs').glob('*.log'))
  if logs and logs[0].read_text().strip():
   toolpid=int(logs[0].read_text().strip());break
  if proc.poll() is not None:raise AssertionError(proc.communicate())
  time.sleep(.025)
 assert toolpid,'probe tool did not start'
 proc.kill();proc.wait(timeout=5)
 os.killpg(toolpid,signal.SIGKILL)
 assert proc.returncode==-signal.SIGKILL
 j=json.loads((childdir/'private-run.json').read_text())
 assert j['status']=='started' and j['seed']==71 and j['config']['name']==Config().name
 assert (childdir/'candidate.sv').read_text()=='process-probe-source'
 assert logs[0].read_text().strip()==str(toolpid)
finally:
 if proc.poll() is None:proc.kill();proc.wait(timeout=5)
 if toolpid:
  try:os.killpg(toolpid,signal.SIGKILL)
  except ProcessLookupError:pass
 proc.communicate()
timeoutdir=a.output/'timeout'
try:Probe().evaluate(c=Config(),source='timeout-probe-source',replay_seed=72,artifacts=timeoutdir,timeout=.2)
except Rejected as e:assert 'timeout' in str(e)
else:raise AssertionError('timeout accepted')
j=json.loads((timeoutdir/'private-run.json').read_text());assert j['status']=='raised' and j['error_type']=='Rejected'
assert (timeoutdir/'candidate.sv').read_text()=='timeout-probe-source' and j['seed']==72
assert any(x.read_text().strip() for x in (timeoutdir/'tool-logs').glob('*.log'))
r={'abrupt_parent_death_retains_started_seed_config_source_and_streamed_log':True,'tool_timeout_rejected_with_retained_evidence':True,'hdl_validation':False}
(a.output/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
