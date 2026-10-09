"""Four fixed, sequential, paired full-five-N public evaluator runs."""
import hashlib,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chip_rl.block_for.rtl import design
from chip_rl.block_for.evaluate import Evaluator
from chip_rl.block_for.spec import Config

private=Path(os.environ['CHIP_RL_FOR_PRIVATE']);out=Path(os.environ['CHIP_RL_FOR_EVIDENCE'])
manifest=json.loads((private/'predeclared.json').read_text())
family=Path(__file__).resolve().parents[1]/'chip_rl/block_for'
h=lambda b:hashlib.sha256(b).hexdigest()
assert {f.name:h(f.read_bytes()) for f in sorted(family.iterdir()) if f.is_file() and f.suffix in ('.py','.md')}==manifest['family_files']
q=Evaluator(private/'cache');rows=[]
for split in ('development','heldout'):
 for arch in ('serial','chunked4'):
  source=design(arch)
  assert h(source.encode())==manifest['generated_candidates'][arch]
  d=private/f'{split}-{arch}';d.mkdir(exist_ok=False)
  result=q.evaluate(Config(4),source,replay_seed=manifest['host_seeds'][split],artifacts=d,split=split)
  row={'split':split,'architecture':arch,'source_sha256':h(source.encode()),'tested_correct':result['tested_correct'],
       'reward_qualified':result['reward_qualified'],'reward':result['reward'],'validation':result['validation'],
       'scored_cases':result['scored_cases'],'constraint_failures':result['constraint_failures'],
       'candidate_simulation_cache_hits':result['candidate_simulation_cache_hits'],
       'baseline_simulation_cache_hits':result['baseline_simulation_cache_hits']}
  rows.append(row)
  out.mkdir(exist_ok=True);(out/'qualification.json').write_text(json.dumps(rows,indent=2)+'\n')
  print(json.dumps({'split':split,'architecture':arch,'correct':row['tested_correct'],'qualified':row['reward_qualified'],'reward':row['reward'],'case_count':len(row['scored_cases']),'failures':row['constraint_failures']}),flush=True)
