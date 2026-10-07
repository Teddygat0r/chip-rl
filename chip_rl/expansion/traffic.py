"""Generated workloads and independently checked retirement events."""
import random
from ..tasks import bits,pack
from .models import Retirement

def commands(c,seed,count):
 if c.name in ('scan','topk','histogram'):
  from .collective_traffic import commands as collective
  return collective(c,seed,count)
 if c.name in ('ecc','crc','freelist'):
  from .integrity_traffic import commands as extra_commands
  return extra_commands(c,seed,count)
 r=random.Random(seed);n=c.lanes;xs=[]
 for t in range(count+48):
  values=[r.randrange(65536) for _ in range(8)]
  mask=(0 if t==0 else (1<<n)-1 if t<32 else r.randrange(256))
  if c.name=='permute':
   indices=[(i if t%5==0 else n-1-i if t%5==1 else 0 if t%5==2 else r.randrange(8)) for i in range(n)]+[7]*(8-n)
   x=pack(values,16)|pack(indices,3)<<128|mask<<152;used=160
  else:
   base=r.randrange(65536)//c.width*c.width
   if t%5==0:values=[(base+r.randrange(c.width))&65535 for _ in range(8)]
   if t%5==1:values=[(base+i*c.width)&65535 for i in range(8)]
   if t%5==2:values=[(base+(i%2)*c.width+r.randrange(c.width))&65535 for i in range(8)]
   if t%5==3:values=[65535,0,c.width-1,c.width,32768,32769,65534,1]
   x=pack(values,16)|mask<<128;used=136
  xs.append(x|(r.getrandbits(512-used)<<used))
 return xs

def trace(c,seed,live):
 r=random.Random(seed);m=Retirement(c);rows=[];pending={};accepted=[];completed={};stale=[];tag=0;expected_ticket=0
 stats=dict(cycles=0,allocated=0,retired=0,flushes=0,resets=0,full_cycles=0,out_of_order_completions=0,stalled_cycles=0,ignored_completions=0)
 for t in range(live+128):
  reset=t<3 or t in (live//2,live//2+1)
  if reset:
   m=Retirement(c);pending={};accepted=[];completed={};stale=[];expected_ticket=0;rows.append((1,0,0,0));stats['resets']+=1;continue
  active=t<live;valid=not (t%113 in range(71,85));ready=not active or (t%41>=10 and r.random()<.8)
  flush=active and t%137==109
  x=(int(ready)<<1)|(int(flush)<<2)
  if active and valid and (t<50 or r.random()<.9):x|=1|(tag<<64);tag=(tag+1)&65535
  eligible=[ticket for ticket,(due,data) in pending.items() if due<=t]
  chosen=None;data=0
  if eligible:
   chosen=eligible[-1] if t%3 else r.choice(eligible);data=pending[chosen][1]
  elif stale and active and r.random()<.6:
   chosen=r.choice(stale);data=r.randrange(65536);stats['ignored_completions']+=1
  if chosen is not None:x|=(1<<3)|(chosen<<16)|(data<<32)
  x|=r.getrandbits(432)<<80
  y=m.step(x,valid)
  stats['cycles']+=1;stats['full_cycles']+=int(len(accepted)==c.depth)
  if bits(y,1,1):
   assert accepted and bits(y,24,16)==accepted[0][0]
   ticket,program=accepted[0];assert ticket in completed
   assert bits(y,40,16)==completed[ticket] and bits(y,56,16)==program
   if ready:accepted.pop(0);completed.pop(ticket);stats['retired']+=1
   else:stats['stalled_cycles']+=1
  if flush:
   stale.extend(ticket for ticket,_ in accepted);pending.clear();accepted=[];completed={};stats['flushes']+=1
  else:
   if chosen in pending:
    if accepted and chosen!=accepted[0][0]:stats['out_of_order_completions']+=1
    completed[chosen]=data&((1<<c.width)-1);del pending[chosen];stale.append(chosen)
   if bits(y,0,1) and valid and x&1:
    ticket=bits(y,8,16);assert ticket==expected_ticket;expected_ticket=(expected_ticket+1)&65535;assert ticket not in dict(accepted)
    accepted.append((ticket,bits(x,64,16)));stats['allocated']+=1
    # Deliberately delay selected oldest instructions while younger ones complete.
    pending[ticket]=(t+(35 if ticket%7==0 else r.randrange(1,9)),r.randrange(65536))
  rows.append((0,int(valid),x,y))
 assert not accepted and not pending and not m.entries
 assert stats['retired']>0 and stats['out_of_order_completions']>0 and stats['full_cycles']>0 and stats['stalled_cycles']>0
 return rows,stats
