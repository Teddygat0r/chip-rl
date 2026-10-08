"""Collect the fixed v13 study; retain raw public results and descriptive statistics."""
import argparse,json,re,statistics,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('/workspace'));p.add_argument('--output',type=Path,default=Path('evidence/v13'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
results={};summary={};calls=dev=held=correct=ineligible=0
for task in ('tlb','dot','tensor'):
 r=json.loads((a.root/f'chip-rl-v13-{task}'/'summary.json').read_text());assert r['all_measured_sources_correct'] and not r['trained_policy']
 assert r['actual_evaluations']<=r['plan']['maximum_actual_unique_evaluations'][task]
 assert len(r['trials'])==3
 results[task]=r;methods={}
 for method in r['plan']['methods']:
  rows=[t['methods'][method] for t in r['trials']]
  assert all(x['query_count']==r['plan']['development_query_budget_including_baseline'][task] for x in rows)
  ds=[next(q['reward'] for q in x['queries'] if q['label']==x['winner']) for x in rows]
  hs=[statistics.mean(h['result']['reward'] for h in x['heldout']) for x in rows]
  methods[method]={'winners':[x['winner'] for x in rows],'development_best_rewards':ds,'development_mean':statistics.mean(ds),'heldout_mean_reward_per_trial':hs,'heldout_mean':statistics.mean(hs),'heldout_all_correct_and_eligible':all(h['result']['tested_correct'] and h['result']['objective_eligible'] for x in rows for h in x['heldout']),'nominal_shared_measurement_seconds_charged':sum(x['nominal_seconds_charged'] for x in rows)}
  assert methods[method]['heldout_all_correct_and_eligible']
 samples=r['measurements'];assert len(samples)==r['actual_evaluations']
 summary[task]={'methods':methods,'actual_unique_evaluations':r['actual_evaluations'],'actual_task_wall_seconds':r['actual_wall_seconds'],'development_queries_charged':r['development_queries_charged'],'heldout_queries_charged':r['heldout_queries_charged'],'catalog_size':len(r['plan']['catalogs'][task])}
 calls+=r['actual_evaluations'];dev+=r['development_queries_charged'];held+=r['heldout_queries_charged'];correct+=sum(v['result']['tested_correct'] for v in samples.values());ineligible+=sum(not v['result'].get('objective_eligible',False) for v in samples.values())
 (a.output/f'{task}-results.json').write_text(json.dumps(r,indent=2)+'\n')
assert calls<=69 and correct==calls and dev==72 and held==45
text=(a.root/'chip-rl-v13-unit-replay-fix.log').read_text();assert re.search(r'Ran 99 tests in .*\n\nOK',text)
s={'families_total':22,'new_families':0,'runtime_unchanged_from_v12':True,'study_plan_commit':'93c225f64174a9bf2a857ec8105bdcfe145fb8b1','actual_unique_hdl_evaluations':calls,'functional_and_mapped_passes':correct,'correct_but_objective_ineligible_measurements':ineligible,'charged_development_queries':dev,'charged_heldout_queries':held,'unit_tests':99,'premeasurement_unit_tests':97,'tasks':summary,'trained_policy':False,'llm_calls':0,'paid_services':False,'new_formal_runs':0,'physical_runs':0,'search_superiority_claim':False,'limitations':['Three workload trials; descriptive results only.','Previously authored finite catalogs; no generated RTL or learned agent.','TLB and tensor budgets exhaust their small catalogs.','Handwritten rule has historical/template prior knowledge.','Identical source/config/private-seed queries reuse a measured result; each method pays the same query charge.','Query budgets match, but this is not a controlled cold-run or equal-wall-time comparison.','Structural stress dimensions were previously exercised in earlier iterations; only workload instances are new. This is not a blind unseen-structure benchmark.','Existing judge-isolation, physical and formal limitations remain.']}
(a.output/'summary.json').write_text(json.dumps(s,indent=2)+'\n');shutil.copy(a.root/'chip-rl-v13-unit-replay-fix.log',a.output/'unit-tests.txt');print(json.dumps(s,indent=2))
