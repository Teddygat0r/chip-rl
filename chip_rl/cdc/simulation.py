"""A transaction scoreboard independent of the DUT's pointer implementation."""
from pathlib import Path
import json,re
from ..evaluate import tool,run,TOOLS,Rejected,digest

def simulate(c,source,netlist,epochs,root):
 root=Path(root);root.mkdir(parents=True,exist_ok=False);root.chmod(0o700)
 xs=[];controls=[];calls=[];meta=[]
 for e in epochs:
  calls.append(f"epoch({len(xs)},{len(e['inputs'])},{len(controls)},{e['cut']},{e['hold']},{int(e['score'])});")
  xs+=e['inputs'];controls+=e['controls'];meta.append({k:v for k,v in e.items() if k not in ('inputs','controls')})
 (root/'inputs.hex').write_text(''.join(f'{x:08x}\n' for x in xs));(root/'controls.hex').write_text(''.join(f'{x:02x}\n' for x in controls));(root/'epochs.json').write_text(json.dumps(meta,indent=2))
 tb='''module tb;
 localparam WIDTH=WIDTH_VALUE,DEPTH=DEPTH_VALUE,A=$clog2(DEPTH);
 reg wclk=0,rclk=0,wrst=1,rrst=1,w_valid=0,r_ready=0;reg [WIDTH-1:0] w_data=0;
 wire w_ready,r_valid;wire [WIDTH-1:0] r_data;
 candidate #(.WIDTH(WIDTH),.DEPTH(DEPTH)) dut(.*);
 reg [31:0] inputs[0:INPUT_LAST];reg [5:0] controls[0:CONTROL_LAST];integer accepted[0:INPUT_LAST];
 integer total=0,total_ticks=0,total_latency=0,peak=0,full_hits=0,empty_hits=0,coincident=0;
 reg held_active=0;reg [WIDTH-1:0] held;
 function [A:0] advance_gray;input [A:0] old;input take;reg [A:0] b;integer i;begin
 b=0;for(i=0;i<=A;i=i+1)b[i]=^(old>>i);b=b+take;advance_gray=(b>>1)^b;end endfunction
 task tick;input [5:0] flags;input valid,ready;input [WIDTH-1:0] payload;output wt,rt;output [WIDTH-1:0] observed;output offered,space;
 reg [A:0] oldw,oldr;begin
 wclk=0;rclk=0;wrst=flags[2];rrst=flags[3];w_valid=valid;r_ready=ready;w_data=payload;#4;
 if(wrst && w_ready!==0 || rrst && r_valid!==0)$fatal(1,"local reset port contract");
 if(!wrst && w_ready!==0 && w_ready!==1 || !rrst && r_valid!==0 && r_valid!==1)$fatal(1,"unknown handshake");
 wt=flags[0] && valid && w_ready && !wrst;rt=flags[1] && ready && r_valid && !rrst;observed=r_data;offered=r_valid && !rrst;space=w_ready && !wrst;
 if(held_active && !rrst && (r_valid!==1 || r_data!==held))$fatal(1,"stalled read changed");
 held_active=r_valid && !rt && !rrst;held=r_data;oldw=dut.wgray;oldr=dut.rgray;
 #1;wclk=flags[0];rclk=flags[1];#4;
 if(flags[0] && dut.wgray!==(wrst?0:advance_gray(oldw,wt)))$fatal(1,"write Gray increment/reset");
 if(flags[1] && dut.rgray!==(rrst?0:advance_gray(oldr,rt)))$fatal(1,"read Gray increment/reset");
 wclk=0;rclk=0;#1;
 end endtask
 task epoch;input integer base,n,control_base,cut,hold,score;
 integer sent,received,t,j,lat;reg offering,wt,rt,offered,space;reg [WIDTH-1:0] observed;reg [5:0] flags;reg saw_full,saw_empty;
 begin
 sent=0;received=0;t=0;offering=0;held_active=0;saw_full=0;saw_empty=0;
 while((cut!=0?sent<cut:received<n) && t<MAX_TICKS)begin
 flags=controls[control_base+t];if(flags[2] || flags[3])offering=0;else if(sent<n && flags[4])offering=1;
 tick(flags,offering,flags[5],sent<n?inputs[base+sent]:0,wt,rt,observed,offered,space);
 if(offered && received>=sent)$fatal(1,"empty advertised data");
 if(space && sent-received==DEPTH)$fatal(1,"full advertised space");
 if(rt)begin
 if(received>=sent)$fatal(1,"read without earlier write");
 if(observed!==inputs[base+received][WIDTH-1:0])$fatal(1,"FIFO ordering/data");
 lat=t-accepted[received];if(lat<1)$fatal(1,"crossing with zero delay");
 if(score)begin total=total+1;total_latency=total_latency+lat;if(lat>peak)peak=lat;end
 received=received+1;
 end
 if(wt)begin accepted[sent]=t;sent=sent+1;offering=0;end
 if(sent-received>DEPTH)$fatal(1,"FIFO capacity overflow");
 if(sent-received==DEPTH)saw_full=1;
 if(sent>0 && sent==received)saw_empty=1;
 if(flags[0] && flags[1] && !flags[2] && !flags[3])coincident=coincident+1;
 t=t+1;
 end
 if(cut!=0)begin
 if(sent!=cut)$fatal(1,"cancellation never reached");
 for(j=0;j<hold;j=j+1)tick(controls[control_base+t+j],0,0,0,wt,rt,observed,offered,space);
 end else begin
 if(sent!=n || received!=n)$fatal(1,"completion deadline");
 if(!saw_full || !saw_empty)$fatal(1,"missing full/empty coverage");
 full_hits=full_hits+1;empty_hits=empty_hits+1;
 for(j=0;j<80;j=j+1)begin tick(controls[control_base+t+j],0,1,0,wt,rt,observed,offered,space);if(rt)$fatal(1,"duplicate after drain");end
 if(score)total_ticks=total_ticks+t;
 end
 end endtask
 initial begin $readmemh("inputs.hex",inputs);$readmemh("controls.hex",controls);
 CALLS
 if(coincident==0)$fatal(1,"missing simultaneous clock edges");
 $display("CDC_PASS %0d %0d %0d %0d %0d %0d %0d",total,total_ticks,total_latency,peak,full_hits,empty_hits,coincident);$finish;
 end endmodule'''
 for key,val in [('WIDTH_VALUE',c.width),('DEPTH_VALUE',c.depth),('INPUT_LAST',len(xs)-1),('CONTROL_LAST',len(controls)-1),('MAX_TICKS',c.max_ticks),('CALLS','\n'.join(calls))]:tb=tb.replace(key,str(val))
 (root/'candidate.sv').write_text(source);(root/'netlist.v').write_text(Path(netlist).read_text());answers=[]
 for label,file in [('rtl','candidate.sv'),('netlist','netlist.v')]:
  selected=tb if label=='rtl' else tb.replace('candidate #(.WIDTH(WIDTH),.DEPTH(DEPTH))','candidate')
  (root/'tb.sv').write_text(selected);(root/(label+'-tb.sv')).write_text(selected)
  cmd=[tool('iverilog')]
  if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
  run(cmd+['-g2012','-s','tb','-o',label+'.vvp',file,'tb.sv'],root,label+'-compile')
  output=run([tool('vvp'),label+'.vvp'],root,label+'-simulation')
  match=re.search(r'CDC_PASS (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)',output)
  if not match:raise Rejected('missing complete CDC result')
  answers.append(tuple(map(int,match.groups())))
 if answers[0]!=answers[1]:raise Rejected('CDC RTL/netlist disagreement')
 values=answers[0]
 return dict(zip(('transactions','ticks','latency_sum','maximum_latency_ticks','full_epochs','empty_epochs','simultaneous_edges'),values))|{'vectors_sha256':digest((root/'inputs.hex').read_text()+(root/'controls.hex').read_text()),'epochs':len(epochs)}
