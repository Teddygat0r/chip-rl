"""Focused block-FOR oracle, workload, RTL-source, and fixed-score tests."""
import hashlib,unittest
from chip_rl.block_for.oracle import decode_input,decode_output,expected,pack_input
from chip_rl.block_for.rtl import design
from chip_rl.block_for.scoring import score_cases
from chip_rl.block_for.workloads import generate
from chip_rl.evaluate import Rejected,sanitize

class BlockForTest(unittest.TestCase):
 def test_directed_and_metamorphic(self):
  for n in (1,2,4,8,16):
   for split in ('development','heldout'):
    w=generate(n,123456,split)
    self.assertGreaterEqual(len(w['inputs']),32)
    self.assertEqual(w['watchdog_service_budget'],len(w['inputs'])*(6*n+80)+1)
    widths=set();spans=set()
    for x,y,label in zip(w['inputs'],w['expected'],w['labels']):
     self.assertEqual(decode_output(y,n),decode_input(x,n))
     self.assertEqual(expected(x^(((1<<512)-1)^((1<<(8*n))-1)),n),y)
     widths.add((y>>8)&15)
     values=decode_input(x,n)
     if label=='width_boundary':spans.add(max(values)-min(values))
     if label=='leading_zero_offset':self.assertEqual(values[0],min(values))
     if label=='trailing_zero_offset':self.assertEqual(values[-1],min(values))
    self.assertEqual(widths,set(range(9)) if n>1 else {0})
    if n>1:self.assertTrue({q for k in range(8) for q in ((1<<k)-1,1<<k,(1<<k)+1) if 1<=q<=255}.union({255})<=spans)
 def test_order_width_and_zero_filling(self):
  v=(3,4,6,3);y=expected(pack_input(v),4)
  self.assertEqual(y,3|(2<<8)|(1<<14)|(3<<16))
  for bad in (y|(1<<20),y|(9<<8),0|(1<<8),255|(1<<8)):
   with self.assertRaises(ValueError):decode_output(bad,4)
  self.assertEqual(expected(pack_input((7,7,7,7)),4),7)
  self.assertEqual(decode_output(7,4),(7,7,7,7))
 def test_reference_source(self):
  for arch in ('serial','chunked4','serial_shiftpack'):
   src=design(arch);sanitize(src)
   self.assertEqual(hashlib.sha256(src.encode()).hexdigest(),FROZEN[arch])
  shifted=design('serial_shiftpack')
  self.assertIn("acc<=(acc << width) | {120'b0,offset};",shifted)
  self.assertIn("assign out_data={116'b0,acc,width,base};",shifted)
  self.assertEqual(expected(pack_input((3,4,6,3)),4),3|(2<<8)|(1<<14)|(3<<16))
  self.assertEqual(expected(pack_input((7,7,7,7)),4),7)
 def test_scoring_completeness_and_gate_failure(self):
  def m(n,area=100,cycles=100,ii=None):
   ii=2*n+3 if ii is None else ii
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

FROZEN={'serial':'6e070e3d9868b0f7139950359ca9ca6ecf0a79cea22755c7226ee988828dc2f6','chunked4':'2303f60c81ed9dbdea4157612dcbe1f07409b3b1ed8be63e5b0e3559a8622dff','serial_shiftpack':'44257a380dd543c478981454a43a9b848ac6bbabae30f6d6e94576b7083322cb'}
if __name__=='__main__':unittest.main()
