"""Installed JSON API qualification for the three audited reset contracts."""
import argparse,json,subprocess,sys,os
from pathlib import Path
from reset_controls_v27 import source
p=argparse.ArgumentParser();p.add_argument('family',choices=['elastic','mshr','router']);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
good=source(a.family,'alternate');bad=source(a.family,'retained')
requests=[{'op':'reset','task':a.family,'seed':27}]
invalid=[{'path':'/tmp/untrusted.sv'},{'rtl':good,'seed':0},{'rtl':good,'max_cycles':1}]
requests += [{'op':'step','action':x} for x in invalid]
requests += [{'op':'step','action':{'rtl':s}} for s in (good,bad,good)]
module={'elastic':'chip_rl.server','mshr':'chip_rl.memory.server','router':'chip_rl.cycle.server'}[a.family]
cp=subprocess.run([sys.executable,'-m',module,'--horizon','2','--cache',a.cache],input=''.join(json.dumps(x)+'\n' for x in requests),capture_output=True,text=True,timeout=900)
(a.output/'requests.json').write_text(json.dumps(requests));(a.output/'output.jsonl').write_text(cp.stdout);(a.output/'stderr.txt').write_text(cp.stderr);assert cp.returncode==0
rows=[json.loads(x) for x in cp.stdout.splitlines()];assert len(rows)==7
assert rows[0]['ok'] and rows[0]['observation']['evaluation']['tested_correct']
assert all(not r['ok'] for r in rows[1:4])
assert rows[4]['ok'] and rows[4]['info']['tested_correct'] and not rows[4]['truncated']
assert rows[5]['ok'] and not rows[5]['info']['tested_correct'] and rows[5]['reward']==0 and rows[5]['truncated']
assert not rows[6]['ok'] and '/workspace/' not in cp.stdout
summary={'family':a.family,'baseline_passed':True,'alternate_passed':True,'preserved_retained_mutant_rejected':True,'invalid_actions_rejected':3,'horizon_checked':True,'private_paths_not_returned':True};(a.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
