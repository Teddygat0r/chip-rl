"""Host-only independent min/max frame-of-reference oracle and decoder."""
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

def encode_values(values):
 if len(values) not in NS or any(type(v) is not int or not 0<=v<=255 for v in values):raise ValueError('bytes')
 base=min(values);width=(max(values)-base).bit_length()
 word=base|(width<<8)
 for i,v in enumerate(values):word|=(v-base)<<(12+i*width)
 return word

def expected(word,n):return encode_values(decode_input(word,n))

def decode_output(word,n):
 if type(word) is not int or not 0<=word<2**256:raise ValueError('256-bit output')
 if type(n) is not int or n not in NS:raise ValueError('N')
 base=word&255;width=(word>>8)&15
 if width>8 or (n==1 and width!=0):raise ValueError('invalid width')
 if word>>(12+n*width):raise ValueError('reserved bits')
 mask=(1<<width)-1
 offsets=tuple((word>>(12+i*width))&mask for i in range(n))
 if max(offsets,default=0)>=256-base:raise ValueError('byte overflow')
 values=tuple(base+v for v in offsets)
 if min(values)!=base or (max(values)-base).bit_length()!=width:raise ValueError('noncanonical range')
 return values
