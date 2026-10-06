"""Local JSON-lines action boundary: python -m chip_rl.server.
This constrains the action interface, not OS access by the compiler processes.
Only trusted-host CLI flags set episode limits. No candidate file paths or commands.
"""
import argparse,json,sys
from .env import ChipEnv
from .evaluate import Rejected,TrustedEvaluator

def serve(inp,out,horizon=8,cache_root=None,objective="balanced"):
    env=None;evaluator=None
    while True:
        line=inp.readline(200001)
        if not line: break
        if len(line)==200001 and not line.endswith('\n'):
            out.write(json.dumps({'ok':False,'error':'request too large; connection closed'})+'\n');out.flush();return
        try:
            if len(line.encode())>200000:raise ValueError('request too large')
            req=json.loads(line)
            if not isinstance(req,dict):raise ValueError('request must be an object')
            if req.get('op')=='reset' and set(req)<={'op','task','seed'}:
                if evaluator is None:evaluator=TrustedEvaluator(cache_root)
                env=ChipEnv(req['task'],horizon=horizon,evaluator=evaluator,objective=objective)
                obs,info=env.reset(seed=req.get('seed',1))
                response={'ok':True,'observation':obs,'info':info}
            elif req.get('op')=='step' and set(req)=={'op','action'}:
                if env is None:raise ValueError('reset first')
                obs,reward,terminated,truncated,info=env.step(req['action'])
                response={'ok':True,'observation':obs,'reward':reward,'terminated':terminated,'truncated':truncated,'info':info}
            else:raise ValueError('only reset(task,seed) and step(action) are supported')
        except Rejected:
            response={'ok':False,'error':'required qualification tools unavailable'}
        except (ValueError,TypeError,KeyError,RuntimeError) as e:
            response={'ok':False,'error':str(e)}
        out.write(json.dumps(response)+'\n');out.flush()

def main():
    p=argparse.ArgumentParser();p.add_argument('--horizon',type=int,default=8);p.add_argument('--cache');p.add_argument('--objective',choices=['area','balanced','latency'],default='balanced');a=p.parse_args()
    if not 1<=a.horizon<=1024:p.error('horizon must be in 1..1024')
    serve(sys.stdin,sys.stdout,a.horizon,a.cache,a.objective)
if __name__=='__main__':main()
