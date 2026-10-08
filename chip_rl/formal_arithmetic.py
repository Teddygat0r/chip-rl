"""Bounded symbolic transaction safety for a one-term signed dot product.
This is NOT an unbounded proof or validation of K=4 arithmetic/timing.
"""
import tempfile,json,shutil
from pathlib import Path
from .evaluate import sanitize,run,tool,Rejected

def check_dot_k1(source,artifacts=None,bound=8):
 result={'status':'unproven','kind':'bounded_symbolic_signed_dot_transactions','k':1,'bound':bound}
 with tempfile.TemporaryDirectory(prefix='dot-bmc-') as td:
  d=Path(td)
  try:
   sanitize(source);(d/'candidate.sv').write_text(source)
   (d/'formal.sv').write_text('''module formal_top(input clk,input in_valid,input out_ready,input [511:0] in_data);
    reg rst=1;always @(posedge clk)rst<=0;wire in_ready,out_valid;wire [255:0] out_data;
    candidate #(.K(1),.DEPTH(16),.WIDTH(16)) dut(.*);
    wire push=in_valid && in_ready;wire pop=out_valid && out_ready;
    wire signed [17:0] golden=$signed(in_data[7:0])*$signed(in_data[39:32]);
    reg [17:0] queue[0:7];reg [3:0] used=0;integer i;reg stalled=0;reg [255:0] held=0;
    always @(posedge clk)begin
     if(rst)begin used<=0;stalled<=0;end
     else begin
      assert(used<=8);
      if(out_valid)begin assert(used>0);assert(out_data=={238'b0,queue[0]});end
      if(stalled)begin assert(out_valid);assert(out_data==held);end
      stalled<=out_valid && !out_ready;held<=out_data;
      if(pop)for(i=0;i<7;i=i+1)queue[i]<=queue[i+1];
      if(push)queue[used-pop]<=golden;
      used<=used+push-pop;
     end
    end endmodule''')
   (d/'formal.ys').write_text(f'read_verilog -formal -sv candidate.sv formal.sv; prep -top formal_top -flatten; memory_map; opt; async2sync; chformal -lower; sat -seq {bound} -set-init-zero -prove-asserts -verify -timeout 45')
   output=run([tool('yosys'),'-s','formal.ys'],d,'formal',60)
   if 'SUCCESS!' not in output:raise Rejected('proof success marker missing')
   result['status']='bounded_pass'
  except (Rejected,OSError) as e:result['error']=str(e)
  (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  if artifacts:shutil.copytree(d,artifacts)
 return result
