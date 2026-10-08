"""Supplemental long verification, separate from the default workload cycle budget."""
import json,re,time
from pathlib import Path
from dataclasses import asdict
from ..evaluate import TrustedEvaluator,tool,run,TOOLS,digest,Rejected
from .workloads import crc_vectors,retirement_vectors
CYCLE_BUDGET={'crc':900000,'retire':200000}

def check(c,source,seed,artifacts,cache=None):
 root=Path(artifacts);root.mkdir(parents=True,exist_ok=False);root.chmod(0o700);start=time.monotonic()
 result={'config':asdict(c),'tested_correct':False,'scope':'long_history_verification_not_scored_default_workload','long_verification_cycle_budget':CYCLE_BUDGET[c.name],'default_workload_cycle_budget':c.max_cycles,'source_sha256':digest(source),'recipe_sha256':digest(''.join(p.read_text() for p in sorted(Path(__file__).parent.glob('*.py')))),'formal':'not_run','physical':'not_run','os_isolation':'not_provided'}
 try:
  q=TrustedEvaluator(cache);sd,sm,_=q._synth(c,source);result['synthesis']=sm
  header=f'''module tb;reg clk=0,rst=1,in_valid=0,out_ready=0;reg [511:0] in_data=0;wire in_ready,out_valid;wire [255:0] out_data;
 candidate #(.WIDTH({c.width}),.DEPTH({c.depth}),.K({c.k})) dut(.*);
 task tick;begin #1;clk=1;#5;clk=0;end endtask
'''
  if c.name=='crc':
   pairs,stats=crc_vectors(c,seed);n=len(pairs)
   (root/'inputs.hex').write_text(''.join(f'{x:0128x}\n' for x,y in pairs));(root/'expected.hex').write_text(''.join(f'{y:064x}\n' for x,y in pairs))
   tb=header+f'''reg [511:0] inputs[0:{n-1}];reg [255:0] expected[0:{n-1}];integer accepted[0:{n-1}];integer sent=0,received=0,cycle=0,latency=0,peak=0;
 reg stalled=0;reg [255:0] held=0;
 initial begin $readmemh("inputs.hex",inputs);$readmemh("expected.hex",expected);
 repeat(3)begin #4;tick;end rst=0;
 while(received<{n} && cycle<{CYCLE_BUDGET[c.name]})begin
 in_valid=sent<{n};in_data=sent<{n}?inputs[sent]:0;out_ready=cycle%37>=5;#4;
 if((in_ready!==0 && in_ready!==1)||(out_valid!==0 && out_valid!==1))$fatal(1,"unknown handshake");
 if(stalled && (out_valid!==1 || out_data!==held))$fatal(1,"stalled response changed");
 stalled=out_valid && !out_ready;held=out_data;
 if(in_valid && in_ready)begin accepted[sent]=cycle;sent=sent+1;end
 if(out_valid && out_ready)begin
 if(received>=sent)$fatal(1,"unsolicited response");
 if(out_data!==expected[received])$fatal(1,"long CRC mismatch command%0d",received);
 if(cycle-accepted[received]<1 || cycle-accepted[received]>64)$fatal(1,"response bound");
 latency=latency+cycle-accepted[received];if(cycle-accepted[received]>peak)peak=cycle-accepted[received];received=received+1;
 end tick;cycle=cycle+1;end
 if(sent!={n} || received!={n})$fatal(1,"long completion deadline");
 in_valid=0;out_ready=1;repeat(80)begin #4;if(out_valid!==0)$fatal(1,"extra response");tick;end
 $display("HISTORY_PASS %0d %0d %0d %0d",received,cycle,latency,peak);$finish;end endmodule'''
  else:
   rows,stats=retirement_vectors(c,seed);n=len(rows)
   if n>CYCLE_BUDGET[c.name]:raise Rejected('long frame budget')
   (root/'vectors.hex').write_text(''.join(f'{rst|(v<<1)|(x<<2)|(y<<514):0193x}\n' for rst,v,x,y in rows))
   tb=header+f'''reg [769:0] vectors[0:{n-1}];integer i;
 initial begin $readmemh("vectors.hex",vectors);
 for(i=0;i<{n};i=i+1)begin rst=vectors[i][0];in_valid=vectors[i][1];in_data=vectors[i][513:2];out_ready=i%3==0;#4;
 if(in_ready!==!rst || out_valid!==!rst || (!rst && out_data!==vectors[i][769:514]))$fatal(1,"long retirement mismatch frame%0d",i);
 tick;end
 $display("HISTORY_PASS {stats['retirements']} {n} 0 0");$finish;end endmodule'''
  (root/'candidate.sv').write_text(source);(root/'netlist.v').write_text((sd/'netlist.v').read_text())
  (root/'private-case.json').write_text(json.dumps({'config':asdict(c),'seed':seed,'stats':stats,'driver_sha256':digest(Path(__file__).read_text())},indent=2))
  result['coverage']=stats;result['vectors_sha256']=digest(''.join(p.read_text() for p in sorted(root.glob('*.hex'))));answers=[]
  for label,file in [('rtl','candidate.sv'),('netlist','netlist.v')]:
   selected=tb if label=='rtl' else re.sub(r'candidate #\(.*?\)\) dut','candidate dut',tb)
   (root/'tb.sv').write_text(selected);(root/(label+'-tb.sv')).write_text(selected)
   cmd=[tool('iverilog')]
   if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
   run(cmd+['-g2012','-s','tb','-o',label+'.vvp',file,'tb.sv'],root,label+'-compile',120)
   log=run([tool('vvp'),label+'.vvp'],root,label+'-simulation',240)
   found=re.search(r'HISTORY_PASS (\d+) (\d+) (\d+) (\d+)',log)
   if not found:raise Rejected('missing complete long result')
   answers.append(tuple(map(int,found.groups())))
  if answers[0]!=answers[1]:raise Rejected('long RTL/netlist divergence')
  result.update(tested_correct=True,completed=answers[0][0],cycles=answers[0][1],latency_sum=answers[0][2],maximum_response_cycles=answers[0][3])
 except (Rejected,ValueError,OSError,AssertionError) as e:result['error']=str(e)
 result['elapsed_s']=round(time.monotonic()-start,3);(root/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
