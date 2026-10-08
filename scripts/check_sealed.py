"""Local mechanism test; the same author sees both sides, so no independence claim."""
import argparse,json,io,subprocess,sys
from pathlib import Path
from chip_rl.quality import sealed
from chip_rl.quality.spec import Config
from chip_rl.quality.rtl import design
from chip_rl.evaluate import digest
from stress_candidates import make
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);p.add_argument('--dot-only',action='store_true');a=p.parse_args();a.output.mkdir(exist_ok=False)
cases=[('dot','valid'),('dot','bad')]+([] if a.dot_only else [('tensor','valid'),('tensor','bad')])
sources=[design(Config(t),'shiftadaptive') if label=='valid' else make(Config(t),'uniform_narrow') for t,label in cases]
root=a.output/'owner';plan=sealed.create(root,[t for t,_ in cases]);pc=plan['plan_commitment']
registered=sealed.register(root,pc,[{'id':str(i),'source_sha256':digest(s)} for i,s in enumerate(sources)]);sc=registered['submission_commitment']
(a.output/'public-plan.json').write_text(json.dumps(plan,indent=2));(a.output/'source-commitment.json').write_text(json.dumps(registered,indent=2))
def call(request):
 cp=subprocess.run([sys.executable,'-m','chip_rl.quality.sealed','--root',str(root),'--plan-commitment',pc,'--submission-commitment',sc,'--cache',a.cache],input=json.dumps(request)+'\n',capture_output=True,text=True,timeout=600)
 assert cp.returncode==0,cp.stderr
 return json.loads(cp.stdout)
rejects=[]
for request in [{'id':'0','rtl':sources[0]+'\n'},{'id':'0','rtl':sources[0],'seed':1},{'id':'0','rtl':sources[0],'split':False},{'id':'0','rtl':sources[0],'artifacts':'/tmp/not-owner'}]:
 response=call(request);assert response=={'ok':False,'error':'request rejected'};rejects.append(response)
try:sealed.release(root,pc,sc);raise AssertionError('premature release')
except ValueError:pass
for i,src in enumerate(sources):
 ack=call({'id':str(i),'rtl':src});assert ack['ok'] and ack['receipt']['status']=='recorded';assert 'tested_correct' not in ack['receipt'];(a.output/f'ack-{i}.json').write_text(json.dumps(ack));print('slot',i,'recorded without correctness feedback',flush=True)
assert not call({'id':'0','rtl':sources[0]})['ok']
receipt=sealed.release(root,pc,sc)
assert [r['tested_correct'] for r in receipt['results']]==[label=='valid' for _,label in cases]
assert all(r['reward']==0 for r in receipt['results'] if not r['tested_correct'])
(a.output/'receipt.json').write_text(json.dumps(receipt,indent=2));(a.output/'summary.json').write_text(json.dumps({'actual_evaluations':len(cases),'valid_accepted':len(cases)//2,'bad_rejected':len(cases)//2,'overrides_rejected':4,'replay_rejected':True,'premature_release_rejected':True,'independence_established':False},indent=2))
print('sealed mechanism passed; no independent evaluation claimed',flush=True)
