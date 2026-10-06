"""Distinct parameterized microarchitectures, authored locally for this benchmark."""
from .rtl import Parameters, design

def serial(c,lanes=1):
    assert c.name in ('dot','tensor')
    if c.name=='tensor':lanes=1
    steps=c.k//lanes if c.name=='dot' else 4*c.k
    if c.name=='dot':
        terms=' + '.join(f'($signed(saved[(idx*{lanes}+{j})*8+:8])*$signed(saved[32+(idx*{lanes}+{j})*8+:8]))' for j in range(lanes))
        comb='piece='+terms+';';body='acc<=acc+piece; if(idx=='+str(steps-1)+') begin out_reg<=0;out_reg[17:0]<=acc+piece;end'
    else:
        comb=f'o=idx/{c.k}; j=idx%{c.k};piece=$signed(saved[((o/2)*4+j)*8+:8])*$signed(saved[64+(j*2+(o%2))*8+:8]);'
        body=f'if(idx%{c.k}=={c.k-1}) begin out_reg[(idx/{c.k})*18+:18]<=acc+piece;acc<=0;end else acc<=acc+piece;'
    return f'''module candidate(input clk,input rst,input in_valid,output in_ready,input [511:0] in_data,
      output out_valid,input out_ready,output [255:0] out_data);
      reg busy,ov;reg [7:0] idx;reg [127:0] saved;reg signed [17:0] acc,piece;reg [255:0] out_reg;integer o,j;
      assign in_ready=!rst && !busy && !ov;assign out_valid=!rst && ov;assign out_data=out_reg;
      always @* begin {comb} end
      always @(posedge clk) begin
       if(rst) begin busy<=0;ov<=0;idx<=0;saved<=0;acc<=0;out_reg<=0;end
       else begin
        if(ov && out_ready) ov<=0;
        if(in_valid && in_ready) begin busy<=1;idx<=0;saved<=in_data[127:0];acc<=0;out_reg<=0;end
        else if(busy) begin {body} idx<=idx+1;if(idx=={steps-1}) begin busy<=0;ov<=1;end end
       end
      end
    endmodule'''

def fifo(c,depth=2):
    return f'''module candidate(input clk,input rst,input in_valid,output in_ready,input [511:0] in_data,
    output out_valid,input out_ready,output [255:0] out_data);
    reg [{c.width-1}:0] data[0:{depth-1}];reg [3:0] rd,wr,count;integer i;
    wire push=in_valid && in_ready;wire pop=out_valid && out_ready;
    assign in_ready=!rst && count<{depth};assign out_valid=!rst && count>0;
    assign out_data={{{{{256-c.width}{{1'b0}}}},data[rd]}};
    always @(posedge clk) begin
     if(rst) begin rd<=0;wr<=0;count<=0;for(i=0;i<{depth};i=i+1)data[i]<=0;end
     else begin
      case({{push,pop}}) 2'b10:count<=count+1;2'b01:count<=count-1;endcase
      if(push) begin data[wr]<=in_data[{c.width-1}:0];wr<=(wr=={depth-1})?0:wr+1;end
      if(pop) rd<=(rd=={depth-1})?0:rd+1;
     end
    end endmodule'''

def temporal(c):
    n=c.name;decl='';reset='';accept='';comb='';tick=''
    if n in ('scratchpad','gather','accelerator'):
        decl+=f'reg [31:0] mem[0:{c.depth-1}];integer z;'
        reset+=f'for(z=0;z<{c.depth};z=z+1) mem[z]<=0;'
    if n=='scratchpad':
        decl+='reg [191:0] saved;reg [1:0] ptr[0:3];reg [2:0] bank;integer off,sel,a,win;'
        reset+='saved<=0;bank<=0;for(z=0;z<4;z=z+1)ptr[z]<=0;'
        accept='saved<=in_data[191:0];bank<=0;busy<=1;'
        comb=f'''win=-1;a=0;for(off=0;off<4;off=off+1) begin sel=(ptr[bank]+off)%4;
          if(win<0 && saved[sel*48] && (saved[sel*48+2+:8]%{c.depth})%4==bank)win=sel;end
          if(win>=0)a=saved[win*48+2+:8]%{c.depth};'''
        tick='''if(win>=0)begin ptr[bank]<=(win+1)%4;result[win]<=1;
          result[8+win*32+:32]<=saved[win*48+1]?saved[win*48+10+:32]:mem[a];
          if(saved[win*48+1])mem[a]<=saved[win*48+10+:32];end
          if(bank==3)begin busy<=0;ov<=1;end else bank<=bank+1;'''
    elif n=='router':
        decl+='reg [164:0] saved;reg [2:0] ptr[0:4];reg [2:0] port;integer off,sel,win,z;'
        reset+='saved<=0;port<=0;for(z=0;z<5;z=z+1)ptr[z]<=0;'
        accept='saved<=in_data[164:0];port<=0;busy<=1;'
        comb='''win=-1;for(off=0;off<5;off=off+1)begin sel=ptr[port]+off;if(sel>=5)sel=sel-5;
        if(win<0 && saved[160+port] && saved[sel*32] && saved[sel*32+1+:3]==port)win=sel;end'''
        tick='''if(win>=0)begin ptr[port]<=(win==4)?0:win+1;result[win]<=1;result[8+port]<=1;result[16+port*16+:16]<=saved[win*32+4+:16];end
        if(port==4)begin busy<=0;ov<=1;end else port<=port+1;'''
    elif n=='scoreboard':
        decl+='reg [95:0] saved;reg [3:0] timers[0:15];reg [1:0] ptr,off;integer sel,z;reg eligible;'
        reset+='saved<=0;ptr<=0;off<=0;for(z=0;z<16;z=z+1)timers[z]<=0;'
        accept='saved<=in_data[95:0];off<=0;busy<=1;for(z=0;z<16;z=z+1) if(timers[z]>0)timers[z]<=timers[z]-1;'
        comb='sel=(ptr+off)%4;eligible=saved[sel*24] && timers[saved[sel*24+1+:4]]==0 && timers[saved[sel*24+5+:4]]==0;'
        tick='''if(eligible || off==3)begin
         for(z=0;z<16;z=z+1)result[8+z]<=timers[z]!=0;
         if(eligible)begin result[sel]<=1;result[8+saved[sel*24+5+:4]]<=1;timers[saved[sel*24+5+:4]]<=1+{1'b0,saved[sel*24+9+:3]};ptr<=(sel+1)%4;end
         busy<=0;ov<=1;end else off<=off+1;'''
    elif n=='gather':
        decl+='reg [31:0] addresses;reg [3:0] mask;reg [2:0] idx,cnt;'
        reset+='addresses<=0;mask<=0;idx<=0;cnt<=0;'
        accept=f'''if(in_data[0])begin mem[in_data[8+:8]%{c.depth}]<=in_data[16+:32];ov<=1;end
        else begin addresses<=in_data[16+:32];mask<=in_data[4+:4];idx<=0;cnt<=0;busy<=1;end'''
        comb=''
        tick=f'''if(mask[idx])begin result[8+cnt*32+:32]<=mem[addresses[idx*8+:8]%{c.depth}];cnt<=cnt+1;end
        if(idx==3)begin result[2:0]<=cnt+mask[idx];busy<=0;ov<=1;end else idx<=idx+1;'''
    elif n=='accelerator':
        decl+='reg [7:0] a,b,idx;reg signed [17:0] acc,piece;integer ia,ib;'
        reset+='a<=0;b<=0;idx<=0;acc<=0;'
        comb=f'''ia=in_data[8+:8]%{c.depth};ib=in_data[16+:8]%{c.depth};piece=$signed(mem[(a+idx)%{c.depth}][7:0])*$signed(mem[(b+idx)%{c.depth}][7:0]);'''
        accept='''case(in_data[1:0])
         0:begin mem[ia]<=in_data[16+:32];ov<=1;end
         1:begin mem[ia]<=mem[ib];result[31:0]<=mem[ib];ov<=1;end
         2:begin a<=ia;b<=ib;idx<=0;acc<=0;busy<=1;end
         3:begin result[31:0]<=mem[ia];ov<=1;end
         endcase'''
        tick=f'''acc<=acc+piece;if(idx=={c.k-1})begin result[17:0]<=acc+piece;busy<=0;ov<=1;end else idx<=idx+1;'''
    else:raise ValueError(n)
    return f'''module candidate(input clk,input rst,input in_valid,output in_ready,input [511:0] in_data,
    output out_valid,input out_ready,output [255:0] out_data);
    reg busy,ov;reg [255:0] result;{decl}
    assign in_ready=!rst && !busy && !ov;assign out_valid=!rst && ov;assign out_data=result;
    {'always @* begin '+comb+' end' if comb else ''}
    always @(posedge clk)begin
      if(rst)begin busy<=0;ov<=0;result<=0;{reset}
      end
      else begin
        if(ov && out_ready)ov<=0;
        if(in_valid && in_ready)begin result<=0;{accept}
        end
        else if(busy)begin {tick}
        end
      end
    end endmodule'''

def architecture(c,label):
    if label=='baseline':return design(c)
    if label=='global4' and c.name=='elastic':
        return design(c).replace('assign ready[g]=!valid[g] || ready[g+1];','assign ready[g]=!valid[S-1] || out_ready;')
    if label=='lazy_cache' and c.name=='cache':
        return design(c).replace('for(z=0;z<DEPTH;z=z+1) begin mem[z]<=0; tag[z]<=0; end','')
    pc=Parameters(c.name)
    if label=='serial1' and c.name in ('dot','tensor'):src=serial(pc)
    elif label=='time_mux' and c.name in ('scratchpad','gather'):src=temporal(pc)
    elif label=='fifo4' and c.name=='elastic':src=fifo(pc,4)
    else:raise ValueError('unsupported architecture')
    return src.replace('module candidate(',f'module candidate #(parameter WIDTH={c.width}, DEPTH={c.depth}, K={c.k})(')

CATALOG={'elastic':['baseline','global4','fifo4'],'dot':['baseline','serial1'],
         'scratchpad':['baseline','time_mux'],'tensor':['baseline','serial1'],
         'cache':['baseline','lazy_cache'],'gather':['baseline','time_mux']}
