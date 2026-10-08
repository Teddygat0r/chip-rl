"""Architectural results from concrete memory tables, independent of DUT state."""
import random
class Memory:
 def __init__(self,seed):
  r=random.Random(seed);self.lines=[r.getrandbits(128) for _ in range(16384)]
 def load(self,address):return (self.lines[address//4]>>(32*(address%4)))&0xffffffff
class PageTables:
 # Small custom format, explicitly NOT an implementation of an ISA MMU.
 def __init__(self,seed):
  r=random.Random(seed);self.tables=[];self.flat=[];base_ppn=r.randrange(256)
  for generation in range(4):
   mem={};truth={}
   for asid in range(4):
    permutation=list(range(16));r.shuffle(permutation)
    for hi in range(16):
     base=0x1000+asid*0x1000+permutation[hi]*64
     mem[0x8000+asid*256+hi*4]=base|int(r.randrange(9)!=0)
     for lo in range(16):
      ppn=r.randrange(256);flags=r.randrange(16)
      mem[base+lo*4]=(ppn<<8)|flags
      truth[asid,(hi<<4)|lo]=(ppn,flags,bool(mem[0x8000+asid*256+hi*4]&1))
   for asid in (0,1):
    root=0x8000+asid*256;mem[root]|=1;base=mem[root]&0xfffc
    for vpn in range(16):
     ppn,flags,_=truth[asid,vpn];truth[asid,vpn]=(ppn,flags,True)
    for vpn,flags in ((0,15),(1,1),(2,0)):
     ppn=(base_ppn+generation*37+asid*13+vpn*7)&255
     mem[base+vpn*4]=(ppn<<8)|flags;truth[asid,vpn]=(ppn,flags,True)
   root=0x8000+4;mem[root]|=1;base=mem[root]&0xfffc
   for lo in range(16):
    vpn=16+lo;ppn,flags,_=truth[0,vpn];truth[0,vpn]=(ppn,flags,True)
   for lo in range(8):
    vpn=16+lo;ppn=(base_ppn+generation*37+vpn*7)&255
    mem[base+lo*4]=(ppn<<8)|15;truth[0,vpn]=(ppn,15,True)
   self.tables.append(mem);self.flat.append(truth)
 def translate(self,address,aux,generation):
  asid=aux&3;vpn=address>>8;mem=self.tables[generation]
  root=mem[0x8000+asid*256+(vpn>>4)*4]
  if not root&1:return (0,1)
  leaf=mem[(root&0xfffc)+(vpn&15)*4]
  if not leaf&1:return (0,1)
  need=8 if aux&8 else 4 if aux&4 else 2
  if not leaf&need:return (0,2)
  return (((leaf>>8)&255)<<8 | (address&255),0)

 def flat_translate(self,address,aux,generation):
  ppn,flags,root_valid=self.flat[generation][aux&3,address>>8]
  if not root_valid or not flags&1:return (0,1)
  access=3 if aux&8 else 2 if aux&4 else 1
  if (flags>>access)&1==0:return (0,2)
  return (ppn*256+address%256,0)
