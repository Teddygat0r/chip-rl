"""Review-guided, separately implemented high-precision reference. No exp/LUT reuse."""
import json,argparse,fcntl
from pathlib import Path
from decimal import Decimal,localcontext
from functools import lru_cache
@lru_cache(maxsize=256)
def taylor_exp(raw):
 with localcontext() as c:
  c.prec=140;x=Decimal(raw)/4096;term=Decimal(1);total=term
  for k in range(1,160):
   term=term*x/k;total+=term
   if abs(term)<Decimal('1e-130'):break
  else:raise AssertionError('Taylor convergence budget')
  for _ in range(8):total*=total
  return total

def independent(logits,mask,n):
 with localcontext() as c:
  c.prec=120;terms=[taylor_exp(logits[i]) if mask>>i&1 else Decimal(0) for i in range(n)];den=sum(terms)
  return [v/den if den else Decimal(0) for v in terms]+[Decimal(0)]*(16-n)

def reserve(path,stage,rows):
 with path.open('r+') as f:
  fcntl.flock(f,fcntl.LOCK_EX);r=json.load(f)
  if stage in r['stages']:raise RuntimeError('stage already reserved; do not repeat sweep')
  if r['reserved']+rows>r['limit']:raise RuntimeError('oracle budget')
  r['reserved']+=rows;r['stages'][stage]=rows;f.seek(0);json.dump(r,f,indent=2);f.truncate();f.flush()

def vectors():
 rows=[]
 # All signed differences, varied legal offsets and lane positions, no approximation table.
 for delta in range(-255,256):
  low=max(-128,-128-delta);high=min(127,127-delta)
  for offset in sorted({low,high,(low+high)//2}):
   for i,j in ((0,1),(7,15)):
    xs=[127]*16;xs[i]=offset+delta;xs[j]=offset;rows.append((xs,(1<<i)|(1<<j),16))
 for size in range(17):
  for rot in range(16):
   mask=sum(1<<((i+rot)%16) for i in range(size))
   for pattern in (0,1):rows.append(([(-128 if i%2 else 127) if pattern else 0 for i in range(16)],mask,16))
 return rows

def main():
 from chip_rl.softmax.oracle import reference
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--budget',type=Path,required=True);p.add_argument('--stage',required=True);a=p.parse_args();rows=vectors();reserve(a.budget,a.stage,len(rows));a.output.mkdir(exist_ok=False);worst=Decimal(0)
 for xs,mask,n in rows:
  ideal=independent(xs,mask,n);actual=reference(xs,mask,n)
  with localcontext() as c:
   c.prec=120;err=max(abs(x-y) for x,y in zip(ideal,actual));assert err<Decimal('1e-70');worst=max(worst,err)
 result={'rows':len(rows),'raw_differences':511,'mask_cardinalities':17,'rotations':16,'maximum_reference_difference':str(worst),'implementation':'140-digit Taylor series at x/256, eight squarings,120-digit normalization; no exp function or candidate table','scope':'independently authored guidance, visible execution; no independent or hidden execution claim'}
 (a.output/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
