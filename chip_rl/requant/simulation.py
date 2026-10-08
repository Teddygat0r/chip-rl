from pathlib import Path
import re,json
from ..evaluate import run,tool,TOOLS,Rejected
from .oracle import check
def _simulate(n,source,netlist,w,root):
 root=Path(root);root.mkdir(parents=True,exist_ok=False)
 for name in ('inputs','masks','release','ready','idle','idle_masks'):(root/(name+'.hex')).write_text(''.join(f'{x:x}\n' for x in w[name]))
 (root/'workload.json').write_text(json.dumps(w['rows']));count=len(w['rows']);deadline=8*n+16;limit=w['limit']
 tb=r'''module tb;
 reg clk=0,rst=1,in_valid=0,out_ready=0;reg [191:0] in_data=0;reg [3:0] in_mask=0;
 wire in_ready,out_valid;wire [31:0] out_data;candidate #(.N(SHAPE)) dut(.*);
 reg [191:0] inputs[0:COUNT-1],idle_data[0:COUNT-1];reg [3:0] masks[0:COUNT-1],idle_masks[0:COUNT-1];
 integer releases[0:COUNT-1],accepted[0:COUNT-1];reg consumers[0:LIMIT-1];
 integer sent=0,received=0,t=0,latency=0,maxlat=0,lat,j;
 reg stalled=0;reg [31:0] held;reg push,pop;
 task edge_clock;begin #1;clk=1;#4;clk=0;#1;end endtask
 task reset_all;begin rst=1;in_valid=0;out_ready=0;stalled=0;
 repeat(1)begin #4;if(in_ready!==0 || out_valid!==0)$fatal(1,"reset ports");edge_clock;end rst=0;end endtask
 task single_reset;begin rst=1;in_valid=0;out_ready=0;stalled=0;
 #4;if(in_ready!==0 || out_valid!==0)$fatal(1,"single reset ports");edge_clock;rst=0;end endtask
 task accept_probe;begin out_ready=1;in_valid=1;#1;j=0;while(in_ready!==1 && j<DEADLINE)begin if(out_valid!==0)$fatal(1,"response before probe acceptance");#4;edge_clock;j=j+1;end
 if(in_ready!==1)$fatal(1,"probe acceptance");if(out_valid!==0)$fatal(1,"response before probe acceptance");#4;edge_clock;out_ready=0;in_valid=0;in_data=~in_data;in_mask=~in_mask;end endtask
 task poison_reset;input [191:0] data;input [3:0] mask;begin
 rst=1;in_valid=1;in_data=data;in_mask=mask;out_ready=1;stalled=0;
 #4;if(in_ready!==0 || out_valid!==0)$fatal(1,"poisoned reset ports");edge_clock;
 rst=0;in_valid=0;out_ready=1;end endtask
 task empty_drain;integer k;begin
 for(k=0;k<DEADLINE;k=k+1)begin #4;if(out_valid!==0)$fatal(1,"response survived cancellation");edge_clock;end
 end endtask
 task capacity_reset;input integer phase;integer k,taken;reg seen;reg [31:0] snapshot;begin
 if(phase==0)reset_all;in_data=inputs[1];in_mask=masks[1];accept_probe;taken=1;seen=0;
 in_data=inputs[1];in_mask=masks[1];in_valid=1;out_ready=0;
 for(k=0;k<2*DEADLINE;k=k+1)begin #4;
 if((in_ready!==0 && in_ready!==1)||(out_valid!==0 && out_valid!==1))$fatal(1,"capacity unknown handshake");
 if(seen && (out_valid!==1 || out_data!==snapshot))$fatal(1,"capacity stalled output changed");
 if(out_valid)begin if(^out_data===1'bx)$fatal(1,"capacity unknown output");seen=1;snapshot=out_data;end
 if(in_ready)taken=taken+1;edge_clock;end
 poison_reset({192{1'b1}},4'hf);empty_drain;
 $display("RESET_PROBE %0d %0d",phase,taken);
 end endtask
 task monitor;begin #4;
 if((in_ready!==0 && in_ready!==1)||(out_valid!==0 && out_valid!==1))$fatal(1,"unknown handshake");
 if(stalled && (out_valid!==1 || out_data!==held))$fatal(1,"stalled output changed");
 if(out_valid)begin if(received>=sent)$fatal(1,"unsolicited response");if(t<=accepted[received])$fatal(1,"minimum latency");if(t-accepted[received]>DEADLINE)$fatal(1,"response deadline");if(^out_data===1'bx)$fatal(1,"unknown output");end
 push=in_valid && in_ready;pop=out_valid && out_ready;
 if(push)begin accepted[sent]=t;sent=sent+1;end
 if(pop)begin $display("OUT %0d %h",received,out_data);lat=t-releases[received];latency=latency+lat;if(lat>maxlat)maxlat=lat;received=received+1;end
 for(j=received;j<sent;j=j+1)if(t-accepted[j]>DEADLINE)$fatal(1,"accepted deadline");
 stalled=out_valid && !out_ready;held=out_data;edge_clock;t=t+1;end endtask
 initial begin
 $readmemh("inputs.hex",inputs);$readmemh("masks.hex",masks);$readmemh("release.hex",releases);$readmemh("ready.hex",consumers);$readmemh("idle.hex",idle_data);$readmemh("idle_masks.hex",idle_masks);
 poison_reset({192{1'b1}},4'hf);empty_drain;
 poison_reset({96{2'b10}},4'h5);empty_drain;
 capacity_reset(0);
 reset_all;
 in_data=inputs[0];in_mask=masks[0];accept_probe;reset_all;
 in_data=inputs[2];in_mask=masks[2];accept_probe;repeat(2)begin #4;edge_clock;end reset_all;
 in_data=inputs[2];in_mask=masks[2];accept_probe;repeat(2*SHAPE+4)begin #4;edge_clock;end single_reset;
 in_data=inputs[1];in_mask=masks[1];accept_probe;j=0;
 while(out_valid!==1 && j<DEADLINE)begin #4;edge_clock;j=j+1;end
 if(out_valid!==1 || ^out_data===1'bx)$fatal(1,"stalled probe result");$display("CANCEL_RESULT %h",out_data);held=out_data;
 repeat(40)begin #4;if(out_valid!==1 || out_data!==held)$fatal(1,"long output stall");edge_clock;end reset_all;
 while(received<COUNT && t<LIMIT)begin
 in_valid=sent<COUNT && t>=releases[sent];in_data=in_valid?inputs[sent]:idle_data[t%COUNT];in_mask=in_valid?masks[sent]:idle_masks[t%COUNT];out_ready=consumers[t];monitor;
 end
 if(sent!=COUNT || received!=COUNT)$fatal(1,"completion deadline");
 $display("REQUANT_PASS %0d %0d %0d %0d",received,t,latency,maxlat);
 in_valid=0;out_ready=1;repeat(DEADLINE)monitor;
 // Repeat capacity-adaptive cancellation after the scored transaction count.
 capacity_reset(1);
 // Verify a fresh response and drain again.
 single_reset;in_data=inputs[1];in_mask=masks[1];accept_probe;j=0;
 while(out_valid!==1 && j<DEADLINE)begin #4;edge_clock;j=j+1;end
 if(out_valid!==1 || ^out_data===1'bx)$fatal(1,"post-counter reset response");
 $display("AFTER_RESET_RESULT %h",out_data);held=out_data;
 repeat(5)begin #4;if(out_valid!==1 || out_data!==held)$fatal(1,"post-reset stall");edge_clock;end
 out_ready=1;#4;edge_clock;repeat(DEADLINE)monitor;
 $display("DRAIN_PASS");$finish;
 end endmodule'''
 for key,value in [('SHAPE',n),('COUNT',count),('LIMIT',limit),('DEADLINE',deadline)]:tb=tb.replace(key,str(value))
 (root/'candidate.sv').write_text(source);(root/'netlist.v').write_bytes(Path(netlist).read_bytes());results=[]
 for stage,file in [('rtl','candidate.sv'),('mapped','netlist.v')]:
  selected=tb if stage=='rtl' else re.sub(r'candidate #\(\.N\(\d+\)\)','candidate',tb);(root/(stage+'-tb.sv')).write_text(selected)
  cmd=[tool('iverilog')]
  if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
  run(cmd+['-g2012','-s','tb','-o',stage+'.vvp',file,stage+'-tb.sv'],root,'requant-'+stage+'-compile',45)
  log=run([tool('vvp'),stage+'.vvp'],root,'requant-'+stage+'-simulation',45)
  outs,metrics,cancelled,after_reset=parse_trace(log,count,w['limit'])
  for value in (cancelled,after_reset):check(w['rows'][1],n,value)
  for i,row in enumerate(w['rows']):check(row,n,outs[i])
  (root/(stage+'-outputs.json')).write_text(json.dumps({'outputs':outs,'metrics':metrics},indent=2));results.append((outs,metrics))
 if results[0]!=results[1]:raise Rejected('RTL/mapped outputs or cycles differ')
 return results[0][1]|{'workload_sha256':w['sha256'],'reset_and_backpressure_checks':True,'mapped_checked':True}


simulate=_simulate

def parse_trace(log,count,limit):
 lines=log.splitlines();outs={};cancelled=None;after_reset=None;metrics=None;drain=False;finished=False;reset_pre=None;reset_post=None
 for line in lines:
  if re.fullmatch(r'RESET_PROBE 0 [0-9]+',line) and reset_pre is None and cancelled is None and not outs and metrics is None:
   reset_pre=int(line.split()[2])
   if not 1<=reset_pre<=97:raise Rejected('reset capacity count')
  elif re.fullmatch(r'RESET_PROBE 1 [0-9]+',line) and metrics is not None and reset_post is None and after_reset is None and not drain:
   reset_post=int(line.split()[2])
   if not 1<=reset_post<=97:raise Rejected('reset capacity count')
  elif re.fullmatch(r'CANCEL_RESULT [0-9a-f]{8}',line) and reset_pre is not None and cancelled is None and not outs and metrics is None:
   cancelled=int(line.split()[1],16)
  elif re.fullmatch(r'OUT [0-9]+ [0-9a-f]{8}',line) and cancelled is not None and metrics is None:
   _,index,value=line.split();index=int(index)
   if index!=len(outs) or index>=count:raise Rejected('duplicate/out-of-order output record')
   outs[index]=int(value,16)
  elif re.fullmatch(r'REQUANT_PASS(?: [0-9]+){4}',line) and metrics is None and len(outs)==count:
   values=list(map(int,line.split()[1:]));transactions,cycles,total,maximum=values
   if transactions!=count or not count+1<=cycles<=limit or not 1<=maximum<cycles or not maximum<=total<=count*maximum:raise Rejected('invalid simulation metrics')
   metrics=dict(zip(('transactions','cycles','latency_sum','maximum_offered_latency'),values))
  elif re.fullmatch(r'AFTER_RESET_RESULT [0-9a-f]{8}',line) and reset_post is not None and metrics is not None and after_reset is None and not drain:
   after_reset=int(line.split()[1],16)
  elif line=='DRAIN_PASS' and after_reset is not None and not drain:
   drain=True
  elif drain and not finished and re.fullmatch(r'(?:rtl|mapped)-tb\.sv:[0-9]+: \$finish called at [0-9]+ \([0-9a-z]+\)',line):
   finished=True
  else:raise Rejected('malformed/incomplete simulation record')
 if reset_pre is None or reset_post is None or cancelled is None or after_reset is None or not drain or metrics is None or len(outs)!=count:raise Rejected('incomplete requant simulation')
 metrics['reset_probe_acceptances']={'before':reset_pre,'after':reset_post}
 return outs,metrics,cancelled,after_reset
