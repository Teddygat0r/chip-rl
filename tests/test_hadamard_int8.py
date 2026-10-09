"""Focused exact arithmetic, format, frozen architecture, and gate checks."""
import hashlib,json,random,unittest
from pathlib import Path
from chip_rl.hadamard_int8.oracle import transform,expected,decode_input,decode_output,pack_input
from chip_rl.hadamard_int8.workloads import generate,butterfly_oracle
from chip_rl.hadamard_int8.rtl import design
from chip_rl.hadamard_int8.spec import Config,NS,configurations,specification
from chip_rl.hadamard_int8.scoring import score_cases
from chip_rl.evaluate import Rejected,sanitize

FROZEN=json.loads((Path(__file__).parents[1]/'chip_rl/hadamard_int8/frozen_sources.json').read_text())

def b(n):return (n//2)*(n.bit_length()-1)

class HadamardInt8Test(unittest.TestCase):
 def test_direct_oracle_matches_independent_butterflies(self):
  r=random.Random(20261009)
  for n in NS:
   for _ in range(1000):
    values=tuple(r.randrange(-128,128) for _ in range(n))
    self.assertEqual(transform(values),butterfly_oracle(values))
    word=pack_input(values,r.getrandbits(512))
    self.assertEqual(decode_input(word,n),values)
    self.assertEqual(decode_output(expected(word,n),n),transform(values))
    self.assertEqual(expected(word,n)>>(16*n),0)
    self.assertEqual(expected(word^(((1<<512)-1)^((1<<(8*n))-1)),n),expected(word,n))
 def test_directed_identities_and_bounds(self):
  for n in NS:
   for c in (-128,-1,0,1,127):
    self.assertEqual(transform((c,)*n),(n*c,)+(0,)*(n-1))
   for c in (-127,-1,1,127):
    for j in range(n):
     v=tuple(-c if (i&j).bit_count()&1 else c for i in range(n))
     self.assertEqual(transform(v),tuple(n*c if k==j else 0 for k in range(n)))
   self.assertEqual(transform((-128,)*n)[0],-128*n)
  v=tuple(127 if i%2==0 else -128 for i in range(16))
  self.assertEqual(transform(v)[1],2040)
  self.assertEqual(transform((-128,)*16)[0],-2048)
 def test_workload_and_protocol_budget(self):
  for n in NS:
   for split in ('development','heldout'):
    w=generate(n,17,split)
    self.assertEqual(w['watchdog_service_budget'],len(w['inputs'])*(2*b(n)+32)+1)
    self.assertTrue({'zero','constant','basis','impulse','alternating','ramp','random','ignored_a','ignored_b'}<=set(w['labels']))
    self.assertGreaterEqual(len(w['inputs']),70)
    for x,y in zip(w['inputs'],w['expected']):self.assertEqual(expected(x,n),y)
    self.assertEqual(w['labels'].count('basis'),4*n)
 def test_sources_and_contract(self):
  self.assertEqual(configurations('development'),NS)
  for n in NS:self.assertEqual(Config(n).n,n)
  for bad in (0,3,32,True):
   with self.assertRaises(ValueError):Config(bad)
  self.assertIn('popcount(i AND j)',specification(Config(4))['protocol'])
  for name in ('serial_butterfly','stage_parallel'):
   source=design(name);sanitize(source)
   self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),FROZEN[name])
   self.assertIn('WORK:begin',source)
   self.assertIn('if(N==1)',source)
 def test_scoring_all_five_unique_and_gates(self):
  def m(n,area=100,cycles=100,ii=None):
   return {'rtl_mapped_checked':True,'exact_rtl_mapped_checked':True,'exact_vectors_checked':32,
    'cells':area,'workload_cycles':cycles,'stream_ii_numerator':31*(b(n)+2 if ii is None else ii),'stream_ii_denominator':31}
  cases=[{'N':n,'candidate_verified':True,'baseline_verified':True,'candidate':m(n),'baseline':m(n)} for n in NS]
  self.assertTrue(score_cases(cases)['reward_qualified'])
  self.assertEqual(score_cases(cases)['reward'],0)
  for bad in (cases[:-1],cases[:-1]+[cases[0]]):
   with self.assertRaises(Rejected):score_cases(bad)
  for kind,value in (('area',401),('cycles',101),('ii',b(16)+7)):
   changed=[dict(c) for c in cases]
   changed[-1]['candidate']=m(16,**{kind:value})
   self.assertFalse(score_cases(changed)['reward_qualified'])

if __name__=='__main__':unittest.main()
