"""Second implementations: no imports from the task reference models/generators."""
from functools import lru_cache

def field(word,offset,width):return (word>>offset)&((1<<width)-1)

def codeword(width,data):
 parity=2
 while (1<<parity)<width+parity+1:parity+=1
 length=width+parity
 # Solve each even-parity equation over the data positions directly.
 data_slots=[p for p in range(1,length+1) if p&(p-1)]
 bits={p:(data>>i)&1 for i,p in enumerate(data_slots)}
 for p in (1<<i for i in range(parity)):bits[p]=sum(bits[d] for d in data_slots if d&p)&1
 word=sum(value<<(p-1) for p,value in bits.items())
 return word|((sum(bits.values())&1)<<length),length+1

@lru_cache(None)
def decode_table8():
 table={}
 for data in range(256):
  code,n=codeword(8,data)
  for error in [0]+[1<<i for i in range(n)]:
   received=code^error
   assert received not in table
   table[received]=code|(data<<32)|(bool(error)<<48)
 return table

def ecc8(word):
 if word&(1<<32):return decode_table8().get(word&8191,2<<48)
 data=word&255;return codeword(8,data)[0]|(data<<32)

def coalesce(c,word):
 addresses=[field(word,16*i,16) for i in range(2*c.k)]
 active=[i for i in range(2*c.k) if word>>(128+i)&1]
 representatives=[i for i in active if all(addresses[j]//c.width!=addresses[i]//c.width for j in active if j<i)]
 result=len(representatives)
 for slot,i in enumerate(representatives):
  members=sum(1<<j for j in active if addresses[j]//c.width==addresses[i]//c.width)
  result|=((addresses[i]//c.width)*c.width)<<(8+24*slot)
  result|=members<<(24+24*slot)
 return result

class Histogram:
 def __init__(self,c):self.c=c;self.history=[]
 def step(self,word):
  c=self.c;mask=(1<<c.width)-1
  if word>>40&1:self.history=[]
  # Reconstruct state from an event log, rather than the primary mutable array.
  sums={i:0 for i in range(c.depth)}
  for index,delta in self.history:sums[index]+=delta
  result=field(word,192,16)<<144
  for lane in range(c.k):
   index=field(word,8*lane,8)
   if word>>(32+lane)&1:
    if index in sums:
     result|=(sums[index]&mask)<<(16*lane);result|=1<<(128+lane)
     delta=field(word,48+8*lane,8);self.history.append((index,delta));sums[index]+=delta
    else:result|=1<<(132+lane)
  for lane in range(c.k):result|=(sums.get(field(word,128+8*lane,8),0)&mask)<<(64+16*lane)
  return result
