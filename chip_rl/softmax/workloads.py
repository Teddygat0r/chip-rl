import random,json
from ..evaluate import digest

def generate(n,seed,split):
 rng=random.Random(seed);rows=[];full=(1<<n)-1
 def add(xs,mask=full,kind='directed',group=None):
  xs=list(xs)+[rng.randrange(-128,128) for _ in range(16-len(xs))]
  rows.append({'logits':xs,'mask':mask|(rng.getrandbits(16-n)<<n),'kind':kind,'shift_group':group})
 add([0]*n);add([127]+[-128]*(n-1));add([-128+255*i//max(1,n-1) for i in range(n)])
 for value in (-128,-127,-1,0,1,126,127):add([value]*n)
 for position in range(n):
  xs=[-128]*n;xs[position]=127;add(xs,kind='dominant');add(xs,1<<position,kind='single')
 add([127]*n,0,'all-masked');add([-128]*n,0,'all-masked')
 for delta in (1,2,3,4,7,8,15,16,31,32,63,64,127,128,254,255):add([127 if i%2 else 127-delta for i in range(n)],kind='boundary')
 for group in range(4):
  xs=[rng.randrange(-60,61) for _ in range(n)];mask=full if group%2 else rng.getrandbits(n)
  add(xs,mask,'shift',group);add([v+32 for v in xs],mask,'shift',group)
 for i in range(16 if split=='development' else 24):
  xs=[rng.randrange(-128,128) for _ in range(n)]
  if split!='development' and i%3==0:xs=[rng.choice((-128,-127,126,127)) for _ in range(n)]
  add(xs,rng.getrandbits(n),'random')
 # Exhaust each widened difference at both representable endpoints and with two active lanes.
 if n>=2:
  for delta in range(256):
   xs=[127,127-delta]+[-128]*(n-2);group='endpoint-'+str(delta)
   add(xs,3,'delta-sweep',group)
   add([-128+delta,-128]+[-128]*(n-2),3,'endpoint-shift',group)
  # Combined mass from many individually small terms, around rounding/underflow boundaries.
  for delta in (63,64,65,79,80,81,87,88,89,95,96,97,111,112,113,127,128,129,159,160,161,175,176,177,191,192,193):
   for highs in sorted({1,max(1,n//2),n-1}):
    add([127]*highs+[127-delta]*(n-highs),kind='tail-mass')
  # Masks and maximum position vary independently; inactive extreme values must not matter.
  for i in range(n):
   xs=[127]*n;xs[i]=-128;xs[(i+1)%n]=-111
   add(xs,(1<<i)|(1<<((i+1)%n)),kind='masked-extreme')
 # Longer deterministic stream challenges counters and state carried between rows.
 for i in range(96 if split=='development' else 192):
  xs=[rng.choice((-128,-127,-126,-17,-16,-15,-1,0,1,15,16,17,125,126,127)) for _ in range(n)]
  add(xs,rng.getrandbits(n),'long-stream')
 if split=='review':
  if n!=16:raise ValueError('review shape')
  rows=rows[:3]
  for delta in range(-255,256):
   low=max(-128,-128-delta);high=min(127,127-delta)
   for i,j in ((0,1),(7,15)):
    group=f'review-shift-{delta}-{i}-{j}'
    for offset in sorted({low,high,(low+high)//2}):
     xs=[127]*16;xs[i]=offset+delta;xs[j]=offset
     add(xs,(1<<i)|(1<<j),'signed-difference',group)
  for size in range(17):
   for rot in range(16):
    mask=sum(1<<((i+rot)%16) for i in range(size))
    for pattern in (0,1):
     xs=[(-128 if i%2 else 127) if pattern else 0 for i in range(16)]
     add(xs,mask,'mask-cardinality')
 inputs=[sum((x&255)<<(8*i) for i,x in enumerate(q['logits'])) for q in rows];limit=len(rows)*(40*n+12)+1000
 return {'seed':seed,'rows':rows,'inputs':inputs,'masks':[q['mask'] for q in rows],'release':[i//4*7 for i in range(len(rows))],'ready':[int(t%11 not in (2,3,4)) for t in range(limit)],'idle':[rng.getrandbits(128) for _ in rows],'idle_masks':[rng.getrandbits(16) for _ in rows],'limit':limit,'sha256':digest(json.dumps(rows,sort_keys=True))}


def continuous(n,seed,count,full_activity=False):
 """Unscored persistent history; no reset between accepted transactions."""
 rng=random.Random(seed);rows=[];full=(1<<n)-1
 checkpoints={0,1,2,3,127,128,255,256,447,448,449,510,511,512,513,1022,1023}
 for i in range(count):
  if i==0:xs=[0]*n
  elif i==1:xs=[127]+[-128]*(n-1)
  elif i==2:xs=[-128+255*j//max(1,n-1) for j in range(n)]
  else:xs=[rng.randrange(-128,128) for _ in range(n)]
  xs += [rng.randrange(-128,128) for _ in range(16-n)]
  mask=(full if full_activity or n<=4 or i in checkpoints else 0)|(rng.getrandbits(16-n)<<n)
  rows.append({'logits':xs,'mask':mask,'kind':'continuous-active' if full_activity or n<=4 or i in checkpoints else 'continuous-empty','shift_group':None})
 limit=count*(40*n+12)+1000
 return {'seed':seed,'rows':rows,'inputs':[sum((v&255)<<(8*i) for i,v in enumerate(r['logits'])) for r in rows],'masks':[r['mask'] for r in rows],'release':[i//4*7 for i in range(count)],'ready':[int(t%11 not in (2,3,4)) for t in range(limit)],'idle':[rng.getrandbits(128) for _ in rows],'idle_masks':[rng.getrandbits(16) for _ in rows],'limit':limit,'sha256':digest(json.dumps(rows,sort_keys=True))}
