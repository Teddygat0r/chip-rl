import argparse,json
from pathlib import Path
from chip_rl.cdc.spec import Config,Choice
from chip_rl.cdc.evaluate import Evaluator
p=argparse.ArgumentParser();p.add_argument('artifact',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args()
if a.output.exists():raise ValueError('replay output must be new')
r=json.loads((a.artifact/'result.json').read_text());source=(a.artifact/'candidate.sv').read_text()
from chip_rl.evaluate import digest
assert digest(source)==r['source_sha256'], 'retained source hash mismatch'
seed=json.loads((a.artifact/'private-seed.json').read_text())['seed']
new=Evaluator(a.cache).evaluate(Config(**r['config']),Choice(**r['choice']),replay_seed=seed,artifacts=a.output,heldout=r['heldout'],trusted_source=source)
assert new['source_sha256']==r['source_sha256'] and new['recipe_sha256']==r['recipe_sha256'] and new['tool_fingerprint']==r['tool_fingerprint']
assert new['tested_correct']==r['tested_correct'] and new['reward']==r['reward'] and new['cases']==r['cases']
print(json.dumps({'replayed':True,'scope':'full CDC qualification replay; same source/recipe/tools/vectors/metrics'}))
