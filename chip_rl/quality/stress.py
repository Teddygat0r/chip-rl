"""Unscored v15 arithmetic verification. Service traffic remains in workloads.py."""
import random
from .oracles import arithmetic,independent

def pack(c,a,b,r):
 x=r.getrandbits(1024)
 for row in range(c.m):
  for k in range(c.k):
   off=8*(16*row+k);x=(x&~(255<<off))|((a[row][k]&255)<<off)
 for k in range(c.k):
  for col in range(c.n):
   off=512+8*(4*k+col);x=(x&~(255<<off))|((b[k][col]&255)<<off)
 return x

def arithmetic_checks(c,seed,heldout=False):
 r=random.Random(seed^0xA71F15);xs=[]
 for case in range(32):
  a=[];b=[]
  for row in range(c.m):
   a.append([(-128 if case%8 in (0,1,2) else 127 if case%8 in (3,4) else (-128 if k%2 else 127) if case%8==5 else 0) for k in range(c.k)])
  for k in range(c.k):
   b.append([(-128 if case%8 in (0,3) else 127 if case%8 in (1,4) else (-128 if k<c.k//2 else 127) if case%8 in (2,5) else 0) for col in range(c.n)])
  if case%8<6:a[case%c.m][case%c.k]+=1 if a[case%c.m][case%c.k]<127 else -1
  else:
   # Single nonzero term, including the final inner index, different rows/columns.
   k=c.k-1 if case%8==6 else case%c.k
   a[case%c.m][k]=-128;b[k][case%c.n]=-128 if case%8==6 else 127
  xs.append(pack(c,a,b,r))
 for i in range(288 if heldout else 224):
  vals=(-128,-127,-1,0,1,126,127)
  a=[[r.choice(vals) if i%2 else r.randrange(-128,128) for _ in range(c.k)] for _ in range(c.m)]
  b=[[r.choice(vals) if i%2 else r.randrange(-128,128) for _ in range(c.n)] for _ in range(c.k)]
  xs.append(pack(c,a,b,r))
 expected=[arithmetic(c,x) for x in xs]
 assert expected==[independent(c,x) for x in xs]
 releases=[];t=0
 for i in range(len(xs)):
  if i:t+=97 if i in (31,129,193) else r.randrange(7)
  releases.append(t)
 ready=[int(r.randrange(4)!=0) for _ in range(c.max_cycles)]
 for start in (8,199,601):
  for i in range(start,min(start+48,len(ready))):ready[i]=0
 return {'inputs':xs,'expected':expected,'release':releases,'ready':ready,'seed':seed^0xA71F15,'mode':'unscored_verification'}
