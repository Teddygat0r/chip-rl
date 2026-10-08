"""Installed JSON boundary smoke and overrides; one baseline and one alias fault."""
import argparse,json,subprocess,sys
from pathlib import Path
from chip_rl.layout.rtl import mutant
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
requests=[{'op':'step','action':{'rtl':'x'}},{'op':'reset','task':'layout','seed':19},{'op':'step','action':{'rtl':mutant('alias')}},{'op':'step','action':{'rtl':'x','banks':32}},{'op':'step','action':{'rtl':'x','objective':'diagonal'}},{'op':'reset','task':'layout','split':'reserve'},{'op':'reset','task':'layout','artifacts':'/tmp/override'},{'op':'step','action':{'rtl':'x','replay_seed':0}}]
requests=[requests[i] for i in (0,1,3,4,5,6,7,2)]+[{'op':'step','action':{'rtl':mutant('alias')}}]
(a.output/'requests.json').write_text(json.dumps(requests));cp=subprocess.run([sys.executable,'-m','chip_rl.layout.server','--cache',a.cache,'--horizon','1'],input=''.join(json.dumps(q)+'\n' for q in requests),capture_output=True,text=True,timeout=120)
(a.output/'output.jsonl').write_text(cp.stdout);(a.output/'stderr.txt').write_text(cp.stderr);assert cp.returncode==0
rows=[json.loads(x) for x in cp.stdout.splitlines()];assert len(rows)==9
assert rows[1]['ok'] and rows[1]['observation']['evaluation']['tested_correct'] and rows[1]['observation']['evaluation']['reward']==1
assert rows[7]['ok'] and not rows[7]['info']['tested_correct'] and rows[7]['truncated'] and rows[7]['reward']==0
assert all(not rows[i]['ok'] for i in (0,2,3,4,5,6,8))
(a.output/'summary.json').write_text(json.dumps({'baseline_passed':1,'mutant_rejected':1,'invalid_requests_rejected':7,'horizon_checked':True},indent=2));print('PASS baseline, alias fault, seven invalid requests, horizon')
