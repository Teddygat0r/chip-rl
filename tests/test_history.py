import unittest,random
from chip_rl.expansion.spec import Config
from chip_rl.history.oracles import PacketCRC,RetirementLedger
from chip_rl.history.workloads import crc_vectors,retirement_vectors
from chip_rl.expansion.integrity_models import CRC
from chip_rl.expansion.models import Retirement

class LongHistories(unittest.TestCase):
 def test_known_crc_check_value(self):
  m=PacketCRC(8)
  for i,b in enumerate(b'123456789'):y=m.step(b|((i==0)<<32)|((i==8)<<33))
  self.assertEqual(y&0xffffffff,0xcbf43926);self.assertEqual(y>>64,9)
 def test_crc_long_history_against_library_oracle(self):
  for width in (8,16,24):
   c=Config('crc',width=width);pairs,stats=crc_vectors(c,77);m=CRC(c)
   self.assertGreater(stats['packet_bytes'],65536)
   for x,y in pairs:self.assertEqual(y,m.step(x))
   n=stats['packet_words'];self.assertEqual(pairs[n-1][1]>>64,(n*(width//8))&65535)
 def test_crc_invalid_does_not_mutate_state(self):
  m=PacketCRC(16);self.assertEqual(m.step(1),1<<33)
  self.assertEqual(m.step(3|(1<<32)),PacketCRC(16).step(3|(1<<32)))
 def test_retirement_long_history_against_primary(self):
  c=Config('retire',width=12,depth=6);rows,stats=retirement_vectors(c,55)
  m=Retirement(c)
  for rst,v,x,y in rows:
   if rst:m=Retirement(c)
   else:self.assertEqual(m.step(x,bool(v)),y)
  self.assertGreater(stats['allocations'],65536);self.assertEqual(stats['wraps'],1)
  self.assertTrue(all(stats[k]>0 for k in ('flushes','duplicate_completions','full_replacements','stalled_frames')))
 def test_long_budget_is_not_default_cycle_override(self):
  from chip_rl.history.evaluate import CYCLE_BUDGET
  from chip_rl.expansion.spec import specification
  c=Config('crc',max_cycles=128);self.assertEqual(c.max_cycles,128)
  self.assertEqual(specification(c)['long_history_verification']['cycle_budget'],CYCLE_BUDGET['crc'])
  with self.assertRaises(ValueError):Config('crc',max_cycles=900000)

 def test_wrap_drain_exposes_live_high_ticket_completion(self):
  for depth in (4,6,8):
   for seed in (12,45,99):
    rows,stats=retirement_vectors(Config('retire',depth=depth),seed)
    allocated=0;found=False
    for rst,v,x,y in rows:
     if rst:allocated=0;continue
     if v and x&1 and y&1:allocated+=1
     if allocated==65536 and not v and x&8 and ((x>>16)&65535)>=65530:found=True
    self.assertTrue(found,(depth,seed))
