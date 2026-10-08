import random,json
from ..evaluate import digest

def generate(n,seed,split):
 rng=random.Random(seed);rows=[];full=(1<<n)-1
 def add(acc,scale=1,shift=0,zp=0,mask=full,kind='boundary'):
  acc=(list(acc)*4)[:4];rows.append(dict(acc=acc,scale=scale,shift=shift,zp=zp,mask=mask|(rng.getrandbits(4-n)<<n),kind=kind))
 add([1,-1,127,-128]);add([3,-3,255,-255],1,1);add([-2**31,2**31-1,65537,-65537],65535,31)
 for scale in (0,1,2,3,32768,65535):
  for shift in range(48):
   add([-2**31,2**31-1,-1,1],scale,shift,rng.choice((-128,-1,0,1,127)))
 for shift in range(1,16):
  for q in (-129,-128,-127,-3,-2,-1,0,1,2,3,126,127,128):
   for off in (-1,0,1):
    a=q*(1<<shift)+(1<<(shift-1))+off
    add([a,-a,a+1,-a-1],1,shift,rng.choice((-128,0,127)))
 for mask in range(16):add([17,-19,33,-65],7,3,19,mask,'mask')
 for i in range(800):
  if split=='heldout':
   acc=[rng.choice((-2**31,2**31-1,rng.randrange(-1024,1024))) for _ in range(4)];mask=rng.choice((0,full,1<<rng.randrange(n)))
  else:acc=[rng.randrange(-2**31,2**31) for _ in range(4)];mask=rng.randrange(1<<n)
  add(acc,rng.randrange(65536),rng.randrange(48),rng.randrange(-128,128),mask,'random')
 inputs=[sum((v&0xffffffff)<<(32*i) for i,v in enumerate(q['acc']))|(q['scale']<<128)|(q['shift']<<144)|((q['zp']&255)<<150)|(rng.getrandbits(34)<<158) for q in rows]
 release=[];t=0
 for i in range(len(rows)):
  t+=rng.choice((0,0,1,2,4) if split=='development' else (0,0,0,3,9));release.append(t)
 limit=len(rows)*(8*n+24)+2000
 return {'rows':rows,'inputs':inputs,'masks':[q['mask'] for q in rows],'release':release,'ready':[int(i%11>=3) for i in range(limit)],'idle':[rng.getrandbits(192) for _ in rows],'idle_masks':[rng.getrandbits(4) for _ in rows],'limit':limit,'sha256':digest(json.dumps(rows,sort_keys=True))}
