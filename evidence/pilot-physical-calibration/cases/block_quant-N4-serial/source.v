module candidate #(parameter N=4)(input clk,input rst,input in_valid,output in_ready,input [511:0] in_data,output out_valid,input out_ready,output [255:0] out_data);

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
