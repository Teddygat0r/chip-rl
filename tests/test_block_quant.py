import io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from chip_rl.evaluate import Rejected,digest,sanitize
from chip_rl.block_quant.spec import Config,NS,SUPPORTED_NS,configurations,specification
from chip_rl.block_quant.oracle import expected,pack,quantized
from chip_rl.block_quant.rtl import CATALOG,design
from chip_rl.block_quant.workloads import generate
from chip_rl.block_quant.env import BlockQuantEnv
from chip_rl.block_quant.server import serve
from chip_rl.block_quant.evaluate import validate_metrics,verified_cache
from chip_rl.block_quant.arithmetic_check import selected
from chip_rl.block_quant.scoring import score_cases

class BlockQuantTests(unittest.TestCase):
 def test_exact_integer_boundaries(self):
  for peak,shift in ((0,0),(127,0),(128,1),(255,1),(256,2),(32768,9)):
   x=-32768 if peak==32768 else peak
   self.assertEqual(quantized((x,))[0],shift)
  self.assertEqual(quantized((129,)),(1,(64,)))  # +64.5 ties to even
  self.assertEqual(quantized((131,)),(1,(66,)))  # +65.5 ties to even
  self.assertEqual(quantized((-129,)),(1,(-64,)))
  self.assertEqual(quantized((-131,)),(1,(-66,)))
  self.assertEqual(quantized((255,)),(1,(127,)))  # +127.5 rounds then clamps
  self.assertEqual(quantized((-32768,256)),(9,(-64,0)))
  self.assertEqual(quantized((-32768,-256)),(9,(-64,0)))
 def test_ignored_input_and_zero_output(self):
  a=pack((255,-129),inactive=(32767,)*14,upper=2**256-1)
  b=pack((255,-129),inactive=(-32768,)*14,upper=0)
  self.assertEqual(expected(a,2),expected(b,2))
  self.assertEqual(expected(a,2)>>132,0)
  self.assertEqual((expected(a,2)>>16)&((1<<112)-1),0)
 def test_catalog_and_deterministic_workloads(self):
  self.assertEqual(CATALOG,('serial','parallel','chunked4'))
  for name in CATALOG:sanitize(design(name))
  for n in NS:
   self.assertEqual(Config(n).n,n)
   for split in ('development','heldout'):
    work=generate(n,12345,split)
    self.assertEqual(work,generate(n,12345,split))
    self.assertEqual(work['expected'],[expected(x,n) for x in work['inputs']])
    self.assertTrue({'zero','signed_extreme','exponent_boundary','tie_even','tie_odd',
                     'maximum_lane','ignored_fields_a','ignored_fields_b'}<=set(work['labels']))
    self.assertEqual(sum(label=='maximum_lane' for label in work['labels']),n)
    self.assertTrue(all(x>>132==0 and ((x>>128)&15)<=9 for x in work['expected']))
    self.assertEqual({(x>>128)&15 for x in work['expected']},set(range(10)))
    from chip_rl.block_quant.oracle import decode
    boundary={max(abs(x) for x in decode(word,n)) for word,label in zip(work['inputs'],work['labels'])
              if label=='exponent_boundary'}
    for s in range(1,10):self.assertTrue({(1<<(s+6))-1,1<<(s+6)}<=boundary)
  for n in (0,17,True,1.0):
   with self.assertRaises(ValueError):Config(n)
  self.assertEqual(specification(Config())['reward'],'balanced_area_cycle_proxy')
 def test_intermediate_lane_counts(self):
  self.assertEqual(SUPPORTED_NS,tuple(range(1,17)))
  self.assertEqual(NS,(1,2,4,8,16))
  for n in (3,5,6,7,9,10,11,12,13,14,15):
   self.assertEqual(Config(n).n,n)
   self.assertEqual(configurations('heldout',n),tuple(sorted(set(NS)|{n})))
   work=generate(n,12345,'heldout')
   self.assertEqual(work['expected'],[expected(x,n) for x in work['inputs']])
   self.assertEqual(sum(label=='maximum_lane' for label in work['labels']),n)
   self.assertEqual(specification(Config(n))['scored_configurations']['heldout'],NS)
   self.assertEqual(specification(Config(n))['measured_configurations'],configurations('heldout',n))
 def test_env_and_json_action_boundary(self):
  baseline={'tested_correct':True,'reward':0.,'reward_qualified':True,
            'service_qualified':True,'hard_constraints_passed':True}
  candidate={'tested_correct':True,'reward':0.2,'reward_qualified':True,
             'service_qualified':True,'hard_constraints_passed':True}
  with patch('chip_rl.block_quant.env.Evaluator') as evaluator:
   evaluator.return_value.evaluate.side_effect=[baseline,candidate]
   env=BlockQuantEnv(n=4,horizon=1,trusted_replay_seed=123)
   obs,_=env.reset();self.assertEqual(obs['evaluation']['reward'],0)
   with self.assertRaises(ValueError):env.step({'rtl':design('chunked4'),'N':16})
   obs,reward,_,truncated,info=env.step({'rtl':design('chunked4')})
   self.assertEqual(reward,0.2);self.assertTrue(truncated);self.assertTrue(info['reward_qualified'])
   self.assertEqual(evaluator.return_value.evaluate.call_count,2)
  with patch('chip_rl.block_quant.env.Evaluator') as evaluator:
   evaluator.return_value.evaluate.return_value=baseline
   requests=io.StringIO('{"op":"reset","N":16}\n{"op":"reset","seed":1}\n')
   out=io.StringIO();serve(requests,out,n=4,trusted_replay_seed=123)
   replies=[json.loads(line) for line in out.getvalue().splitlines()]
   self.assertFalse(replies[0]['ok']);self.assertTrue(replies[1]['ok'])
   self.assertEqual(evaluator.return_value.evaluate.call_count,1)
  for n in (0,17):
   with self.assertRaises(ValueError):BlockQuantEnv(n=n)
  with patch('chip_rl.block_quant.env.Evaluator') as evaluator:
   evaluator.return_value.evaluate.return_value=baseline|{'service_qualified':False}
   with self.assertRaises(RuntimeError):BlockQuantEnv(n=4).reset()
  with patch('chip_rl.block_quant.env.Evaluator') as evaluator:
   evaluator.return_value.evaluate.return_value=baseline|{'service_qualified':False}
   out=io.StringIO();serve(io.StringIO('{"op":"reset","seed":1}\n'),out,n=4)
   self.assertFalse(json.loads(out.getvalue())['ok'])
 def test_scoring_algebra_and_exact_gates(self):
  def metrics(n,cells=100,cycles=100,ii=None):
   return {'cells':cells,'workload_cycles':cycles,'stream_ii_numerator':31*(2*n+3 if ii is None else ii),
           'stream_ii_denominator':31,'rtl_mapped_checked':True,'arithmetic_rtl_mapped_checked':True,
           'arithmetic_vectors_checked':64}
  def case(n,**candidate):
   return {'N':n,'candidate_verified':True,'baseline_verified':True,
           'candidate':metrics(n,**candidate),'baseline':metrics(n)}
  equal=[case(n) for n in NS]
  result=score_cases(equal)
  self.assertTrue(result['service_qualified']);self.assertEqual(result['reward'],0)
  self.assertTrue(all(x['constraints_passed'] for x in result['scored_cases']))
  better=[case(n,cells=50,cycles=50,ii=1) for n in NS]
  self.assertAlmostEqual(score_cases(better)['reward'],0.5)
  boundary=[case(n) for n in NS]
  boundary[-1]=case(16,cells=400,cycles=100,ii=35)
  self.assertTrue(score_cases(boundary)['service_qualified'])
  for changed,reason in (({'cells':401},'area_ratio_at_most_4'),
                         ({'cycles':101},'completion_ratio_at_most_1'),
                         ({'ii':36},'stream_ii_at_most_2N_plus_3')):
   cases=[case(n) for n in NS];cases[-1]=case(16,**changed)
   result=score_cases(cases)
   self.assertFalse(result['service_qualified']);self.assertFalse(result['reward_qualified'])
   self.assertEqual(result['reward'],0)
   self.assertEqual(result['constraint_failures'],[{'N':16,'failed':[reason]}])
  # The observed v36 parallel N=16 is functionally verified yet exceeds 4x cells.
  cases=[case(n) for n in NS]
  cases[-1]={'N':16,'candidate_verified':True,'baseline_verified':True,
             'candidate':metrics(16,cells=9680,cycles=385,ii=1),
             'baseline':metrics(16,cells=2220,cycles=7377,ii=35)}
  result=score_cases(cases)
  self.assertFalse(result['service_qualified']);self.assertEqual(result['reward'],0)
  self.assertEqual(result['constraint_failures'],[{'N':16,'failed':['area_ratio_at_most_4']}])
 def test_scoring_rejects_missing_or_invalid_metrics(self):
  good={'N':1,'candidate_verified':True,'baseline_verified':True,
        'candidate':{'cells':100,'workload_cycles':100,'stream_ii_numerator':5,'stream_ii_denominator':1,
                     'rtl_mapped_checked':True,'arithmetic_rtl_mapped_checked':True,'arithmetic_vectors_checked':61},
        'baseline':{'cells':100,'workload_cycles':100,'stream_ii_numerator':5,'stream_ii_denominator':1,
                     'rtl_mapped_checked':True,'arithmetic_rtl_mapped_checked':True,'arithmetic_vectors_checked':61}}
  self.assertTrue(score_cases([good|{'N':3}])['service_qualified'])
  for changed in ({'N':17},{'N':True},{'baseline_verified':False},
                  {'candidate':good['candidate']|{'cells':float('nan')}},
                  {'baseline':good['baseline']|{'workload_cycles':0}},
                  {'candidate':good['candidate']|{'rtl_mapped_checked':False}}):
   with self.assertRaises(Rejected):score_cases([good|changed])
  with self.assertRaises(Rejected):score_cases([])
 def test_mismatched_verified_baseline_cache_fails_closed(self):
  work=generate(1,111,'development')
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'verified.json'
   path.write_text(json.dumps({'identity':{'source_sha256':'wrong'},'verified':True,'metrics':{}}))
   with self.assertRaises(Rejected):verified_cache(path,{'source_sha256':'expected'},work,1)
   path.write_text(json.dumps({'identity':{'source_sha256':'expected'},'verified':False,'metrics':{}}))
   with self.assertRaises(Rejected):verified_cache(path,{'source_sha256':'expected'},work,1)
 def test_reset_probe_is_a_fresh_verification_gate(self):
  work=generate(16,123,'development')
  key={'arithmetic_vector_sha256':digest(json.dumps(selected(work)))}
  flags=('rtl_mapped_checked','arithmetic_rtl_mapped_checked','reset_backpressure_checked',
         'long_stall_checked','reset_during_stall_checked','long_stall_output_seen',
         'reset_blocked_output_seen')
  metrics={name:True for name in flags}
  metrics.update(arithmetic_vectors_checked=len(selected(work)),
                 arithmetic_vector_sha256=key['arithmetic_vector_sha256'],
                 workload_sha256=work['sha256'],watchdog_sha256=work['watchdog_sha256'],
                 accepted_count=10,consumed_count=10,transactions=10,
                 service_opportunity_bound=96,stream_transactions=32,cells=100)
  self.assertIs(validate_metrics(metrics,key,work,16),metrics)
  metrics['reset_blocked_output_seen']=False
  with self.assertRaises(Rejected):validate_metrics(metrics,key,work,16)
