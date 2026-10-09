"""Unscored directed exact probes at source and mapped levels."""
from pathlib import Path
import json,re
from ..evaluate import run,tool,TOOLS,Rejected,digest

TB='''module tb;
reg clk=0,rst=1,in_valid=0,out_ready=1;reg [511:0] in_data=0;
wire in_ready,out_valid;wire [255:0] out_data;
candidate INSTANTIATION dut(.*);
reg [511:0] inputs[0:COUNT-1];reg [255:0] expected[0:COUNT-1];
integer sent=0,received=0,t=0;
initial begin
 $readmemh("inputs.hex",inputs);$readmemh("expected.hex",expected);
 #1;clk=1;#1;clk=0;rst=0;
 while(received<COUNT && t<LIMIT)begin
  in_valid=sent<COUNT;if(sent<COUNT)in_data=inputs[sent];#1;
  if((in_ready!==0 && in_ready!==1)||(out_valid!==0 && out_valid!==1))$fatal(1,"unknown handshake");
  if(out_valid)begin
   if(received>=sent || out_data!==expected[received])$fatal(1,"exact mismatch index=%0d got=%h expected=%h input=%h",received,out_data,expected[received],inputs[received]);
   received=received+1;
  end
  if(in_valid && in_ready)sent=sent+1;
  clk=1;#1;clk=0;#1;t=t+1;
 end
 if(sent!=COUNT || received!=COUNT)$fatal(1,"exact timeout");
 $display("EXACT_PASS %0d",received);$finish;
end endmodule'''

def selected(work):
 return [(x,y) for x,y,label in zip(work['inputs'],work['expected'],work['labels'])
         if label!='random' and not label.startswith('permutation_')]

def check(n,source,netlist,work,root):
 root=Path(root);root.mkdir(parents=True,exist_ok=False)
 probes=selected(work);count=len(probes)
 assert count>=20
 (root/'inputs.hex').write_text(''.join(f'{x:0128x}\n' for x,_ in probes))
 (root/'expected.hex').write_text(''.join(f'{y:064x}\n' for _,y in probes))
 (root/'candidate.sv').write_text(source)
 (root/'netlist.v').write_bytes(Path(netlist).read_bytes())
 template=TB.replace('COUNT',str(count)).replace('LIMIT',str(count*(4*n+40)+100))
 for stage,file in (('rtl','candidate.sv'),('mapped','netlist.v')):
  (root/(stage+'-tb.sv')).write_text(template.replace('INSTANTIATION',f'#(.N({n}))' if stage=='rtl' else ''))
  cmd=[tool('iverilog')]
  if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
  run(cmd+['-g2012','-s','tb','-o',stage+'.vvp',file,stage+'-tb.sv'],root,'arith-'+stage+'-compile',45)
  log=run([tool('vvp'),stage+'.vvp'],root,'arith-'+stage+'-simulation',90)
  if not re.search(rf'^EXACT_PASS {count}$',log,re.M):raise Rejected('incomplete exact check')
 return {'exact_vectors_checked':count,'exact_vector_sha256':digest(json.dumps(probes)),
         'exact_rtl_mapped_checked':True}
