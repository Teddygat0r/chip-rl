from ..memory.oracles import PageTables as OriginalPageTables
class PageTables(OriginalPageTables):
 def __init__(self,seed):
  super().__init__(seed)
  for g,mem in enumerate(self.tables):
   root=0x8004;mem[root]|=1;base=mem[root]&0xfffc
   for lo in range(16):
    ppn,_,_=self.flat[g][0,16+lo];mem[base+lo*4]=(ppn<<8)|15
    self.flat[g][0,16+lo]=(ppn,15,True)
def signed_byte(x):return (x&255)-256 if x&128 else x&255
def arithmetic(c,x):
 values=[]
 for r in range(c.m):
  for col in range(c.n):
   values.append(sum(signed_byte(x>>(8*(16*r+k)))*signed_byte(x>>(512+8*(4*k+col))) for k in range(c.k)))
 return sum((v&0xffffff)<<(24*i) for i,v in enumerate(values))
def independent(c,x):
 raw=x.to_bytes(128,'little');a=[[int.from_bytes(raw[16*r+k:16*r+k+1],'little',signed=True) for k in range(c.k)] for r in range(c.m)]
 b=[[int.from_bytes(raw[64+4*k+n:65+4*k+n],'little',signed=True) for n in range(c.n)] for k in range(c.k)]
 out=bytearray(48)
 for r,row in enumerate(a):
  for n in range(c.n):out[3*(r*c.n+n):3*(r*c.n+n)+3]=sum(v*b[k][n] for k,v in enumerate(row)).to_bytes(3,'little',signed=True)
 return int.from_bytes(out,'little')
