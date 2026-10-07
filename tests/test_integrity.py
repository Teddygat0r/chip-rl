import unittest,zlib
from chip_rl.expansion.spec import Config
from chip_rl.expansion.integrity_models import ECC,CRC,FreeList,encode,positions
from chip_rl.expansion.integrity_traffic import commands
from chip_rl.tasks import bits
class IntegrityModels(unittest.TestCase):
 def test_ecc_exhaustive_eight_bit_faults(self):
  c=Config('ecc',width=8);m=ECC(c);h,_=positions(8)
  for data in range(256):
   code=encode(8,data);self.assertEqual(m.step(data),code|(data<<32))
   self.assertEqual(m.step(code|(1<<32)),code|(data<<32))
   for i in range(h+1):
    self.assertEqual(m.step((code^(1<<i))|(1<<32)),code|(data<<32)|(1<<48))
    for j in range(i):self.assertEqual(m.step((code^(1<<i)^(1<<j))|(1<<32)),2<<48)
 def test_crc_known_vector_and_packet_errors(self):
  m=CRC(Config('crc',width=8));self.assertEqual(m.step(0),1<<33)
  for i,byte in enumerate(b'123456789'):
   out=m.step(byte|(int(i==0)<<32)|(int(i==8)<<33)|(123<<48))
  self.assertEqual(out,0xcbf43926|(1<<32)|(123<<48)|(9<<64))
  self.assertEqual(m.step(0),1<<33)
  m=CRC(Config('crc',width=16));out=m.step(0x0201|(1<<32));self.assertEqual(out&0xffffffff,zlib.crc32(b'\1\2'))
 def test_freelist_conservation_simultaneous_free_allocate(self):
  c=Config('freelist',depth=8,k=2);m=FreeList(c)
  self.assertEqual(m.step(2),2|(6<<8)|(3<<16)|(0x100<<64))
  self.assertEqual(m.step(2|(2<<16)),2|(5<<8)|(6<<16)|(0x201<<64))
  self.assertEqual(m.step(1|(128<<16)),8|(5<<8)) # freeing an already-free ID is rejected atomically
  self.assertEqual(m.step(3),8|(5<<8))
  self.assertEqual(m.step(8),8<<8)
 def test_generated_ownership_monitor(self):
  for d in (8,16,24,32):
   for k in (2,3,4):
    for seed in range(5):self.assertGreater(len(commands(Config('freelist',depth=d,k=k),seed,256)),256)
 def test_task_defaults_and_structural_parameters(self):
  self.assertEqual(Config('freelist').depth,32);self.assertEqual(Config('retire').depth,8)
  self.assertEqual(positions(12)[0],17)
  with self.assertRaises(ValueError):Config('crc',width=12)
 def test_work_units_and_frozen_constraints(self):
  from chip_rl.expansion.evaluate import work
  from chip_rl.expansion.spec import specification,cases
  c=Config('freelist');self.assertEqual(work(c,8|(255<<16),32<<8),0)
  self.assertEqual(work(c,1|(3<<16),1),3)
  self.assertEqual(specification(c)['mapped_logic_depth_limit'],160)
  self.assertEqual({cc.depth for _,_,cc,_,_ in cases(c,17)},{8,32})
 def test_mutants_change_source(self):
  from chip_rl.expansion.rtl import design,mutants
  for n in ('ecc','crc','freelist'):
   c=Config(n);src=design(c)
   for m in mutants(n):self.assertNotEqual(src,design(c,mutant=m),(n,m))
if __name__=='__main__':unittest.main()
