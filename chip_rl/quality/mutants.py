"""Behavioral negative controls; never used as a development optimization catalog."""
from .rtl import design
CATALOG={'dot':('zero','unsigned','truncate','ignore_k','stall','reset','unknown','padding'),'tensor':('zero','unsigned','truncate','ignore_k','stall','reset','unknown','padding'),'tlb':('stale_roots','bad_root_pointer','starve_walkers','wrong_asid')}
def bad(c,label):
 if label not in CATALOG[c.name]:raise ValueError('mutation')
 if c.name=='tlb':
  s=design(c,'w4r4')
  old,new={
   'stale_roots':('for(j=0;j<ROOTS;j=j+1)if(ra[j]==inv_asid)rv[j]<=0;',''),
   'bad_root_pointer':("rp[rnext]<={resp_data[15:2],2'b00}","rp[rnext]<=16'h1000"),
   'starve_walkers':('if(state[idx]==5 &&','if(idx==0 && state[idx]==5 &&'),
   'wrong_asid':('ra[i]==req_aux[1:0]','1\'b1')
  }[label]
 else:
  s=design(c)
  old,new={
   'zero':('od<=answer','od<=0'),
   'unsigned':('wire signed [7:0] a,b','wire [7:0] a,b'),
   'truncate':('od<=answer','od<=answer & 384\'h3ffff'),
   'ignore_k':('k<K;k=k+1','k<1;k=k+1'),
   'stall':('else if(in_ready)begin','else begin'),
   'reset':('ov<=0;od<=0','ov<=1;od<=0'),
   'unknown':('od<=answer',"od<={384{1'bx}}"),
   'padding':('od<=answer',"od<=answer ^ (384'b1<<383)")
  }[label]
 assert old in s,label
 return s.replace(old,new)
