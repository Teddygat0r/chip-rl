"""Bounded symbolic K=1 arithmetic safety and a failing control, not a K=4 proof."""
import argparse,json
from pathlib import Path
from chip_rl.formal_arithmetic import check_dot_k1
from chip_rl.tasks import Config
from chip_rl.architectures import architecture
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
src=architecture(Config('dot'),'product_pipe');rows={}
for name,s in [('pipeline',src),('corrupt',src.replace('result<=total;','result<=total+1;'))]:
 rows[name]=check_dot_k1(s,artifacts=a.output/name);compact(a.output/name)
(a.output/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
assert rows['pipeline']['status']=='bounded_pass' and rows['corrupt']['status']=='unproven'
print(json.dumps(rows,indent=2))
