"""Affected source-only evaluator checks; proof results never alter reward."""
import argparse,json,shutil
from pathlib import Path
from chip_rl.quality.spec import Config
from chip_rl.quality.rtl import design
from chip_rl.quality.evaluate import Evaluator
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);p.add_argument('--task',choices=('dot','tensor'),required=True);p.add_argument('--only-extra',action='store_true');a=p.parse_args();a.output.mkdir(exist_ok=False);rows=[];c=Config(a.task)
cases=[(label,design(c,label),True) for label in ('parallel','shiftadaptive','fold2','shift2','fold4')]
src=design(c,'shiftadaptive')
for label,old,new in [('stuck_progress','else pos<=pos+LANES','else pos<=pos'),('narrow','AW=15+$clog2(K+1)','AW=15'),('wrong_operand','a=qa[8*l+:8]','a=qb[8*l+:8]')]:
 assert src.count(old)==1;cases.append((label,src.replace(old,new),False))
if a.only_extra:
 if a.task!='dot':raise ValueError('extra checks use dot')
 cases=[(label,src.replace(old,new),False) for label,old,new in [('skip_last','if(pos+l<K)','if(pos+l<K-1)'),('stall_expire','if(ov && out_ready)ov<=0','if(ov)ov<=0')]]
for label,s,want in cases:
 if shutil.disk_usage(a.output).free<300*1024**2:raise SystemExit('disk budget')
 r=Evaluator(a.cache).evaluate(c,s,artifacts=a.output/label);compact(a.output/label);rows.append({'label':label,'expected_valid':want,'result':r});(a.output/'results.json').write_text(json.dumps(rows,indent=2));print(label,r['tested_correct'],r['elapsed_s'],flush=True)
 assert r['tested_correct']==want,label
