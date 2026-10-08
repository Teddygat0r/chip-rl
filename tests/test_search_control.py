import runpy,unittest
from pathlib import Path
m=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/compare_search.py'),run_name='search_control_tests')
class SearchControl(unittest.TestCase):
 def test_each_method_charged_same_budget_without_repeat(self):
  for task in m['CATALOGS']:
   for method in m['METHODS']:
    calls=[]
    def oracle(label):
     calls.append(label)
     return {'result':{'tested_correct':True,'objective_eligible':True,'reward':1.0},'measured_seconds':1.,'shared_measurement':False}
    r=m['transact'](task,method,oracle,17)
    self.assertEqual(len(calls),m['BUDGETS'][task]);self.assertEqual(len(set(calls)),len(calls));self.assertIn(r['winner'],calls)
 def test_reward_cannot_select_unproven_or_ineligible(self):
  rows=[{'label':'safe','tested_correct':True,'objective_eligible':True,'reward':1.}, {'label':'unproven','tested_correct':False,'objective_eligible':True,'reward':9.}, {'label':'slow','tested_correct':True,'objective_eligible':False,'reward':8.}]
  self.assertEqual(m['choose_winner'](rows),'safe')
  with self.assertRaises(ValueError):m['choose_winner'](rows[1:])
 def test_holdout_cannot_start_before_freeze(self):
  s=m['Study'].__new__(m['Study']);s.frozen=False
  with self.assertRaisesRegex(ValueError,'holdout before freeze'):s.measure(0,'heldout',6,'dual')
 def test_unique_evaluation_cap_precedes_tool_work(self):
  s=m['Study'].__new__(m['Study']);s.frozen=True;s.task='dot';s.samples={};s.actual_calls=m['UNIQUE_LIMITS']['dot']
  with self.assertRaisesRegex(ValueError,'budget exceeded'):s.measure(0,'development',0,'baseline')
 def test_shared_measurement_view_cannot_mutate_other_methods(self):
  s=m['Study'].__new__(m['Study']);s.frozen=True;s.samples={'0/development/0/baseline':{'result':{'reward':1.},'measured_seconds':2.}}
  r=s.measure(0,'development',0,'baseline');r['result']['reward']=99
  self.assertEqual(s.measure(0,'development',0,'baseline')['result']['reward'],1.)
 def test_policy_randomness_is_replayable(self):
  def oracle(label):return {'result':{'tested_correct':True,'objective_eligible':True,'reward':1.},'measured_seconds':1.,'shared_measurement':True}
  a=m['transact']('dot','random',oracle,29);b=m['transact']('dot','random',oracle,29)
  self.assertEqual(a,b)

class SearchReplay(unittest.TestCase):
 def setUp(self):
  self.signature=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/replay_search.py'),run_name='search_replay_tests')['qualification_signature']
 def test_saved_array_and_live_tuple_metadata_match(self):
  a={'tested_correct':True,'reward':1.,'weights':[.45,.3,.25],'elapsed_s':2,'synthesis_cache_hits':5}
  b={'tested_correct':True,'reward':1.,'weights':(.45,.3,.25),'elapsed_s':4,'synthesis_cache_hits':0}
  self.assertEqual(self.signature(a),self.signature(b))
 def test_qualification_changes_are_not_normalized_away(self):
  a={'tested_correct':True,'reward':1.,'recipe_sha256':'same','cells':12}
  for key,value in [('tested_correct',1),('reward',.99),('recipe_sha256','different'),('cells',13)]:
   self.assertNotEqual(self.signature(a),self.signature(a|{key:value}))
