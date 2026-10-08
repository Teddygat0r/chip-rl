import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from chip_rl.quality.refinement import union_states,wrapper,extract,prove
from chip_rl.quality.spec import Config
class Refinement(unittest.TestCase):
 def test_alias_collision_rejected(self):
  a={'kind':'a','state_bits':2,'aliases':{'x':0,'y':1}};b={'kind':'b','state_bits':1,'aliases':{'x':0,'y':0}}
  with self.assertRaises(ValueError):union_states([a,b])
 def test_distinct_state_stays_free(self):
  mapping,aliases,n=union_states([{'kind':'a','state_bits':2,'aliases':{'x':0}},{'kind':'b','state_bits':2,'aliases':{'x':1}}]);self.assertEqual(n,3);self.assertEqual(mapping['a',0],mapping['b',1]);self.assertNotEqual(mapping['a',1],mapping['b',0])
 def test_scope_rejected_before_tools(self):
  with self.assertRaises(ValueError):extract('',Config('dot',k=4),'/never-created','original')
 def test_unknown_success_unproven(self):
  with tempfile.TemporaryDirectory() as td,patch('chip_rl.quality.refinement.wrapper',return_value=('module formal_top;endmodule',{})),patch('chip_rl.quality.refinement.run',return_value='SUCCESS!'):
   self.assertEqual(prove([],Path(td)/'p','capture',0)['status'],'unproven')
 def test_missing_tool_unproven(self):
  with tempfile.TemporaryDirectory() as td,patch('chip_rl.quality.refinement.wrapper',return_value=('module formal_top;endmodule',{})),patch('chip_rl.quality.refinement.run',side_effect=OSError('absent')):
   self.assertEqual(prove([],Path(td)/'p','capture',0)['status'],'unproven')
 def test_mixed_configuration_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   roots=[]
   for i in range(2):
    p=Path(td)/str(i);p.mkdir();(p/'metadata.json').write_text(json.dumps({'source_sha256':'same','config':{'k':i}}));roots.append(p)
   with self.assertRaisesRegex(ValueError,'source/config'):wrapper(roots,'equivalence',0)
