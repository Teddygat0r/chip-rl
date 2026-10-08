"""Source-bound inductive obligations for a single-output folded RTL instance.

An inductive result applies to the explicit symbolic-product model only. Reachability,
concrete witness replay and cutpoint linkage are separate obligations, never reward.
"""
import json,re,time
from pathlib import Path
from .components import instrument as validate_template
from .spec import HEADER
from ..evaluate import run,tool,Rejected,digest

def lanes_for(source,c):
 match=re.search(r'localparam LANES=(.*?),AW=',source)
 if not match:raise ValueError('lane declaration')
 value=match[1]
 if value=='((K+3)/4)':return (c.k+3)//4
 if value in ('1','2','4'):return int(value)
 raise ValueError('unsupported lane expression')

def model(source,c,*,reach=False,contradiction=False,concrete=False):
 validate_template(source,c)
 clean=re.sub(r'/\*.*?\*/|//[^\n]*',' ',source,flags=re.S)
 if '.' in clean:raise ValueError('hierarchical references and real literals unsupported in proof template')
 if (c.m,c.n)!=(1,1):raise ValueError('inductive model supports one output only')
 lanes=lanes_for(source,c);case_count=3+(c.k+lanes-1)//lanes
 shifted='reg [8*K-1:0] qa,qb;' in source
 s=source.replace(HEADER,HEADER.replace(');',',input [16*K-1:0] proof_tokens,output proof_ok,output [7:0] proof_goals,output [4:0] proof_case,output proof_cover,output reg [CASECOUNT-1:0] proof_phase_seen=0);'),1)
 s=s.replace('CASECOUNT',str(case_count))
 global_code=r'''
 reg proof_started=0;reg [16*K-1:0] proof_saved;
 reg [1023:0] proof_input;reg proof_pending;reg [4:0] proof_age;
 reg [7:0] proof_seen_events;reg proof_was_stalled;
 wire proof_push=in_valid && in_ready,proof_pop=out_valid && out_ready;
 genvar u;wire [K-1:0] proof_ranges;
 generate for(u=0;u<K;u=u+1)begin:PR
 wire signed [15:0] incoming=proof_tokens[16*u+:16],saved=proof_saved[16*u+:16];
 always @* if(!rst && proof_push)begin assume(incoming>=-16'sd16256);assume(incoming<=16'sd16384);end
 assign proof_ranges[u]=(saved>=-16'sd16256 && saved<=16'sd16384);
 end endgenerate
 always @(posedge clk)begin
 proof_started<=1;
 if(rst)begin proof_saved<=0;proof_input<=0;proof_pending<=0;proof_age<=0;proof_was_stalled<=0;end
 else begin
 if(proof_push)begin proof_saved<=proof_tokens;proof_input<=in_data;proof_pending<=1;proof_age<=0;end
 else if(busy)proof_age<=proof_age+1;
 if(proof_pop)proof_pending<=0;
 proof_was_stalled<=out_valid && !out_ready;
 end end
 // Event history persists across reset after the first clock, so cancellation can
 // be covered in the same witness as completion and a subsequent transaction.
 always @(posedge clk)begin
 if(!proof_started)proof_seen_events<=0;
 else begin
 if(!rst && proof_push)proof_seen_events[0]<=1;
 if(!rst && busy && (pos>0 || K<=LANES))proof_seen_events[1]<=1;
 if(!rst && out_valid)proof_seen_events[2]<=1;
 if(!rst && out_valid && !out_ready)proof_seen_events[3]<=1;
 if(!rst && proof_was_stalled && proof_pop)proof_seen_events[4]<=1;
 if(rst && busy)proof_seen_events[5]<=1;
 if(!rst && proof_push && proof_seen_events[5])proof_seen_events[6]<=1;
 if(!rst && proof_pop && proof_seen_events[6])proof_seen_events[7]<=1;
 end end
 assign proof_goals=proof_seen_events;
 assign proof_case=!proof_started?0:(!busy && !ov)?1:ov?2:3+pos/LANES;
 assign proof_cover=!proof_ok || proof_case<CASECOUNT;
 always @(posedge clk)if(proof_case<CASECOUNT)proof_phase_seen[proof_case]<=1;
 wire proof_control=(proof_pending==(busy || ov)) && !(busy && ov)
 && (!busy || (pos>=0 && pos<K && pos%LANES==0 && proof_age<(K+LANES-1)/LANES && pos==proof_age*LANES))
 && (!ov || (proof_age==(K+LANES-1)/LANES && pos==(((K+LANES-1)/LANES)-1)*LANES))
 && (in_ready==(!rst && !busy && !ov)) && (out_valid==(!rst && ov));
 wire proof_datapath;
 assign proof_ok=PROOF_EXPRESSION;
'''
 s=s.replace('reg busy;reg [1023:0] command;integer pos;', 'reg busy;reg [1023:0] command;integer pos;'+global_code.replace('CASECOUNT',str(case_count)),1)
 s=s.replace('reg signed [AW-1:0] accum;','reg proof_operand_ok;reg signed [AW-1:0] accum;',1)
 s=s.replace('always @* begin chunk=0;','always @* begin proof_operand_ok=1;chunk=0;',1)
 s=s.replace('p=a*b;',r'''proof_operand_ok=proof_operand_ok && (a==proof_input[8*(pos+l)+:8]) && (b==proof_input[512+32*(pos+l)+:8]);p=proof_saved[16*(pos+l)+:16];''',1)
 monitor=r'''
 wire [8*K-1:0] proof_a,proof_b;
 for(genvar z=0;z<K;z=z+1)begin:SNAP
 assign proof_a[8*z+:8]=proof_input[8*z+:8];assign proof_b[8*z+:8]=proof_input[512+32*z+:8];end
 integer z;reg signed [31:0] proof_prefix,proof_total,proof_chunk;reg signed [15:0] proof_term;
 always @* begin proof_prefix=0;proof_total=0;proof_chunk=0;proof_term=0;
 for(z=0;z<K;z=z+1)begin proof_term=proof_saved[16*z+:16];proof_total=proof_total+proof_term;
 if(z<pos)proof_prefix=proof_prefix+proof_term;
 if(z>=pos && z<pos+LANES)proof_chunk=proof_chunk+proof_term;
 end end
 assign proof_datapath=(!busy || ($signed(accum)==proof_prefix && $signed(chunk)==proof_chunk && proof_operand_ok && ROUTE))
 && (!ov || ($signed(accum)==proof_total && $signed(od[23:0])==proof_total)) && od[383:24]==0;
'''.replace('ROUTE','qa==(proof_a>>(8*pos)) && qb==(proof_b>>(8*pos))' if shifted else "1'b1")
 s=s.replace('wire signed [AW-1:0] sum=accum+chunk;','wire signed [AW-1:0] sum=accum+chunk;'+monitor,1)
 s=s.replace('PROOF_EXPRESSION',"1'b1" if reach else "!proof_started || (proof_control && command==proof_input && (&proof_ranges) && proof_datapath)")
 if concrete:
  s=s.replace('p=proof_saved[16*(pos+l)+:16];','p=a*b;')
  s=s.replace('proof_saved<=proof_tokens','proof_saved<=proof_real_tokens')
  extra=r'''wire [16*K-1:0] proof_real_tokens;wire [K-1:0] proof_link;
 genvar j;generate for(j=0;j<K;j=j+1)begin:LINK
 wire signed [7:0] ia=in_data[8*j+:8],ib=in_data[512+32*j+:8];
 wire signed [7:0] sa=proof_input[8*j+:8],sb=proof_input[512+32*j+:8];
 wire signed [15:0] actual=ia*ib,snapshot=sa*sb;
 assign proof_real_tokens[16*j+:16]=actual;
 assign proof_link[j]=proof_saved[16*j+:16]==snapshot;
 end endgenerate
'''
  s=s.replace('wire proof_datapath;',extra+'wire proof_datapath;')
  s=s.replace('always @* if(!rst && proof_push)begin assume(incoming>=-16\'sd16256);assume(incoming<=16\'sd16384);end','')
  s=s.replace('proof_control && command==proof_input','(&proof_link) && proof_control && command==proof_input')
 if contradiction:s=s.replace('endmodule','always @* assume(0);endmodule',1)
 top=f'''module formal_top(input clk,reset_in,in_valid,out_ready,input [1023:0] in_data,input [{16*c.k-1}:0] proof_tokens,
 output proof_ok,output [7:0] proof_goals,output [4:0] proof_case,output proof_cover,output [{case_count-1}:0] proof_phase_seen,output in_ready,out_valid);
 reg started=0;always @(posedge clk)started<=1;wire rst=!started || reset_in;wire [383:0] out_data;
 candidate #(.M(1),.N(1),.K({c.k})) dut(.*);endmodule\n'''
 return s,top,{'source_sha256':digest(source),'instrumented_sha256':digest(s),'config':vars(c),'lanes':lanes,'case_count':case_count,'symbolic_product_range':[-16256,16384],'multiplier_cutpoints':0 if concrete else 1,'concrete_multiplier_link':concrete,'arbitrary_synchronous_resets':True,'arbitrary_output_backpressure':True,'input_stability_assumption':False,'initial_state':'first edge reset, other candidate state unconstrained','contradictory_harness_control':contradiction}

def check(source,c,root,*,mode='induction',bound=24,maxsteps=3,contradiction=False,concrete=False,case=None,phases=False):
 if mode not in ('induction','reach','base','stepcase','coverage'):raise ValueError('mode')
 root=Path(root);root.mkdir(parents=True,exist_ok=False);start=time.monotonic()
 s,h,meta=model(source,c,reach=mode=='reach',contradiction=contradiction,concrete=concrete)
 (root/'original.sv').write_text(source);(root/'candidate.sv').write_text(s);(root/'formal.sv').write_text(h)
 if mode=='induction':option=f'-tempinduct -seq 1 -maxsteps {maxsteps} -prove proof_ok 1 -verify'
 elif mode=='base':option='-seq 2 -prove proof_ok 1 -verify'
 elif mode=='stepcase':
  if type(case) is not int or not 0<=case<meta['case_count']:raise ValueError('case index')
  option=f'-seq 2 -set-at 1 proof_ok 1 -set-at 1 proof_case {case} -prove-skip 1 -prove proof_ok 1 -verify'
 elif mode=='coverage':option='-seq 1 -prove proof_cover 1 -verify'
 else:option=f'-seq {bound} -set-at {bound} proof_goals 255 -show-ports'+(f" -set-at {bound} proof_phase_seen {2**meta['case_count']-1}" if phases else '')
 preparation='setattr -unset init w:*; ' if mode in ('stepcase','coverage') else ''
 script=f'read_verilog -formal -sv candidate.sv formal.sv; prep -top formal_top -flatten; memory_map; opt; chformal -lower; check -assert; {preparation}write_json prepared.json; sat {option} -set-assumes -timeout 20 -dump_vcd witness.vcd -dump_json witness.json'
 (root/'formal.ys').write_text(script)
 r={'status':'unproven','mode':mode,'step_case':case,'phase_coverage_required':phases,'initial_attributes_removed':mode in ('stepcase','coverage'),'max_induction_steps':maxsteps if mode=='induction' else None,'reach_bound':bound if mode=='reach' else None,'solver_timeout_s':20,'wall_timeout_s':35,'assumptions_enforced':True,'concrete_full_design_proof':False,**meta}
 try:
  log=run([tool('yosys'),'-s','formal.ys'],root,'formal',35)
  if mode=='induction' and 'Induction step proven: SUCCESS!' in log and re.search(r'Base case for induction length \d+ proven',log):r['status']='inductive_concrete_instance_pass' if concrete else 'inductive_abstract_pass'
  if mode in ('base','stepcase','coverage') and 'SAT proof finished - no model found: SUCCESS!' in log:r['status']={'base':'reset_base_pass','stepcase':'transition_case_pass','coverage':'case_coverage_pass'}[mode]
  if mode=='reach':
   if 'SAT solving finished - model found:' in log:r['status']='reachable_witness'
   elif 'SAT solving finished - no model found' in log:r['status']='unreachable_within_bound'
 except (Rejected,OSError) as e:
  r['error']=str(e);log=(root/'formal.log').read_text() if (root/'formal.log').exists() else ''
  if 'model found for base case: FAIL!' in log:r['status']='base_case_counterexample'
  elif mode in ('base','stepcase','coverage') and 'SAT proof finished - model found: FAIL!' in log:r['status']='obligation_counterexample'
 r['elapsed_s']=round(time.monotonic()-start,3);(root/'result.json').write_text(json.dumps(r,indent=2));return r
