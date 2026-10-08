import unittest
from chip_rl.memory.oracles import Memory,PageTables
from chip_rl.memory.spec import Config
from chip_rl.memory.workloads import generate
from chip_rl.memory.rtl import design,CATALOG
from chip_rl.memory.mutants import bad,CATALOG as MUTANTS
class MemoryContracts(unittest.TestCase):
 def test_page_walk_matches_independent_flat_mapping(self):
  for seed in (1,77):
   p=PageTables(seed)
   for g in range(4):
    for vpn in range(256):
     for aux in range(16):
      address=vpn*256+(vpn*17)%256
      self.assertEqual(p.translate(address,aux,g),p.flat_translate(address,aux,g))
 def test_directed_permission_asid_invalidation(self):
  p=PageTables(123)
  self.assertNotEqual(p.translate(7,0,0),p.translate(7,1,0))
  self.assertNotEqual(p.translate(7,0,0),p.translate(7,0,1))
  self.assertEqual(p.translate(256,0,0),(0,2));self.assertEqual(p.translate(512,8,0),(0,1))
 def test_word_order_and_private_variation(self):
  m=Memory(1);n=Memory(2)
  self.assertNotEqual(m.load(0),n.load(0))
  for i in range(20):self.assertEqual(m.load(i),(m.lines[i//4]>>(32*(i%4)))&0xffffffff)
 def test_strict_configuration(self):
  for kw in ({'entries':True},{'entries':3},{'max_cycles':20001},{'max_cells':30001}):
   with self.assertRaises(ValueError):Config('mshr',**kw)
  self.assertEqual(Config('tlb',entries=6).entries,6)
 def test_replayable_workload_and_nonempty_mutations(self):
  for n in ('mshr','tlb'):
   c=Config(n);self.assertEqual(generate(c,1),generate(c,1));self.assertNotEqual(generate(c,1)['epochs'],generate(c,2)['epochs'])
   self.assertEqual(len({design(c,a) for a in CATALOG[n]}),2)
   for fault in MUTANTS[n]:self.assertNotEqual(bad(c,fault),design(c))
