import argparse,json
from pathlib import Path
from chip_rl.expansion.spec import Config
from chip_rl.history import evaluate
from chip_rl.evaluate import digest
p=argparse.ArgumentParser();p.add_argument('artifact',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args()
r=json.loads((a.artifact/'result.json').read_text());case=json.loads((a.artifact/'private-case.json').read_text());source=(a.artifact/'candidate.sv').read_text()
assert digest(source)==r['source_sha256']
assert digest(''.join(p.read_text() for p in sorted(Path(evaluate.__file__).parent.glob('*.py'))))==r['recipe_sha256']
assert digest(''.join(p.read_text() for p in sorted(a.artifact.glob('*.hex'))))==r['vectors_sha256']
new=evaluate.check(Config(**case['config']),source,case['seed'],a.output,a.cache)
assert new['synthesis']['tool_fingerprint']==r['synthesis']['tool_fingerprint']
assert new['vectors_sha256']==r['vectors_sha256'] and new['tested_correct']==r['tested_correct']
if r['tested_correct']:assert all(new[k]==r[k] for k in ('completed','cycles','latency_sum','maximum_response_cycles'))
print(json.dumps({'replayed':True,'tested_correct':new['tested_correct'],'scope':'one long verification configuration; not full qualification'},indent=2))
