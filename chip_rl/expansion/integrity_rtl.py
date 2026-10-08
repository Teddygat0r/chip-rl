"""Original integrity and free-list RTL generators, independent of the Python oracles."""
HEADER='''module candidate #(parameter WIDTH=16,DEPTH=8,K=4)(input clk,input rst,input in_valid,output in_ready,input [511:0] in_data,output out_valid,input out_ready,output [255:0] out_data);
'''
BUFFER='''reg ov;reg [255:0] data;assign in_ready=!rst && (!ov || out_ready);assign out_valid=!rst && ov;assign out_data=data;
 always @(posedge clk)if(rst)begin ov<=0;data<=0;end else if(in_ready)begin ov<=in_valid;if(in_valid)data<=y;end
'''

def ecc(alt):
 front='''localparam P=(WIDTH<12)?4:5;localparam H=WIDTH+P;
 reg [H-1:0] enc;reg [H:0] code;reg [P-1:0] syn;reg parity;integer i,j,di;reg v;
 always @*begin enc=0;di=0;v=0;
 for(i=1;i<=H;i=i+1)if((i&(i-1))!=0)begin enc[i-1]=in_data[di];di=di+1;end
 for(j=0;j<P;j=j+1)begin v=0;for(i=1;i<=H;i=i+1)if((i&(1<<j))!=0)v=v^enc[i-1];enc[(1<<j)-1]=v;end
 code=in_data[32]?in_data[H:0]:{^enc,enc};syn=0;
 for(i=1;i<=H;i=i+1)if(code[i-1])syn=syn^i;
 parity=^code;end
'''
 correction='''reg [H:0] corrected;reg [1:0] status;reg [WIDTH-1:0] payload;reg [255:0] y;integer q,z;
 always @*begin corrected=CODE;status=0;payload=0;z=0;y=0;
 if(SYN!=0)begin if(PARITY && SYN<=H)begin corrected[SYN-1]=~CODE[SYN-1];status=1;end else begin corrected=0;status=2;end end
 else if(PARITY)begin corrected[H]=~CODE[H];status=1;end
 for(q=1;q<=H;q=q+1)if((q&(q-1))!=0)begin payload[z]=corrected[q-1];z=z+1;end
 y[31:0]=corrected;y[32+:16]=payload;y[48+:2]=status;end
'''
 if alt=='pipeline':
  middle='''reg v1,v2;reg [H:0] saved_code;reg [P-1:0] saved_syn;reg saved_parity;reg [255:0] data;
  wire r2=!v2 || out_ready;wire r1=!v1 || r2;assign in_ready=!rst && r1;assign out_valid=!rst && v2;assign out_data=data;
  always @(posedge clk)begin
   if(rst)begin v1<=0;v2<=0;saved_code<=0;saved_syn<=0;saved_parity<=0;data<=0;end
   else begin
    if(r2)begin v2<=v1;if(v1)data<=y;end
    if(r1)begin v1<=in_valid;if(in_valid)begin saved_code<=code;saved_syn<=syn;saved_parity<=parity;end end
   end end
'''
  return HEADER+front+correction.replace('CODE','saved_code').replace('SYN','saved_syn').replace('PARITY','saved_parity')+middle+'endmodule'
 if alt=='decoded':
  correction=correction.replace('corrected[SYN-1]=~CODE[SYN-1];','for(q=1;q<=H;q=q+1)corrected[q-1]=CODE[q-1]^(SYN==q);')
 return HEADER+front+correction.replace('CODE','code').replace('SYN','syn').replace('PARITY','parity')+BUFFER+'endmodule'

def crc(alt):
 if alt=='baseline':
  return HEADER+'''reg active;reg [31:0] raw,next_raw;reg [15:0] length,next_length;reg [255:0] y;integer j;
  always @*begin
   next_raw=in_data[32]?32'hffffffff:raw;next_length=(in_data[32]?0:length)+(WIDTH/8);y=0;y[48+:16]=in_data[48+:16];
   if(active || in_data[32])begin
    for(j=0;j<WIDTH;j=j+1)begin if(next_raw[0]^in_data[j])next_raw=(next_raw>>1)^32'hedb88320;else next_raw=next_raw>>1;end
    y[31:0]=~next_raw;y[32]=in_data[33];y[64+:16]=next_length;
   end else y[33]=1;
  end
  always @(posedge clk)begin
   if(rst)begin active<=0;raw<=32'hffffffff;length<=0;end
   else if(in_valid && in_ready && (active || in_data[32]))begin raw<=next_raw;length<=next_length;active<=!in_data[33];end
  end
  '''+BUFFER+'endmodule'
 lanes=1 if alt=='serial' else 4
 return HEADER+f'''reg active,busy,ov;reg [31:0] raw,acc,payload,temp;reg [15:0] length,tag,next_length;reg ending;reg [5:0] left;reg [255:0] data;integer j;
 assign in_ready=!rst && !busy && !ov;assign out_valid=!rst && ov;assign out_data=data;
 always @*begin temp=acc;for(j=0;j<{lanes};j=j+1)begin if(temp[0]^payload[j])temp=(temp>>1)^32'hedb88320;else temp=temp>>1;end end
 always @(posedge clk)begin
  if(rst)begin active<=0;busy<=0;ov<=0;raw<=32'hffffffff;acc<=0;payload<=0;length<=0;tag<=0;next_length<=0;ending<=0;left<=0;data<=0;end
  else begin
   if(ov && out_ready)ov<=0;
   if(in_valid && in_ready)begin
    data<=0;data[48+:16]<=in_data[48+:16];
    if(active || in_data[32])begin busy<=1;left<=WIDTH;acc<=in_data[32]?32'hffffffff:raw;payload<=in_data[31:0];tag<=in_data[48+:16];ending<=in_data[33];next_length<=(in_data[32]?0:length)+(WIDTH/8);end
    else begin ov<=1;data[33]<=1;end
   end else if(busy)begin
    acc<=temp;payload<=payload>>{lanes};left<=left-{lanes};
    if(left=={lanes})begin busy<=0;ov<=1;raw<=temp;length<=next_length;active<=!ending;data<=0;data[31:0]<=~temp;data[32]<=ending;data[48+:16]<=tag;data[64+:16]<=next_length;end
   end
  end end endmodule'''

def freelist(alt):
 comb='''localparam [31:0] ALL=32'hffffffff>>(32-DEPTH);
 reg [31:0] free_bits,pool,grants;reg [31:0] ids,pick;reg bad;reg [2:0] total;reg [5:0] available;reg [255:0] y;integer i,j,win;
 always @*begin
  pool=free_bits;pick=0;grants=0;ids=0;total=0;available=0;win=-1;bad=0;y=0;y[96+:16]=in_data[48+:16];
  if(in_data[3])pool=ALL;
  else begin
   bad=(in_data[2:0]>K) || ((in_data[16+:32]&~ALL)!=0) || ((in_data[16+:32]&free_bits)!=0);
   if(!bad)begin pool=free_bits|in_data[16+:32];
    for(j=0;j<K;j=j+1)if(j<in_data[2:0])begin
     pick=pool & (~pool+1);win=0;for(i=0;i<DEPTH;i=i+1)if(pick[i])win=win|i;
     if(pool!=0)begin pool=pool & (pool-1);grants=grants|pick;ids[8*j+:8]=win;total=total+1;end
    end
   end
  end
  for(i=0;i<DEPTH;i=i+1)available=available+pool[i];
  y[2:0]=total;y[3]=bad;y[8+:6]=available;y[16+:32]=grants;y[64+:32]=ids;
 end
'''
 if alt=='baseline':
  return HEADER+comb+'''always @(posedge clk)if(rst)free_bits<=ALL;else if(in_valid && in_ready)free_bits<=pool;
  '''+BUFFER+'endmodule'
 return HEADER+'''localparam [31:0] ALL=32'hffffffff>>(32-DEPTH);
 reg [31:0] free_bits,grants,ids;reg [2:0] request,total;reg [15:0] tag;reg busy,ov;reg [255:0] data;
 reg bad;integer i,win;reg [5:0] available;reg [31:0] remaining;
 assign in_ready=!rst && !busy && !ov;assign out_valid=!rst && ov;assign out_data=data;
 always @*begin
  bad=(in_data[2:0]>K) || ((in_data[16+:32]&~ALL)!=0) || ((in_data[16+:32]&free_bits)!=0);
  win=-1;for(i=DEPTH-1;i>=0;i=i-1)if(free_bits[i])win=i;
  remaining=free_bits;available=0;for(i=0;i<DEPTH;i=i+1)available=available+free_bits[i];
 end
 always @(posedge clk)begin
  if(rst)begin free_bits<=ALL;grants<=0;ids<=0;request<=0;total<=0;tag<=0;busy<=0;ov<=0;data<=0;end
  else begin
   if(ov && out_ready)ov<=0;
   if(in_valid && in_ready)begin
    data<=0;data[96+:16]<=in_data[48+:16];
    if(in_data[3])begin free_bits<=ALL;ov<=1;data[8+:6]<=DEPTH;end
    else if(bad)begin ov<=1;data[3]<=1;data[8+:6]<=available;end
    else begin free_bits<=free_bits|in_data[16+:32];busy<=1;grants<=0;ids<=0;total<=0;request<=in_data[2:0];tag<=in_data[48+:16];end
   end else if(busy)begin
    if(total==request || win<0)begin busy<=0;ov<=1;data<=0;data[2:0]<=total;data[8+:6]<=available;data[16+:32]<=grants;data[64+:32]<=ids;data[96+:16]<=tag;end
    else begin free_bits[win]<=0;grants[win]<=1;ids[8*total+:8]<=win;total<=total+1;end
   end
  end end endmodule'''

def mutate(c,s,label):
 if label=='semantic':
  if c.name=='ecc':return s.replace('corrected[syn-1]=~code[syn-1];','corrected[syn-1]=code[syn-1];')
  if c.name=='crc':return s.replace("32'hedb88320","32'h04c11db7")
  return s.replace('pool=pool & (pool-1);','pool=pool;')
 if label=='order':
  if c.name=='ecc':return s.replace('status=2;','status=0;')
  if c.name=='crc':return s.replace('in_data[j]','in_data[WIDTH-1-j]')
  return s.replace('ids[8*j+:8]=win;','ids[8*j+:8]=DEPTH-1-win;')
 if label=='dimension':
  if c.name=='ecc':return s.replace('(WIDTH<12)?4:5','5')
  if c.name=='crc':return s.replace('j<WIDTH','j<16').replace('(WIDTH/8)','2')
  return s.replace("32'hffffffff>>(32-DEPTH)","32'hffffffff").replace('i<DEPTH','i<32')
 if label=='state_reset':
  if c.name=='crc':return s.replace("active<=0;raw<=32'hffffffff;length<=0;",'active<=active;raw<=raw;length<=length;')
  return s.replace('if(rst)free_bits<=ALL;', 'if(rst)free_bits<=free_bits;')
 return s
