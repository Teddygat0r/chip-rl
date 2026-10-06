import unittest
from chip_rl.tasks import Config,Model,pack,workload,useful_work

class ReferenceTests(unittest.TestCase):
    def test_elastic_width(self): self.assertEqual(Model(Config('elastic',width=8)).step(0x123),0x23)
    def test_signed_dot_extremes(self):
        m=Model(Config('dot'))
        self.assertEqual(m.step(pack([128]*4+[128]*4,8)),65536)
        self.assertEqual(m.step(pack([128]*4+[127]*4,8)),(-65024)&0x3ffff)
    def test_tensor_layout(self):
        a=[1,2,3,4,5,6,7,8];b=[1,0,0,1,1,0,0,1]
        self.assertEqual(Model(Config('tensor')).step(pack(a+b,8)),pack([4,6,12,14],18))
    def test_banks_fair_read_write(self):
        m=Model(Config('scratchpad')); x=sum((1|(0<<2))<<(48*i) for i in range(4))
        self.assertEqual([m.step(x)&15 for _ in range(8)],[1,2,4,8]*2)
        self.assertEqual(m.step(3|(5<<2)|(123<<10)),1|(123<<8))
        self.assertEqual(m.step(1|(5<<2)),1|(123<<8))
    def test_router_contention_and_backpressure(self):
        m=Model(Config('router'));x=sum((1|((10+i)<<4))<<(32*i) for i in range(5))
        self.assertEqual(m.step(x),0)
        for i in range(5):self.assertEqual(m.step(x|(1<<160)),(1<<i)|(1<<8)|((10+i)<<16))
    def test_scoreboard_hazards_and_completion(self):
        m=Model(Config('scoreboard'));issue=1|(3<<5)|(2<<9)
        self.assertEqual(m.step(issue),1|(1<<11))
        dependent=(1|(3<<1)|(4<<5))<<24
        self.assertEqual(m.step(dependent),1<<11)
        self.assertEqual(m.step(dependent),1<<11)
        self.assertEqual(m.step(dependent),2|(1<<12))
    def test_dma_rows_masks_and_stalls(self):
        m=Model(Config('dma'));start=1|(3<<8)|(1<<24)|(1<<27)|(12<<32)
        self.assertEqual(m.step(start),1|(3<<8)|(120<<24))
        self.assertEqual(m.step(0),1|(3<<8)|(120<<24))
        self.assertEqual(m.step(2),1|(3<<8)|(120<<24))
        self.assertEqual((m.step(2)>>8)&65535,7)
        self.assertEqual((m.step(2)>>8)&65535,15)
        self.assertEqual(m.step(2),1|(19<<8)|(120<<24)|(1<<32))
        self.assertEqual(m.step(2),0)
    def test_accelerator_copy_then_dot(self):
        m=Model(Config('accelerator'))
        for i in range(4): m.step((i<<8)|((i+1)<<16))
        m.step(1|(8<<8)|(1<<16))
        self.assertEqual(m.step(3|(8<<8)),2)
        self.assertEqual(m.step(2),30)
    def test_cache_miss_ack_hit_conflict_write(self):
        m=Model(Config('cache'));a=12
        self.assertEqual(m.step(a<<8),4|(a<<40))
        self.assertEqual(m.step(0),4)
        self.assertEqual(m.step(2|(42<<24)),1|(42<<8))
        self.assertEqual(m.step(a<<8),3|(42<<8))
        self.assertEqual(m.step(1|(a<<8)|(99<<24)),9|(99<<8)|(a<<40))
        self.assertEqual(m.step(a<<8),3|(99<<8))
        self.assertEqual(m.step((a+1024)<<8),4|((a+1024)<<40))
    def test_gather_order_and_duplicates(self):
        m=Model(Config('gather'))
        for i in range(4):m.step(1|(i<<8)|((10+i)<<16))
        self.assertEqual(m.step((0b1011<<4)|pack([3,1,0,3],8)<<16),3|(pack([13,11,13],32)<<8))
        self.assertEqual(m.step(0),0)
    def test_seed_and_split(self):
        c=Config('router');self.assertEqual(workload(c,9),workload(c,9));self.assertNotEqual(workload(c,9),workload(c,10))
        self.assertNotEqual(workload(c,9),workload(c,9,split='heldout'))
if __name__=='__main__':unittest.main()
