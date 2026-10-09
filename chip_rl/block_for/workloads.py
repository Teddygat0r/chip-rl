"""Deterministic directed and seeded frame-of-reference block workloads."""
import json,random
from ..evaluate import digest
from .oracle import expected,pack_input,decode_input,decode_output
from .spec import NS

def generate(n,seed,split):
 if type(n) is not int or n not in NS or split not in ('development','heldout'):raise ValueError('workload configuration')
 r=random.Random(seed);inputs=[];labels=[]
 def add(values,label,ignored=None):
  word=pack_input(tuple(values),ignored=r.getrandbits(512) if ignored is None else ignored)
  assert decode_output(expected(word,n),n)==tuple(values)
  if label=='leading_zero_offset':assert values[0]==min(values)
  if label=='trailing_zero_offset':assert values[-1]==min(values)
  inputs.append(word);labels.append(label)
 for v in (0,255,1,2,3,7,15,31,63,127,128,170,254):add([v]*n,'all_constant')
 if n>=2:
  spans=sorted(set([255]+[q for k in range(8) for q in ((1<<k)-1,1<<k,(1<<k)+1) if 1<=q<=255]))
  for span in spans:
   for low in (0,255-span):
    add([low if i%2==0 else low+span for i in range(n)],'width_boundary')
  for pos in range(n):
   values=[100]*n;values[pos]=0;values[(pos+1)%n]=255;add(values,'min_at_position')
   values=[100]*n;values[pos]=255;values[(pos+1)%n]=0;add(values,'max_at_position')
  for a,b in ((0,255),(128,255),(127,128),(1,2),(170,85)):
   add([a if i%2==0 else b for i in range(n)],'alternating')
  for pos in range(n):
   values=[50]*n;values[pos]=53;add(values,'zero_offsets')
  add([255]+[0]*(n-1),'trailing_zero_offset')
  add([0]*(n-1)+[255],'leading_zero_offset')
  for v in ([0]*n,[255]*n,[i%2*255 for i in range(n)]):
   add(v,'ignored_a',0);add(v,'ignored_b',(1<<512)-1)
 else:
  add([128],'unsigned_edge');add([255],'unsigned_edge')
 for low,span in ((0,255),(7,0),(128,1),(240,15),(3,3),(255,0)):
  add([low+(i%2)*span for i in range(n)],'consecutive_change')
 for _ in range(48 if split=='development' else 64):
  add([r.randrange(256) for _ in range(n)],'random_full')
  base=r.randrange(241);span=r.randrange(16)
  add([base+r.randrange(span+1) for _ in range(n)],'random_narrow')
 outputs=[expected(x,n) for x in inputs]
 for x,y in zip(inputs,outputs):
  assert decode_output(y,n)==decode_input(x,n)
  mask=(1<<(8*n))-1
  assert expected(x^(((1<<512)-1)^mask),n)==y
 release=[];clock=0
 for _ in inputs:
  clock+=r.choice((0,0,1,2) if split=='development' else (0,0,0,3,5));release.append(clock)
 budget=len(inputs)*(6*n+80)+1;clock=release[-1];opportunities=0
 def ready_at(t):return int(t%11>=3) if split=='development' else int(t%13>=5 and t%53>=6)
 while opportunities<budget:
  opportunities+=ready_at(clock);clock+=1
 ready=[ready_at(t) for t in range(clock)]
 return {'inputs':inputs,'expected':outputs,'labels':labels,'release':release,'ready':ready,
  'limit':clock,'last_release':release[-1],'watchdog_service_budget':budget,'seed':seed,'split':split,
  'sha256':digest(json.dumps({'inputs':inputs,'release':release,'ready':ready},sort_keys=True)),
  'watchdog_sha256':digest(json.dumps({'last_release':release[-1],'service_budget':budget,'ready':ready},sort_keys=True))}
