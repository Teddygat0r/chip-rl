"""Collect final scope separately from retained development failures."""
import json,shutil
from pathlib import Path
root=Path('/workspace');out=Path('evidence/v10');out.mkdir(parents=True,exist_ok=True)
paths={'old-port-gap':'retire-port-gap/result.json','initial-qualification':'qualification/summary.json','retire-qualification':'sealed-retire-qualification/summary.json','crc-api':'final-crc-api/summary.json','retire-api':'sealed-retire-api/summary.json','other-api':'other-api/summary.json','long-crc':'long-crc/summary.json','preliminary-long-retire':'long-retire/summary.json','long-retire':'sealed-long-retire/summary.json','old-gap':'old-gap/summary.json','old-syntax-rejection':'old-gap/initial-syntax-rejection.json','objectives':'objectives.json','source-provenance':'sealed-source-provenance.json','fresh-smoke':'sealed-fresh-smoke/summary.json','replay':'sealed-replay.json','budget-api':'budget-api.json','diagnostic-reset-0':'api-diagnostic/0.json','diagnostic-reset-1':'api-diagnostic/1.json'}
r={}
for label,path in paths.items():
 j=json.loads((root/('chip-rl-v10-'+path)).read_text());r[label]=j
 if label not in ('initial-qualification','preliminary-long-retire'):assert not j.get('failures'),(label,j.get('failures'))
 (out/(label+'.json')).write_text(json.dumps(j,indent=2)+'\n')
crc=r['initial-qualification']['tasks']['crc'];retire=r['retire-qualification']['tasks']['retire']
assert not any(x.startswith('crc/') for x in r['initial-qualification']['failures'])
q={'tasks':{'crc':crc,'retire':retire},'failures':[],'scope':'CRC subsuite at7359056; corrected retirement at7cfc4b6. CRC code identity audited.'}
(out/'qualification.json').write_text(json.dumps(q,indent=2)+'\n')
def counts(rows):return [sum(x['tested_correct'] for x in rows),sum(not x['tested_correct'] for x in rows)]
def api(label):return [v[k] for rs in r[label]['tasks'].values() for v in rs.values() for k in ('json','cli','library')]
s={'families_total':19,'pilot_families':6,'experimental_families':13,'new_families':0,'selected_designs_and_mutants':counts(list(crc.values())+list(retire.values())),'selected_api_valid_and_rejected':counts(api('crc-api')+api('retire-api')),'other_api_valid_and_rejected':counts(api('other-api')),'long_valid_configurations_and_adversarial_rejections':counts([v for label in ('long-crc','long-retire') for rs in r[label]['tasks'].values() for v in rs.values()]),'unit_tests':79,'schema_rejections':27,'new_long_budget_override_rejections':4,'old_evaluator_faults_accepted_then_rejected':7,'new_formal_checks':0,'physical_families':0,'unbounded_formal_families':0,'trained_policies':0,'os_isolation':'not_provided','pushed':False,'legacy_hardware_regression':'Root pilots and four fixed-cycle families unchanged; prior evidence inherited, not rerun.','initial_crc_api_reset_failure':'Generic baseline qualification failed; underlying cause not retained and remains unknown. Two later reset diagnostics and final captured API matrix passed; initial failure preserved.','next_architecture_recommendation':'Dual-clock asynchronous FIFO / CDC bridge; assessed, not implemented.'}
assert s['selected_designs_and_mutants']==[6,28]
assert s['selected_api_valid_and_rejected']==[18,84]
assert s['other_api_valid_and_rejected']==[60,246]
assert s['long_valid_configurations_and_adversarial_rejections']==[18,45]
assert r['old-port-gap']['tested_correct'] and not retire['bad_frame_reset_ports']['tested_correct']
assert r['old-port-gap']['source_sha256']==retire['bad_frame_reset_ports']['source_sha256']
assert r['budget-api']['rejections']==4 and r['replay']['replayed']
for n,labels in [('crc',('count12','saturating_count','crc_wrap_restart')),('retire',('ticket12','saturating_ticket','numeric_ticket_order'))]:
 for label in labels:
  old=r['old-gap'][n+'/'+label];new=q['tasks'][n]['bad_'+label]
  assert old['tested_correct'] and not new['tested_correct'] and old['source_sha256']==new['source_sha256']
 assert r['fresh-smoke'][n]['tested_correct']
 assert not r['fresh-smoke']['lower-budget-'+n]['tested_correct']
assert all(r['diagnostic-reset-'+str(i)]['tested_correct'] for i in (0,1))
old=r['preliminary-long-retire']['tasks']['retire']['1-bad_numeric_ticket_order'];new=r['long-retire']['tasks']['retire']['1-bad_numeric_ticket_order']
assert old['tested_correct'] and not new['tested_correct'] and old['source_sha256']==new['source_sha256']
for source,target in [('unit-sealed.log','unit-tests.txt'),('sealed-fresh-tests.log','fresh-checkout-tests.txt'),('sealed-install.log','final-wheel-install.txt'),('final-install.log','initial-wheel-install.txt'),('api.log','initial-api-failure.txt'),('executed-commands.txt','executed-commands.txt')]:shutil.copy(root/('chip-rl-v10-'+source),out/target)
for name in ('old-gap','old-gap-fix','diagnose-api','fresh-smoke','sealed-fresh-smoke','budget-api','retire-port-gap'):shutil.copy(root/('chip-rl-v10-'+name+'.py'),out/(name+'-script.py'))
(out/'summary.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s,indent=2))
