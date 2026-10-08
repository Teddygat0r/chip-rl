"""Experimental source-only JSON-lines boundary; no OS sandbox is implied."""
import argparse,json,sys
from .env import ExpansionEnv
from ..evaluate import Rejected

def serve(inp,out,horizon=4,cache=None,objective="balanced"):
 env=None
 while True:
  line=inp.readline(200001)
  if not line:return
  if len(line)==200001 and not line.endswith('\n'):
   out.write(json.dumps({'ok':False,'error':'request too large; connection closed'})+'\n');out.flush();return
  try:
   if len(line.encode())>200000:raise ValueError('request too large')
   req=json.loads(line)
   if not isinstance(req,dict):raise ValueError('request must be an object')
   if req.get('op')=='reset' and set(req)<={'op','task','seed'}:
    env=ExpansionEnv(req['task'],horizon,cache,objective=objective);obs,info=env.reset(req.get('seed',1))
    result={'ok':True,'observation':obs,'info':info}
   elif req.get('op')=='step' and set(req)=={'op','action'}:
    if env is None:raise ValueError('reset first')
    obs,reward,terminated,truncated,info=env.step(req['action'])
    result={'ok':True,'observation':obs,'reward':reward,'terminated':terminated,'truncated':truncated,'info':info}
   else:raise ValueError('only reset(task,seed) and step(action) are supported')
  except Rejected:result={'ok':False,'error':'required qualification tools unavailable'}
  except (ValueError,TypeError,KeyError,RuntimeError) as e:result={'ok':False,'error':str(e)}
  out.write(json.dumps(result)+'\n');out.flush()

def main():
 p=argparse.ArgumentParser();p.add_argument('--horizon',type=int,default=4);p.add_argument('--cache');p.add_argument('--objective',choices=['area','balanced','latency'],default='balanced');a=p.parse_args()
 if not 1<=a.horizon<=32:p.error('horizon must be in 1..32')
 serve(sys.stdin,sys.stdout,a.horizon,a.cache,a.objective)
if __name__=='__main__':main()
