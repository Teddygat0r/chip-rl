"""Same frozen v14 source/seed/config: verify service scores survive judge hardening."""
import argparse,json
from pathlib import Path
from chip_rl.quality.spec import Config
from chip_rl.quality.evaluate import Evaluator
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('prior',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args();j=json.loads((a.prior/'private-run.json').read_text());before=json.loads((a.prior/'result.json').read_text())
after=Evaluator(a.cache).evaluate(Config(**j['config']),(a.prior/'candidate.sv').read_text(),replay_seed=j['seed'],heldout=before['heldout'],artifacts=a.output)
assert before['tested_correct'] and after['tested_correct'];assert before['objectives']==after['objectives']
keys=('cells','logic_depth','transactions','cycles','latency_sum','maximum_latency','memory_reads')
for x,y in zip(before['cases'],after['cases']):
 for who in ('candidate','baseline'):
  for k in keys:
   if k in x[who]:assert x[who][k]==y[who][k],(who,k)
compact(a.output);print(json.dumps({'scored_metrics_and_objectives_identical':True,'task':j['config']['name'],'new_verification_included_in_reward':False}))
