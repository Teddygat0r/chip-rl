"""Reproduce the explicitly bounded elastic evidence and failing controls."""
import argparse,json
from pathlib import Path
from chip_rl.formal import check_elastic,check_cycle_equivalence
from chip_rl.tasks import Config
from chip_rl.rtl import design
from chip_rl.architectures import architecture
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
c=Config('elastic',width=8);rows={}
for label,src in [('baseline',design(c)),('global4',architecture(c,'global4')),('corrupt',design(c,mutant='corrupt'))]:
 rows[label]=check_elastic(src,width=8,artifacts=a.output/label);compact(a.output/label)
for label,src in [('same',design(c)),('changed_latency',design(c,2))]:
 rows[label]=check_cycle_equivalence(design(c),src,artifacts=a.output/label);compact(a.output/label)
(a.output/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
assert rows['baseline']['status']==rows['global4']['status']==rows['same']['status']=='bounded_pass'
assert rows['corrupt']['status']==rows['changed_latency']['status']=='unproven'
print(json.dumps(rows,indent=2))
