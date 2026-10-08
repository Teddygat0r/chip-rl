"""Summarize completed qualification, without embedding private seeds or logs."""
import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('/workspace'));p.add_argument('--output',type=Path,default=Path('evidence/v12'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
def read(label):
 j=json.loads((a.root/f'chip-rl-v12-release-{label}'/'summary.json').read_text())
 assert not j.get('failures'),(label,j.get('failures'))
 return j
def count(rows):return [sum(r['tested_correct'] for r in rows),sum(not r['tested_correct'] for r in rows)]
def api(j):return [v[k] for rows in j['tasks'].values() for v in rows.values() for k in ('json','cli','library')]
def flat(j):return [r for rows in j['tasks'].values() for r in rows.values()]
def save(name,j):(a.output/name).write_text(json.dumps(j,indent=2)+'\n')
negative=json.loads((a.output/'mutant-rejections.json').read_text())
assert sum(len(v) for v in negative.values())==32 and all(not r['syntax_or_compile_failure'] for v in negative.values() for r in v.values())
process=json.loads((a.root/'chip-rl-v12-journal-process'/'summary.json').read_text())
assert process['abrupt_parent_death_retains_started_seed_config_source_and_streamed_log'] and process['tool_timeout_rejected_with_retained_evidence']
m=read('memory');h=read('heldout');ma=read('api');b=read('budgets');pa=read('pilot-api');ca=read('cycle-api');ea=read('expansion-api');cd=read('cdc-api');cl=read('cycle-library')
assert count(flat(m))==[4,32] and count(flat(h))==[4,0]
assert count(api(ma))==[12,96] and len(b)==4 and all(not x['tested_correct'] and x['reward']==0 for x in b.values())
assert count(api(pa))==[18,237] and count(api(ea))==[78,330]
assert count([r for v in ca['tasks'].values() for r in v['evaluations']])==[8,4]
assert count([r for rows in cl['tasks'].values() for r in rows])==[8,4]
assert count([v[k] for v in cd['cases'].values() for k in ('json','cli','library')])==[12,0]
for label in ('release-unit','clean-unit'):
 text=(a.root/f'chip-rl-v12-{label}.log').read_text();assert re.search(r'Ran 91 tests in .*\n\nOK',text),label
replays={}
for label in ('mshr','tlb','bad'):
 replays[label]=json.loads((a.root/f'chip-rl-v12-release-replay-{label}.log').read_text());assert replays[label]['replayed']
family={}
for n,rows in m['tasks'].items():
 family[n]={'default_designs_and_mutants':count(list(rows.values())),'heldout_designs':sum(r['tested_correct'] for r in h['tasks'][n].values()),'positive_configuration_checks':sum(len(r['cases']) for r in list(rows.values())+list(h['tasks'][n].values()) if r['tested_correct']),'api_valid_and_rejected':count([r[k] for r in ma['tasks'][n].values() for k in ('json','cli','library')]),'schema_rejections':ma['schema_rejections_per_family'],'designs':{k:{'target_cells':r['cases'][0]['candidate']['cells'],'target_logic_depth':r['cases'][0]['candidate']['logic_depth'],'ratios':r['ratios'],'reward':r['reward']} for k,r in rows.items() if r['tested_correct']},'formal':'not_run','physical':'not_run'}
 assert any(v['reward']!=1 for v in family[n]['designs'].values()),'reward insensitive'
s={'families_total':22,'functional_and_synthesis_families':22,'pilot_families':6,'experimental_families':16,'new_families':family,'journal_process_checks':process,'unit_tests':91,'clean_offline_wheel_install':True,'clean_install_unit_tests':91,'memory_default_designs_and_mutants':[4,32],'memory_mutants_rejected_without_syntax_failures':32,'memory_heldout_designs':4,'memory_positive_configuration_checks':24,'memory_api_valid_and_rejected':[12,96],'memory_schema_rejections':8,'memory_budget_rejections':4,'existing_pilot_api_valid_and_rejected':[18,237],'existing_cycle_json_valid_and_rejected':[8,4],'existing_cycle_library_valid_and_rejected':[8,4],'existing_expansion_api_valid_and_rejected':[78,330],'existing_cdc_api_valid':12,'existing_cdc_schema_rejections':cd['schema_rejections']+1,'replay':replays,'new_formal_families':0,'physical_families':0,'unbounded_formal_families':0,'trained_policies':0,'os_isolation':'not_provided','crc_original_failure':'Unresolved: original seed/logs missing. Later captured passes do not diagnose it.','publication':'Only the earlier 20-family checkpoint was approved/pushed; v12 stays local.'}
regression={}
for group,j in [('pilot',pa),('expansion',ea),('memory',ma)]:
 for name,rows in j['tasks'].items():regression[name]={'suite':group,'apis':{k:count([v[k] for v in rows.values()]) for k in ('json','cli','library')}}
for name,v in ca['tasks'].items():regression[name]={'suite':'cycle','apis':{'json':count(v['evaluations']),'library':count(cl['tasks'][name])},'scope':'cycle family exposes JSON and library APIs; no standalone single-candidate CLI'}
regression['cdc_fifo']={'suite':'cdc','apis':{k:count([v[k] for v in cd['cases'].values()]) for k in ('json','cli','library')}}
assert len(regression)==22
save('api-regression-counts.json',regression)
save('summary.json',s)
# Per-family measured results have provenance hashes, never seeds or test vectors.
for label,j in [('memory-results',m),('heldout-results',h)]:save(label+'.json',j)
print(json.dumps(s,indent=2))
