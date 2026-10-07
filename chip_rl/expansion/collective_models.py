"""Original ordered-prefix, stable selection and counter references."""
from ..tasks import bits

def signed(value,width):return (value^(1<<(width-1)))-(1<<(width-1))

def scan(c,x):
 acc=bits(x,160,32);out=0
 for i in range(c.lanes):
  if not bits(x,128+i,1):continue
  if bits(x,136+i,1):acc=0
  value=signed(bits(x,16*i,c.width),c.width)
  before=acc;acc=(acc+value)&0xffffffff
  out|=(before if bits(x,144,1) else acc)<<(32*i)
 return out

def topk(c,x):
 ordered=sorted([(signed(bits(x,16*i,c.width),c.width),i) for i in range(c.lanes) if bits(x,128+i,1)],key=lambda p:(-p[0],p[1]))
 chosen=ordered[:min(bits(x,136,3),c.k)];out=len(chosen)
 for j,(value,index) in enumerate(chosen):out|=((value&65535)|(index<<16))<<(8+24*j)
 return out

class Histogram:
 def __init__(self,c):self.c=c;self.bins=[0]*c.depth
 def step(self,x):
  c=self.c;out=bits(x,192,16)<<144;mask=(1<<c.width)-1
  if bits(x,40,1):self.bins=[0]*c.depth
  old=self.bins.copy();deltas=[0]*c.depth
  for i in range(c.k):
   index=bits(x,8*i,8)
   if bits(x,32+i,1):
    if index>=c.depth:out|=1<<(132+i)
    else:
     out|=self.bins[index]<<(16*i);out|=1<<(128+i)
     delta=bits(x,48+8*i,8);self.bins[index]=(self.bins[index]+delta)&mask;deltas[index]+=delta
  assert all(self.bins[i]==(old[i]+deltas[i])&mask for i in range(c.depth))
  for i in range(c.k):
   index=bits(x,128+8*i,8)
   if index<c.depth:out|=self.bins[index]<<(64+16*i)
  return out
class Stateless:
 def __init__(self,c):self.c=c
 def step(self,x):return globals()[self.c.name](self.c,x)
