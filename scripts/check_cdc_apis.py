import argparse,json,sys,subprocess
from pathlib import Path
from dataclasses import asdict
import chip_rl
from chip_rl.cdc.env import CDCEnv
from chip_rl.cdc.spec import CHOICES
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);a.output.chmod(0o700)
assert 'site-packages' in chip_rl.__file__
requests=[{'op':'reset','task':'cdc_fifo','seed':17}]+[{'op':'step','action':asdict(x)} for x in CHOICES[1:]]
attacks=[{'op':'step','action':{'rtl':'module candidate;endmodule'}},{'op':'step','action':{'architecture':'gray_only','sync_stages':1}},{'op':'step','action':{'architecture':'gray_only','sync_stages':True}},{'op':'step','action':{'architecture':'binary_gray','sync_stages':2,'max_cells':1}},{'op':'reset','task':'cdc_fifo','replay_seed':1},{'op':'reset','task':'cdc_fifo','depth':2},{'op':'reset','task':'cdc_fifo','skip_structural':True},{'op':'reset','task':'crc'}]
requests+=attacks
cp=subprocess.run([sys.executable,'-m','chip_rl.cdc.server','--horizon','8','--cache',a.cache,'--artifacts-root',str(a.output/'server-private')],input=''.join(json.dumps(x)+'\n' for x in requests),capture_output=True,text=True,timeout=1200)
(a.output/'server-output.jsonl').write_text(cp.stdout);(a.output/'server-stderr.txt').write_text(cp.stderr);assert cp.returncode==0
replies=[json.loads(x) for x in cp.stdout.splitlines()];assert len(replies)==len(requests);assert all(not r['ok'] for r in replies[-len(attacks):])
env=CDCEnv(horizon=8,cache=a.cache,trace_root=a.output/'library-private');obs,_=env.reset(17);rows={}
for i,choice in enumerate(CHOICES):
 if i:obs,*_=env.step(asdict(choice))
 cp=subprocess.run([sys.executable,'-m','chip_rl.cdc','--architecture',choice.architecture,'--sync-stages',str(choice.sync_stages),'--cache',a.cache,'--artifacts',str(a.output/f'cli-{i}')],capture_output=True,text=True,timeout=300)
 assert cp.returncode==0,cp.stderr
 cli=json.loads(cp.stdout);js=replies[i]['observation']['evaluation'];lib=obs['evaluation']
 assert replies[i]['ok'] and all(r['tested_correct'] and not r['physical_cdc_safety_verified'] for r in (js,cli,lib))
 rows[f'{choice.architecture}-{choice.sync_stages}']={'json':js,'cli':cli,'library':lib};print(choice,'three APIs passed',flush=True)
 (a.output/'summary.json').write_text(json.dumps({'cases':rows,'schema_rejections':len(attacks),'installed_module':chip_rl.__file__},indent=2))
# Validate bounded parser without invoking HDL.
cp=subprocess.run([sys.executable,'-m','chip_rl.cdc.server'],input='x'*25000+'\n',capture_output=True,text=True,timeout=10)
assert not json.loads(cp.stdout)['ok']
