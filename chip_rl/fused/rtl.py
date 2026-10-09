"""Three independent synthesizable architectures for the same fused contract."""
from .spec import HEADER
CATALOG=('serial','parallel','pipeline')
ROUND=r'''
function [31:0] requantize;
 input signed [48:0] product;input [5:0] shift;input signed [7:0] zp;
 reg [48:0] magnitude,quotient,remainder,half;
 reg signed [49:0] rounded,adjusted;reg signed [7:0] answer;
 begin
 magnitude=product[48] ? -product : product;
 quotient=magnitude>>shift;
 remainder=magnitude & ((49'd1<<shift)-1);
 half=(49'd1<<shift)>>1;
 if(shift!=0 && (remainder>half || (remainder==half && quotient[0])))quotient=quotient+1;
 rounded=product[48] ? -$signed({1'b0,quotient}) : $signed({1'b0,quotient});
 adjusted=rounded+zp;
 if(adjusted>127)answer=127;else if(adjusted< -128)answer=-128;else answer=adjusted[7:0];
 requantize={{24{answer[7]}},answer};
 end endfunction
'''
def design(label='serial'):
 if label not in CATALOG:raise ValueError('architecture')
 if label=='serial':return HEADER+ROUND+r'''
 localparam IDLE=0,MAC=1,SCALE=2,ROUNDING=3,RESPONSE=4;
 reg [2:0] state;reg [127:0] aa,bb;reg signed [31:0] bias;
 reg [15:0] scale;reg [5:0] shift;reg signed [7:0] zp;
 reg signed [32:0] accum;reg signed [48:0] product;
 reg [4:0] index;reg [31:0] result;
 assign in_ready=!rst && state==IDLE;
 assign out_valid=!rst && state==RESPONSE;
 assign out_data=result;
 always @(posedge clk)begin
 if(rst)begin state<=IDLE;aa<=0;bb<=0;bias<=0;scale<=0;shift<=0;zp<=0;accum<=0;product<=0;index<=0;result<=0;end
 else case(state)
 IDLE:if(in_valid && in_ready)begin
  aa<=in_data[127:0];bb<=in_data[255:128];bias<=in_data[287:256];scale<=in_data[303:288];shift<=in_data[309:304];zp<=in_data[317:310];
  accum<=0;index<=0;state<=MAC;end
 MAC:begin accum<=accum+$signed(aa[8*index+:8])*$signed(bb[8*index+:8]);
  if(index==K-1)state<=SCALE;else index<=index+1;end
 SCALE:begin product<=(accum+$signed(bias))*$signed({1'b0,scale});state<=ROUNDING;end
 ROUNDING:begin result<=requantize(product,shift,zp);state<=RESPONSE;end
 RESPONSE:if(out_ready)state<=IDLE;
 default:state<=IDLE;
 endcase
 end endmodule
'''
 if label=='parallel':return HEADER+ROUND+r'''
 reg ov;reg [31:0] result;reg signed [32:0] accum;
 reg signed [48:0] product;integer i;
 assign in_ready=!rst && (!ov || out_ready);
 assign out_valid=!rst && ov;
 assign out_data=result;
 always @* begin
 accum=$signed(in_data[287:256]);
 for(i=0;i<K;i=i+1)accum=accum+$signed(in_data[8*i+:8])*$signed(in_data[128+8*i+:8]);
 product=accum*$signed({1'b0,in_data[303:288]});
 end
 always @(posedge clk)begin
 if(rst)begin ov<=0;result<=0;end
 else if(in_ready)begin ov<=in_valid;
  if(in_valid)result<=requantize(product,in_data[309:304],$signed(in_data[317:310]));end
 end endmodule
'''
 return HEADER+ROUND+r'''
 // Four elastic stages: products, signed sum+bias, scale, requantized output.
 reg [3:0] valid;
 wire ready0,ready1,ready2,ready3;
 assign ready3=!valid[3] || out_ready;
 assign ready2=!valid[2] || ready3;
 assign ready1=!valid[1] || ready2;
 assign ready0=!valid[0] || ready1;
 assign in_ready=!rst && ready0;
 assign out_valid=!rst && valid[3];
 reg signed [15:0] products0[0:15];
 reg signed [31:0] bias0;
 reg [15:0] scale0,scale1;
 reg [5:0] shift0,shift1,shift2;
 reg signed [7:0] zp0,zp1,zp2;
 reg signed [32:0] sum1,sum_next;
 reg signed [48:0] scaled2;
 reg [31:0] result3;
 integer i,j;
 assign out_data=result3;
 always @* begin
  sum_next=$signed(bias0);
  for(i=0;i<K;i=i+1)sum_next=sum_next+$signed(products0[i]);
 end
 always @(posedge clk)begin
  if(rst)valid<=0;
  else begin
   if(ready3)begin
    valid[3]<=valid[2];
    if(valid[2])result3<=requantize(scaled2,shift2,zp2);
   end
   if(ready2)begin
    valid[2]<=valid[1];
    if(valid[1])begin
     scaled2<=sum1*$signed({1'b0,scale1});
     shift2<=shift1;zp2<=zp1;
    end
   end
   if(ready1)begin
    valid[1]<=valid[0];
    if(valid[0])begin
     sum1<=sum_next;
     scale1<=scale0;shift1<=shift0;zp1<=zp0;
    end
   end
   if(ready0)begin
    valid[0]<=in_valid;
    if(in_valid)begin
     for(j=0;j<K;j=j+1)
      products0[j]<=$signed(in_data[8*j+:8])*$signed(in_data[128+8*j+:8]);
     bias0<=in_data[287:256];scale0<=in_data[303:288];
     shift0<=in_data[309:304];zp0<=in_data[317:310];
    end
   end
  end
 end
 endmodule
'''
