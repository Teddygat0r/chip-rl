"""Collect completed installed checks; incomplete or unexpected results fail."""
import json,shutil
from pathlib import Path
root=Path('/workspace');out=Path('evidence/v9');out.mkdir(parents=True,exist_ok=True)
paths={'old-sync-ports':'old-sync-ports/summary.json','synchronous-reset-ports':'sync-ports/summary.json','search-objectives':'search-objectives.json','qualification':'final-qualification/summary.json','selected-api':'final-api/summary.json','deep':'final-deep/summary.json','other-api':'other-api/summary.json','old-gap':'old-gap/summary.json','gap-fix':'final-gap-fix/summary.json','fresh-smoke':'final-fresh-smoke/summary.json','source-provenance':'final-source-provenance.json','score-neutrality':'final-score-neutrality.json','replay':'final-replay.json'}
r={}
for label,path in paths.items():
 j=json.loads((root/('chip-rl-v9-'+path)).read_text());assert not j.get('failures'),label;r[label]=j
 (out/(label+'.json')).write_text(json.dumps(j,indent=2)+'\n')
def counts(name,api=False):
 rows=[v[k] for rs in r[name]['tasks'].values() for v in rs.values() for k in ('json','cli','library')] if api else [v for rs in r[name]['tasks'].values() for v in rs.values()]
 return [sum(v['tested_correct'] for v in rows),sum(not v['tested_correct'] for v in rows)]
s={'families_total':19,'pilot_families':6,'experimental_families':13,'new_families':0,'selected_designs_and_mutants':counts('qualification'),'selected_api_valid_and_rejected':counts('selected-api',True),'deep_valid_configuration_checks_and_rejections':counts('deep'),'other_api_valid_and_rejected':counts('other-api',True),'unit_tests':73,'reset_control_combinations':4,'interruption_accepted_counts':[1,2],'hold_clocks':list(range(10)),'reset_probe_pairs_per_configuration':80,'selected_schema_rejections':9,'other_schema_rejections':18,'synchronous_reset_variants_accepted':3,'other_api_build':'initial_v9; unused qualification driver is the only runtime difference from final v9','new_formal_checks':0,'physical_families':0,'unbounded_formal_families':0,'trained_policies':0,'os_isolation':'not_provided','pushed':False,'legacy_regression':'Root pilot and fixed-cycle code unchanged from v8; previous results inherited, not rerun.'}
assert s['selected_designs_and_mutants']==[9,41]
assert s['selected_api_valid_and_rejected']==[27,123]
assert s['deep_valid_configuration_checks_and_rejections']==[18,44]
assert s['other_api_valid_and_rejected']==[51,186]
assert r['score-neutrality']['score_metrics_unchanged'] and r['replay']['matched_recorded_verdict_and_metrics']
for name in ('ecc','coalesce','histogram'):
 assert r['old-gap'][name]['default']['tested_correct'] and r['old-gap'][name]['deep']['tested_correct']
 assert not r['gap-fix'][name]['tested_correct']
 assert r['old-gap'][name]['default']['source_sha256']==r['gap-fix'][name]['source_sha256']
 assert r['fresh-smoke'][name]['tested_correct']
 assert not r['old-sync-ports'][name]['tested_correct']
 assert all(r['synchronous-reset-ports'][name][k]['tested_correct'] for k in ('default','deep'))
 assert r['old-sync-ports'][name]['source_sha256']==r['synchronous-reset-ports'][name]['default']['source_sha256']
for src,dest in [('unit-final.log','unit-tests.txt'),('final-fresh-tests.log','fresh-checkout-tests.txt'),('final-install.log','wheel-install.txt'),('executed-commands.txt','executed-commands.txt')]:shutil.copy(root/('chip-rl-v9-'+src),out/dest)
for source in ('probe','gap-fix','fresh-smoke','final-gap-fix','final-fresh-smoke','reset-port-witness'):
 shutil.copy(root/('chip-rl-v9-'+source+'.py'),out/(source+'-script.py'))
(out/'summary.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s,indent=2))
