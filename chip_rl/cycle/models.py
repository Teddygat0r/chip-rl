"""Independent physical-cycle oracles. Outputs are sampled BEFORE each rising edge.
step() returns this cycle's outputs and advances state by exactly one clock.
"""
from collections import deque
from ..tasks import bits,signed

class DMA:
 def __init__(self,c):self.c=c;self.state='idle';self.src=self.dst=self.left=self.data=0;self.done=False
 def step(self,x,valid=True):
  st=self.state;y=int(st=='idle')|(int(st=='request')<<1)|(int(st=='response')<<2)|(int(st=='write')<<3)|(int(self.done)<<4)|(int(st!='idle')<<5)
  if st=='request':y|=self.src<<8
  if st=='write':y|=(self.dst<<16)|(self.data<<32)
  self.done=False
  if st=='idle' and valid and x&1:
   self.src=bits(x,8,8)%self.c.depth;self.dst=bits(x,16,8)%self.c.depth;self.left=bits(x,24,4)+1;self.state='request'
  elif st=='request' and bits(x,32,1):self.state='response'
  elif st=='response' and bits(x,33,1):self.data=bits(x,64,32);self.state='write'
  elif st=='write' and bits(x,34,1):
   self.left-=1
   if self.left==0:self.state='idle';self.done=True
   else:self.src=(self.src+1)%self.c.depth;self.dst=(self.dst+1)%self.c.depth;self.state='request'
  return y

class Router:
 def __init__(self,c):self.c=c;self.queues=[deque() for _ in range(5)];self.next=[0]*5
 def step(self,x,valid=True):
  y=0;accepted={}
  for p,q in enumerate(self.queues):
   if q:y|=(1<<p)|(q[0]<<(8+16*p))
   ready=bool(bits(x,160+p,1))
   if q and not ready:continue
   requests={i for i in range(5) if valid and bits(x,i*24,1) and bits(x,i*24+1,3)==p}
   order=sorted(requests,key=lambda i:(i-self.next[p])%5)
   if order:accepted[p]=order[0];y|=1<<(96+order[0])
  for p,q in enumerate(self.queues):
   if q and bits(x,160+p,1):q.popleft()
   if p in accepted:
    i=accepted[p];q.append(bits(x,i*24+4,self.c.width));self.next[p]=(i+1)%5
  return y

class Scoreboard:
 def __init__(self,c):self.c=c;self.time=0;self.ready_at=[0]*16;self.queues=[deque() for _ in range(c.k)];self.next=0
 def step(self,x,valid=True):
  # Absolute completion timestamps, independently of RTL countdown implementation.
  self.time+=1;y=0;winner=None
  for i in sorted(range(self.c.k),key=lambda i:(i-self.next)%self.c.k):
   if self.queues[i]:
    src,dst,lat,tag=self.queues[i][0]
    if self.ready_at[src]<=self.time and self.ready_at[dst]<=self.time:winner=i;break
  if winner is not None:
   src,dst,lat,tag=self.queues[winner].popleft();self.ready_at[dst]=self.time+lat;self.next=(winner+1)%self.c.k;y|=(1<<winner)|(tag<<24)
  for i,q in enumerate(self.queues):
   if not q and valid and bits(x,24*i,1):
    q.append((bits(x,24*i+1,4),bits(x,24*i+5,4),bits(x,24*i+9,3)+1,bits(x,24*i+12,8)));y|=1<<(32+i)
  y|=sum((t>self.time)<<(8+j) for j,t in enumerate(self.ready_at))
  return y

class Accelerator:
 def __init__(self,c):
  self.c=c;self.mem=[0]*c.depth;self.state='idle';self.src=self.dst=self.left=0;self.done=False
  self.active=False;self.ov=False;self.a=self.b=self.j=self.acc=self.result=0
 def step(self,x,valid=True):
  st=self.state;y=int(st=='idle')|(int(st=='request')<<1)|(int(st=='response')<<2)|(int(self.done)<<3)|(int(not self.active and not self.ov)<<4)|(int(self.ov)<<5)|(int(self.active)<<6)|(int(st!='idle')<<7)
  if st=='request':y|=self.src<<8
  if self.ov:y|=(self.result&0x3ffff)<<32
  # Reads precede a concurrent DMA write at this edge.
  if self.active:
   self.acc+=signed(self.mem[(self.a+self.j)%self.c.depth])*signed(self.mem[(self.b+self.j)%self.c.depth]);self.j+=1
   if self.j==self.c.k:self.result=self.acc;self.active=False;self.ov=True
  elif self.ov:
   if bits(x,34,1):self.ov=False
  elif valid and bits(x,1,1):self.a=bits(x,40,8)%self.c.depth;self.b=bits(x,48,8)%self.c.depth;self.j=self.acc=0;self.active=True
  self.done=False
  if st=='idle' and valid and x&1:self.src=bits(x,8,8)%self.c.depth;self.dst=bits(x,16,8)%self.c.depth;self.left=bits(x,24,4)+1;self.state='request'
  elif st=='request' and bits(x,32,1):self.state='response'
  elif st=='response' and bits(x,33,1):
   self.mem[self.dst]=bits(x,64,8);self.left-=1
   if self.left==0:self.state='idle';self.done=True
   else:self.src=(self.src+1)%self.c.depth;self.dst=(self.dst+1)%self.c.depth;self.state='request'
  return y
MODELS={'dma':DMA,'router':Router,'scoreboard':Scoreboard,'accelerator':Accelerator}
