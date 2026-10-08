"""Sanitize local checkpoint evidence; never exports workload seeds or raw logs."""
import argparse,json,hashlib,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,default=Path('/workspace'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
def load(name):return json.loads((a.workspace/name).read_text())
def save(name,data):(a.output/name).write_text(json.dumps(data,indent=2)+'\n')
def trim(r):return {k:v for k,v in r.items() if k not in ('protocol','development_dimensions')}
dev={};held={};final={}
for n in ('dot','tensor','tlb'):
 rows=load(('chip-rl-v14-coverage-development-tlb' if n=='tlb' else 'chip-rl-v14-development-'+n)+'/results.json')
 if n!='tlb':rows+=load('chip-rl-v14-shift-'+n+'/results.json')
 dev[n]={x['architecture']:trim(x['result']) for x in rows}
 held[n]={x['architecture']:trim(x['result']) for x in load('chip-rl-v14-heldout-'+n+'/results.json')}
 final[n]={x['architecture']:trim(x['result']) for x in load(('chip-rl-v14-reserve-tlb' if n=='tlb' else 'chip-rl-v14-coverage-heldout-'+n)+'/results.json')}
assert sum(len(x) for x in dev.values())==26 and all(r['tested_correct'] for rows in dev.values() for r in rows.values())
assert sum(len(x) for x in final.values())==12 and all(r['tested_correct'] for rows in final.values() for r in rows.values())
mut=load('chip-rl-v14-coverage-mutants/results.json');assert len(mut)==20 and all(not x['result']['tested_correct'] for x in mut)
apis=load('chip-rl-v14-final-apis/summary.json');apis['tlb']=load('chip-rl-v14-coverage-apis/summary.json')['tlb'];assert len(apis)==3 and all(len(x)==3 for x in apis.values())
valid=bad=0
for rows in apis.values():
 for label,rs in rows.items():
  for r in rs.values():
   assert r['tested_correct']==(label!='bad')
   valid+=r['tested_correct'];bad+=not r['tested_correct']
aggregate=load('chip-rl-v14-aggregate/summary.json');assert len(aggregate['families'])==22
journals=[]
for root in a.workspace.glob('chip-rl-v14*'):
 if root.is_dir():
  for path in root.rglob('private-run.json'):
   j=json.loads(path.read_text())
   if j.get('evaluator')=='chip_rl.quality.evaluate.Evaluator.evaluate':
    assert j['status']=='completed',path
    r=json.loads(path.with_name('result.json').read_text());journals.append(r)
assert len(journals)==230,len(journals)
summary={'families_total':22,'functional_and_synthesis_families':22,'new_families':0,'new_profiles':3,'development_design_profile_pairs':26,'unique_generic_candidate_sources':len({r['source_sha256'] for rows in dev.values() for r in rows.values()}),'development_paired_configuration_workload_cases':sum(len(r['cases']) for rows in dev.values() for r in rows.values()),'heldout_design_profile_pairs':12,'heldout_paired_configuration_workload_cases':sum(len(r['cases']) for rows in final.values() for r in rows.values()),'heldout_recipe_change_requalifications':20,'additional_reserved_tlb_design_profile_pairs':4,'final_mutants_rejected':20,'final_api_valid':valid,'final_api_fault_rejections':bad,'final_api_schema_rejections':12,'aggregate_baselines':22,'aggregate_behavioral_rejections':21,'aggregate_invalid_action_rejection':1,'aggregate_artifact_override_rejections':22,'unit_tests':112,'source_and_installed_units_passed':True,'new_profile_actual_evaluator_calls_including_all_replays':len(journals),'all_calls_evaluator_reported_correct_including_one_known_false_positive':sum(r['tested_correct'] for r in journals),'all_calls_rejected_including_initial_driver_failure':sum(not r['tested_correct'] for r in journals),'budget_calls_initial':180,'budget_calls_revised_before_repair':230,'known_false_positive_before_repair':1,'captured_survivor_rejected_after_repair':True,'directed_probe_score_neutrality_passed':True,'exact_replays':{'initial_frozen_recipe':3,'host_guard_recipe':1,'coverage_repair_recipe':1,'separate_tool_extraction':True},'formal_new':0,'physical_new':0,'unbounded_formal_families':0,'physical_families':0,'trained_policies':0,'security':'source-only schema and bounded processes; no OS judge sandbox','publication':'local only; no push','original_crc_failure':'unresolved; no new diagnosis','limits':'26 catalog/task pairs are finite exemplars, not evidence of learning difficulty; author-visible structural split; cell/cycle proxies not routed PPA','costs':{'development_elapsed_seconds_by_evaluation':{n:{k:r['elapsed_s'] for k,r in rows.items()} for n,rows in dev.items()},'all_new_calls_summed_elapsed_s':sum(r['elapsed_s'] for r in journals),'elapsed_note':'Sum of evaluation durations, not wall time or compute-matched search. Concurrent runs and synthesis caches used.'}}
save('summary.json',summary);save('development.json',dev);save('heldout-first-freeze.json',held);save('heldout-final-recipe.json',final);save('mutant-rejections.json',[{'task':x['task'],'mutant':x['mutant'],'result':trim(x['result'])} for x in mut]);save('api-results.json',{n:{k:{api:trim(r) for api,r in rs.items()} for k,rs in rows.items()} for n,rows in apis.items()});save('aggregate.json',{'families':{n:{'baseline_correct':r['baseline']['tested_correct'],'fault_or_invalid_action_rejected':r['fault_or_invalid_action_rejected'],'artifact_override_rejected':r['artifact_override_rejected']} for n,r in aggregate['families'].items()},'scope':aggregate['scope']});print(json.dumps(summary,indent=2))
