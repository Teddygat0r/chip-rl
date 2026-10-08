"""Bounded symbolic single-transaction scan, including bounded completion."""
import json,tempfile,shutil
from pathlib import Path
from ..evaluate import sanitize,tool,run,Rejected

def check_scan(source,artifacts=None):
 r={'status':'unproven','kind':'single_symbolic_scan_transaction','width':8,'lanes':4,'bound':9,'consumer':'always_ready','acceptance':'first_post_reset_clock','completion':'by_clock_7'}
 with tempfile.TemporaryDirectory(prefix='scan-bmc-') as td:
  d=Path(td)
  try:
   sanitize(source);(d/'candidate.sv').write_text(source)
   (d/'formal.sv').write_text('''module formal_top(input clk,input [511:0] in_data);
    reg [3:0] cycle=0;always @(posedge clk)cycle<=cycle+1;
    wire rst=cycle==0;wire in_valid=cycle==1;wire out_ready=1;wire in_ready,out_valid;wire [255:0] out_data;
    candidate #(.WIDTH(8),.DEPTH(8),.K(2)) dut(.*);
    reg [255:0] expected,saved;integer i,j,start;reg [31:0] total;reg [1:0] received=0;
    always @*begin expected=0;start=0;total=0;
     for(i=0;i<4;i=i+1)if(in_data[128+i])begin
      start=0;total=in_data[160+:32];
      for(j=0;j<=i;j=j+1)if(in_data[128+j] && in_data[136+j])begin start=j;total=0;end
      for(j=0;j<=i;j=j+1)if(j>=start && in_data[128+j] && (!in_data[144] || j<i))total=total+{{24{in_data[16*j+7]}},in_data[16*j+:8]};
      expected[32*i+:32]=total;
     end
    end
    always @(posedge clk)begin
     if(rst)begin received<=0;saved<=0;end else begin
      if(cycle==1)begin assert(in_ready);saved<=expected;end
      if(out_valid)begin assert(cycle>1);assert(received==0);assert(out_data==saved);received<=received+1;end
      if(cycle==7)assert(received==1);
     end
    end endmodule''')
   (d/'formal.ys').write_text('read_verilog -formal -sv candidate.sv formal.sv; prep -top formal_top -flatten; memory_map; opt; async2sync; chformal -lower; sat -seq 9 -set-init-zero -prove-asserts -verify -timeout 45')
   log=run([tool('yosys'),'-s','formal.ys'],d,'formal',60)
   if 'SUCCESS!' not in log:raise Rejected('missing proof success')
   r['status']='bounded_pass'
  except (Rejected,OSError) as e:r['error']=str(e)
  (d/'result.json').write_text(json.dumps(r,indent=2)+'\n')
  if artifacts:shutil.copytree(d,artifacts)
 return r
