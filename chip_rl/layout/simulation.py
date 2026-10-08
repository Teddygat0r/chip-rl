import json,shutil
from pathlib import Path
from ..evaluate import run,tool,Rejected,TOOLS,digest
from .workloads import validate_mapping,oracle

def simulate_files(root,files):
 cmd=[tool('iverilog')]
 if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
 run(cmd+['-g2012','-s','tb','-o','simulation.vvp',*files],root,'layout-compile',30)
 return run([tool('vvp'),'simulation.vvp'],root,'layout-simulation',30)

def mapping(s,source,netlist,root):
 root=Path(root);root.mkdir(parents=True,exist_ok=False);tables=[]
 for stage in ('rtl','mapped'):
  p=root/stage;p.mkdir();(p/'candidate.sv').write_text(source if stage=='rtl' else Path(netlist).read_text())
  params=f'#(.ROWS({s.rows}),.COLS({s.cols}),.BANKS({s.banks}))' if stage=='rtl' else ''
  (p/'tb.sv').write_text(f'''module tb;reg [5:0] row,col;wire [9:0] addr;candidate {params} probe(.*);integer i,j;
 initial begin for(j=0;j<2;j=j+1)for(i=0;i<{s.words};i=i+1)begin
 row=(j==0?i:{s.words}-1-i)/{s.cols};col=(j==0?i:{s.words}-1-i)%{s.cols};#1;
 if(^addr===1'bx)$fatal(1,"unknown mapping");$display("MAP %0d %0d",row*{s.cols}+col,addr);end $display("PASS");$finish;end endmodule''')
  log=simulate_files(p,['candidate.sv','tb.sv']);table={};seen=0
  for line in log.splitlines():
   if line.startswith('MAP '):
    _,idx,value=line.split();idx=int(idx);value=int(value)
    if idx in table and table[idx]!=value:raise Rejected('history-dependent map')
    table[idx]=value;seen+=1
  if 'PASS' not in log or seen!=2*s.words or sorted(table)!=list(range(s.words)):raise Rejected('incomplete mapping')
  values=[table[i] for i in range(s.words)];validate_mapping(s,values);tables.append(values)
 if tables[0]!=tables[1]:raise Rejected('RTL/synthesis map divergence')
 (root/'mapping.json').write_text(json.dumps(tables[0]));return tables[0]

def pack(xs,width):return sum(x<<(i*width) for i,x in enumerate(xs))
def workload(s,source,netlist,table,requests,root,*,engine_source=None):
 root=Path(root);root.mkdir(parents=True,exist_ok=False);expected=oracle(s,table,requests);n=len(requests);metrics=[]
 (root/'requests.json').write_text(json.dumps(requests));(root/'oracle.json').write_text(json.dumps(expected));
 fields={'rows':(6*s.lanes,[pack([x[0] for x in q['coords']],6) for q in requests]),'cols':(6*s.lanes,[pack([x[1] for x in q['coords']],6) for q in requests]),'masks':(s.lanes,[q['mask'] for q in requests]),'writes':(1,[int(q['write']) for q in requests]),'values':(32*s.lanes,[pack(q['values'],32) for q in requests]),'expected':(32*s.lanes,[pack(x['expected'],32) for x in expected]),'cycles':(32,[x['service_cycles'] for x in expected]),'stalls':(32,[q['stall'] for q in requests]),'resets':(1,[int(q['reset_before']) for q in requests])}
 for stage in ('rtl','mapped'):
  p=root/stage;p.mkdir();(p/'candidate.sv').write_text(source if stage=='rtl' else Path(netlist).read_text());engine=engine_source if engine_source is not None else Path(__file__).with_name('engine.sv').read_text()
  if stage=='mapped':engine=engine.replace('#(.ROWS(ROWS),.COLS(COLS),.BANKS(BANKS))','')
  (p/'engine.sv').write_text(engine)
  declarations=[];loads=[]
  for name,(width,values) in fields.items():
   (p/(name+'.hex')).write_text(''.join(f'{v:x}\n' for v in values));declarations.append(f'reg [{width-1}:0] v_{name}[0:{n-1}];');loads.append(f'$readmemh("{name}.hex",v_{name});')
  tb=f'''module tb;localparam LANES={s.lanes};reg clk=0,rst=1,req_valid=0,out_ready=0,write_req=0;
 reg [6*LANES-1:0] rows,cols;reg [LANES-1:0] mask=0;reg [32*LANES-1:0] values=0;
 wire in_ready,out_valid;wire [32*LANES-1:0] out_data;
 bank_engine #(.ROWS({s.rows}),.COLS({s.cols}),.BANKS({s.banks}),.LANES(LANES)) fixed_engine(.*);
 {''.join(declarations)}
 integer i,j,elapsed,total=0,wall=0,responses=0;reg [32*LANES-1:0] held;
 task tick;begin #5;clk=1;#5;clk=0;wall=wall+1;end endtask
 initial begin {''.join(loads)} tick;rst=0;#1;
 for(i=0;i<{n};i=i+1)begin
 if(v_resets[i])begin rst=1;req_valid=0;tick;rst=0;#1;end
 if(in_ready!==1 || out_valid!==0)$fatal(1,"unexpected engine state");
 rows=v_rows[i];cols=v_cols[i];mask=v_masks[i];values=v_values[i];write_req=v_writes[i];req_valid=1;
 tick;req_valid=0;elapsed=0;
 // Deliberately change unaccepted inputs while work is outstanding.
 rows=~v_rows[i];cols=~v_cols[i];mask=~v_masks[i];values=~v_values[i];write_req=~v_writes[i];
 while(out_valid!==1 && elapsed<LANES+2)begin tick;elapsed=elapsed+1;end
 if(out_valid!==1 || elapsed!=v_cycles[i])$fatal(1,"service mismatch request %0d got %0d expected %0d",i,elapsed,v_cycles[i]);
 if(out_data!==v_expected[i])$fatal(1,"logical memory mismatch request %0d",i);
 total=total+elapsed;held=out_data;
 for(j=0;j<v_stalls[i];j=j+1)begin tick;if(out_valid!==1 || out_data!==held || in_ready!==0)$fatal(1,"stall instability");end
 out_ready=1;tick;out_ready=0;responses=responses+1;
 end
 repeat(4)begin tick;if(out_valid!==0)$fatal(1,"duplicate response");end
 $display("PASS %0d %0d %0d",responses,total,wall);$finish;end endmodule'''
  (p/'tb.sv').write_text(tb);log=simulate_files(p,['candidate.sv','engine.sv','tb.sv']);lines=[x for x in log.splitlines() if x.startswith('PASS ')]
  if len(lines)!=1:raise Rejected('no workload completion')
  _,nr,cy,wall=lines[0].split();r={'requests':int(nr),'service_cycles':int(cy),'wall_cycles':int(wall)}
  if r['requests']!=n or r['service_cycles']!=sum(x['service_cycles'] for x in expected):raise Rejected('workload accounting')
  metrics.append(r)
 if metrics[0]!=metrics[1]:raise Rejected('RTL/mapped service divergence')
 return metrics[0]|{'active_lane_operations':sum(q['mask'].bit_count() for q in requests),'workload_sha256':digest(json.dumps(requests,sort_keys=True)),'mapping_sha256':digest(json.dumps(table)),'rtl_and_mapped':True}

def reset_cancellation(s,source,netlist,root,*,engine_source=None):
 """Host-only directed cancellation check; candidate API cannot supply engine_source."""
 root=Path(root);root.mkdir(parents=True,exist_ok=False);results=[]
 for stage in ('rtl','mapped'):
  p=root/stage;p.mkdir();(p/'candidate.sv').write_text(source if stage=='rtl' else Path(netlist).read_text())
  engine=engine_source if engine_source is not None else Path(__file__).with_name('engine.sv').read_text()
  if stage=='mapped':engine=engine.replace('#(.ROWS(ROWS),.COLS(COLS),.BANKS(BANKS))','')
  (p/'engine.sv').write_text(engine)
  (p/'tb.sv').write_text(f'''module tb;localparam LANES={s.lanes};reg clk=0,rst=1,req_valid=0,out_ready=0,write_req=0;
 reg [6*LANES-1:0] rows,cols;reg [LANES-1:0] mask={{LANES{{1'b1}}}};reg [32*LANES-1:0] values=0;
 wire in_ready,out_valid;wire [32*LANES-1:0] out_data;
 bank_engine #(.ROWS({s.rows}),.COLS({s.cols}),.BANKS({s.banks}),.LANES(LANES)) fixed_engine(.*);
 integer i,n,phase;task tick;begin #5;clk=1;#5;clk=0;end endtask
 task reset_now;begin rst=1;req_valid=1;write_req=1;values=~0;tick;rst=0;req_valid=0;#1;
 if(in_ready!==1 || out_valid!==0)$fatal(1,"reset did not cancel pending/held work");end endtask
 task issue;begin if(in_ready!==1)$fatal(1,"not ready");req_valid=1;tick;req_valid=0;end endtask
 task await_result;begin n=0;while(out_valid!==1 && n<LANES+2)begin tick;n=n+1;end if(out_valid!==1)$fatal(1,"no completion");end endtask
 task consume;begin out_ready=1;tick;out_ready=0;end endtask
 initial begin tick;rst=0;#1;
 for(phase=0;phase<2;phase=phase+1)begin
 rows=0;cols=0;mask=~0;write_req=1;
 for(i=0;i<LANES;i=i+1)values[32*i+:32]=32'habc00000+i;
 issue;tick; // duplicate-address stores require LANES service cycles
 if(out_valid!==0)$fatal(1,"unexpected early duplicate-store completion");
 if(phase==1)begin await_result;repeat(3)tick;end
 reset_now; // phase0 in flight; phase1 stalled response, with valid hostile input
 write_req=0;rows=0;cols=0;mask=~0;values=~0;issue;await_result;
 if(out_data!==0)$fatal(1,"stale data after cancellation reset");consume;
 repeat(3)begin tick;if(out_valid!==0)$fatal(1,"late response after reset");end
 end
 $display("PASS cancellation 2");$finish;end endmodule''')
  log=simulate_files(p,['candidate.sv','engine.sv','tb.sv'])
  if 'PASS cancellation 2' not in log:raise Rejected('reset cancellation incomplete')
  results.append(stage)
 return {'passed_stages':results,'busy_reset':True,'stalled_response_reset':True,'included_in_reward':False}
