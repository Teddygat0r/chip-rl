import copy,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from chip_rl.quality.induction import model,check
from chip_rl.quality.induction_audit import obligations
from chip_rl.quality.reach_replay import wave_values
from chip_rl.quality.spec import Config
from chip_rl.quality.rtl import design
class Induction(unittest.TestCase):
 def test_direct_predicate_and_explicit_initialization(self):
  s,h,m=model(design(Config('dot'),'shiftadaptive'),Config('dot'))
  self.assertIn('assign proof_ok=',s);self.assertNotIn('assert(',s)
  self.assertIn('rst=!started || reset_in',h);self.assertFalse(m['input_stability_assumption'])
 def test_concrete_link_has_no_symbolic_product_assumption(self):
  s,h,m=model(design(Config('dot'),'shiftadaptive'),Config('dot'),concrete=True)
  self.assertNotIn('assume(',s);self.assertIn('p=a*b;',s);self.assertIn('(&proof_link)',s);self.assertEqual(m['multiplier_cutpoints'],0)
 def test_candidate_assumptions_still_rejected(self):
  src=design(Config('dot'),'shiftadaptive').replace('endmodule','always @* assume(0);endmodule')
  with self.assertRaises(ValueError):model(src,Config('dot'))
 def test_harness_hierarchy_access_rejected(self):
  src=design(Config('dot'),'shiftadaptive').replace('endmodule','wire attack=formal_top.started;endmodule')
  with self.assertRaises(ValueError):model(src,Config('dot'))
 def test_unsupported_tensor_scope_rejected(self):
  c=Config('tensor',m=2,n=2)
  with self.assertRaises(ValueError):model(design(c,'shiftadaptive'),c)
 def test_mutant_base_case_is_not_induction_failure(self):
  from chip_rl.evaluate import Rejected
  with tempfile.TemporaryDirectory() as td:
   def fake(cmd,root,label,timeout):
    (root/'formal.log').write_text('SAT temporal induction proof finished - model found for base case: FAIL!');raise Rejected('failed')
   with patch('chip_rl.quality.induction.run',side_effect=fake):
    r=check(design(Config('dot'),'shiftadaptive'),Config('dot'),Path(td)/'case')
   self.assertEqual(r['status'],'base_case_counterexample')
 def test_unknown_success_does_not_count(self):
  with tempfile.TemporaryDirectory() as td,patch('chip_rl.quality.induction.run',return_value='SUCCESS!'):
   self.assertEqual(check(design(Config('dot'),'shiftadaptive'),Config('dot'),Path(td)/'case')['status'],'unproven')
 def test_wavejson_repeat_and_initial_padding(self):
  self.assertEqual(wave_values({'wave':'4=.=','data':['','10','11']}),[2,2,3])
  self.assertEqual(wave_values({'wave':'401.'}),[0,1,1])
 def make_records(self):
  common={'source_sha256':'abc','config':{'k':16},'case_count':3,'instrumented_sha256':'def','assumptions_enforced':True,'contradictory_harness_control':False,'initial_attributes_removed':True}
  return [{**common,'mode':'base','status':'reset_base_pass'},{**common,'mode':'coverage','status':'case_coverage_pass'}]+[{**common,'mode':'stepcase','step_case':i,'status':'transition_case_pass'} for i in range(3)]
 def test_partition_requires_all_cases(self):
  records=self.make_records();self.assertEqual(obligations(records)['status'],'partitioned_abstract_induction_complete')
  for bad in [records[:-1],records+[records[-1]]]:
   with self.assertRaises(ValueError):obligations(bad)
 def test_parameter_mix_with_same_source_is_rejected(self):
  records=self.make_records();records[-1]['config']={'k':4}
  with self.assertRaises(ValueError):obligations(records)
 def test_initialized_transition_and_vacuity_rejected(self):
  for change in [{'initial_attributes_removed':False},{'contradictory_harness_control':True},{'status':'unproven'}]:
   records=self.make_records();records[-1].update(change)
   with self.assertRaises(ValueError):obligations(records)
