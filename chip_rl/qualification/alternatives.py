"""Original parallel alternatives, promoted to the candidate catalog only after testing."""
from ..expansion.integrity_rtl import HEADER,BUFFER

def coalesce_representatives():
 return HEADER+'''localparam N=2*K;reg [15:0] segments[0:N-1];reg [7:0] members[0:N-1];reg [3:0] ranks[0:N-1];reg [N-1:0] first;reg [3:0] total;reg [255:0] y;integer i,j,s;
 always @*begin
 y=0;first=0;total=0;
 for(i=0;i<N;i=i+1)segments[i]=(in_data[16*i+:16]/WIDTH)*WIDTH;
 for(i=0;i<N;i=i+1)begin
  first[i]=in_data[128+i];members[i]=0;ranks[i]=0;
  for(j=0;j<N;j=j+1)begin
   if(j<i && in_data[128+j] && segments[j]==segments[i])first[i]=0;
   members[i][j]=in_data[128+j] && segments[j]==segments[i];
  end
  ranks[i]=total;if(first[i])total=total+1;
 end
 y[3:0]=total;
 for(s=0;s<N;s=s+1)for(i=0;i<N;i=i+1)if(first[i] && ranks[i]==s)begin y[8+24*s+:16]=segments[i];y[24+24*s+:8]=members[i];end
 end
 '''+BUFFER+'endmodule'

def histogram_parallel_bins():
 return HEADER+'''reg [WIDTH-1:0] counts[0:DEPTH-1],next_counts[0:DEPTH-1];reg [WIDTH-1:0] previous;reg [255:0] y;integer i,j,index;
 always @*begin
 y=0;y[144+:16]=in_data[192+:16];previous=0;index=0;
 for(j=0;j<DEPTH;j=j+1)begin
  next_counts[j]=in_data[40]?0:counts[j];
  for(i=0;i<K;i=i+1)if(in_data[32+i] && in_data[8*i+:8]==j)next_counts[j]=next_counts[j]+in_data[48+8*i+:8];
 end
 for(i=0;i<K;i=i+1)if(in_data[32+i])begin
  index=in_data[8*i+:8];
  if(index<DEPTH)begin
   previous=in_data[40]?0:counts[index];
   for(j=0;j<K;j=j+1)if(j<i && in_data[32+j] && in_data[8*j+:8]==index)previous=previous+in_data[48+8*j+:8];
   y[16*i+:16]=previous;y[128+i]=1;
  end else y[132+i]=1;
 end
 for(i=0;i<K;i=i+1)begin index=in_data[128+8*i+:8];if(index<DEPTH)y[64+16*i+:16]=next_counts[index];end
 end
 always @(posedge clk)begin
 if(rst)begin for(j=0;j<DEPTH;j=j+1)counts[j]<=0;end
 else if(in_valid && in_ready)begin for(j=0;j<DEPTH;j=j+1)counts[j]<=next_counts[j];end
 end
 '''+BUFFER+'endmodule'
