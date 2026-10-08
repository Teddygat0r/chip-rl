from pathlib import Path
import json,re
from ..evaluate import run,tool,TOOLS,Rejected,digest
from .oracles import PageTables

def simulate(c,source,netlist,work,root):
 root=Path(root);root.mkdir(parents=True,exist_ok=True)
 requests=[];expected=[];calls=[];pages=PageTables(work['seed']^0x789)
 for e in work['epochs']:
  base=len(requests)
  for r in e['requests']:
   requests.append(r['addr']|(r['aux']<<16))
   for g in range(4):
    data,fault=pages.translate(r['addr'],r['aux'],g) if c.name=='tlb' else (r['data'],0)
    expected.append(data|(fault<<32))
  calls.append(f"epoch({base},{len(e['requests'])},{e['generation']},{int(e['reset'])},{int(e['invalidate'])},{e['interrupt']},{e['inflight']},{e['probe']},{e.get('target_asid',-1)});")
 for name,xs,width in [('requests',requests,6),('expected',expected,9),('controls',work['controls'],2),('lines',work['lines'],32)]:
  (root/(name+'.hex')).write_text(''.join(f'{x:0{width}x}\n' for x in xs))
 tables=[table.get(a,0) for table in work['page_tables'] for a in range(65536)]
 (root/'pages.hex').write_text(''.join(f'{x:08x}\n' for x in tables))
 (root/'workload.json').write_text(json.dumps({k:v for k,v in work.items() if k not in ('lines','page_tables','controls')},indent=2))
 tb=r'''module tb;
 localparam ENTRIES=ENTRY_VALUE,IS_TLB=TLB_VALUE;
 reg clk=0,rst=1,req_valid=0,out_ready=0,mem_ready=0,resp_valid=0,inv_valid=0;
 reg [15:0] req_addr=0;reg [7:0] req_tag=0,req_aux=0;reg [1:0] inv_asid=0;reg [3:0] resp_tag=0;reg [127:0] resp_data=0;
 wire req_ready,out_valid,mem_valid,resp_ready;wire [7:0] out_tag;wire [31:0] out_data;wire [1:0] out_fault;wire [15:0] mem_addr;wire [3:0] mem_tag;
 candidate #(.ENTRIES(ENTRIES)) dut(.*);
 reg [23:0] requests[0:REQUEST_LAST];reg [33:0] expected[0:EXPECTED_LAST];
 reg [7:0] controls[0:CONTROL_LAST];reg [127:0] lines[0:16383];reg [31:0] pages[0:262143];
 reg pending[0:15];integer due[0:15];reg [127:0] payload[0:15];reg [15:0] address[0:15];
 reg accepted[0:255],completed[0:255],committed[0:255];integer offered_at[0:255],accepted_at[0:255];reg [33:0] committed_expected[0:255];
 integer generation[0:3];integer total=0,total_cycles=0,latency_sum=0,max_latency=0,reads=0,peak_pending=0,reordered=0,invalidations=0,canceled=0;
 reg took_response=0;reg held_out=0,held_mem=0;reg [41:0] old_out;reg [19:0] old_mem;
 integer sent,received,t,base_global,current_n,mem_serial;integer bus_total=0,cache_probes=0;integer issued_order[0:15];integer last_return;
 task cycle;input integer base,n;input score;integer j,k,count,lat,g;reg push,pop,issue,response;reg [33:0] want;begin
 #4;
 if(rst)begin
 if(req_ready!==0 || out_valid!==0 || mem_valid!==0 || resp_ready!==0)$fatal(1,"reset port contract");
 end else begin
 if(req_ready!==0 && req_ready!==1 || out_valid!==0 && out_valid!==1 || mem_valid!==0 && mem_valid!==1 || resp_ready!==0 && resp_ready!==1)$fatal(1,"unknown handshake");
 if(held_out && (!out_valid || {out_tag,out_fault,out_data}!==old_out))$fatal(1,"stalled output changed");
 if(held_mem && (!mem_valid || {mem_tag,mem_addr}!==old_mem))$fatal(1,"stalled memory request changed");
 end
 push=!rst && req_valid && req_ready;pop=!rst && out_valid && out_ready;issue=!rst && mem_valid && mem_ready;response=!rst && resp_valid && resp_ready;took_response=response;
 if(!rst && mem_valid && (^{mem_tag,mem_addr})===1'bx)$fatal(1,"unknown memory request");
 if(!rst && out_valid)begin
 if((^{out_tag,out_fault,out_data})===1'bx)$fatal(1,"unknown client response");
 if(out_tag>=n || !accepted[out_tag] || completed[out_tag])$fatal(1,"unknown/duplicate response tag");
 g=IS_TLB?generation[requests[base+out_tag][17:16]]:0;
 want=committed[out_tag]?committed_expected[out_tag]:expected[(base+out_tag)*4+g];
 if({out_fault,out_data}!==want)$fatal(1,"result mismatch tag=%0d actual=%h expected=%h t=%0d",out_tag,{out_fault,out_data},want,t);
 committed[out_tag]=1;committed_expected[out_tag]=want;
 if(t<=accepted_at[out_tag])$fatal(1,"minimum latency");
 end
 if(pop)begin
 completed[out_tag]=1;received=received+1;lat=t-offered_at[out_tag];
 if(score)begin total=total+1;latency_sum=latency_sum+lat;if(lat>max_latency)max_latency=lat;end
 end
 if(response)begin
 if(!pending[resp_tag])$fatal(1,"memory response accounting");
 if(issued_order[resp_tag]<last_return)reordered=reordered+1;
 last_return=issued_order[resp_tag];pending[resp_tag]=0;
 end
 if(issue)begin
 bus_total=bus_total+1;
 if((IS_TLB?mem_tag>=16:mem_tag>=ENTRIES) || pending[mem_tag] || mem_addr[1:0]!=0)$fatal(1,"memory tag reuse/alignment");
 if(sent==received && !push)$fatal(1,"memory request without client work");
 if(!IS_TLB)for(j=0;j<16;j=j+1)if(pending[j] && address[j]==mem_addr)$fatal(1,"duplicate concurrent line fetch");
 pending[mem_tag]=1;address[mem_tag]=mem_addr;issued_order[mem_tag]=mem_serial;mem_serial=mem_serial+1;
 // The initial burst deliberately leaves time to merge all four word requests.
 due[mem_tag]=t+(IS_TLB?5+(mem_addr%13):sent<16?80+mem_tag*7:3+(mem_addr%29));
 if(IS_TLB)begin
 if(mem_addr>=16'h8000 && mem_addr<16'h8400)k=(mem_addr>>8)&3;
 else if(mem_addr>=16'h1000 && mem_addr<16'h5000)k=(mem_addr>>12)-1;
 else $fatal(1,"read outside page tables");
 payload[mem_tag]={96'b0,pages[generation[k]*65536+mem_addr]};
 end else payload[mem_tag]=lines[mem_addr>>2];
 if(score)reads=reads+1;
 end
 if(push)begin
 if(accepted[req_tag] || req_tag>=n)$fatal(1,"input tag reuse");
 accepted[req_tag]=1;accepted_at[req_tag]=t;sent=sent+1;
 end
 for(j=0;j<n;j=j+1)if(accepted[j] && !completed[j] && t-accepted_at[j]>2048)$fatal(1,"per-request deadline");
 count=0;for(j=0;j<16;j=j+1)if(pending[j])count=count+1;if(count>peak_pending)peak_pending=count;
 held_out=!rst && out_valid && !out_ready;old_out={out_tag,out_fault,out_data};
 held_mem=!rst && mem_valid && !mem_ready;old_mem={mem_tag,mem_addr};
 #1;clk=1;#4;clk=0;#1;
 end endtask
 task reset_all;integer j;begin
 rst=1;req_valid=0;resp_valid=0;inv_valid=0;out_ready=0;mem_ready=0;held_out=0;held_mem=0;
 for(j=0;j<4;j=j+1)cycle(0,0,0);
 rst=0;
 for(j=0;j<16;j=j+1)pending[j]=0;
 for(j=0;j<256;j=j+1)begin accepted[j]=0;completed[j]=0;committed[j]=0;end
 end endtask
 task epoch;input integer base,n,gen,do_reset,do_inv,cut,inject_kind,probe,target_asid;
 integer j,k,selected,drain,injected,read_start;reg offering;begin
 sent=0;received=0;t=0;offering=0;injected=0;read_start=bus_total;mem_serial=0;last_return=-1;
 if(do_reset)reset_all();
 for(j=0;j<256;j=j+1)begin accepted[j]=0;completed[j]=0;committed[j]=0;end
 for(j=0;j<4;j=j+1)begin
 if(target_asid<0 || target_asid==j)generation[j]=gen;
 if(IS_TLB && do_inv && (target_asid<0 || target_asid==j))begin inv_valid=1;inv_asid=j;req_valid=0;resp_valid=0;out_ready=1;mem_ready=1;cycle(base,n,0);invalidations=invalidations+1;end
 end
 inv_valid=0;
 while((cut!=0?sent<cut:received<n) && t<MAX_CYCLES)begin
 if(!offering && sent<n && (controls[t][0] || t>MAX_CYCLES/2))begin offering=1;offered_at[sent]=t;end
 req_valid=offering;req_addr=sent<n?requests[base+sent][15:0]:0;req_aux=sent<n?requests[base+sent][23:16]:0;req_tag=sent;
 out_ready=controls[t][1] || t>MAX_CYCLES/2;mem_ready=controls[t][2] || t>MAX_CYCLES/2;
 if(!resp_valid)begin
 selected=-1;for(j=0;j<16;j=j+1)if(pending[j] && due[j]<=t)selected=j;
 if(selected>=0)begin resp_valid=1;resp_tag=selected;resp_data=payload[selected];end
 end
 inv_valid=0;
 if(IS_TLB && inject_kind!=0 && injected<3)begin
 for(j=0;j<16;j=j+1)if(pending[j] && ((inject_kind==1 && address[j]>=16'h8000) || (inject_kind==2 && address[j]<16'h8000)))begin
 inv_valid=1;inv_asid=address[j]>=16'h8000 ?((address[j]>>8)&3):((address[j]>>12)-1);
 end
 if(inject_kind==3 && out_valid && !out_ready)begin inv_valid=1;inv_asid=requests[base+out_tag][17:16];end
 end
 cycle(base,n,cut==0 && probe==0);
 if(inv_valid)begin generation[inv_asid]=(generation[inv_asid]+1)%4;invalidations=invalidations+1;injected=injected+1;end
 inv_valid=0;
 // Handshake values above were pre-edge; use the recorded accepted count.
 if(offering && sent>req_tag)offering=0;
 if(took_response)resp_valid=0;
 t=t+1;
 end
 if(cut!=0)begin if(sent!=cut)$fatal(1,"reset cancellation point unreachable");canceled=canceled+sent-received;end
 else begin
 if(IS_TLB && inject_kind!=0 && injected==0)$fatal(1,"missing in-flight invalidation");
 if(received!=n || sent!=n)$fatal(1,"completion deadline");
 if(probe==0)total_cycles=total_cycles+t;
 if(probe==2)begin if(bus_total!=read_start)$fatal(1,"minimum translation-cache capacity");cache_probes=cache_probes+1;end
 req_valid=0;resp_valid=0;out_ready=1;mem_ready=1;
 for(j=0;j<16;j=j+1)if(pending[j])$fatal(1,"unretired memory operation");
 for(drain=0;drain<20;drain=drain+1)begin cycle(base,n,0);t=t+1;end
 end
 end endtask
 initial begin
 $readmemh("requests.hex",requests);$readmemh("expected.hex",expected);$readmemh("controls.hex",controls);$readmemh("lines.hex",lines);$readmemh("pages.hex",pages);
 CALLS
 if(!IS_TLB && peak_pending<ENTRIES)$fatal(1,"minimum MSHR concurrency");
 if(IS_TLB && cache_probes!=1)$fatal(1,"translation-cache probe missing");
 if(canceled==0)$fatal(1,"missing interrupted reset coverage");
 $display("MEMORY_PASS %0d %0d %0d %0d %0d %0d %0d %0d",total,total_cycles,latency_sum,max_latency,reads,peak_pending,reordered,invalidations);$finish;
 end endmodule'''
 for key,val in [('ENTRY_VALUE',c.entries),('TLB_VALUE',int(c.name=='tlb')),('REQUEST_LAST',len(requests)-1),('EXPECTED_LAST',len(expected)-1),('CONTROL_LAST',len(work['controls'])-1),('MAX_CYCLES',c.max_cycles),('CALLS','\n'.join(calls))]:tb=tb.replace(key,str(val))
 (root/'candidate.sv').write_text(source);(root/'netlist.v').write_text(Path(netlist).read_text());results=[]
 for label,file in [('rtl','candidate.sv'),('netlist','netlist.v')]:
  selected=tb if label=='rtl' else tb.replace('candidate #(.ENTRIES(ENTRIES))','candidate')
  (root/'tb.sv').write_text(selected);(root/(label+'-tb.sv')).write_text(selected)
  cmd=[tool('iverilog')]
  if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
  run(cmd+['-g2012','-s','tb','-o',label+'.vvp',file,'tb.sv'],root,label+'-compile')
  output=run([tool('vvp'),label+'.vvp'],root,label+'-simulation')
  m=re.search(r'MEMORY_PASS((?: \d+){8})',output)
  if not m:raise Rejected('missing complete memory result')
  results.append(tuple(map(int,m.group(1).split())))
 if results[0]!=results[1]:raise Rejected('memory RTL/netlist disagreement')
 return dict(zip(('transactions','cycles','latency_sum','maximum_latency','memory_reads','peak_pending','out_of_order_returns','invalidations'),results[0]))|{'vectors_sha256':digest(''.join((root/(n+'.hex')).read_text() for n in ('requests','expected','controls','lines','pages')))}
