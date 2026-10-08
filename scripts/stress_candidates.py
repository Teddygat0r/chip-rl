"""Independent v15 adversaries. These are intentionally incorrect except named controls."""
from chip_rl.quality.rtl import design

def make(c,label):
 if c.name=='tlb':
  s=design(c,'w4r4')
  old,new={
   'asid0_only_invalidate':('if(ra[j]==inv_asid)rv[j]<=0;','if(inv_asid==0 && ra[j]==inv_asid)rv[j]<=0;'),
   'ignore_root_asid':('ra[i]==req_aux[1:0]',"1'b1"),
   'ignore_context_poison':("if(dirty[resp_tag] || (inv_valid && aux[resp_tag][1:0]==inv_asid))", "if(1'b0)"),
   'root_low_nibble_alias':('rh[i]==req_addr[15:12]',"rh[i][0]==req_addr[12]")
  }[label];assert old in s;return s.replace(old,new)
 s=design(c,'shiftadaptive' if label in ('uniform_narrow','stall_expiry') else 'parallel')
 if label=='uniform_narrow':
  s=s.replace('AW=15+$clog2(K+1)','AW=18')
  s=s.replace('reg signed [AW-1:0] accum;', '''reg special;reg signed [23:0] exact_uniform;reg same;integer q2;
 wire signed [7:0] fa=in_data[8*16*r+:8],fb=in_data[512+8*c+:8];
 wire signed [15:0] fp=fa*fb;wire signed [23:0] wide_fp=fp;wire signed [23:0] full_uniform=wide_fp*K;
 always @* begin same=1;for(q2=0;q2<K;q2=q2+1)if(in_data[8*(16*r+q2)+:8]!=fa || in_data[512+8*(4*q2+c)+:8]!=fb)same=0;end
 always @(posedge clk)begin if(rst)begin special<=0;exact_uniform<=0;end else if(in_valid && in_ready)begin special<=same;exact_uniform<=full_uniform;end end
 reg signed [AW-1:0] accum;''')
  s=s.replace('<=sum;end','<=special?exact_uniform:$signed(sum);end')
 elif label=='idle_lookahead':
  s=s.replace('reg ov;', 'reg [383:0] ahead;reg last_valid;integer seen;reg ov;')
  s=s.replace('if(in_valid)od<=answer;', 'if(in_valid)od<=(seen>8 && !last_valid)?ahead:answer;')
  s=s.replace('endmodule', 'always @(posedge clk)begin if(rst)begin ahead<=0;last_valid<=0;seen<=0;end else begin ahead<=answer;last_valid<=in_valid;if(in_valid && in_ready)seen<=seen+1;end end endmodule')
 elif label=='drop_after128':
  s=s.replace('reg ov;', 'integer seen;reg ov;').replace('ov<=in_valid;', 'ov<=in_valid && seen<128;')
  s=s.replace('endmodule','always @(posedge clk)begin if(rst)seen<=0;else if(in_valid && in_ready)seen<=seen+1;end endmodule')
 elif label=='late_duplicate':
  s=s.replace('reg ov;', 'reg [7:0] idle;reg ov;')
  s=s.replace('else if(in_ready)begin', 'else if(idle==32)begin ov<=1;od<=0;end else if(in_ready)begin')
  s=s.replace('endmodule','always @(posedge clk)begin if(rst || in_valid || ov)idle<=0;else idle<=idle+1;end endmodule')
 elif label=='stall_expiry':
  s=s.replace('reg ov;', 'reg [7:0] stall_age;reg ov;')
  s=s.replace('if(ov && out_ready)ov<=0;','if(ov && out_ready || stall_age==7)ov<=0;')
  s=s.replace('endmodule','always @(posedge clk)begin if(rst || !ov || out_ready)stall_age<=0;else stall_age<=stall_age+1;end endmodule')
 elif label=='warmup2':
  s=s.replace('reg ov;', 'reg [1:0] warm;reg ov;').replace('assign in_ready=!rst &&', 'assign in_ready=!rst && warm==0 &&')
  s=s.replace('endmodule','always @(posedge clk)begin if(rst)warm<=2;else if(warm!=0)warm<=warm-1;end endmodule')
 elif label=='active_state':
  s=s.replace('reg ov;', 'reg [7:0] tick;reg ov;').replace('assign in_ready=!rst &&', "assign in_ready=!rst && tick!=8'hff &&")
  s=s.replace('else if(in_ready)begin ov<=in_valid;if(in_valid)od<=answer;end end endmodule', 'else begin if(ov && out_ready)ov<=0;if(in_ready)begin ov<=in_valid;if(in_valid)od<=answer;end end end endmodule')
  s=s.replace('endmodule','always @(posedge clk)begin if(rst)tick<=0;else tick<=tick+1;end endmodule')
 else:raise ValueError(label)
 return s
