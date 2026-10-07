import random

def commands(c,seed,count):
 r=random.Random(seed);xs=[]
 for t in range(count+64):
  x=r.getrandbits(512)
  def put(offset,width,value):
   nonlocal x
   x=(x&~(((1<<width)-1)<<offset))|((value&((1<<width)-1))<<offset)
  if c.name in ('scan','topk'):
   for i in range(c.lanes):
    values=(0,1,(1<<(c.width-1))-1,1<<(c.width-1),(1<<c.width)-1)
    value=values[t%len(values)] if t%7<3 else r.randrange(1<<c.width)
    put(16*i,c.width,value)
   put(128,8,(1<<c.lanes)-1 if t%5==0 else 0 if t%11==0 else r.getrandbits(8))
   if c.name=='scan':
    put(136,8,0 if t%5==0 else 255 if t%5==1 else r.getrandbits(8));put(144,1,t%2)
    put(160,32,(0,0x7fffffff,0x80000000,0xffffffff)[t%4] if t%3==0 else r.getrandbits(32))
   else:put(136,3,t%8)
  else:
   put(40,1,t%71==1);put(32,4,15 if t%4==0 else r.getrandbits(4))
   for i in range(c.k):
    index=(t//4)%c.depth if t%4==0 else r.randrange(c.depth) if t%4<3 else r.randrange(256)
    put(8*i,8,index);put(48+8*i,8,255 if t%3==0 else r.randrange(256))
    put(128+8*i,8,index if t%3==0 else r.randrange(c.depth+8))
   if t==0:
    put(40,1,0);put(32,4,0);put(128,32,0) # inspect zero state after dirty reset
  xs.append(x)
 if c.name=='histogram':
  # Sustained collisions cross 16-bit wrap even at K=2 before any clear.
  hot=(((1<<c.k)-1)<<32)|sum(255<<(48+8*i) for i in range(c.k))
  xs=xs[:1]+[hot|(r.getrandbits(304)<<208) for _ in range(192)]+xs[1:]
 return xs
