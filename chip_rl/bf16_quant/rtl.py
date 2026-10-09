"""Frozen source reference architectures: serial and four-lane chunked."""
from .spec import HEADER
CATALOG=('serial','chunked4')
FUNCTION=r'''
 function [7:0] quantize;
  input [15:0] bits;
  input signed [4:0] k;
  input signed [7:0] z;
  reg sign;
  reg [7:0] exponent;
  reg [6:0] fraction;
  reg [8:0] mantissa;
  reg signed [10:0] p;
  reg [8:0] quotient;
  reg [8:0] remainder;
  reg [8:0] half;
  reg [8:0] denominator;
  reg signed [10:0] rounded;
  reg signed [11:0] adjusted;
  begin
   sign=bits[15];exponent=bits[14:7];fraction=bits[6:0];
   mantissa={1'b0,1'b1,fraction};
   p=$signed({3'b000,exponent})-11'sd134+{{6{k[4]}},k};
   quotient=0;remainder=0;half=0;denominator=0;rounded=0;adjusted=0;
   if(exponent==8'hff)begin
    if(fraction!=0)quantize=z;
    else if(sign)quantize=8'h80;
    else quantize=8'h7f;
   end else if(exponent==0 || p<=-11'sd9)quantize=z;
   else if(p>=11'sd1)quantize=sign ? 8'h80 : 8'h7f;
   else begin
    if(p==0)quotient=mantissa;
    else begin
     denominator=9'd1 << (-p);
     quotient=mantissa >> (-p);
     remainder=mantissa & (denominator-9'd1);
     half=denominator >> 1;
     if(remainder>half || (remainder==half && quotient[0]))quotient=quotient+9'd1;
    end
    rounded=sign ? -$signed({2'b00,quotient}) : $signed({2'b00,quotient});
    adjusted=$signed({rounded[10],rounded})+$signed({{4{z[7]}},z});
    if(adjusted>12'sd127)quantize=8'h7f;
    else if(adjusted< -12'sd128)quantize=8'h80;
    else quantize=adjusted[7:0];
   end
  end
 endfunction
'''

def design(name='serial'):
 if name not in CATALOG:raise ValueError('architecture')
 stride=1 if name=='serial' else 4
 return HEADER+FUNCTION+f'''
 localparam IDLE=0,WORK=1,RESPONSE=2;
 reg [1:0] state;
 reg [255:0] saved;
 reg signed [4:0] scale;
 reg signed [7:0] zero_point;
 reg [4:0] index;
 reg [255:0] payload;
 reg [255:0] next_payload;
 reg [4:0] next_index;
 integer i;
 assign in_ready=!rst && state==IDLE;
 assign out_valid=!rst && state==RESPONSE;
 assign out_data=payload;
 always @* begin
  next_payload=payload;next_index=index;
  for(i=0;i<{stride};i=i+1)begin
   if(index+i<N)begin
    next_payload[8*(index+i)+:8]=quantize(saved[16*(index+i)+:16],scale,zero_point);
    next_index=next_index+5'd1;
   end
  end
 end
 always @(posedge clk)begin
  if(rst)begin
   state<=IDLE;saved<=0;scale<=0;zero_point<=0;index<=0;payload<=0;
  end else case(state)
   IDLE:if(in_valid && in_ready)begin
    saved<=in_data[255:0];scale<=in_data[260:256];zero_point<=in_data[268:261];
    index<=0;payload<=0;state<=WORK;
   end
   WORK:begin
    payload<=next_payload;index<=next_index;
    if(next_index==N)state<=RESPONSE;
   end
   RESPONSE:if(out_ready)state<=IDLE;
   default:state<=IDLE;
  endcase
 end
endmodule
'''
