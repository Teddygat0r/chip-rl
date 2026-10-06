import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from chip_rl.tasks import Config
from chip_rl.rtl import design
from chip_rl.evaluate import evaluate,sanitize,Rejected,run
from chip_rl.env import ChipEnv
from chip_rl.formal import check_elastic

class EvaluatorTests(unittest.TestCase):
    def test_unsafe_constructs(self):
        c=Config('elastic');s=design(c)
        for extra in ['`include "secret"','// synthesis translate_off','initial $finish;','(* blackbox *)','initial $readmemh("hidden", x);','always #1 clk=~clk;']:
            with self.subTest(extra=extra),self.assertRaises(Rejected):sanitize(s+extra)
    def test_missing_tool_never_passes(self):
        with patch('chip_rl.evaluate.tool',side_effect=Rejected('missing tool')):
            r=evaluate(Config('elastic'),design(Config('elastic')))
        self.assertFalse(r['correct']);self.assertEqual(r['reward'],0)
    def test_timeout(self):
        with tempfile.TemporaryDirectory() as d,self.assertRaises(Rejected):run(['/bin/sleep','3'],d,'timeout',.02)
    def test_budget_is_hard(self):
        c=Config('elastic',max_cells=1);r=evaluate(c,design(c))
        self.assertFalse(r['correct']);self.assertEqual(r['error'],'area resource budget')
    def test_interface_cannot_change(self):
        c=Config('elastic');r=evaluate(c,design(c).replace('input [511:0] in_data','input [510:0] in_data'))
        self.assertFalse(r['correct']);self.assertIn('interface',r['error'])
    def test_step_contract_reward_and_observation_copies(self):
        e=ChipEnv('elastic',horizon=1);o,info=e.reset(8)
        o['constraints']['max_cells']=1;info['baseline']['cells']=999999
        with self.assertRaises(ValueError):e.step({'stages':2,'constraints':{}})
        _,reward,terminated,truncated,info=e.step({'stages':2})
        self.assertTrue(info['correct']);self.assertGreater(reward,1);self.assertFalse(terminated);self.assertTrue(truncated)
        with self.assertRaises(RuntimeError):e.step({'stages':1})
    def test_baseline_workload_must_match(self):
        c=Config('elastic');base=evaluate(c,design(c),count=100)
        r=evaluate(c,design(c,2),count=101,baseline=base)
        self.assertFalse(r['correct']);self.assertEqual(r['reward'],0)
    def test_formal_unknown_never_passes(self):
        with patch('chip_rl.formal.run',side_effect=Rejected('timeout')):
            self.assertEqual(check_elastic(design(Config('elastic')))['status'],'unproven')

class PhysicalAvailabilityTests(unittest.TestCase):
    def test_missing_physical_flow_never_verifies(self):
        from chip_rl.physical import physical
        with tempfile.TemporaryDirectory() as td:
            r=physical(Config('elastic'),design(Config('elastic')),Path(td)/'absent',Path(td)/'out')
            self.assertEqual(r['status'],'not_run');self.assertFalse(r['physical_verified']);self.assertIsNone(r['metrics'])

class MutationCoverageTests(unittest.TestCase):
    def test_cache_readback_catches_lost_hit_write(self):
        from chip_rl.mutants import semantic
        c=Config('cache',depth=16)
        r=evaluate(c,semantic(c))
        self.assertFalse(r['correct']);self.assertIn('functional mismatch',r['error'])
    def test_scoreboard_unfair_priority_rejected(self):
        c=Config('scoreboard');r=evaluate(c,design(c,mutant='unfair'))
        self.assertFalse(r['correct']);self.assertIn('functional mismatch',r['error'])

if __name__=='__main__':unittest.main()
