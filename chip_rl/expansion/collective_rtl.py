"""Original collective datapaths; no CUDA or third-party RTL is reused."""
from .integrity_rtl import HEADER,BUFFER

def scan(alt):
 if alt=='serial':
  return HEADER+'''localparam N=2*K;reg busy,ov,exclusive;reg [3:0] index;reg [127:0] values;reg [7:0] mask,heads;reg [31:0] acc,base,next_acc;reg [255:0] data;
 assign in_ready=!rst && !busy && !ov;assign out_valid=!rst && ov;assign out_data=data;
 always @*begin base=heads[0]?0:acc;next_acc=base+{{(32-WIDTH){values[WIDTH-1]}},values[WIDTH-1:0]};end
 always @(posedge clk)begin
 if(rst)begin busy<=0;ov<=0;exclusive<=0;index<=0;values<=0;mask<=0;heads<=0;acc<=0;data<=0;end
 else begin
  if(ov && out_ready)ov<=0;
  if(in_valid && in_ready)begin busy<=1;index<=0;values<=in_data[127:0];mask<=in_data[128+:8];heads<=in_data[136+:8];exclusive<=in_data[144];acc<=in_data[160+:32];data<=0;end
  else if(busy)begin
   if(mask[0])begin acc<=next_acc;data[32*index+:32]<=exclusive?base:next_acc;end
   values<=values>>16;mask<=mask>>1;heads<=heads>>1;index<=index+1;
   if(index==N-1)begin busy<=0;ov<=1;end
  end
 end end endmodule'''
 if alt=='tree':
  return HEADER+'''localparam N=2*K;reg [31:0] sums[0:3][0:N-1];reg heads[0:3][0:N-1];reg [255:0] y;reg [31:0] value;integer i,j;
 always @*begin y=0;value=0;
  for(i=0;i<N;i=i+1)begin sums[0][i]=in_data[128+i]?{{(32-WIDTH){in_data[16*i+WIDTH-1]}},in_data[16*i+:WIDTH]}:0;heads[0][i]=in_data[128+i] && in_data[136+i];end
  for(j=0;j<3;j=j+1)for(i=0;i<N;i=i+1)begin
   sums[j+1][i]=sums[j][i];heads[j+1][i]=heads[j][i];
   if(i>=(1<<j))begin if(!heads[j][i])sums[j+1][i]=sums[j][i-(1<<j)]+sums[j][i];heads[j+1][i]=heads[j][i-(1<<j)]|heads[j][i];end
  end
  for(i=0;i<N;i=i+1)if(in_data[128+i])begin value=sums[3][i]+(heads[3][i]?0:in_data[160+:32]);if(in_data[144])value=value-sums[0][i];y[32*i+:32]=value;end
 end
 '''+BUFFER+'endmodule'
 return HEADER+'''localparam N=2*K;reg [31:0] acc,value;reg [255:0] y;integer i;
 always @*begin acc=in_data[160+:32];value=0;y=0;
 for(i=0;i<N;i=i+1)if(in_data[128+i])begin
  if(in_data[136+i])acc=0;value={{(32-WIDTH){in_data[16*i+WIDTH-1]}},in_data[16*i+:WIDTH]};
  y[32*i+:32]=in_data[144]?acc:acc+value;acc=acc+value;
 end end
 '''+BUFFER+'endmodule'

def topk(alt):
 header=HEADER+'''localparam N=2*K;
 function signed [15:0] lane;input [511:0] packet;input integer index;begin lane={{(16-WIDTH){packet[16*index+WIDTH-1]}},packet[16*index+:WIDTH]};end endfunction
'''
 if alt=='rank':
  return header+'''reg [255:0] y;integer i,j,rank,total;
  always @*begin y=0;rank=0;total=0;
   for(i=0;i<N;i=i+1)if(in_data[128+i])begin
    rank=0;for(j=0;j<N;j=j+1)if(in_data[128+j] && ((lane(in_data,j)>lane(in_data,i)) || ((lane(in_data,j)==lane(in_data,i)) && j<i)))rank=rank+1;
    if(rank<K && rank<in_data[136+:3])begin y[8+24*rank+:16]=lane(in_data,i);y[24+24*rank+:8]=i;total=total+1;end
   end y[3:0]=total;
  end
  '''+BUFFER+'endmodule'
 return header+'''reg signed [15:0] values[0:K-1];reg [7:0] ids[0:K-1];reg signed [15:0] carry,old;reg [7:0] index,old_index;integer i,j,count,limit;reg [255:0] y;
 always @*begin y=0;count=0;limit=0;carry=0;old=0;index=0;old_index=0;
  for(j=0;j<K;j=j+1)begin values[j]=0;ids[j]=0;end
  for(i=0;i<N;i=i+1)if(in_data[128+i])begin
   carry=lane(in_data,i);index=i;
   for(j=0;j<K;j=j+1)if(j>=count || carry>values[j] || (carry==values[j] && index<ids[j]))begin old=values[j];old_index=ids[j];values[j]=carry;ids[j]=index;carry=old;index=old_index;end
   if(count<K)count=count+1;
  end
  limit=in_data[136+:3];if(limit>count)limit=count;y[3:0]=limit;
  for(j=0;j<K;j=j+1)if(j<limit)begin y[8+24*j+:16]=values[j];y[24+24*j+:8]=ids[j];end
 end
 '''+BUFFER+'endmodule'

def histogram(alt):
 if alt=='serial':
  return HEADER+'''reg [WIDTH-1:0] counts[0:DEPTH-1];reg busy,ov;reg [2:0] index;reg [31:0] addresses,deltas,queries;reg [3:0] mask;reg [255:0] data;integer j;
  assign in_ready=!rst && !busy && !ov;assign out_valid=!rst && ov;assign out_data=data;
  always @(posedge clk)begin
   if(rst)begin for(j=0;j<DEPTH;j=j+1)counts[j]<=0;busy<=0;ov<=0;index<=0;addresses<=0;deltas<=0;queries<=0;mask<=0;data<=0;end
   else begin
    if(ov && out_ready)ov<=0;
    if(in_valid && in_ready)begin
     if(in_data[40])for(j=0;j<DEPTH;j=j+1)counts[j]<=0;
     busy<=1;index<=0;addresses<=in_data[31:0];deltas<=in_data[48+:32];queries<=in_data[128+:32];mask<=in_data[32+:4];data<=0;data[144+:16]<=in_data[192+:16];
    end else if(busy)begin
     if(index<K)begin
      if(mask[0])begin
       if(addresses[7:0]<DEPTH)begin data[16*index+:16]<=counts[addresses[7:0]];data[128+index]<=1;counts[addresses[7:0]]<=counts[addresses[7:0]]+deltas[7:0];end
       else data[132+index]<=1;
      end
      addresses<=addresses>>8;deltas<=deltas>>8;mask<=mask>>1;index<=index+1;
     end else begin
      for(j=0;j<K;j=j+1)if(queries[8*j+:8]<DEPTH)data[64+16*j+:16]<=counts[queries[8*j+:8]];
      busy<=0;ov<=1;
     end
    end
   end end endmodule'''
 return HEADER+'''reg [WIDTH-1:0] counts[0:DEPTH-1],next_counts[0:DEPTH-1];reg [255:0] y;integer i,j,index;
 always @*begin y=0;y[144+:16]=in_data[192+:16];index=0;
  for(j=0;j<DEPTH;j=j+1)next_counts[j]=in_data[40]?0:counts[j];
  for(i=0;i<K;i=i+1)if(in_data[32+i])begin
   index=in_data[8*i+:8];
   if(index<DEPTH)begin y[16*i+:16]=next_counts[index];y[128+i]=1;next_counts[index]=next_counts[index]+in_data[48+8*i+:8];end
   else y[132+i]=1;
  end
  for(i=0;i<K;i=i+1)begin index=in_data[128+8*i+:8];if(index<DEPTH)y[64+16*i+:16]=next_counts[index];end
 end
 always @(posedge clk)begin
  if(rst)begin for(j=0;j<DEPTH;j=j+1)counts[j]<=0;end
  else if(in_valid && in_ready)begin for(j=0;j<DEPTH;j=j+1)counts[j]<=next_counts[j];end
 end
 '''+BUFFER+'endmodule'

def mutate(c,s,label):
 if label=='semantic':
  if c.name=='scan':return s.replace('if(in_data[136+i])acc=0;','')
  if c.name=='topk':return s.replace('index<ids[j]','index>ids[j]')
  return s.replace('next_counts[index]=next_counts[index]+','next_counts[index]=counts[index]+')
 if label=='order':
  if c.name=='scan':return s.replace('in_data[144]?acc:acc+value','in_data[144]?acc+value:acc')
  if c.name=='topk':return s.replace('y[24+24*j+:8]=ids[j];','y[24+24*j+:8]=N-1-ids[j];')
  return s.replace('=next_counts[index];end','=counts[index];end')
 if label=='dimension':
  if c.name in ('scan','topk'):return s.replace('localparam N=2*K','localparam N=8')
  return s.replace('index<DEPTH','index<16')
 if label=='state_reset':return s.replace('for(j=0;j<DEPTH;j=j+1)counts[j]<=0;', 'for(j=0;j<DEPTH;j=j+1)counts[j]<=counts[j];')
 return s
