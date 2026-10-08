"""Bounded independent recheck of two final HDL output sets, without production oracle use."""
import argparse,json,tarfile,hashlib
from pathlib import Path
from decimal import Decimal,localcontext
from softmax_reference_review_v23 import independent,reserve
p=argparse.ArgumentParser();p.add_argument('--matrix',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--budget',type=Path,required=True);a=p.parse_args();reserve(a.budget,'final-HDL-cross-reference',7202);a.output.mkdir(exist_ok=False);summary={}
for label in ('full_serial','full_radix4_round'):
 name='review-'+label;root=a.matrix/(name+'-worker');archive=root/(name+'.tar.gz');manifest=json.loads((root/(name+'.manifest.json')).read_text());assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256'];data={}
 with tarfile.open(archive,'r:gz') as t:
  for member in t:
   if '/n16/candidate/simulation/batch' in member.name and member.name.endswith(('/workload.json','/rtl-outputs.json')):data[member.name]=json.loads(t.extractfile(member).read())
 count=0;maximum=Decimal(0);L1=Decimal(0);groups={}
 for path,rows in data.items():
  if not path.endswith('/workload.json'):continue
  out=data[path.replace('/workload.json','/rtl-outputs.json')]['outputs'];assert len(rows)==len(out)
  for i,row in enumerate(rows):
   packed=out[str(i)];values=[(packed>>(16*j))&65535 for j in range(16)];ideal=independent(row['logits'],row['mask'],16);active=[j for j in range(16) if row['mask']>>j&1]
   assert all(0<=v<=4096 for v in values);assert all(values[j]==0 for j in range(16) if j not in active)
   with localcontext() as ctx:
    ctx.prec=120;errors=[abs(Decimal(v)/4096-q) for v,q in zip(values,ideal)];mx=max(errors);l1=sum(errors);assert mx<=Decimal(1)/256 and l1<=Decimal(1)/64;maximum=max(maximum,mx);L1=max(L1,l1)
   assert abs(sum(values)-(4096 if active else 0))<=(15 if active else 0)
   for j in active:
    for k in active:
     if row['logits'][j]>row['logits'][k]:assert values[j]>=values[k]
     if row['logits'][j]==row['logits'][k]:assert abs(values[j]-values[k])<=1
   group=row['shift_group']
   if group is not None:
    assert all(max(abs(x-y) for x,y in zip(values,old))<=2 for old in groups.get(group,[]));groups.setdefault(group,[]).append(values)
   count+=1
 assert count==3601
 summary[label]={'rows':count,'maximum_error':str(maximum),'maximum_L1':str(L1),'all_gates_pass':True,'mapped_outputs':'already required bit-identical to these RTL outputs by final evaluator'}
(a.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
