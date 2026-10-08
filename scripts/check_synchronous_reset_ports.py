"""Contract-conformance variants: ready may stay high; valid resets on the edge."""
import argparse,json
from pathlib import Path
from chip_rl.expansion.spec import Config
from chip_rl.expansion.rtl import design
from chip_rl.expansion.evaluate import Evaluator
from chip_rl.qualification.workloads import reset_epochs
from chip_rl.qualification.harness import check
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows={}
for name in ('ecc','coalesce','histogram'):
 c=Config(name);source=design(c).replace('assign in_ready=!rst &&','assign in_ready=').replace('assign out_valid=!rst &&','assign out_valid=')
 assert source!=design(c)
 r=Evaluator(a.cache).evaluate(c,source,replay_seed=918181,artifacts=a.output/name/'default')
 d=check(c,source,reset_epochs(c,881919),a.output/name/'deep',a.cache)
 rows[name]={'default':r,'deep':d};(a.output/'summary.json').write_text(json.dumps(rows,indent=2))
 assert r['tested_correct'] and d['tested_correct'],name
 print(name,'synchronous-only ports accepted',flush=True)
