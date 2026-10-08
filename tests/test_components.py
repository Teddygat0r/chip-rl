import io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from chip_rl.quality.spec import Config
from chip_rl.quality.rtl import design
from chip_rl.quality.components import instrument,accumulator_harness,sat
from chip_rl.quality import sealed
from chip_rl.evaluate import digest
class Components(unittest.TestCase):
 def test_cutpoint_and_routing_are_bound_to_source(self):
  c=Config('dot',k=7);s=design(c,'shiftadaptive');a,h,m=instrument(s,c)
  self.assertEqual(m['source_sha256'],digest(s));self.assertEqual(m['cutpoints'],1)
  self.assertIn('assert(a==proof_input',a);self.assertIn('assert(b==proof_input',a)
  self.assertIn('assume(term>=-16\'sd16256)',a);self.assertIn('proof_pending==(busy || ov)',a)
  for bad in [s.replace('p=a*b;','p=0;'),s.replace('reg signed [7:0] a,b','reg [7:0] a,b')]:
   with self.assertRaises(ValueError):instrument(bad,c)
 def test_transition_bound_cannot_skip_assertion_warmup(self):
  from chip_rl.quality.components import check_folded
  with self.assertRaises(ValueError):check_folded(design(Config("dot"),"shiftadaptive"),Config("dot"),"/unused",2,"datapath_transition")
 def test_candidate_cannot_constrain_its_proof(self):
  src=design(Config('dot'),'shiftadaptive')
  for extra in ('always @* assume(0);','always @* assert(1);'):
   with self.assertRaises(ValueError):instrument(src.replace('endmodule',extra+'endmodule'),Config('dot'))
 def test_monitor_namespace_cannot_be_shadowed(self):
  src=design(Config('dot'),'shiftadaptive')
  with self.assertRaises(ValueError):instrument(src.replace('endmodule','wire proof_seen=0;endmodule'),Config('dot'))
 def test_lemma_inputs_are_independent(self):
  h=accumulator_harness();self.assertIn('a[20+:',h);self.assertIn('pos[5+:5]',h)
 def test_unproven_fails_closed(self):
  def fake(cmd,root,label,timeout):
   self.assertIn('-set-assumes',(root/'formal.ys').read_text());return 'No success marker'
  with tempfile.TemporaryDirectory() as td,patch('chip_rl.quality.components.run',side_effect=fake):
   self.assertEqual(sat(Path(td)/'check','','module formal_top;endmodule')['status'],'unproven')
class Sealed(unittest.TestCase):
 def setUp(self):
  patcher=patch("chip_rl.quality.sealed.tool_fingerprint",return_value="0"*64);patcher.start();self.addCleanup(patcher.stop)
 def test_toolchain_tamper_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root,pc,sc=self.setup_batch(td)
   with patch("chip_rl.quality.sealed.tool_fingerprint",return_value="1"*64):
    with self.assertRaises(ValueError):sealed.submit(root,pc,sc,{"id":"0","rtl":"good"})
 def setup_batch(self,td):
  root=Path(td)/'batch';p=sealed.create(root,['dot','tensor']);subs=[{'id':str(i),'source_sha256':digest(s)} for i,s in enumerate(['good','bad'])];s=sealed.register(root,p['plan_commitment'],subs);return root,p['plan_commitment'],s['submission_commitment']
 def test_one_shot_batch_and_embargo(self):
  with tempfile.TemporaryDirectory() as td:
   root,pc,sc=self.setup_batch(td)
   with patch('chip_rl.quality.sealed.Evaluator') as ev:
    ev.return_value.evaluate.return_value={'tested_correct':True,'reward':1.,'objectives':{}}
    ack=sealed.submit(root,pc,sc,{'id':'0','rtl':'good'});self.assertNotIn('tested_correct',ack)
    with self.assertRaises(ValueError):sealed.release(root,pc,sc)
    with self.assertRaises(FileExistsError):sealed.submit(root,pc,sc,{'id':'0','rtl':'good'})
    ev.return_value.evaluate.side_effect=RuntimeError('secret diagnosis')
    sealed.submit(root,pc,sc,{'id':'1','rtl':'bad'})
    r=sealed.release(root,pc,sc);self.assertEqual(r['results'][1]['status'],'unproven');self.assertEqual(r['results'][1]['reward'],0)
    with self.assertRaises(FileExistsError):sealed.release(root,pc,sc)
 def test_tamper_override_and_leak_rejection(self):
  with tempfile.TemporaryDirectory() as td:
   root,pc,sc=self.setup_batch(td)
   for req in [{'id':'0','rtl':'changed'},{'id':'0','rtl':'good','seed':7},{'id':'0','rtl':'good','artifacts':'/tmp/x'}]:
    with self.assertRaises(ValueError):sealed.submit(root,pc,sc,req)
   with self.assertRaises(ValueError):sealed.submit(root,'0'*64,sc,{'id':'0','rtl':'good'})
   with self.assertRaises(ValueError):sealed.submit(root,pc,'0'*64,{'id':'0','rtl':'good'})
   plan=json.loads((root/'plan.json').read_text());plan['slots'][0]['seed']+=1;(root/'plan.json').write_text(json.dumps(plan))
   with self.assertRaises(ValueError):sealed.submit(root,pc,sc,{'id':'0','rtl':'good'})
 def test_json_boundary_does_not_expose_private_plan(self):
  with tempfile.TemporaryDirectory() as td:
   root,pc,sc=self.setup_batch(td);out=io.StringIO()
   sealed.serve(root,pc,sc,io.StringIO('{"id":"0","rtl":"good","seed":1}\n'),out)
   self.assertEqual(json.loads(out.getvalue()),{'ok':False,'error':'request rejected'})
 def test_sources_commit_before_any_feedback(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)/'b';p=sealed.create(root,['dot','tensor'])
   with self.assertRaises(ValueError):sealed.register(root,p['plan_commitment'],[{'id':'0','source_sha256':digest('a')}])
   with patch('chip_rl.quality.sealed.fingerprint',return_value='changed'):
    with self.assertRaises(ValueError):sealed.register(root,p['plan_commitment'],[])
