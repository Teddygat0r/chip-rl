import argparse,json
from pathlib import Path
from chip_rl.memory.spec import Config
from chip_rl.memory.evaluate import Evaluator
from chip_rl.evaluate import digest
p=argparse.ArgumentParser();p.add_argument('artifact',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args()
if a.output.exists():raise ValueError('new replay output required')
r=json.loads((a.artifact/'result.json').read_text());src=(a.artifact/'candidate.sv').read_text();seed=json.loads((a.artifact/'private-seed.json').read_text())['seed']
assert digest(src)==r['source_sha256']
n=Evaluator(a.cache).evaluate(Config(**r['config']),src,replay_seed=seed,artifacts=a.output,heldout=r['heldout'])
for key in ('source_sha256','contract_sha256','tool_fingerprint','recipe_sha256','tested_correct','reward','cases'):assert n[key]==r[key],key
print(json.dumps({'replayed':True,'scope':'same private seed, source, contract, recipe, tools, metrics and vector hashes'}))
