import unittest
from chip_rl.objectives import scores,frontier,PROFILES
from chip_rl.contracts import specification
from chip_rl.tasks import Config
class Goals(unittest.TestCase):
 def test_slow_area_saving_is_not_balanced_success(self):
  rows=[{'baseline':{'cells':100,'cycles':100,'offered_latency':100},'candidate':{'cells':10,'cycles':1000,'offered_latency':1000},'target':True}]
  r=scores(rows);self.assertGreater(r['area']['reward'],1);self.assertTrue(r['area']['eligible'])
  self.assertEqual(r['balanced']['reward'],0);self.assertFalse(r['balanced']['eligible']);self.assertFalse(r['latency']['eligible'])
 def test_baselines_equal_and_constraints_do_not_alias(self):
  b={'cells':100,'cycles':100,'offered_latency':100};r=scores([dict(baseline=b,candidate=b,target=True)])
  for goal in r:self.assertEqual(r[goal]['reward'],1);self.assertTrue(r[goal]['eligible'])
  s=specification(Config('dot'));s['objective_profiles']['area']['max_cycle_ratio']=999
  self.assertEqual(PROFILES['area']['max_cycle_ratio'],16)
 def test_pareto_frontier_keeps_tradeoffs(self):
  p={'baseline':dict(cells=1,cycles=1,latency=1),'small_slow':dict(cells=.5,cycles=2,latency=2),'dominated':dict(cells=2,cycles=2,latency=2)}
  self.assertEqual(set(frontier(p)),{'baseline','small_slow'})
 def test_all_dimensions_gate_objective(self):
  b=dict(cells=100,cycles=100,offered_latency=100)
  rows=[dict(baseline=b,candidate=b,target=True),dict(baseline=b,candidate=dict(cells=100,cycles=300,offered_latency=100),target=False)]
  self.assertFalse(scores(rows)['balanced']['eligible'])
if __name__=='__main__':unittest.main()
