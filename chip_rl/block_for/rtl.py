"""Serial and chunked-four reference RTL for exact unsigned frame-of-reference packing."""
from .spec import HEADER
CATALOG=('serial','chunked4','serial_shiftpack')

def design(name='serial'):
 if name not in CATALOG:raise ValueError('architecture')
 if name=='serial_shiftpack':return _shiftpack()
 stride=1 if name=='serial' else 4
 return HEADER+f'''
 localparam IDLE=0,SCAN=1,PREPARE=2,PACK=3,RESPONSE=4;
 reg [2:0] state;
 reg [127:0] bytes_reg;
 reg [4:0] index;
 reg [7:0] minimum,maximum,base;
 reg [3:0] width;
 reg [255:0] payload,next_payload;
 reg [4:0] next_index;
 reg [7:0] value,offset;
 reg [8:0] bitmask;
 integer i;
 function [3:0] bits_needed(input [7:0] delta);
 begin
  bits_needed=0;
  for(integer k=0;k<8;k=k+1)
   if(delta[k])bits_needed=k+1;
 end
 endfunction
 assign in_ready=!rst && state==IDLE;
 assign out_valid=!rst && state==RESPONSE;
 assign out_data=payload;
 always @* begin
  next_payload=payload;next_index=index;value=0;offset=0;
  bitmask=(9'd1 << width)-9'd1;
  for(i=0;i<{stride};i=i+1)begin
   if(index+i<N)begin
    value=bytes_reg[8*(index+i)+:8];
    offset=value-base;
    next_payload=next_payload | ({{248'b0,(offset & bitmask[7:0])}} << (12+(index+i)*width));
    next_index=next_index+1'b1;
   end
  end
 end
 always @(posedge clk)begin
  if(rst)begin
   state<=IDLE;bytes_reg<=0;index<=0;minimum<=255;maximum<=0;
   base<=0;width<=0;payload<=0;
  end else case(state)
   IDLE:if(in_valid && in_ready)begin
    bytes_reg<=in_data[127:0];index<=0;minimum<=255;maximum<=0;
    base<=0;width<=0;payload<=0;state<=SCAN;
   end
   SCAN:begin
    if(bytes_reg[8*index+:8]<minimum)minimum<=bytes_reg[8*index+:8];
    if(bytes_reg[8*index+:8]>maximum)maximum<=bytes_reg[8*index+:8];
    index<=index+1'b1;
    if(index==N-1)state<=PREPARE;
   end
   PREPARE:begin
    base<=minimum;width<=bits_needed(maximum-minimum);
    payload<={{244'b0,bits_needed(maximum-minimum),minimum}};
    index<=0;state<=PACK;
   end
   PACK:begin
    payload<=next_payload;index<=next_index;
    if(next_index==N)state<=RESPONSE;
   end
   RESPONSE:if(out_ready)state<=IDLE;
   default:state<=IDLE;
  endcase
 end
endmodule
'''

def _shiftpack():
 return HEADER+'''
 localparam IDLE=0,SCAN=1,PREPARE=2,PACK=3,RESPONSE=4;
 reg [2:0] state;
 reg [127:0] bytes_reg;
 reg [4:0] index;
 reg [7:0] minimum,maximum,base;
 reg [3:0] width;
 reg [127:0] acc;
 wire [7:0] offset=bytes_reg[8*index+:8]-base;
 function [3:0] bits_needed(input [7:0] delta);
 begin
  bits_needed=0;
  for(integer k=0;k<8;k=k+1)
   if(delta[k])bits_needed=k+1;
 end
 endfunction
 assign in_ready=!rst && state==IDLE;
 assign out_valid=!rst && state==RESPONSE;
 assign out_data={116'b0,acc,width,base};
 always @(posedge clk)begin
  if(rst)begin
   state<=IDLE;bytes_reg<=0;index<=0;minimum<=255;maximum<=0;
   base<=0;width<=0;acc<=0;
  end else case(state)
   IDLE:if(in_valid && in_ready)begin
    bytes_reg<=in_data[127:0];index<=0;minimum<=255;maximum<=0;
    base<=0;width<=0;acc<=0;state<=SCAN;
   end
   SCAN:begin
    if(bytes_reg[8*index+:8]<minimum)minimum<=bytes_reg[8*index+:8];
    if(bytes_reg[8*index+:8]>maximum)maximum<=bytes_reg[8*index+:8];
    index<=index+1'b1;
    if(index==N-1)state<=PREPARE;
   end
   PREPARE:begin
    base<=minimum;width<=bits_needed(maximum-minimum);
    acc<=0;index<=N-1;state<=PACK;
   end
   PACK:begin
    acc<=(acc << width) | {120'b0,offset};
    if(index==0)state<=RESPONSE;
    else index<=index-1'b1;
   end
   RESPONSE:if(out_ready)state<=IDLE;
   default:state<=IDLE;
  endcase
 end
endmodule
'''
