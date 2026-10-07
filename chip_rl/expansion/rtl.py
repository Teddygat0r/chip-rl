"""Original synthesizable datapaths; no third-party RTL is incorporated."""
HEADER='''module candidate #(parameter WIDTH=16,DEPTH=8,K=4)(input clk,input rst,input in_valid,output in_ready,input [511:0] in_data,output out_valid,input out_ready,output [255:0] out_data);
 localparam N=2*K;
'''
def kernel(name,decoded=False):
 if name=='permute':
  expr='''for(i=0;i<N;i=i+1)if(in_data[152+i] && in_data[128+3*i+:3]<N)y[16*i+:16]=(in_data[(in_data[128+3*i+:3])*16+:WIDTH]);'''
  if decoded:expr='''for(i=0;i<N;i=i+1)for(j=0;j<N;j=j+1)if(in_data[152+i] && in_data[128+3*i+:3]==j)y[16*i+:16]=y[16*i+:16]|in_data[16*j+:WIDTH];'''
  return 'reg [255:0] y;integer i,j;always @*begin y=0;'+expr+'end\n'
 return '''reg [255:0] y;reg [15:0] base[0:N-1];reg [7:0] masks[0:N-1];integer i,j,count,found;
 always @*begin y=0;count=0;found=-1;for(i=0;i<N;i=i+1)begin base[i]=0;masks[i]=0;end
 for(i=0;i<N;i=i+1)if(in_data[128+i])begin
  found=-1;for(j=0;j<N;j=j+1)if(j<count && base[j]==((in_data[16*i+:16]/WIDTH)*WIDTH))found=j;
  if(found<0)begin base[count]=(in_data[16*i+:16]/WIDTH)*WIDTH;masks[count]=1<<i;count=count+1;end
  else masks[found]=masks[found]|(1<<i);
 end
 y[3:0]=count;for(i=0;i<N;i=i+1)begin y[8+24*i+:16]=base[i];y[24+24*i+:8]=masks[i];end
 end
'''

def transactional(c,alt):
 if alt=='shift_serial':return shift_serial()
 if alt=='serial':
  if c.name=='permute':
   work='''if(saved[152+idx] && saved[128+3*idx+:3]<N)acc[16*idx+:16]<=saved[saved[128+3*idx+:3]*16+:WIDTH];'''
   decl='';comb='';clear=''
  else:
   decl='reg [15:0] bases[0:N-1];reg [7:0] masks[0:N-1];integer j,found;reg [3:0] used;'
   comb='''always @*begin found=-1;for(j=0;j<N;j=j+1)if(j<used && bases[j]==((saved[16*idx+:16]/WIDTH)*WIDTH))found=j;end'''
   clear='used<=0;for(j=0;j<N;j=j+1)begin bases[j]<=0;masks[j]<=0;end'
   work='''if(saved[128+idx])begin
    if(found<0)begin bases[used]<=(saved[16*idx+:16]/WIDTH)*WIDTH;masks[used]<=1<<idx;used<=used+1;end
    else masks[found]<=masks[found]|(1<<idx);
   end'''
  output='acc' if c.name=='permute' else 'result_pack'
  extra='' if c.name=='permute' else '''reg [255:0] result_pack;integer z;always @*begin result_pack=0;result_pack[3:0]=used;for(z=0;z<N;z=z+1)begin result_pack[8+24*z+:16]=bases[z];result_pack[24+24*z+:8]=masks[z];end end'''
  return HEADER+f'''reg busy,ov;reg [3:0] idx;reg [511:0] saved;reg [255:0] acc;{decl}
  assign in_ready=!rst && !busy && !ov;assign out_valid=!rst && ov;assign out_data={output};{comb} {extra}
  always @(posedge clk)begin
   if(rst)begin busy<=0;ov<=0;idx<=0;saved<=0;acc<=0;{clear} end
   else begin
    if(ov && out_ready)ov<=0;
    if(in_valid && in_ready)begin busy<=1;idx<=0;saved<=in_data;acc<=0;{clear} end
    else if(busy)begin {work} idx<=idx+1;if(idx==N-1)begin busy<=0;ov<=1;end end
   end
  end endmodule'''
 s=HEADER+kernel(c.name,alt=='decoded')
 s+='''reg ov;reg [255:0] data;
 assign in_ready=!rst && (!ov || out_ready);assign out_valid=!rst && ov;assign out_data=data;
 always @(posedge clk)if(rst)begin ov<=0;data<=0;end else if(in_ready)begin ov<=in_valid;if(in_valid)data<=y;end
 endmodule'''
 return s

def retirement(shift=False):
 common='''reg [15:0] tickets[0:DEPTH-1],tags[0:DEPTH-1];reg [WIDTH-1:0] values[0:DEPTH-1];reg [DEPTH-1:0] occupied,done;
 reg [15:0] next_ticket;reg [3:0] count,head,tail;reg [255:0] y;integer j;
 wire flush=in_data[2];wire rv=(count!=0) && done[head] && !flush;wire pop=rv && in_data[1];
 wire ready=(count<DEPTH || pop) && !flush;wire push=ready && in_valid && in_data[0];
 assign in_ready=!rst;assign out_valid=!rst;assign out_data=y;
 always @*begin y=0;y[0]=ready;y[1]=rv;y[72+:4]=count;
 if(push)y[8+:16]=next_ticket;if(rv)begin y[24+:16]=tickets[head];y[40+:16]=values[head];y[56+:16]=tags[head];end end
'''
 if not shift:
  body='''always @(posedge clk)begin
   if(rst)begin occupied<=0;done<=0;next_ticket<=0;count<=0;head<=0;tail<=0;for(j=0;j<DEPTH;j=j+1)begin tickets[j]<=0;tags[j]<=0;values[j]<=0;end end
   else if(flush)begin occupied<=0;done<=0;count<=0;head<=0;tail<=0;end
   else begin
    count<=count+push-pop;
    if(in_data[3])for(j=0;j<DEPTH;j=j+1)if(occupied[j] && !done[j] && tickets[j]==in_data[16+:16])begin done[j]<=1;values[j]<=in_data[32+:WIDTH];end
    if(pop)begin occupied[head]<=0;done[head]<=0;head<=(head+1)%DEPTH;end
    if(push)begin occupied[tail]<=1;done[tail]<=0;tickets[tail]<=next_ticket;tags[tail]<=in_data[64+:16];values[tail]<=0;tail<=(tail+1)%DEPTH;next_ticket<=next_ticket+1;end
   end end'''
 else:
  common=common.replace('done[head]','done[0]').replace('tickets[head]','tickets[0]').replace('values[head]','values[0]').replace('tags[head]','tags[0]')
  body='''always @(posedge clk)begin
   if(rst)begin occupied<=0;done<=0;next_ticket<=0;count<=0;head<=0;tail<=0;for(j=0;j<DEPTH;j=j+1)begin tickets[j]<=0;tags[j]<=0;values[j]<=0;end end
   else if(flush)begin occupied<=0;done<=0;count<=0;end
   else begin
    count<=count+push-pop;
    for(j=0;j<DEPTH;j=j+1)begin
     if(j<count-pop)begin
      tickets[j]<=tickets[j+pop];tags[j]<=tags[j+pop];values[j]<=values[j+pop];done[j]<=done[j+pop];
      if(in_data[3] && !done[j+pop] && tickets[j+pop]==in_data[16+:16])begin done[j]<=1;values[j]<=in_data[32+:WIDTH];end
     end else done[j]<=0;
    end
    if(push)begin tickets[count-pop]<=next_ticket;tags[count-pop]<=in_data[64+:16];values[count-pop]<=0;done[count-pop]<=0;next_ticket<=next_ticket+1;end
   end end'''
 return HEADER+common+body+' endmodule'

CATALOG={'scan':('baseline','tree','serial'),'topk':('baseline','rank'),'histogram':('baseline','serial','parallel_bins'),'permute':('baseline','decoded','serial','shift_serial'),'coalesce':('baseline','serial','representatives'),'retire':('baseline','shift','pruned'), 'ecc':('baseline','decoded','pipeline'), 'crc':('baseline','nibble','serial'), 'freelist':('baseline','serial')}
def design(c,alt='baseline',mutant=None):
 if alt not in CATALOG[c.name]:raise ValueError('architecture')
 if c.name=='coalesce' and alt=='representatives':
  from ..qualification.alternatives import coalesce_representatives
  s=coalesce_representatives()
 elif c.name=='histogram' and alt=='parallel_bins':
  from ..qualification.alternatives import histogram_parallel_bins
  s=histogram_parallel_bins()
 elif c.name in ('scan','topk','histogram'):
  from . import collective_rtl
  s=getattr(collective_rtl,c.name)(alt)
 elif c.name in ('ecc','crc','freelist'):
  from . import integrity_rtl
  s=getattr(integrity_rtl,c.name)(alt)
 else:s=retirement(alt=='shift') if c.name=='retire' else transactional(c,alt)
 if alt=='pruned':s=s.replace('for(j=0;j<DEPTH;j=j+1)begin tickets[j]<=0;tags[j]<=0;values[j]<=0;end','')
 if c.name in ('crc','retire'):
  from ..history.adversaries import NAMES as HISTORY_FAULTS,mutate
  if mutant in HISTORY_FAULTS[c.name]:s=mutate(c.name,s,mutant)
 if mutant=='frame_reset_ports':s=s.replace('assign in_ready=!rst;assign out_valid=!rst;',"assign in_ready=1'b1;assign out_valid=1'b1;")
 if mutant=='reset_ready':s=s.replace('if(rst)','if(rst && out_ready)')
 if mutant=='reset_valid':s=s.replace('if(rst)','if(rst && in_valid)')
 if mutant=='reset_priority':s=s.replace('if(rst)','if(rst && !in_valid)')
 if mutant=='late1535':s=s.replace('assign out_valid=!rst',"reg [15:0] accepts;always @(posedge clk)if(rst)accepts<=0;else if(in_valid && in_ready)accepts<=accepts+1;assign out_valid=(accepts<1535) && !rst")
 if mutant=='zero':s=s.replace('assign out_data=data;',"assign out_data=256'b0;").replace('assign out_data=y;',"assign out_data=256'b0;")
 if mutant=='padding':s=s.replace('assign out_data=data;','assign out_data=data ^ {in_data[511],255\'b0};').replace('assign out_data=y;','assign out_data=y ^ {in_data[511],255\'b0};')
 if mutant=='clock':s=s.replace('posedge clk','negedge clk')
 if mutant=='no_reset':s=s.replace('if(rst)begin','if(1\'b0)begin')
 if mutant=='late_drop':s=s.replace('assign out_valid=!rst',"reg [15:0] ticks;always @(posedge clk)if(rst)ticks<=0;else ticks<=ticks+1;assign out_valid=(ticks<256) && !rst")
 if mutant=='stall':s=s.replace('else if(in_ready)begin','else begin') if c.name!='retire' else s.replace('wire pop=rv && in_data[1];','wire pop=rv;')
 if mutant=='semantic':
  if c.name=='permute':s=s.replace('in_data[128+3*i+:3]<N','1\'b1').replace('(in_data[128+3*i+:3])*16','(in_data[128+3*i+:3]%N)*16')
  elif c.name=='coalesce':s=s.replace('masks[found]=masks[found]|(1<<i)','masks[found]=masks[found]')
  else:s=s.replace(' && done[head]','')
 if mutant=='order':
  if c.name=='permute':s=s.replace('y[16*i+:16]','y[16*(N-1-i)+:16]')
  elif c.name=='coalesce':s=s.replace('y[8+24*i+:16]','y[8+24*(N-1-i)+:16]').replace('y[24+24*i+:8]','y[24+24*(N-1-i)+:8]')
  else:s=s.replace('wire flush=in_data[2];',"wire flush=1'b0;")
 if mutant=='dimension':s=s.replace('localparam N=2*K','localparam N=8') if c.name!='retire' else s.replace('count<DEPTH','count<8')
 if mutant=='counter1023':s=s.replace('assign out_valid=!rst',"reg [15:0] accepts;always @(posedge clk)if(rst)accepts<=0;else if(in_valid && in_ready)accepts<=accepts+1;assign out_valid=(accepts<1023) && !rst")
 if mutant=='overwrite' and c.name=='retire':s=s.replace(' && !done[j]','')
 if c.name in ('ecc','crc','freelist'):s=integrity_rtl.mutate(c,s,mutant)
 if c.name in ('scan','topk','histogram'):
  from . import collective_rtl
  s=collective_rtl.mutate(c,s,mutant)
 return s
MUTANTS=('zero','padding','clock','no_reset','late_drop','stall','semantic','order','dimension')

def mutants(name):return MUTANTS+(('overwrite',) if name=='retire' else ('counter1023',))+(('state_reset',) if name in ('crc','freelist','histogram') else ())+(('reset_priority','reset_ready','reset_valid') if name in ('ecc','coalesce','histogram') else ())+(('late1535',) if name=='histogram' else ())+(('count12','saturating_count','crc_wrap_restart') if name=='crc' else ('ticket12','saturating_ticket','numeric_ticket_order','frame_reset_ports') if name=='retire' else ())


def shift_serial():
 return HEADER+"""reg busy,ov;reg [3:0] left;reg [127:0] values;reg [23:0] indices;reg [7:0] mask;reg [255:0] acc;reg [15:0] value;
 assign in_ready=!rst && !busy && !ov;assign out_valid=!rst && ov;assign out_data=acc;
 always @*begin value=0;if(mask[0] && indices[2:0]<N)value=values[16*indices[2:0]+:WIDTH];end
 always @(posedge clk)begin
  if(rst)begin busy<=0;ov<=0;left<=0;values<=0;indices<=0;mask<=0;acc<=0;end
  else begin
   if(ov && out_ready)ov<=0;
   if(in_valid && in_ready)begin busy<=1;left<=N;values<=in_data[127:0];indices<=in_data[128+:24];mask<=in_data[152+:8];acc<=0;end
   else if(busy)begin acc<=(acc>>16)|({240'b0,value}<<(16*(N-1)));indices<=indices>>3;mask<=mask>>1;left<=left-1;if(left==1)begin busy<=0;ov<=1;end end
  end end endmodule"""
