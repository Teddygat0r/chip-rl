"""Four fixed, fresh, sequential paired five-N serial/shiftpack evaluations."""
import hashlib,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chip_rl.block_for.rtl import design
from chip_rl.block_for.evaluate import Evaluator
from chip_rl.block_for.spec import Config

private=Path(os.environ['CHIP_RL_SHIFTPACK_PRIVATE']);out=Path(os.environ['CHIP_RL_SHIFTPACK_EVIDENCE'])
manifest=json.loads((private/'predeclared.json').read_text())
family=Path(__file__).resolve().parents[1]/'chip_rl/block_for'
h=lambda b:hashlib.sha256(b).hexdigest()
assert {f.name:h(f.read_bytes()) for f in sorted(family.iterdir()) if f.is_file() and f.suffix in ('.py','.md')}==manifest['family_files']
q=Evaluator(private/'cache');rows=[]
for split in ('development','heldout'):
 for arch in ('serial','serial_shiftpack'):
  source=design(arch)
  assert h(source.encode())==manifest['generated_candidates'][arch]
  d=private/f'{split}-{arch}';d.mkdir(exist_ok=False)
  result=q.evaluate(Config(4),source,replay_seed=manifest['host_seeds'][split],artifacts=d,split=split)
  case_rows=[]
  for c,s in zip(result['cases'],result['scored_cases']):
   assert c['N']==s['N']
   case_rows.append({'N':c['N'],'candidate_cells':c['candidate']['cells'],'baseline_cells':c['baseline']['cells'],
    'candidate_logic_depth':c['candidate']['logic_depth'],'baseline_logic_depth':c['baseline']['logic_depth'],
    'candidate_workload_cycles':c['candidate']['workload_cycles'],'baseline_workload_cycles':c['baseline']['workload_cycles'],
    'candidate_ii':c['candidate']['stream_ii_numerator']/c['candidate']['stream_ii_denominator'],
    'baseline_ii':c['baseline']['stream_ii_numerator']/c['baseline']['stream_ii_denominator'],
    'area_ratio':s['area_ratio'],'completion_ratio':s['completion_ratio'],'constraints_passed':s['constraints_passed']})
  row={'split':split,'architecture':arch,'source_sha256':h(source.encode()),'tested_correct':result['tested_correct'],
       'reward_qualified':result['reward_qualified'],'reward':result['reward'],'validation':result['validation'],
       'cases':case_rows,'constraint_failures':result['constraint_failures'],
       'candidate_simulation_cache_hits':result['candidate_simulation_cache_hits'],
       'baseline_simulation_cache_hits':result['baseline_simulation_cache_hits']}
  rows.append(row)
  out.mkdir(exist_ok=True);(out/'qualification.json').write_text(json.dumps(rows,indent=2)+'\n')
  print(json.dumps({'split':split,'architecture':arch,'correct':row['tested_correct'],'qualified':row['reward_qualified'],
   'reward':row['reward'],'case_count':len(row['cases']),'candidate_cache_hits':row['candidate_simulation_cache_hits'],
   'baseline_cache_hits':row['baseline_simulation_cache_hits'],'failures':row['constraint_failures']}),flush=True)
