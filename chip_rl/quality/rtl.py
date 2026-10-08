from .spec import HEADER
from ..memory.rtl import tlb as original_tlb
CATALOG={'tlb':('w1','w2','w4','w1r1','w2r2','w4r4'),'dot':('parallel','tree','fold1','fold2','fold4','adaptive','shift1','shift2','shift4','shiftadaptive'),'tensor':('parallel','tree','fold1','fold2','fold4','adaptive','shift1','shift2','shift4','shiftadaptive')}
def tlb(label):
 walkers=int(label[1]);roots=int(label[3]) if len(label)>2 else 0
 s=original_tlb().replace('localparam WALKERS=1;',f'localparam WALKERS={walkers};')
 if not roots:return s
 s=s.replace(' reg [2:0] state',f''' localparam ROOTS={roots};
 reg rv[0:ROOTS-1];reg [1:0] ra[0:ROOTS-1];reg [3:0] rh[0:ROOTS-1];reg [15:0] rp[0:ROOTS-1];integer rnext,rhit;
 reg [2:0] state''')
 s=s.replace(' free_idx=-1;', ' rhit=-1;for(i=0;i<ROOTS;i=i+1)if(rv[i] && ra[i]==req_aux[1:0] && rh[i]==req_addr[15:12])rhit=i;\n free_idx=-1;')
 s=s.replace(' for(j=0;j<WALKERS;j=j+1)begin state[j]<=0;', ' rnext<=0;for(j=0;j<ROOTS;j=j+1)rv[j]<=0;\n for(j=0;j<WALKERS;j=j+1)begin state[j]<=0;')
 s=s.replace(' else state[free_idx]<=1;', " else if(rhit>=0)begin state[free_idx]<=3;leafaddr[free_idx]<=rp[rhit]+({12'b0,req_addr[11:8]}<<2);end else state[free_idx]<=1;")
 s=s.replace(' else begin state[resp_tag]<=3;', " else begin rv[rnext]<=1;ra[rnext]<=aux[resp_tag][1:0];rh[rnext]<=va[resp_tag][15:12];rp[rnext]<={resp_data[15:2],2'b00};rnext<=rnext==ROOTS-1?0:rnext+1;state[resp_tag]<=3;")
 s=s.replace(' if(inv_valid)begin', ' if(inv_valid)begin\n for(j=0;j<ROOTS;j=j+1)if(ra[j]==inv_asid)rv[j]<=0;')

 return s

def design(c,label=None):
 label=label or CATALOG[c.name][0]
 if label not in CATALOG[c.name]:raise ValueError('architecture')
 if c.name=='tlb':return tlb(label)
 s=HEADER+'''reg ov;reg [383:0] od;
 assign out_valid=!rst && ov;assign out_data=od;
 '''
 if label in ('parallel','tree'):
  s+='assign in_ready=!rst && (!ov || out_ready);wire [383:0] answer;\n'
  s+='genvar r,c,k;generate for(r=0;r<M;r=r+1)begin:ROW for(c=0;c<N;c=c+1)begin:COL\n'
  if label=='parallel':
   s+='wire signed [23:0] sums[0:K];assign sums[0]=0;for(k=0;k<K;k=k+1)begin:PROD wire signed [7:0] a,b;wire signed [15:0] p;assign a=in_data[8*(16*r+k)+:8];assign b=in_data[512+8*(4*k+c)+:8];assign p=a*b;assign sums[k+1]=sums[k]+p;end assign answer[24*(r*N+c)+:24]=sums[K];\n'
  else:
   # Fixed 16-leaf tree with inactive leaves zero; synthesis removes inactive logic.
   s+='wire signed [15:0] p[0:15];for(k=0;k<16;k=k+1)begin:P if(k<K)begin wire signed [7:0] a,b;assign a=in_data[8*(16*r+k)+:8];assign b=in_data[512+8*(4*k+c)+:8];assign p[k]=a*b;end else assign p[k]=0;end\n'
   for level,width,count in [(1,17,8),(2,18,4),(3,19,2),(4,20,1)]:
    prev='p' if level==1 else f's{level-1}'
    s+=f'wire signed [{width-1}:0] s{level}[0:{count-1}];for(k=0;k<{count};k=k+1)begin:L{level} assign s{level}[k]={prev}[2*k]+{prev}[2*k+1];end\n'
   s+='assign answer[24*(r*N+c)+:24]=s4[0];\n'
  s+='end end if(M*N<16)assign answer[383:24*M*N]=0;endgenerate\n'
  return s+'''always @(posedge clk)begin if(rst)begin ov<=0;od<=0;end else if(in_ready)begin ov<=in_valid;if(in_valid)od<=answer;end end endmodule\n'''
 lanes='((K+3)/4)' if label in ('adaptive','shiftadaptive') else label[-1]
 s+=f'localparam LANES={lanes},AW=15+$clog2(K+1);\n'
 s+='''reg busy;reg [1023:0] command;integer pos;
 assign in_ready=!rst && !busy && !ov;
 genvar r,c;generate for(r=0;r<M;r=r+1)begin:R for(c=0;c<N;c=c+1)begin:C
 reg signed [AW-1:0] accum;reg signed [AW-1:0] chunk;reg signed [7:0] a,b;reg signed [15:0] p;integer l;
 always @* begin chunk=0;a=0;b=0;p=0;for(l=0;l<LANES;l=l+1)begin if(pos+l<K)begin a=command[8*(16*r+pos+l)+:8];b=command[512+8*(4*(pos+l)+c)+:8];p=a*b;chunk=chunk+p;end end end
 wire signed [AW-1:0] sum=accum+chunk;
 always @(posedge clk)begin
 if(rst)begin accum<=0;od[24*(r*N+c)+:24]<=0;end
 else if(in_valid && in_ready)accum<=0;
 else if(busy)begin accum<=sum;if(pos+LANES>=K)od[24*(r*N+c)+:24]<=sum;end
 end end end
 if(M*N<16)always @(posedge clk)od[383:24*M*N]<=0;endgenerate
 always @(posedge clk)begin
 if(rst)begin busy<=0;ov<=0;pos<=0;command<=0;end else begin
 if(ov && out_ready)ov<=0;
 if(in_valid && in_ready)begin busy<=1;command<=in_data;pos<=0;end
 else if(busy)begin if(pos+LANES>=K)begin busy<=0;ov<=1;end else pos<=pos+LANES;end
 end end endmodule
'''
 if label.startswith('shift'):
  s=s.replace('reg signed [AW-1:0] accum;', 'reg [8*K-1:0] qa,qb;integer q;reg signed [AW-1:0] accum;')
  s=s.replace('command[8*(16*r+pos+l)+:8]', 'qa[8*l+:8]').replace('command[512+8*(4*(pos+l)+c)+:8]', 'qb[8*l+:8]')
  s=s.replace('wire signed [AW-1:0] sum=accum+chunk;', """always @(posedge clk)begin
 if(rst)begin qa<=0;qb<=0;end
 else if(in_valid && in_ready)begin for(q=0;q<K;q=q+1)begin qa[8*q+:8]<=in_data[8*(16*r+q)+:8];qb[8*q+:8]<=in_data[512+8*(4*q+c)+:8];end end
 else if(busy)begin qa<=qa>>(8*LANES);qb<=qb>>(8*LANES);end end
 wire signed [AW-1:0] sum=accum+chunk;""")
 return s
