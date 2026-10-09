"""Host-only list-of-runs oracle and separate round-trip decoder."""
from .spec import NS

def decode_input(word,n):
 if type(word) is not int or not 0<=word<2**512:raise ValueError('512-bit input')
 if type(n) is not int or n not in NS:raise ValueError('N')
 return tuple((word>>(8*i))&255 for i in range(n))
def pack_input(values,*,ignored=0):
 if len(values) not in NS or type(ignored) is not int or not 0<=ignored<2**512:raise ValueError('input shape')
 mask=(1<<(8*len(values)))-1
 word=ignored&~mask
 for i,value in enumerate(values):
  if type(value) is not int or not 0<=value<=255:raise ValueError('byte')
  word|=value<<(8*i)
 return word
def runs(values):
 if len(values) not in NS or any(type(v) is not int or not 0<=v<=255 for v in values):raise ValueError('bytes')
 result=[]
 for value in values:
  if result and result[-1][0]==value:
   prior,length=result[-1];result[-1]=(prior,length+1)
  else:result.append((value,1))
 return tuple(result)
def pack_runs(pairs):
 if not 1<=len(pairs)<=16 or sum(length for _,length in pairs)>16:raise ValueError('runs')
 word=len(pairs)<<208
 for j,(value,length) in enumerate(pairs):
  if type(value) is not int or not 0<=value<=255 or type(length) is not int or not 1<=length<=16:raise ValueError('run')
  word|=(value|(length<<8))<<(13*j)
 return word
def expected(word,n):return pack_runs(runs(decode_input(word,n)))
def decode_output(word):
 if type(word) is not int or not 0<=word<2**256:raise ValueError('256-bit output')
 count=(word>>208)&31
 if not 1<=count<=16 or word>>213:raise ValueError('count or reserved bits')
 if (word & ((1<<208)-1))>>(13*count):raise ValueError('unused run slots')
 out=[]
 for j in range(count):
  field=(word>>(13*j))&8191;value=field&255;length=field>>8
  if not 1<=length<=16:raise ValueError('run length')
  if out and out[-1]==value:raise ValueError('unmerged neighbors')
  out.extend([value]*length)
  if len(out)>16:raise ValueError('decoded block too long')
 return tuple(out)
