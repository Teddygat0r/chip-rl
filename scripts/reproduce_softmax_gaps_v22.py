"""Trusted-host reproduction against a preserved v21 interpreter and final interpreter."""
import argparse,json,subprocess,os
from pathlib import Path
from chip_rl.softmax.audit_cases import attack
p=argparse.ArgumentParser();p.add_argument('--old-python',required=True);p.add_argument('--new-python',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
code="""import sys,json
from pathlib import Path
from chip_rl.softmax.evaluate import Evaluator
from chip_rl.softmax.spec import Config
r=Evaluator(sys.argv[3]).evaluate(Config(),Path(sys.argv[1]).read_text(),replay_seed=220022,artifacts=Path(sys.argv[2]),split='development')
print(json.dumps(r))
"""
rows=[]
for label in ('mask_delta17','single_edge_reset'):
 src=a.output/(label+'.sv');src.write_text(attack(label))
 for stage,interpreter,want in [('before',a.old_python,True),('after',a.new_python,False)]:
  out=a.output/(stage+'-'+label);cp=subprocess.run([interpreter,'-c',code,str(src.resolve()),str(out.resolve()),a.cache],cwd='/tmp',text=True,capture_output=True,timeout=240)
  (a.output/(stage+'-'+label+'.stdout')).write_text(cp.stdout);(a.output/(stage+'-'+label+'.stderr')).write_text(cp.stderr);assert cp.returncode==0
  r=json.loads(cp.stdout);assert r['tested_correct']==want,(stage,label,r);rows.append({'stage':stage,'label':label,'result':r})
(a.output/'summary.json').write_text(json.dumps(rows,indent=2));print('Both v21 false acceptances reproduced and rejected by final judge.')
