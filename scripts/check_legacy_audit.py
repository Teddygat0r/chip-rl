"""Default JSON API baseline/fault regressions for the existing twenty families.
This targeted v12 regression supplements, rather than relabels, v11's full matrices.
"""
import argparse,json,sys,subprocess,os
from pathlib import Path
from chip_rl.tasks import Config
from chip_rl.contracts import PILOT
from chip_rl.adversaries import mutant
from chip_rl.cycle.rtl import design as cycle_design
from chip_rl.expansion.spec import Config as ExpansionConfig,NAMES
from chip_rl.expansion.rtl import design as expansion_design
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
rows={};jobs=[]
for n in PILOT:jobs.append((n,'chip_rl.server',mutant(Config(n),'zero')))
for n in ('dma','router','scoreboard','accelerator'):jobs.append((n,'chip_rl.cycle.server',cycle_design(Config(n,depth=16),mutant='zero')))
for n in NAMES:jobs.append((n,'chip_rl.expansion.server',expansion_design(ExpansionConfig(n),mutant='zero')))
jobs.append(('cdc_fifo','chip_rl.cdc.server',None))
for n,module,src in jobs:
 reqs=[{'op':'reset','task':n,'seed':17},{'op':'step','action':{'rtl':src or 'forbidden'}},{'op':'reset','task':n,'artifacts':'/tmp/agent-selected'}]
 cp=subprocess.run([sys.executable,'-m',module,'--cache',a.cache],input=''.join(json.dumps(x)+'\n' for x in reqs),capture_output=True,text=True,timeout=1200)
 (a.output/(n+'.jsonl')).write_text(cp.stdout);(a.output/(n+'-stderr.txt')).write_text(cp.stderr);assert cp.returncode==0,(n,cp.stderr)
 out=[json.loads(x) for x in cp.stdout.splitlines()];assert len(out)==3
 assert out[0]['ok'] and out[0]['observation']['evaluation']['tested_correct'],(n,out[0])
 if src:assert out[1]['ok'] and not out[1]['observation']['evaluation']['tested_correct']
 else:assert not out[1]['ok']
 assert not out[2]['ok'];rows[n]={'baseline':out[0]['observation']['evaluation'],'fault_or_invalid_action_rejected':True,'artifact_override_rejected':True}
 (a.output/'summary.json').write_text(json.dumps({'families':rows,'scope':'default JSON reset, one fault/invalid action and artifact override per existing family; not a full repeat of v11 matrices'},indent=2))
 print(n,'baseline passed; fault/action and artifact override rejected',flush=True)
