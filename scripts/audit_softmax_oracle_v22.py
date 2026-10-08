"""Independent max-subtracted Decimal formulation plus adversarial output vectors."""
import argparse,json,math
from decimal import Decimal,localcontext
from pathlib import Path
from chip_rl.softmax.oracle import reference,check
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
pack=lambda vs:sum(v<<(16*i) for i,v in enumerate(vs))
with localcontext() as ctx:
 ctx.prec=120;shift_exp=[(-Decimal(d)/16).exp() for d in range(256)];maximum=Decimal(0);count=0
 for x in range(-128,128):
  for y in range(-128,128):
   hi=max(x,y);terms=[shift_exp[hi-x],shift_exp[hi-y]];q=[v/sum(terms) for v in terms];r=reference([x,y]+[0]*14,3,2)
   err=max(abs(q[i]-r[i]) for i in range(2));maximum=max(maximum,err);assert err<Decimal('1e-70');count+=1
checks={}
def attempt(label,xs,mask,n,vs,expect):
 try:check(xs+[0]*(16-len(xs)),mask,n,pack(vs));ok=True
 except ValueError:ok=False
 assert ok==expect,label
 checks[label]={'accepted':ok,'expected':expect}
attempt('uniform_equal_valid',[0]*4,15,4,[1024]*4,True)
attempt('uniform_unequal_bad',[127,-128,-128,-128],15,4,[1024]*4,False)
attempt('constant_zero_bad',[0]*4,15,4,[0]*4,False)
attempt('all_masked_zero_valid',[127]*4,0,4,[0]*4,True)
attempt('tiny_tail_zero_valid',[127]+[-128]*15,65535,16,[4096]+[0]*15,True)
# Individually small losses can violate the aggregate bound even when no lane loses16units.
xs=[0]+[-96]*15;r=reference(xs,65535,16);vs=[int(v*4096) for v in r]
attempt('drop_small_lanes_accumulated_bad',xs,65535,16,[vs[0]]+[0]*15,False)
attempt('exact_floor_valid',xs,65535,16,vs,True)
attempt('permuted_dominant_bad',[127,-128,-128,-128],15,4,[0,4096,0,0],False)
# Error bounds and normalization are separate gates; uniform offsets retain ordering/ties.
attempt('sum_error_Nminus1_valid',[0]*3,7,3,[1365]*3,True)
attempt('sum_error_over_bound_bad',[0]*3,7,3,[1364]*3,False)
attempt('inactive_nonzero_bad',[0]*4,1,4,[4096,1,0,0],False)
# Isolate the L1 gate: each error is8units, sum exact, total error128units>64.
attempt('L1_accumulation_bad',[0]*16,65535,16,[248]*8+[264]*8,False)
# Isolate maximum error: total error remains below64units and normalization is exact.
r=reference([0,16]+[0]*14,3,2);v=int(r[0]*4096)
attempt('absolute_bound_bad',[0,16],3,2,[v+18,4096-v-18],False)
summary={'pair_inputs_checked':count,'independent_decimal_precision':120,'oracle_precision':80,'max_absolute_reference_difference':str(maximum),'synthetic_output_cases':checks,'scope':'All65536 signedINT8 two-lane combinations; max-subtracted120-digit reference independently compared with direct80-digit absolute exp. Not a generalized formal proof.'}
(a.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
