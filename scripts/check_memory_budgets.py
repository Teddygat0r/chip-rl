"""Host budget enforcement and keyword-call failure provenance."""
import argparse,json
from pathlib import Path
from chip_rl.memory.spec import Config
from chip_rl.memory.rtl import design
from chip_rl.memory.evaluate import Evaluator
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
q=Evaluator(a.cache);rows={}
for task in ('mshr','tlb'):
 for label,kw in [('cells',{'max_cells':1}),('cycles',{'max_cycles':256})]:
  c=Config(task,**kw);directory=a.output/(task+'-'+label)
  r=q.evaluate(c=c,source=design(c),artifacts=directory)
  assert not r['tested_correct'] and r['reward']==0
  journal=json.loads((directory/'private-run.json').read_text())
  assert journal['config']['name']==task and (directory/'candidate.sv').read_text()==design(c)
  assert list((directory/'tool-logs').glob('*.log'))
  rows[task+'-'+label]=r
(a.output/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
print('Four budget rejections; keyword source/config and tool diagnostics retained.')
