"""Trusted-host audit of the fixed v18 refinement chain; performs no SAT calls."""
import argparse,json,re
from pathlib import Path
from chip_rl.evaluate import digest
from chip_rl.quality.induction_audit import audit_partition
from chip_rl.quality.refinement import wrapper,union_states
p=argparse.ArgumentParser();p.add_argument('--artifacts',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();w=a.artifacts
models=w/'chip-rl-v18-models';metas=[]
for kind in ('original','concrete','abstract'):
 d=models/kind;m=json.loads((d/'metadata.json').read_text());metas.append(m)
 assert m.get('negative_control') is None and m['config']['k']==16 and m['config']['m']==m['config']['n']==1
 for filename,key in [('candidate.sv','model_sha256'),('formal.sv','harness_sha256'),('transition.json','transition_sha256')]:assert digest((d/filename).read_text())==m[key]
 raw=json.loads((d/'raw.json').read_text())['modules']['formal_top'];t=json.loads((d/'transition.json').read_text())['modules'][m['module']]
 qd={}
 for cell in raw['cells'].values():
  if cell['type']=='$dff':
   assert int(cell['parameters']['CLK_POLARITY'],2)==1 and cell['connections']['CLK']==raw['ports']['clk']['bits']
   assert len(cell['connections']['Q'])==len(cell['connections']['D'])
   for q,n in zip(cell['connections']['Q'],cell['connections']['D']):assert q not in qd;qd[q]=n
 assert t['ports']['state']['bits']==sorted(qd) and t['ports']['next_state']['bits']==[qd[q] for q in sorted(qd)]
 assert not any(re.search('ff|latch|mem|assert|assume|cover|check',c['type'],re.I) for c in t['cells'].values())
 assert not any('init' in n.get('attributes',{}) for n in t['netnames'].values())
 expected={n:c for n,c in raw['cells'].items() if c['type'] not in ('$dff','$assume','$assert','$cover')};assert expected==t['cells']
 for alias,idx in m['aliases'].items():
  name,bit=alias.rsplit(':',1);assert raw['netnames'][name]['bits'][int(bit)]==sorted(qd)[idx]
 if kind!='abstract':assert not m['removed_formal_cells']
 else:assert m['removed_formal_cells']==['$assume']*32
 if kind!='original':assert m['aliases']['started:0']==m['aliases']['dut.proof_started:0']
 muls=[c for c in raw['cells'].values() if c['type']=='$mul']
 for c in muls:
  v={k:int(x,2) for k,x in c['parameters'].items()};assert v=={'A_SIGNED':1,'B_SIGNED':1,'A_WIDTH':8,'B_WIDTH':8,'Y_WIDTH':16}
# Prior model identity, reset base, exhaustive transition partition, phase witnesses.
prior=audit_partition(w/'chip-rl-v17-partition',[w/'chip-rl-v17-replays/3',w/'chip-rl-v17-replays/4'])
assert prior['instrumented_sha256']==metas[2]['model_sha256']
assert (models/'abstract/formal.sv').read_bytes()==(w/'chip-rl-v17-partition/0-base/formal.sv').read_bytes()
assert all(m['source_sha256']==prior['source_sha256'] and m['config']==prior['config'] for m in metas)
# Compare init restrictions in the abstract/concrete state mapping.
mapping,aliases,n=union_states(metas[1:]);initial=[]
for m in metas[1:]:
 raw=json.loads((models/m['kind']/'raw.json').read_text())['modules']['formal_top'];bits={}
 for name,net in raw['netnames'].items():
  if 'init' in net.get('attributes',{}):
   for i,b in enumerate(reversed(net['attributes']['init'])):
    if b in '01':bits[mapping[(m['kind'],m['aliases'][f'{name}:{i}'])]]=b
 initial.append(bits)
assert initial[0]==initial[1]
checks=[(w/'chip-rl-v18-probe',[models/'original',models/'concrete'],'noninterference',None),(w/'chip-rl-v18-reset',[models/'concrete'],'capture',0)]
checks += [(w/f'chip-rl-v18-cases/capture-{i}',[models/'concrete'],'capture',i) for i in range(1,5)]
checks += [(w/f'chip-rl-v18-cases/equivalence-{i}',[models/'abstract',models/'concrete'],'equivalence',i) for i in range(7)]
for d,roots,mode,case in checks:
 r=json.loads((d/'result.json').read_text());h,meta=wrapper(roots,mode,case)
 assert r['status']=='combinational_refinement_pass' and (d/'miter.sv').read_text()==h
 assert 'SAT proof finished - no model found: SUCCESS!' in (d/'proof.log').read_text()
 assert '-set-assumes' not in (d/'proof.ys').read_text()
 for i,root in enumerate(roots):assert (d/f'transition-{i}.json').read_bytes()==(root/'transition.json').read_bytes()
 tree=json.loads((d/'miter.json').read_text());assert not any(re.search('ff|latch|mem|assert|assume|cover|check',c['type'],re.I) for m in tree['modules'].values() for c in m['cells'].values())
 if mode=='capture' and case==0:assert r['binding_count']==0 and r['unconditional_reset_establishment']
# Non-reset relation cases cover every reachable busy/valid/input combination.
for busy in (0,1):
 for ov in (0,1):
  if busy and ov:continue
  for valid in (0,1):assert (not busy and not ov and valid) or not valid or (busy and not ov) or (not busy and ov)
negative=[]
for name in ('product_capture','operand_capture'):
 d=w/'chip-rl-v18-negative'/name;r=json.loads((d/'result.json').read_text());assert r['status']=='counterexample' and (d/'witness.json').exists();negative.append(name)
prod=w/'chip-rl-v17-product-link/signed';pr=json.loads((prod/'result.json').read_text());assert pr['status']=='bounded_pass' and pr['kind']=='signed_product_range_linkage'
assert (prod/'formal.sv').read_text()=="module formal_top(input signed [7:0] a,b);wire signed [15:0] p=a*b;always @* begin assert(p>=-16256);assert(p<=16384);end endmodule"
assert 'SAT proof finished - no model found: SUCCESS!' in (prod/'formal.log').read_text()
assert '-prove-asserts' in (prod/'formal.ys').read_text()
# Report distinguishes auditable local composition from independent proof review.
r={'status':'local_compositional_refinement_checks_complete','scope':'fixed shiftadaptive dot K16 M=N=1, first edge synchronous reset, arbitrary later synchronous reset and output backpressure','source_sha256':prior['source_sha256'],'config':prior['config'],'accepted_obligations':len(checks),'negative_controls_rejected':negative,'prior_abstract_induction':prior,'raw_dff_mapping_checked':True,'signed_multipliers_checked':True,'initial_state_mapping_checked':True,'capture_case_coverage_checked':True,'independent_proof_review':False,'single_monolithic_concrete_proof':False,'mapped_gate_equivalence':False,'physical_verified':False,'trusted_boundary':'Yosys elaboration/SAT, Python D/Q extraction, structural substitution and composition argument; not an independent certificate checker'}
a.output.write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
