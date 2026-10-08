"""Replay extracted D/Q transitions against the original sequential RTL."""
import argparse,json,random,shutil
from pathlib import Path
from chip_rl.evaluate import run,tool
p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
m=json.loads((a.model/'metadata.json').read_text());assert m['kind']=='original';n=m['state_bits'];aliases={}
for name,i in m['aliases'].items():
 net,bit=name.rsplit(':',1);aliases.setdefault(i,f'seq.{net}[{bit}]' if net not in ('started','dut.ov','dut.busy') else f'seq.{net}')
assert len(aliases)==n
for name in ('candidate.sv','formal.sv','transition.json'):shutil.copyfile(a.model/name,a.output/name)
run([tool('yosys'),'-p','read_json transition.json; write_verilog transition.v'],a.output,'export',35)
rng=random.Random(180018);vectors=[]
for i in range(1200):vectors.append(f"reset_in=1'b{int(i==0 or rng.randrange(50)==0)};in_valid=1'b{rng.randrange(2)};out_ready=1'b{int(rng.randrange(4)!=0)};in_data=1024'h{rng.getrandbits(1024):0256x};tick;")
s='''module tb;reg clk=0,reset_in=0,in_valid=0,out_ready=0;reg [1023:0] in_data=0;
wire in_ready,out_valid;wire [383:0] out_data;formal_top seq(.*);
'''+f'reg [{n-1}:0] state=0;wire [{n-1}:0] next_state,actual;wire ready,valid;wire [383:0] data;transition_original ext(.*);\n'+''.join(f'assign actual[{i}]={aliases[i]};\n' for i in range(n))+'''
integer cycles=0,responses=0;task tick;begin
#5;clk=1;state=next_state;#1;
if(state!==actual)$fatal(1,"state mismatch %0d",cycles);
if(ready!==in_ready || valid!==out_valid || (valid && data!==out_data))$fatal(1,"output mismatch %0d",cycles);
if(out_valid && out_ready)responses=responses+1;
cycles=cycles+1;#4;clk=0;end endtask
initial begin
'''+ '\n'.join(vectors)+'''\nif(responses<10)$fatal(1,"insufficient responses");$display("PASS %0d cycles %0d responses",cycles,responses);$finish;end endmodule\n'''
(a.output/'tb.sv').write_text(s)
run([tool('iverilog'),'-B',str(Path(tool('iverilog')).parent.parent/'lib/x86_64-linux-gnu/ivl'),'-g2012','-s','tb','-o','test.vvp','candidate.sv','formal.sv','transition.v','tb.sv'],a.output,'compile',35)
log=run([tool('vvp'),'test.vvp'],a.output,'simulation',35);assert 'PASS ' in log
(a.output/'result.json').write_text(json.dumps({'status':'extracted_transition_replay_pass','seed':180018,'cycles':1200,'state_bits_checked':n,'source_sha256':m['source_sha256'],'log':log},indent=2));print(log)
