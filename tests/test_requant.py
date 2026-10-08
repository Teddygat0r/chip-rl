import unittest
from chip_rl.requant.oracle import lane,check,expected
from chip_rl.requant.rtl import design,bad,CATALOG,MUTANTS
from chip_rl.requant.spec import Config,shapes
from chip_rl.requant.simulation import parse_trace
from chip_rl.requant.env import RequantEnv
from chip_rl.evaluate import sanitize,Rejected
class RequantTests(unittest.TestCase):
 def test_hand_computed_rounding(self):
  for a,want in [(1,0),(3,2),(5,2),(-1,0),(-3,-2),(-5,-2)]:self.assertEqual(lane(a,1,1,0),want)
  self.assertEqual(lane(-2**31,65535,47,0),-1)
  self.assertEqual(lane(2**31-1,65535,47,0),1)
 def test_saturation_after_zero_point(self):
  self.assertEqual(lane(200,1,0,-128),72)
  self.assertEqual(lane(-200,1,0,127),-73)
  self.assertEqual(lane(2**31-1,65535,0,-128),127)
  self.assertEqual(lane(-2**31,65535,0,127),-128)
 def test_mask_unused_and_width(self):
  r=dict(acc=[1,-1,17,19],scale=1,shift=0,zp=0,mask=15)
  self.assertEqual(expected(r,2),0xff01)
  for v in (-1,2**32+0xff01,True,0):
   with self.assertRaises(ValueError):check(r,2,v)
 def test_source_catalog(self):
  self.assertEqual(len(set(map(design,CATALOG))),5)
  for s in [design(x) for x in CATALOG]+[bad(x) for x in MUTANTS]:sanitize(s)
  self.assertEqual(len({bad(x) for x in MUTANTS}),len(MUTANTS))
 def test_trace_strictness(self):
  log='RESET_PROBE 0 1\nCANCEL_RESULT 00000001\nOUT 0 00000001\nREQUANT_PASS 1 3 2 2\nRESET_PROBE 1 1\nAFTER_RESET_RESULT 00000001\nDRAIN_PASS\n'
  self.assertEqual(parse_trace(log,1,100)[0],{0:1})
  for s in [log.replace('RESET_PROBE 0 1\n',''),log.replace('RESET_PROBE 1 1','RESET_PROBE 1 0'),log.replace('OUT 0','OUT 1'),log+'DRAIN_PASS\n',log.replace('OUT 0 00000001','OUT 0 100000001'),log.replace('REQUANT_PASS 1','REQUANT_PASS 2')]:
   with self.assertRaises(Rejected):parse_trace(s,1,100)
 def test_scope_and_action(self):
  self.assertEqual(shapes('development'),[2,4]);self.assertEqual(shapes('heldout'),[1,3])
  e=RequantEnv()
  with self.assertRaises(RuntimeError):e.step({'rtl':design()})
  e.steps=0
  with self.assertRaises(ValueError):e.step({'rtl':design(),'max_cells':999999})
  with self.assertRaises(ValueError):Config('dot')
