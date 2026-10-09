import io,json,unittest,tempfile
from pathlib import Path
from chip_rl.sparse24.oracle import expected,pack
from chip_rl.sparse24.rtl import design,CATALOG
from chip_rl.sparse24.spec import Config,PAIRS,configurations,specification
from chip_rl.sparse24.workloads import generate
from chip_rl.sparse24.simulation import parse_trace
from chip_rl.sparse24.env import Sparse24Env
from chip_rl.sparse24.server import serve
from chip_rl.sparse24.scoring import score_cases
from chip_rl.sparse24.decoder_check import vectors
from chip_rl.sparse24.evaluate import verified_cache
from chip_rl.evaluate import sanitize,Rejected

ZERO=((0,0,0,0),(0,0),6,0)
def slots(first=ZERO):return [first]+[ZERO]*7
class Sparse24Tests(unittest.TestCase):
 def test_hand_selector_table_and_reserved_zero(self):
  a=(-12,7,31,-5);w=(3,-2)
  self.assertEqual(PAIRS,((0,1),(0,2),(0,3),(1,2),(1,3),(2,3)))
  for selector,want in enumerate((-50,-98,-26,-41,31,103,0,0)):
   x=pack(slots((a,w,selector,31)),0,1,0,0,3)
   self.assertEqual(expected(x,1),want&0xffffffff)
  for selector in (6,7):
   x=pack(slots(((-128,127,-127,126),(127,-128),selector,0)),11,1,0,-3)
   self.assertEqual(expected(x,1),8)
 def test_signed_rounding_scale_clamp_and_width(self):
  for bias,want in ((1,0),(3,2),(5,2),(-1,0),(-3,-2),(-5,-2)):
   self.assertEqual(expected(pack(slots(),bias,1,1,0),1),want&0xffffffff)
  self.assertEqual(expected(pack(slots(),123456,0,0,-7),1),0xfffffff9)
  self.assertEqual(expected(pack(slots(),2**31-1,65535,47,0),1),1)
  self.assertEqual(expected(pack(slots(),-2**31,65535,47,0),1),0xffffffff)
  self.assertEqual(expected(pack(slots(),2**31-1,65535,0,0),1),127)
  self.assertEqual(expected(pack(slots(),-2**31,65535,0,0),1),0xffffff80)
  with self.assertRaises(ValueError):expected(pack(slots(),0,1,0,0)|(48<<496),1)
 def test_ignored_bits_and_group_permutation(self):
  first=((2,3,5,7),(3,-2),1,0);other=((-1,4,6,8),(-3,2),4,0)
  x=pack([first,other]+[ZERO]*6,11,1,0,0)
  y=pack([other,first]+[ZERO]*6,11,1,0,0,3)
  self.assertEqual(expected(x,2),expected(y,2))
  changed=[(first[0],first[1],first[2],31)]+[((127,-128,11,-12),(127,-128),5,31)]*7
  self.assertEqual(expected(pack(slots(first),11,1,0,0),1),expected(pack(changed,11,1,0,0,3),1))
 def test_catalog_workloads_and_replay(self):
  self.assertEqual(CATALOG,('serial','pipeline'))
  for name in CATALOG:sanitize(design(name))
  self.assertEqual(configurations('development'),(1,2,4));self.assertEqual(configurations('heldout'),(3,5,6,7))
  self.assertEqual(specification(Config())['reward'],'balanced_area_cycle_proxy')
  self.assertEqual(specification(Config(8))['scored_configurations']['heldout'],(3,5,6,7,8))
  for g in range(1,9):
   for split in ('development','heldout'):
    w=generate(g,123,split)
    self.assertEqual(w,generate(g,123,split))
    self.assertEqual(len(w['inputs']),len(w['expected']))
    self.assertEqual(w['expected'],[expected(x,g) for x in w['inputs']])
    self.assertEqual(sum(w['ready'][w['last_release']:]),w['watchdog_service_budget'])
    for selector in range(8):
     for group in range(g):self.assertIn(f'selector_{selector}_group_{group}',w['labels'])
    for i,label in enumerate(w['labels'][:-1]):
     if label.endswith('_a') and w['labels'][i+1]==label[:-2]+'_b':
      self.assertEqual(w['expected'][i],w['expected'][i+1])
 def test_trace_and_action_boundary(self):
  trace='LONG_STALL_PASS 257 1\nRESET_STALL_PASS 1\nOUT 0 00000001\nSCORED_PASS 1 5 2 2 3 3\nCOUNTERS 1 1 1 1 2 3 3 2 2\nSAT_PASS 32 40 0 31\nSPARSE24_PASS\n'
  self.assertEqual(parse_trace(trace,1,100,65)[0],[1])
  for bad in (trace.replace('OUT 0','OUT 1'),trace.replace('COUNTERS 1 1','COUNTERS 0 1'),trace.replace('SPARSE24_PASS\n',''),trace.replace('RESET_STALL_PASS 1\n','')):
   with self.assertRaises(Rejected):parse_trace(bad,1,100,65)
  env=Sparse24Env()
  with self.assertRaises(RuntimeError):env.step({'rtl':design()})
  env.steps=0
  with self.assertRaises(ValueError):env.step({'rtl':design(),'G':8})
  class FakeJudge:
   def evaluate(self,*_args,**_kwargs):return {'tested_correct':True,'reward':0.25,'reward_qualified':True,'hard_constraints_passed':True}
  env.q=FakeJudge();obs,reward,_,_,info=env.step({'rtl':design('pipeline')})
  self.assertEqual(reward,0.25);self.assertTrue(info['reward_qualified'])
  self.assertEqual(obs['evaluation']['reward'],0.25)
  inp=io.StringIO('{"op":"reset","g":8}\n');out=io.StringIO();serve(inp,out)
  self.assertFalse(json.loads(out.getvalue())['ok'])
  for g in (0,9,True,1.0):
   with self.assertRaises(ValueError):Config(g)
  for g in (0,9):
   with self.assertRaises(ValueError):Sparse24Env(g=g)
   invalid=io.StringIO('{"op":"reset","seed":1}\n');response=io.StringIO();serve(invalid,response,g=g)
   self.assertFalse(json.loads(response.getvalue())['ok'])
  for g in range(1,9):self.assertEqual(Config(g).g,g)
 def test_scalar_decoder_vectors(self):
  for g in range(1,9):
   commands,outputs=vectors(g)
   self.assertEqual(len(commands),24*g)
   self.assertEqual(outputs,[expected(x,g) for x in commands])
   for group in range(g):
    for selector in range(8):
     i=24*group+3*selector
     self.assertEqual((commands[i]>>(56*group+48))&7,selector)
     if selector>=6:self.assertEqual(outputs[i:i+3],[0]*3)
     else:
      a=(-11,5,19,-7);first,second=PAIRS[selector]
      want=[2*a[first],-3*a[second],-4*a[first]+3*a[second]]
      self.assertEqual(outputs[i:i+3],[x&0xffffffff for x in want])
 def test_balanced_proxy_and_gates(self):
  def case(g,ca,ba,cc,bc,ii):
   def m(cells,cycles,stream):return {'cells':cells,'workload_cycles':cycles,'stream_ii_numerator':stream,
    'stream_ii_denominator':1,'rtl_mapped_checked':True,'decoder_rtl_mapped_checked':True,'decoder_vectors_checked':24*g}
   return {'G':g,'candidate_verified':True,'baseline_verified':True,'candidate':m(ca,cc,ii),'baseline':m(ba,bc,2*g+4)}
  baseline=[case(g,100,100,200,200,2*g+4) for g in range(1,9)]
  self.assertEqual(score_cases(baseline)['reward'],0)
  self.assertTrue(score_cases(baseline)['reward_qualified'])
  better=[case(g,50,100,100,200,1) for g in range(1,9)]
  self.assertAlmostEqual(score_cases(better)['reward'],0.5)
  boundary=case(1,400,100,200,200,6)
  self.assertTrue(score_cases([boundary])['reward_qualified'])
  self.assertEqual(score_cases([boundary])['reward'],0)
  for bad in (case(1,401,100,100,200,1),case(1,50,100,201,200,1),case(1,50,100,100,200,7)):
   result=score_cases([bad]);self.assertFalse(result['reward_qualified']);self.assertEqual(result['reward'],0)
  for bad in (case(1,0,100,100,200,1),case(1,50,0,100,200,1),case(1,50,100,0,200,1)):
   with self.assertRaises(Rejected):score_cases([bad])
  missing=case(1,50,100,100,200,1);missing['baseline_verified']=False
  with self.assertRaises(Rejected):score_cases([missing])
  for key in ('rtl_mapped_checked','decoder_rtl_mapped_checked'):
   unverified=case(1,50,100,100,200,1);unverified['baseline'][key]=False
   with self.assertRaises(Rejected):score_cases([unverified])
  wrong_count=case(1,50,100,100,200,1);wrong_count['candidate']['decoder_vectors_checked']=23
  with self.assertRaises(Rejected):score_cases([wrong_count])
 def test_verified_cache_identity_and_workload(self):
  identity={'source_sha256':'a','G':1,'decoder_vector_sha256':'d'}
  work={'sha256':'w','watchdog_sha256':'s'}
  m={'cells':100,'workload_cycles':200,'stream_ii_numerator':6,'stream_ii_denominator':1,
     'rtl_mapped_checked':True,'decoder_rtl_mapped_checked':True,'decoder_vectors_checked':24,
     'workload_sha256':'w','watchdog_sha256':'s','decoder_vector_sha256':'d'}
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'cache.json'
   def write(i=identity,v=True,metrics=m):p.write_text(json.dumps({'identity':i,'verified':v,'metrics':metrics}))
   write();self.assertEqual(verified_cache(p,identity,1,work,'baseline'),m)
   write(v=False)
   with self.assertRaises(Rejected):verified_cache(p,identity,1,work,'baseline')
   write(i=identity|{'G':2})
   with self.assertRaises(Rejected):verified_cache(p,identity,1,work,'baseline')
   write(metrics=m|{'workload_sha256':'different'})
   with self.assertRaises(Rejected):verified_cache(p,identity,1,work,'baseline')
   write(metrics=m|{'decoder_rtl_mapped_checked':False})
   with self.assertRaises(Rejected):verified_cache(p,identity,1,work,'baseline')
if __name__=='__main__':unittest.main()
