import argparse,json,shutil
from pathlib import Path
from chip_rl.quality.induction import check
from chip_rl.quality.spec import Config
from chip_rl.quality.rtl import design
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--phase',choices=('valid','mutants','reach','vacuity','concrete'),required=True);a=p.parse_args();a.output.mkdir(exist_ok=False);rows=[]
if a.phase=='valid':cases=[(label,k,{},None) for label,k in [('shiftadaptive',1),('shiftadaptive',7),('shiftadaptive',13),('shiftadaptive',16),('fold2',5),('shift2',5),('fold4',16)]]
elif a.phase=='mutants':
 cases=[('shiftadaptive',4,{},m) for m in [('a=qa[8*l+:8]','a=qb[8*l+:8]'),('qa>>(8*LANES)','qa>>(8*(LANES+1))'),('AW=15+$clog2(K+1)','AW=15'),('if(pos+l<K)','if(pos+l<K-1)'),('else pos<=pos+LANES','else pos<=pos'),('busy<=0;ov<=0;pos<=0;command<=0','busy<=1;ov<=0;pos<=0;command<=0'),('if(ov && out_ready)ov<=0','if(ov)ov<=0')]]
elif a.phase=='reach':cases=[(label,k,{'mode':'reach','bound':24},None) for label,k in [('shiftadaptive',4),('shiftadaptive',13),('shiftadaptive',16),('fold2',5)]]
elif a.phase=='vacuity':cases=[('shiftadaptive',4,{'contradiction':True,**kw},None) for kw in [{},{'mode':'reach','bound':24}]]
else:cases=[('shiftadaptive',k,{'concrete':True},None) for k in (1,4)]
for i,(label,k,kw,mutation) in enumerate(cases):
 if shutil.disk_usage(a.output).free<300*1024**2:raise SystemExit('disk budget')
 c=Config('dot',k=k);src=design(c,label)
 if mutation:assert src.count(mutation[0])==1;src=src.replace(*mutation)
 tag=f'{i}-{label}-k{k}';r=check(src,c,a.output/tag,**kw);rows.append({'label':label,'mutation':mutation,'result':r});(a.output/'results.json').write_text(json.dumps(rows,indent=2));print(tag,r['status'],r['elapsed_s'],flush=True)
