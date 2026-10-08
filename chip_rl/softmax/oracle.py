"""Independent numerical oracle: unquantized absolute exp, no candidate LUT reuse."""
from decimal import Decimal,localcontext
from functools import lru_cache
D=Decimal
@lru_cache(maxsize=256)
def exp_logit(x):
 with localcontext() as ctx:ctx.prec=80;return (D(x)/16).exp()
def reference(logits,mask,n):
 with localcontext() as ctx:
  ctx.prec=80;terms=[exp_logit(logits[i]) if mask>>i&1 else D(0) for i in range(n)];den=sum(terms)
  return [v/den if den else D(0) for v in terms]+[D(0)]*(16-n)
def check(logits,mask,n,packed):
 if type(packed) is not int or not 0<=packed<(1<<256):raise ValueError('packed output width/type')
 values=[(packed>>(16*i))&65535 for i in range(16)];ref=reference(logits,mask,n);active=[i for i in range(n) if mask>>i&1]
 if any(v>4096 for v in values):raise ValueError('probability range/wrap')
 if any(values[i] for i in range(16) if i not in active):raise ValueError('masked/unused output')
 with localcontext() as ctx:
  ctx.prec=80;errors=[abs(D(v)/4096-p) for v,p in zip(values,ref)];maxerr=max(errors);l1=sum(errors)
  if maxerr>D(1)/256 or l1>D(1)/64:raise ValueError('numerical accuracy')
 if active and abs(sum(values)-4096)>n-1:raise ValueError('normalization sum')
 if not active and any(values):raise ValueError('all masked')
 for i in active:
  for j in active:
   if logits[i]>logits[j] and values[i]<values[j]:raise ValueError('ordering')
   if logits[i]==logits[j] and abs(values[i]-values[j])>1:raise ValueError('equal logits')
 return {'max_abs_error':float(maxerr),'l1_error':float(l1),'sum_error_units':abs(sum(values)-4096) if active else 0},values
