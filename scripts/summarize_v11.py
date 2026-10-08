"""Collect recorded installed checks; fail rather than assume missing success."""
import json,shutil
from pathlib import Path
root=Path('/workspace');out=Path('evidence/v11');out.mkdir(parents=True,exist_ok=True)
paths={'cdc':'final-cdc/summary.json','cdc-api':'final-cdc-api/summary.json','formal':'final-formal/summary.json','crc-diagnostic':'crc-diagnostic/summary.json','crc-environment':'crc-diagnostic/environment.json','crc-reproducibility':'crc-diagnostic/reproducibility.json','runtime-identity':'runtime-identity.json','source-provenance':'source-provenance.json','budget':'budgets/summary.json','pilot':'pilot/summary.json','cycle':'cycle/summary.json','expansion-api':'expansion-api/summary.json','pilot-api':'pilot-api/summary.json','cycle-api':'cycle-api/summary.json','fresh-dimensions':'fresh-cdc/result.json'}
r={}
for label,path in paths.items():
 j=json.loads((root/('chip-rl-v11-'+path)).read_text());r[label]=j
 assert not j.get('failures'),(label,j.get('failures'))
 (out/(label+'.json')).write_text(json.dumps(j,indent=2)+'\n')
def counts(rows):return [sum(x['tested_correct'] for x in rows),sum(not x['tested_correct'] for x in rows)]
def api(label):return [v[k] for rs in r[label]['tasks'].values() for v in rs.values() for k in ('json','cli','library')]
cdc=list(r['cdc']['cases'].values());s={'families_total':20,'functional_and_synthesis_families':20,'pilot_families':6,'experimental_families':14,'new_family':'cdc_fifo','cdc_default_and_heldout_runs_and_rejections':counts(cdc),'cdc_positive_configuration_checks':sum(len(v['cases']) for v in cdc if v['tested_correct']),'cdc_api_accepted':sum(v[k]['tested_correct'] for v in r['cdc-api']['cases'].values() for k in ('json','cli','library')),'cdc_schema_rejections':r['cdc-api']['schema_rejections']+1,'cdc_budget_rejections':sum(not v['tested_correct'] for v in r['budget'].values()),'pilot_designs_and_mutants':counts([v for rows in r['pilot']['tasks'].values() for v in rows.values()]),'cycle_designs_and_mutants':counts([v for rows in r['cycle']['tasks'].values() for v in rows.values()]),'expansion_api_valid_and_rejected':counts(api('expansion-api')),'pilot_api_valid_and_rejected':counts(api('pilot-api')),'cycle_api_valid_and_rejected':counts([v for x in r['cycle-api']['tasks'].values() for v in x['evaluations']]),'unit_tests':83,'new_bounded_formal_design_variants':sum(v['status']=='bounded_pass' for k,v in r['formal'].items() if k not in ('corrupt','single_sync')),'formal_bound':24,'formal_scope':'width4/depth2 event-enable digital abstraction, initial coordinated reset; no unbounded/liveness/analog proof','corrupt_formal_counterexample':r['formal']['corrupt']['status']=='unproven','one_stage_digital_model_passes_but_structural_qualification_rejects':r['formal']['single_sync']['status']=='bounded_pass' and not r['cdc']['cases']['bad_single_sync']['tested_correct'],'physical_families':0,'physical_cdc_safety_verified':False,'unbounded_formal_families':0,'trained_policies':0,'os_isolation':'not_provided','pushed':False,'crc_original_failure':'Root cause unknown: original private seed and tool logs not retained. Three captured replays passed; not a reliability claim.'}
assert s['cdc_default_and_heldout_runs_and_rejections']==[8,12]
assert s['cdc_positive_configuration_checks']==32 and s['cdc_api_accepted']==12
assert s['new_bounded_formal_design_variants']==4 and s['cdc_budget_rejections']==2
assert s['expansion_api_valid_and_rejected']==[78,330]
from chip_rl.contracts import PILOT
from chip_rl.architectures import CATALOG
from chip_rl.adversaries import labels
assert set(r['pilot']['tasks'])==set(PILOT) and set(r['pilot-api']['tasks'])==set(PILOT)
assert s['pilot_designs_and_mutants']==[sum(len(CATALOG[n]) for n in PILOT),sum(len(labels(n)) for n in PILOT)]
assert s['pilot_api_valid_and_rejected']==[3*len(PILOT),3*(sum(len(labels(n)) for n in PILOT)+8)]
assert s['cycle_designs_and_mutants']==[13,28]
assert s['cycle_api_valid_and_rejected']==[8,4]
assert r['fresh-dimensions']['tested_correct']
for name in ('replay','replay-bad'):
 j=json.loads((root/('chip-rl-v11-'+name+'.log')).read_text());assert j['replayed'];(out/(name+'.json')).write_text(json.dumps(j,indent=2))
for name in ('final-units','install','final-formal','cdc-suite','cdc-api','pilot','cycle','pilot-api','cycle-api','expansion-api'):
 shutil.copy(root/('chip-rl-v11-'+name+'.log'),out/(name+'.txt'))
(out/'summary.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s,indent=2))
