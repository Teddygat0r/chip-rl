"""Private long packets and ticket-wrap traces; bounded host-only generation."""
import random
from .oracles import PacketCRC,RetirementLedger

def crc_vectors(c,seed):
 r=random.Random(seed);oracle=PacketCRC(c.width);xs=[];ys=[];n=(65536+c.width//8-1)//(c.width//8)+32+r.randrange(32)
 for i in range(n):
  x=r.getrandbits(512);x&=~(3<<32);x|=(i==0)<<32;x|=(i==n-1)<<33
  xs.append(x);ys.append(oracle.step(x))
 # Error continuation, explicit restart of active state, start/end on one word.
 for start,end in [(0,0),(0,1),(1,0),(0,0),(1,0),(0,1),(1,1),(0,0)]:
  x=(r.getrandbits(512)&~(3<<32))|(start<<32)|(end<<33);xs.append(x);ys.append(oracle.step(x))
 return list(zip(xs,ys)),{'packet_words':n,'packet_bytes':n*(c.width//8),'byte_count_wraps':1,'responses':len(xs)}

def retirement_vectors(c,seed,target=None):
 r=random.Random(seed);m=RetirementLedger(c);rows=[(1,0,0,0)]*3;stats={'duplicate_completions':0,'out_of_order_completions':0,'full_replacements':0,'stalled_frames':0,'wraps':0}
 target=66000+r.randrange(512) if target is None else target
 phase=r.randrange(31);blocked=r.randrange(2,7);issue_phase=r.randrange(47);reverse_phase=r.randrange(7);duplicate_phase=r.randrange(19)
 flush_points=(1023+r.randrange(128),32767+r.randrange(128),65533,65537)
 cycle=0;flushed=set()
 while m.allocations<target or m.live:
  if cycle>=200000:raise ValueError('long retirement generation budget')
  allocating=m.allocations<target and not (m.sequence==65536 and m.live);ready=((cycle+phase)%31>=blocked)
  x=2*ready;valid=allocating and (cycle+issue_phase)%47!=0
  if allocating:x|=1
  # Flush around rollover without resetting the ticket counter.
  if m.allocations in flush_points and m.allocations not in flushed:
   x|=4;flushed.add(m.allocations)
  pending=[seq for seq in m.live if seq not in m.finished]
  chosen=None
  if m.finished and cycle%19==duplicate_phase:
   chosen=next(iter(m.finished));stats['duplicate_completions']+=1
  elif pending:
   chosen=pending[-1] if cycle%7==reverse_phase else pending[0]
   stats['out_of_order_completions']+=chosen!=m.live[0]
  if chosen is not None:x|=8|((chosen&65535)<<16)|(r.getrandbits(16)<<32)
  else:x|=8|(((m.sequence+123)&65535)<<16)|(r.getrandbits(16)<<32)
  x|=r.getrandbits(16)<<64|r.getrandbits(432)<<80
  before=m.allocations;y=m.step(x,valid)
  if y&2 and not ready:stats['stalled_frames']+=1
  if ((y>>72)&15)==c.depth and y&2 and ready and m.allocations>before:stats['full_replacements']+=1
  rows.append((0,int(valid),x,y));cycle+=1
 stats.update(allocations=m.allocations,retirements=m.retirements,flushes=m.flushes,wraps=m.allocations//65536)
 # Reset after wrap and verify ticket zero plus completion/retirement once again.
 rows.extend([(1,1,r.getrandbits(512),0)]*3);m=RetirementLedger(c)
 for x,v in [(1|(31<<64),1),(8|(23<<32),0),(2,0),(2,0)]:rows.append((0,v,x,m.step(x,v)))
 stats['frames']=len(rows)
 assert stats['wraps']>=1 and all(stats[k]>0 for k in ('duplicate_completions','out_of_order_completions','full_replacements','stalled_frames'))
 return rows,stats
