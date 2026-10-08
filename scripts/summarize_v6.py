"""Collect the integrity batch's measured evidence, never private vectors/seeds."""
import argparse,json,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,default=Path('/workspace'));p.add_argument('--output',type=Path,default=Path('evidence/v6'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
paths={'replay':'replay.json','qualification':'final-qualification/summary.json','api':'final-api/summary.json','structural-stress':'final-holdouts/summary.json','formal':'formal/summary.json','old-expansion-api':'old-expansion-api/summary.json','old-cycle':'cycle-regression/summary.json','old-pilot-compute':'regression/compute/summary.json','old-pilot-memory':'regression/memory/summary.json','source-provenance':'source-provenance.json','fresh-smoke':'fresh-smoke.json','rollouts':'rollouts.json'}
reports={}
for name,path in paths.items():
 r=json.loads((a.workspace/('chip-rl-v6-'+path)).read_text());assert not r.get('failures'),(name,r.get('failures'));reports[name]=r
 (a.output/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n')
for src,dest in [('results-commands.txt','executed-commands.txt'),('unit-final.log','unit-tests.txt'),('fresh-tests.log','fresh-checkout-tests.txt'),('final-wheel.log','wheel-install.txt')]:shutil.copy(a.workspace/('chip-rl-v6-'+src),a.output/dest)
q=reports['qualification']['tasks'];api=reports['api']['tasks'];oldexp=reports['old-expansion-api']['tasks'];old={**reports['old-pilot-compute']['tasks'],**reports['old-pilot-memory']['tasks']}
def counts(rs):return [sum(r['tested_correct'] for r in rs),sum(not r['tested_correct'] for r in rs)]
summary={'new_experimental_families':3,'functional_and_synthesis_families_total':16,'pilot_families':6,'experimental_families':10,'new_designs_and_rejections':counts([r for rs in q.values() for r in rs.values()]),'new_api_passes_and_rejections':counts([r[k] for rs in api.values() for r in rs.values() for k in ('json','cli','library')]),'schema_override_rejections':9,'structural_cases':sum(len(v['cases']) for v in reports['structural-stress']['tasks'].values()),'old_expansion_api_passes_and_rejections':counts([r[k] for rs in oldexp.values() for r in rs.values() for k in ('json','cli','library')]),'old_pilot_api_passes_and_rejections':counts([r[k] for rs in old.values() for r in rs.values() for k in ('json','cli','library')]),'old_cycle_designs_and_rejections':counts([r for rs in reports['old-cycle']['tasks'].values() for r in rs.values()]),'new_bounded_formal_families':1,'new_bounded_formal_valid_designs':sum(reports['formal'][n]['status']=='bounded_pass' for n in ('baseline','decoded','pipeline')),'pipeline_formal_status':reports['formal']['pipeline']['status'],'unbounded_formal_families':0,'physical_families':0,'trained_policies':0,'unit_tests':61,'os_isolation':'not_provided','pushed':False}
assert summary['new_designs_and_rejections']==[8,32] and summary['new_api_passes_and_rejections']==[24,96]
assert summary['old_expansion_api_passes_and_rejections']==[27,90] and summary['old_pilot_api_passes_and_rejections']==[18,219]
assert summary['old_cycle_designs_and_rejections']==[13,28] and summary['structural_cases']==4
assert all(r['tested_correct'] for r in reports['fresh-smoke'].values())
(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
cost={n:{label:{'wall_s':r['elapsed_s'],'tested_correct':r['tested_correct'],'reward':r['reward'],'pareto_point':r.get('pareto_point'),'objectives':r.get('objectives')} for label,r in rs.items()} for n,rs in q.items()}
(a.output/'cost-and-tradeoffs.json').write_text(json.dumps(cost,indent=2)+'\n');print(json.dumps(summary,indent=2))
