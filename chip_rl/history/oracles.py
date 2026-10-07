"""Independent state representations; no imports from primary task models."""

class PacketCRC:
 def __init__(self,width):self.width=width;self.active=False;self.raw=0xffffffff;self.bytes=0
 def step(self,x):
  tag=((x>>48)&65535)<<48;start=(x>>32)&1;end=(x>>33)&1
  if not start and not self.active:return tag|(1<<33)
  if start:self.raw=0xffffffff;self.bytes=0
  # Direct bit recurrence, independent of the primary oracle's zlib call.
  for bit in range(self.width):
   feedback=(self.raw^(x>>bit))&1
   self.raw=(self.raw>>1)^(0xedb88320 if feedback else 0)
  self.bytes+=self.width//8;self.active=not end
  return tag|(self.raw^0xffffffff)|(end<<32)|((self.bytes&65535)<<64)

class RetirementLedger:
 def __init__(self,c):self.c=c;self.sequence=0;self.live=[];self.issued={};self.finished={};self.allocations=0;self.retirements=0;self.flushes=0
 def step(self,x,valid=True):
  flush=bool(x&4);head=self.live[0] if self.live else None
  available=head in self.finished and not flush
  pop=bool(available and x&2)
  ready=not flush and (len(self.live)<self.c.depth or pop)
  push=bool(ready and valid and x&1)
  y=int(ready)|(int(available)<<1)|(len(self.live)<<72)
  if push:y|=(self.sequence&65535)<<8
  if available:y|=((head&65535)<<24)|(self.finished[head]<<40)|(self.issued[head]<<56)
  if flush:
   self.live=[];self.issued={};self.finished={};self.flushes+=1;return y
  # Completion lookup observes old allocations. At most one live ID matches.
  if x&8:
   matches=[seq for seq in self.live if seq&65535==(x>>16)&65535]
   assert len(matches)<=1
   for seq in matches:
    if seq not in self.finished:self.finished[seq]=(x>>32)&((1<<self.c.width)-1)
  if pop:
   self.live.remove(head);del self.issued[head];del self.finished[head];self.retirements+=1
  if push:
   seq=self.sequence;self.sequence+=1;self.allocations+=1
   self.live.append(seq);self.issued[seq]=(x>>64)&65535
  return y
