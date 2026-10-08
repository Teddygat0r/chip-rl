from pathlib import Path
import json,re,random
from ..evaluate import run,tool,TOOLS,Rejected,digest

def simulate(c,source,netlist,w,root):
 root=Path(root);root.mkdir(parents=True,exist_ok=True)
 w=dict(w);rng=random.Random(w['seed']^0x15A71);w['idle']=[rng.getrandbits(1024) for _ in range(len(w['inputs']))]
 for name,width in [('inputs',256),('expected',96),('release',8),('ready',1),('idle',256)]:
  (root/(name+'.hex')).write_text(''.join(f'{x:0{width}x}\n' for x in w[name]))
 tb=r'''module tb;
 reg clk=0,rst=1,in_valid=0,out_ready=0;reg [1023:0] in_data=0;
 wire in_ready,out_valid;wire [383:0] out_data;
 candidate #(.M(M_VALUE),.N(N_VALUE),.K(K_VALUE)) dut(.*);
 reg [1023:0] inputs[0:COUNT-1];reg [383:0] expected[0:COUNT-1];integer releases[0:COUNT-1],accepted[0:COUNT-1];reg consumers[0:LIMIT-1];reg [1023:0] idle_data[0:COUNT-1];
 integer sent=0,received=0,t=0,latency=0,maxlat=0,lat,j;
 reg stalled=0;reg [383:0] held;reg push,pop;
 task edge_clock;begin #1;clk=1;#4;clk=0;#1;end endtask
 task reset_all;begin
 rst=1;in_valid=0;out_ready=0;stalled=0;
 repeat(3)begin #4;if(in_ready!==0 || out_valid!==0)$fatal(1,"reset ports");edge_clock();end
 rst=0;
 end endtask
 task check;begin
 #4;
 if((in_ready!==0 && in_ready!==1)||(out_valid!==0 && out_valid!==1))$fatal(1,"unknown handshake");
 if(stalled && (out_valid!==1 || out_data!==held))$fatal(1,"stalled output changed");
 if(out_valid)begin
 if(received>=sent)$fatal(1,"unsolicited response");
 if(t<=accepted[received])$fatal(1,"minimum latency");
 if(out_data!==expected[received])$fatal(1,"functional mismatch at %0d",received);
 end
 push=in_valid && in_ready;pop=out_valid && out_ready;
 if(push)begin accepted[sent]=t;sent=sent+1;end
 if(pop)begin lat=t-releases[received];latency=latency+lat;if(lat>maxlat)maxlat=lat;received=received+1;end
 for(j=received;j<sent;j=j+1)if(t-accepted[j]>256)$fatal(1,"accepted deadline");
 stalled=out_valid && !out_ready;held=out_data;edge_clock();t=t+1;
 end endtask
 initial begin
 $readmemh("inputs.hex",inputs);$readmemh("expected.hex",expected);$readmemh("release.hex",releases);$readmemh("ready.hex",consumers);$readmemh("idle.hex",idle_data);
 reset_all();
 // Cancel a command immediately after acceptance, before any response can retire.
 in_valid=1;in_data=inputs[0];out_ready=0;#1;
 j=0;while(!in_ready && j<LIMIT)begin #4;edge_clock();j=j+1;end
 if(!in_ready)$fatal(1,"reset acceptance unreachable");#4;edge_clock();reset_all();
 // Also cancel a datapath after two internal work cycles.
 in_valid=1;in_data=inputs[2];out_ready=0;#1;
 j=0;while(!in_ready && j<LIMIT)begin #4;edge_clock();j=j+1;end
 if(!in_ready)$fatal(1,"partial reset acceptance deadline");#4;edge_clock();in_valid=0;
 repeat(2)begin #4;edge_clock();end reset_all();
 // Cancel a completed, stalled response too.
 in_valid=1;in_data=inputs[1];out_ready=0;#1;
 j=0;while(!in_ready && j<LIMIT)begin #4;edge_clock();j=j+1;end
 if(!in_ready)$fatal(1,"post-reset acceptance deadline");#4;edge_clock();in_valid=0;
 j=0;while(!out_valid && j<256)begin #4;edge_clock();j=j+1;end
 if(!out_valid)$fatal(1,"reset output point unreachable");
 held=out_data;if(held!==expected[1])$fatal(1,"pre-reset result mismatch");
 repeat(40)begin #4;if(out_valid!==1 || out_data!==held)$fatal(1,"long stalled response changed");edge_clock();end
 reset_all();
 while(received<COUNT && t<LIMIT)begin
 in_valid=sent<COUNT && t>=releases[sent];in_data=in_valid?inputs[sent]:idle_data[t%COUNT];out_ready=consumers[t];check();
 end
 if(sent!=COUNT || received!=COUNT)$fatal(1,"completion deadline");
 $display("QUALITY_PASS %0d %0d %0d %0d",received,t,latency,maxlat);
 in_valid=0;out_ready=1;repeat(256)check();$display("DRAIN_PASS");$finish;
 end endmodule'''
 for k,v in [('M_VALUE',c.m),('N_VALUE',c.n),('K_VALUE',c.k),('COUNT',len(w['inputs'])),('LIMIT',c.max_cycles)]:tb=tb.replace(k,str(v))
 (root/'candidate.sv').write_text(source);(root/'netlist.v').write_text(Path(netlist).read_text());results=[]
 for label,file in [('rtl','candidate.sv'),('netlist','netlist.v')]:
  selected=tb if label=='rtl' else re.sub(r'candidate #\(\.M\(\d+\),\.N\(\d+\),\.K\(\d+\)\)', 'candidate',tb)
  (root/(label+'-tb.sv')).write_text(selected)
  cmd=[tool('iverilog')]
  if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
  run(cmd+['-g2012','-s','tb','-o',label+'.vvp',file,label+'-tb.sv'],root,label+'-compile')
  out=run([tool('vvp'),label+'.vvp'],root,label+'-simulation');m=re.search(r'QUALITY_PASS((?: \d+){4})',out)
  if not m or 'DRAIN_PASS' not in out:raise Rejected('missing complete arithmetic result')
  results.append(tuple(map(int,m.group(1).split())))
 if results[0]!=results[1]:raise Rejected('arithmetic RTL/netlist disagreement')
 return dict(zip(('transactions','cycles','latency_sum','maximum_latency'),results[0]))|{'vectors_sha256':digest(''.join((root/(n+'.hex')).read_text() for n in ('inputs','expected','release','ready','idle')))}
