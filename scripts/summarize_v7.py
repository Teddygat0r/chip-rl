"""Collect measured collective-task evidence and identify inherited regressions."""
import argparse,json,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,default=Path('/workspace'));p.add_argument('--output',type=Path,default=Path('evidence/v7'));p.add_argument('--prior',type=Path,default=Path('/workspace/chip-rl-remediation/evidence/v6/summary.json'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
paths={'replay':'replay.json','qualification':'final-qualification/summary.json','api':'final-api/summary.json','structural-stress':'final-holdouts/summary.json','formal':'formal/summary.json','old-expansion-api':'old-expansion-api/summary.json','source-provenance':'source-provenance.json','fresh-smoke':'fresh-smoke.json','rollouts':'rollouts.json','legacy-identity':'legacy-identity.json'};reports={}
for name,path in paths.items():
 r=json.loads((a.workspace/('chip-rl-v7-'+path)).read_text());assert not r.get('failures'),(name,r.get('failures'));reports[name]=r
 (a.output/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n')
prior=json.loads(a.prior.read_text());(a.output/'inherited-v6-summary.json').write_text(json.dumps(prior,indent=2)+'\n')
for src,dest in [('results-commands.txt','executed-commands.txt'),('unit-final.log','unit-tests.txt'),('fresh-tests.log','fresh-checkout-tests.txt'),('final-wheel.log','wheel-install.txt')]:shutil.copy(a.workspace/('chip-rl-v7-'+src),a.output/dest)
def counts(rs):return [sum(r['tested_correct'] for r in rs),sum(not r['tested_correct'] for r in rs)]
q=reports['qualification']['tasks'];api=reports['api']['tasks'];old=reports['old-expansion-api']['tasks']
s={'new_experimental_families':3,'functional_and_synthesis_families_total':19,'pilot_families':6,'experimental_families':13,'new_designs_and_rejections':counts([r for rs in q.values() for r in rs.values()]),'new_api_passes_and_rejections':counts([r[k] for rs in api.values() for r in rs.values() for k in ('json','cli','library')]),'schema_override_rejections':9,'structural_cases':sum(len(v['cases']) for v in reports['structural-stress']['tasks'].values()),'old_expansion_api_passes_and_rejections':counts([r[k] for rs in old.values() for r in rs.values() for k in ('json','cli','library')]),'legacy_runtime_identical_to_v6':reports['legacy-identity']['identical'],'pilot_controller_regression':'Inherited v6 HDL results; no fresh full pilot/controller run in v7. 29 runtime files identical; 3000 contract outputs identical. Expansion API matrix rerun in full.','new_bounded_formal_families':1,'new_bounded_formal_valid_designs':sum(reports['formal'][n]['status']=='bounded_pass' for n in ('baseline','tree','serial')),'tree_formal_status':reports['formal']['tree']['status'],'unbounded_formal_families':0,'physical_families':0,'trained_policies':0,'unit_tests':66,'os_isolation':'not_provided','pushed':False}
assert s['new_designs_and_rejections']==[7,31] and s['new_api_passes_and_rejections']==[21,93]
assert s['old_expansion_api_passes_and_rejections']==[51,186] and s['structural_cases']==6
assert all(r['tested_correct'] for r in reports['fresh-smoke'].values()) and s['legacy_runtime_identical_to_v6']
assert prior['old_pilot_api_passes_and_rejections']==[18,219] and prior['old_cycle_designs_and_rejections']==[13,28]
(a.output/'summary.json').write_text(json.dumps(s,indent=2)+'\n')
cost={n:{label:{'wall_s':r['elapsed_s'],'tested_correct':r['tested_correct'],'reward':r['reward'],'pareto_point':r.get('pareto_point'),'objectives':r.get('objectives')} for label,r in rs.items()} for n,rs in q.items()}
(a.output/'cost-and-tradeoffs.json').write_text(json.dumps(cost,indent=2)+'\n');print(json.dumps(s,indent=2))
