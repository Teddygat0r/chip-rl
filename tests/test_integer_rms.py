import io,json,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from chip_rl.evaluate import sanitize,Rejected,digest
from chip_rl.integer_rms.spec import Config,NS,specification
from chip_rl.integer_rms.oracle import expected,pack,decode,normalized
from chip_rl.integer_rms.rtl import CATALOG,design
from chip_rl.integer_rms.workloads import generate
from chip_rl.integer_rms.arithmetic_check import selected
from chip_rl.integer_rms.scoring import score_cases
from chip_rl.integer_rms.env import IntegerRmsEnv
from chip_rl.integer_rms.server import serve

class IntegerRmsTests(unittest.TestCase):
 def test_oracle_exact(self):
  self.assertEqual(normalized((0,)),(0,1,(0,)))
  self.assertEqual(normalized((1,)),(1,1,(256,)))
  self.assertEqual(normalized((-32768,)),(32768**2,32768,(-256,)))
  self.assertEqual(normalized((1024,1,0,0))[1:],(512,(512,0,0,0)))
  self.assertEqual(normalized((1024,3,0,0))[1:],(512,(512,2,0,0)))
  self.assertEqual(normalized((1024,-3,0,0))[1:],(512,(512,-2,0,0)))
  self.assertEqual(normalized((1024,-1,0,0))[1:],(512,(512,0,0,0)))
  for n in NS:
   a=tuple([0]*(n-1)+[-32768]);w=pack(a,inactive=(32767,)*(16-n),upper=2**256-1)
   z=pack(a,inactive=(-32768,)*(16-n),upper=0)
   self.assertEqual(expected(w,n),expected(z,n))
   self.assertEqual(decode(w,n),a)
   self.assertEqual(expected(w,n)>>(16*n),0)
  for bad in (0,3,17,True,1.0):
   with self.assertRaises(ValueError):Config(bad)
 def test_directed_witnesses_and_controls(self):
  # Intentionally faulty arithmetic controls are host-only, not replacements for the oracle.
  def no_epsilon(a):
   s=sum(x*x for x in a);d=math.isqrt(s//len(a));return d
  def narrow_abs(a):return abs(a[0])&32767
  def truncate(a):
   s=sum(x*x for x in a);d=math.isqrt(s//len(a)+1)
   return tuple(((-1 if x<0 else 1)*(abs(x)*256//d)) for x in a)
  self.assertNotEqual(no_epsilon((0,)),normalized((0,))[1])
  self.assertNotEqual(narrow_abs((-32768,)),abs(-32768))
  self.assertNotEqual(truncate((1024,3,0,0)),normalized((1024,3,0,0))[2])
  for n in NS:
   w=generate(n,7,'development')
   self.assertEqual(w,generate(n,7,'development'))
   self.assertEqual(w['expected'],[expected(x,n) for x in w['inputs']])
   self.assertGreaterEqual(len(selected(w)),30)
   labels=set(w['labels'])
   self.assertTrue({'all_zero','equal_magnitude','single_position','mixed_sign','ignored_a','ignored_b','sqrt_near_square'}<=labels)
   self.assertEqual(w['labels'].count('single_position'),4*n)
   self.assertIn('sqrt_exact_square',labels)
   self.assertIn('sqrt_above_square',labels)
   if n>1:self.assertIn('sqrt_below_square',labels)
   else:self.assertNotIn('sqrt_below_square',labels)
   if n>1:
    self.assertIn('floor_division',labels)
    self.assertEqual(w['labels'].count('half_tie_even'),2)
    self.assertEqual(w['labels'].count('half_tie_odd'),2)
    anchors={abs(decode(word,n)[0]) for word,label in zip(w['inputs'],w['labels']) if label.startswith('half_tie')}
    self.assertEqual(anchors,{ {2:725,4:1024,8:1449,16:2048}[n] })
   else:self.assertFalse(any(x.startswith('half_tie') for x in labels))
   for word,label in zip(w['inputs'],w['labels']):
    if label.startswith('half_tie'):
     lanes=decode(word,n);d=normalized(lanes)[1]
     q,rem=divmod(abs(lanes[1])*256,d)
     self.assertEqual(2*rem,d)
     self.assertEqual(label,'half_tie_even' if q%2==0 else 'half_tie_odd')
 def test_source_and_contract(self):
  self.assertEqual(CATALOG,('serial','chunked4','serial_comb_root'))
  frozen=json.loads((Path(__file__).resolve().parents[1]/'chip_rl/integer_rms/frozen_sources.json').read_text())
  for name in CATALOG:sanitize(design(name))
  for name,sha in frozen.items():self.assertEqual(digest(design(name)),sha)
  new=design('serial_comb_root')
  self.assertIn('for(k=0;k<16;k=k+1)',new)
  self.assertIn('root<=isqrt32_exact(mean_plus_one)',new)
  self.assertNotIn('   SQRT:begin',new)
  self.assertEqual(specification(Config())['scored_configurations']['development'],NS)
  self.assertIn('not floating-point',specification(Config())['protocol'])
 def test_scoring(self):
  def m(n,a=100,c=100,ii=None):return {'cells':a,'workload_cycles':c,'stream_ii_numerator':31*(2*n+24 if ii is None else ii),'stream_ii_denominator':31,'rtl_mapped_checked':True,'arithmetic_rtl_mapped_checked':True,'arithmetic_vectors_checked':30}
  def cases(n=16,a=100,c=100,ii=None):return [{'N':x,'candidate_verified':True,'baseline_verified':True,'candidate':m(x,a if x==n else 100,c if x==n else 100,ii if x==n else None),'baseline':m(x)} for x in NS]
  self.assertEqual(score_cases(cases())['reward'],0)
  with self.assertRaises(Rejected):score_cases(cases()[:-1])
  duplicate=cases();duplicate[-1]=duplicate[0]
  with self.assertRaises(Rejected):score_cases(duplicate)
  self.assertTrue(score_cases(cases(a=400))['reward_qualified'])
  for kw in ({'a':401},{'c':101},{'ii':57}):
   r=score_cases(cases(**kw));self.assertFalse(r['reward_qualified']);self.assertEqual(r['reward'],0)
 def test_json_source_only(self):
  baseline={'tested_correct':True,'reward':0.,'reward_qualified':True,'service_qualified':True,'hard_constraints_passed':True}
  with patch('chip_rl.integer_rms.env.Evaluator') as q:
   q.return_value.evaluate.return_value=baseline
   o=io.StringIO();serve(io.StringIO('{"op":"reset","N":16}\n{"op":"reset","seed":1}\n'),o,n=4,trusted_replay_seed=1)
   ans=[json.loads(x) for x in o.getvalue().splitlines()]
   self.assertFalse(ans[0]['ok']);self.assertTrue(ans[1]['ok'])
