"""Summarize local v29 journals; never copy replay seeds or operand vectors."""
import hashlib,json,sys
from pathlib import Path
FIELDS=('cells','logic_depth','transactions','workload_cycles','accepted_to_first_sum','maximum_accepted_to_first',
 'accepted_to_consumption_sum','maximum_accepted_to_consumption','service_opportunity_age_sum','maximum_service_opportunity_age',
 'offered_to_consumption_sum','maximum_offered_to_consumption','accepted_count','consumed_count','ready_low_cycles',
 'output_blocked_cycles','input_blocked_cycles','stream_cycles','stream_ii_numerator','stream_ii_denominator',
 'workload_sha256','watchdog_sha256','watchdog_cycles','service_opportunity_bound','long_stall_output_seen','reset_blocked_output_seen')

def main(root,out):
 root=Path(root);out=Path(out)
 previous=json.loads((Path(__file__).resolve().parents[1]/'evidence/v28/summary.json').read_text())
 old={(x['split'],x['K'],x['architecture']):x['metrics'] for x in previous['records']}
 records=[];aggregates=[]
 for split in ('dev','heldout'):
  for arch in ('serial','parallel'):
   name=f'aggregate-{split}-{arch}'
   r=json.loads((root/name/'result.json').read_text())
   if not r['tested_correct'] or not r['reward_qualified'] or not r['hard_constraints_passed'] or r['validation']!='rtl_and_mapped_exact_pass':raise ValueError('unqualified '+name)
   want=(2,4,8) if split=='dev' else (1,2,4,8,16)
   if tuple(r['declared_scored_Ks'])!=want or len(r['cases'])!=len(want) or len(r['scored_cases'])!=len(want):raise ValueError('case set '+name)
   aggregates.append({'split':'development' if split=='dev' else split,'architecture':arch,'reward':r['reward'],'reward_qualified':r['reward_qualified'],
    'hard_constraints_passed':r['hard_constraints_passed'],'declared_scored_Ks':list(want),'source_sha256':r['source_sha256'],'recipe_sha256':r['recipe_sha256']})
   for case,scored in zip(r['cases'],r['scored_cases']):
    k=case['K'];m=case['candidate'];ref=old[('development' if split=='dev' else split,k,arch)]
    if not case['candidate_verified'] or not case['baseline_verified'] or scored['K']!=k or not scored['constraints_passed']:raise ValueError('unverified case')
    for key in ('cells','logic_depth','transactions','workload_cycles','accepted_to_first_sum','offered_to_consumption_sum','stream_ii_numerator','stream_ii_denominator','workload_sha256'):
     if m[key]!=ref[key]:raise ValueError('v28 scored prefix changed: '+str((split,k,arch,key)))
    if not m['long_stall_output_seen'] or not m['reset_blocked_output_seen']:raise ValueError('frozen valid architecture did not present output during probes')
    if m['accepted_count']!=m['transactions'] or m['consumed_count']!=m['transactions']:raise ValueError('counter mismatch')
    records.append({'split':'development' if split=='dev' else split,'K':k,'architecture':arch,
     'metrics':{key:m[key] for key in FIELDS},'area_ratio':scored['area_ratio'],'completion_ratio':scored['completion_ratio'],
     'stream_ii':scored['stream_ii'],'hard_constraints':scored['constraints']})
 control=json.loads((root/'aggregate-control-nonresponding'/'result.json').read_text())
 err=(root/'aggregate-control-nonresponding'/'private-error.txt').read_text()
 if control['tested_correct'] or control['reward_qualified'] or control['reward']!=0 or 'service opportunity timeout' not in err:raise ValueError('nonresponding control did not fail progress')
 refused=json.loads((root/'aggregate-control-refuse-input'/'result.json').read_text())
 err=(root/'aggregate-control-refuse-input'/'private-error.txt').read_text()
 if refused['tested_correct'] or refused['reward_qualified'] or refused['reward']!=0 or 'completion timeout' not in err:raise ValueError('unaccepted-work control did not reach watchdog')
 api=[json.loads(x) for x in (root/'api-responses.jsonl').read_text().splitlines()]
 if len(api)!=2 or not all(x['ok'] for x in api) or api[0]['observation']['evaluation']['reward']!=0 or not api[0]['observation']['evaluation']['reward_qualified'] or not api[1]['info']['reward_qualified']:raise ValueError('API smoke')
 calls=len(list(root.glob('*/result.json')))+len(list(root.glob('api-traces/*/result.json')))
 sims=len(list(root.rglob('tool-logs/fused-*-simulation-*.log')))
 synth=len(list(root.rglob('tool-logs/fused-synthesis-*.log')))
 if calls>24 or sims>160 or len(records)!=16:raise ValueError('campaign budget')
 summary={'task':'fused_dot_requant','version':'v29-experimental','measurement_scope':'Icarus RTL and Yosys mapped simulation; Yosys generic ABC cells and logic-depth proxy; not routed timing or power',
  'reward_policy':'experimental_balanced_proxy','progress_service_opportunity_bound':'K+64 ready-high cycles strictly after acceptance, including consumption',
  'watchdog_service_budget':'N*(K+64)+1 ready-high cycles starting at last scheduled release','positive_design_configurations':len(records),
  'evaluation_calls':calls,'simulator_runs':sims,'new_synthesis_builds':synth,'formal_validations':0,'physical_validations':0,
  'source_unit_tests_passed':197,'installed_unit_tests_passed':197,
  'nonresponding_control':'rejected_by_service_opportunity_timeout','unaccepted_work_control':'rejected_by_whole_run_watchdog',
  'api_reset_step_passed':True,
  'preliminary_instrumentation_error':'one COUNTERS marker typo was corrected before frozen aggregate runs',
  'aggregates':aggregates,'records':records,'private_artifact_root':str(root.resolve())}
 archive=root.parent/'chip-rl-v29-private-artifacts.tar.gz'
 if archive.is_file():
  summary['private_artifact_archive']=str(archive.resolve())
  summary['private_artifact_archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
  summary['private_artifact_manifest']=str((root.parent/'chip-rl-v29-private-manifest.json').resolve())
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(summary,indent=2)+'\n')
 print(f'{len(records)} positive design/configurations; {calls} evaluator calls; {sims} simulator runs; {synth} new syntheses')
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('usage: python scripts/summarize_fused_v29.py PRIVATE_RUN_ROOT OUTPUT_JSON')
 main(*sys.argv[1:])
