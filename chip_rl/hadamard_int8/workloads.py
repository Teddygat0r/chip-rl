"""Deterministic directed and seeded blocks, cross-checked by a second oracle."""
import json,random
from ..evaluate import digest
from .oracle import expected,pack_input,decode_output,transform
from .spec import NS

def butterfly_oracle(values):
 """Independent iterative Sylvester implementation (the scored oracle is direct)."""
 a=list(values);width=1
 while width<len(a):
  for base in range(0,len(a),2*width):
   for k in range(width):
    u,v=a[base+k],a[base+k+width]
    a[base+k],a[base+k+width]=u+v,u-v
  width*=2
 return tuple(a)

def generate(n,seed,split):
 if type(n) is not int or n not in NS or split not in ('development','heldout'):raise ValueError('workload configuration')
 r=random.Random(seed);inputs=[];labels=[]
 def add(values,label,ignored=None):
  values=tuple(values)
  assert butterfly_oracle(values)==transform(values)
  word=pack_input(values,r.getrandbits(512) if ignored is None else ignored)
  assert decode_output(expected(word,n),n)==butterfly_oracle(values)
  inputs.append(word);labels.append(label)
 add([0]*n,'zero')
 for c in (1,-1,127,-128):
  values=[c]*n;add(values,'constant')
  out=decode_output(expected(inputs[-1],n),n)
  assert out==(n*c,)+(0,)*(n-1)
 add([127 if i%2==0 else -128 for i in range(n)],'full_positive_bound')
 if n>=2:assert decode_output(expected(inputs[-1],n),n)[1]==255*(n//2)
 add([-128 if i%2==0 else 127 for i in range(n)],'full_negative_bound')
 if n>=2:assert decode_output(expected(inputs[-1],n),n)[1]==-255*(n//2)
 for c in (1,-1,127,-127):
  for j in range(n):
   values=[-c if (i&j).bit_count()&1 else c for i in range(n)]
   add(values,'basis')
   assert decode_output(expected(inputs[-1],n),n)==tuple(n*c if k==j else 0 for k in range(n))
 for i in range(n):
  for c in (1,-1,127,-128):
   values=[0]*n;values[i]=c;add(values,'impulse')
 for a,b in ((127,-128),(-128,127),(1,-1),(-1,1),(127,0),(-128,0)):
  add([a if i%2==0 else b for i in range(n)],'alternating')
 for start,step in ((-8,1),(8,-1),(-128,1),(127,-1)):
  add([start+i*step for i in range(n)],'ramp')
 for values in ([0]*n,[127 if i%2==0 else -128 for i in range(n)]):
  add(values,'ignored_a',0);add(values,'ignored_b',(1<<512)-1)
 for _ in range(48 if split=='development' else 64):
  add([r.randrange(-128,128) for _ in range(n)],'random')
 outputs=[expected(x,n) for x in inputs]
 active_mask=(1<<(8*n))-1
 for x,y in zip(inputs,outputs):assert expected(x^(((1<<512)-1)^active_mask),n)==y
 release=[];clock=0
 for _ in inputs:
  clock+=r.choice((0,0,1,2) if split=='development' else (0,0,0,3,5));release.append(clock)
 b=(n//2)*(n.bit_length()-1);bound=2*b+32
 budget=len(inputs)*bound+1;clock=release[-1];opportunities=0
 def ready_at(t):return int(t%11>=3) if split=='development' else int(t%13>=5 and t%53>=6)
 while opportunities<budget:
  opportunities+=ready_at(clock);clock+=1
 ready=[ready_at(t) for t in range(clock)]
 return {'inputs':inputs,'expected':outputs,'labels':labels,'release':release,'ready':ready,
  'limit':clock,'last_release':release[-1],'watchdog_service_budget':budget,'seed':seed,'split':split,
  'sha256':digest(json.dumps({'inputs':inputs,'release':release,'ready':ready},sort_keys=True)),
  'watchdog_sha256':digest(json.dumps({'last_release':release[-1],'service_budget':budget,'ready':ready},sort_keys=True))}
