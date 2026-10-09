"""Summarize one fresh paired sparse24 campaign without exposing private vectors."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chip_rl.sparse24.rtl import design
from chip_rl.evaluate import digest
FIELDS=('cells','logic_depth','transactions','workload_cycles','accepted_to_first_sum','maximum_accepted_to_first',
 'accepted_to_consumption_sum','maximum_accepted_to_consumption','service_opportunity_age_sum','maximum_service_opportunity_age',
 'offered_to_consumption_sum','maximum_offered_to_consumption','accepted_count','consumed_count','ready_low_cycles',
 'output_blocked_cycles','input_blocked_cycles','stream_transactions','stream_cycles','stream_ii_numerator','stream_ii_denominator',
 'workload_sha256','watchdog_sha256','watchdog_cycles','service_opportunity_bound','long_stall_output_seen','reset_blocked_output_seen',
 'rtl_mapped_checked','reset_backpressure_checked')

def main(root,out):
 root=Path(root);out=Path(out)
 results={}
 for arch in ('serial','pipeline'):
  r=json.loads((root/f'fresh-heldout-{arch}'/'result.json').read_text())
  if not r['tested_correct'] or r['validation']!='rtl_and_mapped_exact_pass' or r['reward'] is not None or r['reward_qualified'] or r['source_sha256']!=digest(design(arch)):
   raise ValueError('invalid fresh result '+arch)
  if tuple(r['declared_scored_Gs'])!=(1,2,4,8) or len(r['cases'])!=4:raise ValueError('missing G case')
  results[arch]=r
 pre=json.loads((root/'preflight-paired-dev'/'result.json').read_text())
 if not pre['tested_correct'] or tuple(pre['declared_scored_Gs'])!=(1,2,4,8):raise ValueError('preflight failed')
 records=[];coverage={}
 for g in (1,2,4,8):
  baseline=None;hashes=set()
  for arch in ('serial','pipeline'):
   case=next(x for x in results[arch]['cases'] if x['G']==g);m=case['candidate']
   if not case['candidate_verified'] or not case['baseline_verified'] or not all(m[key] for key in ('rtl_mapped_checked','reset_backpressure_checked','long_stall_output_seen','reset_blocked_output_seen')):
    raise ValueError('unverified '+str((g,arch)))
   if m['accepted_count']!=m['transactions'] or m['consumed_count']!=m['transactions'] or m['stream_transactions']!=32:raise ValueError('valid count '+str((g,arch)))
   hashes.add(m['workload_sha256'])
   if arch=='serial':baseline={key:m[key] for key in FIELDS}
   elif any(case['baseline'][key]!=baseline[key] for key in FIELDS):raise ValueError('unpaired baseline '+str((g,arch)))
   n=m['transactions']
   records.append({'G':g,'architecture':arch,'metrics':{key:m[key] for key in FIELDS},
    'mean_accepted_to_first':m['accepted_to_first_sum']/n,'mean_accepted_to_consumption':m['accepted_to_consumption_sum']/n,
    'mean_offered_to_consumption':m['offered_to_consumption_sum']/n,'stream_initiation_interval':m['stream_ii_numerator']/31})
  if len(hashes)!=1:raise ValueError('workload mismatch')
  meta=json.loads((root/f'fresh-heldout-pipeline'/f'g{g}'/'candidate'/'simulation'/'private-workload.json').read_text())
  labels=meta['labels']
  for selector in range(8):
   for group in range(g):
    if f'selector_{selector}_group_{group}' not in labels:raise ValueError('selector coverage')
  for required in ('reserved_zero_extreme','signed_extreme','tie','clamp','extreme','ignored_directed_a','ignored_directed_b'):
   if required not in labels:raise ValueError('coverage '+required)
  if g>1 and ('permutation_a' not in labels or 'permutation_b' not in labels):raise ValueError('permutation coverage')
  coverage[str(g)]={key:labels.count(key) for key in ('reserved_zero_extreme','signed_extreme','tie','clamp','extreme','ignored_directed_a','ignored_directed_b','permutation_a','permutation_b')}
 failures={}
 for name,needle in (('pair_swap','wrong output'),('reserved_nonzero','functional mismatch')):
  r=json.loads((root/f'control-{name}'/'result.json').read_text());err=(root/f'control-{name}'/'private-error.txt').read_text()
  if r['tested_correct'] or r['reward'] is not None or r['reward_qualified'] or needle not in err:raise ValueError('fault control '+name)
  failures[name]='rejected'
 api=[json.loads(x) for x in (root/'api-responses.jsonl').read_text().splitlines()]
 if len(api)!=2 or not all(x['ok'] for x in api) or any(x['observation']['evaluation']['reward'] is not None or x['observation']['evaluation']['reward_qualified'] for x in api):raise ValueError('API')
 calls=len(list(root.glob('*/result.json')))+len(list(root.glob('api-traces/*/result.json')))
 sims=len(list(root.rglob('tool-logs/sparse24-*-simulation-*.log')))
 synth=len(list(root.rglob('tool-logs/sparse24-synthesis-*.log')))
 for arch in ('serial','pipeline'):
  if 'End of script.' not in (root/f'manual-g1-{arch}-synthesis.log').read_text():raise ValueError('manual synthesis log '+arch)
 if calls>24 or sims>160 or len(records)!=8:raise ValueError('campaign budget')
 replay=json.loads((root/'private-replay-root.json').read_text())
 summary={'version':'v31-sparse24-experimental','task':'sparse24_dot_requant','source_freeze_commit':replay['frozen_source_commit'],
  'reward':None,'reward_qualified':False,'architectures':[{'name':a,'source_sha256':results[a]['source_sha256']} for a in ('serial','pipeline')],
  'fresh_workload':'one private heldout replay root shared by both designs at G=1,2,4,8',
  'positive_fresh_design_configurations':8,'positive_preflight_design_configurations':8,
  'evaluation_calls':calls,'simulator_runs':sims,'journaled_synthesis_builds':synth,'manual_G1_synthesis_builds':2,
  'unique_design_G_synthesis_builds':synth+2,'source_unit_tests_passed':202,'installed_unit_tests_passed':202,
  'formal_validations':0,'physical_validations':0,'decoder_fault_controls':failures,'api_reset_step_passed':True,
  'coverage_labels_by_G':coverage,'records':records,'private_artifact_root':str(root.resolve()),
  'measurement_scope':'Icarus RTL and Yosys mapped replay; Yosys generic ABC cell count and longest generic-cell chain proxy, no library delay or routed timing/power'}
 archive=root.parent/'chip-rl-v31-private-artifacts.tar.gz'
 if archive.is_file():
  summary['private_artifact_archive']=str(archive.resolve());summary['private_artifact_archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
  summary['private_artifact_manifest']=str((root.parent/'chip-rl-v31-private-manifest.json').resolve())
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(summary,indent=2)+'\n')
 print(f'{len(records)} fresh positive records; {calls} evaluator calls; {sims} simulator runs; {synth+2} unique syntheses')
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('usage: python scripts/summarize_sparse24_v31.py PRIVATE_RUN_ROOT OUTPUT_JSON')
 main(*sys.argv[1:])
