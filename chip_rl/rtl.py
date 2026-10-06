"""Original synthesizable reference designs. No third-party RTL is included."""
from .tasks import Config

def design(c:Config, stages=4, mutant=None):
    if stages not in (1,2,4,6): raise ValueError('stages must be 1,2,4,6')
    decl=''; calc=''; reset=''; update=''; n=c.name
    if n=='elastic': calc=f'y[{c.width-1}:0]=in_data[{c.width-1}:0];'
    elif n=='dot':
        decl='integer j; reg signed [17:0] acc;'
        calc=f'acc=0; for(j=0;j<{c.k};j=j+1) acc=acc+$signed(in_data[j*8+:8])*$signed(in_data[32+j*8+:8]); y[17:0]=acc;'
    elif n=='tensor':
        decl='integer r,s,j; reg signed [17:0] acc;'
        calc=f'for(r=0;r<2;r=r+1) for(s=0;s<2;s=s+1) begin acc=0; for(j=0;j<{c.k};j=j+1) acc=acc+$signed(in_data[(r*4+j)*8+:8])*$signed(in_data[64+(j*2+s)*8+:8]); y[(r*2+s)*18+:18]=acc; end'
    elif n=='scratchpad':
        decl=f'reg [31:0] mem[0:{c.depth-1}]; reg [1:0] ptr[0:3]; integer b,o,i,a,z; integer win[0:3];'
        reset=f'for(z=0;z<{c.depth};z=z+1) mem[z]<=0; for(z=0;z<4;z=z+1) ptr[z]<=0;'
        calc=f'''for(b=0;b<4;b=b+1) begin
          win[b]=-1;
          for(o=0;o<4;o=o+1) begin
            i=(ptr[b]+o)%4; a=in_data[i*48+2+:8]%{c.depth};
            if(win[b]<0 && in_data[i*48] && a%4==b) win[b]=i;
          end
          if(win[b]>=0) begin
            i=win[b]; a=in_data[i*48+2+:8]%{c.depth}; y[i]=1;
            y[8+i*32+:32]=in_data[i*48+1] ? in_data[i*48+10+:32] : mem[a];
          end
        end'''
        update=f'''for(z=0;z<4;z=z+1) if(win[z]>=0) begin
          ptr[z]<=(win[z]+1)%4;
          if(in_data[win[z]*48+1]) mem[in_data[win[z]*48+2+:8]%{c.depth}]<=in_data[win[z]*48+10+:32];
        end'''
    elif n=='router':
        decl='reg [2:0] ptr[0:4]; integer p,o,i,z; integer win[0:4];'
        reset='for(z=0;z<5;z=z+1) ptr[z]<=0;'
        calc='''for(p=0;p<5;p=p+1) begin
          win[p]=-1;
          for(o=0;o<5;o=o+1) begin
            i=ptr[p]+o; if(i>=5) i=i-5;
            if(win[p]<0 && in_data[160+p] && in_data[i*32] && in_data[i*32+1+:3]==p) win[p]=i;
          end
          if(win[p]>=0) begin y[win[p]]=1; y[8+p]=1; y[16+p*16+:16]=in_data[win[p]*32+4+:16]; end
        end'''
        update='for(z=0;z<5;z=z+1) if(win[z]>=0) ptr[z]<=(win[z]==4)?0:win[z]+1;'
    elif n=='scoreboard':
        decl='reg [3:0] busy[0:15]; reg [1:0] ptr; reg [3:0] nb[0:15]; integer j,o,i,win,z;'
        reset='for(z=0;z<16;z=z+1) busy[z]<=0; ptr<=0;'
        calc='''for(j=0;j<16;j=j+1) nb[j]=(busy[j]>0)?busy[j]-1:0;
        win=-1;
        for(o=0;o<4;o=o+1) begin
          i=(ptr+o)%4;
          if(win<0 && in_data[i*24] && nb[in_data[i*24+1+:4]]==0 && nb[in_data[i*24+5+:4]]==0) win=i;
        end
        if(win>=0) begin nb[in_data[win*24+5+:4]]=1+{1'b0,in_data[win*24+9+:3]}; y[win]=1; end
        for(j=0;j<16;j=j+1) y[8+j]=(nb[j]!=0);'''
        update='for(z=0;z<16;z=z+1) busy[z]<=nb[z]; if(win>=0) ptr<=(win+1)%4;'
    elif n=='dma':
        decl='''reg active,na; reg [15:0] base,stride,nb,ns;
        reg [3:0] row,col,rows,cols,nr,nc,nrs,ncs; reg [15:0] addr;'''
        reset='active<=0; base<=0; stride<=0; row<=0; col<=0; rows<=0; cols<=0;'
        calc='''na=active; nb=base; ns=stride; nr=row; nc=col; nrs=rows; ncs=cols; addr=0;
        if(in_data[0] && !active) begin
          na=1; nb=in_data[8+:16]; ns=in_data[32+:16]; nrs=1+{1'b0,in_data[27+:3]}; ncs=1+{1'b0,in_data[24+:3]}; nr=0; nc=0;
        end
        if(na) begin
          addr=nb+nr*ns+4*nc; y[0]=1; y[8+:16]=addr; y[24+:8]=8'h0f << addr[1:0]; y[32]=(nr==nrs-1 && nc==ncs-1);
          if(in_data[1]) begin nc=nc+1; if(nc==ncs) begin nc=0; nr=nr+1; end if(nr==nrs) na=0; end
        end'''
        update='active<=na; base<=nb; stride<=ns; row<=nr; col<=nc; rows<=nrs; cols<=ncs;'
    elif n=='accelerator':
        decl=f'reg [31:0] mem[0:{c.depth-1}]; integer a,b,j,z; reg signed [17:0] acc;'
        reset=f'for(z=0;z<{c.depth};z=z+1) mem[z]<=0;'
        calc=f'''a=in_data[8+:8]%{c.depth}; b=in_data[16+:8]%{c.depth}; acc=0;
        case(in_data[1:0])
          1:y[31:0]=mem[b];
          2:begin for(j=0;j<{c.k};j=j+1) acc=acc+$signed(mem[(a+j)%{c.depth}][7:0])*$signed(mem[(b+j)%{c.depth}][7:0]); y[17:0]=acc; end
          3:y[31:0]=mem[a];
        endcase'''
        update='if(in_data[1:0]==0) mem[a]<=in_data[16+:32]; if(in_data[1:0]==1) mem[a]<=mem[b];'
    elif n=='cache':
        decl=f'''reg [31:0] mem[0:{c.depth-1}]; reg [15:0] tag[0:{c.depth-1}]; reg [{c.depth-1}:0] cvalid;
        reg pending; reg [15:0] pa; integer ix,pi,z; reg [15:0] addr,tg;'''
        reset=f'pending<=0; pa<=0; cvalid<=0; for(z=0;z<{c.depth};z=z+1) begin mem[z]<=0; tag[z]<=0; end'
        calc=f'''addr={{in_data[23:10],2'b00}}; ix=(addr/4)%{c.depth}; pi=(pa/4)%{c.depth}; tg=addr/{4*c.depth};
        if(in_data[1:0]==2) begin if(pending) begin y[0]=1; y[8+:32]=in_data[24+:32]; end end
        else if(pending) y[2]=1;
        else if(in_data[1:0]==1) begin y[0]=1; y[3]=1; y[40+:16]=addr; y[8+:32]=in_data[24+:32]; end
        else if(cvalid[ix] && tag[ix]==tg) begin y[0]=1; y[1]=1; y[8+:32]=mem[ix]; end
        else begin y[2]=1; y[40+:16]=addr; end'''
        update=f'''if(in_data[1:0]==2) begin
          if(pending) begin mem[pi]<=in_data[24+:32]; tag[pi]<=pa/{4*c.depth}; cvalid[pi]<=1; pending<=0; end
        end else if(!pending) begin
          if(in_data[1:0]==1) begin if(cvalid[ix] && tag[ix]==tg) mem[ix]<=in_data[24+:32]; end
          else if(!(cvalid[ix] && tag[ix]==tg)) begin pending<=1; pa<=addr; end
        end'''
    elif n=='gather':
        decl=f'reg [31:0] mem[0:{c.depth-1}]; integer i,cnt,z;'
        reset=f'for(z=0;z<{c.depth};z=z+1) mem[z]<=0;'
        calc=f'''cnt=0; if(!in_data[0]) begin for(i=0;i<4;i=i+1) if(in_data[4+i]) begin
          y[8+cnt*32+:32]=mem[in_data[16+i*8+:8]%{c.depth}]; cnt=cnt+1; end y[2:0]=cnt; end'''
        update=f'if(in_data[0]) mem[in_data[8+:8]%{c.depth}]<=in_data[16+:32];'
    source=f'''module candidate(input clk,input rst,input in_valid,output in_ready,
      input [511:0] in_data,output out_valid,input out_ready,output [255:0] out_data);
    localparam S={stages};
    reg [S-1:0] valid; reg [255:0] data[0:S-1]; wire [S:0] ready;
    assign ready[S]=out_ready;
    genvar g;
    generate for(g=0;g<S;g=g+1) begin: elastic_stage
      assign ready[g]=!valid[g] || ready[g+1];
    end endgenerate
    assign in_ready=ready[0] && !rst;
    assign out_valid=valid[S-1] && !rst;
    assign out_data=data[S-1];
    wire fire=in_valid && in_ready;
    reg [255:0] y; integer st;
    {decl}
    always @* begin
      y=0;
      {calc}
    end
    always @(posedge clk) begin
      if(rst) begin
        valid<=0;
        for(st=0;st<S;st=st+1) data[st]<=0;
        {reset}
      end else begin
        for(st=S-1;st>0;st=st-1) if(ready[st]) begin
          valid[st]<=valid[st-1]; if(valid[st-1]) data[st]<=data[st-1];
        end
        if(ready[0]) begin valid[0]<=in_valid; if(in_valid) data[0]<=y; end
        if(fire) begin {update} end
      end
    end
    endmodule
    '''
    if mutant=='corrupt': source=source.replace('data[0]<=y;',"data[0]<=y ^ 256'h1;")
    if mutant=='drop': source=source.replace('valid[0]<=in_valid;',"valid[0]<=1'b0;")
    if mutant=='unstable': source=source.replace('assign out_data=data[S-1];','assign out_data=data[S-1] ^ in_data[255:0];')
    if mutant=='unfair':
        if n not in ('scratchpad','router','scoreboard'): raise ValueError('no arbiter')
        source=source.replace('ptr[z]<=(win[z]+1)%4;', 'ptr[z]<=0;').replace('ptr[z]<=(win[z]==4)?0:win[z]+1;', 'ptr[z]<=0;').replace('ptr<=(win+1)%4;', 'ptr<=0;')
    return source
