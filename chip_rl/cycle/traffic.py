"""Protocol-aware stimuli plus independent transaction/property monitors.
Driving follows the oracle's ready signals; any DUT timing divergence is a failure
of this explicitly fixed-cycle controller contract, not allowed latency flexibility.
"""
import random
from ..tasks import bits,signed
from .models import MODELS

def trace(c,seed,live=640):
 r=random.Random(seed);m=MODELS[c.name](c);rows=[];n=c.name
 memory=[r.getrandbits(32) for _ in range(c.depth)];memory[:4]=[128]*4
 pending=None;pending_inputs=[None]*5;expected=[[] for _ in range(5)];next_id=1
 job=[];history=[[] for _ in range(c.depth)];dot_jobs=[];setup=0
 stats=dict(cycles=0,accepted=0,retired=0,resets=0,overlap_cycles=0,idle_clocks=0,fair_grants=[],nonzero_results=0)
 for t in range(live+160):
  reset=t<3 or t in (live//2,live//2+1)
  if reset:
   m=MODELS[n](c);pending=None;pending_inputs=[None]*5;expected=[[] for _ in range(5)];job=[];history=[[] for _ in range(c.depth)];dot_jobs=[];setup=0
   rows.append((1,0,0,0));stats['resets']+=1;continue
  active=t<live;valid=not (120<=t%320<152);x=0
  if not valid:stats['idle_clocks']+=1
  if n in ('dma','accelerator'):
   rr=(not active or t%71>=9) and r.random()<.85;wr=(not active or t%47>=11) and r.random()<.75
   if not active:rr=wr=True
   x=(int(rr)<<32)|(int(wr)<<34)
   if pending is not None and pending[0]<=t:x|=(1<<33)|(pending[1]<<64)
   if active and m.state=='idle' and valid and (setup==0 or r.randrange(3)==0):
    src,dst,length=(0,0,4) if setup==0 else (r.randrange(c.depth),r.randrange(c.depth),r.randrange(1,17))
    x|=1|(src<<8)|(dst<<16)|((length-1)<<24);setup+=1
   if n=='accelerator' and active and not m.active and not m.ov and valid:
    a,b=(0,0) if setup==1 and m.state=='idle' else (r.randrange(c.depth),r.randrange(c.depth))
    x|=2|(a<<40)|(b<<48)
   y=m.step(x,valid)
   if bits(y,4 if n=='dma' else 3,1):assert not job
   if y&1 and valid and x&1:
    job=[((bits(x,16,8)+i)%c.depth,memory[(bits(x,8,8)+i)%c.depth]) for i in range(bits(x,24,4)+1)];stats['accepted']+=len(job)
   if bits(y,1,1) and rr:
    assert pending is None;pending=(t+(r.randrange(1,8) if active else 1),memory[bits(y,8,8)])
   if bits(y,2,1) and bits(x,33,1):
    assert pending is not None;pending=None
    if n=='accelerator':
     addr,data=job.pop(0);assert bits(x,64,8)==data&255
     history[addr].append((t,data&255));stats['retired']+=1
   if n=='dma' and bits(y,3,1) and wr:
    assert job;addr,data=job.pop(0);assert (bits(y,16,8),bits(y,32,32))==(addr,data);stats['retired']+=1
   if n=='accelerator':
    stats['overlap_cycles']+=int(bool(bits(y,6,1) and bits(y,7,1)))
    if bits(y,4,1) and valid and bits(x,1,1):dot_jobs.append((t,bits(x,40,8),bits(x,48,8)))
    if bits(y,5,1):
     assert dot_jobs;start,a,b=dot_jobs[0]
     assert t>=start+c.k+1
     def value(addr,when):return next((v for ts,v in reversed(history[addr%c.depth]) if ts<when),0)
     want=sum(signed(value(a+j,start+j+1))*signed(value(b+j,start+j+1)) for j in range(c.k))&0x3ffff
     assert bits(y,32,18)==want,(t,want,bits(y,32,18))
     if wr:dot_jobs.pop(0);stats['nonzero_results']+=int(want!=0)
  else:
   k=5 if n=='router' else c.k
   for i in range(k):
    if pending_inputs[i] is None and active and (t<80 or r.random()<.8):
     if n=='router':pending_inputs[i]=(next_id,0 if t<80 else r.randrange(5));next_id+=1
     else:pending_inputs[i]=(15 if t<80 else r.randrange(8),i if t<80 else r.randrange(8),1 if t<80 else r.randrange(1,9),next_id%256);next_id+=1
    if pending_inputs[i] is not None:
     if n=='router':tag,dest=pending_inputs[i];slot=1|(dest<<1)|(tag<<4)
     else:src,dst,lat,tag=pending_inputs[i];slot=1|(src<<1)|(dst<<5)|((lat-1)<<9)|(tag<<12)
     x|=slot<<(24*i)
   if n=='router':
    ready=31 if t<80 or not active else sum(int(r.random()<.6 and t%53>=8)<<p for p in range(5));x|=ready<<160
   y=m.step(x,valid)
   if n=='router':
    for p in range(5):
     if bits(y,p,1) and bits(x,160+p,1):
      assert expected[p] and bits(y,8+16*p,16)==expected[p].pop(0);stats['retired']+=1
    for i in range(5):
     if bits(y,96+i,1):
      assert valid and pending_inputs[i] is not None;tag,dest=pending_inputs[i];expected[dest].append(tag&((1<<c.width)-1));assert len(expected[dest])<=1;pending_inputs[i]=None;stats['accepted']+=1
      if t<80:stats['fair_grants'].append(i)
   else:
    for i in range(k):
     if bits(y,i,1):
      assert expected[i] and bits(y,24,8)==expected[i].pop(0);stats['retired']+=1
      if t<80:stats['fair_grants'].append(i)
    for i in range(k):
     if bits(y,32+i,1):
      assert valid and pending_inputs[i] is not None;expected[i].append(pending_inputs[i][3]);assert len(expected[i])<=1;pending_inputs[i]=None;stats['accepted']+=1
  rows.append((0,int(valid),x,y));stats['cycles']+=1
 # A reset may abort previously accepted work, but every surviving command drains.
 if n in ('dma','accelerator'):assert not job and pending is None and m.state=='idle'
 else:assert not any(expected) and not any(pending_inputs[:5 if n=='router' else c.k])
 if n=='accelerator':assert not dot_jobs and not m.active and not m.ov;assert stats['overlap_cycles']>0 and stats['nonzero_results']>0
 if n in ('router','scoreboard'):
  grants=stats['fair_grants'];k=5 if n=='router' else c.k
  assert grants[:k*3]==list(range(k))*3,(n,grants[:k*3])
 assert stats['accepted']>0 and stats['retired']>0
 return rows,stats
