"""Trusted, deterministic RTL and mapped replay against an external integer oracle."""
from pathlib import Path
import json,re
from ..evaluate import run,tool,TOOLS,Rejected

TB=r'''module tb;
reg clk=0,rst=0,in_valid=0,out_ready=0;reg [511:0] in_data=0;
wire in_ready,out_valid;wire [255:0] out_data;
candidate INSTANTIATION dut(.*);
reg [511:0] inputs[0:COUNT-1];reg [255:0] expected[0:COUNT-1];
integer release_time[0:COUNT-1];reg consumer[0:LIMIT-1];
integer accepted[0:COUNT-1],service_age[0:COUNT-1];integer sent=0,received=0,t=0,j,waited;
integer first_seen[0:COUNT-1];integer first_sum=0,max_first=0,offered_sum=0,max_offered=0,delay;
integer raw_sum=0,max_raw=0,service_sum=0,max_service=0;
integer ready_low=0,output_blocked=0,input_blocked=0;
integer long_seen=0,reset_seen=0;
integer sat_sent=0,sat_received=0,sat_t=0,sat_first=-1,sat_last=-1;
reg stalled=0;reg [255:0] held=0;reg push,pop;
task tick;begin #1;clk=1;#2;clk=0;#1;end endtask
task reset_edge;input ready_setting;begin rst=1;in_valid=1;in_data={512{1'b1}};out_ready=ready_setting;
 #2;if(in_ready!==0 || out_valid!==0)$fatal(1,"reset handshake exposed");tick;
 rst=0;in_valid=0;out_ready=1;stalled=0;end endtask
task drain;input integer count;integer d;begin
 for(d=0;d<count;d=d+1)begin #2;if(out_valid!==0)$fatal(1,"canceled or duplicate response");tick;end
 end endtask
initial begin
 $readmemh("inputs.hex",inputs);$readmemh("expected.hex",expected);
 $readmemh("release.hex",release_time);$readmemh("ready.hex",consumer);
 reset_edge(1'b1);drain(DEADLINE);
 // Accept a command, then cancel while it is in flight or stalled.
 in_data=inputs[0];in_valid=1;out_ready=1;waited=0;
 #2;while(in_ready!==1 && waited<DEADLINE)begin tick;#2;waited=waited+1;end
 if(in_ready!==1 || out_valid!==0)$fatal(1,"probe acceptance");tick;
 in_valid=1;in_data=inputs[1];out_ready=0;
 for(j=0;j<DEADLINE+4;j=j+1)begin #2;
 if((in_ready!==0 && in_ready!==1)||(out_valid!==0 && out_valid!==1))$fatal(1,"unknown probe handshake");
 if(stalled && (out_valid!==1 || out_data!==held))$fatal(1,"probe stalled output changed");
 stalled=out_valid;held=out_data;tick;end
 reset_edge(1'b1);drain(DEADLINE);
 // Fresh response after cancellation, including a prolonged output stall.
 in_data=inputs[0];in_valid=1;out_ready=0;waited=0;
 #2;while(in_ready!==1 && waited<DEADLINE)begin tick;#2;waited=waited+1;end
 if(in_ready!==1)$fatal(1,"post-reset acceptance");tick;in_valid=0;waited=0;
 #2;while(out_valid!==1 && waited<DEADLINE)begin tick;#2;waited=waited+1;end
 if(out_valid!==1 || out_data!==expected[0])$fatal(1,"post-reset functional result");
 held=out_data;
 for(j=0;j<24;j=j+1)begin #2;if(out_valid!==1 || out_data!==held)$fatal(1,"long output stall");tick;end
 out_ready=1;#2;tick;drain(DEADLINE);reset_edge(1'b1);
 // An accepted response remains correct and stable through a 257-cycle
 // consumer stall, then the interface recovers and accepts fresh work.
 in_data=inputs[2];in_valid=1;out_ready=0;#2;
 if(in_ready!==1)$fatal(1,"long-stall acceptance");tick;in_valid=0;stalled=0;
 for(j=0;j<257;j=j+1)begin #2;
 if((in_ready!==0 && in_ready!==1)||(out_valid!==0 && out_valid!==1))$fatal(1,"long-stall unknown handshake");
 if(stalled && (out_valid!==1 || out_data!==held))$fatal(1,"long-stall output changed");
 if(out_valid && out_data!==expected[2])$fatal(1,"long-stall wrong output");
 if(out_valid)long_seen=1;
 stalled=out_valid;held=out_data;tick;end
 out_ready=1;waited=0;#2;
 while(out_valid!==1 && waited<DEADLINE)begin tick;#2;waited=waited+1;end
 if(out_valid!==1 || out_data!==expected[2])$fatal(1,"long-stall recovery output");
 tick;in_data=inputs[3];in_valid=1;#2;
 if(in_ready!==1)$fatal(1,"long-stall recovery acceptance");tick;in_valid=0;waited=0;
 #2;while(out_valid!==1 && waited<DEADLINE)begin tick;#2;waited=waited+1;end
 if(out_valid!==1 || out_data!==expected[3])$fatal(1,"long-stall recovery result");
 tick;drain(DEADLINE);$display("LONG_STALL_PASS 257 %0d",long_seen);reset_edge(1'b1);
 // Reset while an output is blocked cancels it. New work must be unaffected.
 in_data=inputs[4];in_valid=1;out_ready=0;#2;
 if(in_ready!==1)$fatal(1,"reset-stall acceptance");tick;in_valid=0;stalled=0;
 for(j=0;j<RESET_WINDOW;j=j+1)begin #2;
 if((in_ready!==0 && in_ready!==1)||(out_valid!==0 && out_valid!==1))$fatal(1,"reset-stall unknown handshake");
 if(stalled && (out_valid!==1 || out_data!==held))$fatal(1,"reset-stall changed");
 if(out_valid)begin if(out_data!==expected[4])$fatal(1,"reset-stall result");reset_seen=1;end
 stalled=out_valid;held=out_data;tick;end
 reset_edge(1'b0);drain(DEADLINE);
 in_data=inputs[5];in_valid=1;out_ready=1;#2;
 if(in_ready!==1)$fatal(1,"fresh-after-reset acceptance");tick;in_valid=0;waited=0;
 #2;while(out_valid!==1 && waited<DEADLINE)begin tick;#2;waited=waited+1;end
 if(out_valid!==1 || out_data!==expected[5])$fatal(1,"fresh-after-reset result");
 tick;drain(DEADLINE);$display("RESET_STALL_PASS %0d",reset_seen);reset_edge(1'b1);
 // Scored schedule. The producer holds each offered item until accepted.
 for(j=0;j<COUNT;j=j+1)first_seen[j]=-1;
 while(received<COUNT && t<LIMIT)begin
 in_valid=sent<COUNT && t>=release_time[sent];
 if(sent<COUNT)in_data=inputs[sent];out_ready=consumer[t];#2;
 if((in_ready!==0 && in_ready!==1)||(out_valid!==0 && out_valid!==1))$fatal(1,"unknown handshake");
 if(stalled && (out_valid!==1 || out_data!==held))$fatal(1,"stalled output changed");
 if(!out_ready)ready_low=ready_low+1;
 if(out_valid && !out_ready)output_blocked=output_blocked+1;
 if(in_valid && !in_ready)input_blocked=input_blocked+1;
 if(out_valid)begin
 if(received>=sent)$fatal(1,"unsolicited response");
 if(t<=accepted[received])$fatal(1,"unregistered response");
 if(out_data!==expected[received])$fatal(1,"functional mismatch");
 if(first_seen[received]<0)begin
  first_seen[received]=t;delay=t-accepted[received];first_sum=first_sum+delay;
  if(delay>max_first)max_first=delay;end
 end
 push=in_valid && in_ready;pop=out_valid && out_ready;
 // Count only ready-high edges strictly after acceptance. Consumption's
 // ready-high edge is included. No raw-wall-clock age is a correctness gate.
 for(j=received;j<sent;j=j+1)begin
  if(out_ready)service_age[j]=service_age[j]+1;
  if(service_age[j]>DEADLINE)$fatal(1,"service opportunity timeout");end
 if(push)begin accepted[sent]=t;service_age[sent]=0;sent=sent+1;end
 if(pop)begin $display("OUT %0d %064h",received,out_data);
 delay=t-release_time[received];offered_sum=offered_sum+delay;
 if(delay>max_offered)max_offered=delay;
 delay=t-accepted[received];raw_sum=raw_sum+delay;
 if(delay>max_raw)max_raw=delay;
 service_sum=service_sum+service_age[received];
 if(service_age[received]>max_service)max_service=service_age[received];
 received=received+1;end
 stalled=out_valid && !out_ready;held=out_data;tick;t=t+1;
 end
 if(sent!=COUNT || received!=COUNT)$fatal(1,"completion timeout");
 $display("SCORED_PASS %0d %0d %0d %0d %0d %0d",received,t,first_sum,max_first,offered_sum,max_offered);
 $display("COUNTERS %0d %0d %0d %0d %0d %0d %0d %0d %0d",sent,received,ready_low,output_blocked,input_blocked,raw_sum,max_raw,service_sum,max_service);
 in_valid=0;out_ready=1;drain(DEADLINE);reset_edge(1'b1);
 // Separate saturated stream with an always-ready consumer.
 while(sat_received<32 && sat_t<SAT_LIMIT)begin
 in_valid=sat_sent<32;if(sat_sent<32)in_data=inputs[sat_sent];out_ready=1;#2;
 if((in_ready!==0 && in_ready!==1)||(out_valid!==0 && out_valid!==1))$fatal(1,"unknown saturation handshake");
 if(out_valid)begin
 if(sat_received>=sat_sent || out_data!==expected[sat_received])$fatal(1,"saturation result");end
 push=in_valid && in_ready;pop=out_valid;
 if(push)begin if(sat_first<0)sat_first=sat_t;sat_last=sat_t;sat_sent=sat_sent+1;end
 if(pop)sat_received=sat_received+1;
 tick;sat_t=sat_t+1;end
 if(sat_sent!=32 || sat_received!=32 || sat_last<=sat_first)$fatal(1,"saturation timeout");
 $display("SAT_PASS %0d %0d %0d %0d",sat_received,sat_t,sat_first,sat_last);
 in_valid=0;out_ready=1;drain(DEADLINE);
 $display("BLOCK_QUANT_PASS");$finish;
end endmodule'''

def parse_trace(log,count,limit,service_bound):
 lines=log.splitlines();outs=[];scored=None;counters=None;sat=None;done=False;long_stall=None;reset_stall=None
 for line in lines:
  m=re.fullmatch(r'LONG_STALL_PASS 257 ([01])',line)
  if m and long_stall is None and reset_stall is None and not outs:
   long_stall=bool(int(m[1]));continue
  m=re.fullmatch(r'RESET_STALL_PASS ([01])',line)
  if m and long_stall is not None and reset_stall is None and not outs:
   reset_stall=bool(int(m[1]));continue
  m=re.fullmatch(r'OUT (\d+) ([0-9a-f]{64})',line)
  if m and reset_stall is not None and scored is None:
   if int(m[1])!=len(outs) or len(outs)>=count:raise Rejected('out-of-order trace')
   outs.append(int(m[2],16));continue
  m=re.fullmatch(r'SCORED_PASS((?: \d+){6})',line)
  if m and reset_stall is not None and scored is None and len(outs)==count:
   n,cycles,first_sum,max_first,offered_sum,max_offered=map(int,m[1].split())
   if n!=count or cycles>limit or not 1<=max_first<=first_sum or not max_first<=offered_sum or max_offered>offered_sum:raise Rejected('invalid scored metrics')
   scored={'transactions':n,'workload_cycles':cycles,'accepted_to_first_sum':first_sum,'maximum_accepted_to_first':max_first,'offered_to_consumption_sum':offered_sum,'maximum_offered_to_consumption':max_offered};continue
  m=re.fullmatch(r'COUNTERS((?: \d+){9})',line)
  if m and scored is not None and counters is None and sat is None:
   accepted_count,consumed_count,ready_low,output_blocked,input_blocked,raw_sum,max_raw,service_sum,max_service=map(int,m[1].split())
   if accepted_count!=count or consumed_count!=count or not 0<=output_blocked<=ready_low<=scored['workload_cycles'] or not 0<=input_blocked<=scored['workload_cycles']:raise Rejected('invalid direct counters')
   if not scored['accepted_to_first_sum']<=raw_sum<=count*max_raw or not scored['maximum_accepted_to_first']<=max_raw<=scored['workload_cycles']:raise Rejected('invalid raw age')
   if not count<=service_sum<=count*max_service or not 1<=max_service<=service_bound or service_sum>raw_sum:raise Rejected('invalid service age')
   counters={'accepted_count':accepted_count,'consumed_count':consumed_count,'ready_low_cycles':ready_low,'output_blocked_cycles':output_blocked,'input_blocked_cycles':input_blocked,
    'accepted_to_consumption_sum':raw_sum,'maximum_accepted_to_consumption':max_raw,'service_opportunity_age_sum':service_sum,'maximum_service_opportunity_age':max_service};continue
  m=re.fullmatch(r'SAT_PASS((?: \d+){4})',line)
  if m and counters is not None and sat is None:
   n,cycles,first,last=map(int,m[1].split())
   if n!=32 or first<0 or last<=first or cycles<last or cycles>32*64:raise Rejected('invalid saturated metrics')
   sat={'stream_transactions':n,'stream_cycles':cycles,'stream_first_accept':first,'stream_last_accept':last,'stream_ii_numerator':last-first,'stream_ii_denominator':31};continue
  if line=='BLOCK_QUANT_PASS' and sat is not None and not done:done=True;continue
  if done and re.fullmatch(r'(?:rtl|mapped)-tb\.sv:\d+: \$finish called at \d+ \([0-9a-z]+\)',line):continue
  raise Rejected('malformed simulation record')
 if not done or scored is None or counters is None or sat is None or long_stall is None or reset_stall is None:raise Rejected('incomplete simulation')
 return outs,scored|counters|sat|{'long_stall_output_seen':long_stall,'reset_blocked_output_seen':reset_stall}

def simulate(n,source,netlist,w,root):
 root=Path(root);root.mkdir(parents=True,exist_ok=False)
 count=len(w['inputs']);deadline=2*n+64
 for name,values in [('inputs',w['inputs']),('expected',w['expected']),('release',w['release']),('ready',w['ready'])]:
  (root/(name+'.hex')).write_text(''.join(f'{v:x}\n' for v in values))
 (root/'private-workload.json').write_text(json.dumps({'seed':w['seed'],'split':w['split'],'labels':w['labels'],'sha256':w['sha256'],'watchdog_sha256':w['watchdog_sha256'],'last_release':w['last_release'],'watchdog_service_budget':w['watchdog_service_budget']}))
 (root/'candidate.sv').write_text(source);(root/'netlist.v').write_bytes(Path(netlist).read_bytes())
 replacement={'COUNT':count,'LIMIT':w['limit'],'DEADLINE':deadline,
              'RESET_WINDOW':2*n+16,'SAT_LIMIT':32*(2*n+10)+100}
 template=TB
 for key,value in replacement.items():template=re.sub(r'\b'+key+r'\b',str(value),template)
 records=[]
 for stage,file in [('rtl','candidate.sv'),('mapped','netlist.v')]:
  tb=template.replace('INSTANTIATION',f'#(.N({n}))' if stage=='rtl' else '')
  (root/(stage+'-tb.sv')).write_text(tb)
  cmd=[tool('iverilog')]
  if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
  run(cmd+['-g2012','-s','tb','-o',stage+'.vvp',file,stage+'-tb.sv'],root,'block-quant-'+stage+'-compile',45)
  log=run([tool('vvp'),stage+'.vvp'],root,'block-quant-'+stage+'-simulation',90)
  outputs,metrics=parse_trace(log,count,w['limit'],deadline)
  if outputs!=w['expected']:raise Rejected('oracle output mismatch')
  records.append((outputs,metrics))
 if records[0]!=records[1]:raise Rejected('RTL/mapped divergence')
 return records[0][1]|{'workload_sha256':w['sha256'],'watchdog_sha256':w['watchdog_sha256'],'watchdog_cycles':w['limit'],
  'service_opportunity_bound':deadline,'rtl_mapped_checked':True,'reset_backpressure_checked':True,'long_stall_checked':True,'reset_during_stall_checked':True}
