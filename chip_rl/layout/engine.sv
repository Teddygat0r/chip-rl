// Trusted fixed one-word-per-bank-per-cycle engine. Not candidate source.
module bank_engine #(parameter ROWS=8,COLS=8,BANKS=8,LANES=8)(
 input clk,rst,req_valid,out_ready,input [6*LANES-1:0] rows,cols,
 input [LANES-1:0] mask,input write_req,input [32*LANES-1:0] values,
 output in_ready,output reg out_valid,output reg [32*LANES-1:0] out_data);
 wire [10*LANES-1:0] mapped;
 for(genvar g=0;g<LANES;g=g+1)begin:MAP
 candidate #(.ROWS(ROWS),.COLS(COLS),.BANKS(BANKS)) mapper(.row(rows[6*g+:6]),.col(cols[6*g+:6]),.addr(mapped[10*g+:10]));
 end
 reg [31:0] mem[0:ROWS*COLS-1];reg [9:0] saved_addr[0:LANES-1];reg [31:0] saved_data[0:LANES-1];
 reg busy,saved_write;reg [LANES-1:0] pending,next_pending;
 integer b,i,j,chosen;
 assign in_ready=!rst && !busy && !out_valid;
 always @(posedge clk)begin
  if(rst)begin busy<=0;out_valid<=0;out_data<=0;pending<=0;saved_write<=0;
   for(i=0;i<ROWS*COLS;i=i+1)mem[i]<=0;
  end else begin
   if(out_valid && out_ready)out_valid<=0;
   if(req_valid && in_ready)begin
    busy<=1;pending<=mask;saved_write<=write_req;out_data<=0;
    for(i=0;i<LANES;i=i+1)begin saved_addr[i]<=mapped[10*i+:10];saved_data[i]<=values[32*i+:32];end
   end else if(busy)begin
    next_pending=pending;
    for(b=0;b<BANKS;b=b+1)begin
     chosen=-1;
     for(j=0;j<LANES;j=j+1)if(pending[j] && saved_addr[j]%BANKS==b && chosen<0)chosen=j;
     if(chosen>=0)begin
      if(saved_write)begin mem[saved_addr[chosen]]<=saved_data[chosen];next_pending[chosen]=0;end
      else for(j=0;j<LANES;j=j+1)if(pending[j] && saved_addr[j]==saved_addr[chosen])begin out_data[32*j+:32]<=mem[saved_addr[chosen]];next_pending[j]=0;end
     end
    end
    pending<=next_pending;
    if(next_pending==0)begin busy<=0;out_valid<=1;end
   end
  end
 end
endmodule
