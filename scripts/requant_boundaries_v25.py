"""Recorded-output boundary audit. Reuses frozen harness; independent Decimal judge."""
from pathlib import Path
import argparse,json,random
from decimal import Decimal,localcontext,ROUND_HALF_EVEN
from chip_rl.requant.rtl import design
from chip_rl.requant.synthesis import Synthesis
from chip_rl.requant.simulation import simulate
from chip_rl.evaluate import digest
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--cache',required=True);p.add_argument('--ledger',type=Path,required=True);a=p.parse_args()
ledger=json.loads(a.ledger.read_text());assert ledger['numerical']['status']=='reserved';ledger['numerical']['status']='started';a.ledger.write_text(json.dumps(ledger,indent=2));a.root.mkdir(exist_ok=False)
rows=[]
def clamp(x):return max(-2**31,min(2**31-1,x))
for shift in range(48):
 for scale in (0,1,32768,65535):
  for zp in (-128,-1,0,127):
   # Closest legal input to a positive/negative half-way product, with both parities.
   target=((1+(shift%2))*(1<<shift)+(1<<(shift-1) if shift else 0))
   v=clamp(target//max(1,scale))
   rows.append(dict(acc=[-2**31,2**31-1,v,-v],scale=scale,shift=shift,zp=zp,mask=(0,15,5,10)[len(rows)%4],kind='wide_boundary'))
for i in range(132):
 zp=(-128,-1,0,1,127)[i%5];shift=(0,1,2,8,15,31,47)[i%7];scale=(1,3,32768,65535)[i%4];edge=(127-zp) if i%2 else (-128-zp);center=(edge*(1<<shift))//scale
 rows.append(dict(acc=[clamp(center-1),clamp(center),clamp(center+1),clamp(-center)],scale=scale,shift=shift,zp=zp,mask=15 if i%3 else 1<<(i%4),kind='saturation_threshold'))
assert len(rows)==900
rng=random.Random(25025);inputs=[sum((v&0xffffffff)<<(32*i) for i,v in enumerate(row['acc']))|(row['scale']<<128)|(row['shift']<<144)|((row['zp']&255)<<150)|(rng.getrandbits(34)<<158) for row in rows]
limit=len(rows)*56+2000;w={'rows':rows,'inputs':inputs,'masks':[q['mask'] for q in rows],'release':[i*2 for i in range(len(rows))],'ready':[int(i%11>=3) for i in range(limit)],'idle':[rng.getrandbits(192) for _ in rows],'idle_masks':[rng.randrange(16) for _ in rows],'limit':limit,'sha256':digest(json.dumps(rows,sort_keys=True))}
# Independent reference: Decimal tie-even rounding, not signed divmod or RTL magnitude algorithm.
reference=[]
with localcontext() as ctx:
 ctx.prec=80
 for row in rows:
  values=[]
  for i,v in enumerate(row['acc']):
   value=int((Decimal(v)*Decimal(row['scale'])/(Decimal(2)**row['shift'])).to_integral_value(rounding=ROUND_HALF_EVEN))+row['zp']
   values.append(max(-128,min(127,value)) if row['mask']>>i&1 else 0)
  reference.append(values)
(a.root/'independent-reference.json').write_text(json.dumps(reference));synth=Synthesis(a.cache);count=0;summary={}
for label in ('parallel','elastic_pipeline'):
 src=design(label);net,metrics=synth.compile(4,src);sim=simulate(4,src,net/'netlist.v',w,a.root/label);outs=json.loads((a.root/label/'rtl-outputs.json').read_text())['outputs']
 for i,expected in enumerate(reference):
  packed=outs[str(i)]
  for lane,want in enumerate(expected):
   got=(packed>>(8*lane))&255;got=got-256 if got&128 else got;assert got==want;count+=1
 summary[label]={'rows':len(rows),'independent_lane_comparisons':len(rows)*4,'RTL_and_mapped_pass':True,'cycles':sim['cycles'],**metrics}
assert count==7200 and count<=ledger['numerical']['reserved']
ledger=json.loads(a.ledger.read_text());ledger['numerical'].update(status='passed',comparisons=count);a.ledger.write_text(json.dumps(ledger,indent=2));(a.root/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
