"""Run installed public entry points with their DEFAULT mandatory qualification.
No count/replay/profile override is passed. All bad classes plus unseen counter limits.
"""
import argparse,json,subprocess,sys,tempfile,time
from pathlib import Path
import chip_rl
from chip_rl.tasks import Config
from chip_rl.contracts import PILOT
from chip_rl.coverage import PROFILE
from chip_rl.evaluate import TrustedEvaluator
from chip_rl.adversaries import labels,mutant,threshold_mutant
from chip_rl.rtl import design
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);p.add_argument('--tasks',nargs='+',default=list(PILOT));a=p.parse_args()
assert 'site-packages' in chip_rl.__file__,'Run with the installed wheel, outside the source tree'
a.output.mkdir(parents=True,exist_ok=False);q=TrustedEvaluator(a.cache);rows={};fail=[]
for n in a.tasks:
 c=Config(n);cases=[('baseline',design(c),True)]+[(label,mutant(c,label),False) for label in labels(n)]
 if n in ('dot','tensor'):cases += [(f'drop_{k}',threshold_mutant(c,k),False) for k in (127,257,777,1023)]
 # A genuine persistent JSON process: baseline reset, then source-only steps.
 requests=[{'op':'reset','task':n,'seed':17}]+[{'op':'step','action':{'rtl':src}} for _,src,_ in cases[1:]]
 start=time.monotonic()
 proc=subprocess.run([sys.executable,'-m','chip_rl.server','--horizon',str(len(cases)),'--cache',a.cache],input=''.join(json.dumps(r)+'\n' for r in requests),capture_output=True,text=True,timeout=2400)
 if proc.returncode:raise RuntimeError(proc.stderr[-1000:])
 replies=[json.loads(line) for line in proc.stdout.splitlines()]
 assert len(replies)==len(cases)
 rows[n]={}
 for (label,src,expected),reply in zip(cases,replies):
  if not reply.get('ok'):raise RuntimeError(reply)
  result=reply['observation']['evaluation'];rows[n][label]={'json':result,'expected':expected}
  if result['tested_correct']!=expected or result['coverage_profile']!=PROFILE:fail.append(n+'/'+label+'/json')
  print(n,label,'json',result['tested_correct'],flush=True)
 # CLI and direct library invoke the same default gate on identical source bytes.
 with tempfile.TemporaryDirectory() as td:
  file=Path(td)/'candidate.sv'
  for label,src,expected in cases:
   file.write_text(src)
   cp=subprocess.run([sys.executable,'-m','chip_rl',n,'--rtl',str(file),'--cache',a.cache],capture_output=True,text=True,timeout=1200)
   result=json.loads(cp.stdout);rows[n][label]['cli']=result
   lib=q.evaluate(c,src);rows[n][label]['library']=lib
   for api,r in [('cli',result),('library',lib)]:
    if r['tested_correct']!=expected or r['coverage_profile']!=PROFILE:fail.append(n+'/'+label+'/'+api)
   if cp.returncode!=(0 if expected else 1):fail.append(n+'/'+label+'/exit-code')
   print(n,label,'cli/library',result['tested_correct'],lib['tested_correct'],flush=True)
  report={'installed_module':chip_rl.__file__,'profile':PROFILE,'tasks':rows,'failures':fail,'last_family_wall_s':time.monotonic()-start}
  (a.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
if fail:raise SystemExit(1)
