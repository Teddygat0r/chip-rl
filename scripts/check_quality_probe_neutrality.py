"""Host-only paired check: the new unscored probe must not change scored work."""
import argparse,json
from pathlib import Path
from chip_rl.quality.spec import Config
from chip_rl.quality.evaluate import Evaluator
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('prior',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args();j=json.loads((a.prior/'private-run.json').read_text());before=json.loads((a.prior/'result.json').read_text())
assert before['tested_correct'] and j['config']['name']=='tlb'
after=Evaluator(a.cache).evaluate(Config(**j['config']),(a.prior/'candidate.sv').read_text(),replay_seed=j['seed'],heldout=before['heldout'],artifacts=a.output)
assert after['tested_correct'] and before['objectives']==after['objectives']
for x,y in zip(before['cases'],after['cases']):
 for who in ('candidate','baseline'):
  assert {k:v for k,v in x[who].items() if k not in ('vectors_sha256','invalidations')}=={k:v for k,v in y[who].items() if k not in ('vectors_sha256','invalidations')}
  assert y[who]['invalidations']==x[who]['invalidations']+4
  assert y[who]['vectors_sha256']!=x[who]['vectors_sha256']
compact(a.output);print(json.dumps({'score_neutral':True,'extra_invalidation_pulses_per_case':4,'scored_metrics_and_objectives_identical':True}))
