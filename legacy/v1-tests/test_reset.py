"""Cold-memory reads plus a dirty-state reset for every stateful family.
Unlike bulk initialization workloads, these observations cannot mask missing reset.
"""
import tempfile,unittest
from pathlib import Path
from chip_rl.tasks import Config,Model
from chip_rl.rtl import design
from chip_rl.alternates import alternate
from chip_rl.evaluate import bench,simulate,Rejected

# Two accepted priming commands in the common bench modify state. It then resets
# with work buffered. Check state immediately, before initialization can hide it.
CASES={
 'scratchpad':(3|(7<<2)|(0xdeadbeef<<10),[1|(7<<2)]),
 'accelerator':((7<<8)|(0xdeadbeef<<16),[3|(7<<8)]),
 'gather':(1|(7<<8)|(0xdeadbeef<<16),[(1<<4)|(7<<16)]),
 'cache':(12<<8,[0,2|(123<<24),0]),
 'dma':(1|(5<<8)|(7<<24)|(7<<27)|(13<<32),[0,2]),
 'scoreboard':(1|(7<<5)|(7<<9),[0,0]),
 'router':((31<<160)|sum((1|((j+9)<<4))<<(32*j) for j in range(5)),[(31<<160)|sum((1|((j+9)<<4))<<(32*j) for j in range(5))]),
}

def reset_probe(c,source):
    dirty,xs=CASES[c.name];model=Model(c);ys=[model.step(x) for x in xs]
    with tempfile.TemporaryDirectory() as td:
        d=Path(td);(d/'candidate.sv').write_text(source)
        (d/'inputs.hex').write_text(''.join(f'{x:0128x}\n' for x in xs))
        (d/'expected.hex').write_text(''.join(f'{x:064x}\n' for x in ys))
        (d/'weights.hex').write_text('00000001\n'*len(xs))
        tb=bench(xs,ys,17,200)
        tb=tb.replace('in_data=inputs[0];out_ready=0;',f"in_data=512'h{dirty:x};out_ready=0;")
        (d/'tb.sv').write_text(tb);return simulate(d,'candidate.sv','reset')

class ResetTests(unittest.TestCase):
    def test_state_cleared_before_initialization(self):
        for name in CASES:
            c=Config(name,depth=16)
            for variant in (design,alternate):
                with self.subTest(task=name,variant=variant.__name__):reset_probe(c,variant(c))
    def test_missing_memory_reset_is_rejected(self):
        for name in ('scratchpad','accelerator','gather'):
            c=Config(name,depth=16);s=design(c).replace('mem[z]<=0;','mem[z]<=mem[z];')
            with self.subTest(task=name),self.assertRaises(Rejected):reset_probe(c,s)
if __name__=='__main__':unittest.main()
