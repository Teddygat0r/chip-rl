"""Independent list/dictionary reference functions, and an abstract retirement log."""
from collections import deque
from ..tasks import bits

def result(c,x):
 n=c.lanes
 if c.name=='permute':
  values=[bits(x,16*i,c.width) for i in range(n)];indices=[bits(x,128+3*i,3) for i in range(n)]
  return sum((values[j] if j<n and bits(x,152+i,1) else 0)<<(16*i) for i,j in enumerate(indices))
 if c.name=='coalesce':
  groups={}
  for i in range(n):
   if bits(x,128+i,1):
    base=bits(x,16*i,16)//c.width*c.width;groups[base]=groups.get(base,0)|(1<<i)
  return len(groups)|sum((base|(mask<<16))<<(8+24*j) for j,(base,mask) in enumerate(groups.items()))
 raise ValueError(c.name)

class Retirement:
 def __init__(self,c):self.c=c;self.entries=deque();self.next_ticket=0
 def step(self,x,valid=True):
  flush=bool(bits(x,2,1));head=self.entries[0] if self.entries else None
  rv=bool(head and head['done'] and not flush);pop=rv and bits(x,1,1)
  ready=(len(self.entries)<self.c.depth or pop) and not flush
  y=int(ready)|(int(rv)<<1)|(len(self.entries)<<72)
  allocate=valid and bits(x,0,1) and ready
  if allocate:y|=self.next_ticket<<8
  if rv:y|=(head['ticket']<<24)|(head['value']<<40)|(head['tag']<<56)
  if flush:self.entries.clear();return y
  if pop:self.entries.popleft()
  if bits(x,3,1):
   for e in self.entries:
    if e['ticket']==bits(x,16,16) and not e['done']:e['done']=True;e['value']=bits(x,32,self.c.width);break
  if allocate:
   self.entries.append(dict(ticket=self.next_ticket,tag=bits(x,64,16),done=False,value=0));self.next_ticket=(self.next_ticket+1)&65535
  return y


class Stateless:
 def __init__(self,c):self.c=c
 def step(self,x):return result(self.c,x)
def machine(c):
 if c.name in ('scan','topk','histogram'):
  from .collective_models import Stateless as CollectiveStateless,Histogram
  return Histogram(c) if c.name=='histogram' else CollectiveStateless(c)
 from .integrity_models import ECC,CRC,FreeList
 return {'ecc':ECC,'crc':CRC,'freelist':FreeList}.get(c.name,Stateless)(c)
