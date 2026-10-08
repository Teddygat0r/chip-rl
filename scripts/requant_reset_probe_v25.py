from pathlib import Path
import json,re,argparse
from chip_rl.requant.rtl import design
from chip_rl.requant.synthesis import Synthesis
from chip_rl.evaluate import run,tool,TOOLS,Rejected
from chip_rl.audit import ACTIVE
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();root=a.root;root.mkdir();q=Synthesis(a.cache);summary={}
tb='''module tb;
reg clk=0,rst=1,in_valid=0,out_ready=0;reg [191:0] in_data=0;reg [3:0] in_mask=0;wire in_ready,out_valid;wire [31:0] out_data;
candidate #(.N(4)) dut(.*);integer accepted=0,t;
task edge_clock;begin #4;clk=1;#4;clk=0;end endtask
initial begin
edge_clock;rst=0;in_mask=15;in_valid=1;in_data[31:0]=3;in_data[143:128]=1;
for(t=0;t<8;t=t+1)begin #1;if(in_ready===1)accepted=accepted+1;edge_clock;end
if(accepted!=2 || out_valid!==1)$fatal(1,"two occupied slots required by selected architecture");
rst=1;in_valid=0;#1;if(in_ready!==0 || out_valid!==0)$fatal(1,"reset ports");edge_clock;rst=0;out_ready=1;
for(t=0;t<8;t=t+1)begin #1;if(out_valid!==0)$fatal(1,"response survived two-pending cancellation");edge_clock;end
$display("TWO_PENDING_CANCEL_PASS");$finish;end endmodule'''
source=design('elastic_pipeline');bad=source.replace('if(rst)begin pv<=0;ov<=0;','if(rst)begin pv<=pv && ov && in_mask[0];ov<=0;');assert source!=bad
for label,src,want in [('valid',source,True),('bad',bad,False)]:
 folder=root/label;folder.mkdir();(folder/'candidate.sv').write_text(src);token=ACTIVE.set(folder)
 try:
  net,metrics=q.compile(4,src);(folder/'netlist.v').write_bytes((net/'netlist.v').read_bytes());summary[label]={'metrics':metrics,'stages':{}}
  for stage,file in [('rtl','candidate.sv'),('mapped','netlist.v')]:
   bench=tb if stage=='rtl' else tb.replace(' #(.N(4))','');(folder/(stage+'-tb.sv')).write_text(bench)
   cmd=[tool('iverilog')]
   if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
   run(cmd+['-g2012','-s','tb','-o',stage+'.vvp',file,stage+'-tb.sv'],folder,'requant-reset-'+stage+'-compile',45)
   try:log=run([tool('vvp'),stage+'.vvp'],folder,'requant-reset-'+stage+'-simulation',45);passed='TWO_PENDING_CANCEL_PASS' in log;reason=log
   except Rejected as e:passed=False;reason=str(e)
   assert passed==want
   if not want:assert 'response survived two-pending cancellation' in reason
   summary[label]['stages'][stage]={'passed':passed,'reason':reason}
 finally:ACTIVE.reset(token)
(root/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
