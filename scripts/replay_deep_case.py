"""Replay one retained deep-test configuration, not full environment qualification."""
import argparse,json,hashlib
from pathlib import Path
from chip_rl.qualification import harness
from chip_rl.expansion.spec import Config
from chip_rl.evaluate import TrustedEvaluator,digest
p=argparse.ArgumentParser();p.add_argument('artifact',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args()
r=json.loads((a.artifact/'result.json').read_text());source=(a.artifact/'candidate.sv').read_text()
assert digest(source)==r['source_sha256'],'source differs'
assert digest(Path(harness.__file__).read_text())==r['driver_sha256'],'use original deep driver'
q=TrustedEvaluator(a.cache);assert q.tool_fingerprint==r['synthesis']['tool_fingerprint'],'toolchain differs'
xs=[int(x,16) for x in (a.artifact/'inputs.hex').read_text().splitlines()];ys=[int(x,16) for x in (a.artifact/'expected.hex').read_text().splitlines()]
assert len(xs)==len(ys);epochs=[];offset=0
for row in json.loads((a.artifact/'epochs.json').read_text()):
 count=row.pop('count');epochs.append({**row,'pairs':list(zip(xs[offset:offset+count],ys[offset:offset+count]))});offset+=count
assert offset==len(xs) and digest(json.dumps(epochs,sort_keys=True))==r['epochs_sha256'],'vectors differ'
observed=harness.check(Config(**r['config']),source,epochs,a.output,a.cache)
matched=observed['tested_correct']==r['tested_correct']
if r['tested_correct']:
 matched=matched and all(observed[k]==r[k] for k in ('responses','active_cycles','offered_latency_sum','maximum_offered_latency'))
print(json.dumps({'matched_recorded_verdict_and_metrics':matched,'observed_tested_correct':observed['tested_correct'],'scope':'one deep configuration; not full environment qualification'},indent=2))
raise SystemExit(0 if matched else 1)
