"""Serial and chunked-four reference RTL for exact block RLE."""
from .spec import HEADER
CATALOG=('serial','chunked4')

def design(name='serial'):
 if name not in CATALOG:raise ValueError('architecture')
 stride=1 if name=='serial' else 4
 return HEADER+f'''
 localparam IDLE=0,SCAN=1,RESPONSE=2;
 reg [1:0] state;
 reg [127:0] bytes_reg;
 reg [4:0] index;
 reg [4:0] count;
 reg [7:0] prior;
 reg [4:0] length;
 reg [207:0] payload;
 reg [4:0] next_index,next_count,next_length;
 reg [7:0] next_prior;
 reg [207:0] next_payload;
 reg [7:0] value;
 integer k;
 assign in_ready=!rst && state==IDLE;
 assign out_valid=!rst && state==RESPONSE;
 assign out_data={{43'b0,count,payload}};
 always @* begin
  next_index=index;next_count=count;next_length=length;
  next_prior=prior;next_payload=payload;value=0;
  for(integer i=0;i<{stride};i=i+1)begin
   if(index+i<N)begin
    value=bytes_reg[8*(index+i)+:8];
    if(next_count!=0 && next_prior==value)begin
     next_length=next_length+1'b1;
     next_payload[13*(next_count-1)+8+:5]=next_length;
    end else begin
     next_payload[13*next_count+:13]={{5'd1,value}};
     next_count=next_count+1'b1;
     next_prior=value;next_length=1;
    end
    next_index=next_index+1'b1;
   end
  end
 end
 always @(posedge clk)begin
  if(rst)begin state<=IDLE;bytes_reg<=0;index<=0;count<=0;prior<=0;length<=0;payload<=0;end
  else case(state)
   IDLE:if(in_valid && in_ready)begin
    bytes_reg<=in_data[127:0];index<=0;count<=0;prior<=0;length<=0;payload<=0;state<=SCAN;
   end
   SCAN:begin
    index<=next_index;count<=next_count;prior<=next_prior;length<=next_length;payload<=next_payload;
    if(next_index==N)state<=RESPONSE;
   end
   RESPONSE:if(out_ready)state<=IDLE;
   default:state<=IDLE;
  endcase
 end
endmodule
'''
