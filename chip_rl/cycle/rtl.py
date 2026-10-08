"""Original RTL for experimental cycle controllers. Separate from v1 command models."""
HEADER='''module candidate #(parameter WIDTH=16, DEPTH=16, K=4)(input clk,input rst,input in_valid,output in_ready,input [511:0] in_data,
 output out_valid,input out_ready,output [255:0] out_data);
 reg [255:0] y;assign out_data=y;assign in_ready=!rst;assign out_valid=!rst;
'''

def dma():
 return '''reg [1:0] state;reg [7:0] src,dst;reg [4:0] left;reg [31:0] data;reg done;
 always @*begin y=0;y[0]=state==0;y[1]=state==1;y[2]=state==2;y[3]=state==3;y[4]=done;y[5]=state!=0;
 if(state==1)y[8+:8]=src;if(state==3)begin y[16+:8]=dst;y[32+:32]=data;end end
 always @(posedge clk)begin
  if(rst)begin state<=0;src<=0;dst<=0;left<=0;data<=0;done<=0;end
  else begin done<=0;case(state)
   0:if(in_valid && in_data[0])begin src<=in_data[8+:8]%DEPTH;dst<=in_data[16+:8]%DEPTH;left<=1+{1'b0,in_data[24+:4]};state<=1;end
   1:if(in_data[32])state<=2;
   2:if(in_data[33])begin data<=in_data[64+:32];state<=3;end
   3:if(in_data[34])begin left<=left-1;if(left==1)begin state<=0;done<=1;end else begin src<=(src+1)%DEPTH;dst<=(dst+1)%DEPTH;state<=1;end end
  endcase end
 end
'''

def router():
 return '''reg [4:0] occupied;reg [WIDTH-1:0] payload[0:4];reg [2:0] ptr[0:4];integer win[0:4];integer p,o,i,z;
 always @*begin y=0;
 for(p=0;p<5;p=p+1)begin
  y[p]=occupied[p];if(occupied[p])y[8+16*p+:16]=payload[p];win[p]=-1;
  if(!occupied[p] || in_data[160+p])begin
   for(o=0;o<5;o=o+1)begin i=ptr[p]+o;if(i>=5)i=i-5;
    if(win[p]<0 && in_valid && in_data[i*24] && in_data[i*24+1+:3]==p)win[p]=i;
   end
  end
  if(win[p]>=0)y[96+win[p]]=1;
 end end
 always @(posedge clk)begin
  if(rst)begin occupied<=0;for(z=0;z<5;z=z+1)begin ptr[z]<=0;payload[z]<=0;end end
  else for(z=0;z<5;z=z+1)begin
   if(in_data[160+z])occupied[z]<=0;
   if(win[z]>=0)begin occupied[z]<=1;payload[z]<=in_data[win[z]*24+4+:WIDTH];ptr[z]<=(win[z]==4)?0:win[z]+1;end
  end
 end
'''

def scoreboard():
 return '''reg [K-1:0] occupied;reg [3:0] qs[0:K-1],qd[0:K-1],ql[0:K-1];reg [7:0] qt[0:K-1];reg [3:0] busy[0:15],nb[0:15];reg [1:0] ptr;integer o,i,z,win;
 always @*begin y=0;for(z=0;z<16;z=z+1)nb[z]=(busy[z]>0)?busy[z]-1:0;win=-1;
 for(o=0;o<K;o=o+1)begin i=(ptr+o)%K;
 if(win<0 && occupied[i] && nb[qs[i]]==0 && nb[qd[i]]==0)win=i;end
 if(win>=0)begin nb[qd[win]]=ql[win];y[win]=1;y[24+:8]=qt[win];end
 for(z=0;z<16;z=z+1)y[8+z]=nb[z]!=0;
 for(z=0;z<K;z=z+1)if((!occupied[z] || win==z) && in_valid && in_data[24*z])y[32+z]=1;
 end
 always @(posedge clk)begin
 if(rst)begin occupied<=0;ptr<=0;for(z=0;z<16;z=z+1)busy[z]<=0;for(z=0;z<K;z=z+1)begin qs[z]<=0;qd[z]<=0;ql[z]<=0;qt[z]<=0;end end
 else begin
  for(z=0;z<16;z=z+1)busy[z]<=nb[z];
  if(win>=0)begin occupied[win]<=0;ptr<=(win+1)%K;end
  for(z=0;z<K;z=z+1)if(y[32+z])begin occupied[z]<=1;qs[z]<=in_data[z*24+1+:4];qd[z]<=in_data[z*24+5+:4];ql[z]<=1+{1'b0,in_data[z*24+9+:3]};qt[z]<=in_data[z*24+12+:8];end
 end end
'''

def accelerator():
 return '''reg [1:0] state;reg [7:0] src,dst;reg [4:0] left;reg done;
 reg [7:0] mem[0:DEPTH-1];reg active,ov;reg [7:0] a,b;reg [2:0] idx;reg signed [17:0] acc,result,piece;integer z;
 always @*begin
  piece=$signed(mem[(a+idx)%DEPTH])*$signed(mem[(b+idx)%DEPTH]);
  y=0;y[0]=state==0;y[1]=state==1;y[2]=state==2;y[3]=done;y[4]=!active && !ov;y[5]=ov;y[6]=active;y[7]=state!=0;
  if(state==1)y[8+:8]=src;if(ov)y[32+:18]=result;
 end
 always @(posedge clk)begin
  if(rst)begin state<=0;src<=0;dst<=0;left<=0;done<=0;active<=0;ov<=0;a<=0;b<=0;idx<=0;acc<=0;result<=0;for(z=0;z<DEPTH;z=z+1)mem[z]<=0;end
  else begin
   done<=0;
   if(active)begin acc<=acc+piece;idx<=idx+1;if(idx==K-1)begin result<=acc+piece;active<=0;ov<=1;end end
   else if(ov)begin if(in_data[34])ov<=0;end
   else if(in_valid && in_data[1])begin a<=in_data[40+:8]%DEPTH;b<=in_data[48+:8]%DEPTH;idx<=0;acc<=0;active<=1;end
   case(state)
    0:if(in_valid && in_data[0])begin src<=in_data[8+:8]%DEPTH;dst<=in_data[16+:8]%DEPTH;left<=1+{1'b0,in_data[24+:4]};state<=1;end
    1:if(in_data[32])state<=2;
    2:if(in_data[33])begin mem[dst]<=in_data[64+:8];left<=left-1;if(left==1)begin state<=0;done<=1;end else begin src<=(src+1)%DEPTH;dst<=(dst+1)%DEPTH;state<=1;end end
   endcase
  end
 end
'''

def design(c,alternate=False,mutant=None):
 s=HEADER+globals()[c.name]()+'endmodule\n'
 if alternate=='decoded' and c.name=='router':s=HEADER+decoded_router()+'endmodule\n';alternate=False
 if alternate and alternate!='pruned':
  if c.name in ('router','scoreboard'):
   bound='5' if c.name=='router' else 'K'
   s=s.replace(f'for(o=0;o<{bound};o=o+1)',f'for(o={bound}-1;o>=0;o=o-1)').replace('win[p]<0 && ','').replace('win<0 && ','')
  else:
   # Register encoding changes, same externally specified physical-cycle protocol.
   s=s.replace('reg [1:0] state;','reg [3:0] state;')
   import re
   s=re.sub(r'state([<=>!]+)([0-3])',lambda m:'state'+m[1]+str(1<<int(m[2])),s)
   s=re.sub(r'(?m)(\s)([0-3]):if',lambda m:m[1]+str(1<<int(m[2]))+':if',s)
 if alternate=='pruned':
  for expr in {'dma':['src<=0;','dst<=0;','left<=0;','data<=0;'],
               'router':['payload[z]<=0;'],
               'scoreboard':['qs[z]<=0;','qd[z]<=0;','ql[z]<=0;','qt[z]<=0;'],
               'accelerator':['src<=0;','dst<=0;','left<=0;','a<=0;','b<=0;','idx<=0;','acc<=0;','result<=0;']}[c.name]:
   s=s.replace(expr,'',1)
 if mutant=='late_drop':
  s=s.replace('assign out_data=y;',"reg [15:0] ticks;always @(posedge clk)if(rst)ticks<=0;else ticks<=ticks+1;assign out_data=(ticks<128)?y:256'b0;")
 if mutant=='zero':s=s.replace('assign out_data=y;',"assign out_data=256'b0;")
 elif mutant=='clock':s=s.replace('posedge clk','negedge clk')
 elif mutant=='drop':
  if c.name=='dma':s=s.replace('y[3]=state==3','y[3]=0')
  elif c.name=='router':s=s.replace('y[p]=occupied[p]','y[p]=0')
  elif c.name=='scoreboard':s=s.replace('y[win]=1','y[win]=0')
  else:s=s.replace('y[5]=ov','y[5]=0')
 elif mutant=='stall':
  if c.name=='dma':s=s.replace('3:if(in_data[34])','3:if(1)')
  elif c.name=='router':s=s.replace('if(in_data[160+z])occupied[z]<=0;','occupied[z]<=0;')
  elif c.name=='scoreboard':s=s.replace('busy[z]<=nb[z];','if(in_valid)busy[z]<=nb[z];')
  else:s=s.replace('if(in_data[34])ov<=0;','ov<=0;')
 elif mutant=='unfair' and c.name in ('router','scoreboard'):
  s=s.replace('ptr[p]+o','o').replace('(ptr+o)%K','o')
 elif mutant=='no_reset':
  s=s.replace('state<=0;','state<=state;',1).replace('occupied<=0;','occupied<=occupied;',1)
  if c.name=='accelerator':s=s.replace('mem[z]<=0;','mem[z]<=mem[z];')
 elif mutant=='no_overlap' and c.name=='accelerator':s=s.replace('if(active)begin','if(active && state==0)begin')
 elif mutant=='bad_data' and c.name=='dma':s=s.replace('data<=in_data[64+:32]','data<=0')
 return s

def decoded_router():
 return '''reg [4:0] occupied;reg [WIDTH-1:0] payload[0:4];reg [2:0] ptr[0:4];integer win[0:4];integer p,i,z,l;reg [2:0] rank,best;
 always @*begin y=0;rank=0;best=7;
 for(p=0;p<5;p=p+1)begin
  y[p]=occupied[p];if(occupied[p])y[8+16*p+:16]=payload[p];win[p]=-1;best=7;
  if(!occupied[p] || in_data[160+p])begin
   for(i=0;i<5;i=i+1)begin
    rank=(i>=ptr[p])?i-ptr[p]:i+5-ptr[p];
    if(in_valid && in_data[i*24] && in_data[i*24+1+:3]==p && rank<best)begin win[p]=i;best=rank;end
   end
  end
  for(i=0;i<5;i=i+1)if(win[p]==i)y[96+i]=1;
 end end
 always @(posedge clk)begin
  if(rst)begin occupied<=0;for(z=0;z<5;z=z+1)begin ptr[z]<=0;payload[z]<=0;end end
  else for(z=0;z<5;z=z+1)begin
   if(in_data[160+z])occupied[z]<=0;
   if(win[z]>=0)begin occupied[z]<=1;ptr[z]<=(win[z]==4)?0:win[z]+1;
    for(l=0;l<5;l=l+1)if(win[z]==l)payload[z]<=in_data[l*24+4+:WIDTH];
   end
  end
 end
'''
