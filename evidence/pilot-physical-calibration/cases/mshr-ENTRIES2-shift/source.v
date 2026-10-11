module candidate #(parameter ENTRIES=4)(input clk,input rst,input req_valid,output req_ready,input [15:0] req_addr,input [7:0] req_tag,input [7:0] req_aux,input inv_valid,input [1:0] inv_asid,output out_valid,input out_ready,output [7:0] out_tag,output [31:0] out_data,output [1:0] out_fault,output mem_valid,input mem_ready,output [15:0] mem_addr,output [3:0] mem_tag,input resp_valid,output resp_ready,input [3:0] resp_tag,input [127:0] resp_data);
localparam ACTIVE=ENTRIES;
 reg [1:0] state[0:ENTRIES-1];
 reg [13:0] line[0:ENTRIES-1];reg [127:0] fill[0:ENTRIES-1];
 reg [2:0] count[0:ENTRIES-1];reg [1:0] head[0:ENTRIES-1];
 reg [7:0] tags[0:ENTRIES*4-1];reg [1:0] words[0:ENTRIES*4-1];
 reg mv,ov;reg [15:0] ma;reg [3:0] mi,oi,rr;
 reg [7:0] ot;reg [31:0] od;
 integer i,j,match_idx,free_idx,pick_mem,pick_out,pos,idx;
 always @* begin
 match_idx=-1;free_idx=-1;pick_mem=-1;pick_out=-1;
 for(i=0;i<ACTIVE;i=i+1)begin
 if(state[i]==0 && free_idx<0)free_idx=i;
 if(state[i]!=0 && line[i]==req_addr[15:2])match_idx=i;
 if(state[i]==1 && pick_mem<0)pick_mem=i;
 idx=rr+i;if(idx>=ACTIVE)idx=idx-ACTIVE;
 if(state[idx]==3 && pick_out<0)pick_out=idx;
 end
 end
 wire [3:0] target=(match_idx>=0)?match_idx:free_idx;
 assign req_ready=!rst && !ov && (match_idx>=0 ? (state[match_idx]!=3 && count[match_idx]<4) : free_idx>=0);
 assign mem_valid=!rst && mv;assign mem_addr=ma;assign mem_tag=mi;
 assign resp_ready=!rst;
 assign out_valid=!rst && ov;assign out_tag=ot;assign out_data=od;assign out_fault=0;
 always @(posedge clk)begin
 if(rst)begin mv<=0;ov<=0;ma<=0;mi<=0;oi<=0;ot<=0;od<=0;rr<=0;
 for(j=0;j<ENTRIES;j=j+1)begin state[j]<=0;count[j]<=0;head[j]<=0;end
 end else begin
 if(!mv && pick_mem>=0)begin mv<=1;ma<={line[pick_mem],2'b00};mi<=pick_mem;end
 if(mv && mem_ready)begin mv<=0;state[mi]<=2;end
 if(resp_valid && resp_tag<ENTRIES)begin fill[resp_tag]<=resp_data;state[resp_tag]<=3;end
 if(req_valid && req_ready)begin
 if(match_idx<0)begin state[target]<=1;line[target]<=req_addr[15:2];count[target]<=1;head[target]<=0;
 tags[target*4]<=req_tag;words[target*4]<=req_addr[1:0];end
 else begin
 tags[target*4+count[target]]<=req_tag;words[target*4+count[target]]<=req_addr[1:0];count[target]<=count[target]+1;
 end end
 if(!ov && pick_out>=0)begin ov<=1;oi<=pick_out;ot<=tags[pick_out*4+0];od<=fill[pick_out]>>(words[pick_out*4+0]*32);end
 if(ov && out_ready)begin ov<=0;rr<=oi==ACTIVE-1?0:oi+1;
 if(count[oi]==1)begin state[oi]<=0;count[oi]<=0;end else begin count[oi]<=count[oi]-1;for(j=0;j<3;j=j+1)begin tags[oi*4+j]<=tags[oi*4+j+1];words[oi*4+j]<=words[oi*4+j+1];end end
 end
 end end
 endmodule
