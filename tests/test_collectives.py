import unittest
from itertools import product
from chip_rl.expansion.spec import Config
from chip_rl.expansion.models import machine
from chip_rl.expansion.collective_models import scan,topk,Histogram
from chip_rl.expansion.collective_traffic import commands
from chip_rl.tasks import bits
class CollectiveModels(unittest.TestCase):
 def test_signed_seed_segment_exclusive_and_mask(self):
  c=Config('scan',width=8,k=2)
  x=255|(2<<16)|(3<<32)|(4<<48)|(15<<128)|(1<<138)|(10<<160)
  self.assertEqual([bits(scan(c,x),32*i,32) for i in range(4)],[9,11,3,7])
  self.assertEqual([bits(scan(c,x|(1<<144)),32*i,32) for i in range(4)],[10,9,0,3])
  x=(x&~(1<<130))|(1<<144)
  self.assertEqual([bits(scan(c,x),32*i,32) for i in range(4)],[10,9,0,11])
 def test_stable_topk_exhaustive_small_alphabet(self):
  c=Config('topk',width=8,k=2)
  for vals in product((-128,-1,0,127),repeat=4):
   for mask in range(16):
    for quota in (0,1,2,7):
     x=sum((v&255)<<(16*i) for i,v in enumerate(vals))|(mask<<128)|(quota<<136);y=topk(c,x)
     ids=[bits(y,24+24*j,8) for j in range(y&15)]
     self.assertEqual(len(ids),min(quota,2,mask.bit_count()));self.assertEqual(len(ids),len(set(ids)))
     for j,i in enumerate(ids):
      self.assertTrue(mask>>i&1);self.assertEqual(bits(y,8+24*j,16),vals[i]&65535)
      if j:self.assertGreater((vals[ids[j-1]],-ids[j-1]),(vals[i],-i))
     if ids:
      for i in range(4):
       if mask>>i&1 and i not in ids:self.assertLess((vals[i],-i),(vals[ids[-1]],-ids[-1]))
 def test_histogram_collision_wrap_clear_invalid_and_query(self):
  c=Config('histogram',depth=8,width=8,k=2);m=Histogram(c)
  x=(3<<32)|(250<<48)|(10<<56)
  y=m.step(x);self.assertEqual(bits(y,0,16),0);self.assertEqual(bits(y,16,16),250);self.assertEqual(bits(y,64,16),4)
  self.assertEqual(bits(m.step(x|(1<<40)),64,16),4)
  y=m.step(255|(1<<32)|(1<<48));self.assertEqual(bits(y,132,4),1);self.assertEqual(bits(y,64,16),4)
 def test_all_models_and_generated_conservation(self):
  for n in ('permute','coalesce','ecc','crc','freelist','scan','topk','histogram'):
   c=Config(n);m=machine(c);self.assertIsInstance(m.step(0),int)
  for d in (8,16,24,32):
   c=Config('histogram',depth=d,width=12,k=3);m=machine(c)
   for x in commands(c,917,256):self.assertLess(m.step(x),1<<256)
 def test_mutants_are_distinct(self):
  from chip_rl.expansion.rtl import design,mutants
  for n in ('scan','topk','histogram'):
   c=Config(n)
   for label in mutants(n):self.assertNotEqual(design(c),design(c,mutant=label),(n,label))
if __name__=='__main__':unittest.main()
