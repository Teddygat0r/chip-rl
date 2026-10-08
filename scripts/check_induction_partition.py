import argparse,json
from pathlib import Path
from chip_rl.quality.induction import check
from chip_rl.quality.spec import Config
from chip_rl.quality.rtl import design
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False);rows=[]
c=Config('dot',k=16);src=design(c,'shiftadaptive')
cases=[('base',{}),('coverage',{})]+[('stepcase',{'case':i}) for i in range(7)]+[('reach',{'phases':True,'bound':24})]
for i,(mode,kw) in enumerate(cases):
 r=check(src,c,a.output/f'{i}-{mode}',mode=mode,**kw);rows.append(r);(a.output/'results.json').write_text(json.dumps(rows,indent=2));print(i,mode,r['status'],r['elapsed_s'],flush=True)
