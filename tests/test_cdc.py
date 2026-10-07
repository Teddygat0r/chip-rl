import io,json,unittest
from chip_rl.cdc.spec import Config,Choice,CHOICES,configurations,specification
from chip_rl.cdc.workloads import make
from chip_rl.cdc.server import serve
from chip_rl.cdc.rtl import design

class CDCContracts(unittest.TestCase):
 def test_parameter_boundary(self):
  for kwargs in ({'depth':3},{'width':True},{'max_ticks':30001},{'max_cells':4097}):
   with self.assertRaises(ValueError):Config(**kwargs)
  for kwargs in ({'sync_stages':1},{'sync_stages':True},{'architecture':'raw_rtl'}):
   with self.assertRaises(ValueError):Choice(**kwargs)
  self.assertEqual(len({design(x) for x in CHOICES}),4)
 def test_separate_experimental_contract(self):
  s=specification(Config())
  self.assertFalse(s['pilot_eligible']);self.assertFalse(s['physical_cdc_safety_verified'])
  self.assertEqual(s['action_type'],'architecture_parameters_only')
  self.assertEqual({c.depth for c in configurations(Config())},{2,4,8,16})
 def test_reproducible_phase_reset_and_wrap_schedules(self):
  c=Config(max_ticks=512);a=make(c,77);self.assertEqual(a,make(c,77));self.assertNotEqual(a,make(c,78))
  self.assertEqual(len(a),25)
  self.assertEqual(sum(e['score'] for e in a),5)
  self.assertTrue(all(len(e['inputs'])>64*c.depth for e in a if e['score']))
  self.assertEqual({e['cut'] for e in a},{0,1,c.depth})
  self.assertTrue(any(v&3==3 for e in a for v in e['controls']))
  self.assertTrue(any(bool(v&4)!=bool(v&8) for e in a for v in e['controls']))
  self.assertNotEqual({(e['w_period'],e['r_period']) for e in a},{(e['w_period'],e['r_period']) for e in make(c,77,True)})
 def test_server_rejects_host_controls_without_tools(self):
  for r in ({'op':'reset','task':'cdc_fifo','depth':2},{'op':'reset','task':'cdc_fifo','replay_seed':1},{'op':'step','action':{}},[]):
   out=io.StringIO();serve(io.StringIO(json.dumps(r)+'\n'),out);self.assertFalse(json.loads(out.getvalue())['ok'])
  out=io.StringIO();serve(io.StringIO('x'*25000+'\n'),out);self.assertFalse(json.loads(out.getvalue())['ok'])
