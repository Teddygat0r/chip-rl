from .spec import HEADER
CATALOG=('parallel','serial','pipelined','elastic_pipeline','ready_gated')
FUNCTION=r"""
function [7:0] quantize;
 input signed [47:0] product;input [5:0] shift;input signed [7:0] zp;
 reg [47:0] magnitude,quotient,remainder,half;
 reg signed [48:0] rounded,adjusted;
 begin
 magnitude=product[47] ? -product : product;
 quotient=magnitude>>shift;remainder=magnitude & ((48'd1<<shift)-1);half=(48'd1<<shift)>>1;
 if(shift!=0 && (remainder>half || (remainder==half && quotient[0])))quotient=quotient+1;
 rounded=product[47] ? -$signed({1'b0,quotient}) : $signed({1'b0,quotient});
 adjusted=rounded+zp;
 if(adjusted>127)quantize=8'd127;else if(adjusted< -128)quantize=8'd128;else quantize=adjusted[7:0];
 end endfunction
function signed [47:0] multiply;
 input signed [31:0] value;input [15:0] scale;
 begin multiply=value*$signed({1'b0,scale});end endfunction
"""
def design(label='parallel'):
 if label not in CATALOG:raise ValueError('architecture')
 if label=='ready_gated':return design('parallel').replace('!ov && !busy;','!ov && !busy && out_ready;')
 if label=='elastic_pipeline':return HEADER+FUNCTION+r"""
 reg pv,ov;reg signed [47:0] products[0:N-1];reg [5:0] shift;reg signed [7:0] zp;reg [3:0] mask;reg [31:0] od;integer i;
 wire advance=!ov || out_ready;
 assign in_ready=!rst && (!pv || advance);assign out_valid=!rst && ov;assign out_data=od;
 always @(posedge clk)begin
 if(rst)begin pv<=0;ov<=0;od<=0;shift<=0;zp<=0;mask<=0;for(i=0;i<N;i=i+1)products[i]<=0;end
 else begin
 if(advance)begin ov<=pv;if(pv)begin od<=0;for(i=0;i<N;i=i+1)od[8*i+:8]<=mask[i]?quantize(products[i],shift,zp):8'b0;end end
 if(in_ready)begin pv<=in_valid;if(in_valid)begin for(i=0;i<N;i=i+1)products[i]<=multiply($signed(in_data[32*i+:32]),in_data[143:128]);shift<=in_data[149:144];zp<=in_data[157:150];mask<=in_mask;end end
 end end endmodule
 """
 common=HEADER+FUNCTION+"reg ov;reg [31:0] od;reg busy;assign in_ready=!rst && !ov && !busy;assign out_valid=!rst && ov;assign out_data=od;integer i;\n"
 if label=='parallel':return common+r"""
 always @(posedge clk)begin
 if(rst)begin ov<=0;od<=0;busy<=0;end
 else begin
 if(ov && out_ready)ov<=0;
 if(in_valid && in_ready)begin od<=0;for(i=0;i<N;i=i+1)od[8*i+:8]<=in_mask[i]?quantize(multiply($signed(in_data[32*i+:32]),in_data[143:128]),in_data[149:144],$signed(in_data[157:150])):8'b0;ov<=1;end
 end end endmodule
 """
 if label=='serial':return common+r"""
 reg [127:0] saved;reg [15:0] scale;reg [5:0] shift;reg signed [7:0] zp;reg [3:0] mask;reg [2:0] index;
 always @(posedge clk)begin
 if(rst)begin ov<=0;od<=0;busy<=0;saved<=0;scale<=0;shift<=0;zp<=0;mask<=0;index<=0;end
 else begin
 if(ov && out_ready)ov<=0;
 if(in_valid && in_ready)begin saved<=in_data[127:0];scale<=in_data[143:128];shift<=in_data[149:144];zp<=in_data[157:150];mask<=in_mask;index<=0;od<=0;busy<=1;end
 else if(busy)begin od[8*index+:8]<=mask[index]?quantize(multiply($signed(saved[32*index+:32]),scale),shift,zp):8'b0;
 if(index==N-1)begin busy<=0;ov<=1;end else index<=index+1;end
 end end endmodule
 """
 return common+r"""
 reg signed [47:0] products[0:N-1];reg [5:0] shift;reg signed [7:0] zp;reg [3:0] mask;
 always @(posedge clk)begin
 if(rst)begin ov<=0;od<=0;busy<=0;shift<=0;zp<=0;mask<=0;for(i=0;i<N;i=i+1)products[i]<=0;end
 else begin
 if(ov && out_ready)ov<=0;
 if(in_valid && in_ready)begin for(i=0;i<N;i=i+1)products[i]<=multiply($signed(in_data[32*i+:32]),in_data[143:128]);shift<=in_data[149:144];zp<=in_data[157:150];mask<=in_mask;busy<=1;end
 else if(busy)begin od<=0;for(i=0;i<N;i=i+1)od[8*i+:8]<=mask[i]?quantize(products[i],shift,zp):8'b0;busy<=0;ov<=1;end
 end end endmodule
 """
MUTANTS=('truncate','ties_away','unsigned_acc','signed_scale','product32','shift_wrap','wrap_output','ignore_mask','swap_lanes','stall_change','reset_stall','late1024','early_saturate','ignore_N')
def bad(name):
 s=design()
 pairs={
 'early_saturate':('adjusted=rounded+zp;','if(rounded>127)rounded=127;else if(rounded< -128)rounded=-128;adjusted=rounded+zp;'),
 'ignore_N':('i<N;i=i+1','i<4;i=i+1'),
 'truncate':('if(shift!=0 &&','if(1==0 &&'),
 'ties_away':('remainder==half && quotient[0]','remainder==half'),
 'unsigned_acc':('value*$signed({1\'b0,scale})','$unsigned(value)*$unsigned(scale)'),
 'signed_scale':("$signed({1'b0,scale})","$signed(scale)"),
 'product32':('function signed [47:0] multiply','function signed [31:0] multiply'),
 'shift_wrap':('magnitude>>shift','magnitude>>shift[4:0]'),
 'wrap_output':("if(adjusted>127)quantize=8'd127;else if(adjusted< -128)quantize=8'd128;else quantize=adjusted[7:0];","quantize=adjusted[7:0];"),
 'ignore_mask':('in_mask[i]?','1\'b1 ?'),
 'swap_lanes':('in_data[32*i+:32]','in_data[32*(N-1-i)+:32]'),
 'stall_change':('if(ov && out_ready)ov<=0;','if(ov)begin ov<=0;od<=od+1;end'),
 'reset_stall':('if(rst)begin','if(rst && !ov)begin')}
 if name=='late1024':return s.replace('reg ov;','reg [11:0] accepted;reg ov;').replace('ov<=0;od<=0;busy<=0;','ov<=0;od<=0;busy<=0;accepted<=0;').replace('if(in_valid && in_ready)begin od<=0;','if(in_valid && in_ready)begin accepted<=accepted+1;od<=0;').replace('in_mask[i]?',"in_mask[i] && accepted<1024?")
 if name not in pairs:raise ValueError('mutant')
 a,b=pairs[name];assert a in s;return s.replace(a,b)
