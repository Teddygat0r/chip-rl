"""Exercise the exact preserved escaped source through the installed agent API."""
import argparse,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
source=(Path(__file__).resolve().parents[1]/'evidence/v25/reset-counterexample.sv').read_text()
requests=[{'op':'reset','task':'requant','seed':26},{'op':'step','action':{'rtl':source}},{'op':'step','action':{'rtl':source}}]
cp=subprocess.run([sys.executable,'-m','chip_rl.requant','--horizon','1','--cache',a.cache],input=''.join(json.dumps(x)+'\n' for x in requests),capture_output=True,text=True,timeout=300)
(a.output/'requests.json').write_text(json.dumps(requests));(a.output/'output.jsonl').write_text(cp.stdout);(a.output/'stderr.txt').write_text(cp.stderr);assert cp.returncode==0
rows=[json.loads(x) for x in cp.stdout.splitlines()];assert len(rows)==3
assert rows[0]['ok'] and rows[0]['observation']['evaluation']['tested_correct']
assert rows[1]['ok'] and not rows[1]['info']['tested_correct'] and rows[1]['reward']==0 and rows[1]['truncated']
assert not rows[2]['ok'];assert '/workspace/' not in cp.stdout
summary={'baseline_passed':True,'exact_v25_exploit_rejected':True,'reward_zero':True,'horizon_checked':True};(a.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
