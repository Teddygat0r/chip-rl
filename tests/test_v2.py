import io,json,tempfile,unittest,random
from unittest.mock import patch
from chip_rl.tasks import Config,Model,NAMES
from chip_rl.rtl import design
from chip_rl.contracts import PILOT
from chip_rl.corpus import commands,schedule
from chip_rl.evaluate import TrustedEvaluator,Rejected,reward,sanitize,run
from chip_rl.env import ChipEnv
from chip_rl.server import serve
from chip_rl.formal import check_elastic

class Contracts(unittest.TestCase):
    def test_independent_private_corpus(self):
        with patch('chip_rl.tasks.workload',side_effect=AssertionError):
            for n in NAMES:
                c=Config(n,depth=16)
                a=commands(c,1);b=commands(c,2)
                self.assertNotEqual(a,b);self.assertEqual(a,commands(c,1))
                self.assertTrue(all(0<=x<2**512 for x in a))
    def test_reward_monotone(self):
        rng=random.Random(17)
        for _ in range(1000):
            b=dict(cells=rng.randrange(1,10000),cycles=rng.randrange(1,10000),offered_latency=rng.random()*100)
            self.assertEqual(reward(b,b),1)
            for key in b:
                worse=b.copy();worse[key]+=1
                self.assertLess(reward(b,worse),1)
    def test_schedule_independent_of_acceptance(self):
        c=Config('elastic');arrival,consumer,limit=schedule(c,100,51)
        self.assertEqual(arrival[:4],[0]*4);self.assertEqual(consumer[:32],[0]*32)
        self.assertEqual((arrival,consumer,limit),schedule(c,100,51))
    def test_full_domain_cache_alias(self):
        c=Config('cache');m=Model(c)
        m.step(0);m.step(2|(42<<24));self.assertEqual(m.step(2048<<8)&7,4)
        xs=commands(c,51)
        self.assertTrue(any(((x>>8)&65535)==2048 and not x&3 for x in xs))
    def test_cold_reads_before_write(self):
        for n in ('scratchpad','gather'):
            ys=[Model(Config(n)).step(x) for x in commands(Config(n),1)[:4]]
            self.assertTrue(all(y<256 for y in ys))
    def test_sanitize(self):
        s=design(Config('elastic'));sanitize(s)
        for extra in ['`include "secret"','// synthesis translate_off','initial $finish;','(* blackbox *)','always #1 clk=~clk;','bind tb evil x();']:
            with self.assertRaises(Rejected):sanitize(s+extra)
    def test_timeout(self):
        with tempfile.TemporaryDirectory() as d,self.assertRaises(Rejected):run(['/bin/sleep','3'],d,'timeout',.02)
    def test_formal_unknown(self):
        with patch('chip_rl.formal.run',side_effect=Rejected('timeout')):
            self.assertEqual(check_elastic(design(Config('elastic')))['status'],'unproven')
    def test_missing_tools_fail_closed(self):
        with patch('chip_rl.evaluate.tool',side_effect=Rejected('missing tool')),self.assertRaises(Rejected):TrustedEvaluator()
    def test_experimental_excluded(self):
        for n in ('dma','router','scoreboard','accelerator'):
            with self.assertRaises(ValueError):ChipEnv(n)
    def test_config_validation(self):
        for kw in ({'width':True},{'max_cells':0},{'max_cycles':'HDL'}):
            with self.assertRaises(ValueError):Config('dot',**kw)

class Boundary(unittest.TestCase):
    def test_source_only_and_private_seed(self):
        env=ChipEnv('elastic',horizon=1)
        with patch.object(env._evaluator,'evaluate',return_value={'tested_correct':True,'reward':1.}) as ev:
            obs,_=env.reset(99);self.assertEqual(ev.call_args.kwargs,{})
            obs['constraints']['config']['max_cells']=1
            self.assertNotEqual(env.observation()['constraints']['config']['max_cells'],1)
            for a in ({'seed':1,'rtl':''},{'stages':2},{'rtl':'','artifacts':'x'},{'rtl':'','constraints':{}},[]):
                with self.assertRaises(ValueError):env.step(a)
            env.step({'rtl':design(Config('elastic'))});self.assertEqual(ev.call_args.kwargs,{})
            with self.assertRaises(RuntimeError):env.step({'rtl':''})
    def test_server_injections(self):
        inp=[{'op':'reset','task':'elastic','seed':'1; $finish'}, {'op':'reset','task':'elastic','replay_seed':1}, {'op':'reset','task':'elastic','artifacts':'/tmp/test'}, {'op':'reset','task':'scoreboard'}, {'op':'reset','task':'dot','count':16}]
        out=io.StringIO();serve(io.StringIO(''.join(json.dumps(x)+'\n' for x in inp)),out)
        self.assertTrue(all(not json.loads(x)['ok'] for x in out.getvalue().splitlines()))
    def test_public_failure_coarse(self):
        q=TrustedEvaluator()
        with patch.object(q,'_synth',side_effect=Rejected('secret vector 123, functional mismatch')):
            r=q.evaluate(Config('elastic'),design(Config('elastic')))
        self.assertNotIn('123',json.dumps(r));self.assertNotIn('seed',r);self.assertEqual(r['reason'],'functional mismatch')
    def test_invalid_replay_seed(self):
        q=TrustedEvaluator()
        with patch.object(q,'_synth',side_effect=AssertionError('tool reached')):
            for seed in (True,-1,2**128,[],{},'initial'):
                self.assertFalse(q.evaluate(Config('dot'),design(Config('dot')),replay_seed=seed)['tested_correct'])


class HDLBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.q=TrustedEvaluator()
    def test_hard_cell_and_cycle_budgets(self):
        for c in (Config('elastic',max_cells=1),Config('elastic',max_cycles=2)):
            r=self.q.evaluate(c,design(c),replay_seed=2,count=16)
            self.assertFalse(r['tested_correct']);self.assertEqual(r['reward'],0)
    def test_interface(self):
        c=Config('elastic');r=self.q.evaluate(c,design(c).replace('input [511:0] in_data','input [510:0] in_data'),replay_seed=3,count=16)
        self.assertFalse(r['tested_correct']);self.assertEqual(r['reason'],'changed interface')
    def test_no_private_payload_on_success(self):
        r=self.q.evaluate(Config('elastic'),design(Config('elastic')),count=16)
        self.assertTrue(r['tested_correct']);self.assertEqual(r['reward'],1)
        for forbidden in ('seed','inputs','expected','logs','private_results'):
            self.assertNotIn(forbidden,r)
    def test_generated_clock(self):
        c=Config('elastic');s=design(c).replace('posedge clk','posedge in_valid')
        r=self.q.evaluate(c,s,replay_seed=2,count=16)
        self.assertFalse(r['tested_correct']);self.assertEqual(r['reason'],'clock contract violation')
    def test_async_reset(self):
        c=Config('elastic');s=design(c).replace('posedge clk','posedge clk or posedge rst')
        r=self.q.evaluate(c,s,replay_seed=2,count=16)
        self.assertFalse(r['tested_correct']);self.assertEqual(r['reason'],'clock contract violation')
    def test_missing_physical(self):
        from chip_rl.physical import physical
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            r=physical(Config('elastic'),design(Config('elastic')),Path(d)/'absent',Path(d)/'out')
            self.assertEqual(r['status'],'not_run');self.assertFalse(r['physical_verified'])

class MandatoryCoverage(unittest.TestCase):
    def test_no_legacy_count_can_shorten_profile(self):
        from chip_rl.coverage import cases
        for n in PILOT:
            c=Config(n)
            for seed in range(10):
                default=cases(c,seed)
                self.assertEqual(default,cases(c,seed,16))
                self.assertEqual(default,cases(c,seed,80))
                self.assertEqual(default,cases(c,seed,128))
                self.assertGreaterEqual(default[1][4],1024)
                self.assertTrue(all(x[4]>=128 for x in default))
    def test_lengths_vary_and_budget_explicit(self):
        from chip_rl.coverage import cases,BANDS
        c=Config('dot')
        lengths={cases(c,seed)[1][4] for seed in range(30)}
        self.assertGreater(len(lengths),20)
        for seed in range(30):
            for _,_,cc,secret,count,band in cases(c,seed):
                lo,hi=BANDS[band];self.assertTrue(lo<=count<=hi)
                xs=commands(cc,secret,count)
                _,_,limit=schedule(cc,len(xs),secret)
                self.assertLessEqual(limit,cc.max_cycles)

if __name__=='__main__':unittest.main()
