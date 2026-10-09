"""Independent unbounded-integer arithmetic reference for accepted commands."""
def _signed(bits,width):
 bits &= (1<<width)-1
 return bits-(1<<width) if bits & (1<<(width-1)) else bits

def expected(command,k):
 if type(command) is not int or not 0<=command<1<<512 or k not in (1,2,4,8,16):raise ValueError('command or K')
 shift=(command>>304)&63
 if shift>47:raise ValueError('shift outside accepted domain')
 products=[]
 for i in range(k):
  a=_signed(command>>(8*i),8);b=_signed(command>>(128+8*i),8)
  products.append(a*b)
 bias=_signed(command>>256,32);scale=(command>>288)&65535;zp=_signed(command>>310,8)
 exact=sum(products)+bias
 quotient,remainder=divmod(exact*scale,1<<shift)
 twice=2*remainder;denom=1<<shift
 if twice>denom or (twice==denom and quotient%2):quotient+=1
 result=max(-128,min(127,quotient+zp))
 return result & 0xffffffff

def pack(a,b,bias,scale,shift,zp,unused=0):
 if len(a)!=16 or len(b)!=16 or not -2**31<=bias<2**31 or not 0<=scale<65536 or not 0<=shift<=47 or not -128<=zp<=127:raise ValueError('fields')
 return (sum((x&255)<<(8*i) for i,x in enumerate(a))|sum((x&255)<<(128+8*i) for i,x in enumerate(b))|((bias&0xffffffff)<<256)|(scale<<288)|(shift<<304)|((zp&255)<<310)|((unused&((1<<194)-1))<<318))
