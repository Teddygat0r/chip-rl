"""Independent driver with reset interruption, bounded stalls, and epoch scoring."""
from pathlib import Path
import json,tempfile,shutil,re,time
from dataclasses import asdict
from ..evaluate import TrustedEvaluator,tool,run,TOOLS,digest,Rejected

def check(c,source,epochs,artifacts,cache=None):
 root=Path(artifacts);root.mkdir(parents=True,exist_ok=False);root.chmod(0o700);q=TrustedEvaluator(cache)
 result={'config':asdict(c),'driver_sha256':digest(Path(__file__).read_text()),'epochs_sha256':digest(json.dumps(epochs,sort_keys=True)),'tested_correct':False,'scope':'deep_test_only_not_default_or_pilot_promotion','source_sha256':digest(source),'formal':'not_run','physical':'not_run','os_isolation':'not_provided'};started=time.monotonic()
 try:
  sd,sm,_=q._synth(c,source);result['synthesis']=sm
  flat=[pair for e in epochs for pair in e['pairs']];offset=0;calls=[]
  for i,e in enumerate(epochs):
   calls.append(f"epoch({offset},{len(e['pairs'])},{e.get('cut',0)},{e.get('hold',0)},{e.get('period',1)},{i},{int(e.get('score',True))},{e.get('reset_valid',1)},{e.get('reset_ready',1)},512'h{e.get('reset_payload',((1<<512)-1) if i%2 else 0):x});")
   offset+=len(e['pairs'])
  tb='''module tb;
 reg clk=0,rst=1,in_valid=0,out_ready=0;reg [511:0] in_data=0;wire in_ready,out_valid;wire [255:0] out_data;
 candidate #(.WIDTH(WIDTH_VALUE),.DEPTH(DEPTH_VALUE),.K(K_VALUE)) dut(.*);
 reg [511:0] inputs[0:LAST];reg [255:0] expected[0:LAST];integer accepted[0:LAST];integer total=0,total_cycles=0,total_latency=0,peak=0;
 task tick;begin #1;clk=1;#5;clk=0;end endtask
 task epoch;input integer base,n,cut,hold,period,identifier,score,reset_valid,reset_ready;input [511:0] reset_payload;integer sent,received,cycle,j,latency;reg stalled;reg [255:0] held;
 begin
 rst=1;in_valid=reset_valid;out_ready=reset_ready;in_data=reset_payload;repeat(3)begin #4;tick;if(out_valid!==0)$fatal(1,"reset did not cancel output after clock edge");end
 rst=0;sent=0;received=0;cycle=0;stalled=0;held=0;
 while(received<n && cycle<MAX_CYCLES_VALUE && (cut==0 || sent<cut))begin
  in_valid=(sent<n && cycle>=sent*period);in_data=sent<n?inputs[base+sent]:0;
  out_ready=(cycle%47>=13 && cycle%7!=0);#4;
  if((in_ready!==0 && in_ready!==1)||(out_valid!==0 && out_valid!==1))$fatal(1,"unknown handshake");
  if(stalled && (out_valid!==1 || out_data!==held))$fatal(1,"unstable stalled output");
  stalled=out_valid && !out_ready;held=out_data;
  if(in_valid && in_ready)begin accepted[sent]=cycle;sent=sent+1;end
  if(out_valid && out_ready)begin
   if(received>=sent)$fatal(1,"unsolicited response");
   if(out_data!==expected[base+received])$fatal(1,"independent oracle mismatch epoch%0d command%0d",identifier,received);
   if(cycle-accepted[received]<1 || cycle-accepted[received]>64)$fatal(1,"response bound");
   latency=cycle-received*period;if(cut==0 && score)begin total_latency=total_latency+latency;if(latency>peak)peak=latency;total=total+1;end
   received=received+1;
  end
  tick;cycle=cycle+1;
 end
 if(cut!=0)begin
  if(sent!=cut)$fatal(1,"interruption never reached");
  in_valid=0;out_ready=0;repeat(hold)begin #4;tick;end
 end else begin
  if(sent!=n || received!=n)$fatal(1,"completion deadline");
  in_valid=0;out_ready=1;repeat(80)begin #4;if(out_valid!==0)$fatal(1,"extra response");tick;end
  if(score)total_cycles=total_cycles+cycle;
 end
 end endtask
 initial begin $readmemh("inputs.hex",inputs);$readmemh("expected.hex",expected);
 CALLS
 $display("DEEP_PASS %0d %0d %0d %0d",total,total_cycles,total_latency,peak);$finish;end endmodule'''
  for key,val in [('MAX_CYCLES_VALUE',c.max_cycles),('WIDTH_VALUE',c.width),('DEPTH_VALUE',c.depth),('K_VALUE',c.k),('LAST',len(flat)-1),('CALLS','\n'.join(calls))]:tb=tb.replace(key,str(val))
  (root/'candidate.sv').write_text(source);(root/'netlist.v').write_text((sd/'netlist.v').read_text())
  (root/'inputs.hex').write_text(''.join(f'{x:0128x}\n' for x,y in flat));(root/'expected.hex').write_text(''.join(f'{y:064x}\n' for x,y in flat))
  (root/'epochs.json').write_text(json.dumps([{k:v for k,v in e.items() if k!='pairs'}|{'count':len(e['pairs'])} for e in epochs],indent=2))
  answers=[]
  for label,file in [('rtl','candidate.sv'),('netlist','netlist.v')]:
   selected=tb if label=='rtl' else re.sub(r'candidate #\(.*?\)\) dut','candidate dut',tb)
   (root/'tb.sv').write_text(selected);(root/(label+'-tb.sv')).write_text(selected)
   command=[tool('iverilog')]
   if str(TOOLS) in command[0]:command+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
   run(command+['-g2012','-s','tb','-o',label+'.vvp',file,'tb.sv'],root,label+'-compile')
   log=run([tool('vvp'),label+'.vvp'],root,label+'-simulation',120)
   match=re.search(r'DEEP_PASS (\d+) (\d+) (\d+) (\d+)',log)
   if not match:raise Rejected('missing complete deep result')
   answers.append(tuple(map(int,match.groups())))
  if answers[0]!=answers[1]:raise Rejected('RTL/netlist disagreement')
  result.update(tested_correct=True,epochs=len(epochs),responses=answers[0][0],active_cycles=answers[0][1],offered_latency_sum=answers[0][2],maximum_offered_latency=answers[0][3])
 except (Rejected,OSError,ValueError) as e:result['error']=str(e)
 result['elapsed_s']=round(time.monotonic()-started,3);(root/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
