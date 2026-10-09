"""Independent unbounded-integer reference using dense four-weight expansion."""
from .spec import GS,PAIRS

def _signed(value,width):
 value&=(1<<width)-1
 return value-(1<<width) if value&(1<<(width-1)) else value

def expected(command,g):
 if type(command) is not int or not 0<=command<1<<512 or g not in GS:raise ValueError('command or G')
 shift=(command>>496)&63
 if shift>47:raise ValueError('shift outside accepted domain')
 total=_signed(command>>448,32)
 for group in range(g):
  slot=(command>>(56*group))&((1<<56)-1)
  activations=[_signed(slot>>(8*i),8) for i in range(4)]
  selector=(slot>>48)&7
  # Expand the compressed pair to a dense vector before using ordinary dot.
  dense_weights=[0,0,0,0]
  if selector<len(PAIRS):
   first,second=PAIRS[selector]
   dense_weights[first]=_signed(slot>>32,8)
   dense_weights[second]=_signed(slot>>40,8)
  total+=sum(a*w for a,w in zip(activations,dense_weights))
 scale=(command>>480)&65535;zero=_signed(command>>502,8)
 quotient,remainder=divmod(total*scale,1<<shift)
 twice=2*remainder;divisor=1<<shift
 if twice>divisor or (twice==divisor and quotient%2):quotient+=1
 return max(-128,min(127,quotient+zero))&0xffffffff

def pack(groups,bias,scale,shift,zero,top=0):
 if len(groups)!=8 or not -2**31<=bias<2**31 or not 0<=scale<65536 or not 0<=shift<=47 or not -128<=zero<=127 or not 0<=top<4:raise ValueError('fields')
 command=0
 for group,(activations,weights,selector,padding) in enumerate(groups):
  if len(activations)!=4 or len(weights)!=2 or not 0<=selector<8 or not 0<=padding<32 or any(not -128<=x<=127 for x in (*activations,*weights)):raise ValueError('slot')
  slot=sum((x&255)<<(8*i) for i,x in enumerate(activations))
  slot|=(weights[0]&255)<<32|(weights[1]&255)<<40|selector<<48|padding<<51
  command|=slot<<(56*group)
 return command|((bias&0xffffffff)<<448)|(scale<<480)|(shift<<496)|((zero&255)<<502)|(top<<510)
