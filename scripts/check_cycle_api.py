"""Installed experimental JSON API: valid designs, late loss and constraint attacks."""
import argparse,json,subprocess,sys
from pathlib import Path
import chip_rl
from chip_rl.tasks import Config
from chip_rl.cycle.rtl import design
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args()
assert 'site-packages' in chip_rl.__file__
a.output.mkdir(parents=True,exist_ok=False);rows={};fail=[]
for n in ('dma','router','scoreboard','accelerator'):
 c=Config(n,depth=16);alt='decoded' if n=='router' else 'pruned'
 reqs=[{'op':'reset','task':n,'seed':17},
       {'op':'step','action':{'rtl':design(c,alternate=alt)}},
       {'op':'step','action':{'rtl':design(c,mutant='late_drop')}},
       {'op':'step','action':{'rtl':design(c),'replay_seed':1}},
       {'op':'reset','task':n,'max_cycles':1}]
 cmd=[sys.executable,'-m','chip_rl.cycle.server','--horizon','3']
 if a.cache:cmd+=['--cache',a.cache]
 proc=subprocess.run(cmd,input=''.join(json.dumps(x)+'\n' for x in reqs),capture_output=True,text=True,timeout=1200)
 assert proc.returncode==0,proc.stderr
 out=[json.loads(x) for x in proc.stdout.splitlines()];assert len(out)==len(reqs)
 assert all(x['ok'] for x in out[:3]) and all(not x['ok'] for x in out[3:])
 results=[x['observation']['evaluation'] for x in out[:3]]
 if [r['tested_correct'] for r in results]!=[True,True,False]:fail.append(n)
 assert all(r['pilot_eligible'] is False for r in results)
 assert 'physical-cycle' in out[0]['observation']['contract_text']
 rows[n]={'evaluations':results,'action_rejected':out[3],'reset_rejected':out[4]}
 print(n,[r['tested_correct'] for r in results],flush=True)
 (a.output/'summary.json').write_text(json.dumps({'tasks':rows,'failures':fail,'installed_module':chip_rl.__file__},indent=2)+'\n')
if fail:raise SystemExit(1)
