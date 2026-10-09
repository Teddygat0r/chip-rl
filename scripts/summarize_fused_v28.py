"""Summarize local v28 private run journals without publishing inputs or seeds."""
import json,sys
from pathlib import Path

FIELDS=('cells','logic_depth','transactions','workload_cycles','accepted_to_first_sum','maximum_accepted_to_first','offered_to_consumption_sum','maximum_offered_to_consumption','stream_cycles','stream_ii_numerator','stream_ii_denominator','workload_sha256')
def read(root,name):
 r=json.loads((root/name/'result.json').read_text())
 if not r['tested_correct'] or r['validation']!='rtl_and_mapped_exact_pass':raise ValueError('unvalidated '+name)
 return r

def measured(x):
 return {k:x[k] for k in FIELDS}|{'mean_accepted_to_first':x['accepted_to_first_sum']/x['transactions'],'mean_offered_to_consumption':x['offered_to_consumption_sum']/x['transactions'],'stream_initiation_interval':x['stream_ii_numerator']/x['stream_ii_denominator']}

def main(root,out):
 root=Path(root);out=Path(out);records=[]
 for k in (2,4,8):
  for arch in ('serial','parallel'):
   r=read(root,f'dev-k{k}-{arch}')
   records.append({'split':'development','K':k,'architecture':arch,'metrics':measured(r['candidate'])})
 for k in (1,2,4,8,16):
  r=read(root,f'heldout-k2-parallel' if k==2 else f'heldout-v2-k{k}-paired')
  for arch,key in (('serial','baseline'),('parallel','candidate')):
   records.append({'split':'heldout','K':k,'architecture':arch,'metrics':measured(r[key])})
 fingerprints={k:{r[k] for r in (read(root,'dev-k2-serial'),read(root,'heldout-v2-k16-paired'))} for k in ('tool_fingerprint','contract_sha256','recipe_sha256')}
 if len(fingerprints['tool_fingerprint'])!=1 or len(fingerprints['recipe_sha256'])!=2:raise ValueError('unexpected fingerprints')
 for name in ('ties_away','drop_on_retirement','reset_ignored'):
  r=json.loads((root/f'mutant-{name}'/'result.json').read_text())
  if r['tested_correct']:raise ValueError('mutant passed '+name)
 calls=len(list(root.glob('*/result.json')))+len(list(root.glob('api-traces/*/result.json')))
 simulation_runs=len(list(root.rglob('tool-logs/fused-*-simulation-*.log')))
 syntheses=len(list(root.rglob('tool-logs/fused-synthesis-*.log')))
 api=json.loads(next(root.glob('api-traces/*/result.json')).read_text())
 if not api['tested_correct']:raise ValueError('API smoke failed')
 summary={'task':'fused_dot_requant','version':'v28-experimental','reward':None,'reward_qualified':False,
  'validated_design_configurations':len(records),'development_design_configurations':6,'heldout_design_configurations':10,
  'mutants_rejected':['ties_away','drop_on_retirement','reset_ignored'],
  'evaluation_calls':calls,'simulator_runs':simulation_runs,'unique_synthesis_builds':syntheses,
  'initial_heldout_harness_false_rejections':8,'api_reset_smoke_passed':True,
  'formal_validations':0,'physical_validations':0,'unit_tests_passed':195,
  'tool_fingerprint':next(iter(fingerprints['tool_fingerprint'])),
  'recipe_sha256_development':read(root,'dev-k2-serial')['recipe_sha256'],
  'recipe_sha256_heldout_corrected':read(root,'heldout-v2-k16-paired')['recipe_sha256'],
  'private_artifact_root':str(root.resolve()),'records':records,
  'measurement_scope':'Icarus RTL and Yosys mapped replay; Yosys generic ABC cell count and logic-depth proxy; simulation cycles only, not routed timing or power'}
 if calls!=24 or simulation_runs>160 or len(records)!=16:raise ValueError('unexpected campaign size')
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(summary,indent=2)+'\n')
 print(f'{len(records)} validated design/configurations; {calls} evaluator calls; {simulation_runs} simulator runs; {syntheses} syntheses')
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('usage: python scripts/summarize_fused_v28.py PRIVATE_RUN_ROOT OUTPUT_JSON')
 main(*sys.argv[1:])
