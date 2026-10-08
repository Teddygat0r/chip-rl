import io,json,unittest
from pathlib import Path
from unittest.mock import patch
from chip_rl.tasks import Config,NAMES,workload
from chip_rl.heldout import challenge
from chip_rl.alternates import alternate,STRATEGIES
from chip_rl.rtl import design
from chip_rl.evaluate import sanitize,Rejected
from chip_rl.server import serve

class AuditTests(unittest.TestCase):
    def test_challenge_does_not_call_training_generator(self):
        with patch('chip_rl.tasks.workload',side_effect=AssertionError('training generator called')):
            for name in NAMES:
                c=Config(name,depth=16)
                a=challenge(c,19,16)
                self.assertTrue(a);self.assertEqual(a,challenge(c,19,16))
                self.assertTrue(all(0<=x<1<<512 for x in a))
    def test_task_specific_alternates_not_only_retiming(self):
        for name in NAMES:
            c=Config(name)
            self.assertNotEqual(alternate(c),design(c,2),name)
            self.assertIn(name,STRATEGIES);sanitize(alternate(c))
    def test_contract_is_packaged(self):
        self.assertEqual(Path('docs/contracts.md').read_text(),Path('chip_rl/contracts.md').read_text())
    def test_forbidden_hierarchy_and_elaboration_features(self):
        for payload in ['always @* y=tb.expected[0];','bind tb evil x();','import pkg::*;','disable tb;']:
            with self.subTest(payload=payload),self.assertRaises(Rejected):sanitize(design(Config('elastic'))+payload)
    def test_json_external_action_boundary(self):
        requests=[{'op':'step','action':{'stages':2}}, {'op':'reset','task':'elastic','seed':13},
                  {'op':'step','action':{'constraints':{},'stages':2}}, {'op':'step','action':{'stages':2}},
                  {'op':'step','action':{'stages':1}}, {'op':'exec','cmd':'anything'}]
        out=io.StringIO();serve(io.StringIO(''.join(json.dumps(x)+'\n' for x in requests)),out,horizon=1)
        rows=[json.loads(x) for x in out.getvalue().splitlines()]
        self.assertEqual([r['ok'] for r in rows],[False,True,False,True,False,False])
        self.assertIn('Command',rows[1]['observation']['contract_text'])
        self.assertTrue(rows[3]['info']['correct']);self.assertGreater(rows[3]['reward'],1)

class InputBoundaryTests(unittest.TestCase):
    def test_seed_cannot_inject_testbench(self):
        from chip_rl.evaluate import evaluate
        payload='1; integer f; initial begin f=$fopen("/tmp/chip-escape", "w"); end; reg [31:0] injected=1'
        for seed in (payload,{},[],True,-1,2**32,1.25):
            with self.subTest(seed=seed),patch('chip_rl.evaluate.simulate',side_effect=AssertionError('HDL tool reached')):
                result=evaluate(Config('elastic'),design(Config('elastic')),seed=seed)
                self.assertFalse(result['correct']);self.assertIn('unsigned 32-bit',result['error'])
        out=io.StringIO()
        serve(io.StringIO(json.dumps({'op':'reset','task':'elastic','seed':payload})+'\n'),out)
        self.assertFalse(json.loads(out.getvalue())['ok'])
    def test_resource_config_cannot_inject_hdl(self):
        for kwargs in ({'max_cycles':'1; arbitrary HDL'}, {'max_cells':0}, {'width':True}, {'max_cycles':100001}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):Config('elastic',**kwargs)

if __name__=='__main__':unittest.main()
