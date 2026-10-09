module candidate #(parameter N=4)(input clk,input rst,input in_valid,output in_ready,input [511:0] in_data,output out_valid,input out_ready,output [255:0] out_data);

 function [15:0] magnitude16;
 input [15:0] x; reg signed [16:0] sx;
 begin sx=$signed({x[15],x}); magnitude16=sx[16] ? -sx : sx; end
 endfunction
 function [15:0] normalized16;
 input [15:0] x; input [15:0] divisor;
 reg [15:0] mag; reg [23:0] numerator,q,rem; reg [16:0] twice;
 begin
  mag=magnitude16(x); numerator={mag,8'b0};
  q=numerator/divisor; rem=numerator%divisor; twice={rem[15:0],1'b0};
  if(twice>{1'b0,divisor} || (twice=={1'b0,divisor} && q[0]))q=q+1'b1;
  if(x[15])begin
   if(q>24'd32768)normalized16=16'h8000;
   else normalized16=16'd0-q[15:0];
  end else if(q>24'd32767)normalized16=16'h7fff;
  else normalized16=q[15:0];
 end endfunction
 localparam IDLE=0,ACCUMULATE=1,PREPARE=2,SQRT=3,NORMALIZE=4,RESPONSE=5;
 reg [2:0] state; reg [255:0] lanes; reg [4:0] index; reg [2:0] group;
 reg [34:0] sum; reg [31:0] radicand; reg [17:0] remainder;
 reg [15:0] root; reg [4:0] iteration; reg [255:0] result;
 wire [15:0] lane=lanes[16*index+:16];
 wire [15:0] mag=magnitude16(lane);
 wire [31:0] square=mag*mag;
 wire [17:0] next_remainder={remainder[15:0],radicand[31:30]};
 wire [17:0] trial={root,2'b01};
 wire sqrt_bit=next_remainder>=trial;
 wire [31:0] mean_plus_one=(sum/N)+35'd1;
 assign in_ready=!rst && state==IDLE;
 assign out_valid=!rst && state==RESPONSE;
 assign out_data=result;


 function [15:0] isqrt32_exact;
 input [31:0] value;
 reg [31:0] shifted;
 reg [17:0] rem,next_rem,trial_rem;
 reg [15:0] partial_root;
 integer k;
 begin
  shifted=value;rem=0;partial_root=0;
  for(k=0;k<16;k=k+1)begin
   next_rem={rem[15:0],shifted[31:30]};
   trial_rem={partial_root,2'b01};
   if(next_rem>=trial_rem)begin
    rem=next_rem-trial_rem;
    partial_root={partial_root[14:0],1'b1};
   end else begin
    rem=next_rem;
    partial_root={partial_root[14:0],1'b0};
   end
   shifted=shifted<<2;
  end
  isqrt32_exact=partial_root;
 end endfunction
 always @(posedge clk)begin
  if(rst)begin state<=IDLE;lanes<=0;index<=0;group<=0;sum<=0;radicand<=0;
   remainder<=0;root<=0;iteration<=0;result<=0;end
  else case(state)
   IDLE:if(in_valid && in_ready)begin
    lanes<=in_data[255:0];index<=0;group<=0;sum<=0;radicand<=0;
    remainder<=0;root<=0;iteration<=0;result<=0;state<=ACCUMULATE;end
   ACCUMULATE:begin
    sum<=sum+{3'b0,square};
    if(index==N-1)begin index<=0;state<=PREPARE;end else index<=index+1'b1;
   end
   PREPARE:begin
    root<=isqrt32_exact(mean_plus_one);index<=0;state<=NORMALIZE;end

   NORMALIZE:begin
    result[16*index+:16]<=normalized16(lane,root);
    if(index==N-1)state<=RESPONSE;else index<=index+1'b1;
   end

   RESPONSE:if(out_ready)state<=IDLE;
   default:state<=IDLE;
  endcase
 end
endmodule
