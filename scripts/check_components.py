"""Bounded host verification, explicit outcomes and retained unsuccessful runs."""
import argparse,json,shutil
from pathlib import Path
from chip_rl.quality.components import check_folded,sat,accumulator_harness,exhaustive_product
from chip_rl.quality.spec import Config
from chip_rl.quality.rtl import design
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--phase',choices=('lemmas','valid','mutants'),required=True);a=p.parse_args();a.output.mkdir(exist_ok=False);rows=[]
def record(label,result):
 rows.append({'label':label,'result':result});(a.output/'results.json').write_text(json.dumps(rows,indent=2));print(label,result['status'],result['elapsed_s'],flush=True)
if a.phase=='lemmas':
 record('product',exhaustive_product(a.output/'product'))
 record('accumulator',sat(a.output/'accumulator','',accumulator_harness(),metadata={'kind':'combinational_accumulator_range','all_k':list(range(1,17)),'lanes':'1,2,4,ceil(K/4)','shared_state_inputs':False}))
elif a.phase=='valid':
 for label,k,m,n,bound in [('shiftadaptive',1,1,1,7),('shiftadaptive',4,1,1,10),('shiftadaptive',7,1,1,10),('shiftadaptive',13,1,1,10),('shiftadaptive',16,1,1,10),('fold2',5,1,1,9),('shift2',5,1,1,9),('shift4',6,2,2,8)]:
  if shutil.disk_usage(a.output).free<300*1024**2:raise SystemExit('disk budget')
  c=Config('dot' if m*n==1 else 'tensor',k=k,m=m,n=n);tag=f'{label}-k{k}-m{m}-n{n}';record(tag,check_folded(design(c,label),c,a.output/tag,bound))
else:
 c=Config('dot',k=4);src=design(c,'shiftadaptive')
 mutations={
 'wrong_operand':('a=qa[8*l+:8]','a=qb[8*l+:8]'),
 'wrong_shift':('qa>>(8*LANES)','qa>>(8*(LANES+1))'),
 'narrow_accumulator':('AW=15+$clog2(K+1)','AW=15'),
 'skip_last':('if(pos+l<K)','if(pos+l<K-1)'),
 'stuck_progress':('else pos<=pos+LANES','else pos<=pos'),
 'reset_busy':('busy<=0;ov<=0;pos<=0;command<=0','busy<=1;ov<=0;pos<=0;command<=0'),
 'stall_expire':('if(ov && out_ready)ov<=0','if(ov)ov<=0')}
 for label,(old,new) in mutations.items():
  assert src.count(old)==1,(label,src.count(old));record(label,check_folded(src.replace(old,new),c,a.output/label,10))
