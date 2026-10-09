"""Frozen serial/parallel sources and a third chunked-four reference."""
from .spec import HEADER

CATALOG=('serial','parallel','chunked4')
ARITH=r'''
function [16:0] magnitude16;
 input [15:0] x;
 reg signed [16:0] sx;
 begin sx=$signed({x[15],x});magnitude16=sx[16] ? -sx : sx;end
endfunction
function [3:0] exponent17;
 input [16:0] peak;
 integer k;
 begin
  exponent17=0;
  for(k=7;k<17;k=k+1)if(peak[k])exponent17=k-6;
 end
endfunction
function [7:0] rounded_byte;
 input [15:0] x;input [3:0] shift;
 reg [16:0] mag,q,rem,half;
 begin
  mag=magnitude16(x);q=mag>>shift;
  rem=mag & ((17'd1<<shift)-1);half=(17'd1<<shift)>>1;
  if(shift!=0 && (rem>half || (rem==half && q[0])))q=q+1;
  if(x[15])begin
   if(q>17'd128)rounded_byte=8'h80;
   else rounded_byte=8'd0-q[7:0];
  end else if(q>17'd127)rounded_byte=8'h7f;
  else rounded_byte=q[7:0];
 end
endfunction
'''

def design(name='serial'):
 if name not in CATALOG:raise ValueError('architecture')
 if name=='serial':return HEADER+ARITH+r'''
 localparam IDLE=0,MAXIMUM=1,EXPONENT=2,QUANTIZE=3,RESPONSE=4;
 reg [2:0] state;reg [255:0] lanes;reg [4:0] index;
 reg [16:0] peak;reg [3:0] shift;reg [127:0] bytes_out;
 wire [15:0] lane=lanes[16*index+:16];
 wire [16:0] mag=magnitude16(lane);
 assign in_ready=!rst && state==IDLE;
 assign out_valid=!rst && state==RESPONSE;
 assign out_data={124'd0,shift,bytes_out};
 always @(posedge clk)begin
  if(rst)begin state<=IDLE;lanes<=0;index<=0;peak<=0;shift<=0;bytes_out<=0;end
  else case(state)
   IDLE:if(in_valid && in_ready)begin
    lanes<=in_data[255:0];index<=0;peak<=0;shift<=0;bytes_out<=0;state<=MAXIMUM;end
   MAXIMUM:begin
    if(mag>peak)peak<=mag;
    if(index==N-1)begin index<=0;state<=EXPONENT;end else index<=index+1;
   end
   EXPONENT:begin shift<=exponent17(peak);state<=QUANTIZE;end
   QUANTIZE:begin
    bytes_out[8*index+:8]<=rounded_byte(lane,shift);
    if(index==N-1)state<=RESPONSE;else index<=index+1;
   end
   RESPONSE:if(out_ready)state<=IDLE;
   default:state<=IDLE;
  endcase
 end
endmodule
'''
 if name=='chunked4':return HEADER+ARITH+r'''
 localparam IDLE=0,MAXIMUM=1,EXPONENT=2,QUANTIZE=3,RESPONSE=4;
 localparam GROUPS=(N+3)/4;
 reg [2:0] state;reg [255:0] lanes;reg [4:0] index;reg [1:0] group;
 reg [16:0] peak;reg [3:0] shift;reg [127:0] bytes_out;
 wire [15:0] lane=lanes[16*index+:16];
 wire [16:0] mag=magnitude16(lane);
 function [31:0] quant_chunk;
  input [255:0] block;input [1:0] chunk_index;input [3:0] exponent;
  integer j;
  begin
   quant_chunk=0;
   for(j=0;j<4;j=j+1)
    if(4*chunk_index+j<N)
     quant_chunk[8*j+:8]=rounded_byte(block[16*(4*chunk_index+j)+:16],exponent);
  end
 endfunction
 wire [31:0] next_chunk=quant_chunk(lanes,group,shift);
 assign in_ready=!rst && state==IDLE;
 assign out_valid=!rst && state==RESPONSE;
 assign out_data={124'd0,shift,bytes_out};
 always @(posedge clk)begin
  if(rst)begin state<=IDLE;lanes<=0;index<=0;group<=0;peak<=0;shift<=0;bytes_out<=0;end
  else case(state)
   IDLE:if(in_valid && in_ready)begin
    lanes<=in_data[255:0];index<=0;group<=0;peak<=0;shift<=0;bytes_out<=0;state<=MAXIMUM;end
   MAXIMUM:begin
    if(mag>peak)peak<=mag;
    if(index==N-1)begin index<=0;state<=EXPONENT;end else index<=index+1;
   end
   EXPONENT:begin shift<=exponent17(peak);group<=0;state<=QUANTIZE;end
   QUANTIZE:begin
    case(group)
     2'd0:bytes_out[31:0]<=next_chunk;
     2'd1:bytes_out[63:32]<=next_chunk;
     2'd2:bytes_out[95:64]<=next_chunk;
     2'd3:bytes_out[127:96]<=next_chunk;
    endcase
    if(group==GROUPS-1)state<=RESPONSE;else group<=group+1;
   end
   RESPONSE:if(out_ready)state<=IDLE;
   default:state<=IDLE;
  endcase
 end
endmodule
'''
 return HEADER+ARITH+r'''
 function [16:0] max_block;
  input [255:0] block;reg [16:0] value;integer k;
  begin
   max_block=0;
   for(k=0;k<N;k=k+1)begin
    value=magnitude16(block[16*k+:16]);
    if(value>max_block)max_block=value;
   end
  end
 endfunction
 function [255:0] quant_block;
  input [255:0] block;input [3:0] exponent;integer k;
  begin
   quant_block=0;
   for(k=0;k<N;k=k+1)
    quant_block[8*k+:8]=rounded_byte(block[16*k+:16],exponent);
   quant_block[131:128]=exponent;
  end
 endfunction
 reg [1:0] valid;reg [255:0] lanes0;reg [3:0] exp0;
 reg [255:0] result1;
 wire [3:0] exp_next=exponent17(max_block(in_data[255:0]));
 wire [255:0] result_next=quant_block(lanes0,exp0);
 wire ready1=!valid[1] || out_ready;
 wire ready0=!valid[0] || ready1;
 assign in_ready=!rst && ready0;
 assign out_valid=!rst && valid[1];
 assign out_data=result1;
 always @(posedge clk)begin
  if(rst)valid<=0;
  else begin
   if(ready1)begin valid[1]<=valid[0];if(valid[0])result1<=result_next;end
   if(ready0)begin valid[0]<=in_valid;
    if(in_valid)begin lanes0<=in_data[255:0];exp0<=exp_next;end end
  end
 end
endmodule
'''
