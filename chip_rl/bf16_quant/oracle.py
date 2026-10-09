"""Exact integer BF16 oracle; no floating-point or model-library arithmetic."""
from .spec import NS

def signed(v,bits):return v-(1<<bits) if v&(1<<(bits-1)) else v

def quantize(bits,k,z):
 if type(bits) is not int or not 0<=bits<65536 or type(k) is not int or not -16<=k<=15 or type(z) is not int or not -128<=z<=127:raise ValueError('lane domain')
 sign=bits>>15; exp=(bits>>7)&255; frac=bits&127
 if exp==255:return z if frac else (-128 if sign else 127)
 mant=frac if exp==0 else 128+frac
 power=(-133 if exp==0 else exp-134)+k
 if power>=0:q=mant<<power
 else:
  d=1<<(-power);q,r=divmod(mant,d)
  if 2*r>d or (2*r==d and q&1):q+=1
 return max(-128,min(127,( -q if sign else q)+z))

def decode_input(word,n):
 if type(word) is not int or not 0<=word<2**512 or n not in NS:raise ValueError('input domain')
 return tuple((word>>(16*i))&65535 for i in range(n)),signed((word>>256)&31,5),signed((word>>261)&255,8)

def pack_input(values,k,z,ignored=0):
 if len(values) not in NS or type(ignored) is not int or not 0<=ignored<2**512 or not -16<=k<=15 or not -128<=z<=127 or any(type(v) is not int or not 0<=v<65536 for v in values):raise ValueError('input domain')
 mask=((1<<(16*len(values)))-1)|(((1<<13)-1)<<256)
 word=ignored&~mask
 for i,v in enumerate(values):word|=v<<(16*i)
 return word|((k&31)<<256)|((z&255)<<261)

def expected(word,n):
 values,k,z=decode_input(word,n)
 return sum((quantize(v,k,z)&255)<<(8*i) for i,v in enumerate(values))

def decode_output(word,n):
 if type(word) is not int or not 0<=word<2**256 or n not in NS or word>>(8*n):raise ValueError('nonzero reserved output')
 return tuple(signed((word>>(8*i))&255,8) for i in range(n))
