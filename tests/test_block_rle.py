"""Focused exact block-RLE tests; hardware smoke is kept separate."""
import hashlib,unittest
from chip_rl.block_rle.oracle import decode_input,decode_output,expected,pack_input,runs
from chip_rl.block_rle.rtl import design
from chip_rl.block_rle.scoring import score_cases
from chip_rl.block_rle.workloads import generate
from chip_rl.evaluate import Rejected,sanitize

class BlockRleTest(unittest.TestCase):
 def test_directed_and_metamorphic(self):
  for n in (1,2,4,8,16):
   for split in ('development','heldout'):
    w=generate(n,123456,split)
    self.assertGreaterEqual(len(w['inputs']),32)
    self.assertEqual(w['watchdog_service_budget'],len(w['inputs'])*(4*n+64)+1)
    for x,y in zip(w['inputs'],w['expected']):
     self.assertEqual(decode_output(y),decode_input(x,n))
     self.assertEqual(sum(length for _,length in runs(decode_input(x,n))),n)
     self.assertEqual(expected(x^(((1<<512)-1)^((1<<(8*n))-1)),n),y)
 def test_order_and_zero_filling(self):
  v=(65,65,66,65)
  y=expected(pack_input(v),4)
  self.assertEqual(y,(65|(2<<8))|((66|(1<<8))<<13)|((65|(1<<8))<<26)|(3<<208))
  with self.assertRaises(ValueError):decode_output(y|(1<<213))
  for invalid in (
   y|(1<<39), # unused run slots
   y|(1<<213), # high reserved bit
   0, # zero count
   31<<208, # oversized count
   (65|(0<<8))|(1<<208), # zero run length
   (65|(1<<8))|((65|(1<<8))<<13)|(2<<208), # unmerged equal neighbors
   (65|(16<<8))|((66|(1<<8))<<13)|(2<<208), # aggregate length > 16
  ):
   with self.assertRaises(ValueError):decode_output(invalid)
 def test_reference_source(self):
  for arch in ('serial','chunked4'):
   src=design(arch)
   sanitize(src)
   self.assertEqual(hashlib.sha256(src.encode()).hexdigest(),FROZEN[arch])
 def test_scoring_completeness_and_gate_failure(self):
  def m(n,area=100,cycles=100,ii=None):
   ii=n+2 if ii is None else ii
   return {'rtl_mapped_checked':True,'exact_rtl_mapped_checked':True,'exact_vectors_checked':32,
    'cells':area,'workload_cycles':cycles,'stream_ii_numerator':31*ii,'stream_ii_denominator':31}
  cases=[{'N':n,'candidate_verified':True,'baseline_verified':True,'candidate':m(n),'baseline':m(n)} for n in (1,2,4,8,16)]
  self.assertEqual(score_cases(cases)['reward'],0)
  self.assertTrue(score_cases(cases)['reward_qualified'])
  for bad in (cases[:-1],cases[:-1]+[cases[0]]):
   with self.assertRaises(Rejected):score_cases(bad)
  cases[0]['candidate']=m(1,ii=100)
  result=score_cases(cases)
  self.assertEqual(result['reward'],0)
  self.assertFalse(result['reward_qualified'])

FROZEN={'serial':'5768a73b8ad3e0b8cab1592f0227f94765cfde3ef55828eeca2049f63f3e87b9','chunked4':'35e4ff8f63b14f5679f4ddee44ca67a1f2865c571ef0f59ff3a3f56c25c75366'}
if __name__=='__main__':unittest.main()
