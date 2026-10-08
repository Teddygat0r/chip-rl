import json,os,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import patch
from chip_rl.audit import journal
from chip_rl._tools import run,Rejected
from chip_rl.cdc.spec import Config
class Dummy:
 @journal
 def evaluate(self,c,src,*,replay_seed=None,artifacts=None):
  with tempfile.TemporaryDirectory() as td:
   run([sys.executable,'-c','print("retained diagnostic",flush=True);raise SystemExit(1)'],td,'failure')
class Audit(unittest.TestCase):
 def test_source_seed_and_tool_log_survive_tool_temp_cleanup(self):
  with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'CHIP_RL_TRACE_ROOT':td}):
   with self.assertRaises(Rejected):Dummy().evaluate(Config(),'retained source',replay_seed=123)
   p=next(Path(td).iterdir());r=json.loads((p/'private-run.json').read_text())
   self.assertEqual(r['seed'],123);self.assertEqual(r['status'],'raised')
   self.assertEqual((p/'candidate.sv').read_text(),'retained source')
   self.assertIn('retained diagnostic',next((p/'tool-logs').iterdir()).read_text())
   self.assertEqual(p.stat().st_mode&0o777,0o700)
 def test_default_capture_is_not_reused(self):
  with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'CHIP_RL_TRACE_ROOT':td}):
   for _ in range(2):
    with self.assertRaises(Rejected):Dummy().evaluate(Config(),'x')
   rows=[json.loads((p/'private-run.json').read_text()) for p in Path(td).iterdir()]
   self.assertEqual(len(rows),2);self.assertNotEqual(rows[0]['seed'],rows[1]['seed'])

 def test_keyword_library_call_retains_same_source_and_configuration(self):
  with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'CHIP_RL_TRACE_ROOT':td}):
   with self.assertRaises(Rejected):Dummy().evaluate(c=Config(),src='keyword source',replay_seed=77)
   p=next(Path(td).iterdir());r=json.loads((p/'private-run.json').read_text())
   self.assertEqual(r['config']['width'],16);self.assertEqual(r['seed'],77)
   self.assertEqual((p/'candidate.sv').read_text(),'keyword source')
