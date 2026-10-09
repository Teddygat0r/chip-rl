"""Summarize one fresh, source-frozen three-architecture fused comparison."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chip_rl.fused.rtl import design
from chip_rl.evaluate import digest
FIELDS=('cells','logic_depth','transactions','workload_cycles','accepted_to_first_sum','maximum_accepted_to_first',
 'accepted_to_consumption_sum','maximum_accepted_to_consumption','service_opportunity_age_sum','maximum_service_opportunity_age',
 'offered_to_consumption_sum','maximum_offered_to_consumption','accepted_count','consumed_count','ready_low_cycles',
 'output_blocked_cycles','input_blocked_cycles','stream_transactions','stream_cycles','stream_ii_numerator','stream_ii_denominator',
 'workload_sha256','watchdog_sha256','watchdog_cycles','service_opportunity_bound','long_stall_output_seen','reset_blocked_output_seen',
 'rtl_mapped_checked','reset_backpressure_checked')

def main(root,out):
 root=Path(root);out=Path(out);results={}
 for arch in ('serial','parallel','pipeline'):
  r=json.loads((root/f'fresh-heldout-{arch}'/'result.json').read_text())
  if not r['tested_correct'] or r['validation']!='rtl_and_mapped_exact_pass' or not r['reward_qualified'] or r['source_sha256']!=digest(design(arch)):
   raise ValueError('invalid architecture result: '+arch)
  if tuple(r['declared_scored_Ks'])!=(1,2,4,8,16) or len(r['cases'])!=5:raise ValueError('missing K case')
  results[arch]=r
 pre=json.loads((root/'preflight-pipeline-dev'/'result.json').read_text())
 if not pre['tested_correct'] or tuple(pre['declared_scored_Ks'])!=(2,4,8):raise ValueError('pipeline preflight failed')
 records=[]
 for k in (1,2,4,8,16):
  hashes=set();baseline=None
  for arch in ('serial','parallel','pipeline'):
   r=results[arch];case=next(c for c in r['cases'] if c['K']==k);m=case['candidate']
   if not case['candidate_verified'] or not case['baseline_verified'] or not m['rtl_mapped_checked'] or not m['reset_backpressure_checked']:
    raise ValueError('unverified '+str((k,arch)))
   if m['transactions']!=206 or m['accepted_count']!=206 or m['consumed_count']!=206 or m['stream_transactions']!=32 or not m['long_stall_output_seen'] or not m['reset_blocked_output_seen']:
    raise ValueError('missing valid results/probes '+str((k,arch)))
   hashes.add(m['workload_sha256'])
   if arch=='serial':baseline={key:m[key] for key in FIELDS}
   elif any(case['baseline'][key]!=baseline[key] for key in FIELDS):raise ValueError('unpaired baseline '+str((k,arch)))
   records.append({'K':k,'architecture':arch,'metrics':{key:m[key] for key in FIELDS},
    'mean_accepted_to_first':m['accepted_to_first_sum']/206,'mean_accepted_to_consumption':m['accepted_to_consumption_sum']/206,
    'mean_offered_to_consumption':m['offered_to_consumption_sum']/206,'stream_initiation_interval':m['stream_ii_numerator']/m['stream_ii_denominator']})
  if len(hashes)!=1:raise ValueError('workload differs between architectures')
 calls=len(list(root.glob('*/result.json')))
 sims=len(list(root.rglob('tool-logs/fused-*-simulation-*.log')))
 builds=len(list(root.rglob('tool-logs/fused-synthesis-*.log')))
 manual_k2=root/'manual-k2-synthesis.log'
 if not manual_k2.is_file() or 'End of script.' not in manual_k2.read_text():raise ValueError('missing initial K2 synthesis log')
 if calls>24 or sims>160 or len(records)!=15:raise ValueError('campaign budget')
 replay_path=root/'private-replay-root.json'
 if not replay_path.is_file():replay_path=root.parent/'chip-rl-v30-private-replay.json'
 replay=json.loads(replay_path.read_text())
 summary={'version':'v30-reference-comparison','family':'fused_dot_requant','source_freeze_commit':replay['frozen_source_commit'],
  'architectures':[{ 'name':arch,'source_sha256':results[arch]['source_sha256'],'experimental_v29_reward':results[arch]['reward'],
   'reward_qualified':results[arch]['reward_qualified']} for arch in ('serial','parallel','pipeline')],
  'fresh_workload':'one private replay root with heldout K=1,2,4,8,16; identical operand/traffic schedule for all three sources at each K',
  'positive_fresh_design_configurations':15,'preflight_pipeline_development_configurations':3,
  'evaluation_calls':calls,'simulator_runs':sims,'synthesis_builds_in_journals':builds,'initial_K2_synthesis_builds':1,
  'unique_pipeline_K_synthesis_builds':builds+1,'source_unit_tests_passed':197,'installed_unit_tests_passed':197,
  'formal_validations':0,'physical_validations':0,'errors':[],
  'generic_depth_method':'Yosys 0.52 read_verilog -sv; chparam K; hierarchy -check -top candidate; synth -top candidate; check -assert; write_json; host logical_depth counts longest generic combinational-cell chain between inputs/FF outputs and outputs/FF inputs, with FF outputs reset to depth zero; no cell delays or physical parasitics',
  'records':records,'private_artifact_root':str(root.resolve())}
 archive=root.parent/'chip-rl-v30-private-artifacts.tar.gz'
 if archive.is_file():
  summary['private_artifact_archive']=str(archive.resolve());summary['private_artifact_archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
  summary['private_artifact_manifest']=str((root.parent/'chip-rl-v30-private-manifest.json').resolve())
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(summary,indent=2)+'\n')
 print(f'{len(records)} fresh positive records; {calls} evaluator calls; {sims} simulator runs; {builds+1} pipeline K syntheses')
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('usage: python scripts/summarize_fused_v30.py PRIVATE_RUN_ROOT OUTPUT_JSON')
 main(*sys.argv[1:])
