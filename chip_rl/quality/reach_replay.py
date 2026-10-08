"""Replay SAT control witnesses on original RTL and the concrete invariant monitor."""
import json,random,time
from pathlib import Path
from .spec import Config
from .induction import model,lanes_for
from .oracles import arithmetic,independent
from ..evaluate import run,tool,Rejected,digest
from .._tools import TOOLS

def wave_values(record):
 data=iter(record.get('data',[]));value=None;out=[]
 for char in record['wave']:
  if char=='4':
   if record.get('data'):assert next(data)==''
   continue
  if char=='=':
   bits=next(data);value=int(bits,2) if bits and set(bits)<={'0','1'} else None
  elif char in ('0','1'):value=int(char)
  elif char in ('x','z'):value=None
  elif char!='.':raise ValueError('unsupported WaveJSON character')
  out.append(value)
 return out

def replay(artifact,root,*,varied=False):
 artifact=Path(artifact);root=Path(root);root.mkdir(parents=True,exist_ok=False);start=time.monotonic()
 record=json.loads((artifact/'result.json').read_text())
 if record['status']!='reachable_witness':raise ValueError('SAT witness required')
 c=Config(**record['config']);src=(artifact/'original.sv').read_text()
 signals={s['name']:wave_values(s) for s in json.loads((artifact/'witness.json').read_text())['signal']}
 keys=['in_valid','in_ready','out_ready','out_valid','in_data','reset_in','proof_goals'];lengths={len(signals[k]) for k in keys}
 if len(lengths)!=1:raise ValueError('inconsistent witness lengths')
 count=lengths.pop();assert count==record['reach_bound']
 if any(x is None for k in keys if k!='proof_goals' for x in signals[k]):raise ValueError('undefined witness input/control')
 if varied:
  rng=random.Random(1701);value=int.from_bytes(bytes([128])*128,'little')
  for i in range(count):
   if i and signals['in_valid'][i-1] and signals['in_ready'][i-1]:value=rng.getrandbits(1024)
   signals['in_data'][i]=value
 (root/'candidate.sv').write_text(src)
 linked,_,_=model(src,c,concrete=True);assert 'assume(' not in linked
 (root/'linked.sv').write_text(linked.replace('module candidate ','module linked_candidate ',1))
 expected=[arithmetic(c,x) for x in signals['in_data']];assert expected==[independent(c,x) for x in signals['in_data']]
 for key,vals in {**signals,'expected':expected}.items():
  (root/(key+'.hex')).write_text(''.join(f'{v:x}\n' if v is not None else 'x\n' for v in vals))
 phase_count=3+(c.k+lanes_for(src,c)-1)//lanes_for(src,c)
 has_phases='proof_phase_seen' in signals
 phase_check='if(linked_phases!==phases[i])$fatal(1,"phase witness mismatch");' if has_phases else ''
 phase_load='$readmemh("proof_phase_seen.hex",phases);' if has_phases else ''
 tb=f'''module tb;reg clk=0,rst=1,in_valid=0,out_ready=0;reg [1023:0] in_data=0;
 wire in_ready,out_valid;wire [383:0] out_data;candidate #(.M(1),.N(1),.K({c.k})) dut(.*);
 wire [{phase_count-1}:0] linked_phases;reg [{phase_count-1}:0] phases[0:{count-1}];
 wire linked_ready,linked_valid,proof_ok;wire [383:0] linked_data;wire [7:0] proof_goals;
 linked_candidate #(.M(1),.N(1),.K({c.k})) linked(.clk(clk),.rst(rst),.in_valid(in_valid),.out_ready(out_ready),.in_data(in_data),.in_ready(linked_ready),.out_valid(linked_valid),.out_data(linked_data),.proof_tokens({16*c.k}'b0),.proof_ok(proof_ok),.proof_goals(proof_goals),.proof_phase_seen(linked_phases));
 reg iv[0:{count-1}],ir[0:{count-1}],ov[0:{count-1}],orr[0:{count-1}],resetv[0:{count-1}];
 reg [1023:0] inputs[0:{count-1}];reg [23:0] expected[0:{count-1}];reg [7:0] goals[0:{count-1}];
 reg pending=0;reg [383:0] want;integer i;integer accepted=0,completed=0,cancelled=0;
 initial begin
 {phase_load}
 $readmemh("in_valid.hex",iv);$readmemh("in_ready.hex",ir);$readmemh("out_valid.hex",ov);$readmemh("out_ready.hex",orr);$readmemh("reset_in.hex",resetv);$readmemh("in_data.hex",inputs);$readmemh("expected.hex",expected);$readmemh("proof_goals.hex",goals);
 for(i=0;i<{count};i=i+1)begin
 rst=(i==0)?1:resetv[i];in_valid=iv[i];out_ready=orr[i];in_data=inputs[i];#4;
 if(in_ready!==ir[i] || out_valid!==ov[i])$fatal(1,"witness control mismatch at %0d",i);
 {phase_check}
 if(proof_ok!==1)$fatal(1,"concrete invariant/link mismatch at %0d",i);
 if(i>0 && proof_goals!==goals[i])$fatal(1,"reach goal mismatch at %0d",i);
 if(i>0 && (in_ready!==linked_ready || out_valid!==linked_valid || out_data!==linked_data))$fatal(1,"instrumentation changed observables");
 if(rst)begin if(pending)cancelled=cancelled+1;pending=0;end
 else begin
 if(out_valid)begin if(!pending || out_data!==want)$fatal(1,"independent oracle mismatch");end
 if(out_valid && out_ready)begin pending=0;completed=completed+1;end
 if(in_valid && in_ready)begin if(pending)$fatal(1,"overlapping outstanding work");pending=1;want={{360'b0,expected[i]}};accepted=accepted+1;end
 end
 #1;clk=1;#5;clk=0;
 end
 if(goals[{count-1}]!==255 || accepted<2 || completed<1 || cancelled<1)$fatal(1,"required reachability absent");
 $display("PASS %0d %0d %0d",accepted,completed,cancelled);$finish;end endmodule'''
 (root/'tb.sv').write_text(tb)
 r={'status':'unproven','scope':'finite_concrete_witness_and_invariant_link_replay','source_sha256':digest(src),'cycles':count,'varied_data':varied,'phase_mask_checked':has_phases,'independent_oracles':2,'unbounded_composition_proof':False}
 try:
  cmd=[tool('iverilog')]
  if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
  run(cmd+['-g2012','-s','tb','-o','sim','candidate.sv','linked.sv','tb.sv'],root,'compile',30)
  log=run([tool('vvp'),'sim'],root,'simulation',30)
  if 'PASS ' in log:r['status']='witness_replay_pass';r['counts']=log.strip()
 except (Rejected,OSError) as e:r['error']=str(e)
 r['elapsed_s']=round(time.monotonic()-start,3);(root/'result.json').write_text(json.dumps(r,indent=2));return r
