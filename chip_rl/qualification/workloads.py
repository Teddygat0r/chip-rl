"""New distributions, independent expected results, and interrupted/reset epochs."""
import random
from .oracles import ecc8,coalesce,Histogram

def make(c,seed=808080):
 r=random.Random(seed);epochs=[]
 if c.name=='ecc':
  words=list(range(8192));r.shuffle(words)
  xs=[word|(1<<32)|(r.getrandbits(479)<<33)|(r.getrandbits(19)<<13) for word in words]
  xs += [data|(r.getrandbits(24)<<8)|(r.getrandbits(479)<<33) for data in range(256)]
  epochs.append({'name':'all_8192_received_words_and_256_encodings','pairs':[(x,ecc8(x)) for x in xs],'period':1})
  for hold in range(6):
   dirty=(37|(1<<32));epochs.append({'name':f'cancel_after_{hold}_clocks','pairs':[(dirty,ecc8(dirty))],'cut':1,'hold':hold})
   xs=[r.getrandbits(512) for _ in range(48)];epochs.append({'name':'post_reset','pairs':[(x,ecc8(x)) for x in xs],'period':3})
 elif c.name=='coalesce':
  for phase in ('all_one','all_distinct','boundary','zipf_hot','rotating_first','sparse'):
   xs=[]
   for t in range(1024):
    addresses=[]
    for lane in range(2*c.k):
     if phase=='all_one':a=((t*67)%65536//c.width)*c.width+r.randrange(c.width)
     elif phase=='all_distinct':a=(t*257+lane*c.width)&65535
     elif phase=='boundary':a=(65536-c.width+(lane%3)-1+t%2)&65535
     elif phase=='zipf_hot':a=(r.choice([0]*12+[1]*4+[2,3,511])*c.width+r.randrange(c.width))&65535
     elif phase=='rotating_first':a=(((lane+t)%3)*c.width+r.randrange(c.width))&65535
     else:a=r.randrange(65536)
     addresses.append(a)
    mask=(1<<(2*c.k))-1 if phase!='sparse' else r.getrandbits(2*c.k)
    x=r.getrandbits(512)
    for i,a in enumerate(addresses):x=(x&~(65535<<(16*i)))|(a<<(16*i))
    lane_mask=(1<<(2*c.k))-1;x=(x&~(lane_mask<<128))|(mask<<128)
    xs.append(x)
   epochs.append({'name':phase,'pairs':[(x,coalesce(c,x)) for x in xs],'period':2})
  for hold in range(10):
   x=0xffff|(1<<128);epochs.append({'name':'cancel','pairs':[(x,coalesce(c,x))],'cut':1,'hold':hold})
   x=(15<<128)|(1<<16);epochs.append({'name':'after_cancel','pairs':[(x,coalesce(c,x))]*8,'period':1})
 else:
  def epoch(xs,name,**kwargs):
   oracle=Histogram(c);epochs.append({'name':name,'pairs':[(x,oracle.step(x)) for x in xs],**kwargs})
  for phase in ('one_bin_wrap','rotating_collisions','invalid_mix','clear_storm'):
   xs=[]
   for t in range(2048 if phase=='one_bin_wrap' else 1152):
    x=r.getrandbits(512)
    def put(offset,width,value):
     nonlocal x
     x=(x&~(((1<<width)-1)<<offset))|((value&((1<<width)-1))<<offset)
    put(32,4,(1<<c.k)-1);put(40,1,phase=='clear_storm' and t%3!=0)
    for lane in range(c.k):
     index=0 if phase=='one_bin_wrap' else (t+lane%2)%c.depth
     if phase=='invalid_mix' and (t+lane)%3==0:index=255
     put(8*lane,8,index);put(48+8*lane,8,255 if t%2==0 else 1)
     put(128+8*lane,8,index if index<c.depth else t%c.depth)
    xs.append(x)
   epoch(xs,phase,period=3)
  for hold in range(c.k+4):
   dirty=sum((c.depth-1)<<(8*i) for i in range(c.k))|(((1<<c.k)-1)<<32)|sum(255<<(48+8*i) for i in range(c.k))
   epoch([dirty],'interrupted_atomic_updates',cut=1,hold=hold)
   xs=[]
   for base in range(0,c.depth,c.k):xs.append(sum(((base+i)%c.depth)<<(128+8*i) for i in range(c.k)))
   epoch(xs,'query_every_bin_after_reset',period=1)
 return epochs+reset_epochs(c,seed^0x525354)


def reset_epochs(c,seed):
 """Reset every occupied stage across all valid/ready control combinations.

 The payload is independent of each control combination. The following commands
 observe state before updating it; reset probes never interrupt scored long runs.
 """
 from .oracles import codeword
 r=random.Random(seed);epochs=[]
 def pairs(xs):
  if c.name=='histogram':
   m=Histogram(c);return [(x,m.step(x)) for x in xs]
  if c.name=='coalesce':return [(x,coalesce(c,x)) for x in xs]
  return [(x,codeword(c.width,x&((1<<c.width)-1))[0]|((x&((1<<c.width)-1))<<32)) for x in xs]
 if c.name=='histogram':
  dirty=sum((c.depth-1)<<(8*i) for i in range(c.k))|(((1<<c.k)-1)<<32)|sum(255<<(48+8*i) for i in range(c.k))
  clean=[sum(((base+i)%c.depth)<<(128+8*i) for i in range(c.k)) for base in range(0,c.depth,c.k)]
 elif c.name=='coalesce':
  dirty=0xffff|(1<<128);clean=[(15<<128)|(1<<16),0,(1<<128)|0xffff]
 else:dirty=37;clean=[0,1,(1<<c.width)-1,37]
 for valid in (0,1):
  for ready in (0,1):
   for cut in (1,2):
    for hold in range(10):
     label=f'v{valid}_r{ready}_cut{cut}_hold{hold}'
     epochs.append({'name':'interrupt_'+label,'score':False,'pairs':pairs([dirty]*cut),'cut':cut,'hold':hold})
     epochs.append({'name':'observe_'+label,'score':False,'pairs':pairs(clean),'period':2,
                    'reset_valid':valid,'reset_ready':ready,'reset_payload':r.getrandbits(512)})
 return epochs
