import unittest
from chip_rl.expansion.spec import Config,cases
from chip_rl.expansion.models import result,Retirement
from chip_rl.expansion.traffic import trace
from chip_rl.tasks import pack,bits
class ExpansionModels(unittest.TestCase):
 def test_permute_mask_duplicates_and_oob(self):
  c=Config('permute',width=8,k=2)
  x=pack([0xff01,2,3,4,5,6,7,8],16)|(pack([3,3,7,0],3)<<128)|(15<<152)
  self.assertEqual(result(c,x),pack([4,4,0,1],16))
  self.assertEqual(result(c,x&~(1<<153)),pack([4,0,0,1],16))
 def test_coalesce_stable_line_groups(self):
  c=Config('coalesce',width=16,k=2);x=pack([31,16,65535,0],16)|(15<<128)
  self.assertEqual(result(c,x),3|((16|(3<<16))<<8)|((65520|(4<<16))<<32)|((0|(8<<16))<<56))
  self.assertEqual(result(c,x&~(15<<128)),0)
 def test_retire_out_of_order_and_flush(self):
  m=Retirement(Config('retire',depth=4,width=8))
  self.assertEqual(m.step(1|(42<<64)),1)
  self.assertEqual(m.step(1|(43<<64)),1|(1<<8)|(1<<72))
  m.step((1<<3)|(1<<16)|(0xabcd<<32),False)
  self.assertEqual(m.step(0,False),1|(2<<72))
  m.step((1<<3)|(0x1234<<32),False)
  y=m.step(0,False);self.assertEqual(y,3|(0x34<<40)|(42<<56)|(2<<72))
  self.assertEqual(m.step(0,False),y)
  m.step((1<<3)|(0x99<<32),False) # repeated completion cannot overwrite held data
  self.assertEqual(m.step(2,False),y)
  self.assertEqual(m.step(0,False),3|(1<<24)|(0xcd<<40)|(43<<56)|(1<<72))
  m.step(4);self.assertEqual(m.step(1|(7<<64)),1|(2<<8))
  m.step((1<<3)|(1<<16)|(0xff<<32));self.assertEqual(m.step(0),1|(1<<72))
 def test_retire_event_monitor(self):
  for d in (4,6,8):
   for w in (8,16):
    for seed in range(5):
     rows,s=trace(Config('retire',depth=d,width=w),seed,1024)
     self.assertGreater(s['flushes'],0);self.assertGreater(s['out_of_order_completions'],0)
 def test_coverage_floors_and_structures(self):
  for n in ('permute','coalesce','retire'):
   rows=cases(Config(n),17)
   self.assertGreaterEqual(rows[1][-1],1024);self.assertGreaterEqual(len(rows),4)
 def test_stateless_padding_invariance(self):
  for n in ('permute','coalesce'):
   c=Config(n);x=(1<<160)-1
   self.assertEqual(result(c,x),result(c,x|(1<<511)))
if __name__=='__main__':unittest.main()

class ExpansionBoundary(unittest.TestCase):
 def test_constraints_cannot_alias_or_enter_actions(self):
  from unittest.mock import patch
  from chip_rl.expansion.env import ExpansionEnv
  with patch('chip_rl.expansion.env.Evaluator') as q:
   q.return_value.evaluate.return_value={'tested_correct':True,'reward':1.,'metrics':[]}
   e=ExpansionEnv('coalesce',horizon=1,objective='area');obs,_=e.reset()
   obs['constraints']['config']['width']=32;obs['evaluation']['metrics'].append('edit')
   self.assertEqual(e.c.width,16);self.assertEqual(e.last['metrics'],[])
   for action in ({'rtl':obs['rtl'],'width':32},{'rtl':obs['rtl'],'replay_seed':1}):
    with self.assertRaises(ValueError):e.step(action)
   self.assertTrue(e.step({'rtl':obs['rtl']})[3])
   with self.assertRaises(RuntimeError):e.step({'rtl':obs['rtl']})
 def test_server_rejects_budget_seed_and_goal_overrides(self):
  import io,json
  from chip_rl.expansion.server import serve
  reqs=[{'op':'reset','task':'retire','max_cells':1},{'op':'reset','task':'retire','replay_seed':1},{'op':'reset','task':'retire','objective':'area'}]
  out=io.StringIO();serve(io.StringIO(''.join(json.dumps(x)+'\n' for x in reqs)),out)
  self.assertTrue(all(not json.loads(x)['ok'] for x in out.getvalue().splitlines()))
 def test_existing_cycle_clock_budget_is_enforced(self):
  from chip_rl.cycle.evaluate import simulate
  from chip_rl.tasks import Config as OldConfig
  from chip_rl.evaluate import Rejected
  with self.assertRaisesRegex(Rejected,'cycle budget'):
   simulate(None,OldConfig('dma',depth=16,max_cycles=128),'',None,17)
