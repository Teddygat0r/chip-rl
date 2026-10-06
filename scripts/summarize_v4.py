"""Create public evidence from completed trusted-host runs (no private vectors/seeds)."""
import argparse,json,shutil
from pathlib import Path
from chip_rl.objectives import frontier
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,default=Path('/workspace'));p.add_argument('--output',type=Path,default=Path('evidence/v4'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
w=a.workspace
sources={
 'qualification-compute':'chip-rl-v4-qualification-final/compute/summary.json',
 'qualification-memory':'chip-rl-v4-qualification-final/memory/summary.json',
 'api-compute':'chip-rl-v4-api/compute/summary.json','api-memory':'chip-rl-v4-api/memory/summary.json',
 'cycle-qualification':'chip-rl-v4-cycle-release/summary.json','cycle-api':'chip-rl-v4-cycle-api-release/summary.json',
 'heldout-compute':'chip-rl-v4-holdouts/compute/summary.json','heldout-scratchpad':'chip-rl-v4-holdouts/scratchpad/summary.json',
 'heldout-memory':'chip-rl-v4-holdouts/memory/summary.json',
 'formal-elastic':'chip-rl-v4-formal-elastic/summary.json','formal-dot':'chip-rl-v4-formal-dot-reproduced/summary.json',
 'arrival-gate':'chip-rl-v4-arrival-final/result.json'}
sources['objective-api']='chip-rl-v4-objective-api-final.json'
reports={}
for name,src in sources.items():
 r=json.loads((w/src).read_text());assert not r.get('failures'),(name,r.get('failures'))
 reports[name]=r;(a.output/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n')
shutil.copy(w/'chip-rl-v4-unit-final.log',a.output/'unit-tests.txt')
q={**reports['qualification-compute']['tasks'],**reports['qualification-memory']['tasks']}
api={**reports['api-compute']['tasks'],**reports['api-memory']['tasks']}
cy=reports['cycle-qualification']['tasks']
pareto={};cost={}
for n,rs in q.items():
 valid={k:r for k,r in rs.items() if not k.startswith('bad_')}
 assert all(r['tested_correct'] for r in valid.values())
 pareto[n]={'frontier':frontier({k:r['pareto_point'] for k,r in valid.items()}),'designs':{k:{'point':r['pareto_point'],'objectives':r['objectives'],'relation':r['baseline_relation']} for k,r in valid.items()}}
 costs=[r['elapsed_s'] for r in rs.values()]
 cost[n]={'valid_wall_s':{k:r['elapsed_s'] for k,r in valid.items()},'bad_wall_s':{k:r['elapsed_s'] for k,r in rs.items() if k.startswith('bad_')},'qualification_sum_wall_s':sum(costs),'note':'shared synthesis/compiler caches; concurrent jobs; not cold or controlled hardware comparison'}
summary={'pilot_families':len(q),'pilot_valid_designs':sum(not k.startswith('bad_') for rs in q.values() for k in rs),'pilot_bad_rejected':sum(not r['tested_correct'] for rs in q.values() for k,r in rs.items() if k.startswith('bad_')),
 'pilot_api_bad_rejected':sum(not r[api_name]['tested_correct'] for rs in api.values() for k,r in rs.items() if k!='baseline' for api_name in ('json','cli','library')),
 'pilot_api_baselines':sum(r['baseline'][api_name]['tested_correct'] for r in api.values() for api_name in ('json','cli','library')),
 'experimental_cycle_families':len(cy),'cycle_valid_designs':sum(r['tested_correct'] for rs in cy.values() for r in rs.values()),'cycle_bad_rejected':sum(not r['tested_correct'] for rs in cy.values() for r in rs.values()),
 'structural_fresh_cases':sum(len(v['heldouts']) for label in ('heldout-compute','heldout-scratchpad','heldout-memory') for v in reports[label]['tasks'].values()),
 'bounded_formal_families':2,'unbounded_formal_families':0,'physical_families':0,'trained_policies':0,
 'os_sandbox':'not_provided','scope':'six pilot families plus four separate experimental fixed-cycle controllers; no promotion'}
assert summary['pilot_bad_rejected']==65 and summary['pilot_api_bad_rejected']==219 and summary['pilot_api_baselines']==18
assert summary['pilot_valid_designs']==16 and summary['cycle_valid_designs']==13 and summary['cycle_bad_rejected']==28 and summary['structural_fresh_cases']==12
for n,r in [('summary',summary),('pareto',pareto),('cost',cost)]: (a.output/(n+'.json')).write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(summary,indent=2))
