import argparse,json,shutil
from pathlib import Path
from chip_rl.quality.spec import Config
from chip_rl.quality.rtl import design
from chip_rl.quality.evaluate import Evaluator
from chip_rl.suite import compact
from stress_candidates import make
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.root.mkdir(exist_ok=False);rows=[]
cases=[]
for task in ('dot','tensor'):
 for label in ('parallel','tree','shift4','shiftadaptive'):cases.append((task,label,True,False))
 for label in ('uniform_narrow','idle_lookahead','drop_after128','late_duplicate','stall_expiry','warmup2','active_state'):cases.append((task,label,label in ('warmup2','active_state'),True))
for label in ('w1','w2','w4','w1r1','w2r2','w4r4'):cases.append(('tlb',label,True,False))
for label in ('asid0_only_invalidate','ignore_root_asid','ignore_context_poison','root_low_nibble_alias'):cases.append(('tlb',label,False,True))
for task,label,valid,attack in cases:
 if shutil.disk_usage(a.root).free<300*1024**2:raise SystemExit('disk budget')
 c=Config(task);src=make(c,label) if attack else design(c,label);p=a.root/(task+'-'+label);r=Evaluator(a.cache).evaluate(c,src,artifacts=p);rows.append({'task':task,'candidate':label,'intended_valid':valid,'result':r});compact(p);(a.root/'results.json').write_text(json.dumps(rows,indent=2));print(task,label,'intended',valid,'reported',r['tested_correct'],'reward',r['reward'],flush=True)
assert all(x['result']['tested_correct']==x['intended_valid'] for x in rows)
