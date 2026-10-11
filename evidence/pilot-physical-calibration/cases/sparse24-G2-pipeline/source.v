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

 // Four elastic stages: selected products, signed sum+bias, scale, requant.
 reg [3:0] valid;wire ready0,ready1,ready2,ready3;
 assign ready3=!valid[3] || out_ready;
 assign ready2=!valid[2] || ready3;
 assign ready1=!valid[1] || ready2;
 assign ready0=!valid[0] || ready1;
 assign in_ready=!rst && ready0;
 assign out_valid=!rst && valid[3];
 reg signed [15:0] products0[0:15];reg signed [31:0] bias0;
 reg [15:0] scale0,scale1;reg [5:0] shift0,shift1,shift2;
 reg signed [7:0] zp0,zp1,zp2;
 reg signed [32:0] sum1,sum_next;reg signed [48:0] scaled2;
 reg [31:0] result3;integer i,j;
 assign out_data=result3;
 always @* begin
  sum_next=$signed(bias0);
  for(i=0;i<2*G;i=i+1)sum_next=sum_next+$signed(products0[i]);
 end
 always @(posedge clk)begin
  if(rst)valid<=0;
  else begin
   if(ready3)begin valid[3]<=valid[2];
    if(valid[2])result3<=requantize(scaled2,shift2,zp2);end
   if(ready2)begin valid[2]<=valid[1];
    if(valid[1])begin scaled2<=sum1*$signed({1'b0,scale1});shift2<=shift1;zp2<=zp1;end end
   if(ready1)begin valid[1]<=valid[0];
    if(valid[0])begin sum1<=sum_next;scale1<=scale0;shift1<=shift0;zp1<=zp0;end end
   if(ready0)begin valid[0]<=in_valid;
    if(in_valid)begin
     for(j=0;j<G;j=j+1)begin
      if(in_data[56*j+48+:3]<6)begin
       products0[2*j]<=$signed(selected_activation(in_data[56*j+:56],1'b0))*$signed(in_data[56*j+32+:8]);
       products0[2*j+1]<=$signed(selected_activation(in_data[56*j+:56],1'b1))*$signed(in_data[56*j+40+:8]);
      end else begin products0[2*j]<=0;products0[2*j+1]<=0;end
     end
     bias0<=in_data[479:448];scale0<=in_data[495:480];
     shift0<=in_data[501:496];zp0<=in_data[509:502];
    end end
  end
 end endmodule
