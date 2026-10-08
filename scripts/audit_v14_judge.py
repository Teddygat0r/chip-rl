"""Run against the immutable v14 installed wheel from /tmp."""
import argparse,json,secrets
from pathlib import Path
from stress_candidates import make
from chip_rl.quality.spec import Config
from chip_rl.quality.evaluate import Evaluator
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.root.mkdir(parents=True,exist_ok=False);rows=[]
for task,label,valid in [('dot','uniform_narrow',False),('tensor','uniform_narrow',False),('dot','idle_lookahead',False),('dot','drop_after128',False),('dot','late_duplicate',False),('dot','stall_expiry',False),('dot','warmup2',True),('dot','active_state',True),('tlb','asid0_only_invalidate',False),('tlb','ignore_root_asid',False)]:
 c=Config(task);r=Evaluator(a.cache).evaluate(c,make(c,label),artifacts=a.root/(task+'-'+label));rows.append({'task':task,'candidate':label,'intended_valid':valid,'result':r});compact(a.root/(task+'-'+label));(a.root/'results.json').write_text(json.dumps(rows,indent=2));print(task,label,'intended',valid,'reported',r['tested_correct'],'reward',r['reward'],flush=True)
