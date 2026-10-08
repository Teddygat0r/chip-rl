"""Installed goal selection and immutable agent boundary, using real HDL checks."""
import argparse,json,subprocess,sys,tempfile
from pathlib import Path
import chip_rl
from chip_rl.tasks import Config
from chip_rl.architectures import architecture
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args()
assert 'site-packages' in chip_rl.__file__
src=architecture(Config('dot'),'serial1');rows={}
with tempfile.TemporaryDirectory() as td:
 path=Path(td)/'candidate.sv';path.write_text(src)
 for goal in ('area','balanced','latency'):
  req=[{'op':'reset','task':'dot','seed':17},{'op':'step','action':{'rtl':src}},{'op':'reset','task':'dot','objective':'area'}]
  cp=subprocess.run([sys.executable,'-m','chip_rl.server','--horizon','1','--objective',goal,'--cache',a.cache],input=''.join(json.dumps(x)+'\n' for x in req),text=True,capture_output=True,timeout=300)
  assert cp.returncode==0,cp.stderr
  out=[json.loads(x) for x in cp.stdout.splitlines()];assert not out[2]['ok']
  cli=subprocess.run([sys.executable,'-m','chip_rl','dot','--rtl',str(path),'--objective',goal,'--cache',a.cache],text=True,capture_output=True,timeout=300)
  assert cli.returncode==0,cli.stderr # Functionally valid even when goal-ineligible.
  rows[goal]={'json':out[1]['observation']['evaluation'],'cli':json.loads(cli.stdout)}
  for r in rows[goal].values():
   assert r['tested_correct'] and r['objective']==goal and r['objective_eligible']==(goal=='area')
   assert (r['reward']>0)==(goal=='area')
a.output.write_text(json.dumps(rows,indent=2)+'\n')
print({g:{api:r['reward'] for api,r in results.items()} for g,results in rows.items()})
