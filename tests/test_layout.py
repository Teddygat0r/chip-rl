import copy,io,json,random,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from chip_rl.layout.spec import Shape,Config,shapes
from chip_rl.layout.workloads import generate,oracle,queue_service,validate_mapping
from chip_rl.layout.evaluate import score
from chip_rl.layout.synthesis import inspect
from chip_rl.layout.env import LayoutEnv
from chip_rl.layout.server import serve
class Layout(unittest.TestCase):
 def test_full_mapping_bijection_required(self):
  s=Shape(8,8,8,8)
  for mapping in ([0]*64,list(range(63)),list(range(1,65))):
   with self.assertRaises(ValueError):validate_mapping(s,mapping)
 def test_disjoint_structural_splits(self):
  keys=[set((s.rows,s.cols,s.banks,s.lanes) for s in shapes(k)) for k in ('development','heldout','reserve')]
  self.assertFalse(keys[0]&keys[1] or keys[0]&keys[2] or keys[1]&keys[2])
 def test_independent_cycle_models_on_all_shapes(self):
  for split in ('development','heldout','reserve'):
   for s in shapes(split):
    for label in ('linear','xor','add'):
     mapping=[r*s.cols+(c if label=='linear' else c^(r&(s.banks-1)) if label=='xor' else c//s.banks*s.banks+(c+r)%s.banks) for r in range(s.rows) for c in range(s.cols)]
     qs=generate(s,1984,'diagonal',split);expected=oracle(s,mapping,qs)
     self.assertEqual([x['service_cycles'] for x in expected],[queue_service(s,mapping,q) for q in qs])
 def test_duplicate_stores_serialize_broadcast_reads(self):
  s=Shape(8,8,8,8);q={'coords':[(0,0)]*8,'mask':255,'write':True,'values':list(range(8)),'reset_before':True};read={**q,'write':False,'reset_before':False};r=oracle(s,list(range(64)),[q,read]);self.assertEqual(r[0]['service_cycles'],8);self.assertEqual(r[1]['service_cycles'],1);self.assertEqual(r[1]['expected'],[7]*8)
 def test_masks_reset_and_zero_request(self):
  s=Shape(8,8,8,8);q={'coords':[(0,0)]*8,'mask':0,'write':False,'values':[5]*8,'reset_before':True};r=oracle(s,list(range(64)),[q])[0];self.assertEqual(r,{'expected':[0]*8,'service_cycles':1})
 def test_seed_reproducible_but_changes_values(self):
  s=shapes()[0];a=generate(s,1,'transpose','development');self.assertEqual(a,generate(s,1,'transpose','development'));self.assertNotEqual(a,generate(s,2,'transpose','development'))
 def test_zero_cell_baseline_and_overhead_sensitivity(self):
  row={'candidate':{'cells':0,'service_cycles':100},'baseline':{'cells':0,'service_cycles':100}}
  self.assertEqual(score([row])['reward'],1);row['candidate']['cells']=32;self.assertLess(score([row])['reward'],1);row['candidate']['service_cycles']=40;self.assertGreater(score([row])['reward'],1)
 def test_service_gate(self):
  row={'candidate':{'cells':0,'service_cycles':201},'baseline':{'cells':0,'service_cycles':100}};self.assertEqual(score([row])['reward'],0)
 def test_stateful_and_undriven_netlists_rejected(self):
  from chip_rl.evaluate import Rejected
  ports={'row':{'direction':'input','bits':list(range(1,7))},'col':{'direction':'input','bits':list(range(7,13))},'addr':{'direction':'output','bits':['0']*10}}
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'netlist.json'
   for cell in ('$_DFF_P_','$memrd','$_DLATCH_P_'):
    p.write_text(json.dumps({'modules':{'candidate':{'ports':ports,'cells':{'x':{'type':cell}}}}}));
    with self.assertRaises(Rejected):inspect(td)
   bad=copy.deepcopy(ports);bad['addr']['bits'][0]='x';p.write_text(json.dumps({'modules':{'candidate':{'ports':bad,'cells':{}}}}))
   with self.assertRaises(Rejected):inspect(td)
 def test_constraints_not_action_fields(self):
  e=LayoutEnv();e.steps=0
  for action in ({'rtl':'x','banks':32},{'rtl':'x','split':'reserve'},{'rtl':'x','artifacts':'/tmp/x'},{'source':'x'}):
   with self.assertRaises(ValueError):e.step(action)
 def test_server_rejects_before_reset_and_overrides(self):
  inp=io.StringIO('\n'.join(json.dumps(x) for x in [{'op':'step','action':{'rtl':'x'}},{'op':'reset','task':'layout','split':'reserve'},{'op':'reset','task':'layout','artifacts':'/tmp/x'}])+'\n');out=io.StringIO();serve(inp,out);self.assertTrue(all(not json.loads(x)['ok'] for x in out.getvalue().splitlines()))
 def test_episode_seed_not_hidden_seed(self):
  with patch('chip_rl.layout.env.Evaluator.evaluate',return_value={'tested_correct':True,'reward':1}) as mock:
   e=LayoutEnv();e.reset(123);self.assertNotIn('replay_seed',mock.call_args.kwargs)

 def test_manual_sensitivity_divergence_rejected(self):
  from chip_rl.layout.synthesis import source_gate
  from chip_rl.layout.spec import HEADER
  from chip_rl.evaluate import Rejected
  for event in ('@(row)','@(row or col[0])','@(posedge row[0])'):
   with self.assertRaises(Rejected):source_gate(HEADER.replace('output [9:0]','output reg [9:0]')+'always '+event+' addr=row*COLS+col;endmodule')
  for event in ('@*',):
   source_gate(HEADER.replace('output [9:0]','output reg [9:0]')+'always '+event+' addr=row*COLS+col;endmodule')

  source_gate(HEADER.replace('output [9:0]','output reg [9:0]')+'always @(*) addr=row*COLS+col;endmodule')

 def test_normalization_does_not_allow_attributes_or_manual_lists(self):
  from chip_rl.layout.synthesis import source_gate
  from chip_rl.layout.audit_cases import correct,bad
  from chip_rl.evaluate import Rejected
  for label in ('wildcard','always_comb','function','column_major'):source_gate(correct(label))
  for source in (bad('attribute'),bad('manual_sensitivity'),correct('wildcard').replace('endmodule','(* keep *) wire x;endmodule')):
   with self.assertRaises(Rejected):source_gate(source)
 def test_reset_probe_reads_before_refill(self):
  from chip_rl.layout.verification import probes
  s=shapes()[0];qs=probes(s,1);answers=oracle(s,list(range(s.words)),qs)
  resets=[i for i,q in enumerate(qs) if q['reset_before']];self.assertEqual(len(resets),2);i=resets[1]
  self.assertFalse(qs[i]['write']);self.assertEqual(qs[i]['kind'],'probe-reset-zero')
  for q,r in zip(qs,answers):
   if q['kind']=='probe-reset-zero':self.assertEqual(r['expected'],[0]*s.lanes)
 def test_masked_word_overwrite_preserves_inactive_values(self):
  s=shapes()[0];coords=[(0,i) for i in range(s.lanes)];full=(1<<s.lanes)-1
  qs=[{'coords':coords,'mask':full,'write':True,'values':list(range(1,9)),'reset_before':True},{'coords':coords,'mask':0x55,'write':True,'values':[99]*8,'reset_before':False},{'coords':coords,'mask':full,'write':False,'values':[123]*8,'reset_before':False}]
  self.assertEqual(oracle(s,list(range(s.words)),qs)[-1]['expected'],[99,2,99,4,99,6,99,8])
 def test_verification_is_not_a_scoring_input(self):
  from chip_rl.layout.evaluate import score
  cases=[{'candidate':{'cells':3,'service_cycles':100},'baseline':{'cells':0,'service_cycles':200}}]
  before=score(cases);cases[0]['candidate']['verification_cycles']=1000000;self.assertEqual(before,score(cases))
 def test_engine_and_resource_overrides_are_not_actions(self):
  e=LayoutEnv();e.steps=0
  for key in ('engine_source','max_cells','ports','verification','split'):
   with self.assertRaises(ValueError):e.step({'rtl':'x',key:0})
