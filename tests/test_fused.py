import unittest,io,json
from chip_rl.fused.oracle import expected,pack
from chip_rl.fused.rtl import design,CATALOG
from chip_rl.fused.spec import Config,configurations,specification
from chip_rl.fused.workloads import generate
from chip_rl.fused.simulation import parse_trace
from chip_rl.fused.env import FusedEnv
from chip_rl.fused.server import serve
from chip_rl.fused.scoring import score_cases
from chip_rl.evaluate import sanitize,Rejected

Z=[0]*16
class FusedTests(unittest.TestCase):
 def test_hand_computed_arithmetic(self):
  def result(a=Z,b=Z,bias=0,scale=1,shift=0,zp=0,k=1):return expected(pack(a,b,bias,scale,shift,zp),k)
  for bias,want in ((1,0),(3,2),(5,2),(-1,0),(-3,-2),(-5,-2)):
   self.assertEqual(result(bias=bias,shift=1),want&0xffffffff)
  a=[2]+[0]*15;b=[3]+[0]*15
  self.assertEqual(result(a,b,bias=-1,shift=1,zp=-3),0xffffffff)
  self.assertEqual(result(bias=200,zp=-128),72)
  self.assertEqual(result(bias=-200,zp=127),(-73)&0xffffffff)
  self.assertEqual(result(bias=2**31-1,scale=65535,shift=47),1)
  self.assertEqual(result(bias=-2**31,scale=65535,shift=47),0xffffffff)
  self.assertEqual(result(bias=2**31-1,scale=65535,shift=0),127)
  self.assertEqual(result(bias=-2**31,scale=65535,shift=0),0xffffff80)
  self.assertEqual(result(bias=1234,scale=0,zp=-7),0xfffffff9)
  self.assertEqual(result(bias=32768,shift=15),1)
  self.assertEqual(result(bias=2**31-1,shift=31),1)
  self.assertEqual(result(bias=2**31-1,shift=47),0)
 def test_dot_width_and_unused(self):
  aa=[-128]*16;bb=[-128]*16
  self.assertEqual(expected(pack(aa,bb,0,1,15,0),16),8)
  self.assertEqual(expected(pack(aa,bb,2**31-1,1,31,0),16),1)
  first=pack([1]+[2]*15,[3]+[4]*15,5,1,0,0)
  altered=pack([1]+[-128]*15,[3]+[127]*15,5,1,0,0,(1<<194)-1)
  self.assertEqual(expected(first,1),8)
  self.assertEqual(expected(first,1),expected(altered,1))
  with self.assertRaises(ValueError):expected(first|(48<<304),1)
 def test_catalog_and_workloads(self):
  self.assertEqual(CATALOG,('serial','parallel','pipeline'))
  self.assertEqual(len(set(map(design,CATALOG))),3)
  for name in CATALOG:sanitize(design(name))
  self.assertEqual(configurations('development'),(2,4,8))
  self.assertEqual(configurations('heldout'),(1,2,4,8,16))
  for k in configurations('heldout'):
   for split in ('development','heldout'):
    w=generate(k,199,split)
    self.assertEqual(len(w['inputs']),len(w['expected']))
    self.assertEqual(w['expected'],[expected(x,k) for x in w['inputs']])
    self.assertEqual(w,generate(k,199,split))
    self.assertEqual(w['watchdog_service_budget'],len(w['inputs'])*(k+64)+1)
    self.assertEqual(sum(w['ready'][w['last_release']:]),w['watchdog_service_budget'])
    self.assertEqual(w['ready'][-1],1)
  self.assertEqual(specification(Config())['reward_policy']['hard_gates']['area_ratio_at_most'],4)
 def test_trace_fails_closed(self):
  trace='LONG_STALL_PASS 257 1\nRESET_STALL_PASS 1\nOUT 0 00000001\nSCORED_PASS 1 5 2 2 3 3\nCOUNTERS 1 1 1 1 2 3 3 2 2\nSAT_PASS 32 40 0 31\nFUSED_PASS\n'
  self.assertEqual(parse_trace(trace,1,100,68)[0],[1])
  for bad in (trace.replace('OUT 0','OUT 1'),trace.replace('SCORED_PASS 1','SCORED_PASS 2'),trace.replace('SAT_PASS 32','SAT_PASS 31'),trace+'FUSED_PASS\n',trace.replace('FUSED_PASS\n',''),trace.replace('COUNTERS 1 1','COUNTERS 0 1'),trace.replace('RESET_STALL_PASS 1\n',''),trace.replace(' 2 2\nSAT_PASS',' 2 69\nSAT_PASS')):
   with self.assertRaises(Rejected):parse_trace(bad,1,100,68)
 def test_action_scope(self):
  env=FusedEnv()
  with self.assertRaises(RuntimeError):env.step({'rtl':design()})
  env.steps=0
  with self.assertRaises(ValueError):env.step({'rtl':design(),'K':16})
  for k in (0,3,17):
   with self.assertRaises(ValueError):Config(k)
  class FakeJudge:
   def evaluate(self,*_args,**_kwargs):return {'tested_correct':True,'reward':.25,'reward_qualified':True}
  env.q=FakeJudge();obs,reward,terminated,truncated,info=env.step({'rtl':design('parallel')})
  self.assertEqual(reward,.25);self.assertTrue(info['reward_qualified'])
  self.assertTrue(obs['evaluation']['tested_correct'])
  stream=io.StringIO('{"op":"reset","k":16}\n');out=io.StringIO();serve(stream,out)
  self.assertFalse(json.loads(out.getvalue())['ok'])
 def test_balanced_score_algebra(self):
  def row(k,ca,cc,ii):return {'K':k,'baseline_verified':True,'candidate_verified':True,
   'baseline':{'cells':100,'workload_cycles':100,'stream_ii_numerator':k+4,'stream_ii_denominator':1},
   'candidate':{'cells':ca,'workload_cycles':cc,'stream_ii_numerator':ii,'stream_ii_denominator':1}}
  base=score_cases([row(4,100,100,8)])
  self.assertTrue(base['reward_qualified']);self.assertEqual(base['reward'],0)
  fast=score_cases([row(4,50,50,1)])
  self.assertTrue(fast['reward_qualified']);self.assertAlmostEqual(fast['reward'],.5)
  two=score_cases([row(4,50,50,1),row(8,100,100,12)])
  self.assertAlmostEqual(two['reward'],1-2**-.5)
  boundary=score_cases([row(4,400,100,8)])
  self.assertTrue(boundary['reward_qualified']);self.assertEqual(boundary['reward'],0)
 def test_balanced_score_gates_and_invalid_metrics(self):
  def row(cells=100,cycles=100,ii=8):return {'K':4,'baseline_verified':True,'candidate_verified':True,
   'baseline':{'cells':100,'workload_cycles':100,'stream_ii_numerator':8,'stream_ii_denominator':1},
   'candidate':{'cells':cells,'workload_cycles':cycles,'stream_ii_numerator':ii,'stream_ii_denominator':1}}
  for case,failed in ((row(cells=401),'area_ratio_at_most_4'),(row(cycles=101),'completion_ratio_at_most_1'),(row(ii=9),'stream_ii_at_most_K_plus_4')):
   result=score_cases([case]);self.assertFalse(result['reward_qualified']);self.assertEqual(result['reward'],0)
   self.assertIn(failed,result['constraint_failures'][0]['failed'])
  for field in ('cells','workload_cycles','stream_ii_numerator','stream_ii_denominator'):
   for bad in (None,0,-1,True,float('nan'),float('inf'),float('-inf'),'100'):
    case=row();case['candidate'][field]=bad
    with self.assertRaises(Rejected):score_cases([case])
  for mutate in (lambda x:x.update(baseline_verified=False),lambda x:x.pop('baseline'),lambda x:x['baseline'].update(cells=0),lambda x:x.update(candidate_verified=False)):
   case=row();mutate(case)
   with self.assertRaises(Rejected):score_cases([case])
  with self.assertRaises(Rejected):score_cases([])
if __name__=='__main__':unittest.main()
