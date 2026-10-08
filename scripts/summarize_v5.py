"""Collect completed expansion evidence without publishing private vectors/seeds."""
import argparse,json,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,default=Path('/workspace'));p.add_argument('--output',type=Path,default=Path('evidence/v5'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
paths={'qualification':'chip-rl-v5-final-qualification/summary.json','api':'chip-rl-v5-final-api/summary.json','structural-stress':'chip-rl-v5-final-holdouts/summary.json','formal':'chip-rl-v5-final-formal/summary.json','goal-api':'chip-rl-v5-goal-api.json','old-cycle-regression':'chip-rl-v5-final-cycle-regression/summary.json','source-provenance':'chip-rl-v5-source-provenance.json','fresh-smoke':'chip-rl-v5-fresh-smoke.json'}
paths.update({f'old-api-{n}':f'chip-rl-v5-regression/{n}/summary.json' for n in ('compute','scratchpad','cache','gather')})
reports={}
for name,path in paths.items():
 r=json.loads((a.workspace/path).read_text());assert not r.get('failures'),(name,r.get('failures'));reports[name]=r
 (a.output/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n')
for src,dest in [('chip-rl-v5-unit-final.log','unit-tests.txt'),('chip-rl-v5-fresh-tests.log','fresh-checkout-tests.txt'),('chip-rl-v5-final-wheel.log','wheel-install.txt')]:shutil.copy(a.workspace/src,a.output/dest)
q=reports['qualification']['tasks'];api=reports['api']['tasks'];old={}
for n in ('compute','scratchpad','cache','gather'):old.update(reports['old-api-'+n]['tasks'])
summary={'new_experimental_families':3,'new_valid_designs':sum(r['tested_correct'] for rs in q.values() for r in rs.values()),'new_mutants_rejected':sum(not r['tested_correct'] for rs in q.values() for r in rs.values()),'new_api_valid_checks':sum(r[key]['tested_correct'] for rs in api.values() for r in rs.values() for key in ('json','cli','library')),'new_api_bad_rejected':sum(not r[key]['tested_correct'] for rs in api.values() for r in rs.values() for key in ('json','cli','library')),'schema_override_rejections':9,'new_structural_cases':sum(len(v['cases']) for v in reports['structural-stress']['tasks'].values()),'new_bounded_formal_families':1,'new_unbounded_formal_families':0,'physical_families':0,'trained_policies':0,'pilot_families_unchanged':6,'total_experimental_families':7,'total_runnable_families':13,'unit_tests':54,'old_pilot_api_rejections':sum(not r[api_name]['tested_correct'] for rs in old.values() for k,r in rs.items() if k!='baseline' for api_name in ('json','cli','library')),'old_pilot_baseline_api_passes':sum(rs['baseline'][api_name]['tested_correct'] for rs in old.values() for api_name in ('json','cli','library')),'old_cycle_valid_designs':sum(r['tested_correct'] for rs in reports['old-cycle-regression']['tasks'].values() for r in rs.values()),'old_cycle_bad_rejected':sum(not r['tested_correct'] for rs in reports['old-cycle-regression']['tasks'].values() for r in rs.values()),'os_sandbox':'not_provided','pushed':False}
assert summary['new_valid_designs']==9 and summary['new_mutants_rejected']==30 and summary['new_api_valid_checks']==27 and summary['new_api_bad_rejected']==90
assert summary['new_structural_cases']==6 and summary['old_pilot_api_rejections']==219 and summary['old_pilot_baseline_api_passes']==18
assert summary['old_cycle_valid_designs']==13 and summary['old_cycle_bad_rejected']==28
(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
cost={n:{label:{'wall_s':r['elapsed_s'],'tested_correct':r['tested_correct'],'reward':r['reward'],'pareto_point':r.get('pareto_point')} for label,r in rs.items()} for n,rs in q.items()}
(a.output/'cost-and-tradeoffs.json').write_text(json.dumps(cost,indent=2)+'\n')
print(json.dumps(summary,indent=2))
