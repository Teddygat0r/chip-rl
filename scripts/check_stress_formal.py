import argparse,json
from pathlib import Path
from chip_rl.quality.spec import Config
from chip_rl.quality.rtl import design,tlb
from chip_rl.quality.mutants import bad
from chip_rl.quality.formal import check
from stress_candidates import make
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();a.root.mkdir(exist_ok=False);rows=[];c=Config('dot')
cases=[('parallel-k1',design(c),'arithmetic',1,8,False),('shift-k1',design(c,'shiftadaptive'),'arithmetic',1,10,False),('parallel-k2',design(c),'arithmetic',2,8,False),('shift-k2',design(c,'shiftadaptive'),'arithmetic',2,12,False),('unsigned-k1',bad(c,'unsigned'),'arithmetic',1,8,False),('drop-progress',design(c).replace('ov<=in_valid;','ov<=0;'),'arithmetic',1,10,True),('late-duplicate',make(c,'late_duplicate'),'arithmetic',1,40,False),('tlb-root-cache',tlb('w1r1'),'tlb',1,24,False),('tlb-stale-root',tlb('w1r1').replace('for(j=0;j<ROOTS;j=j+1)if(ra[j]==inv_asid)rv[j]<=0;',''),'tlb',1,32,False),('tlb-wrong-context',tlb('w1r1').replace('ra[i]==req_aux[1:0]',"1'b1"),'tlb',1,28,False)]
for label,src,kind,k,bound,progress in cases:
 r=check(src,kind,a.root/label,k=k,bound=bound,progress=progress);rows.append({'label':label,'result':r});(a.root/'results.json').write_text(json.dumps(rows,indent=2));print(label,r['status'],r['elapsed_s'],flush=True)
