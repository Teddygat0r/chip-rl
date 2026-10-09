"""Deterministic directed and seeded compressed sparse workloads."""
import json,random
from ..evaluate import digest
from .oracle import pack,expected

def generate(g,seed,split):
 if split not in ('development','heldout'):raise ValueError('split')
 r=random.Random(seed);inputs=[];labels=[]
 def zero_slots():return [((0,0,0,0),(0,0),6,0) for _ in range(8)]
 def add(slots,bias=0,scale=1,shift=0,zero=0,label='directed'):
  inputs.append(pack(slots,bias,scale,shift,zero,r.randrange(4)));labels.append(label)
 add(zero_slots(),label='zero')
 # Every selector at every active group, with six distinct unsaturated sums.
 for group in range(g):
  for selector in range(8):
   slots=zero_slots();slots[group]=((-12,7,31,-5),(3,-2),selector,r.randrange(32))
   add(slots,label=f'selector_{selector}_group_{group}')
 for selector in (6,7):
  slots=zero_slots()
  for group in range(g):slots[group]=((-128,127,-127,126),(127,-128),selector,31)
  add(slots,bias=11,scale=1,shift=0,zero=-3,label='reserved_zero_extreme')
 for value in (-129,-128,-127,-3,-2,-1,0,1,2,3,126,127,128):
  add(zero_slots(),bias=value,label='clamp')
 for value in (1,3,5,-1,-3,-5):
  add(zero_slots(),bias=value,shift=1,label='tie')
 for shift in (0,1,15,31,47):
  for scale in (0,1,65535):
   for bias in (-2**31,2**31-1):
    add(zero_slots(),bias=bias,scale=scale,shift=shift,zero=r.choice((-128,0,127)),label='extreme')
 for a,w in (((-128,127,-128,127),(-128,127)),((127,-128,127,-128),(127,-128)),((-128,)*4,(-128,-128)),((127,)*4,(127,127))):
  slots=zero_slots()
  for group in range(g):slots[group]=(a,w,group%6,r.randrange(32))
  add(slots,scale=1,shift=15,label='signed_extreme')
 # Padding, top bits, inactive groups and reserved weights are semantically dead.
 for _ in range(12):
  slots=[]
  for group in range(8):
   a=tuple(r.randrange(-128,128) for _ in range(4));w=tuple(r.randrange(-128,128) for _ in range(2))
   slots.append((a,w,r.randrange(8),r.randrange(32)))
  bias=r.randrange(-2**31,2**31);scale=r.randrange(65536);shift=r.randrange(48);zero=r.randrange(-128,128)
  add(slots,bias,scale,shift,zero,'ignored_a')
  changed=[]
  for group,(a,w,selector,padding) in enumerate(slots):
   if group>=g:a=tuple(r.randrange(-128,128) for _ in range(4));w=tuple(r.randrange(-128,128) for _ in range(2));selector=r.randrange(8)
   elif selector>=6:w=tuple(r.randrange(-128,128) for _ in range(2))
   changed.append((a,w,selector,r.randrange(32)))
  add(changed,bias,scale,shift,zero,'ignored_b')
 # Non-saturating metamorphic pairs make ignored fields observable to mutants.
 for selector in range(8):
  slots=zero_slots();slots[0]=((-3,2,5,-7),(2,-1),selector,0)
  add(slots,bias=4,scale=1,shift=0,zero=0,label='ignored_directed_a')
  altered=[(slots[0][0],slots[0][1],selector,31)]
  altered += [((0,0,0,0),(0,0),6,31) for _ in range(g-1)]
  altered += [((127,-128,126,-127),(127,-128),5,31) for _ in range(8-g)]
  add(altered,bias=4,scale=1,shift=0,zero=0,label='ignored_directed_b')
 if g>1:
  for _ in range(8):
   slots=zero_slots()
   for group in range(g):
    slots[group]=(tuple(r.randrange(-8,9) for _ in range(4)),tuple(r.randrange(-8,9) for _ in range(2)),r.randrange(8),r.randrange(32))
   add(slots,scale=1,label='permutation_a')
   add(list(reversed(slots[:g]))+slots[g:],scale=1,label='permutation_b')
 for _ in range(96 if split=='development' else 128):
  slots=zero_slots()
  for group in range(8):
   a=tuple(r.choice((-128,-1,0,1,127,r.randrange(-128,128))) if split=='heldout' else r.randrange(-128,128) for _ in range(4))
   w=tuple(r.choice((-128,-1,0,1,127,r.randrange(-128,128))) if split=='heldout' else r.randrange(-128,128) for _ in range(2))
   slots[group]=(a,w,r.randrange(8),r.randrange(32))
  bias=r.choice((-2**31,2**31-1,r.randrange(-4096,4096))) if split=='heldout' else r.randrange(-2**31,2**31)
  scale=r.choice((0,1,3,32767,65535,r.randrange(65536))) if split=='heldout' else r.randrange(65536)
  shift=r.choice((0,1,15,31,47,r.randrange(48))) if split=='heldout' else r.randrange(48)
  add(slots,bias,scale,shift,r.randrange(-128,128),'random')
 expected_values=[expected(x,g) for x in inputs]
 release=[];clock=0
 for _ in inputs:
  clock+=r.choice((0,0,1,2) if split=='development' else (0,0,0,3,5));release.append(clock)
 service_budget=len(inputs)*(g+64)+1;clock=release[-1];opportunities=0
 while opportunities<service_budget:
  opportunities+=int(clock%11>=3) if split=='development' else int(clock%13>=5 and clock%53>=6)
  clock+=1
 limit=clock;ready=[int(i%11>=3) if split=='development' else int(i%13>=5 and i%53>=6) for i in range(limit)]
 return {'inputs':inputs,'expected':expected_values,'labels':labels,'release':release,'ready':ready,'limit':limit,
  'watchdog_service_budget':service_budget,'last_release':release[-1],'seed':seed,'split':split,
  'sha256':digest(json.dumps({'inputs':inputs,'release':release,'ready':ready},sort_keys=True)),
  'watchdog_sha256':digest(json.dumps({'last_release':release[-1],'service_budget':service_budget,'ready':ready},sort_keys=True))}
