"""Unscored, independent selector-position check against dense expansion."""
from pathlib import Path
import re,json
from ..evaluate import run,tool,TOOLS,Rejected,digest
from .oracle import pack,expected

ZERO=((0,0,0,0),(0,0),6,0)
TB='''module tb;
reg clk=0,rst=1,in_valid=0,out_ready=1;reg [511:0] in_data=0;
wire in_ready,out_valid;wire [31:0] out_data;
candidate INSTANTIATION dut(.*);
reg [511:0] inputs[0:COUNT-1];reg [31:0] expected[0:COUNT-1];
integer sent=0,received=0,t=0;
initial begin
 $readmemh("inputs.hex",inputs);$readmemh("expected.hex",expected);
 #1;clk=1;#1;clk=0;rst=0;
 while(received<COUNT && t<LIMIT)begin
  in_valid=sent<COUNT;if(sent<COUNT)in_data=inputs[sent];#1;
  if((in_ready!==0 && in_ready!==1)||(out_valid!==0 && out_valid!==1))$fatal(1,"decoder unknown handshake");
  if(out_valid)begin
   if(received>=sent || out_data!==expected[received])$fatal(1,"decoder mismatch");
   received=received+1;
  end
  if(in_valid && in_ready)sent=sent+1;
  clk=1;#1;clk=0;#1;t=t+1;
 end
 if(sent!=COUNT || received!=COUNT)$fatal(1,"decoder timeout");
 $display("DECODER_PASS %0d",received);$finish;
end endmodule'''

def vectors(g):
 """Distinct activations, both weight positions, signed weights, every selector and group."""
 inputs=[]
 for group in range(g):
  for selector in range(8):
   for weights in ((2,0),(0,-3),(-4,3)):
    slots=[ZERO]*8
    slots[group]=((-11,5,19,-7),weights,selector,31)
    inputs.append(pack(slots,0,1,0,0))
 return inputs,[expected(x,g) for x in inputs]

def check(g,source,netlist,root):
 root=Path(root);root.mkdir(parents=True,exist_ok=False)
 inputs,outputs=vectors(g)
 (root/'inputs.hex').write_text(''.join(f'{x:0128x}\n' for x in inputs))
 (root/'expected.hex').write_text(''.join(f'{x:08x}\n' for x in outputs))
 (root/'candidate.sv').write_text(source)
 (root/'netlist.v').write_bytes(Path(netlist).read_bytes())
 template=TB.replace('COUNT',str(len(inputs))).replace('LIMIT',str(len(inputs)*(2*g+10)+200))
 for stage,file in (('rtl','candidate.sv'),('mapped','netlist.v')):
  (root/(stage+'-tb.sv')).write_text(template.replace('INSTANTIATION',f'#(.G({g}))' if stage=='rtl' else ''))
  cmd=[tool('iverilog')]
  if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
  run(cmd+['-g2012','-s','tb','-o',stage+'.vvp',file,stage+'-tb.sv'],root,'decoder-'+stage+'-compile',45)
  log=run([tool('vvp'),stage+'.vvp'],root,'decoder-'+stage+'-simulation',90)
  if not re.search(rf'^DECODER_PASS {len(inputs)}$',log,re.M):raise Rejected('incomplete decoder check')
 return {'decoder_vectors_checked':len(inputs),'decoder_vector_sha256':digest(json.dumps(inputs)),
         'decoder_rtl_mapped_checked':True}
