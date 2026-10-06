"""Cover every default cache index and isolate every address tag bit."""
import tempfile,unittest
from pathlib import Path
from chip_rl.tasks import Config,Model
from chip_rl.rtl import design
from chip_rl.alternates import alternate
from chip_rl.evaluate import bench,simulate,Rejected

def exercise(source):
    c=Config('cache');xs=[]
    # Alternating each one-hot tag with zero exposes ignored high tag bits.
    for tag in (0,1,0,2,0,4,0,8,0,16,0,32,0,63):
        for ix in range(256):
            addr=(tag<<10)|(ix<<2);value=0xa5000000|(tag<<16)|ix
            xs.extend([addr<<8,2|(value<<24),addr<<8])
    model=Model(c);ys=[model.step(x) for x in xs]
    with tempfile.TemporaryDirectory() as td:
        d=Path(td);(d/'candidate.sv').write_text(source)
        (d/'inputs.hex').write_text(''.join(f'{x:0128x}\n' for x in xs))
        (d/'expected.hex').write_text(''.join(f'{y:064x}\n' for y in ys))
        (d/'weights.hex').write_text('00000001\n'*len(xs))
        (d/'tb.sv').write_text(bench(xs,ys,73,30000))
        return simulate(d,'candidate.sv','cache-addressing')

class CacheAddressingTests(unittest.TestCase):
    def test_full_index_and_tag_bit_walk(self):
        for variant in (design,alternate):
            with self.subTest(variant=variant.__name__):self.assertEqual(exercise(variant(Config('cache')))['transactions'],10752)
    def test_index_and_tag_truncation_mutants(self):
        c=Config('cache');s=design(c)
        for mutant in (s.replace('ix=(addr/4)%256','ix=(addr/4)%128'),
                       s.replace('tg=addr/1024','tg=(addr/1024)%32').replace('tag[pi]<=pa/1024','tag[pi]<=(pa/1024)%32')):
            with self.assertRaises(Rejected):exercise(mutant)
if __name__=='__main__':unittest.main()
