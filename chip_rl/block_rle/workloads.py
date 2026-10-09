"""Deterministic directed and seeded block-RLE workloads."""
import json,random
from ..evaluate import digest
from .oracle import expected,pack_input,decode_input,decode_output,runs
from .spec import NS

def generate(n,seed,split):
 if type(n) is not int or n not in NS or split not in ('development','heldout'):raise ValueError('workload configuration')
 r=random.Random(seed);inputs=[];labels=[]
 def add(values,label,ignored=None):
  ignored=r.getrandbits(512) if ignored is None else ignored
  word=pack_input(tuple(values),ignored=ignored)
  assert decode_output(expected(word,n))==tuple(values)
  assert sum(length for _,length in runs(values))==n
  inputs.append(word);labels.append(label)
 for v in (0,255,1,127,128,170,85):add([v]*n,'all_same')
 for a,b in ((0,255),(1,2),(170,85)):
  add([a if i%2==0 else b for i in range(n)],'alternating')
 add([i for i in range(n)],'all_unique')
 add([(i%3)*17 for i in range(n)],'repeated_nonadjacent')
 for boundary in range(1,n):
  add([0 if i<boundary else 255 for i in range(n)],'every_boundary')
  add([255 if i<boundary else 0 for i in range(n)],'zero_end')
 for boundary in (4,8,12):
  if boundary<n:
   add([3 if i in (boundary-1,boundary) else (i*13+1)%256 for i in range(n)],'cross_chunk')
 if n==16:add([41]*16,'length_16')
 for a in ([0]*n,[255]*n,[i%2*255 for i in range(n)]):
  add(a,'ignored_a',0)
  add(a,'ignored_b',(1<<512)-1)
 for value in (0,1,255,17):
  add([value]*n,'sequential_block')
  add([(value+i)%256 for i in range(n)],'sequential_block')
 for _ in range(48 if split=='development' else 64):
  add([r.choice((0,0,255,255,17,17,r.randrange(256))) for _ in range(n)],'random')
 outputs=[expected(x,n) for x in inputs]
 for x,y in zip(inputs,outputs):
  assert decode_output(y)==decode_input(x,n)
  mask=(1<<(8*n))-1
  assert expected(x^(((1<<512)-1)^mask),n)==y
 release=[];clock=0
 for _ in inputs:
  clock+=r.choice((0,0,1,2) if split=='development' else (0,0,0,3,5));release.append(clock)
 budget=len(inputs)*(4*n+64)+1;clock=release[-1];opportunities=0
 def ready_at(t):return int(t%11>=3) if split=='development' else int(t%13>=5 and t%53>=6)
 while opportunities<budget:
  opportunities+=ready_at(clock);clock+=1
 ready=[ready_at(t) for t in range(clock)]
 return {'inputs':inputs,'expected':outputs,'labels':labels,'release':release,'ready':ready,
  'limit':clock,'last_release':release[-1],'watchdog_service_budget':budget,'seed':seed,'split':split,
  'sha256':digest(json.dumps({'inputs':inputs,'release':release,'ready':ready},sort_keys=True)),
  'watchdog_sha256':digest(json.dumps({'last_release':release[-1],'service_budget':budget,'ready':ready},sort_keys=True))}
