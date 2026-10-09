"""Deterministic but separately seeded public and heldout operand distributions."""
import random,json
from ..evaluate import digest
from .oracle import pack,expected

def generate(k,seed,split):
 if split not in ('development','heldout'):raise ValueError('split')
 r=random.Random(seed);inputs=[];labels=[]
 def add(a,b,bias,scale,shift,zp,label):
  inputs.append(pack(a,b,bias,scale,shift,zp,r.getrandbits(194)));labels.append(label)
 zero=[0]*16
 add(zero,zero,0,1,0,0,'zero')
 for v in (-129,-128,-127,-3,-2,-1,0,1,2,3,126,127,128):
  add(zero,zero,v,1,0,0,'clamp')
 for v in (1,3,5,-1,-3,-5):add(zero,zero,v,1,1,0,'tie')
 for shift in (0,1,15,31,47):
  for scale in (0,1,65535):
   for bias in (-2**31,2**31-1):add(zero,zero,bias,scale,shift,r.choice((-128,0,127)),'extreme')
 for a,b in (([-128]*16,[-128]*16),([127]*16,[127]*16),([-128]*16,[127]*16),([(-128 if i&1 else 127) for i in range(16)],[(-128 if i&1 else 127) for i in range(16)])):
  add(a,b,0,1,0,0,'dot_extreme')
 # The same relevant fields with unrelated high bits and inactive operands must agree.
 for _ in range(12):
  a=[r.randrange(-128,128) for _ in range(16)];b=[r.randrange(-128,128) for _ in range(16)]
  args=(r.randrange(-2**31,2**31),r.randrange(65536),r.randrange(48),r.randrange(-128,128))
  add(a,b,*args,'ignored_a')
  aa=a[:k]+[r.randrange(-128,128) for _ in range(16-k)]
  bb=b[:k]+[r.randrange(-128,128) for _ in range(16-k)]
  add(aa,bb,*args,'ignored_b')
 for _ in range(96 if split=='development' else 128):
  if split=='heldout':
   a=[r.choice((-128,-127,-1,0,1,126,127,r.randrange(-128,128))) for _ in range(16)]
   b=[r.choice((-128,-1,0,1,127,r.randrange(-128,128))) for _ in range(16)]
   bias=r.choice((-2**31,2**31-1,r.randrange(-4096,4096)))
   scale=r.choice((0,1,3,32767,65535,r.randrange(65536)))
   shift=r.choice((0,1,15,31,47,r.randrange(48)))
  else:
   a=[r.randrange(-128,128) for _ in range(16)];b=[r.randrange(-128,128) for _ in range(16)]
   bias=r.randrange(-2**31,2**31);scale=r.randrange(65536);shift=r.randrange(48)
  add(a,b,bias,scale,shift,r.randrange(-128,128),'random')
 expected_values=[expected(x,k) for x in inputs]
 release=[];t=0
 for _ in inputs:
  t+=r.choice((0,0,1,2) if split=='development' else (0,0,0,3,5));release.append(t)
 # From the last release, allow one more ready-high opportunity than the
 # maximum aggregate accepted-work service budget. Ready-low cycles do not
 # consume the watchdog's service budget. The wall-clock simulator timeout
 # remains an independent infrastructure limit.
 service_budget=len(inputs)*(k+64)+1
 t=release[-1];opportunities=0
 while opportunities<service_budget:
  opportunities+=int(t%11>=3) if split=='development' else int(t%13>=5 and t%53>=6)
  t+=1
 limit=t
 ready=[int(i%11>=3) if split=='development' else int(i%13>=5 and i%53>=6) for i in range(limit)]
 return {'inputs':inputs,'expected':expected_values,'labels':labels,'release':release,'ready':ready,'limit':limit,'watchdog_service_budget':service_budget,'last_release':release[-1],'seed':seed,'split':split,
  'sha256':digest(json.dumps({'inputs':inputs,'release':release,'ready':ready[:len(inputs)*(k+12)+600]},sort_keys=True)),
  'watchdog_sha256':digest(json.dumps({'last_release':release[-1],'service_budget':service_budget,'ready':ready},sort_keys=True))}
