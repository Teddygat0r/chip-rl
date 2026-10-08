"""Small bounded SAT checks. Separate from reward; no unbounded or physical claim."""
from pathlib import Path
import json,time
from ..evaluate import sanitize,tool,run,Rejected,digest

def arithmetic_harness(k,progress=False,input_bits=8):
 return r'''module formal_top(input clk,input launch,input ready,input reset_in,input [1023:0] in_data);
 reg started=0;always @(posedge clk)started<=1;
 wire rst=!started || reset_in;wire in_valid=launch && !rst;wire out_ready=READY;
 wire in_ready,out_valid;wire [383:0] out_data;
 candidate #(.M(1),.N(1),.K(K_VALUE)) dut(.*);
 DOMAIN
 wire push=in_valid && in_ready;wire pop=out_valid && out_ready;
 wire signed [23:0] sums[0:K_VALUE];assign sums[0]=0;
 genvar g;generate for(g=0;g<K_VALUE;g=g+1)begin:G
 wire signed [7:0] a=in_data[g*8+:8],b=in_data[512+g*32+:8];
 wire signed [15:0] product=a*b;assign sums[g+1]=sums[g]+product;
 end endgenerate
 reg [23:0] queue[0:7];reg [3:0] used=0;reg stalled=0;reg [383:0] held;
 reg [4:0] age[0:7];integer i;reg waiting=0;reg [1023:0] offered;
 always @(posedge clk)begin if(rst)waiting<=0;else begin if(waiting)begin assume(launch);assume(in_data==offered);end waiting<=in_valid && !in_ready;offered<=in_data;end end
 always @(posedge clk)begin
 if(rst)begin used<=0;stalled<=0;for(i=0;i<8;i=i+1)age[i]<=0;assert(!in_ready && !out_valid);end
 else begin
 assert(used<=8);
 if(out_valid)begin assert(used>0);assert(out_data=={360'b0,queue[0]});end
 if(stalled)begin assert(out_valid);assert(out_data==held);end
 stalled<=out_valid && !out_ready;held<=out_data;
 for(i=0;i<8;i=i+1)if(i<used)age[i]<=age[i]+1;
 PROGRESS
 if(pop)for(i=0;i<7;i=i+1)begin queue[i]<=queue[i+1];age[i]<=age[i+1]+1;end
 if(push)begin queue[used-pop]<=sums[K_VALUE];age[used-pop]<=0;end
 used<=used+push-pop;
 end end endmodule
'''.replace('K_VALUE',str(k)).replace('READY',"1'b1" if progress else 'ready').replace('DOMAIN','' if input_bits==8 else f'genvar d;generate for(d=0;d<{k};d=d+1)begin:D always @(posedge clk)if(in_valid)begin assume(in_data[8*d+{input_bits} +: {8-input_bits}]=={{{8-input_bits}{{in_data[8*d+{input_bits-1}]}}}});assume(in_data[512+32*d+{input_bits} +: {8-input_bits}]=={{{8-input_bits}{{in_data[512+32*d+{input_bits-1}]}}}});end end endgenerate').replace('PROGRESS','if(used>0)assert(age[0]<=5);' if progress else '')

def tlb_harness():
 return r'''module formal_top(input clk,input launch,input context,input ready,input invalidate,input inv_context,input reset_in);
 reg started=0;always @(posedge clk)started<=1;wire rst=!started || reset_in;
 reg active=0,committed=0,ctx=0,stalled=0;reg [41:0] held;reg [31:0] committed_data;
 reg [1:0] generation=0;reg pending=0;reg [127:0] reply;reg [3:0] reply_tag;
 wire req_valid=launch && !active && !rst;wire req_ready;
 wire [15:0] req_addr=16'h005a;wire [7:0] req_aux={7'b0,context},req_tag=0;
 wire inv_valid=invalidate && !rst;wire [1:0] inv_asid={1'b0,inv_context};
 wire out_valid;wire out_ready=ready;wire [7:0] out_tag;wire [31:0] out_data;wire [1:0] out_fault;
 wire mem_valid;wire mem_ready=!pending && !rst;wire [15:0] mem_addr;wire [3:0] mem_tag;
 wire resp_valid=pending && !rst;wire resp_ready;wire [127:0] resp_data=reply;wire [3:0] resp_tag=reply_tag;
 candidate #(.ENTRIES(2)) dut(.*);
 wire [31:0] correct=32'h205a+({31'b0,ctx}<<12)+({31'b0,generation[ctx]}<<8);
 wire [31:0] want=committed?committed_data:correct;
 reg [31:0] memory_value;reg legal;
 always @* begin memory_value=0;legal=1;
 case(mem_addr)
 16'h8000:memory_value=32'h1001+({31'b0,generation[0]}<<6);
 16'h8100:memory_value=32'h2001+({31'b0,generation[1]}<<6);
 16'h1000:memory_value=generation[0]?0:32'h200f;
 16'h1040:memory_value=generation[0]?32'h210f:0;
 16'h2000:memory_value=generation[1]?0:32'h300f;
 16'h2040:memory_value=generation[1]?32'h310f:0;
 default:begin memory_value=0;legal=0;end
 endcase end
 always @(posedge clk)begin
 if(rst)begin active<=0;committed<=0;stalled<=0;generation<=0;pending<=0;ctx<=0;assert(!out_valid && !req_ready && !mem_valid && !resp_ready);end
 else begin
 if(stalled)begin assert(out_valid);assert({out_tag,out_fault,out_data}==held);end
 stalled<=out_valid && !out_ready;held<={out_tag,out_fault,out_data};
 if(inv_valid)generation[inv_context]<=!generation[inv_context];
 if(req_valid && req_ready)begin assert(!active);active<=1;ctx<=context;committed<=0;end
 if(out_valid)begin assert(active);assert(out_tag==0);assert(out_fault==0);assert(out_data==want);committed<=1;committed_data<=want;end
 if(out_valid && out_ready)begin active<=0;committed<=0;end
 if(resp_valid && resp_ready)pending<=0;
 if(mem_valid && mem_ready)begin assert(legal);assert(mem_tag==0);assert(active);pending<=1;reply<={96'b0,memory_value};reply_tag<=mem_tag;end
 end end endmodule
'''

def check(source,kind,root,*,k=1,bound=8,progress=False,input_bits=8):
 root=Path(root);root.mkdir(parents=True,exist_ok=False);start=time.monotonic()
 r={'status':'unproven','kind':kind,'k':k if kind=='arithmetic' else None,'bound':bound,'accepted_operand_bits':input_bits if kind=='arithmetic' else None,'unbounded':False,'progress_property':progress,'physical':False,'source_sha256':digest(source),'initial_state':'first edge reset; candidate non-reset state unconstrained except explicit HDL initializers','assumptions':f'arithmetic M=N=1, signed {input_bits}-bit operand domain sign-extended to8 bits, arbitrary synchronous resets and launch; ready arbitrary unless progress mode fixes it high' if kind=='arithmetic' else 'two ASIDs, one VPN, two alternating page generations, no permission faults, one outstanding client and fixed one-cycle external response; arbitrary resets, invalidations and output stalls','assumptions_enforced_by_sat':True,'solver_timeout_s':45,'wall_timeout_s':60}
 try:
  sanitize(source);(root/'candidate.sv').write_text(source);h=arithmetic_harness(k,progress,input_bits) if kind=='arithmetic' else tlb_harness();(root/'formal.sv').write_text(h)
  (root/'formal.ys').write_text(f'read_verilog -formal -sv candidate.sv formal.sv; prep -top formal_top -flatten; memory_map; opt; async2sync; chformal -lower; sat -seq {bound} -set-assumes -prove-asserts -verify -timeout 45 -dump_vcd counterexample.vcd')
  out=run([tool('yosys'),'-s','formal.ys'],root,'formal',60)
  if 'SUCCESS!' in out:r['status']='bounded_pass'
  else:r['reason']='No proof-success marker; result unproven'
 except (Rejected,OSError) as e:
  r['error']=str(e)
  log=(root/'formal.log').read_text() if (root/'formal.log').exists() else ''
  if 'FAIL!' in log or 'proof did fail' in log:r['status']='counterexample'
 r['elapsed_s']=round(time.monotonic()-start,3);(root/'result.json').write_text(json.dumps(r,indent=2));return r
