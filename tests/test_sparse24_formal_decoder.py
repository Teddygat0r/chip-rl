"""Pure manifest/extraction checks for the deployed sparse24 decoder proof."""
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
from chip_rl.sparse24.rtl import design,SELECT
from scripts import prove_sparse24_decoder_v34 as proof

class DecoderProofHarnessTests(unittest.TestCase):
 def test_extraction_binds_both_deployed_architectures(self):
  e=proof.extract()
  self.assertEqual(e['rtl_file_sha256'],proof.sha((proof.BASE/'chip_rl/sparse24/rtl.py').read_bytes()))
  self.assertEqual(e['serial_source_sha256'],proof.sha(design('serial')))
  self.assertEqual(e['pipeline_source_sha256'],proof.sha(design('pipeline')))
  self.assertIn(e['function'],SELECT)
  self.assertEqual(e['serial_activation'],'selected_activation(slot,index[0])')
  self.assertEqual(e['serial_weight'],'index[0] ? slot[47:40] : slot[39:32]')
  self.assertEqual(e['serial_guard'],'slot[50:48]<6')
  self.assertEqual(e['pipeline_guard'],'in_data[56*j+48+:3]<6')
  self.assertEqual(e['pipeline_w0'],'in_data[56*j+32+:8]')
  self.assertEqual(e['pipeline_w1'],'in_data[56*j+40+:8]')
 def test_harness_oracle_and_mutant(self):
  h=proof.harnesses(proof.extract())
  self.assertEqual(set(h),{'serial','pipeline','mutant'})
  self.assertIn('for(j=0;j<8;j=j+1)',h['pipeline'])
  masks=[f"3'd{s}:dense_mask=4'b{mask};" for s,mask in enumerate(('0011','0101','1001','0110','1010','1100'))]
  self.assertTrue(all(m in proof.ORACLE for m in masks))
  self.assertIn('default:dense_mask=4\'b0000;',proof.ORACLE)
  self.assertIn("3'd1:selected_activation=second ? slot[23:16] : slot[7:0];",h['serial'])
  self.assertIn("3'd1:selected_activation=second ? slot[31:24] : slot[7:0];",h['mutant'])
  self.assertEqual(h['serial'].replace("3'd1:selected_activation=second ? slot[23:16] : slot[7:0];",
    "3'd1:selected_activation=second ? slot[31:24] : slot[7:0];"),h['mutant'])
 def test_extraction_fails_closed_if_deployed_path_changes(self):
  actual=design
  with patch.object(proof,'design',side_effect=lambda label:actual(label).replace('slot[50:48]<6','slot[50:48]<=6') if label=='serial' else actual(label)):
   with self.assertRaisesRegex(ValueError,'serial MAC guard'):proof.extract()
  with patch.object(proof,'design',side_effect=lambda label:actual(label).replace('in_data[56*j+40+:8]','in_data[56*j+32+:8]') if label=='pipeline' else actual(label)):
   with self.assertRaisesRegex(ValueError,'elastic guarded product operands'):proof.extract()
 def test_solver_outcome_and_witness_decoding(self):
  self.assertEqual(proof.classify(0,'SAT proof finished - no model found: SUCCESS!',False),'proved')
  self.assertEqual(proof.classify(1,'ERROR: Called with -verify and proof did fail!',True),'counterexample')
  self.assertEqual(proof.classify(1,'ERROR: Called with -verify and proof did fail!',False),'unproven_error')
  self.assertEqual(proof.classify(1,'ERROR: parser failed',True),'unproven_error')
  slot=(1<<48)|(122<<40)|(255<<32)|(0<<24)|(128<<16)|(34<<8)
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'witness.vcd';p.write_text(f'b00001 v0\nb{slot:056b} v2\n')
   w=proof.witness_example(p)
   self.assertEqual((w['selector'],w['index'],w['activations'],w['weights']),(1,1,[0,34,-128,0],[-1,122]))
 def test_recorded_manifest_binds_current_source_and_harness(self):
  data=json.loads((proof.BASE/'evidence/v34/summary.json').read_text())
  self.assertEqual(data['proof_driver_sha256'],proof.sha(Path(proof.__file__).read_bytes()))
  extracted=proof.extract();h=proof.harnesses(extracted)
  for name in ('rtl_file_sha256','serial_source_sha256','pipeline_source_sha256'):
   self.assertEqual(data['source_sha256'][name],extracted[name])
  for name in ('serial','pipeline','mutant'):
   self.assertEqual(data['results'][name]['harness_sha256'],proof.sha(h[name]))
   self.assertNotIn('-seq',data['results'][name]['command'][-1])
  self.assertEqual(data['oracle_sha256'],proof.sha(proof.ORACLE))
  self.assertEqual(data['proof_invocations'],3)
  self.assertEqual([data['results'][name]['outcome'] for name in ('serial','pipeline','mutant')],
                   ['proved','proved','counterexample'])

if __name__=='__main__':unittest.main()
