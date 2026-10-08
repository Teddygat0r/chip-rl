import unittest
import io,json
from unittest.mock import patch
from chip_rl.tasks import Config,bits
from chip_rl.cycle.models import DMA,Router,Scoreboard,Accelerator
from chip_rl.cycle.traffic import trace
class CycleOracles(unittest.TestCase):
 def test_dma_moves_values_and_holds_write(self):
  m=DMA(Config('dma',depth=16));self.assertEqual(m.step(1|(2<<8)|(5<<16)|(1<<24)),1)
  self.assertEqual(m.step(1<<32),34|(2<<8));self.assertEqual(m.step((1<<33)|(123<<64)),36)
  expected=40|(5<<16)|(123<<32)
  self.assertEqual(m.step(0,False),expected);self.assertEqual(m.step(1<<34,False),expected)
  self.assertEqual(m.step(1<<32),34|(3<<8));m.step((1<<33)|(456<<64));self.assertEqual(m.step(1<<34),40|(6<<16)|(456<<32))
  self.assertEqual(m.step(0),17);self.assertEqual(m.step(0),1)
 def test_router_storage_and_backpressure(self):
  m=Router(Config('router'));self.assertEqual(m.step(1|(2<<1)|(42<<4)),1<<96)
  held=4|(42<<40);self.assertEqual(m.step(0,False),held);self.assertEqual(m.step(0,False),held)
  self.assertEqual(m.step(1<<162,False),held);self.assertEqual(m.step(0,False),0)
 def test_scoreboard_completion_during_input_idle(self):
  m=Scoreboard(Config('scoreboard',k=2))
  x=1|(3<<5)|(3<<9)|(9<<12)
  x|=(1|(3<<1)|(4<<5)|(10<<12))<<24
  self.assertEqual(m.step(x),3<<32)
  self.assertEqual(m.step(0,False),1|(1<<11)|(9<<24))
  for _ in range(3):self.assertEqual(m.step(0,False),1<<11)
  self.assertEqual(m.step(0,False),2|(1<<12)|(10<<24))
 def test_accumulator_exact_and_concurrent_read_before_write(self):
  m=Accelerator(Config('accelerator',depth=16));m.mem[:4]=[128]*4;m.step(2)
  m.state='response';m.dst=0;m.left=1
  m.step((1<<33)|(127<<64),False);self.assertEqual(m.acc,16384);self.assertEqual(m.mem[0],127)
  for _ in range(3):m.step(0,False)
  out=m.step(0,False);self.assertEqual(bits(out,32,18),65536);self.assertTrue(out&(1<<5))
  self.assertEqual(m.step(0,False),out)
 def test_protocol_monitors_multiple_seeds_and_dimensions(self):
  for n in ('dma','router','scoreboard','accelerator'):
   for c in (Config(n,depth=16,k=4),Config(n,depth=64,k=2,width=8)):
    for seed in range(5):
     rows,stats=trace(c,seed);self.assertGreater(stats['retired'],0);self.assertEqual(len(rows),800)
     self.assertGreater(stats['idle_clocks'],0)
 def test_json_rejects_host_controls(self):
  from chip_rl.cycle.server import serve
  reqs=[{'op':'step','action':{'rtl':'x'}},
        {'op':'reset','task':'dma','replay_seed':1},
        {'op':'reset','task':'dma','cache':'/tmp/agent'},
        {'op':'reset','task':'dma','objective':'area'}]
  out=io.StringIO();serve(io.StringIO(''.join(json.dumps(x)+'\n' for x in reqs)),out)
  self.assertTrue(all(not json.loads(x)['ok'] for x in out.getvalue().splitlines()))
 def test_source_only_episode_and_observation_copy(self):
  from chip_rl.cycle.env import CycleEnv
  with patch('chip_rl.cycle.env.CycleEvaluator') as q:
   q.return_value.evaluate.return_value={'tested_correct':True,'reward':1.,'metrics':{'cells':1}}
   e=CycleEnv('dma',horizon=1);obs,_=e.reset(seed=3)
   self.assertIn('read-response data',obs['contract_text'])
   obs['evaluation']['metrics']['cells']=999
   self.assertEqual(e.result['metrics']['cells'],1)
   for action in ({'rtl':'x','seed':1},{'path':'/tmp/x'},{'rtl':'x','objective':'area'}):
    with self.assertRaises(ValueError):e.step(action)
   self.assertTrue(e.step({'rtl':obs['rtl']})[3])
   with self.assertRaises(RuntimeError):e.step({'rtl':obs['rtl']})
if __name__=='__main__':unittest.main()
