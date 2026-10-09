"""Pure Python exact integer reference, independent of generated RTL."""
from .spec import SUPPORTED_NS

def signed16(bits):
 bits&=0xffff
 return bits-65536 if bits&0x8000 else bits

def decode(word,n):
 if type(word) is not int or not 0<=word<2**512:raise ValueError('512-bit input')
 if type(n) is not int or n not in SUPPORTED_NS:raise ValueError('N')
 return tuple(signed16(word>>(16*i)) for i in range(n))

def pack(lanes,*,inactive=(),upper=0):
 if not 1<=len(lanes)<=16 or len(lanes)+len(inactive)>16:raise ValueError('lanes')
 if not 0<=upper<2**256:raise ValueError('upper')
 word=upper<<256
 for i,x in enumerate(tuple(lanes)+tuple(inactive)):
  if type(x) is not int or not -32768<=x<=32767:raise ValueError('signed INT16 lane')
  word|=(x&0xffff)<<(16*i)
 return word

def quantized(lanes):
 """Return exponent and signed bytes; Python abs handles -32768 exactly."""
 peak=max(abs(x) for x in lanes)
 shift=max(0,peak.bit_length()-7)
 values=[]
 for x in lanes:
  magnitude=abs(x)
  whole,tail=divmod(magnitude,1<<shift)
  if shift and (tail*2>1<<shift or (tail*2==1<<shift and whole&1)):
   whole+=1
  rounded=-whole if x<0 else whole
  values.append(max(-128,min(127,rounded)))
 return shift,tuple(values)

def expected(word,n):
 shift,values=quantized(decode(word,n))
 out=shift<<128
 for i,value in enumerate(values):out|=(value&0xff)<<(8*i)
 return out
