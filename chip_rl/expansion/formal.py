"""Bounded symbolic permutation safety at four 8-bit lanes, separate from simulation."""
import json,tempfile,shutil
from pathlib import Path
from ..evaluate import sanitize,tool,run,Rejected

def check_permute(source,artifacts=None):
 r={'status':'unproven','kind':'bounded_symbolic_permutation_transactions','width':8,'lanes':4,'bound':8}
 with tempfile.TemporaryDirectory(prefix='permute-bmc-') as td:
  d=Path(td)
  try:
   sanitize(source);(d/'candidate.sv').write_text(source)
   (d/'formal.sv').write_text('''module formal_top(input clk,input in_valid,input out_ready,input [511:0] in_data);
    reg rst=1;always @(posedge clk)rst<=0;wire in_ready,out_valid;wire [255:0] out_data;
    candidate #(.WIDTH(8),.DEPTH(8),.K(2)) dut(.*);
    reg [255:0] expected;integer j;always @*begin expected=0;
     for(j=0;j<4;j=j+1)if(in_data[152+j] && in_data[128+3*j+:3]<4)
      expected[16*j+:8]=(in_data >> (16*in_data[128+3*j+:3]));end
    reg [255:0] queue[0:15];reg [4:0] used=0;integer i;wire push=in_valid && in_ready;wire pop=out_valid && out_ready;
    reg stalled=0;reg [255:0] held=0;
    always @(posedge clk)begin
     if(rst)begin used<=0;stalled<=0;end else begin
      assert(used<=16);if(out_valid)begin assert(used>0);assert(out_data==queue[0]);end
      if(stalled)begin assert(out_valid);assert(out_data==held);end
      stalled<=out_valid && !out_ready;held<=out_data;
      if(pop)for(i=0;i<15;i=i+1)queue[i]<=queue[i+1];
      if(push)queue[used-pop]<=expected;used<=used+push-pop;
     end end endmodule''')
   (d/'formal.ys').write_text('read_verilog -formal -sv candidate.sv formal.sv; prep -top formal_top -flatten; memory_map; opt; async2sync; chformal -lower; sat -seq 8 -set-init-zero -prove-asserts -verify -timeout 45')
   log=run([tool('yosys'),'-s','formal.ys'],d,'formal',60)
   if 'SUCCESS!' not in log:raise Rejected('missing proof success')
   r['status']='bounded_pass'
  except (Rejected,OSError) as e:r['error']=str(e)
  (d/'result.json').write_text(json.dumps(r,indent=2)+'\n')
  if artifacts:shutil.copytree(d,artifacts)
 return r
