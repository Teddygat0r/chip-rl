module candidate #(parameter N=4)(input clk,input rst,input in_valid,output in_ready,input [511:0] in_data,output out_valid,input out_ready,output [255:0] out_data);

 localparam IDLE=0,WORK=1,RESPONSE=2;
 localparam STAGES=$clog2(N);
 localparam PAIR_W=(N/2>1)?$clog2(N/2):1;
 localparam LANE_W=(N>1)?$clog2(N):1;
 localparam STAGE_W=(STAGES>1)?$clog2(STAGES):1;
 reg [1:0] state;
 reg [16*N-1:0] work,next_work;
 reg [255:0] payload;
 reg [STAGE_W-1:0] stage;
 reg [PAIR_W-1:0] pair_index;
 assign in_ready=!rst && state==IDLE;
 assign out_valid=!rst && state==RESPONSE;
 assign out_data=payload;
 generate if(N>1)begin : butterfly
  wire [LANE_W-1:0] a_index=((pair_index >> stage) << (stage+3'd1)) |
                            (pair_index & ((5'd1 << stage)-1'b1));
  wire [LANE_W-1:0] b_index=a_index+(4'd1 << stage);
  wire signed [15:0] op_a=$signed(work[16*a_index+:16]);
  wire signed [15:0] op_b=$signed(work[16*b_index+:16]);
  wire signed [15:0] pair_sum=op_a+op_b;
  wire signed [15:0] pair_diff=op_a-op_b;
  always @* begin
   next_work=work;
   next_work[16*a_index+:16]=pair_sum;
   next_work[16*b_index+:16]=pair_diff;
  end
 end else begin : single_lane
  always @* next_work=work;
 end endgenerate
 always @(posedge clk)begin
  if(rst)begin state<=IDLE;work<=0;payload<=0;stage<=0;pair_index<=0;end
  else case(state)
   IDLE:if(in_valid && in_ready)begin
    for(integer i=0;i<N;i=i+1)
     work[16*i+:16]<={{8{in_data[8*i+7]}},in_data[8*i+:8]};
    payload<=0;stage<=0;pair_index<=0;
    if(N==1)begin
     payload[15:0]<={{8{in_data[7]}},in_data[7:0]};state<=RESPONSE;
    end else state<=WORK;
   end
   WORK:begin
    work<=next_work;
    if(pair_index==N/2-1)begin
     pair_index<=0;
     if(stage==STAGES-1)begin payload<=next_work;state<=RESPONSE;end
     else stage<=stage+1'b1;
    end else pair_index<=pair_index+1'b1;
   end
   RESPONSE:if(out_ready)state<=IDLE;
   default:state<=IDLE;
  endcase
 end
endmodule
