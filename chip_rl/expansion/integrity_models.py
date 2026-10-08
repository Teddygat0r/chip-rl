"""Original integrity/allocation oracles. ECC decoding uses nearest-codeword search.
CRC uses Python's zlib implementation, independent of the RTL polynomial recurrence.
"""
from functools import lru_cache
import zlib
from ..tasks import bits,pack

def positions(width):
 p=next(p for p in range(2,7) if 2**p>=width+p+1)
 return width+p,[i for i in range(1,width+p+1) if i&(i-1)]
@lru_cache(maxsize=65536)
def encode(width,value):
 h,loc=positions(width);word=sum(((value>>j)&1)<<(pos-1) for j,pos in enumerate(loc))
 for parity in (1<<i for i in range(h.bit_length())):
  word|=(sum((word>>(j-1))&1 for j in range(1,h+1) if j&parity)%2)<<(parity-1)
 return word|((word.bit_count()%2)<<h)
def ecc(c,x):
 h,loc=positions(c.width)
 if not bits(x,32,1):
  data=bits(x,0,c.width);return encode(c.width,data)|(data<<32)
 received=bits(x,0,h+1);raw=sum(((received>>(pos-1))&1)<<j for j,pos in enumerate(loc))
 # Any one-bit correction changes at most one payload bit. Search legal codewords
 # instead of reproducing the RTL's syndrome arithmetic and correction selection.
 for data in [raw]+[raw^(1<<j) for j in range(c.width)]:
  canonical=encode(c.width,data);distance=(canonical^received).bit_count()
  if distance<=1:return canonical|(data<<32)|(int(distance==1)<<48)
 return 2<<48

class CRC:
 def __init__(self,c):self.c=c;self.active=False;self.value=0;self.length=0
 def step(self,x):
  tag=bits(x,48,16)<<48;start=bits(x,32,1);end=bits(x,33,1)
  if not self.active and not start:return tag|(1<<33)
  if start:self.value=0;self.length=0
  payload=bits(x,0,self.c.width).to_bytes(self.c.width//8,'little')
  self.value=zlib.crc32(payload,self.value);self.length=(self.length+len(payload))&65535;self.active=not end
  return self.value|(end<<32)|tag|(self.length<<64)

class FreeList:
 def __init__(self,c):self.c=c;self.free=set(range(c.depth))
 def step(self,x):
  tag=bits(x,48,16)<<96
  if bits(x,3,1):self.free=set(range(self.c.depth));return tag|(len(self.free)<<8)
  count=bits(x,0,3);released={i for i in range(32) if bits(x,16+i,1)}
  if count>self.c.k or released & self.free or any(i>=self.c.depth for i in released):return tag|8|(len(self.free)<<8)
  self.free|=released;chosen=sorted(self.free)[:count];self.free-=set(chosen)
  return tag|len(chosen)|(len(self.free)<<8)|(sum(1<<i for i in chosen)<<16)|(pack(chosen,8)<<64)

class ECC:
 def __init__(self,c):self.c=c
 def step(self,x):return ecc(self.c,x)
