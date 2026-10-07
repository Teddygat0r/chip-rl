"""Independent digital event schedules: phases, pauses, backpressure and reset epochs."""
import random

def make(c,seed,heldout=False):
 r=random.Random(seed);profiles=[(2,3),(5,1),(1,5),(3,3),(7,4)] if not heldout else [(4,7),(2,9),(9,2),(5,5),(1,1)]
 epochs=[]
 for pi,(wp,rp) in enumerate(profiles):
  wphase=r.randrange(wp);rphase=wphase if wp==rp else r.randrange(rp)
  reset_end=8*max(wp,rp)+5;warm=8*c.depth+30
  controls=[]
  pause_start=2*warm+reset_end+80;pause_len=19+r.randrange(19)
  for t in range(c.max_ticks+100):
   w=int(t%wp==wphase and not pause_start<=t<pause_start+pause_len)
   rr=int(t%rp==rphase and not pause_start+110<=t<pause_start+110+pause_len)
   wrst=t<reset_end-2*max(wp,rp);rrst=t<reset_end-max(wp,rp)
   local=t-reset_end
   alloww=local>=0 and (local<warm or local>=2*warm and r.randrange(5)!=0)
   allowr=local>=warm and (local<2*warm or r.randrange(4)!=0)
   if t>c.max_ticks//2:alloww=allowr=True
   controls.append(w|(rr<<1)|(int(wrst)<<2)|(int(rrst)<<3)|(int(alloww)<<4)|(int(allowr)<<5))
  count=(32+r.randrange(8))*2*c.depth+1
  def epoch(label,n,cut=0,hold=0,score=False):
   xs=[r.getrandbits(c.width) for _ in range(n)]
   for i in range(min(n,2*c.depth)):xs[i]=(i*31+pi)&((1<<c.width)-1)
   epochs.append({'name':label,'inputs':xs,'controls':controls,'cut':cut,'hold':hold,'score':score,'w_period':wp,'r_period':rp,'w_phase':wphase,'r_phase':rphase})
  epoch(f'profile{pi}',count,score=True)
  for cut,hold in ((1,0),(c.depth,5*max(wp,rp))):
   epoch(f'interrupt{pi}-{cut}',c.depth+1,cut,hold)
   epoch(f'post_reset{pi}-{cut}',2*c.depth+3)
 return epochs
