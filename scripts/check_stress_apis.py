import argparse,json,subprocess,sys
from pathlib import Path
from chip_rl.quality.spec import Config
from chip_rl.quality.rtl import design
from stress_candidates import make
from chip_rl.quality.evaluate import Evaluator
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);p.add_argument('--tasks',nargs='+',choices=('dot','tensor','tlb'),default=('dot','tensor','tlb'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows={}
for n in a.tasks:
 c=Config(n);cases=[('baseline',design(c),True),('alternate',design(c,'w4r4' if n=='tlb' else 'shiftadaptive'),True),('bad',make(c,'asid0_only_invalidate' if n=='tlb' else 'uniform_narrow'),False)]
 reqs=[{'op':'reset','task':n,'seed':7}]+[{'op':'step','action':{'rtl':s}} for _,s,_ in cases[1:]]+[{'op':'reset','task':n,'replay_seed':1},{'op':'reset','task':n,'artifacts':'/tmp/override'},{'op':'step','action':{'rtl':cases[0][1],'objective':'stream'}},{'op':'reset','task':n,'k':1}]
 cp=subprocess.run([sys.executable,'-m','chip_rl.quality.server','--cache',a.cache],input=''.join(json.dumps(r)+'\n' for r in reqs),capture_output=True,text=True,timeout=1200);(a.output/(n+'.jsonl')).write_text(cp.stdout);(a.output/(n+'-stderr.txt')).write_text(cp.stderr);assert cp.returncode==0,cp.stderr
 replies=[json.loads(x) for x in cp.stdout.splitlines()];assert len(replies)==7 and all(not x['ok'] for x in replies[3:]);rows[n]={}
 for (label,src,want),reply in zip(cases,replies):
  assert reply['ok'],reply;path=a.output/(n+'-'+label+'.sv');path.write_text(src)
  cp=subprocess.run([sys.executable,'-m','chip_rl.quality',n,'--rtl',str(path),'--cache',a.cache],capture_output=True,text=True,timeout=1200);assert cp.returncode==(0 if want else 1),(n,label,cp.stderr)
  results={'json':reply['observation']['evaluation'],'cli':json.loads(cp.stdout),'library':Evaluator(a.cache).evaluate(c,src)}
  rows[n][label]=results;(a.output/'summary.json').write_text(json.dumps(rows,indent=2));
  assert all(r['tested_correct']==want for r in results.values()),(n,label)
  print(n,label,'all three API paths passed',flush=True)
