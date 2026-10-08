import unittest
from chip_rl.softmax.oracle import check
from chip_rl.softmax.simulation import parse_trace,batches
from chip_rl.softmax.workloads import generate,continuous
from chip_rl.evaluate import Rejected
class Review(unittest.TestCase):
 def test_packed_integer_width(self):
  p=sum(256<<(16*i) for i in range(16))
  for x in (p+(1<<256),p-(1<<256),True,1.0):
   with self.assertRaises(ValueError):check([0]*16,65535,16,x)
 def test_tie_rule_not_silently_relaxed(self):
  for vs in ([272,240]+[256]*14,[272,272,240,240]+[256]*12,[271]+[256]*15):
   with self.assertRaisesRegex(ValueError,'equal logits'):check([0]*16,65535,16,sum(v<<(16*i) for i,v in enumerate(vs)))
 def test_strict_trace(self):
  z='0'*64;good=f'CANCEL_RESULT {z}\nOUT 0 {z}\nSOFTMAX_PASS 1 2 1 1\nAFTER_RESET_RESULT {z}\nDRAIN_PASS\n'
  self.assertEqual(parse_trace(good,1,100)[1]['transactions'],1)
  self.assertEqual(parse_trace(good+'rtl-tb.sv:47: $finish called at 500 (1s)\n',1,100)[1]['transactions'],1)
  bad=[good.replace('OUT 0 '+z,'OUT 0 '+z+'\nOUT 0 '+z),good.replace('OUT 0 '+z,'OUT 0 1'+z),good.replace('DRAIN_PASS','junkDRAIN_PASSjunk'),good.replace('SOFTMAX_PASS 1','SOFTMAX_PASS 9'),good.replace('OUT 0 '+z+'\n',''),good+'OUT x z\n','SOFTMAX_PASS 1 2 1 1\nDRAIN_PASS\n']
  for s in bad:
   with self.assertRaises(Rejected):parse_trace(s,1,100)
 def test_review_masks_differences_and_groups(self):
  w=generate(16,23,'review');rs=[r for r in w['rows'] if r['kind']=='signed-difference'];self.assertEqual(len(w['rows']),3601)
  deltas=set()
  for r in rs:
   lanes=[i for i in range(16) if r['mask']>>i&1];deltas.add(r['logits'][lanes[0]]-r['logits'][lanes[1]])
  self.assertEqual(deltas,set(range(-255,256)));self.assertEqual({r['mask'].bit_count() for r in w['rows']},set(range(17)))
  seen=set()
  for b in batches(16,w):
   groups={r['shift_group'] for r in b['rows'] if r['shift_group'] is not None};self.assertFalse(seen&groups);seen|=groups
 def test_continuous_history_lengths_and_activity(self):
  for n in (2,4,16):
   for count in (449,512,1024):
    w=continuous(n,23,count);self.assertEqual(len(w['rows']),count);self.assertTrue(w['rows'][-1]['mask']&((1<<n)-1))
    if n<=4:self.assertTrue(all(r['mask']&((1<<n)-1) for r in w['rows']))
  self.assertTrue(all(r['mask']==65535 for r in continuous(16,23,1024,True)['rows']))
