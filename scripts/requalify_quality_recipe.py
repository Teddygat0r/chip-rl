"""Verify the documented API-guard-only recipe change preserves prior results."""
import argparse,json
from pathlib import Path
from chip_rl.quality.spec import Config
from chip_rl.quality.evaluate import Evaluator
from chip_rl.suite import compact
p=argparse.ArgumentParser();p.add_argument('previous',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows=[]
for entry in json.loads((a.previous/'results.json').read_text()):
 label=entry['architecture'];prior=a.previous/label;j=json.loads((prior/'private-run.json').read_text());before=entry['result']
 after=Evaluator(a.cache).evaluate(Config(**j['config']),(prior/'candidate.sv').read_text(),replay_seed=j['seed'],heldout=True,artifacts=a.output/label)
 def signature(r):return json.dumps({k:v for k,v in r.items() if k not in ('recipe_sha256','elapsed_s')},sort_keys=True,separators=(',',':'))
 assert signature(before)==signature(after),'API guard change altered qualification'
 assert before['recipe_sha256']!=after['recipe_sha256'] and after['tested_correct']
 rows.append({'architecture':label,'result':after,'prior_recipe_sha256':before['recipe_sha256'],'qualification_unchanged_except_recipe_and_elapsed':True});compact(a.output/label);(a.output/'results.json').write_text(json.dumps(rows,indent=2));print(label,'unchanged qualification with strict host API',flush=True)
