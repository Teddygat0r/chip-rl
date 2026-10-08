import unittest
from chip_rl.softmax.rtl import design,CATALOG
from chip_rl.softmax.audit_cases import attack,OLD,NEW
from chip_rl.softmax.workloads import generate
from chip_rl.softmax.spec import shapes
from chip_rl.softmax.oracle import check,reference
class Audit(unittest.TestCase):
 def test_exhaustive_difference_and_endpoint_groups(self):
  w=generate(9,1,'audit');rows=[r for r in w['rows'] if r['kind']=='delta-sweep']
  self.assertEqual({r['logits'][0]-r['logits'][1] for r in rows},set(range(256)))
  self.assertTrue(all(r['mask']&511==3 for r in rows));self.assertGreater(len(w['rows']),750)
 def test_new_structures_are_disjoint(self):
  self.assertFalse(set(shapes('audit'))&set(sum([shapes(s) for s in ('development','heldout','reserve')],[])))
 def test_all_directed_rows_have_valid_nearest_oracle(self):
  for n in shapes('audit'):
   for r in generate(n,22,'audit')['rows']:
    values=[int(p*4096+__import__('decimal').Decimal('.5')) for p in reference(r['logits'],r['mask'],n)]
    check(r['logits'],r['mask'],n,sum(v<<(16*i) for i,v in enumerate(values)))
 def test_distinct_architectures_and_fault_sources(self):
  self.assertEqual(len({design(n) for n in CATALOG}),7)
  for label in OLD+NEW:self.assertNotIn(attack(label),{design(n) for n in CATALOG})

 def test_batches_preserve_rows_and_shift_pairs(self):
  from chip_rl.softmax.simulation import batches
  for n in (1,4,8,16):
   w=generate(n,22,'audit');parts=list(batches(n,w));self.assertEqual([r for p in parts for r in p['rows']],w['rows'])
   seen=set()
   for p in parts:
    self.assertLessEqual(len(p['rows']),448);groups={r['shift_group'] for r in p['rows'] if r['shift_group'] is not None};self.assertFalse(groups&seen);seen|=groups
   if n>1:self.assertTrue(any(len(p['rows'])>256 for p in parts))
