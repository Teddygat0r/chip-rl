"""Unscored reset probes must not tighten a trusted scored-cycle budget."""
import tempfile,unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from chip_rl.tasks import Config
from chip_rl.cycle.evaluate import simulate
from chip_rl.cycle.traffic import trace
from chip_rl.evaluate import Rejected

class RouterBudgetTests(unittest.TestCase):
 def setUp(self):
  self.c=Config('router',depth=16);self.seed=27
  self.rows,self.stats=trace(self.c,self.seed,live=512+self.seed%257)
 def test_original_exact_cycle_budget_reaches_hdl(self):
  with tempfile.TemporaryDirectory() as td:
   sd=Path(td);(sd/'netlist.v').write_text('module candidate; endmodule')
   with patch('chip_rl.cycle.evaluate.run',side_effect=RuntimeError('reached HDL')) as run:
    with self.assertRaisesRegex(RuntimeError,'reached HDL'):
     simulate(None,replace(self.c,max_cycles=len(self.rows)),'module candidate; endmodule',sd,self.seed)
    self.assertEqual(run.call_count,1)
 def test_original_insufficient_budget_still_rejected(self):
  with patch('chip_rl.cycle.evaluate.run') as run:
   with self.assertRaisesRegex(Rejected,'cycle budget'):
    simulate(None,replace(self.c,max_cycles=len(self.rows)-1),'',Path('/unused'),self.seed)
   run.assert_not_called()
