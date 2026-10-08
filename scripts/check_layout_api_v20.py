"""Final installed JSON boundary: no agent overrides for engine/storage/judge constraints."""
import argparse,json,subprocess,sys
from pathlib import Path
from chip_rl.layout.audit_cases import bad
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
requests=[('before-reset',{'op':'step','action':{'rtl':'x'}},False),('baseline',{'op':'reset','task':'layout','seed':20},True)]
for key,value in [('banks',32),('objective','diagonal'),('replay_seed',0),('engine_source','replacement'),('verification',False),('max_cells',1000000),('max_depth',1000000),('ports',32),('memory_words',1000000),('shape',{'rows':1})]:requests.append(('action-'+key,{'op':'step','action':{'rtl':'x',key:value}},False))
for key,value in [('split','reserve'),('artifacts','/tmp/override'),('max_cells',1000000),('engine_source','replacement')]:requests.append(('reset-'+key,{'op':'reset','task':'layout',key:value},False))
requests += [('alias',{'op':'step','action':{'rtl':bad('alias')}},True),('after-horizon',{'op':'step','action':{'rtl':bad('alias')}},False)]
(a.output/'requests.json').write_text(json.dumps(requests));cp=subprocess.run([sys.executable,'-m','chip_rl.layout.server','--cache',a.cache,'--horizon','1'],input=''.join(json.dumps(q)+'\n' for _,q,_ in requests),capture_output=True,text=True,timeout=120)
(a.output/'output.jsonl').write_text(cp.stdout);(a.output/'stderr.txt').write_text(cp.stderr);assert cp.returncode==0
rows=[json.loads(x) for x in cp.stdout.splitlines()];assert len(rows)==len(requests)
for (label,req,want),r in zip(requests,rows):
 assert r['ok']==want,label
 if label=='baseline':assert r['observation']['evaluation']['tested_correct'] and r['observation']['evaluation']['reward']==1 and r['observation']['evaluation']['verification']
 if label=='alias':assert not r['info']['tested_correct'] and r['reward']==0 and r['truncated']
assert '/workspace/' not in cp.stdout and 'private-run.json' not in cp.stdout
summary={'baseline_passed':1,'alias_fault_rejected':1,'invalid_requests_rejected':sum(not x[2] for x in requests),'horizon_checked':True,'private_paths_not_returned':True};(a.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
