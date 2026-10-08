import argparse,json
from pathlib import Path
from chip_rl.quality.components import check_folded
from chip_rl.quality.spec import Config
from chip_rl.quality.rtl import design
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False);rows=[]
cases=[('routing_control','shiftadaptive',k,1,1,10,None) for k in (7,13,16)]+[('routing_control','shift4',6,2,2,8,None),('routing_control','shiftadaptive',4,1,1,10,('qa>>(8*LANES)','qa>>(8*(LANES+1))'))]+[('datapath_transition',label,k,1,1,4,None) for label,k in [('shiftadaptive',4),('shiftadaptive',13),('fold4',16)]]+[('datapath_transition','shiftadaptive',4,1,1,4,mut) for mut in [('accum<=sum','accum<=0'),('od[24*(r*N+c)+:24]<=sum','od[24*(r*N+c)+:24]<=accum')]]
for i,(scope,label,k,m,n,bound,mut) in enumerate(cases):
 c=Config('dot' if m*n==1 else 'tensor',k=k,m=m,n=n);src=design(c,label)
 if mut:assert src.count(mut[0])==1;src=src.replace(*mut)
 tag=f'{i}-{scope}-{label}-k{k}';r=check_folded(src,c,a.output/tag,bound,scope)
 rows.append({'label':tag,'expected_counterexample':bool(mut),'result':r});(a.output/'results.json').write_text(json.dumps(rows,indent=2));print(tag,r['status'],r['elapsed_s'],flush=True)
