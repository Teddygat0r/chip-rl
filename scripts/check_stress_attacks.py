import argparse,json
from pathlib import Path
from chip_rl.quality.spec import Config
from chip_rl.quality.evaluate import Evaluator
from chip_rl.suite import compact
from stress_candidates import make
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(exist_ok=False);rows=[]
for n in ('dot','tensor','tlb'):
 labels=('asid0_only_invalidate','ignore_root_asid','ignore_context_poison','root_low_nibble_alias') if n=='tlb' else ('uniform_narrow','idle_lookahead','drop_after128','late_duplicate','stall_expiry','warmup2','active_state')
 for label in labels:
  c=Config(n);want=label in ('warmup2','active_state');dest=a.output/(n+'-'+label);r=Evaluator(a.cache).evaluate(c,make(c,label),artifacts=dest);rows.append({'task':n,'candidate':label,'intended_valid':want,'result':r});compact(dest);(a.output/'results.json').write_text(json.dumps(rows,indent=2));print(n,label,want,r['tested_correct'],flush=True)
assert all(x['intended_valid']==x['result']['tested_correct'] for x in rows)
