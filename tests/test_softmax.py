import unittest,random,io,json
from decimal import Decimal,localcontext,ROUND_FLOOR
from unittest.mock import patch
from chip_rl.softmax.oracle import reference,check
from chip_rl.softmax.spec import Config,shapes
from chip_rl.softmax.workloads import generate
from chip_rl.softmax.env import SoftmaxEnv
from chip_rl.softmax.server import serve
class Softmax(unittest.TestCase):
 def packed(self,values):return sum(v<<(16*i) for i,v in enumerate(values))
 def test_reference_equal_masks_and_single(self):
  self.assertEqual(reference([0]*16,15,4)[:4],[Decimal('.25')]*4)
  self.assertEqual(reference([127]*16,0,8),[Decimal(0)]*16)
  self.assertEqual(reference([-128]*16,1<<3,8)[3],1)
 def test_reference_precision_independently_recomputed(self):
  xs=[-128,-31,0,1,63,127]+[0]*10;p=reference(xs,63,6)
  with localcontext() as ctx:
   ctx.prec=120;t=[(Decimal(x)/16).exp() for x in xs[:6]];q=[v/sum(t) for v in t]
   self.assertTrue(all(abs(a-b)<Decimal('1e-70') for a,b in zip(p,q)))
 def test_floor_reference_is_valid_on_all_shapes(self):
  for n in (3,4,5,7,8,12,16):
   w=generate(n,210021,'heldout')
   for row in w['rows']:
    values=[int(p*4096) for p in reference(row['logits'],row['mask'],n)]
    check(row['logits'],row['mask'],n,self.packed(values))
 def test_wrong_uniform_approximation_rejected(self):
  with self.assertRaises(ValueError):check([127]+[-128]*15,15,4,self.packed([1024]*4))
 def test_masked_unused_and_overflow_rejected(self):
  for vals,mask in [([4096,1],1),([5000],1),([0]*4+[1],15)]:
   with self.assertRaises(ValueError):check([0]*16,mask,4,self.packed(vals))
 def test_shift_reference_and_order(self):
  xs=[-32,-16,0,16]+[0]*12;p=reference(xs,15,4);q=reference([v+32 for v in xs],15,4)
  self.assertTrue(all(abs(a-b)<Decimal('1e-70') for a,b in zip(p,q)));self.assertEqual(p[:4],sorted(p[:4]))
 def test_no_contract_or_oracle_override(self):
  e=SoftmaxEnv();e.steps=0
  for key in ('absolute_error_limit','oracle','split','replay_seed','artifacts','max_cells','N'):
   with self.assertRaises(ValueError):e.step({'rtl':'x',key:0})
 def test_disjoint_shapes_reproducible_workloads(self):
  groups=[set(shapes(s)) for s in ('development','heldout','reserve')];self.assertFalse(groups[0]&groups[1] or groups[0]&groups[2] or groups[1]&groups[2]);self.assertEqual(generate(4,1,'development'),generate(4,1,'development'));self.assertNotEqual(generate(4,1,'development')['rows'],generate(4,2,'development')['rows'])
 def test_episode_seed_does_not_select_private_workload(self):
  with patch('chip_rl.softmax.env.Evaluator.evaluate',return_value={'tested_correct':True,'reward':1}) as p:
   SoftmaxEnv().reset(21);self.assertNotIn('replay_seed',p.call_args.kwargs)
 def test_json_boundary_rejects_overrides(self):
  inp=io.StringIO('\n'.join(json.dumps(q) for q in [{'op':'step','action':{'rtl':'x'}},{'op':'reset','task':'softmax','N':1},{'op':'reset','task':'softmax','absolute_error_limit':1}])+'\n');out=io.StringIO();serve(inp,out);self.assertTrue(all(not json.loads(x)['ok'] for x in out.getvalue().splitlines()))
