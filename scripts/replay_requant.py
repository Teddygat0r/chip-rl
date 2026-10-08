import argparse,json
from pathlib import Path
from chip_rl.requant.spec import Config
from chip_rl.requant.evaluate import Evaluator
from chip_rl.evaluate import digest
p=argparse.ArgumentParser();p.add_argument('artifact',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args();before=json.loads((a.artifact/'result.json').read_text());j=json.loads((a.artifact/'private-run.json').read_text());source=(a.artifact/'candidate.sv').read_text();assert digest(source)==before['source_sha256']
r=Evaluator(a.cache).evaluate(Config(**j['config']),source,replay_seed=j['seed'],artifacts=a.output,split=before['split'])
for key in ('tested_correct','reward','cases','recipe_sha256','tool_fingerprint','objective_eligible'):assert r[key]==before[key],key
print(json.dumps({'exact_replay':True,'tested_correct':r['tested_correct'],'reward':r['reward']}))
