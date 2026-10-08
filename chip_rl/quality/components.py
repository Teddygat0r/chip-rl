"""Host-only, source-bound component verification; never a reward or full-proof gate.

The multiplier cutpoint preserves control, registers, routing and accumulator RTL.
Every cut is recorded. Routing and recurrence assertions use an independent snapshot.
Only the recognized folded template is supported, with explicit fail-closed anchors.
"""
import json,time,re
from pathlib import Path
from ..evaluate import sanitize,digest,run,tool,Rejected
from .spec import Config,HEADER
from .._tools import TOOLS

def instrument(source,c,scope="combined"):
 sanitize(source)
 clean=re.sub(r'/\*.*?\*/|//[^\n]*',' ',source,flags=re.S)
 if re.search(r'\b(?:assume|assert|cover|restrict|property|sequence|checker)\b|\b(?:proof_|prev_)\w*',clean):raise ValueError('candidate formal constraints or monitor namespace forbidden')
 if scope not in ("combined","routing_control","datapath_transition"):raise ValueError("proof scope")
 if c.name not in ('dot','tensor'):raise ValueError('arithmetic only')
 anchors=['p=a*b;','wire signed [AW-1:0] sum=accum+chunk;','reg busy;reg [1023:0] command;integer pos;','reg signed [7:0] a,b;reg signed [15:0] p;']
 if not source.startswith(HEADER) or any(source.count(x)!=1 for x in anchors):raise ValueError('unsupported folded template/cutpoint')
 shifted='reg [8*K-1:0] qa,qb;' in source
 a='qa[8*t+:8]' if shifted else 'command[8*(16*r+pos+t)+:8]'
 b='qb[8*t+:8]' if shifted else 'command[512+8*(4*(pos+t)+c)+:8]'
 s=source.replace(HEADER,HEADER.replace(');',',input [16*K*M*N-1:0] proof_terms);'),1)
 s=s.replace(anchors[2],anchors[2]+r'''
 reg [16*K*M*N-1:0] proof_saved;
 reg [1023:0] proof_input;
 reg proof_pending=0,proof_seen=0,proof_stall=0;
 reg [383:0] proof_held;integer proof_age=0;
 genvar pi;generate for(pi=0;pi<K*M*N;pi=pi+1)begin:BOUND
 wire signed [15:0] term=proof_terms[16*pi+:16];
 always @(posedge clk)if(!rst && in_valid && in_ready)begin
 assume(term>=-16'sd16256);assume(term<=16'sd16384);end
 end endgenerate
 always @(posedge clk)begin
 proof_seen<=1;
 if(rst)begin proof_pending<=0;proof_stall<=0;proof_age<=0;end
 else begin
 if(proof_seen)begin
 assert(proof_pending==(busy || ov));assert(!(busy && ov));
 assert(in_ready==(!busy && !ov));assert(out_valid==ov);
 if(busy)begin assert(pos>=0 && pos<K);assert(pos%LANES==0);
 assert(proof_age==pos/LANES);assert(proof_age<(K+LANES-1)/LANES);end
 if(proof_pending && proof_age==(K+LANES-1)/LANES)assert(ov);
 if(ov)assert(proof_age==(K+LANES-1)/LANES);
 if(proof_stall)begin assert(out_valid);assert(out_data==proof_held);end
 end
 proof_stall<=out_valid && !out_ready;proof_held<=out_data;
 if(in_valid && in_ready)begin proof_saved<=proof_terms;proof_input<=in_data;proof_pending<=1;proof_age<=0;end
 else if(busy)proof_age<=proof_age+1;
 if(out_valid && out_ready)proof_pending<=0;
 end
 if(proof_seen && rst)assert(!in_ready && !out_valid);
 end
''',1)
 s=s.replace('p=a*b;',r'''if(proof_seen && !rst && busy)begin
 assert(a==proof_input[8*(16*r+pos+l)+:8]);
 assert(b==proof_input[512+8*(4*(pos+l)+c)+:8]);end
 p=proof_saved[16*((r*N+c)*K+pos+l)+:16];''',1)
 monitor=r'''
 reg signed [31:0] proof_prefix,proof_total,proof_chunk;integer z,t;
 reg signed [15:0] proof_term;
 always @* begin
 proof_prefix=0;proof_total=0;proof_chunk=0;proof_term=0;
 for(z=0;z<K;z=z+1)begin
 proof_term=proof_saved[16*((r*N+c)*K+z)+:16];
 proof_total=proof_total+proof_term;
 if(z<pos)proof_prefix=proof_prefix+proof_term;
 if(z>=pos && z<pos+LANES)proof_chunk=proof_chunk+proof_term;
 end end
 always @(posedge clk)if(proof_seen && !rst)begin
 if(busy)begin
 assert($signed(accum)==proof_prefix);assert($signed(chunk)==proof_chunk);
 assert($signed(sum)==proof_prefix+proof_chunk);
 for(t=0;t<LANES;t=t+1)if(pos+t<K)begin
 assert(OPERAND_A==proof_input[8*(16*r+pos+t)+:8]);
 assert(OPERAND_B==proof_input[512+8*(4*(pos+t)+c)+:8]);
 end end
 if(ov)assert($signed(od[24*(r*N+c)+:24])==proof_total);
 end
'''.replace('OPERAND_A',a).replace('OPERAND_B',b)
 s=s.replace(anchors[1],anchors[1]+monitor,1)
 # Explicit zero-padding assertion, independent of arithmetic slice checks.
 s=s.replace('endmodule',r'''generate if(M*N<16)begin:PAD
 always @(posedge clk)if(proof_seen && !rst && ov)assert(out_data[383:24*M*N]==0);
 end endgenerate
 endmodule''',1)
 h=f'''module formal_top(input clk,reset_in,in_valid,out_ready,input [1023:0] in_data,input [{16*c.k*c.m*c.n-1}:0] proof_terms);
 reg started=0;always @(posedge clk)started<=1;wire rst=!started || reset_in;
 wire in_ready,out_valid;wire [383:0] out_data;
 candidate #(.M({c.m}),.N({c.n}),.K({c.k})) dut(.*);endmodule\n'''
 if scope=='routing_control':
  for text in ['assert(out_data==proof_held);','assert($signed(accum)==proof_prefix);','assert($signed(chunk)==proof_chunk);','assert($signed(sum)==proof_prefix+proof_chunk);','if(ov)assert($signed(od[24*(r*N+c)+:24])==proof_total);']:
   s=s.replace(text,'')
 elif scope=='datapath_transition':
  start=s.index(' reg [16*K*M*N-1:0] proof_saved;');end=s.index(' assign in_ready',start)
  globals_ = r''' reg [16*K*M*N-1:0] proof_saved;
 reg proof_seen=0,prev_rst,prev_push,prev_busy,prev_last;
 always @(posedge clk)begin
 proof_seen<=1;prev_rst<=rst;prev_push<=in_valid && in_ready;prev_busy<=busy;prev_last<=pos+LANES>=K;
 if(!proof_seen && busy)begin assume(pos>=0 && pos<K);assume(pos%LANES==0);end
 if(in_valid && in_ready)proof_saved<=proof_terms;
 end
 genvar pi;generate for(pi=0;pi<K*M*N;pi=pi+1)begin:BOUND
 wire signed [15:0] incoming=proof_terms[16*pi+:16],saved=proof_saved[16*pi+:16];
 always @(posedge clk)begin
 if(!proof_seen && busy)begin assume(saved>=-16'sd16256);assume(saved<=16'sd16384);end
 if(!rst && in_valid && in_ready)begin assume(incoming>=-16'sd16256);assume(incoming<=16'sd16384);end
 end end endgenerate
'''
  s=s[:start]+globals_+s[end:]
  s=s.replace("if(proof_seen && !rst && busy)begin\n assert(a==proof_input[8*(16*r+pos+l)+:8]);\n assert(b==proof_input[512+8*(4*(pos+l)+c)+:8]);end",'')
  local=r'''reg signed [AW-1:0] prev_accum,prev_sum;reg [23:0] prev_od;
 reg signed [31:0] proof_chunk;reg signed [15:0] proof_term;integer z;
 always @* begin proof_chunk=0;proof_term=0;
 for(z=0;z<K;z=z+1)begin proof_term=proof_saved[16*((r*N+c)*K+z)+:16];
 if(z>=pos && z<pos+LANES)proof_chunk=proof_chunk+proof_term;end end
 always @(posedge clk)begin
 prev_accum<=accum;prev_sum<=sum;prev_od<=od[24*(r*N+c)+:24];
 if(!rst && busy)assert($signed(chunk)==proof_chunk);
 if(proof_seen)begin
 if(prev_rst)begin assert(accum==0);assert(od[24*(r*N+c)+:24]==0);end
 else begin
 if(prev_push)assert(accum==0);
 else if(prev_busy)assert(accum==prev_sum);
 else assert(accum==prev_accum);
 if(!prev_push && prev_busy && prev_last)assert($signed(od[24*(r*N+c)+:24])==$signed(prev_sum));
 else assert(od[24*(r*N+c)+:24]==prev_od);
 end end end
'''
  s=s.replace(monitor,local)
  s=s.replace('always @(posedge clk)if(proof_seen && !rst && ov)assert(out_data[383:24*M*N]==0);','')
  h=h.replace('wire rst=!started || reset_in;','wire rst=reset_in;')
 return s,h,{'scope':scope,'cutpoints':1,'cut':'signed 8x8 multiply replaced by captured signed16 token at the same logical term','product_range':[-16256,16384],'range_assumed_only_at_acceptance':True,'operand_routing_checked':scope!='datapath_transition','shifted':shifted,'source_sha256':digest(source),'instrumented_sha256':digest(s)}

def accumulator_harness():
 # Every supported K and lane count in one combinational proof. Bounds are legal
 # prefix/product-range facts, not assumptions about implementation correctness.
 modules=[];instances=[]
 for k in range(1,17):
  for lanes in sorted({1,2,4,(k+3)//4}):
   aw=15+k.bit_length();name=f'a{k}_{lanes}'
   modules.append(f'''module {name}(input signed [{aw-1}:0] accum,chunk,input [4:0] pos);
 wire signed [{aw-1}:0] sum=accum+chunk;
 wire signed [31:0] aa=accum,bb=chunk;
 wire signed [31:0] count=(pos+{lanes}>{k})?{k}-pos:{lanes};
 always @* begin
 assume(pos<{k});assume(pos%{lanes}==0);
 assume(aa>=-16256*$signed({{1'b0,pos}}));assume(aa<=16384*$signed({{1'b0,pos}}));
 assume(bb>=-16256*count);assume(bb<=16384*count);
 assert($signed(sum)==aa+bb);end endmodule''')
   idx=len(instances);instances.append(f'{name} u{name}(a[{20*idx}+:{aw}],b[{20*idx}+:{aw}],pos[{5*idx}+:5]);')
 return '\n'.join(modules)+f'\nmodule formal_top(input [{20*len(instances)-1}:0] a,b,input [{5*len(instances)-1}:0] pos);'+''.join(instances)+'endmodule\n'

def sat(root,source,harness,*,bound=1,metadata=None):
 root=Path(root);root.mkdir(parents=True,exist_ok=False);start=time.monotonic()
 r={'status':'unproven','bound':bound,'unbounded_implementation_proof':False,'solver_timeout_s':30,'wall_timeout_s':45,'assumptions_enforced':True,**(metadata or {})}
 (root/'candidate.sv').write_text(source);(root/'formal.sv').write_text(harness)
 script=f'read_verilog -formal -sv candidate.sv formal.sv; prep -top formal_top -flatten; memory_map; opt; async2sync; chformal -lower; sat -seq {bound} -set-assumes -prove-asserts -verify -timeout 30 -dump_vcd counterexample.vcd'
 (root/'formal.ys').write_text(script)
 try:
  log=run([tool('yosys'),'-s','formal.ys'],root,'formal',45)
  if 'SUCCESS!' in log:r['status']='bounded_pass'
  else:r['reason']='proof success marker absent'
 except (Rejected,OSError) as e:
  r['error']=str(e);log=(root/'formal.log').read_text() if (root/'formal.log').exists() else ''
  if 'proof did fail' in log or 'FAIL!' in log:r['status']='counterexample'
 r['elapsed_s']=round(time.monotonic()-start,3);(root/'result.json').write_text(json.dumps(r,indent=2));return r

def check_folded(source,c,root,bound,scope="combined"):
 if type(bound) is not int or bound<(4 if scope=="datapath_transition" else 4):raise ValueError("at least four steps required to activate sampled transition assertions")
 instrumented,harness,meta=instrument(source,c,scope)
 root=Path(root)
 r=sat(root,instrumented,harness,bound=bound,metadata={'kind':'bounded_abstract_folded_components','config':vars(c),**meta})
 (root/'original.sv').write_text(source);return r

def exhaustive_product(root):
 """All65536 signed byte pairs; independently computed integer Python oracle."""
 root=Path(root);root.mkdir(parents=True,exist_ok=False);start=time.monotonic()
 expected=[]
 for a in range(256):
  for b in range(256):expected.append((a if a<128 else a-256)*(b if b<128 else b-256))
 (root/'expected.hex').write_text(''.join(f'{p&65535:04x}\n' for p in expected))
 # The exact typed product expression is the template cutpoint, not a sampled MAC.
 (root/'product.sv').write_text('module product_unit(input signed [7:0] a,b,output signed [15:0] p);assign p=a*b;endmodule\n')
 (root/'tb.sv').write_text('''module tb;reg signed [7:0] a,b;wire signed [15:0] p;product_unit dut(a,b,p);
 reg [15:0] expected[0:65535];integer i;
 initial begin $readmemh("expected.hex",expected);for(i=0;i<65536;i=i+1)begin
 a=i/256;b=i%256;#1;if(p!==expected[i])$fatal(1,"product mismatch");
 if($signed(p)<-16256 || $signed(p)>16384)$fatal(1,"product bounds");end
 $display("PASS 65536");$finish;end endmodule''')
 r={'status':'unproven','kind':'exhaustive_signed_int8_product','pairs':65536,'range':[min(expected),max(expected)],'full_implementation_proof':False}
 try:
  cmd=[tool('iverilog')]
  if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
  run([tool('yosys'),'-p','read_verilog -sv product.sv; synth -top product_unit; check -assert; write_verilog -noattr netlist.v'],root,'synthesis',45)
  passed=[]
  for mode,src in [('rtl','product.sv'),('mapped','netlist.v')]:
   run(cmd+['-g2012','-s','tb','-o','sim',src,'tb.sv'],root,mode+'-compile',30)
   out=run([tool('vvp'),'sim'],root,mode+'-simulation',30)
   if 'PASS 65536' in out:passed.append(mode)
  r['passed_stages']=passed
  if passed==['rtl','mapped']:r['status']='exhaustive_pass'
 except (Rejected,OSError) as e:r['error']=str(e)
 r['elapsed_s']=round(time.monotonic()-start,3);(root/'result.json').write_text(json.dumps(r,indent=2));return r
