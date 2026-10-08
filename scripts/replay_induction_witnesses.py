import argparse,json
from pathlib import Path
from chip_rl.quality.reach_replay import replay
p=argparse.ArgumentParser();p.add_argument('--artifacts',type=Path,required=True,help='Parent containing chip-rl-v17-* evidence directories');p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False);rows=[]
cases=[('chip-rl-v17-reach/0-shiftadaptive-k4',True),('chip-rl-v17-reach/3-fold2-k5',False),('chip-rl-v17-reach/3-fold2-k5',True),('chip-rl-v17-partition/9-reach',False),('chip-rl-v17-partition/9-reach',True),('chip-rl-v17-reach-extra/shiftadaptive-1',False),('chip-rl-v17-reach-extra/shiftadaptive-7',False),('chip-rl-v17-reach-extra/shiftadaptive-7',True),('chip-rl-v17-reach-extra/shift2-5',False)]
for i,(path,varied) in enumerate(cases):
 r=replay(a.artifacts/path,a.output/str(i),varied=varied);rows.append(r);(a.output/'results.json').write_text(json.dumps(rows,indent=2));print(i,path,varied,r['status'],flush=True)
 assert r['status']=='witness_replay_pass'
