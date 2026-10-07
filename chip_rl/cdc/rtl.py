from .spec import Choice

def design(choice=Choice(),formal=False):
 extra=',input clk,input wtick,input rtick,output [$clog2(DEPTH):0] formal_wgray,formal_rgray' if formal else ''
 s='''module candidate #(parameter WIDTH=16,DEPTH=4)(input wclk,rclk,wrst,rrst,input w_valid,output w_ready,input [WIDTH-1:0] w_data,output r_valid,input r_ready,output [WIDTH-1:0] r_dataEXTRA);
 localparam A=$clog2(DEPTH);reg [WIDTH-1:0] mem[0:DEPTH-1];
 reg [A:0] wgray,rgray;
 function [A:0] decode;input [A:0] gray;integer i;begin decode=0;for(i=A;i>=0;i=i-1)decode[i]=^(gray>>i);end endfunction
'''.replace('EXTRA',extra)
 if choice.architecture=='binary_gray':s+='reg [A:0] wbin,rbin;\n'
 else:s+='wire [A:0] wbin=decode(wgray),rbin=decode(rgray);\n'
 for side,clk,rst,remote in [('w','wclk','wrst','rgray'),('r','rclk','rrst','wgray')]:
  for i in range(1,choice.sync_stages+1):s+=f'reg [A:0] {side}_seen{i};\n'
  body=''.join(f'{side}_seen{i}<=0;' for i in range(1,choice.sync_stages+1))
  updates=''.join(f'{side}_seen{i}<={remote if i==1 else side+"_seen"+str(i-1)};' for i in range(1,choice.sync_stages+1))
  s+=block(side,f'if({rst})begin {body}end else begin {updates}end',formal)
 s+=f'''wire [A:0] wremote=w_seen{choice.sync_stages},rremote=r_seen{choice.sync_stages};
 wire [A:0] full_mask=(1<<A)|(1<<(A-1));
 wire full=(wgray==(wremote^full_mask));wire empty=(rgray==rremote);
 assign w_ready=!wrst && !full;assign r_valid=!rrst && !empty;
 assign r_data=mem[rbin[A-1:0]];
 wire wtake=w_valid && w_ready;wire rtake=r_valid && r_ready;
 wire [A:0] wn=wbin+1,rn=rbin+1;
'''
 for side,rst in [('w','wrst'),('r','rrst')]:
  reset=f'{side}gray<=0;'+(f'{side}bin<=0;' if choice.architecture=='binary_gray' else '')
  update=f'{side}gray<=({side}n>>1)^{side}n;'+(f'{side}bin<={side}n;' if choice.architecture=='binary_gray' else '')
  s+=block(side,f'if({rst})begin {reset}end else if({side}take)begin {update}end',formal)
 s+=block('w','if(wtake)mem[wbin[A-1:0]]<=w_data;',formal)
 return s+('assign formal_wgray=wgray;assign formal_rgray=rgray;\n' if formal else '')+'endmodule\n'

def block(side,body,formal):
 return f'always @(posedge {"clk" if formal else side+"clk"})begin '+(f'if({side}tick)begin ' if formal else '')+body+' '+('end ' if formal else '')+'end\n'
MUTANTS=('zero','wrong_clock','single_sync','binary_crossing','full_mask','empty_flag','no_wreset','no_rreset','overwrite_full','read_advance','reverse_data','early_wrap')
def bad_source(choice,fault):
 s=design(choice)
 if fault=='zero':s=s.replace('assign r_data=mem[rbin[A-1:0]];','assign r_data=0;')
 elif fault=='wrong_clock':s=s.replace('@(posedge rclk)','@(posedge wclk)')
 elif fault=='single_sync':s=s.replace(f'wremote=w_seen{choice.sync_stages},rremote=r_seen{choice.sync_stages}','wremote=w_seen1,rremote=r_seen1')
 elif fault=='binary_crossing':s=s.replace('wgray<=(wn>>1)^wn;','wgray<=wn;').replace('rgray<=(rn>>1)^rn;','rgray<=rn;')
 elif fault=='full_mask':s=s.replace('(1<<A)|(1<<(A-1))','(1<<A)')
 elif fault=='empty_flag':s=s.replace('wire empty=(rgray==rremote);','wire empty=0;')
 elif fault=='no_wreset':s=s.replace('if(wrst)','if(1\'b0)')
 elif fault=='no_rreset':s=s.replace('if(rrst)','if(1\'b0)')
 elif fault=='overwrite_full':s=s.replace('assign w_ready=!wrst && !full;','assign w_ready=!wrst;')
 elif fault=='read_advance':s=s.replace('wire rtake=r_valid && r_ready;','wire rtake=r_valid;')
 elif fault=='reverse_data':s=s.replace('assign r_data=mem[rbin[A-1:0]];','assign r_data=~mem[rbin[A-1:0]];')
 elif fault=='early_wrap':s=s.replace('wbin+1,rn=rbin+1','(wbin+1)&(DEPTH-1),rn=(rbin+1)&(DEPTH-1)')
 else:raise ValueError('fault')
 return s
