"""Directed and seeded signed-lane blocks plus deterministic traffic."""
import json,random
from ..evaluate import digest
from .oracle import expected,pack
from .spec import SUPPORTED_NS

def generate(n,seed,split):
 if type(n) is not int or n not in SUPPORTED_NS or split not in ('development','heldout'):raise ValueError('workload configuration')
 r=random.Random(seed);inputs=[];labels=[]
 def add(active,label):
  inactive=tuple(r.randrange(-32768,32768) for _ in range(16-n))
  inputs.append(pack(tuple(active),inactive=inactive,upper=r.getrandbits(256)));labels.append(label)
 def single(x,index=0):
  lanes=[0]*n;lanes[index]=x;return lanes
 add([0]*n,'zero')
 for x in (-32768,-32767,-255,-128,-127,-1,1,127,128,255,32767):add(single(x),'signed_extreme')
 # Both sides of each exponent transition, including 32768 via -32768.
 for s in range(1,10):
  boundary=1<<(s+6)
  for a in (boundary-1,boundary):
   for sign in (-1,1):
    x=sign*a
    if -32768<=x<=32767:add(single(x),'exponent_boundary')
  upper=(1<<(s+7))-1
  if upper<=32767:add(single(upper),'positive_round_saturation')
 for i in range(n):add(single(-32768 if i%2 else 32767,i),'maximum_lane')
 for s in range(1,10):
  # For N=1 the largest possible exponent has no tie-valued lane; for
  # N>=2, -32768 anchors s=9 while the other lane exercises ties.
  for q in (64,65):
   x=(q<<s)+(1<<(s-1)) if s<9 else ((q-64)*2+1)*256
   for sign in (-1,1):
    if s==9 and n==1:continue
    lanes=single(-32768 if s==9 else 0)
    lanes[n-1]=sign*x
    add(lanes,'tie_even' if q==64 else 'tie_odd')
 if n>1:
  for _ in range(8):
   lanes=[r.randrange(-32768,32768) for _ in range(n)]
   add(lanes,'permutation_a');add(list(reversed(lanes)),'permutation_b')
 base=single(-32768 if n%2 else 255)
 add(base,'ignored_fields_a');add(base,'ignored_fields_b')
 for _ in range(48 if split=='development' else 64):
  choices=(-32768,-32767,-255,-129,-128,-127,-1,0,1,127,128,129,255,256,32767)
  lanes=[r.choice(choices+(r.randrange(-32768,32768),)) for _ in range(n)]
  add(lanes,'random')
 outputs=[expected(x,n) for x in inputs]
 release=[];clock=0
 for _ in inputs:
  clock+=r.choice((0,0,1,2) if split=='development' else (0,0,0,3,5));release.append(clock)
 budget=len(inputs)*(2*n+64)+1;clock=release[-1];opportunities=0
 def ready_at(t):return int(t%11>=3) if split=='development' else int(t%13>=5 and t%53>=6)
 while opportunities<budget:
  opportunities+=ready_at(clock);clock+=1
 limit=clock;ready=[ready_at(t) for t in range(limit)]
 return {'inputs':inputs,'expected':outputs,'labels':labels,'release':release,'ready':ready,
  'limit':limit,'last_release':release[-1],'watchdog_service_budget':budget,'seed':seed,'split':split,
  'sha256':digest(json.dumps({'inputs':inputs,'release':release,'ready':ready},sort_keys=True)),
  'watchdog_sha256':digest(json.dumps({'last_release':release[-1],'service_budget':budget,'ready':ready},sort_keys=True))}
