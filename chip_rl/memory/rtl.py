from .spec import HEADER
CATALOG={'mshr':('ring','shift'),'tlb':('blocking','dual')}

def mshr(architecture='ring'):
 shift=architecture=='shift'
 s=HEADER+'''localparam ACTIVE=ENTRIES;
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
 tags[target*4+TAIL]<=req_tag;words[target*4+TAIL]<=req_addr[1:0];count[target]<=count[target]+1;
 end end
 if(!ov && pick_out>=0)begin ov<=1;oi<=pick_out;ot<=tags[pick_out*4+HEAD];od<=fill[pick_out]>>(words[pick_out*4+HEAD]*32);end
 if(ov && out_ready)begin ov<=0;rr<=oi==ACTIVE-1?0:oi+1;
 if(count[oi]==1)begin state[oi]<=0;count[oi]<=0;end else begin count[oi]<=count[oi]-1;POP end
 end
 end end
 endmodule
'''
 s=s.replace('TAIL','count[target]' if shift else '((head[target]+count[target])&3)').replace('HEAD','0' if shift else 'head[pick_out]')
 pop='for(j=0;j<3;j=j+1)begin tags[oi*4+j]<=tags[oi*4+j+1];words[oi*4+j]<=words[oi*4+j+1];end' if shift else 'head[oi]<=head[oi]+1;'
 return s.replace('POP',pop)

def design(c,architecture=None):
 if c.name=='mshr':return mshr(architecture or 'ring')
 return tlb(architecture or 'blocking')

def tlb(architecture='blocking'):
 walkers=1 if architecture=='blocking' else 2
 return HEADER+f'localparam WALKERS={walkers};\n'+'''
 reg [2:0] state[0:WALKERS-1];reg [15:0] va[0:WALKERS-1],leafaddr[0:WALKERS-1];
 reg [7:0] aux[0:WALKERS-1],tag[0:WALKERS-1];reg dirty[0:WALKERS-1];
 reg [31:0] result[0:WALKERS-1];reg [1:0] fault[0:WALKERS-1];
 reg cv[0:ENTRIES-1];reg [7:0] vpn[0:ENTRIES-1],ppn[0:ENTRIES-1];
 reg [1:0] asid[0:ENTRIES-1];reg [3:0] flags[0:ENTRIES-1];reg [3:0] victim;
 reg mv,ov,mroot;reg [15:0] ma;reg [3:0] mi,oi,rr;reg [7:0] ot;reg [31:0] od;reg [1:0] ofault;
 integer i,j,free_idx,hit,pick_mem,pick_out,idx;
 function permitted;input [3:0] f;input [7:0] a;begin permitted=a[3]?f[3]:(a[2]?f[2]:f[1]);end endfunction
 function [15:0] rootaddr;input [15:0] address;input [7:0] a;begin rootaddr=16'h8000+({14'b0,a[1:0]}<<8)+({12'b0,address[15:12]}<<2);end endfunction
 always @* begin
 free_idx=-1;hit=-1;pick_mem=-1;pick_out=-1;
 for(i=0;i<WALKERS;i=i+1)begin
 if(state[i]==0 && free_idx<0)free_idx=i;
 idx=(rr+i)%WALKERS;
 if((state[idx]==1 || state[idx]==3) && pick_mem<0)pick_mem=idx;
 if(state[idx]==5 && !(inv_valid && aux[idx][1:0]==inv_asid) && pick_out<0)pick_out=idx;
 end
 for(i=0;i<ENTRIES;i=i+1)if(cv[i] && vpn[i]==req_addr[15:8] && asid[i]==req_aux[1:0])hit=i;
 end
 assign req_ready=!rst && !inv_valid && free_idx>=0;
 assign mem_valid=!rst && mv;assign mem_addr=ma;assign mem_tag=mi;assign resp_ready=!rst;
 assign out_valid=!rst && ov;assign out_tag=ot;assign out_data=od;assign out_fault=ofault;
 always @(posedge clk)begin
 if(rst)begin mv<=0;ov<=0;ma<=0;mi<=0;oi<=0;mroot<=0;ot<=0;od<=0;ofault<=0;rr<=0;victim<=0;
 for(j=0;j<WALKERS;j=j+1)begin state[j]<=0;dirty[j]<=0;end
 for(j=0;j<ENTRIES;j=j+1)cv[j]<=0;
 end else begin
 if(req_valid && req_ready)begin
 va[free_idx]<=req_addr;aux[free_idx]<=req_aux;tag[free_idx]<=req_tag;dirty[free_idx]<=0;
 if(hit>=0)begin state[free_idx]<=5;fault[free_idx]<=permitted(flags[hit],req_aux)?0:2;
 result[free_idx]<=permitted(flags[hit],req_aux)?{16'b0,ppn[hit],req_addr[7:0]}:0;end
 else state[free_idx]<=1;
 end
 if(!mv && pick_mem>=0 && !inv_valid)begin
 mv<=1;mi<=pick_mem;mroot<=state[pick_mem]==1 || dirty[pick_mem];
 ma<=(state[pick_mem]==1 || dirty[pick_mem])?rootaddr(va[pick_mem],aux[pick_mem]):leafaddr[pick_mem];
 if(dirty[pick_mem])begin state[pick_mem]<=1;dirty[pick_mem]<=0;end
 end
 if(mv && mem_ready)begin mv<=0;state[mi]<=mroot?2:4;end
 if(resp_valid && resp_tag<WALKERS)begin
 if(dirty[resp_tag] || (inv_valid && aux[resp_tag][1:0]==inv_asid))begin state[resp_tag]<=1;dirty[resp_tag]<=0;end
 else if(state[resp_tag]==2)begin
 if(!resp_data[0])begin state[resp_tag]<=5;fault[resp_tag]<=1;result[resp_tag]<=0;end
 else begin state[resp_tag]<=3;leafaddr[resp_tag]<={resp_data[15:2],2'b00}+({12'b0,va[resp_tag][11:8]}<<2);end
 end else if(state[resp_tag]==4)begin
 state[resp_tag]<=5;fault[resp_tag]<=!resp_data[0]?1:!permitted(resp_data[3:0],aux[resp_tag])?2:0;
 result[resp_tag]<=resp_data[0] && permitted(resp_data[3:0],aux[resp_tag])?{16'b0,resp_data[15:8],va[resp_tag][7:0]}:0;
 if(resp_data[0])begin cv[victim]<=1;vpn[victim]<=va[resp_tag][15:8];asid[victim]<=aux[resp_tag][1:0];ppn[victim]<=resp_data[15:8];flags[victim]<=resp_data[3:0];victim<=victim==ENTRIES-1?0:victim+1;end
 end end
 if(!ov && pick_out>=0)begin ov<=1;oi<=pick_out;ot<=tag[pick_out];od<=result[pick_out];ofault<=fault[pick_out];end
 if(ov && out_ready)begin ov<=0;state[oi]<=0;rr<=(oi+1)%WALKERS;end
 if(inv_valid)begin
 for(j=0;j<ENTRIES;j=j+1)if(asid[j]==inv_asid)cv[j]<=0;
 for(j=0;j<WALKERS;j=j+1)if(state[j]!=0 && aux[j][1:0]==inv_asid && !(ov && oi==j))begin
 if(state[j]==5)begin state[j]<=1;dirty[j]<=0;end
 else if(!(resp_valid && resp_tag==j))dirty[j]<=1;
 end
 end
 end end endmodule
'''
