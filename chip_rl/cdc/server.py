import json,sys,argparse
from .env import CDCEnv
from ..evaluate import Rejected

def serve(inp,out,horizon=4,cache=None,trace_root=None):
 env=None
 while True:
  line=inp.readline(20001)
  if not line:return
  if len(line)==20001 and not line.endswith('\n'):
   out.write(json.dumps({'ok':False,'error':'oversized request; connection closed'})+'\n');out.flush();return
  try:
   if len(line.encode())>20000:raise ValueError('request too large')
   request=json.loads(line)
   if not isinstance(request,dict):raise ValueError('object required')
   if request.get('op')=='reset' and set(request)<={'op','task','seed'} and request.get('task')=='cdc_fifo':
    env=CDCEnv(horizon,cache,trace_root);obs,info=env.reset(request.get('seed',1));result={'ok':True,'observation':obs,'info':info}
   elif request.get('op')=='step' and set(request)=={'op','action'}:
    if env is None:raise ValueError('reset first')
    obs,reward,term,trunc,info=env.step(request['action']);result={'ok':True,'observation':obs,'reward':reward,'terminated':term,'truncated':trunc,'info':info}
   else:raise ValueError('only reset(task,seed) and step(action) supported')
  except (ValueError,TypeError,KeyError,RuntimeError,Rejected) as e:result={'ok':False,'error':str(e)}
  out.write(json.dumps(result)+'\n');out.flush()
def main():
 p=argparse.ArgumentParser();p.add_argument('--horizon',type=int,default=4);p.add_argument('--cache');p.add_argument('--artifacts-root');a=p.parse_args()
 if not 1<=a.horizon<=32:p.error('horizon')
 serve(sys.stdin,sys.stdout,a.horizon,a.cache,a.artifacts_root)
if __name__=='__main__':main()
