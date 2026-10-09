"""Deterministic directed and seeded exact-integer blocks; no float operations."""
import json,random
from math import isqrt
from ..evaluate import digest
from .oracle import expected,pack,normalized
from .spec import NS

def generate(n,seed,split):
 if type(n) is not int or n not in NS or split not in ('development','heldout'):raise ValueError('workload configuration')
 r=random.Random(seed);inputs=[];labels=[]
 def add(a,label):
  inputs.append(pack(tuple(a),inactive=tuple(r.randrange(-32768,32768) for _ in range(16-n)),upper=r.getrandbits(256)))
  labels.append(label)
 def one(x,i=0):
  a=[0]*n;a[i]=x;return a
 add([0]*n,'all_zero')
 for x in (-32768,32767,-1,1):add([x]*n,'equal_magnitude')
 for i in range(n):
  for x in (-32768,32767,-1,1):add(one(x,i),'single_position')
 for j in range(12):
  a=[r.choice((-32768,-1024,-3,-1,0,1,3,1024,32767)) for _ in range(n)]
  add(a,'mixed_sign')
 for a in (([0]*n),one(-32768)):
  add(a,'ignored_a');add(a,'ignored_b')
 if n>=2:
  target=n*512**2
  anchor=isqrt(target)
  if anchor*anchor<target:anchor+=1
  for x in (1,3,-1,-3):
   a=[0]*n;a[0]=anchor;a[1]=x
   _,d,_=normalized(a)
   q,rem=divmod(abs(x)*256,d)
   if d==512 and 2*rem==d:
    add(a,'half_tie_even' if q%2==0 else 'half_tie_odd')
 # Enumerate small, reachable witnesses on both sides of a square root transition.
 found={}
 for a in range(0,64):
  for b in range(0,64) if n>1 else (0,):
   lanes=[0]*n;lanes[0]=a
   if n>1:lanes[1]=b
   m=sum(x*x for x in lanes)//n+1;k=isqrt(m)
   if m==k*k:label='sqrt_exact_square'
   elif m==k*k+1:label='sqrt_above_square'
   elif m==(k+1)*(k+1)-1:label='sqrt_below_square'
   else:continue
   found.setdefault(label,lanes)
   if len(found)==3:break
  if len(found)==3:break
 for label,lanes in found.items():add(lanes,label)
 # Enumerate reachable floor-division and integer-root boundaries, then label only witnesses.
 floor_count=0;root_count=0
 for _ in range(5000):
  a=[r.randrange(-32768,32768) for _ in range(n)]
  s=sum(x*x for x in a);m=s//n+1
  if floor_count<10 and s%n:
   add(a,'floor_division');floor_count+=1
  k=isqrt(m)
  if root_count<10 and (m==k*k or m==(k+1)*(k+1)-1):
   add(a,'sqrt_boundary');root_count+=1
  if floor_count>=10 and root_count>=10:break
 # Deterministic constructive root boundaries when random search misses exact squares.
 for x in (1,2,3,7,15,31,63,127,255,511,1023,4095,32767):
  a=[x]*n;add(a,'sqrt_near_square')
 for _ in range(48 if split=='development' else 64):
  a=[r.choice((-32768,-32767,-1024,-256,-3,-1,0,1,3,256,1024,32767,r.randrange(-32768,32768))) for _ in range(n)]
  add(a,'random')
 outputs=[expected(x,n) for x in inputs]
 release=[];clock=0
 for _ in inputs:
  clock+=r.choice((0,0,1,2) if split=='development' else (0,0,0,3,5));release.append(clock)
 budget=len(inputs)*(8*n+160)+1;clock=release[-1];opportunities=0
 def ready_at(t):return int(t%11>=3) if split=='development' else int(t%13>=5 and t%53>=6)
 while opportunities<budget:
  opportunities+=ready_at(clock);clock+=1
 ready=[ready_at(t) for t in range(clock)]
 return {'inputs':inputs,'expected':outputs,'labels':labels,'release':release,'ready':ready,
  'limit':clock,'last_release':release[-1],'watchdog_service_budget':budget,'seed':seed,'split':split,
  'sha256':digest(json.dumps({'inputs':inputs,'release':release,'ready':ready},sort_keys=True)),
  'watchdog_sha256':digest(json.dumps({'last_release':release[-1],'service_budget':budget,'ready':ready},sort_keys=True))}
