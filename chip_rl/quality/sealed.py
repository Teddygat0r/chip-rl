"""Trusted-owner batch commit/evaluate/release protocol, NOT an OS sandbox.

Owner retains plan, seeds, sources and diagnostics. Candidate-facing requests contain
only a precommitted identifier and RTL. A witnessed commitment is required externally;
this module cannot establish a different person's independence or stop its host owner.
"""
import fcntl,json,secrets,os
from pathlib import Path
from ..audit import write
from ..evaluate import digest,tool
from .spec import Config
from .evaluate import Evaluator
PROTOCOL='chip-rl-sealed-v1'

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def fingerprint():
 base=Path(__file__).resolve().parent.parent
 return digest(''.join(str(p.relative_to(base))+':'+digest(p.read_text())+'\n' for p in sorted(p for p in base.rglob('*') if p.suffix in ('.py','.md'))))
def tool_fingerprint():
 import hashlib
 return digest(''.join(n+':'+hashlib.sha256(Path(tool(n)).read_bytes()).hexdigest()+'\n' for n in ('yosys','yosys-abc','iverilog','vvp')))
def commitment(value):return digest(canonical(value))
def _hash(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def _new(path,value):
 # Exclusive create means an interrupted attempt is consumed; never silently retried.
 with path.open('x') as f:f.write(canonical(value)+'\n');f.flush();os.fsync(f.fileno())

def create(root,tasks,*,split='stress'):
 if not isinstance(tasks,list) or not 1<=len(tasks)<=8 or any(t not in ('dot','tensor','tlb') for t in tasks):raise ValueError('one to eight supported tasks')
 if split not in (False,True,'stress'):raise ValueError('split')
 root=Path(root);root.mkdir(parents=True,exist_ok=False)
 plan={'protocol':PROTOCOL,'nonce':secrets.token_hex(32),'runtime_sha256':fingerprint(),'toolchain_sha256':tool_fingerprint(),'split':split,'slots':[{'id':str(i),'task':t,'seed':secrets.randbits(128)} for i,t in enumerate(tasks)]}
 receipt={'protocol':PROTOCOL,'plan_commitment':commitment(plan),'slots':[{'id':x['id'],'task':x['task']} for x in plan['slots']],'feedback':'batch only; commit all sources before first evaluation','independence':'not established','os_isolation':'not provided'}
 write(root/'plan.json',plan);write(root/'public-plan.json',receipt);return receipt

def _plan(root,expected):
 p=json.loads((root/'plan.json').read_text())
 if not _hash(expected) or commitment(p)!=expected:raise ValueError('plan commitment mismatch')
 if p['runtime_sha256']!=fingerprint():raise ValueError('runtime commitment mismatch')
 if p['toolchain_sha256']!=tool_fingerprint():raise ValueError('toolchain commitment mismatch')
 return p

def register(root,expected,submissions):
 root=Path(root)
 with (root/'lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);plan=_plan(root,expected)
  if not isinstance(submissions,list) or len(submissions)!=len(plan['slots']):raise ValueError('commit every slot')
  for s,p in zip(submissions,plan['slots']):
   if not isinstance(s,dict) or set(s)!={'id','source_sha256'} or s['id']!=p['id'] or not _hash(s['source_sha256']):raise ValueError('ordered source commitments only')
  record={'protocol':PROTOCOL,'plan_commitment':expected,'submissions':submissions}
  _new(root/'submissions.json',record)
  return {'protocol':PROTOCOL,'plan_commitment':expected,'submission_commitment':commitment(record)}

def _submissions(root,expected):
 s=json.loads((root/'submissions.json').read_text())
 if not _hash(expected) or commitment(s)!=expected:raise ValueError('submission commitment mismatch')
 return s

def submit(root,plan_commitment,submission_commitment,request,*,cache=None):
 root=Path(root)
 with (root/'lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);plan=_plan(root,plan_commitment);registered=_submissions(root,submission_commitment)
  if registered['plan_commitment']!=plan_commitment:raise ValueError('commitment chain mismatch')
  if (root/'released.json').exists():raise ValueError('batch released')
  if not isinstance(request,dict) or set(request)!={'id','rtl'}:raise ValueError('source-only request required')
  slot=next((s for s in plan['slots'] if s['id']==request['id']),None)
  if slot is None:raise ValueError('unknown slot')
  source=request['rtl']
  if not isinstance(source,str) or len(source.encode())>100000:raise ValueError('source size/type')
  expected=next(s['source_sha256'] for s in registered['submissions'] if s['id']==slot['id'])
  if digest(source)!=expected:raise ValueError('source commitment mismatch')
  attempt=root/('attempt-'+slot['id']+'.json');_new(attempt,{'status':'started','source_sha256':expected})
  try:
   result=Evaluator(cache).evaluate(Config(slot['task']),source,replay_seed=slot['seed'],heldout=plan['split'],artifacts=root/('private-'+slot['id']))
   write(attempt,{'status':'completed','source_sha256':expected,'tested_correct':result['tested_correct'],'reward':result['reward'],'objectives':{k:{'eligible':v['eligible'],'reward':v['reward']} for k,v in result.get('objectives',{}).items()},'private_result_sha256':commitment(result)})
  except Exception:
   # Detailed tool/journal information stays on the trusted host. No retry oracle.
   write(attempt,{'status':'unproven','source_sha256':expected})
  return {'protocol':PROTOCOL,'id':slot['id'],'status':'recorded','plan_commitment':plan_commitment,'submission_commitment':submission_commitment}

def release(root,plan_commitment,submission_commitment):
 root=Path(root)
 with (root/'lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);plan=_plan(root,plan_commitment);registered=_submissions(root,submission_commitment)
  if registered['plan_commitment']!=plan_commitment:raise ValueError('commitment chain mismatch')
  rows=[]
  for slot in plan['slots']:
   p=root/('attempt-'+slot['id']+'.json')
   if not p.exists():raise ValueError('batch incomplete')
   r=json.loads(p.read_text());done=r['status']=='completed'
   rows.append({'id':slot['id'],'task':slot['task'],'source_sha256':r['source_sha256'],'status':'completed' if done else 'unproven','tested_correct':r.get('tested_correct',False) if done else False,'reward':r.get('reward',0.) if done else 0.,'objectives':r.get('objectives',{}) if done else {}})
  receipt={'protocol':PROTOCOL,'plan_commitment':plan_commitment,'submission_commitment':submission_commitment,'results':rows,'independence':'not established','physical':'not_run','formal':'not_run'}
  _new(root/'released.json',receipt);return receipt

def serve(root,pc,sc,inp,out,*,cache=None):
 """One batch's precommitted requests. Host selects root/cache/commitments, never agent."""
 while True:
  line=inp.readline(200001)
  if not line:return
  if len(line.encode())>200000:
   out.write(canonical({'ok':False,'error':'request too large; connection closed'})+'\n');out.flush();return
  try:result={'ok':True,'receipt':submit(root,pc,sc,json.loads(line),cache=cache)}
  except (ValueError,TypeError,KeyError,FileExistsError,json.JSONDecodeError):result={'ok':False,'error':'request rejected'}
  out.write(canonical(result)+'\n');out.flush()

def main():
 import argparse,sys
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--plan-commitment',required=True);p.add_argument('--submission-commitment',required=True);p.add_argument('--cache');a=p.parse_args()
 serve(a.root,a.plan_commitment,a.submission_commitment,sys.stdin,sys.stdout,cache=a.cache)
if __name__=='__main__':main()
