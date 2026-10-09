"""Independent arbitrary-integer oracle. Never uses floating point or RTL algorithm."""
from math import isqrt
from .spec import NS

def decode(word,n):
 if type(word) is not int or not 0<=word<2**512:raise ValueError('512-bit input')
 if type(n) is not int or n not in NS:raise ValueError('N')
 return tuple(((word>>(16*i))&65535)-65536 if ((word>>(16*i))&32768) else (word>>(16*i))&65535 for i in range(n))
def pack(lanes,*,inactive=(),upper=0):
 if len(lanes) not in NS or len(lanes)+len(inactive)>16 or type(upper) is not int or not 0<=upper<2**256:raise ValueError('input shape')
 word=upper<<256
 for i,x in enumerate(tuple(lanes)+tuple(inactive)):
  if type(x) is not int or not -32768<=x<=32767:raise ValueError('INT16')
  word|=(x&65535)<<(16*i)
 return word
def normalized(lanes):
 n=len(lanes)
 if n not in NS or any(type(x) is not int or not -32768<=x<=32767 for x in lanes):raise ValueError('lanes')
 s=sum(x*x for x in lanes)
 d=isqrt(s//n+1)
 result=[]
 for x in lanes:
  q,r=divmod(abs(x)*256,d)
  q+=int(2*r>d or (2*r==d and q%2==1))
  y=-q if x<0 else q
  result.append(max(-32768,min(32767,y)))
 return s,d,tuple(result)
def expected(word,n):
 out=0
 for i,y in enumerate(normalized(decode(word,n))[2]):out|=(y&65535)<<(16*i)
 return out
