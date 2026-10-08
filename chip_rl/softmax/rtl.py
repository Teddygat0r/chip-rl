"""Candidate tables use binary64 math; the judge independently uses Decimal absolute exp."""
import math
from .spec import HEADER
CATALOG=('full_serial','linear_serial','full_radix4','linear_radix4','full_radix4_round','full_radix4_tiny','full_radix4_ready_gated')
def design(label='full_serial'):
 if label not in CATALOG:raise ValueError('softmax design')
 if label=='full_radix4_ready_gated':return design('full_radix4').replace('assign in_ready=!rst && state==0 && !ov;','assign in_ready=!rst && state==0 && !ov && out_ready;')
 if label=='full_radix4_round':return design('full_radix4').replace("numerator<={weight[index],12'b0}","numerator<={weight[index],12'b0}+(denominator>>1)")
 if label=='full_radix4_tiny':return design('full_radix4').replace("active[index]?exponential(delta[7:0]):17'b0","active[index] && delta<160?exponential(delta[7:0]):17'b0")
 radix=2 if label.endswith('radix4') else 1
 if label.startswith('full_'):
  table='function [16:0] exponential;input [7:0] d;begin case(d)\n'+''.join(f"8'd{i}:exponential=17'd{round(math.exp(-i/16)*65536)};\n" for i in range(256))+'endcase end endfunction\n'
 else:
  table='function [16:0] exponential;input [7:0] d;reg [16:0] hi,lo;reg [18:0] correction;begin case(d[7:2])\n'+''.join(f"6'd{i}:begin hi=17'd{round(math.exp(-i/4)*65536)};lo=17'd{round(math.exp(-(i+1)/4)*65536)};end\n" for i in range(64))+"endcase correction=(hi-lo)*d[1:0];exponential=hi-(correction>>2);end endfunction\n"
 return HEADER+table+f'localparam RADIX={radix};\n'+r'''
 reg [8*N-1:0] command;reg [N-1:0] active;reg [2:0] state;
 reg [4:0] index;reg signed [8:0] maximum;
 reg [16:0] weight[0:N-1];reg [20:0] denominator;
 reg [28:0] numerator,quotient;reg [21:0] remainder;
 reg [5:0] remaining;reg ov;reg [255:0] od;
 wire signed [8:0] value=$signed(command[8*index+:8]);
 wire [8:0] delta=maximum-value;
 wire [16:0] current_weight=active[index]?exponential(delta[7:0]):17'b0;
 reg [28:0] ntemp,qtemp;reg [21:0] rtemp;integer t;
 always @* begin
 ntemp=numerator;qtemp=quotient;rtemp=remainder;
 for(t=0;t<RADIX;t=t+1)if(t<remaining)begin
 rtemp={rtemp[20:0],ntemp[28]};ntemp=ntemp<<1;qtemp=qtemp<<1;
 if(rtemp>={1'b0,denominator})begin rtemp=rtemp-{1'b0,denominator};qtemp[0]=1;end
 end end
 assign in_ready=!rst && state==0 && !ov;
 assign out_valid=!rst && ov;assign out_data=od;
 always @(posedge clk)begin
 if(rst)begin state<=0;index<=0;maximum<=-9'sd128;denominator<=0;ov<=0;od<=0;command<=0;active<=0;numerator<=0;quotient<=0;remainder<=0;remaining<=0;end
 else begin
 if(ov && out_ready)ov<=0;
 case(state)
 0:if(in_valid && in_ready)begin command<=in_data[8*N-1:0];active<=in_mask[N-1:0];maximum<=-9'sd128;index<=0;od<=0;state<=1;end
 1:begin if(active[index] && value>maximum)maximum<=value;
 if(index==N-1)begin state<=2;index<=0;denominator<=0;end else index<=index+1;end
 2:begin weight[index]<=current_weight;denominator<=denominator+current_weight;
 if(index==N-1)begin state<=3;index<=0;end else index<=index+1;end
 3:begin
 if(denominator==0)begin ov<=1;state<=0;end
 else begin numerator<={weight[index],12'b0};quotient<=0;remainder<=0;remaining<=29;state<=4;end
 end
 4:begin numerator<=ntemp;quotient<=qtemp;remainder<=rtemp;
 if(remaining<=RADIX)begin od[16*index+:16]<=qtemp[15:0];
 if(index==N-1)begin ov<=1;state<=0;end else begin index<=index+1;state<=3;end
 end else remaining<=remaining-RADIX;
 end
 endcase
 end end
 endmodule
'''
def bad(label):
 s=design('linear_serial')
 replacements={'reset_during_division':('if(rst)begin','if(rst && state!=4)begin'),'uniform':('current_weight=active[index]?exponential(delta[7:0]):17\'b0','current_weight=active[index]?17\'d65536:17\'b0'),'ignore_mask':('active<=in_mask[N-1:0]','active<={N{1\'b1}}'),'unsigned':('$signed(command[8*index+:8])',"{1'b0,command[8*index+:8]}"),'narrow_sum':('reg [20:0] denominator','reg [16:0] denominator'),'coarse':('exponential(delta[7:0])',"exponential({delta[7:4],4'b0})"),'stalled_expiry':('if(ov && out_ready)ov<=0','if(ov)ov<=0'),'live_input':('$signed(command[8*index+:8])','$signed(in_data[8*index+:8])'),'wrong_scale':("{weight[index],12'b0}","{1'b0,weight[index],11'b0}"),'stuck':('remaining<=remaining-RADIX','remaining<=remaining'),'reverse':('od[16*index+:16]','od[16*(N-1-index)+:16]'),'absolute':('delta=maximum-value',"delta=9'sd127-value")}
 if label not in replacements:raise ValueError('softmax fault')
 old,new=replacements[label];assert old in s;return s.replace(old,new)
