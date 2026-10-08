import random
from ..tasks import bits
from .integrity_models import encode,positions,FreeList

def commands(c,seed,count):
 r=random.Random(seed);xs=[]
 if c.name=='ecc':
  h,_=positions(c.width)
  for data in (0,1,(1<<c.width)-1,1<<(c.width-1)):
   code=encode(c.width,data);xs.append(data);xs.append(code|(1<<32))
   for i in range(h+1):xs.append((code^(1<<i))|(1<<32))
   for i in range(h+1):xs.append((code^(1<<i)^(1<<((i+1)%(h+1))))|(1<<32))
  for t in range(count):
   data=r.randrange(1<<c.width);code=encode(c.width,data)
   if t%7==0:xs.append(data);continue
   for i in r.sample(range(h+1),t%4):code^=1<<i
   xs.append(code|(1<<32))
  xs=[x|(r.getrandbits(32-(h+1 if bits(x,32,1) else c.width))<<(h+1 if bits(x,32,1) else c.width)) for x in xs]
  used=33
 elif c.name=='crc':
  # Begin with an invalid continuation: reset must cancel the primed packet.
  xs=[0,1<<33];remaining=0
  for t in range(count+64):
   start=(remaining==0 or t%97==0);remaining=(1+(t%23)) if start else remaining
   remaining-=1;end=remaining==0
   x=r.getrandbits(c.width)|(int(start)<<32)|(int(end)<<33)|(r.randrange(65536)<<48)
   xs.append(x)
   if end:xs.append(r.getrandbits(c.width)|(r.randrange(65536)<<48))
  xs=[x|(r.getrandbits(32-c.width)<<c.width)|(r.getrandbits(14)<<34) for x in xs]
  used=64
 else:
  m=FreeList(c);allocated=set();xs=[]
  for t in range(count+64):
   if t==0:x=0
   elif t%53==0:x=8 # flush
   elif t%11==0:x=r.randrange(1,8)|(r.getrandbits(32)<<16) # invalid frees/counts
   else:
    owned=sorted(set(range(c.depth))-m.free)
    chosen=r.sample(owned,r.randrange(min(len(owned),c.k)+1))
    x=(c.k if t%9<5 else r.randrange(c.k+1))|(sum(1<<i for i in chosen)<<16)
   x|=(r.randrange(65536)<<48)|(r.getrandbits(12)<<4)
   # Separate ownership/conservation monitor, grounded in accepted operation events.
   y=m.step(x);grant=(y>>16)&0xffffffff
   if x&8:allocated.clear()
   elif not y&8:
    released={i for i in range(c.depth) if bits(x,16+i,1)}
    assert released<=allocated;allocated-=released
    ids=[i for i in range(c.depth) if grant>>i&1]
    assert not set(ids)&allocated and len(ids)==(y&7)
    allocated|=set(ids)
   assert len(allocated)+bits(y,8,6)==c.depth
   xs.append(x)
  used=64
 return [x|(r.getrandbits(512-used)<<used) for x in xs]
