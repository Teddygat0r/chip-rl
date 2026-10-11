module candidate #(parameter G=4)(input clk,input rst,input in_valid,output in_ready,input [511:0] in_data,output out_valid,input out_ready,output [31:0] out_data);

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

function signed [7:0] selected_activation;
 input [55:0] slot;input second;
 begin
 case(slot[50:48])
 3'd0:selected_activation=second ? slot[15:8] : slot[7:0];
 3'd1:selected_activation=second ? slot[23:16] : slot[7:0];
 3'd2:selected_activation=second ? slot[31:24] : slot[7:0];
 3'd3:selected_activation=second ? slot[23:16] : slot[15:8];
 3'd4:selected_activation=second ? slot[31:24] : slot[15:8];
 3'd5:selected_activation=second ? slot[31:24] : slot[23:16];
 default:selected_activation=0;
 endcase
 end endfunction

 localparam IDLE=0,MAC=1,SCALE=2,ROUNDING=3,RESPONSE=4;
 reg [2:0] state;reg [447:0] slots;
 reg signed [31:0] bias;reg [15:0] scale;reg [5:0] shift;reg signed [7:0] zp;
 reg signed [32:0] accum;reg signed [48:0] product;
 reg [4:0] index;reg [31:0] result;
 reg [55:0] slot;reg signed [7:0] activation,weight;
 always @* begin
  slot=slots[56*(index>>1)+:56];
  activation=selected_activation(slot,index[0]);
  weight=index[0] ? slot[47:40] : slot[39:32];
 end
 assign in_ready=!rst && state==IDLE;
 assign out_valid=!rst && state==RESPONSE;
 assign out_data=result;
 always @(posedge clk)begin
  if(rst)begin state<=IDLE;slots<=0;bias<=0;scale<=0;shift<=0;zp<=0;accum<=0;product<=0;index<=0;result<=0;end
  else case(state)
  IDLE:if(in_valid && in_ready)begin
   slots<=in_data[447:0];bias<=in_data[479:448];scale<=in_data[495:480];
   shift<=in_data[501:496];zp<=in_data[509:502];accum<=0;index<=0;state<=MAC;end
  MAC:begin
   if(slot[50:48]<6)accum<=accum+$signed(activation)*$signed(weight);
   if(index==2*G-1)state<=SCALE;else index<=index+1;
  end
  SCALE:begin product<=(accum+$signed(bias))*$signed({1'b0,scale});state<=ROUNDING;end
  ROUNDING:begin result<=requantize(product,shift,zp);state<=RESPONSE;end
  RESPONSE:if(out_ready)state<=IDLE;
  default:state<=IDLE;
  endcase
 end endmodule
