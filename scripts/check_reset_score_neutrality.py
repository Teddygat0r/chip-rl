"""Compare an old retained deep run with the same workload plus reset probes."""
import argparse,json
from pathlib import Path
from chip_rl.expansion.spec import Config
from chip_rl.qualification.workloads import reset_epochs
from chip_rl.qualification.harness import check
from chip_rl.evaluate import digest
p=argparse.ArgumentParser();p.add_argument('artifact',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args()
r=json.loads((a.artifact/'result.json').read_text());source=(a.artifact/'candidate.sv').read_text();assert digest(source)==r['source_sha256']
xs=[int(x,16) for x in (a.artifact/'inputs.hex').read_text().splitlines()];ys=[int(x,16) for x in (a.artifact/'expected.hex').read_text().splitlines()]
epochs=[];offset=0
for row in json.loads((a.artifact/'epochs.json').read_text()):
 n=row.pop('count');epochs.append({**row,'pairs':list(zip(xs[offset:offset+n],ys[offset:offset+n]))});offset+=n
assert offset==len(xs)==len(ys) and digest(json.dumps(epochs,sort_keys=True))==r['epochs_sha256']
c=Config(**r['config']);observed=check(c,source,epochs+reset_epochs(c,991111),a.output,a.cache)
keys=('responses','active_cycles','offered_latency_sum','maximum_offered_latency')
assert r['tested_correct'] and observed['tested_correct']
assert observed['synthesis']['tool_fingerprint']==r['synthesis']['tool_fingerprint']
assert all(observed[k]==r[k] for k in keys)
print(json.dumps({'score_metrics_unchanged':True,'metrics':{k:observed[k] for k in keys},'extra_reset_epochs':160,'source_sha256':r['source_sha256']},indent=2))
