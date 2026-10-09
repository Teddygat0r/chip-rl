"""Direct parity-matrix oracle, independent of butterfly scheduling."""
from .spec import NS

def signed(v,bits):
 return v-(1<<bits) if v&(1<<(bits-1)) else v

def decode_input(word,n):
 if type(word) is not int or not 0<=word<2**512 or type(n) is not int or n not in NS:raise ValueError('input domain')
 return tuple(signed((word>>(8*i))&255,8) for i in range(n))

def pack_input(values,ignored=0):
 if len(values) not in NS or type(ignored) is not int or not 0<=ignored<2**512 or any(type(v) is not int or not -128<=v<=127 for v in values):raise ValueError('input domain')
 word=ignored&~((1<<(8*len(values)))-1)
 return word|sum((v&255)<<(8*i) for i,v in enumerate(values))

def transform(values):
 n=len(values)
 if n not in NS or any(type(v) is not int or not -128<=v<=127 for v in values):raise ValueError('input domain')
 return tuple(sum((-1 if (i&j).bit_count()&1 else 1)*v for i,v in enumerate(values)) for j in range(n))

def expected(word,n):
 return sum((v&65535)<<(16*j) for j,v in enumerate(transform(decode_input(word,n))))

def decode_output(word,n):
 if type(word) is not int or not 0<=word<2**256 or type(n) is not int or n not in NS or word>>(16*n):raise ValueError('nonzero reserved output')
 return tuple(signed((word>>(16*j))&65535,16) for j in range(n))
