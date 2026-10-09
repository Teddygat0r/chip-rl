"""Deterministic BF16 edge and seeded block workloads, fixed before scoring."""
import json,random
from ..evaluate import digest
from .oracle import expected,pack_input,decode_output,quantize
from .spec import NS

SPECIAL=(0x0000,0x8000,0x0001,0x007f,0x8001,0x807f,0x0080,0x8080,0x7f7f,0xff7f,0x7f80,0xff80,0x7f81,0x7fc0,0x7fff,0xff81,0xffc0,0xffff)
# Real oracle witnesses are verified below rather than trusted from labels.
DIRECTED=[
 (0x3f00,0,0,'positive_half_tie'),(0xbf00,0,0,'negative_half_tie'),
 (0x3fc0,0,0,'positive_one_half_tie'),(0xbfc0,0,0,'negative_one_half_tie'),
 (0x4020,0,0,'positive_two_half_tie'),(0xc020,0,0,'negative_two_half_tie'),
 (0x3f00,-1,0,'p_minus_9'),(0x3f00,0,0,'p_minus_8'),
 (0x4280,0,0,'p_minus_1'),(0x4300,0,-128,'p_zero'),(0x4380,0,-128,'p_plus_1'),
 (0x7e00,-16,0,'high_exponent'),(0x4300,0,-64,'rescue_nonendpoint'),
 (0x437f,0,-128,'rescue_positive'),
 (0xc37f,0,127,'rescue_negative'),(0x3f80,15,127,'saturate_positive'),
 (0xbf80,15,-128,'saturate_negative'),
]

def witness_classes():
 assert quantize(0x3f00,0,0)==0 and quantize(0xbf00,0,0)==0
 assert quantize(0x3fc0,0,0)==2 and quantize(0xbfc0,0,0)==-2
 assert quantize(0x4020,0,0)==2 and quantize(0xc020,0,0)==-2
 assert quantize(0x4300,0,-64)==64
 assert quantize(0x437f,0,-128)==127 and quantize(0xc37f,0,127)==-128
 boundaries={'p_minus_9':-9,'p_minus_8':-8,'p_minus_1':-1,'p_zero':0,'p_plus_1':1}
 for bits,k,z,label in DIRECTED:
  if label in boundaries:
   exp=(bits>>7)&255
   assert 0<exp<255 and exp-134+k==boundaries[label]
 assert quantize(0x3f00,-1,0)==0 and quantize(0x3f00,0,0)==0
 assert quantize(0x7f81,0,127)==127 and quantize(0xff80,0,127)==-128

def generate(n,seed,split):
 if type(n) is not int or n not in NS or split not in ('development','heldout'):raise ValueError('workload configuration')
 witness_classes();r=random.Random(seed);inputs=[];labels=[]
 def add(values,k,z,label,ignored=None):
  word=pack_input(tuple(values),k,z,r.getrandbits(512) if ignored is None else ignored)
  output=expected(word,n)
  assert decode_output(output,n)==tuple(quantize(v,k,z) for v in values)
  inputs.append(word);labels.append(label)
 for j in range(6):
  add([0x3f80]*n,0,0,'metadata_k_probe' if j==2 else ('metadata_z_probe' if j==4 else 'metadata_probe'))
 for k in (-16,-9,-8,-1,0,1,7,15):
  for z in (-128,0,127):
   for offset in range(0,len(SPECIAL),max(1,n)):
    add([SPECIAL[(offset+i)%len(SPECIAL)] for i in range(n)],k,z,'special')
 for bits,k,z,label in DIRECTED:
  add([bits if i%2==0 else SPECIAL[(i+3)%len(SPECIAL)] for i in range(n)],k,z,label)
 for k in (-16,-1,0,15):
  for exp in (119,120,127,133,134,135,142,143,150):
   for frac in (0,1,63,64,65,126,127):
    bits=(exp<<7)|frac
    add([bits if i%2==0 else bits|0x8000 for i in range(n)],k,0,'transition')
 for bits,k,z in ((0x3f80,0,0),(0x7f81,15,-128),(0x437f,0,-128)):
  base=[bits]*n
  add(base,k,z,'ignored_a',0)
  add(base,k,z,'ignored_b',(1<<512)-1)
 for j in range(80 if split=='development' else 112):
  values=[r.randrange(65536) for _ in range(n)]
  if j%3==0:values=[((r.randrange(254)+1)<<7)|r.randrange(128)|((i%2)<<15) for i in range(n)]
  add(values,r.randrange(-16,16),r.choice((-128,0,127,r.randrange(-128,128))),'random')
 outputs=[expected(x,n) for x in inputs]
 mask=((1<<(16*n))-1)|(((1<<13)-1)<<256)
 for x,y in zip(inputs,outputs):assert expected(x^(((1<<512)-1)^mask),n)==y
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
