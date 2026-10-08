"""Trusted-host checks for a complete, parameter-bound partitioned induction bundle."""
import json
from pathlib import Path
from ..evaluate import digest
from .reach_replay import wave_values

def obligations(records):
 if not records:raise ValueError('missing obligations')
 base=records[0];identity=(base['source_sha256'],base['config'],base['case_count'],base['instrumented_sha256'])
 for r in records:
  if (r['source_sha256'],r['config'],r['case_count'],r['instrumented_sha256'])!=identity:raise ValueError('mixed source, parameters or invariant')
  if r.get('contradictory_harness_control') or not r.get('assumptions_enforced'):raise ValueError('invalid assumptions')
 groups={m:[r for r in records if r['mode']==m] for m in ('base','coverage','stepcase')}
 if len(groups['base'])!=1 or groups['base'][0]['status']!='reset_base_pass':raise ValueError('reset base missing')
 if len(groups['coverage'])!=1 or groups['coverage'][0]['status']!='case_coverage_pass':raise ValueError('case coverage missing')
 steps=groups['stepcase']
 if sorted(r['step_case'] for r in steps)!=list(range(base['case_count'])):raise ValueError('case hole or duplicate')
 if any(r['status']!='transition_case_pass' or not r['initial_attributes_removed'] for r in steps):raise ValueError('unproven or initialized transition')
 if len(records)!=2+base['case_count']:raise ValueError('unexpected obligation')
 return {'status':'partitioned_abstract_induction_complete','source_sha256':base['source_sha256'],'config':base['config'],'case_count':base['case_count'],'instrumented_sha256':base['instrumented_sha256'],'concrete_composition_proved':False}

def audit_partition(root,replays):
 root=Path(root);records=[]
 for p in sorted(root.glob('*/result.json')):
  r=json.loads(p.read_text())
  if r['mode']=='reach':continue
  d=p.parent
  if digest((d/'original.sv').read_text())!=r['source_sha256'] or digest((d/'candidate.sv').read_text())!=r['instrumented_sha256']:raise ValueError('source hash mismatch')
  if f".K({r['config']['k']})" not in (d/'formal.sv').read_text():raise ValueError('parameter binding')
  script=(d/'formal.ys').read_text();log=(d/'formal.log').read_text()
  if '-set-assumes' not in script or 'SAT proof finished - no model found: SUCCESS!' not in log:raise ValueError('proof evidence missing')
  if r['mode'] in ('coverage','stepcase'):
   prepared=json.loads((d/'prepared.json').read_text())
   if any('init' in n.get('attributes',{}) for m in prepared['modules'].values() for n in m['netnames'].values()):raise ValueError('initial state still restricted')
  records.append(r)
 result=obligations(records)
 reaches=list(root.glob('*-reach/result.json'))
 if len(reaches)!=1:raise ValueError('one phase witness required')
 r=json.loads(reaches[0].read_text());d=reaches[0].parent
 if r['status']!='reachable_witness' or not r['phase_coverage_required'] or r['source_sha256']!=result['source_sha256'] or r['config']!=result['config']:raise ValueError('mismatched reachability')
 reach_bound=r['reach_bound']
 signals={s['name']:wave_values(s) for s in json.loads((d/'witness.json').read_text())['signal']}
 if signals['proof_phase_seen'][-1]!=2**result['case_count']-1 or signals['proof_goals'][-1]!=255:raise ValueError('uncovered phase/event')
 for path in replays:
  path=Path(path);r=json.loads((path/'result.json').read_text())
  if r['status']!='witness_replay_pass' or not r['phase_mask_checked'] or r['source_sha256']!=result['source_sha256']:raise ValueError('replay evidence')
  if f".K({result['config']['k']})" not in (path/'tb.sv').read_text() or 'PASS ' not in (path/'simulation.log').read_text():raise ValueError('replay binding')
 if not replays:raise ValueError('concrete replay required')
 result.update(phase_reach_bound=reach_bound,phase_witness_verified=True,concrete_replays=len(replays),independent_evaluation=False)
 return result
