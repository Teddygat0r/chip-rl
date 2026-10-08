"""Exercise the existing experimental cycle reset/step library API."""
import argparse,json
from pathlib import Path
from chip_rl.cycle.env import CycleEnv
from chip_rl.cycle.rtl import design
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows={}
for name in ('dma','router','scoreboard','accelerator'):
 e=CycleEnv(name,horizon=2,cache=a.cache);obs,_=e.reset(17);rs=[obs['evaluation']]
 alt='decoded' if name=='router' else 'pruned'
 for src in (design(e.c,alternate=alt),design(e.c,mutant='late_drop')):
  obs,reward,terminated,truncated,info=e.step({'rtl':src});rs.append(obs['evaluation'])
 assert [r['tested_correct'] for r in rs]==[True,True,False],name
 assert truncated and not terminated and reward==0
 rows[name]=rs;(a.output/'summary.json').write_text(json.dumps({'tasks':rows,'failures':[]},indent=2)+'\n')
 print(name,'library baseline/alternate accepted; late loss rejected',flush=True)
