import argparse,json,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,default=Path('/workspace'));p.add_argument('--output',type=Path,default=Path('evidence/v8'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
paths={'qualification':'final-qualification/summary.json','selected-api':'final-api/summary.json','deep':'final-deep/summary.json','other-api':'other-api/summary.json','pilot-regression':'pilot-regression/summary.json','formal-first':'formal/summary.json','formal-installed-attempt':'final-formal/summary.json','formal-baseline-retry':'formal-baseline-retry/result.json','source-provenance':'source-provenance.json','fresh-smoke':'fresh-smoke.json','deep-replay':'deep-replay.json','old-reset-gap':'old-blindspot/summary.json','reset-fix':'reset-fix/summary.json','old-late-gap':'old-late1535/result.json','late-fix':'late-fix/summary.json'};reports={}
for label,path in paths.items():
 r=json.loads((a.workspace/('chip-rl-v8-'+path)).read_text());assert not r.get('failures'),(label,r.get('failures'));reports[label]=r
 (a.output/(label+'.json')).write_text(json.dumps(r,indent=2)+'\n')
for src,dest in [('unit-final.log','unit-tests.txt'),('fresh-tests.log','fresh-checkout-tests.txt'),('frozen-wheel.log','wheel-install.txt'),('executed-commands.txt','executed-commands.txt')]:shutil.copy(a.workspace/('chip-rl-v8-'+src),a.output/dest)
def counts(rs):return [sum(r['tested_correct'] for r in rs),sum(not r['tested_correct'] for r in rs)]
s={'families_total':19,'new_families':0,'pilot_families':6,'experimental_families':13,'deepened_families':['ecc','coalesce','histogram'],'selected_designs_and_mutants':counts([v for rs in reports['qualification']['tasks'].values() for v in rs.values()]),'selected_api_valid_and_rejected':counts([v[k] for rs in reports['selected-api']['tasks'].values() for v in rs.values() for k in ('json','cli','library')]),'deep_valid_configuration_checks_and_rejections':counts([v for rs in reports['deep']['tasks'].values() for v in rs.values()]),'other_api_valid_and_rejected':counts([v[k] for rs in reports['other-api']['tasks'].values() for v in rs.values() for k in ('json','cli','library')]),'pilot_valid_designs_and_rejected_mutants':counts([v for rs in reports['pilot-regression']['tasks'].values() for v in rs.values()]),'unit_tests':71,'selected_schema_override_rejections':9,'other_schema_override_rejections':18,'new_alternatives':['coalesce:representatives','histogram:parallel_bins'],'bounded_formal_ecc_designs_with_successful_attempt':3,'formal_limit':'Width8,bound8,capacity<=2 asserted,liveness not proved. Installed baseline attempt timed out; byte-identical same-budget retry passed. Both retained. Historical timeouts unchanged.','physical_families':0,'unbounded_formal_families':0,'trained_policies':0,'os_isolation':'not_provided','pushed':False,'fixed_cycle_regression':'Prior v7/v6 results retained; v8 changed the transaction driver, not the fixed-cycle simulator. No new full cycle-suite run claimed.'}
assert s['selected_designs_and_mutants']==[9,35] and s['selected_api_valid_and_rejected']==[27,105]
assert s['deep_valid_configuration_checks_and_rejections']==[18,32]
assert s['other_api_valid_and_rejected']==[51,186] and s['pilot_valid_designs_and_rejected_mutants']==[16,71]
assert reports['formal-baseline-retry']['status']=='bounded_pass'
assert all(reports['formal-installed-attempt'][n]['status']=='bounded_pass' for n in ('decoded','pipeline'))
assert all(reports['fresh-smoke'][n]['tested_correct'] for n in ('ecc','coalesce','histogram')) and not reports['fresh-smoke']['lowered_budget']['tested_correct']
assert reports['deep-replay']['matched_recorded_verdict_and_metrics']
for n in ('ecc','coalesce','histogram'):
 assert reports['old-reset-gap'][n]['tested_correct'] and not reports['reset-fix'][n]['reset_priority']['tested_correct']
 assert reports['old-reset-gap'][n]['source_sha256']==reports['reset-fix'][n]['reset_priority']['source_sha256']
assert reports['old-late-gap']['tested_correct'] and not reports['late-fix']['late1535']['tested_correct']
assert reports['old-late-gap']['source_sha256']==reports['late-fix']['late1535']['source_sha256']
(a.output/'summary.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s,indent=2))
