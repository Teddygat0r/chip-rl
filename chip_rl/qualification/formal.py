"""Separate bounded ECC checks; no unbounded equivalence claim."""
import json,tempfile,shutil
from pathlib import Path
from ..evaluate import sanitize,tool,run,Rejected
from .oracles import codeword

def check_ecc_capacity_two(source,artifacts=None):
 r={'status':'unproven','kind':'bounded_symbolic_ecc_zero_one_two_errors','width':8,'bound':8,'maximum_outstanding_asserted':2,'liveness':'not_proved'}
 with tempfile.TemporaryDirectory(prefix='ecc-bmc-small-monitor-') as td:
  d=Path(td)
  try:
   sanitize(source);(d/'candidate.sv').write_text(source)
   # Independent parity-basis codewords from the Python encoder; no RTL syndrome oracle.
   terms=' ^ '.join(f"({{13{{payload[{i}]}}}} & 13'h{codeword(8,1<<i)[0]:x})" for i in range(8))
   (d/'formal.sv').write_text('''module formal_top(input clk,input in_valid,input out_ready,input decode,input [7:0] payload,input [3:0] e1,e2,input [478:0] reserved);
    reg rst=1;always @(posedge clk)rst<=0;wire in_ready,out_valid;wire [255:0] out_data;
    wire [12:0] canonical=TERMS;
    wire [12:0] errors=(13'b1<<e1)^(13'b1<<e2);
    wire [1:0] count=(e1==e2)?0:((e1<13)+(e2<13));
    wire [511:0] in_data={reserved,decode,19'b0,(decode?(canonical^errors):{5'b0,payload})};
    candidate #(.WIDTH(8),.DEPTH(8),.K(4)) dut(.*);
    reg [255:0] expected;always @*begin
     assume(e1<=13);assume(e2<=13);expected=0;
     if(decode && count==2)expected[49]=1;
     else begin expected[12:0]=canonical;expected[32+:8]=payload;expected[48]=decode && count==1;end
    end
    reg [255:0] queue[0:1];reg [1:0] used=0;integer i;wire push=in_valid && in_ready;wire pop=out_valid && out_ready;
    reg stalled=0;reg [255:0] held=0;
    always @(posedge clk)begin
     if(rst)begin used<=0;stalled<=0;end else begin
      assert(used<=2);if(out_valid)begin assert(used>0);assert(out_data==queue[0]);end
      if(stalled)begin assert(out_valid);assert(out_data==held);end
      stalled<=out_valid && !out_ready;held<=out_data;
      if(pop)for(i=0;i<1;i=i+1)queue[i]<=queue[i+1];
      if(push)queue[used-pop]<=expected;used<=used+push-pop;
     end end endmodule'''.replace('TERMS',terms))
   (d/'formal.ys').write_text('read_verilog -formal -sv candidate.sv formal.sv; prep -top formal_top -flatten; memory_map; opt; async2sync; chformal -lower; sat -seq 8 -set-init-zero -set-assumes -prove-asserts -verify -timeout 45')
   log=run([tool('yosys'),'-s','formal.ys'],d,'formal',60)
   if 'SUCCESS!' not in log:raise Rejected('missing proof success')
   r['status']='bounded_pass'
  except (Rejected,OSError) as e:r['error']=str(e)
  (d/'result.json').write_text(json.dumps(r,indent=2)+'\n')
  if artifacts:shutil.copytree(d,artifacts)
 return r
