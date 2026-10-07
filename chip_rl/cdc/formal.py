"""Bounded event-enable abstraction, not analog or physical CDC proof."""
import json,tempfile,shutil
from pathlib import Path
from dataclasses import asdict
from ..evaluate import tool,run,Rejected,digest
from .rtl import design

def check(choice,artifacts,mutation=None,bound=24):
 r={'status':'unproven','choice':asdict(choice),'width':4,'depth':2,'bound':bound,'model':'shared-generator event-enable abstraction of independent positive edges','assumptions':'initial coordinated reset for3 events; arbitrary clock enables and inputs; no fairness','unbounded':False,'liveness_proved':False,'metastability_modeled':False,'physical_cdc_safety_verified':False,'mutation':mutation}
 with tempfile.TemporaryDirectory(prefix='cdc-formal-') as td:
  d=Path(td)
  try:
   source=design(choice,formal=True)
   if mutation=='corrupt':source=source.replace('assign r_data=mem[rbin[A-1:0]];','assign r_data=~mem[rbin[A-1:0]];')
   elif mutation=='single_sync':source=source.replace(f'wremote=w_seen{choice.sync_stages},rremote=r_seen{choice.sync_stages}','wremote=w_seen1,rremote=r_seen1')
   elif mutation is not None:raise ValueError('formal mutation')
   (d/'candidate.sv').write_text(source);r['model_sha256']=digest(source)
   (d/'formal.sv').write_text('''module formal_top(input clk,input we,re,input w_valid,r_ready,input [3:0] w_data);
 reg [2:0] boot=0;always @(posedge clk)if(boot<4)boot<=boot+1;
 wire wrst=boot<3,rrst=boot<3;wire wtick=wrst?1'b1:we,rtick=rrst?1'b1:re;
 wire wclk=0,rclk=0,w_ready,r_valid;wire [3:0] r_data;wire [1:0] formal_wgray,formal_rgray;
 candidate #(.WIDTH(4),.DEPTH(2)) dut(.*);
 wire push=wtick && w_valid && w_ready && !wrst;wire pop=rtick && r_valid && r_ready && !rrst;
 reg [3:0] queue[0:1];reg [2:0] used=0;reg stalled=0;reg [3:0] held=0;
 reg [1:0] oldw=0,oldr=0;reg oldwt=0,oldrt=0,oldpush=0,oldpop=0,oldreset=1;
 function [1:0] advance;input [1:0] gray;input take;reg [1:0] binary;begin binary={gray[1],gray[1]^gray[0]}+take;advance=(binary>>1)^binary;end endfunction
 always @(posedge clk)begin
 if(boot!=0)begin
  assert(formal_wgray==(oldwt?(oldreset?0:advance(oldw,oldpush)):oldw));
  assert(formal_rgray==(oldrt?(oldreset?0:advance(oldr,oldpop)):oldr));
 end
 oldw<=formal_wgray;oldr<=formal_rgray;oldwt<=wtick;oldrt<=rtick;oldpush<=push;oldpop<=pop;oldreset<=wrst;
 if(wrst)begin used<=0;stalled<=0;end else begin
  assert(used<=2);if(w_ready)assert(used<2);
  if(r_valid)begin assert(used>0);assert(r_data==queue[0]);end
  if(stalled)begin assert(r_valid);assert(r_data==held);end
  stalled<=r_valid && !pop;held<=r_data;
  if(pop)queue[0]<=queue[1];if(push)queue[used-pop]<=w_data;used<=used+push-pop;
 end end endmodule''')
   (d/'formal.ys').write_text(f'read_verilog -formal -sv candidate.sv formal.sv; prep -top formal_top -flatten; memory_map; opt; async2sync; chformal -lower; sat -seq {bound} -set-init-zero -prove-asserts -verify -timeout 45 -dump_vcd counterexample.vcd')
   log=run([tool('yosys'),'-s','formal.ys'],d,'formal',60)
   if 'SUCCESS!' not in log:raise Rejected('missing bounded success')
   r['status']='bounded_pass'
  except (Rejected,OSError,ValueError) as e:r['error']=str(e)
  (d/'result.json').write_text(json.dumps(r,indent=2)+'\n');shutil.copytree(d,artifacts)
 return r
