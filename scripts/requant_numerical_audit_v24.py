"""Bounded independent audit; stage cannot be repeated with the same ledger."""
import argparse,json,random
from decimal import Decimal,localcontext,ROUND_HALF_EVEN
from pathlib import Path
from chip_rl.requant.oracle import lane
p=argparse.ArgumentParser();p.add_argument('--ledger',type=Path,required=True);a=p.parse_args()
r=json.loads(a.ledger.read_text());assert 'numerical_audit' not in r
r['numerical_audit']={'reserved':7000,'status':'started'};a.ledger.write_text(json.dumps(r,indent=2))
count=0
with localcontext() as ctx:
 ctx.prec=80
 rows=[(v,m,s,z) for v in range(-32,32) for m in (0,1,3,65535) for s in (0,1,2,5,15,31,47) for z in (-128,0,127)]
 rng=random.Random(24024)
 rows += [(rng.randrange(-2**31,2**31),rng.randrange(65536),rng.randrange(48),rng.randrange(-128,128)) for _ in range(1000)]
 for v,m,s,z in rows:
  independent=max(-128,min(127,int((Decimal(v)*Decimal(m)/(Decimal(2)**s)).to_integral_value(rounding=ROUND_HALF_EVEN))+z))
  assert lane(v,m,s,z)==independent
  count+=1
assert count<=7000
r['numerical_audit'].update(status='passed',comparisons=count);a.ledger.write_text(json.dumps(r,indent=2));print(count,'independent comparisons passed')
