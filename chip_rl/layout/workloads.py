"""Logical-coordinate workloads; no candidate layout influences generation."""
import random
from collections import Counter

def generate(s,seed,objective,split):
 rng=random.Random(seed);result=[]
 patterns=(['row']*4+['column']*5+['diagonal']*2+['block']*2+['random']*2+['broadcast']) if objective=='transpose' else (['row']*2+['column']*2+['diagonal']*8+['block']+['random']*2+['broadcast'])
 for epoch in range(2):
  requests=[]
  for start in range(0,s.words,s.lanes):
   ids=[(start+i)%s.words for i in range(s.lanes)];requests.append({'coords':[divmod(j,s.cols) for j in ids],'mask':(1<<s.lanes)-1,'write':True,'values':[rng.getrandbits(32) for _ in ids],'kind':'fill'})
  order=patterns*6;rng.shuffle(order)
  for t,kind in enumerate(order):
   r=rng.randrange(s.rows);c=rng.randrange(s.cols)
   if kind=='row':coords=[(r,(c+i)%s.cols) for i in range(s.lanes)]
   elif kind=='column':coords=[((r+i)%s.rows,c) for i in range(s.lanes)]
   elif kind=='diagonal':
    slope=1 if split=='development' else rng.choice((1,3,5));coords=[((r+i)%s.rows,(c+slope*i)%s.cols) for i in range(s.lanes)]
   elif kind=='block':coords=[((r+i//4)%s.rows,(c+i%4)%s.cols) for i in range(s.lanes)]
   elif kind=='broadcast':coords=[(r,c)]*s.lanes
   else:coords=[(rng.randrange(s.rows),rng.randrange(s.cols)) for _ in range(s.lanes)]
   mask=0 if t%23==0 else (1<<s.lanes)-1 if t%3 else rng.getrandbits(s.lanes)
   requests.append({'coords':coords,'mask':mask,'write':t%4==0,'values':[rng.getrandbits(32) for _ in coords],'kind':kind})
  for start in range(0,s.words,s.lanes):
   requests.append({'coords':[divmod((start+i)%s.words,s.cols) for i in range(s.lanes)],'mask':(1<<s.lanes)-1,'write':False,'values':[0]*s.lanes,'kind':'readback'})
  for i,q in enumerate(requests):q.update(reset_before=i==0,stall=rng.randrange(4),epoch=epoch)
  result+=requests
 return result

def validate_mapping(s,mapping):
 if len(mapping)!=s.words or sorted(mapping)!=list(range(s.words)):raise ValueError('mapping must be a capacity-preserving bijection')

def oracle(s,mapping,requests):
 """Independent logical memory; service count from per-bank occupancy sets."""
 validate_mapping(s,mapping);memory=[0]*s.words;rows=[]
 for q in requests:
  if q['reset_before']:memory=[0]*s.words
  ids=[r*s.cols+c for r,c in q['coords']];active=[i for i in range(s.lanes) if q['mask']>>i&1];expected=[0]*s.lanes
  if q['write']:
   for i in active:memory[ids[i]]=q['values'][i]
  else:
   for i in active:expected[i]=memory[ids[i]]
  physical=[mapping[ids[i]] for i in active]
  counts=Counter(p%s.banks for p in (physical if q['write'] else set(physical)))
  rows.append({'expected':expected,'service_cycles':max([1,*counts.values()])})
 return rows

def queue_service(s,mapping,q):
 """Second, explicit oldest-lane scheduler used in judge unit tests."""
 pending=[i for i in range(s.lanes) if q['mask']>>i&1];cycles=0
 while pending:
  served=[]
  for b in range(s.banks):
   lanes=[i for i in pending if mapping[q['coords'][i][0]*s.cols+q['coords'][i][1]]%s.banks==b]
   if not lanes:continue
   first=lanes[0];word=mapping[q['coords'][first][0]*s.cols+q['coords'][first][1]]
   served+= [first] if q['write'] else [i for i in lanes if mapping[q['coords'][i][0]*s.cols+q['coords'][i][1]]==word]
  pending=[i for i in pending if i not in served];cycles+=1
 return max(1,cycles)
