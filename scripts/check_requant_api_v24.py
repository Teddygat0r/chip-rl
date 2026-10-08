"""Installed source-only API and scripted three-step episode; not trained RL."""
import argparse,json,subprocess,sys
from pathlib import Path
from chip_rl.requant.rtl import design,bad
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
requests=[('before-reset',{'op':'step','action':{'rtl':'x'}},False),('baseline',{'op':'reset','task':'requant','seed':24},True)]
for key in ('N','shift','rounding','max_cells','oracle','replay_seed','artifacts','verification'):
 requests.append(('override-'+key,{'op':'step','action':{'rtl':design(),key:0}},False))
for key in ('artifacts','split','seed_override','max_cells'):
 requests.append(('reset-'+key,{'op':'reset','task':'requant',key:0},False))
for name in ('serial','pipelined'):requests.append((name,{'op':'step','action':{'rtl':design(name)}},True))
requests += [('bad',{'op':'step','action':{'rtl':bad('early_saturate')}},True),('after-horizon',{'op':'step','action':{'rtl':design()}},False)]
(a.output/'requests.json').write_text(json.dumps(requests));cp=subprocess.run([sys.executable,'-m','chip_rl.requant','--horizon','3','--cache',a.cache],input=''.join(json.dumps(req)+'\n' for _,req,_ in requests),text=True,capture_output=True,timeout=600)
(a.output/'output.jsonl').write_text(cp.stdout);(a.output/'stderr.txt').write_text(cp.stderr);assert cp.returncode==0
rows=[json.loads(x) for x in cp.stdout.splitlines()];assert len(rows)==len(requests)
for (name,req,want),r in zip(requests,rows):
 assert r['ok']==want,name
 if name in ('baseline','serial','pipelined'):assert r['observation']['evaluation']['tested_correct'] and r['observation']['evaluation']['objective_eligible']
 if name=='bad':assert r['reward']==0 and not r['info']['tested_correct'] and r['truncated']
assert '/workspace/' not in cp.stdout and 'private-run.json' not in cp.stdout
summary={'correct_designs':3,'bad_rejected':1,'invalid_requests_rejected':sum(not x[2] for x in requests),'horizon_checked':True,'private_paths_not_returned':True};(a.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
