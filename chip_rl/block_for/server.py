"""JSON-lines source-only boundary; N and replay controls belong to the host."""
import argparse,json,sys
from .env import BlockForEnv
from ..evaluate import Rejected

def serve(inp,out,horizon=4,cache=None,n=4,*,trusted_replay_seed=None,split='development'):
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
   if req.get('op')=='reset' and set(req)<={'op','seed'}:
    env=BlockForEnv(n,horizon,cache,trusted_replay_seed=trusted_replay_seed,split=split)
    obs,info=env.reset(req.get('seed',1));result={'ok':True,'observation':obs,'info':info}
   elif req.get('op')=='step' and set(req)=={'op','action'}:
    if env is None:raise ValueError('reset first')
    obs,reward,terminated,truncated,info=env.step(req['action'])
    result={'ok':True,'observation':obs,'reward':reward,'terminated':terminated,'truncated':truncated,'info':info}
   else:raise ValueError('only reset(seed) and step(action) are supported')
  except Rejected:result={'ok':False,'error':'required qualification tools unavailable'}
  except (ValueError,TypeError,KeyError,RuntimeError) as e:result={'ok':False,'error':str(e)}
  out.write(json.dumps(result)+'\n');out.flush()

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--horizon',type=int,default=4);p.add_argument('--cache');p.add_argument('--n',type=int,default=4)
 p.add_argument('--trusted-replay-seed',type=int)
 p.add_argument('--split',choices=('development','heldout'),default='development')
 a=p.parse_args()
 if not 1<=a.horizon<=32:p.error('horizon must be in 1..32')
 try:serve(sys.stdin,sys.stdout,a.horizon,a.cache,a.n,trusted_replay_seed=a.trusted_replay_seed,split=a.split)
 except ValueError as e:p.error(str(e))

if __name__=='__main__':main()
