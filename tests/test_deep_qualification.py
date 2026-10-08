import unittest,itertools
from chip_rl.qualification.oracles import codeword,decode_table8,ecc8,coalesce,Histogram
from chip_rl.expansion.spec import Config,cases
class IndependentQualification(unittest.TestCase):
 def test_complete_small_ecc_domain(self):
  table=decode_table8();self.assertEqual(len(table),3584)
  codes=[codeword(8,data)[0] for data in range(256)]
  for i,a in enumerate(codes):
   self.assertEqual(a.bit_count()%2,0)
   for b in codes[:i]:self.assertGreaterEqual((a^b).bit_count(),4)
  counts=[0,0,0]
  for received in range(8192):counts[(ecc8(received|(1<<32))>>48)&3]+=1
  self.assertEqual(counts,[256,3328,4608])
 def test_coalescing_partition_invariants(self):
  c=Config('coalesce',width=64,k=2)
  for groups in itertools.product(range(3),repeat=4):
   for mask in range(16):
    x=sum((g*64+i)<<(16*i) for i,g in enumerate(groups))|(mask<<128);y=coalesce(c,x);used=0;last=-1
    for j in range(y&15):
     members=(y>>(24+24*j))&255;base=(y>>(8+24*j))&65535
     self.assertTrue(members);self.assertFalse(used&members);used|=members
     leader=(members&-members).bit_length()-1;self.assertGreater(leader,last);last=leader
     for i in range(4):self.assertEqual(bool(members>>i&1),bool(mask>>i&1 and groups[i]*64==base))
    self.assertEqual(used,mask)
 def test_histogram_previous_values_and_wrap(self):
  c=Config('histogram',width=16);m=Histogram(c);x=(15<<32)|sum(255<<(48+8*i) for i in range(4))
  for t in range(193):
   y=m.step(x)
   for i in range(4):self.assertEqual((y>>(16*i))&65535,((4*t+i)*255)&65535)
   self.assertEqual((y>>64)&65535,((t+1)*1020)&65535)
  self.assertEqual(m.step(x|(1<<40))&65535,0)
 def test_host_bounds_and_long_histogram_band(self):
  self.assertEqual(Config('coalesce',width=64,k=1).lanes,2)
  for n in ('permute','histogram','ecc'):
   with self.assertRaises(ValueError):Config(n,k=1)
  long=[count for i,j,c,s,count in cases(Config('histogram'),88) if i==0 and j==1]
  self.assertTrue(2048<=long[0]<=2304)
if __name__=='__main__':unittest.main()

class ScenarioConstraints(unittest.TestCase):
 def test_correct_but_backlogged_candidate_is_ineligible(self):
  from chip_rl.qualification.objectives import assess
  base={'config':{'name':'coalesce'},'tested_correct':True,'epochs_sha256':'same','responses':1000,'active_cycles':2000,'maximum_offered_latency':16,'synthesis':{'cells':100}}
  slow={**base,'active_cycles':12000,'maximum_offered_latency':9000,'synthesis':{'cells':20}}
  self.assertEqual(assess(base,base)['reward'],1.)
  self.assertFalse(assess(slow,base)['eligible']);self.assertEqual(assess(slow,base)['reward'],0.)
  with self.assertRaises(ValueError):assess({**base,'epochs_sha256':'other'},base)

class ResetInterruptionCoverage(unittest.TestCase):
 def test_cross_product_and_reset_state_observation(self):
  from chip_rl.qualification.workloads import reset_epochs
  for name in ('ecc','coalesce','histogram'):
   c=Config(name);epochs=reset_epochs(c,12345)
   observed=set()
   for dirty,clean in zip(epochs[::2],epochs[1::2]):
    observed.add((clean['reset_valid'],clean['reset_ready'],dirty['cut'],dirty['hold']))
    self.assertFalse(clean['score']);self.assertFalse(dirty['score'])
    if name=='histogram':
     self.assertTrue(all(y==0 for x,y in clean['pairs']))
     queried={(x>>(128+8*i))&255 for x,y in clean['pairs'] for i in range(c.k)}
     self.assertEqual(queried,set(range(c.depth)))
   self.assertEqual(observed,set(itertools.product((0,1),(0,1),(1,2),range(10))))
 def test_reset_payloads_reproducible_and_seed_sensitive(self):
  from chip_rl.qualification.workloads import reset_epochs
  c=Config('ecc');a=reset_epochs(c,123);b=reset_epochs(c,456)
  self.assertEqual(a,reset_epochs(c,123));self.assertNotEqual(a,b)
